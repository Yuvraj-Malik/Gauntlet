# Gauntlet

Red-team benchmark and runtime guard for AI agents that move money through PayPal.
Attacks are scored on real PayPal **sandbox** outcomes, not simulated flags.

> Status: week 1 — guard core + sandbox client. Built for the PayPal AI Hackathon 2026.

## Idea in one line
The guard doesn't ask "does this text look malicious?" It asks "can untrusted data
influence payment parameters?" Untrusted values (payee, amount from an invoice or web page)
are allowed only when trusted evidence backs them up: an allowlist, payee history,
the mandate, or a human step-up. Related work: CaMeL (Debenedetti et al., 2025),
AgentDojo, AP2.

## Setup
```bash
uv venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
cp .env.example .env                      # fill sandbox credentials
pytest
playwright install chromium
python scripts/smoke_sandbox.py   # --show to watch the buyer approve
```

Money moves through **Orders v2** (create -> buyer approves -> capture). Buyer approval is automated
with Playwright and stands in for the user's prior authorization. We use Orders rather than Payouts
because Payouts is unavailable for developer accounts in some countries.

## Layout
- `gauntlet/guard/` — provenance tags, mandate/intent, deterministic policy, isolated verifier hook
- `gauntlet/paypal/` — sandbox REST client (refuses to run against live)
- `scripts/` — smoke tests and runners
- `tests/` — guard unit tests
- `web/` — scoreboard (React + AG Grid), later

## Attack taxonomy (locked)
payee swap · amount/cart drift · split-under-cap · replayed capture · forged invoice

## License
MIT
