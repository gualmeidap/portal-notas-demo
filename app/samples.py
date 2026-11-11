"""Fictional documents and e-mails used by the demo.

Everything here is invented: company names, CNPJs (fake check digits), e-mail
domains (the reserved `.example` TLD) and amounts. Documents are described as
text lines and rendered to real PDFs by `pdfgen.render_pdf`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional

from .pdfgen import render_pdf

TOMADOR = "INSTITUTO EDUCACIONAL EXEMPLO LTDA"
TOMADOR_CNPJ = "00.111.222/0001-00"

PURCHASING_ADDR = "compras@university.example"
FISCAL_ADDR = "fiscal@university.example"
FINANCE_ADDR = "financeiro@university.example"
MAILBOX_ADDR = "contratos.ti@university.example"


@dataclass
class Attachment:
    filename: str
    lines: List[str] = field(default_factory=list)
    # Scanned documents have no text layer: the PDF is a blank page and the
    # text comes from (mock) OCR, exactly the branch production takes.
    ocr_text: Optional[str] = None
    ocr_confidence: float = 0.95
    data: Optional[bytes] = None  # uploaded files keep their own bytes

    @property
    def scanned(self) -> bool:
        return self.ocr_text is not None

    def pdf(self) -> bytes:
        if self.data is not None:
            return self.data
        return render_pdf([] if self.scanned else self.lines)


def br(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def nf_lines(razao: str, cnpj: str, numero: int, emissao: date, valor: str, descricao: str,
             competencia: date, municipio: str = "EXEMPLO/SP") -> List[str]:
    return [
        f"PREFEITURA MUNICIPAL DE {municipio.split('/')[0]}",
        "NOTA FISCAL DE SERVIÇOS ELETRÔNICA - NFS-e",
        f"Número da Nota: {numero:08d}",
        f"Data de Emissão: {br(emissao)}",
        f"Código de Verificação: {(numero * 7919 + len(razao) * 104729) % 10**8:08d}",
        "",
        "PRESTADOR DE SERVIÇOS",
        f"Razão Social: {razao}",
        f"CNPJ: {cnpj}   Inscrição Municipal: 0000000",
        f"Município: {municipio}",
        "",
        "TOMADOR DE SERVIÇOS",
        f"Nome: {TOMADOR}",
        f"CPF/CNPJ: {TOMADOR_CNPJ}",
        "",
        f"Discriminação dos Serviços: {descricao}",
        f"Competência: {competencia.strftime('%m/%Y')}",
        "",
        f"Valor Total da Nota: R$ {valor}",
        "ISS retido: não",
    ]


def boleto_lines(razao: str, cnpj: str, vencimento: date, valor: str, nosso_numero: int) -> List[str]:
    return [
        f"{razao}",
        "BOLETO DE COBRANÇA",
        f"Beneficiário: {razao} - CNPJ {cnpj}",
        f"Pagador: {TOMADOR}",
        f"Nosso Número: {nosso_numero}",
        f"Data de Vencimento: {br(vencimento)}",
        f"Valor do Documento: R$ {valor}",
        "Linha Digitável: 00190.00009 01234.567893 00000.000000 1 00000000000000",
        "Local de pagamento: pagável em qualquer banco até o vencimento",
    ]


def combined_lines(razao: str, cnpj: str, numero: int, emissao: date, vencimento: date, valor: str,
                   descricao: str, competencia: date) -> List[str]:
    # Some suppliers send a single "fatura" with the NF and the boleto together.
    return nf_lines(razao, cnpj, numero, emissao, valor, descricao, competencia) + [""] + \
        boleto_lines(razao, cnpj, vencimento, valor, numero * 7)[1:]


@dataclass
class SampleEmail:
    sender: str
    subject: str
    body: str
    attachments: List[Attachment]
    days_ago: float = 0
    # Download links resolved by the (mock) scraper, keyed by URL
    links: dict = field(default_factory=dict)
    # What the supplier sends when asked for a missing invoice
    vendor_reply: Optional[List[Attachment]] = None


def _month_back(today: date, n: int) -> date:
    y, m = today.year, today.month - n
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, 1)


def supplier_emails(today: date, month_offset: int = 0, seq: int = 0) -> dict:
    """One month's worth of e-mails per supplier, keyed by supplier.

    `month_offset` lets the seed build past months with the same templates.
    """
    comp = _month_back(today, month_offset + 1)  # service month = previous month
    emissao = _month_back(today, month_offset) + timedelta(days=2)
    venc = _month_back(today, month_offset) + timedelta(days=19)
    n = 1000 + seq * 37 + month_offset * 211

    def nf_boleto(prefix, razao, cnpj, valor, desc, municipio="EXEMPLO/SP"):
        return [
            Attachment(f"{prefix}_NFSe_{n}.pdf", nf_lines(razao, cnpj, n, emissao, valor, desc, comp, municipio)),
            Attachment(f"{prefix}_Boleto_{n}.pdf", boleto_lines(razao, cnpj, venc, valor, n * 3)),
        ]

    mes = comp.strftime("%m/%Y")
    return {
        "FIBRANORTE": SampleEmail(
            "faturamento@fibranorte.example", f"Fatura e NFS-e - competência {mes}",
            "Prezado cliente, seguem em anexo a nota fiscal e o boleto referentes ao link dedicado.",
            nf_boleto("FibraNorte", "FIBRANORTE TELECOM LTDA", "11.222.333/0001-81", "1.890,00",
                      "Link dedicado de internet 500 Mbps - North Campus"),
        ),
        "AURORA NET": SampleEmail(
            "cobranca@auroranet.example", f"Sua fatura Aurora Net chegou ({mes})",
            "Olá! Sua fatura do mês está disponível em anexo (nota fiscal + boleto no mesmo arquivo).",
            [Attachment(f"AuroraNet_Fatura_{n}.pdf", combined_lines(
                "AURORA NET PROVEDOR DE INTERNET LTDA", "22.333.444/0001-92", n, emissao, venc, "749,90",
                "Internet fibra 300 Mbps - South Campus", comp))],
        ),
        "VALELINK": SampleEmail(
            "nfe@valelink.example", f"NFS-e {n} - ValeLink",
            "Segue NFS-e e boleto. Qualquer dúvida estamos à disposição.",
            nf_boleto("ValeLink", "VALELINK INTERNET EIRELI", "33.444.555/0001-03", "1.250,00",
                      "Internet dedicada 200 Mbps + IP fixo - East Campus"),
        ),
        "SINALMAX": SampleEmail(
            "financeiro@sinalmax.example", f"Documentos de cobrança {mes}",
            "Segue documentação digitalizada.",
            [
                Attachment(f"SinalMax_NF_digitalizada_{n}.pdf", ocr_text="\n".join(nf_lines(
                    "SINALMAX TELECOM LTDA", "44.555.666/0001-14", n, emissao, "2.430,00",
                    "Link de dados 1 Gbps - West Campus", comp))),
                Attachment(f"SinalMax_Boleto_{n}.pdf", boleto_lines(
                    "SINALMAX TELECOM LTDA", "44.555.666/0001-14", venc, "2.430,00", n * 5)),
            ],
        ),
        "PONTOCOM FIBRA": SampleEmail(
            "boletos@pontocomfibra.example", f"Boleto PontoCom Fibra - vencimento {br(venc)}",
            "Segue boleto para pagamento. A nota fiscal será enviada separadamente.",
            [Attachment(f"PontoCom_Boleto_{n}.pdf", boleto_lines(
                "PONTOCOM FIBRA LTDA", "55.666.777/0001-25", venc, "599,00", n * 9))],
            vendor_reply=[Attachment(f"PontoCom_NFSe_{n}.pdf", nf_lines(
                "PONTOCOM FIBRA LTDA", "55.666.777/0001-25", n, emissao, "599,00",
                "Internet fibra 100 Mbps - Downtown Campus", comp))],
        ),
        "NUVEMCERTA": SampleEmail(
            "billing@nuvemcerta.example", f"NuvemCerta - Nota fiscal {mes}",
            "Your invoice for cloud hosting is attached.",
            nf_boleto("NuvemCerta", "NUVEMCERTA HOSTING S.A.", "66.777.888/0001-36", "3.120,00",
                      "Hospedagem em nuvem - servidores de aplicação"),
        ),
        "ASSINAFACIL": SampleEmail(
            "no-reply@assinafacil.example", f"Sua nota fiscal AssinaFácil está disponível ({mes})",
            "Olá! A nota fiscal da sua assinatura está disponível para download em "
            f"https://portal.assinafacil.example/nf/download?id=af{n}x . Este link expira em 30 dias.",
            [],
            links={f"https://portal.assinafacil.example/nf/download?id=af{n}x": [
                Attachment(f"AssinaFacil_NF_{n}.pdf", combined_lines(
                    "ASSINAFACIL TECNOLOGIA LTDA", "77.888.999/0001-47", n, emissao, venc, "389,00",
                    "Plano empresarial de assinatura eletrônica", comp))]},
        ),
        "REGISTRA DOMINIOS": SampleEmail(
            "cobranca@registra.example", "Renovação de domínio - documento fiscal",
            "A nota fiscal da renovação está em https://faturas.registra.example/doc/rg" + str(n),
            [],
            links={f"https://faturas.registra.example/doc/rg{n}": [
                Attachment(f"Registra_NF_{n}.pdf", combined_lines(
                    "REGISTRA DOMINIOS E HOSPEDAGEM LTDA", "88.999.000/0001-58", n, emissao, venc, "140,00",
                    "Renovação anual de domínios institucionais", comp))]},
        ),
    }


def unknown_vendor_email(today: date) -> SampleEmail:
    comp = _month_back(today, 1)
    emissao = today - timedelta(days=1)
    venc = today + timedelta(days=15)
    return SampleEmail(
        "nf@horizonteconect.example", "Nota fiscal de serviço - Horizonte Conectividade",
        "Bom dia, segue nota fiscal e boleto do novo contrato de link de backup.",
        [
            Attachment("Horizonte_NFSe_7781.pdf", nf_lines(
                "HORIZONTE CONECTIVIDADE LTDA", "99.000.111/0001-69", 7781, emissao, "980,00",
                "Link de backup 100 Mbps - North Campus", comp, municipio="VALE VERDE/SP")),
            Attachment("Horizonte_Boleto_7781.pdf", boleto_lines(
                "HORIZONTE CONECTIVIDADE LTDA", "99.000.111/0001-69", venc, "980,00", 77810)),
        ],
    )


def newsletter_email() -> SampleEmail:
    return SampleEmail(
        "marketing@eventos-tech.example", "Webinar: tendências de conectividade para 2027",
        "Inscreva-se no nosso webinar gratuito! Vagas limitadas.", [],
    )


def manual_samples(today: date) -> dict:
    """PDFs offered for download so visitors can try the manual upload."""
    comp = _month_back(today, 1)
    return {
        "sample_nfse_valelink.pdf": nf_lines(
            "VALELINK INTERNET EIRELI", "33.444.555/0001-03", 4521, today - timedelta(days=3), "1.250,00",
            "Internet dedicada 200 Mbps + IP fixo - East Campus", comp),
        "sample_boleto_valelink.pdf": boleto_lines(
            "VALELINK INTERNET EIRELI", "33.444.555/0001-03", today + timedelta(days=12), "1.250,00", 99881),
        "sample_nfse_unknown_supplier.pdf": nf_lines(
            "ESTRELA DO SUL REDES LTDA", "12.121.212/0001-12", 310, today - timedelta(days=2), "455,00",
            "Manutenção de rede cabeada - South Campus", comp, municipio="PORTO CLARO/RS"),
    }
