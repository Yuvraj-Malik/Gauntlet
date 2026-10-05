"""Benchmark: every scenario x model x trial, guard OFF vs ON on the SAME agent proposals.

Examples:
  py scripts/eval.py                                              # fake agent, instant
  py scripts/eval.py --models groq/openai/gpt-oss-120b --trials 3 --split dev
  py scripts/eval.py --models groq/openai/gpt-oss-120b --split heldout   # final numbers only!
"""
import argparse
import json
import math
import time
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from gauntlet.arena import SCENARIOS  # noqa: E402
from gauntlet.arena.cache import get_proposals  # noqa: E402
from gauntlet.arena.runner import as_dict, run  # noqa: E402


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0, c - h), min(1, c + h)


def pct(k, n):
    if n == 0:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{100*k/n:.0f}% [{100*lo:.0f}-{100*hi:.0f}] ({k}/{n})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="scripted:naive")
    ap.add_argument("--trials", type=int, default=1)
    ap.add_argument("--temperature", type=float, default=None, help="default 0 for 1 trial, else 0.7")
    ap.add_argument("--split", choices=["dev", "heldout", "all"], default="dev")
    ap.add_argument("--only", default=None, help="comma-separated scenario ids")
    a = ap.parse_args()

    models = [m.strip() for m in a.models.split(",") if m.strip()]
    temp = a.temperature if a.temperature is not None else (0.0 if a.trials == 1 else 0.7)
    ids = a.only.split(",") if a.only else [s for s, sc in SCENARIOS.items()
                                            if a.split == "all" or sc.split == a.split]
    out_dir = Path("runs") / f"eval-{time.strftime('%Y%m%d-%H%M%S')}-{a.split}"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows, calls, hits, errors = [], 0, 0, 0
    total, i = len(models) * len(ids) * a.trials, 0
    for model in models:
        for sid in ids:
            sc = SCENARIOS[sid].fill()
            for t in range(a.trials):
                i += 1
                try:
                    props, hit = get_proposals(model, sc, t, temp)
                except Exception as e:
                    errors += 1
                    print(f"[{i}/{total}] {sid} t{t}: ERROR {type(e).__name__}: {str(e)[:120]}")
                    rows.append({"model": model, "scenario": sid, "trial": t, "error": str(e)[:300]})
                    continue
                hits += hit
                calls += not hit
                res = []
                for g in (False, True):
                    o = as_dict(run(SCENARIOS[sid], model, g, live=False, proposals=props))
                    o.update(model=model, trial=t)
                    rows.append(o)
                    res.append(o)
                off, on = res
                tag = ("ATTACK " + ("BLOCKED" if not on["attack_success"] and off["attack_success"] else
                                    "GOT THROUGH" if on["attack_success"] else "agent resisted")
                       if sc.kind == "attack" else
                       ("ok" if on["task_success"] else "FALSE POSITIVE" if on["blocked_correct"] else
                        "held for user" if on["held_correct"] else "agent got it wrong"))
                print(f"[{i}/{total}] {sid:34} t{t} {'(cached) ' if hit else ''}{tag}")

    with (out_dir / "results.jsonl").open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    ok = [r for r in rows if "error" not in r]
    agg = defaultdict(lambda: defaultdict(Decimal))
    cls = defaultdict(lambda: defaultdict(int))
    for r in ok:
        k = (r["model"], "ON" if r["guard"] else "OFF")
        s = agg[k]
        if r["kind"] == "attack":
            s["atk_n"] += 1
            s["atk_win"] += r["attack_success"]
            s["usd_lost"] += Decimal(r["unauthorized_usd"])
            c = cls[(r["model"], r["attack_class"])]
            c["n"] += r["guard"]
            c["on" if r["guard"] else "off"] += r["attack_success"]
        else:
            s["ben_n"] += 1
            s["ben_ok"] += r["task_success"]
            s["fp"] += r["blocked_correct"] > 0
            s["held"] += r["held_correct"] > 0

    L = ["# Gauntlet eval", "",
         f"- split: **{a.split}**  models: {', '.join(models)}  trials: {a.trials}  temperature: {temp}",
         f"- scenarios: {len(ids)}  LLM calls: {calls}  cache hits: {hits}  errors: {errors}",
         "- value [95% Wilson CI] (k/n). Guard OFF and ON are judged on the same agent proposals.", "",
         "| model | guard | attack success ↓ | $ unauthorized ↓ | benign task success ↑ | false-positive blocks ↓ | held for user |",
         "|---|---|---|---|---|---|---|"]
    for (m, g), s in sorted(agg.items()):
        bn = int(s["ben_n"])
        L.append(f"| {m} | {g} | {pct(int(s['atk_win']), int(s['atk_n']))} | ${s['usd_lost']:.2f} | "
                 f"{pct(int(s['ben_ok']), bn)} | {pct(int(s['fp']), bn) if g == 'ON' else '-'} | "
                 f"{pct(int(s['held']), bn) if g == 'ON' else '-'} |")
    L += ["", "## Attack success by class (guard OFF → ON)", "", "| model | class | OFF | ON |", "|---|---|---|---|"]
    for (m, c), s in sorted(cls.items()):
        L.append(f"| {m} | {c} | {pct(s['off'], s['n'])} | {pct(s['on'], s['n'])} |")
    L += ["", "False positive = guard blocked a payment the user actually wanted.",
          "Held for user = guard asked for approval on a wanted payment (friction, not loss)."]
    summary = "\n".join(L)
    (out_dir / "summary.md").write_text(summary, encoding="utf-8")
    print("\n" + summary)


if __name__ == "__main__":
    main()
