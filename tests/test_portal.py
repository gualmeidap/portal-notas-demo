"""Portal pages: month by month, due dates, trash triage, direct send, removal rules, settings, reports."""
import pytest
from fastapi.testclient import TestClient

from app import workflow as wf
from app.i18n import en
from app.main import app
from app.portal import CATEGORIES, categorize
from app.sandbox import DemoError, Sandbox


@pytest.fixture()
def sb():
    return Sandbox()


def by_sender(sb, needle, statuses=wf.QUEUE):
    return next(e for e in sb.emails.values() if needle in e.sender and e.status in statuses)


def test_month_grid_counts_and_marking_outside(sb):
    m = sb.portal.months(sb)
    cur = m["current"]
    assert len(m["months"]) == 4 and m["months"][2] == cur
    total = m["cards"][cur]["total"]
    assert total == 13 and m["cards"][m["months"][0]]["arrived"] == total  # past months: everything arrived
    missed = next(r for r in m["rows"] if r["cells"][cur] == "missed")
    assert sb.portal.mark_outside(missed["name"], cur) == {"marked": True}
    row = next(r for r in sb.portal.months(sb)["rows"] if r["name"] == missed["name"])
    assert row["cells"][cur] == "outside"
    assert sb.portal.mark_outside(missed["name"], cur) == {"marked": False}  # clicking again undoes it
    # on-demand and outside-the-portal suppliers never count
    assert all(r["cells"][cur] == "dash" for r in m["rows"] if not r["tracked"])


def test_processing_an_invoice_registers_the_arrival(sb):
    em = by_sender(sb, "auroranet")
    sb.process(em.id)
    inv = sb.invoices[em.invoice_ids[0]]
    key = ("Aurora Net Provedor", f"{inv['vencimento'][6:10]}-{inv['vencimento'][3:5]}")
    assert sb.portal.arrivals[key]["email_id"] == em.id
    assert sb.portal.arrivals[key]["numero"] == inv["numero"]


def test_due_dates_have_late_soon_and_paid(sb):
    d = sb.portal.due_rows(sb, sb.portal.months(sb)["current"])
    assert d["counts"]["late"] >= 1 and d["counts"]["soon"] >= 1 and d["counts"]["on_demand"] == 1
    late = next(r for r in d["rows"] if r["state"] == "late")
    sb.portal.set_paid(late["name"], d["month"], True)
    row = next(r for r in sb.portal.due_rows(sb, d["month"])["rows"] if r["name"] == late["name"])
    assert row["state"] == "paid"
    assert sb.portal.notifications(sb)["count"] == d["counts"]["late"] + d["counts"]["soon"] - 1


def test_trash_triage_adds_up_and_follows_deletes(sb):
    t = sb.portal.triage(sb)
    assert sum(c["count"] for c in t["categories"]) == t["total"]
    assert {c["key"] for c in t["categories"]} == set(CATEGORIES)
    spam = by_sender(sb, "eventos-tech")
    sb.delete(spam.id)
    assert spam.category == "newsletter"
    assert sb.portal.triage(sb)["total"] == t["total"] + 1
    page = sb.portal.history(sb, "deleted", 1, "newsletter", "")
    assert page["rows"][0]["id"] == spam.id and page["pages"] >= 2
    sb.restore(spam.id)
    assert sb.portal.triage(sb)["total"] == t["total"]


def test_history_filters_and_pagination(sb):
    all_ = sb.portal.history(sb, "all", 1, "", "")
    done = sb.portal.history(sb, "done", 1, "", "")
    assert all_["counts"]["all"] == all_["counts"]["done"] + all_["counts"]["deleted"]
    assert done["total"] == all_["counts"]["done"] and len(all_["rows"]) == 10
    assert sb.portal.history(sb, "all", 999, "", "")["page"] == all_["pages"]
    assert categorize("x", "URGENTE: sua conta será bloqueada") == "scam"


def test_forward_rule_waits_for_the_cover_then_prints(sb):
    em = by_sender(sb, "assinafacil")
    assert sb.email_view(em)["can_forward"]
    sb.forward(em.id)
    assert em.status == wf.AWAITING_COVER
    assert sb.outbox.messages[0]["to"] == "accounts.payable@university.example"
    assert not em.invoice_ids  # the PDF was never read
    sb.simulate_cover_reply(em.id)
    assert em.status == wf.READY_TO_PRINT and sb.package_pdf(em.id).startswith(b"%PDF")
    sb.finalize(em.id)
    assert em.status == wf.DONE
    with pytest.raises(wf.WorkflowError):
        sb.forward(em.id)


def test_process_all_leaves_forward_only_suppliers_alone(sb):
    em = by_sender(sb, "assinafacil")
    sb.process_queue()
    assert em.status == wf.PENDING
    with pytest.raises(DemoError):
        sb.process(em.id)


def test_forward_without_a_rule_is_refused(sb):
    sb.portal.direct_rules.clear()
    em = by_sender(sb, "assinafacil")
    assert not sb.email_view(em)["can_forward"]
    with pytest.raises(DemoError):
        sb.forward(em.id)


def test_direct_send_rule_closes_without_purchasing_and_fiscal():
    c = TestClient(app)
    r = c.put("/api/settings/direct", json={"supplier": "Aurora Net Provedor", "dest": "payer@university.example",
                                            "how": "process", "after": "close", "note": "pays by card"})
    assert r.status_code == 200
    em = next(e for e in c.get("/api/emails?view=queue").json() if "auroranet" in e["sender"])
    out = c.post(f"/api/emails/{em['id']}/actions/process").json()
    assert out["status"] == "Completed"
    assert any(m["to"] == "payer@university.example" for m in c.get("/api/outbox").json())


def test_removal_rules_apply_now():
    c = TestClient(app)
    r = c.post("/api/settings/removal/senders", json={"value": "eventos-tech.example"}).json()
    assert r["removed"] == 1 and "1 e-mail" in r["message"]
    queue = [e["sender"] for e in c.get("/api/emails?view=queue").json()]
    assert not any("eventos-tech" in s for s in queue)
    assert c.post("/api/settings/removal/senders", json={"value": "ab"}).status_code == 422
    assert c.post("/api/settings/removal/nope", json={"value": "abcd"}).status_code == 404


def test_removal_rule_catches_new_mail_on_arrival(sb):
    sb.portal.removal["senders"].append("auroranet.example")
    incoming = by_sender(sb, "auroranet")
    assert sb.apply_removal_rules(incoming) and incoming.status == wf.DELETED
    assert "auroranet.example" in en(incoming.reason)


def test_sector_addresses_are_validated_and_used():
    c = TestClient(app)
    bad = c.put("/api/settings/sectors", json={"purchasing": {"receives": "not-an-email", "also": []},
                                               "fiscal": {"receives": "f@university.example", "also": []}})
    assert bad.status_code == 422
    good = c.put("/api/settings/sectors", json={"purchasing": {"receives": "buy@university.example", "also": []},
                                                "fiscal": {"receives": "f@university.example", "also": []}})
    assert good.status_code == 200
    em = next(e for e in c.get("/api/emails?view=queue").json() if "valelink" in e["sender"] or "pontocom" in e["sender"])
    c.post(f"/api/emails/{em['id']}/actions/process")
    assert c.get("/api/settings").json()["settings"]["purchasing"]["receives"] == "buy@university.example"


def test_description_pattern_changes_the_invoice_description(sb):
    em = by_sender(sb, "auroranet")
    sb.process(em.id)
    row = next(r for r in sb.invoice_rows() if r["email_id"] == em.id)
    assert row["description"].startswith("PAGAMENTO DA NF ") and "LINK DE INTERNET" in row["description"]
    c = TestClient(app)
    assert c.put("/api/pattern", json={"pattern": "no placeholder"}).status_code == 422
    assert c.put("/api/pattern", json={"pattern": "NF {numero} / {fornecedor}"}).status_code == 200
    assert c.get("/api/descriptions").json()["sample"] == "NF 4521 / VALELINK INTERNET"


def test_value_rule_overrides_the_default_description(sb):
    inv = {"numero": "1", "fornecedor": "NuvemCerta Hosting", "vencimento": "10/11/2026", "descricao": "",
           "vendor_key": "NUVEMCERTA"}
    assert "HOSPEDAGEM E NUVEM" in sb.portal.describe({**inv, "valor_num": 100.0})
    assert "ALTO CONSUMO" in sb.portal.describe({**inv, "valor_num": 6000.0})


def test_reports_and_pages_answer_in_both_languages():
    c = TestClient(app)
    paths = ["/api/overview", "/api/months", "/api/due", "/api/triage", "/api/history?filter=deleted&page=2",
             "/api/report/deadlines", "/api/report/senders", "/api/report/senders?group=B", "/api/report/types?kind=scam",
             "/api/descriptions", "/api/settings", "/api/settings/tickets/preview", "/api/settings/teams/preview",
             "/api/notifications", "/api/search?q=aurora", "/api/logs/counts", "/api/logs?level=WARNING&days=30"]
    for lang in ("en", "pt"):
        for path in paths:
            r = c.get(path, headers={"X-Lang": lang})
            assert r.status_code == 200, (path, r.text)
    assert c.get("/api/due?month=2026-13").status_code == 400
    t = c.get("/api/triage", headers={"X-Lang": "pt"}).json()
    assert any(x["label"] == "Suspeito de golpe" for x in t["categories"])


def test_logs_filters():
    c = TestClient(app)
    everything = c.get("/api/logs?days=30").json()
    only_errors = c.get("/api/logs?days=30&level=ERROR").json()
    assert only_errors and all(r["level"] == "ERROR" for r in only_errors) and len(only_errors) < len(everything)
    assert all(r["area"] == "Login" for r in c.get("/api/logs?days=30&area=Login").json())
    assert c.get("/api/logs/counts").json()["areas"]
    assert not c.get("/api/logs?days=1&q=zzzz-nothing").json()


def test_seed_has_no_real_looking_data(sb):
    blob = repr([(e.sender, e.subject) for e in sb.emails.values()]) + repr(sb.portal.rules) + repr(sb.portal.settings)
    for needle in ("@gmail", "@hotmail", ".com.br", ".edu", "192.168"):
        assert needle not in blob, needle
