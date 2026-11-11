from datetime import date

from app.i18n import en
from app.extraction import Extractor, fold, format_brl, parse_brl, parse_thread_reply
from app.pdfgen import render_pdf
from app.samples import boleto_lines, combined_lines, nf_lines

TODAY = date(2026, 11, 10)


def test_fold_keeps_length_and_strips_accents():
    text = "Discriminação dos Serviços"
    assert fold(text) == "discriminacao dos servicos"
    assert len(fold(text)) == len(text)


def test_brl_roundtrip():
    assert parse_brl("1.890,00") == 1890.0
    assert format_brl(1890.0) == "R$ 1.890,00"
    assert format_brl(749.9) == "R$ 749,90"


def test_nf_fields_from_a_real_pdf():
    ex = Extractor()
    pdf = render_pdf(nf_lines("FIBRANORTE TELECOM LTDA", "11.222.333/0001-81", 1234, TODAY, "1.890,00",
                              "Link dedicado de internet 500 Mbps - North Campus", date(2026, 10, 1)))
    doc = ex.extract_pdf(pdf, "nf.pdf")
    assert doc.doc_type == "nota_fiscal"
    assert doc.fornecedor == "FibraNorte Telecom"
    assert doc.unidade == "North Campus"
    assert doc.numero == "1234"
    assert doc.emissao == "10/11/2026"
    assert doc.valor == "1.890,00" and doc.valor_num == 1890.0
    assert doc.descricao.startswith("Link dedicado")  # accents and case preserved from the original
    assert doc.competencia == "10/2026"
    assert doc.warnings == []


def test_boleto_and_nf_are_paired_by_amount():
    ex = Extractor()
    nf = ex.extract_text("\n".join(nf_lines("VALELINK INTERNET EIRELI", "33.444.555/0001-03", 9, TODAY, "1.250,00",
                                            "Internet", date(2026, 10, 1))), "nf.pdf")
    other = ex.extract_text("\n".join(boleto_lines("VALELINK INTERNET EIRELI", "33.444.555/0001-03",
                                                   date(2026, 11, 29), "99,00", 1)), "other.pdf")
    boleto = ex.extract_text("\n".join(boleto_lines("VALELINK INTERNET EIRELI", "33.444.555/0001-03",
                                                    date(2026, 11, 30), "1.250,00", 2)), "boleto.pdf")
    assert boleto.doc_type == "boleto"
    records, orphans = ex.build_records([other, nf, boleto])
    assert len(records) == 1
    assert records[0]["vencimento"] == "30/11/2026"  # due date comes from the matching boleto
    assert records[0]["files"] == ["nf.pdf", "boleto.pdf"]
    assert [o.filename for o in orphans] == ["other.pdf"]


def test_combined_document():
    ex = Extractor()
    doc = ex.extract_text("\n".join(combined_lines("AURORA NET PROVEDOR DE INTERNET LTDA", "22.333.444/0001-92", 5,
                                                   TODAY, date(2026, 11, 29), "749,90", "Fibra", TODAY)))
    assert doc.doc_type == "combinado"
    assert doc.vencimento == "29/11/2026"
    assert doc.fornecedor == "Aurora Net Provedor"


def test_unknown_supplier_is_flagged_not_guessed():
    ex = Extractor()
    doc = ex.extract_text("\n".join(nf_lines("ESTRELA DO SUL REDES LTDA", "12.121.212/0001-12", 1, TODAY, "455,00",
                                             "Rede", TODAY)))
    assert doc.fornecedor == "ESTRELA DO SUL REDES LTDA"
    assert doc.unidade == ""
    assert any("not in the rules" in en(w) for w in doc.warnings)


def test_supplier_found_by_cnpj_when_name_differs():
    ex = Extractor()
    doc = ex.extract_text("\n".join(nf_lines("SM TELECOMUNICACOES LTDA", "44.555.666/0001-14", 1, TODAY, "10,00",
                                             "x", TODAY)))
    assert doc.fornecedor == "SinalMax Telecom"


def test_image_only_pdf_has_no_text():
    doc = Extractor().extract_pdf(render_pdf([]), "scan.pdf")
    assert doc.doc_type == "sem_texto"


def test_reply_classification():
    purchasing, fiscal = ["compras@university.example"], ["fiscal@university.example"]
    assert parse_thread_reply("compras@university.example", "Lançado. PEDIDO: 004812", purchasing, fiscal) == \
        {"kind": "purchasing", "po_number": "004812"}
    # Purchasing sometimes answers with "NF <number> <po>" on one line
    assert parse_thread_reply("compras@university.example", "NF 697959    004723", purchasing, fiscal)["po_number"] == "004723"
    assert parse_thread_reply("fiscal@university.example", "FISCAL OK", purchasing, fiscal) == {"kind": "fiscal"}
    assert parse_thread_reply("nf@supplier.example", "Segue a NF", purchasing, fiscal) == {"kind": "supplier"}
