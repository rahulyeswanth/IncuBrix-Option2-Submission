#!/usr/bin/env python3
"""Re-render one asset from its (hand-edited) spec.json.

    python tools/rerender.py output/assets/EORC57-V01/spec.json

Use this when you tweak wording in spec.json. Note: the next `run.py` will overwrite
hand edits if the input text produces a different fingerprint; edit the input file instead
for permanent changes.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source_code"))
from engine import render  # noqa: E402


def main(spec_path):
    spec_path = Path(spec_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    theme = render.Theme(json.loads((ROOT / "configuration" / "brand.json").read_text(encoding="utf-8")))
    d = spec_path.parent
    fmt = spec["format"]
    if fmt == "Short video":
        render.render_video(spec, d / "final.mp4", theme)
    elif fmt == "Carousel":
        render.render_carousel(spec, d, theme)
    elif fmt == "Graphic":
        render.render_graphic(spec, d / "final.png", theme)
    else:
        (d / "final.txt").write_text(spec["caption"] + "\n", encoding="utf-8")
    print("re-rendered", spec["asset_id"])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
