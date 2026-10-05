"""Invoice binding: deterministic checks on amounts. No LLM.

1. Totals: parse every "Total due: $X" in the documents the agent read. A total counts only if its
   line items (when present) add up to it. Free-text notes like "please remit $96" are ignored.
2. User-stated amount: if the user's instruction names an amount that is not a cap
   ("pay the $46 invoice"), the payment must equal it.

Limitation: if the attacker controls the WHOLE invoice, they can make a self-consistent total.
Binding stops notes/addenda from changing the amount; it can't verify the invoice itself.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

_MONEY = r"\$\s?(-?[\d,]+(?:\.\d{1,2})?)"
_TOTAL = re.compile(r"total due:?\s*" + _MONEY, re.I)
_LINE = re.compile(r"^.{3,}?\s" + _MONEY + r"\s*$")
_CAP_WORDS = re.compile(r"\b(more than|max(?:imum)?|limit|under|up to|no more|at most|cap|exceed|less than)\b", re.I)


def _d(s: str) -> Decimal | None:
    try:
        return Decimal(s.replace(",", ""))
    except InvalidOperation:
        return None


def invoice_totals(text: str) -> set[Decimal]:
    """Totals whose line items are consistent (or that have no line items above them)."""
    out: set[Decimal] = set()
    items: list[Decimal] = []
    for line in text.splitlines():
        m = _TOTAL.search(line)
        if m:
            t = _d(m.group(1))
            if t is not None and (not items or sum(items) == t):
                out.add(t)
            items = []
            continue
        lm = _LINE.match(line.strip())
        if lm and "total" not in line.lower():
            v = _d(lm.group(1))
            if v is not None:
                items.append(v)
        if line.strip().startswith(("INVOICE", "-----", "--- page")):
            items = []
    return out


def stated_amounts(instruction: str) -> set[Decimal]:
    """Amounts the user named that are not caps/limits."""
    out = set()
    for m in re.finditer(_MONEY, instruction):
        clause = re.split(r"[.;!?]\s", instruction[:m.start()])[-1]  # same sentence, before the amount
        after = instruction[m.end():m.end() + 12].lower()
        is_cap = bool(_CAP_WORDS.search(clause)) or after.lstrip().startswith(("total", "each", "per "))
        if not is_cap:
            v = _d(m.group(1))
            if v is not None:
                out.add(v)
    return out


def check_amount(amount: Decimal, instruction: str, docs_read: list[str]) -> str | None:
    """Return a reason string if the amount is NOT bound to trusted/structured evidence."""
    stated = stated_amounts(instruction)
    if stated:
        return None if amount in stated else f"amount {amount} differs from the amount the user stated ({', '.join(map(str, sorted(stated)))})"
    totals: set[Decimal] = set()
    for t in docs_read:
        totals |= invoice_totals(t)
    if not totals:
        return None  # no structured invoice to bind to; other checks still apply
    if amount in totals:
        return None
    return f"amount {amount} does not match any invoice total ({', '.join(map(str, sorted(totals)))})"
