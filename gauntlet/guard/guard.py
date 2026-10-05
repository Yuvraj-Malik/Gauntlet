"""The guard: deterministic policy first, isolated LLM verifier second."""
from __future__ import annotations

from typing import Callable, Optional

from .intent import Mandate, PaymentIntent
from .policy import Decision, GuardState, Verdict, evaluate, worst

# verifier(user_instruction, intent_summary) -> (consistent?, reason)
# It must NEVER receive untrusted content. Only these two strings.
Verifier = Callable[[str, str], "tuple[bool, str]"]


class Guard:
    def __init__(self, mandate: Mandate, state: Optional[GuardState] = None,
                 verifier: Optional[Verifier] = None):
        self.mandate = mandate
        self.state = state or GuardState()
        self.verifier = verifier

    def check(self, intent: PaymentIntent) -> Decision:
        decision = evaluate(intent, self.mandate, self.state)
        if decision.verdict == Verdict.BLOCK or self.verifier is None:
            return decision
        ok, why = self.verifier(self.mandate.instruction, intent.summary())
        if not ok:
            decision.verdict = worst(decision.verdict, Verdict.STEP_UP)
            decision.reasons.append(f"verifier: {why}")
        return decision

    def record(self, intent: PaymentIntent) -> None:
        """Call only after the payment actually succeeded on PayPal."""
        self.state.spent += intent.amount.value
        self.state.payee_history.add(intent.payee.value.lower())
        if intent.idempotency_key:
            self.state.seen_keys.add(intent.idempotency_key)
