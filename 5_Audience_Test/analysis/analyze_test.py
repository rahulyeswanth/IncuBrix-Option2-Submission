#!/usr/bin/env python3
"""Validate and summarize genuine IncuBrix preference-test responses."""
import argparse
import collections
import csv
import math
from pathlib import Path


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - m) / d, (c + m) / d


def analyze(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as fh:
        raw = list(csv.DictReader(fh))
    rows = [r for r in raw if r.get("participant_id") and r.get("consent(Yes/No)", "").lower() == "yes"
            and r.get("eligible(Yes/No)", "").lower() == "yes"]
    errors = []
    keys = [(r["participant_id"], r.get("pair", "")) for r in rows]
    duplicates = [key for key, n in collections.Counter(keys).items() if n > 1]
    if duplicates:
        errors.append(f"duplicate participant/pair rows: {duplicates}")
    people = sorted({r["participant_id"] for r in rows})
    if len(people) < 20:
        errors.append(f"only {len(people)} eligible consenting participants; need at least 20")
    expected_pairs = {"1", "2", "3", "4", "5"}
    for person in people:
        got = {r["pair"] for r in rows if r["participant_id"] == person}
        if got != expected_pairs:
            errors.append(f"{person} has pairs {sorted(got)}, expected 1-5")
    for r in rows:
        if r.get("stop_on_feed(A/B/neither)", "").strip().lower() not in {"a", "b", "neither"}:
            errors.append(f"{r['participant_id']} pair {r['pair']}: invalid stop-on-feed answer")
    lines = [
        "# Genuine audience preference-test report",
        "",
        f"Eligible consenting participants: **{len(people)}**",
        f"Analyzed pair responses: **{len(rows)}**",
        "",
    ]
    if errors:
        lines += ["## Validation status: NOT COMPLETE", ""] + [f"- {e}" for e in errors]
    else:
        lines += ["## Validation status: COMPLETE", "", "All structural checks passed."]
    lines += ["", "## Pair results", ""]
    by_pair = collections.defaultdict(list)
    for row in rows:
        by_pair[row["pair"]].append(row)
    for pair in sorted(by_pair):
        answers = [r["stop_on_feed(A/B/neither)"].strip().upper() for r in by_pair[pair]]
        a, b = answers.count("A"), answers.count("B")
        n = a + b
        lo, hi = wilson(a, n)
        verdict = "A preferred" if lo > .5 else "B preferred" if hi < .5 else "no clear difference"
        lines.append(
            f"- Pair {pair}: A={a}, B={b}, neither={len(answers)-n}; "
            f"A share={a/n:.1%} (95% CI {lo:.1%}–{hi:.1%}) — {verdict}"
            if n else f"- Pair {pair}: no A/B responses"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "Treat this small convenience sample as directional, not causal proof. "
        "Report recruitment, exclusions, missing data, and all outcomes.",
    ]
    return "\n".join(lines) + "\n", errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", type=Path)
    ap.add_argument("--report", type=Path, default=Path("results_report.md"))
    args = ap.parse_args()
    report, errors = analyze(args.results)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
