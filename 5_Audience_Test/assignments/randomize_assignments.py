#!/usr/bin/env python3
"""Create reproducible, balanced preference-test presentation assignments."""
import argparse
import csv
import random
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--participants", type=int, default=20)
    ap.add_argument("--seed", type=int, default=20261102)
    ap.add_argument("--out", type=Path, default=Path("assignments.csv"))
    args = ap.parse_args()
    if args.participants < 20:
        ap.error("the assessment requires at least 20 participants")
    pairs = list(csv.DictReader(Path(__file__).with_name("pair_definitions.csv").open(encoding="utf-8-sig")))
    rng = random.Random(args.seed)
    rows = []
    for number in range(1, args.participants + 1):
        ordered = pairs[:]
        rng.shuffle(ordered)
        for position, pair in enumerate(ordered, 1):
            swap = rng.choice([False, True])
            rows.append({
                "participant_id": f"P{number:02d}",
                "presentation_position": position,
                "pair": pair["pair"],
                "shown_first_label": "B" if swap else "A",
                "shown_first_asset_id": pair["asset_id_B"] if swap else pair["asset_id_A"],
                "shown_second_label": "A" if swap else "B",
                "shown_second_asset_id": pair["asset_id_A"] if swap else pair["asset_id_B"],
                "seed": args.seed,
            })
    with args.out.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} assignments for {args.participants} participants to {args.out}")


if __name__ == "__main__":
    main()
