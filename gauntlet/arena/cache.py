"""Disk cache of agent proposals, keyed by (model, scenario content, trial, temperature).

Re-running the guard, baselines, or analysis never re-calls the LLM.
Change a scenario's text and its key changes, so stale results can't leak in.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path

from gauntlet.agent import PaymentAgent, ProposedPayment
from .scenario import Scenario

CACHE_DIR = Path(".cache") / "proposals"
VERSION = 2  # bump when the agent's prompt/tools change


def _key(model: str, sc: Scenario, trial: int, temperature: float) -> str:
    blob = json.dumps({"m": model, "i": sc.instruction, "d": sc.documents, "t": trial,
                       "temp": temperature, "v": VERSION}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:24]


def get_proposals(model: str, sc: Scenario, trial: int, temperature: float) -> tuple[list[ProposedPayment], bool]:
    """Returns (proposals, cache_hit). `sc` must already be filled."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    f = CACHE_DIR / f"{_key(model, sc, trial, temperature)}.json"
    if f.exists():
        return [ProposedPayment(d["payee"], Decimal(d["amount"]), d["currency"], d["memo"],
                                d["docs_read"], d.get("invoice_id")) for d in json.loads(f.read_text())], True
    ps, _ = PaymentAgent(model, temperature=temperature).run(sc.instruction, sc.documents)
    f.write_text(json.dumps([{"payee": p.payee, "amount": str(p.amount), "currency": p.currency,
                              "memo": p.memo, "docs_read": p.docs_read, "invoice_id": p.invoice_id}
                             for p in ps]))
    return ps, False
