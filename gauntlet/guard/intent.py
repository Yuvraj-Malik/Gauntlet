"""What the user authorized (Mandate) and what the agent proposes (PaymentIntent)."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field

from .provenance import Tagged

Action = Literal["create_order", "capture", "payout", "refund", "pay_invoice"]


class Mandate(BaseModel):
    """The user's original, trusted instruction plus hard limits."""
    instruction: str
    max_amount: Decimal
    currency: str = "USD"
    allowed_payees: set[str] = Field(default_factory=set)
    # cumulative cap across the session, defeats split-under-cap
    session_cap: Optional[Decimal] = None


class PaymentIntent(BaseModel):
    """A proposed money movement, with provenance on every parameter."""
    action: Action
    payee: Tagged[str]
    amount: Tagged[Decimal]
    currency: Tagged[str]
    idempotency_key: Optional[str] = None  # PayPal-Request-Id / capture target
    memo: str = ""

    def summary(self) -> str:
        """Plain summary for the isolated verifier. Contains NO untrusted free text."""
        return (f"{self.action}: {self.amount.value} {self.currency.value} "
                f"to {self.payee.value}")
