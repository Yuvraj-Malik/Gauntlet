"""Deterministic policy checks. No LLM, no text classification."""
from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field

from .intent import Mandate, PaymentIntent


class Verdict(str, Enum):
    ALLOW = "allow"
    STEP_UP = "step_up"   # hold and ask the human
    BLOCK = "block"


class Decision(BaseModel):
    verdict: Verdict
    reasons: list[str] = Field(default_factory=list)


class GuardState(BaseModel):
    """Trusted state the guard owns. Never written from untrusted content."""
    payee_history: set[str] = Field(default_factory=set)
    seen_keys: set[str] = Field(default_factory=set)
    spent: Decimal = Decimal("0")


_RANK = {Verdict.ALLOW: 0, Verdict.STEP_UP: 1, Verdict.BLOCK: 2}


def worst(a: Verdict, b: Verdict) -> Verdict:
    return a if _RANK[a] >= _RANK[b] else b


def evaluate(intent: PaymentIntent, mandate: Mandate, state: GuardState) -> Decision:
    verdict, reasons = Verdict.ALLOW, []

    def flag(v: Verdict, why: str) -> None:
        nonlocal verdict
        verdict = worst(verdict, v)
        reasons.append(why)

    amt = intent.amount.value
    if amt <= 0:
        flag(Verdict.BLOCK, "non-positive amount")
    if amt > mandate.max_amount:
        flag(Verdict.BLOCK, f"amount {amt} exceeds mandate cap {mandate.max_amount}")
    if intent.currency.value != mandate.currency:
        flag(Verdict.BLOCK, f"currency {intent.currency.value} != mandate {mandate.currency}")
    if mandate.session_cap is not None and state.spent + amt > mandate.session_cap:
        flag(Verdict.BLOCK, f"session total {state.spent + amt} exceeds cap {mandate.session_cap}")

    # Replay: same capture / request id used twice
    if intent.idempotency_key and intent.idempotency_key in state.seen_keys:
        flag(Verdict.BLOCK, f"replayed key {intent.idempotency_key}")

    # Payee: untrusted origin is OK only if trusted evidence backs it up
    payee = intent.payee.value.lower()
    known = payee in {p.lower() for p in mandate.allowed_payees} or payee in state.payee_history
    if mandate.allowed_payees and not known:
        if intent.payee.untrusted:
            flag(Verdict.BLOCK, f"payee {payee} from untrusted source and not allowlisted")
        else:
            flag(Verdict.STEP_UP, f"payee {payee} not in allowlist")
    elif not known and intent.payee.untrusted:
        flag(Verdict.STEP_UP, f"new payee {payee} came from {intent.payee.origin or 'untrusted content'}")

    # Amount derived from untrusted content: allowed under cap, but note it
    if intent.amount.untrusted and verdict == Verdict.ALLOW:
        reasons.append(f"amount from {intent.amount.origin or 'untrusted'} within mandate")

    return Decision(verdict=verdict, reasons=reasons)
