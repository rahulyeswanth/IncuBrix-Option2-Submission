#!/usr/bin/env python3
"""Run command:  python run.py inputs/ --out output/

Turns every .md/.txt/.srt/.vtt file in the given paths into platform-ready assets plus
calendar.csv and scheduler_export.csv. Safe to re-run: unchanged assets are skipped, edited
inputs update their assets in place, nothing is duplicated.
"""
import argparse
import logging
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "source_code"))
from engine.pipeline import Engine  # noqa: E402

EXTS = {".md", ".txt", ".srt", ".vtt"}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", help="input files or folders")
    ap.add_argument("--out", default="output", help="output folder (default: output)")
    ap.add_argument("--start-date", help="first posting date, YYYY-MM-DD (default: tomorrow)")
    ap.add_argument("--base-url", help="landing URL for tracking links (default from config/brand.json)")
    ap.add_argument("--simulate-failure", type=int, metavar="N",
                    help="demo only: make the Nth render raise once, to show recovery")
    ap.add_argument("--ai", action="store_true",
                    help="optionally rewrite hooks with an OpenAI-compatible provider; safely falls back offline")
    a = ap.parse_args(argv)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(out / "run.log", encoding="utf-8"), logging.StreamHandler()])
    files = []
    for p in map(Path, a.inputs):
        if p.is_dir():
            files += sorted(f for f in p.iterdir() if f.suffix.lower() in EXTS)
        elif p.exists():
            files.append(p)
        else:
            logging.error("input not found: %s", p)
    if not files:
        logging.error("no input files found")
        return 2
    eng = Engine(out, HERE / "configuration", a.start_date, a.base_url, ai_enabled=a.ai)
    eng.fail_after = a.simulate_failure
    s = eng.run(files)
    logging.info("DONE %s", {k: v for k, v in s.items() if k != "failed_inputs"})
    return 1 if s["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
