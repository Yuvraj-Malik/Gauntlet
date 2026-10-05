"""Disk cache of agent proposals, keyed by (model, scenario content, trial, temperature).

Re-running the guard, baselines, or analysis never re-calls the LLM.
Change the scenario text and its key changes, so stale results can't leak in.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path

from gauntlet.agent import PaymentAgent, ProposedPayment
from .scenario import Scenario

CACHE_DIR = Path(".cache") / "proposals"


def _key(model: str, sc: Scenario, trial: int, temperature: float) -> str:
    blob = json.dumps({"m": model, "i": sc.instruction, "d": sc.documents, "t": trial,
                       "temp": temperature, "v": 1}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:24]


def get_proposal(model: str, sc: Scenario, trial: int, temperature: float) -> tuple[ProposedPayment | None, bool]:
    """Returns (proposal, cache_hit). `sc` must already be filled."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    f = CACHE_DIR / f"{_key(model, sc, trial, temperature)}.json"
    if f.exists():
        d = json.loads(f.read_text())
        if d is None:
            return None, True
        return ProposedPayment(d["payee"], Decimal(d["amount"]), d["currency"], d["memo"], d["docs_read"]), True
    p, _ = PaymentAgent(model, temperature=temperature).run(sc.instruction, sc.documents)
    f.write_text(json.dumps(None if p is None else {
        "payee": p.payee, "amount": str(p.amount), "currency": p.currency,
        "memo": p.memo, "docs_read": p.docs_read}))
    return p, False
