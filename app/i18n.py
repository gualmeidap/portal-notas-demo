"""Bilingual messages (English / Portuguese).

Business code never formats text for one language. Every user-facing message
is a `T(en, pt)` pair; the API boundary picks the visitor's language with
`localize()`. Because pairs are stored as-is (logs, timeline, issues), the
language toggle also translates everything that already happened.
"""
from __future__ import annotations

from typing import Any, Iterable

LANGS = ("en", "pt")


class T(tuple):
    """An (english, portuguese) message. Hashable and sortable, like a str."""

    def __new__(cls, en: str, pt: str):
        return super().__new__(cls, (en, pt))

    def __getnewargs__(self):  # pickle / copy support
        return (self[0], self[1])

    def __deepcopy__(self, memo):  # immutable
        return self

    @property
    def en(self) -> str:
        return self[0]

    @property
    def pt(self) -> str:
        return self[1]

    def get(self, lang: str) -> str:
        return self[1] if lang == "pt" else self[0]

    def __add__(self, other):  # T + T / T + str keeps both languages
        if isinstance(other, T):
            return T(self[0] + other[0], self[1] + other[1])
        if isinstance(other, str):
            return T(self[0] + other, self[1] + other)
        return NotImplemented


def tjoin(sep: str, items: Iterable[Any]) -> T:
    items = [i if isinstance(i, T) else T(str(i), str(i)) for i in items]
    return T(sep.join(i.en for i in items), sep.join(i.pt for i in items))


def en(value: Any) -> str:
    return value.en if isinstance(value, T) else value


def localize(value: Any, lang: str) -> Any:
    """Recursively replace every T in a JSON-like payload by one language."""
    if isinstance(value, T):
        return value.get(lang)
    if isinstance(value, dict):
        return {k: localize(v, lang) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [localize(v, lang) for v in value]
    return value


def pick_lang(raw: str) -> str:
    raw = (raw or "").lower()
    return "pt" if raw.startswith("pt") else "en"
