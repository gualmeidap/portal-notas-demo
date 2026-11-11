import pytest

from app import workflow as wf
from app.i18n import en
from app.sandbox import DemoError, Sandbox, SandboxManager


@pytest.fixture(scope="module")
def template():
    return Sandbox()


@pytest.fixture
def sb(template):
    import copy
    return copy.deepcopy(template)


def by_sender(sb, needle):
    return next(e for e in sb.emails.values() if needle in e.sender and e.status in wf.QUEUE)


def test_seed_has_history_and_work_in_progress(sb):
    s = sb.summary()
    assert s["by_status"][wf.DONE] >= 16
    assert s["in_workflow"] == 4
    assert s["queue"] == 4
    assert s["incoming"] == 2


def test_happy_path_through_every_state(sb):
    em = by_sender(sb, "auroranet")
    assert sb.process(em.id)["status"] == wf.AWAITING_PURCHASING
    assert sb.outbox.messages[0]["to"] == "purchasing.south@university.example"  # per-supplier Purchasing rule
    sb.simulate_purchasing_reply(em.id)
    assert em.status == wf.READY_FOR_FISCAL and em.po_number
    sb.send_fiscal(em.id)
    sb.simulate_fiscal_reply(em.id)
    assert em.status == wf.READY_TO_PRINT
    assert em.sharepoint_url.startswith("https://tenant.sharepoint.example/")
    assert sb.package_pdf(em.id).startswith(b"%PDF")
    sb.finalize(em.id)
    assert em.status == wf.DONE
    assert [t["status"] for t in em.timeline][-1] == wf.DONE


def test_direct_to_fiscal_supplier_skips_purchasing_and_scraper_downloads_link(sb):
    sb.portal.direct_rules.clear()  # the seeded forward rule is covered by its own test
    em = by_sender(sb, "assinafacil")
    assert not em.attachments
    sb.process(em.id)
    assert em.status == wf.AWAITING_FISCAL
    assert em.attachments and em.attachments[0].filename.startswith("AssinaFacil_NF_")


def test_missing_invoice_round_trip(sb):
    em = by_sender(sb, "pontocom")
    sb.process(em.id)
    assert em.status == wf.MISSING_NF
    with pytest.raises(DemoError):
        sb.simulate_supplier_reply(em.id)  # must ask first
    sb.request_invoice(em.id)
    sb.simulate_supplier_reply(em.id)
    assert em.status == wf.AWAITING_PURCHASING


def test_review_paths_after_inbox_sync(sb):
    sb.fetch_inbox()
    scanned = by_sender(sb, "sinalmax")
    unknown = by_sender(sb, "horizonte")
    assert "OCR confidence" in en(sb.process(scanned.id)["message"])
    assert scanned.status == wf.PENDING
    sb.process(unknown.id)
    assert "not in the rules" in en(unknown.issue)

    # Operator fixes the unknown supplier in the editable preview
    recs = sb.preview(unknown.id)["records"]
    recs[0]["unidade"] = "North Campus"
    recs[0]["fornecedor"] = "Horizonte Conectividade"
    sb.confirm(unknown.id, recs)
    assert unknown.status == wf.AWAITING_PURCHASING


def test_registering_supplier_with_llm_unblocks_extraction(sb):
    sb.fetch_inbox()
    em = by_sender(sb, "horizonte")
    suggestion = sb.ai_vendor(email_id=em.id)["suggestion"]
    assert suggestion["chave_normalizada"] == "HORIZONTE CONECTIVIDADE"
    assert suggestion["unidade"] == "Vale Verde"
    sb.upsert_vendor(suggestion["chave_normalizada"], {"fornecedor": "Horizonte Conectividade",
                                                       "unidade": "North Campus"})
    assert sb.process(em.id)["status"] == wf.AWAITING_PURCHASING


def test_delete_and_restore_moves_mailbox_folder(sb):
    em = by_sender(sb, "eventos-tech")
    sb.process(em.id)
    assert "No attachment" in en(em.issue)
    sb.delete(em.id)
    assert em.timeline[-1]["folder"] == "Fila_Excluidos"
    sb.restore(em.id)
    assert em.status == wf.PENDING and em.timeline[-1]["folder"] == "Inbox/Fila_Pendente"


def test_invalid_transition_is_refused(sb):
    em = by_sender(sb, "auroranet")
    with pytest.raises(wf.WorkflowError):
        sb.finalize(em.id)


def test_confirm_validates_fields(sb):
    em = by_sender(sb, "auroranet")
    with pytest.raises(DemoError) as err:
        sb.confirm(em.id, [{"fornecedor": "X", "unidade": "", "numero": "1", "valor": "abc"}])
    assert err.value.status == 422


def test_manual_upload_preview_then_confirm(sb):
    samples = sb.samples()
    p = sb.manual_preview([("nf.pdf", samples["sample_nfse_valelink.pdf"]),
                           ("boleto.pdf", samples["sample_boleto_valelink.pdf"])])
    assert len(p["records"]) == 1 and p["records"][0]["vencimento"]
    before = len(sb.invoices)
    r = sb.manual_confirm(p["token"], p["records"], "fiscal")
    assert r["status"] == wf.AWAITING_FISCAL
    assert len(sb.invoices) == before + 1
    with pytest.raises(DemoError):  # token is single-use
        sb.manual_confirm(p["token"], p["records"], "fiscal")


def test_manual_upload_rejects_non_pdf(sb):
    with pytest.raises(DemoError):
        sb.manual_preview([("x.txt", b"hello")])


def test_finance_spreadsheet(sb):
    from io import BytesIO
    from openpyxl import load_workbook
    ws = load_workbook(BytesIO(sb.finance_xlsx())).active
    assert ws["A1"].value == "Unidade"
    assert ws.max_row == len(sb.invoice_rows()) + 1


def test_sandboxes_are_isolated_and_evicted():
    mgr = SandboxManager(factory=lambda: Sandbox(seed=False), max_sessions=2)
    a, b = mgr.get("a"), mgr.get("b")
    assert a is not b and mgr.get("a") is a
    mgr.get("c")
    assert len(mgr) == 2 and mgr.get("b") is not b  # least recently used went away
