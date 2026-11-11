"""Processing workflow: states, allowed transitions and mailbox folders.

The production system keeps two things in sync: the status in PostgreSQL and
the physical folder/read flag of the message in the Microsoft 365 mailbox, so
the inbox stays organized even for people who never open the web app.

English names are used in the demo; the production (Portuguese) name is kept
next to each state for reference.
"""
from __future__ import annotations

from .i18n import T

PENDING = "Pending"                          # Pendente
MISSING_NF = "Missing invoice"               # Sem Nota Fiscal
AWAITING_PURCHASING = "Awaiting Purchasing"  # Aguardando Compras
READY_FOR_FISCAL = "Ready for Fiscal"        # Aguardando Envio Fiscal
AWAITING_FISCAL = "Awaiting Fiscal"          # Aguardando Fiscal (or "Direto Fiscal" suppliers)
AWAITING_COVER = "Awaiting Cover"            # Aguardando Capa (direct-send suppliers)
READY_TO_PRINT = "Ready to print"            # Pronto para Impressão
DONE = "Completed"                           # Concluído
DELETED = "Deleted"                          # Excluído

PRODUCTION_NAMES = {
    PENDING: "Pendente",
    MISSING_NF: "Sem Nota Fiscal",
    AWAITING_PURCHASING: "Aguardando Compras",
    READY_FOR_FISCAL: "Aguardando Envio Fiscal",
    AWAITING_FISCAL: "Aguardando Fiscal",
    AWAITING_COVER: "Aguardando Capa",
    READY_TO_PRINT: "Pronto para Impressão",
    DONE: "Concluído",
    DELETED: "Excluído",
}

QUEUE = (PENDING, MISSING_NF)
BOARD = (AWAITING_PURCHASING, READY_FOR_FISCAL, AWAITING_FISCAL, AWAITING_COVER, READY_TO_PRINT)
CLOSED = (DONE, DELETED)

# action -> (states it may start from, resulting state or None when it depends)
TRANSITIONS = {
    "process": ((PENDING,), None),
    "confirm": ((PENDING,), None),
    "delete": ((PENDING, MISSING_NF, AWAITING_PURCHASING, READY_FOR_FISCAL, AWAITING_FISCAL, AWAITING_COVER, READY_TO_PRINT), DELETED),
    "restore": ((DELETED,), PENDING),
    "request_invoice": ((MISSING_NF,), MISSING_NF),
    "simulate_supplier_reply": ((MISSING_NF,), None),
    "simulate_purchasing_reply": ((AWAITING_PURCHASING,), READY_FOR_FISCAL),
    "send_fiscal": ((READY_FOR_FISCAL,), AWAITING_FISCAL),
    "simulate_fiscal_reply": ((AWAITING_FISCAL,), READY_TO_PRINT),
    "forward": ((PENDING,), None),
    "simulate_cover_reply": ((AWAITING_COVER,), READY_TO_PRINT),
    "finalize": ((READY_TO_PRINT,), DONE),
}


class WorkflowError(Exception):
    """Raised when an action is not allowed from the e-mail's current state."""


def check(action: str, status: str) -> None:
    if action not in TRANSITIONS:
        raise WorkflowError(T(f"Unknown action '{action}'.", f"Ação desconhecida '{action}'."))
    allowed, _ = TRANSITIONS[action]
    if status not in allowed:
        raise WorkflowError(T(f"'{action}' is not allowed while the e-mail is '{status}'.",
                              f"'{action}' não é permitido enquanto o e-mail está em '{PRODUCTION_NAMES[status]}'."))


def mailbox_state(status: str) -> tuple:
    """(folder, is_read) the message should have in the mailbox for a status."""
    if status in QUEUE:
        return "Inbox/Fila_Pendente", False
    if status == DELETED:
        return "Fila_Excluidos", True
    return "Inbox", True
