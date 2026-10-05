"""Run scenarios with and without the guard.

Examples:
  py scripts/run_scenario.py                                  # all scenarios, fake agent, no PayPal
  py scripts/run_scenario.py --model groq/llama-3.3-70b-versatile
  py scripts/run_scenario.py --model groq/llama-3.3-70b-versatile --live --only payee_swap_hidden_01
"""
import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from gauntlet.arena import SCENARIOS  # noqa: E402
from gauntlet.arena.runner import as_dict, run  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="scripted:naive")
    ap.add_argument("--live", action="store_true", help="really move sandbox money")
    ap.add_argument("--show", action="store_true", help="show the approval browser")
    ap.add_argument("--only", default=None)
    ap.add_argument("--guard", choices=["off", "on", "both"], default="both")
    a = ap.parse_args()

    guards = {"off": [False], "on": [True], "both": [False, True]}[a.guard]
    ids = [a.only] if a.only else list(SCENARIOS)
    Path("runs").mkdir(exist_ok=True)
    out = Path("runs") / "latest.jsonl"
    with out.open("w") as f:
        for sid in ids:
            for g in guards:
                o = run(SCENARIOS[sid], a.model, g, a.live, a.show)
                f.write(json.dumps(as_dict(o)) + "\n")
                mark = "ATTACK SUCCEEDED" if o.attack_success else ("task ok" if o.task_success else "-")
                print(f"{sid:28} guard={'ON ' if g else 'OFF'} verdict={o.verdict:10} "
                      f"paid_to={o.paid_to or '(nothing)':42} {mark}")
                if o.capture_id:
                    print(f"{'':34}PayPal: order {o.order_id}, capture {o.capture_id} (search this in the receiver's Activity)")
                for r in o.reasons:
                    print(f"{'':34}reason: {r}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
