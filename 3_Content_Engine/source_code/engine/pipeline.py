"""Pipeline: input file(s) -> planned assets -> QA gates -> render -> calendar.csv + scheduler export.

Design rules
  * Deterministic: same input -> same asset_ids, same files. No network, no API cost.
  * Idempotent / refreshable: asset_id = <input-stem-code>-<format>-<nn>. Re-running updates the
    asset in place if its content fingerprint changed; unchanged assets are skipped; stale ones are
    marked retired; nothing is ever appended twice.
  * Crash-safe: files are written as *.part then renamed; state.json is saved atomically after
    every asset, so a failed run resumes where it stopped.
"""
import csv
import datetime as dt
import hashlib
import json
import logging
import os
import re
import shutil
import time
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from . import ai, extract, render

COLUMNS = ["asset_id", "platform", "format", "content_pillar", "hook", "caption", "cta", "utm_link",
           "final_file_url", "source_file_url", "source_input", "tools_used", "rights_checked",
           "ai_label_needed", "scheduled_date", "test_published_url", "impressions_or_views",
           "engagement_rate", "clicks", "status", "notes", "duplicate_check", "completeness_check"]

PILLARS = {
    "Repurposing playbooks": {"slug": "repurposing", "tags": ["#contentrepurposing", "#podcasting", "#contentcreator"],
                              "words": {"recording", "recordings", "episode", "platform", "version", "carousel", "reuse", "spread", "scan",
                                        "windows", "packaging", "original", "shape", "post", "clips"}},
    "Hooks and openings": {"slug": "hooks", "tags": ["#videohooks", "#contentstrategy", "#shortformvideo"],
                           "words": {"hook", "promise", "promises", "overpromises", "open", "greeting", "payoff", "lead", "problem", "number",
                                     "surprising", "scrolling", "claims", "claim", "name", "pause", "breath", "frustrations"}},
    "Captions and editing craft": {"slug": "craft", "tags": ["#videoediting", "#captions", "#contentcreator"],
                                   "words": {"caption", "captions", "cut", "trim", "words", "screen", "edit", "text", "safe", "jargon",
                                             "hashtags", "slide", "twenty", "plain", "line"}},
    "Creator workflow": {"slug": "workflow", "tags": ["#creatorworkflow", "#contentcreator", "#productivity"],
                         "words": {"batch", "session", "track", "list", "history", "test", "compare", "format", "write", "worked", "watch"}},
    "Trust and rights": {"slug": "trust", "tags": ["#creatoreconomy", "#contentcreator", "#podcasting"],
                         "words": {"permission", "guest", "label", "honesty", "trust", "voice", "face", "misled", "agreed", "consent"}},
}

PLATFORM_ROTATION = ["LinkedIn", "Instagram", "YouTube Shorts", "X", "Threads"]
FORMAT_PLAN = [  # (format label, count per input, platforms it may use)
    ("Short video", 8, ["Instagram", "YouTube Shorts", "LinkedIn", "X"]),
    ("Carousel", 4, ["LinkedIn", "Instagram"]),
    ("Graphic", 4, ["LinkedIn", "Instagram", "X", "Threads"]),
    ("Text post", 4, ["LinkedIn", "X", "Threads"]),
]
FMT_CODE = {"Short video": "V", "Carousel": "C", "Graphic": "G", "Text post": "T"}
TOOLS = {"Short video": "IncuBrix content engine (Python, Pillow, ffmpeg); Inter font (SIL OFL)",
         "Carousel": "IncuBrix content engine (Python, Pillow); Inter font (SIL OFL)",
         "Graphic": "IncuBrix content engine (Python, Pillow); Inter font (SIL OFL)",
         "Text post": "IncuBrix content engine (Python)"}

log = logging.getLogger("engine")


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def hook_similarity(a, b):
    """Token Jaccard score used to catch near-duplicate hooks."""
    aa = {t for t in extract.tokens(a) if t not in extract.STOPWORDS}
    bb = {t for t in extract.tokens(b) if t not in extract.STOPWORDS}
    return len(aa & bb) / len(aa | bb) if aa and bb else 0.0


def sha(s, n=8):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:n]


def stem_code(path):
    """Stable short code for an input file name (refresh of the same file keeps the same ids)."""
    stem = Path(path).stem
    return "".join(w[0] for w in re.split(r"[^a-zA-Z0-9]+", stem) if w)[:3].upper() + sha(stem, 3).upper()


def atomic_write(path, data, mode="w"):
    tmp = str(path) + ".part"
    with open(tmp, mode, **({} if "b" in mode else {"encoding": "utf-8", "newline": ""})) as fh:
        fh.write(data)
    os.replace(tmp, path)


class Engine:
    def __init__(self, out_dir, config_dir, start_date=None, base_url=None, ai_enabled=False):
        self.out = Path(out_dir)
        self.cfg = Path(config_dir)
        self.brand = load_json(self.cfg / "brand.json")
        self.plat = {k: v for k, v in load_json(self.cfg / "platforms.json").items() if not k.startswith("_")}
        self.claims = load_json(self.cfg / "claims.json")["claims"]
        po = self.cfg / "pillar_overrides.json"
        self.pillar_map = load_json(po).get("pillars", {}) if po.exists() else {}
        ao = self.cfg / "asset_overrides.json"
        self.asset_overrides = load_json(ao).get("assets", {}) if ao.exists() else {}
        self.theme = render.Theme(self.brand)
        self.base_url = base_url or self.brand["base_url"]
        self.ai_enabled = ai_enabled
        self.ai_runs = []
        self.start = dt.date.fromisoformat(start_date) if start_date else dt.date.today() + dt.timedelta(days=1)
        (self.out / "assets").mkdir(parents=True, exist_ok=True)
        self.state_path = self.out / "state.json"
        self.state = self._load_state()
        self.fail_after = None      # test hook: raise on the Nth render of this run
        self._renders = 0

    # ---------------------------------------------------------------- state
    def _load_state(self):
        if self.state_path.exists():
            try:
                return load_json(self.state_path)
            except json.JSONDecodeError:
                bak = self.state_path.with_suffix(".corrupt.json")
                shutil.move(self.state_path, bak)
                log.error("state.json was corrupt; moved to %s and starting clean", bak.name)
        return {"assets": {}, "hooks": {}, "version": 1}

    def _save_state(self):
        atomic_write(self.state_path, json.dumps(self.state, indent=1, sort_keys=True))

    # ---------------------------------------------------------------- planning
    def plan(self, input_path):
        text = extract.load_text(input_path)
        info = extract.analyse(text, self.brand["max_hook_words"])
        title = extract.load_title(input_path, info["topic"])
        code = stem_code(input_path)
        block = [x.lower() for x in self.brand.get("hook_blocklist", [])]
        hooks = [h for h in info["hooks"] if not re.search(r"\b(it|them|this)\b", h, re.I)
                 and not h.startswith('"') and not any(x in h.lower() for x in block)]
        points = info["points"]
        if len(hooks) < 6 or len(points) < 10:
            raise extract.InputError(f"{input_path}: not enough usable material ({len(hooks)} hooks, {len(points)} points)")
        specs, hi, pi = [], 0, 0
        plat_i = {}
        for fmt, count, plats in FORMAT_PLAN:
            for n in range(1, count + 1):
                hook = hooks[hi % len(hooks)]
                hi += 1
                guard_h = 0
                while fmt != "Carousel" and re.search(r"\bslides?\b", hook, re.I) and guard_h < len(hooks):
                    hook = hooks[hi % len(hooks)]     # slide-specific lines only make sense on carousels
                    hi += 1
                    guard_h += 1
                pts = []
                need = {"Short video": 3, "Carousel": 5, "Graphic": 1, "Text post": 2}[fmt]
                guard = 0
                while len(pts) < need and guard < 200:
                    cand = points[pi % len(points)]
                    pi += 1
                    guard += 1
                    if norm(cand) != norm(hook) and cand not in pts:
                        pts.append(cand)
                platform = plats[plat_i.get(fmt, 0) % len(plats)]
                plat_i[fmt] = plat_i.get(fmt, 0) + 1
                specs.append({"asset_id": f"{code}-{FMT_CODE[fmt]}{n:02d}", "format": fmt, "platform": platform,
                               "hook": hook, "points": pts, "source_title": title, "source_input": Path(input_path).name,
                               "keywords": info["keywords"]})
        for spec in specs:
            override = self.asset_overrides.get(spec["asset_id"])
            if override:
                if "hook" in override:
                    spec["hook"] = override["hook"]
                if "points" in override:
                    spec["points"] = list(override["points"])
                spec["manual_override_reason"] = override.get("reason", "")
        if self.ai_enabled:
            try:
                specs, meta = ai.transform_hooks(specs, text, self.brand["max_hook_words"])
                self.ai_runs.append(meta)
                log.info("AI TRANSFORM accepted %s hook rewrites via %s",
                         meta["accepted_rewrites"], meta["model"])
            except ai.AIUnavailable as exc:
                self.ai_runs.append({"mode": "offline_fallback", "reason": str(exc)})
                log.warning("AI unavailable; deterministic offline fallback used: %s", exc)
        return specs

    def _pillar(self, spec):
        if self.pillar_map.get(spec["hook"]) in PILLARS:
            return self.pillar_map[spec["hook"]]
        hook_t = set(extract.tokens(spec["hook"]))
        pts_t = set(extract.tokens(" ".join(spec["points"])))
        score = {p: 3 * len(hook_t & PILLARS[p]["words"]) + len(pts_t & PILLARS[p]["words"]) for p in PILLARS}
        best = max(PILLARS, key=lambda p: (score[p], -list(PILLARS).index(p)))
        if score[best] == 0:
            best = list(PILLARS)[int(sha(spec["asset_id"], 2), 16) % len(PILLARS)]
        return best

    def _hashtags(self, pillar, platform):
        cfg = self.plat[platform]
        tags = PILLARS[pillar]["tags"]
        k = min(len(tags), cfg["max_hashtags"])
        return tags[:k] if k > 0 else []

    def _cta(self, spec):
        c = self.brand["cta_templates"]
        return c[int(sha(spec["asset_id"], 2), 16) % len(c)]

    def _utm(self, spec, platform, pillar):
        q = {"utm_source": self.plat[platform]["code"], "utm_medium": "organic_social",
             "utm_campaign": self.brand["campaign"], "utm_content": spec["asset_id"],
             "utm_term": PILLARS[pillar]["slug"]}
        return self.base_url + "?" + urlencode(q)

    def _caption(self, spec, pillar, cta, utm):
        platform = spec["platform"]
        limit = self.plat[platform]["max_caption_chars"]
        tags = " ".join(self._hashtags(pillar, platform))
        link = utm
        parts_full = [spec["hook"], *spec["points"][:2], cta, link, tags]
        tight = [spec["hook"], cta, link, tags]
        for parts in (parts_full, tight, [spec["hook"], cta, tags], [spec["hook"], tags], [spec["hook"]]):
            text = "\n\n".join(p for p in parts if p)
            if platform == "X":     # X counts any URL as 23 characters
                n = len(text) - len(link) + 23 if link in text else len(text)
            else:
                n = len(text)
            if n <= limit:
                return text
        return spec["hook"][:limit]

    def _scenes(self, spec, cta):
        fmt, pts = spec["format"], spec["points"]
        if fmt == "Short video":
            sc = [{"kind": "hook", "text": spec["hook"]}]
            sc += [{"kind": "point", "n": i, "text": p} for i, p in enumerate(pts, 1)]
            sc.append({"kind": "cta", "text": cta, "sub": "Follow for more creator workflows."})
            return sc
        if fmt == "Carousel":
            sl = [{"kind": "cover", "text": spec["hook"], "sub": spec["source_title"]}]
            sl += [{"kind": "point", "n": i, "text": p} for i, p in enumerate(pts, 1)]
            sl.append({"kind": "cta", "text": cta, "sub": "Save this and share it with your editor."})
            return sl
        if fmt == "Graphic":
            return [{"kind": "card", "text": spec["hook"], "sub": pts[0] if pts else ""}]
        return []

    # ---------------------------------------------------------------- QA gates
    def qa(self, spec, rec):
        """Return list of (code, severity, message). severity 'reject' blocks; 'hold' -> Draft."""
        issues = []
        b, cfg = self.brand, self.plat[spec["platform"]]
        blob = " ".join([spec["hook"], rec["caption"], " ".join(spec["points"])]).lower()
        words = len(spec["hook"].split())
        if words > b["max_hook_words"] or words < 4:
            issues.append(("HOOK_LENGTH", "reject", f"hook is {words} words"))
        for ph in b["banned_phrases"]:
            if re.search(r"(?<![a-z])" + re.escape(ph.lower()) + r"(?![a-z])", blob):
                issues.append(("BANNED_PHRASE", "reject", f"contains '{ph}'"))
        if sum(blob.count(ch) for ch in "!") > b["max_exclamations"]:
            issues.append(("TOO_MANY_EXCLAMATIONS", "reject", "more than one !"))
        if re.search("[\U0001F300-\U0001FAFF☀-➿]", rec["caption"]) and len(re.findall("[\U0001F300-\U0001FAFF☀-➿]", rec["caption"])) > b["max_emoji"]:
            issues.append(("TOO_MANY_EMOJI", "reject", "more than one emoji"))
        verified = {
            c["feature"].lower() for c in self.claims
            if c.get("verified") and str(c.get("evidence", "")).strip()
        }
        for ph in b["unverified_features"]:
            if ph in blob and ph not in verified:
                issues.append(("UNVERIFIED_FEATURE", "hold", f"mentions '{ph}' (no evidence)"))
        for ph in b["product_claim_triggers"]:
            if ph in blob:
                issues.append(("PRODUCT_CLAIM", "hold", f"product claim '{ph}' needs a verified entry in claims.json"))
        # A verified flag without an evidence reference is never enough.
        for claim in self.claims:
            feature = claim["feature"].lower()
            if feature in blob and feature not in verified:
                issues.append(("UNVERIFIED_CLAIM", "hold", f"'{claim['feature']}' lacks verified evidence"))
        text_len = len(rec["caption"])
        if spec["platform"] == "X":
            text_len = text_len - len(rec["utm_link"]) + 23 if rec["utm_link"] in rec["caption"] else text_len
        if text_len > cfg["max_caption_chars"]:
            issues.append(("CAPTION_TOO_LONG", "reject", f"{text_len}>{cfg['max_caption_chars']}"))
        ntags = len(re.findall(r"#\w+", rec["caption"]))
        if ntags > cfg["max_hashtags"]:
            issues.append(("TOO_MANY_HASHTAGS", "reject", f"{ntags}>{cfg['max_hashtags']}"))
        parsed = urlparse(rec["utm_link"])
        params = parse_qs(parsed.query)
        required_utm = {"utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"}
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or not required_utm.issubset(params):
            issues.append(("NO_UTM", "reject", "tracking link incomplete"))
        elif params["utm_content"][0] != spec["asset_id"]:
            issues.append(("BAD_UTM_ASSET", "reject", "utm_content does not match asset_id"))
        if spec["format"] == "Short video":
            dur = render.video_duration({"scenes": self._scenes(spec, rec["cta"])})
            if dur > cfg["max_video_seconds"] - 2:
                issues.append(("TOO_LONG", "reject", f"{dur:.1f}s"))
        return issues

    # ---------------------------------------------------------------- run
    def run(self, inputs, resume_note=""):
        t0 = time.time()
        summary = {"inputs": len(inputs), "planned": 0, "created": 0, "updated": 0, "unchanged": 0,
                   "rejected": 0, "held": 0, "duplicates_removed": 0, "errors": 0, "retired": 0,
                   "input_words": 0, "failed_inputs": []}
        rejects = []
        seen_hooks = dict(self.state["hooks"])      # normalised hook -> asset_id that owns it
        run_ids = set()
        for ipath in inputs:
            try:
                specs = self.plan(ipath)
                summary["input_words"] += len(extract.load_text(ipath).split())
            except (extract.InputError, OSError) as exc:
                log.error("INPUT REJECTED %s: %s", ipath, exc)
                summary["failed_inputs"].append({"input": str(ipath), "error": str(exc)})
                summary["errors"] += 1
                continue
            summary["planned"] += len(specs)
            for spec in specs:
                aid = spec["asset_id"]
                run_ids.add(aid)
                hk = norm(spec["hook"])
                owner = seen_hooks.get(hk)
                if not owner:
                    owner = next(
                        (existing_owner for existing_hook, existing_owner in seen_hooks.items()
                         if existing_owner != aid and hook_similarity(hk, existing_hook) >= 0.86),
                        None,
                    )
                if owner and owner != aid:
                    log.info("duplicate hook removed: %s duplicates %s", aid, owner)
                    summary["duplicates_removed"] += 1
                    rejects.append({"asset_id": aid, "reason": f"DUPLICATE_HOOK of {owner}", "hook": spec["hook"]})
                    continue
                pillar = self._pillar(spec)
                cta = self._cta(spec)
                utm = self._utm(spec, spec["platform"], pillar)
                rec = {"cta": cta, "utm_link": utm}
                rec["caption"] = self._caption(spec, pillar, cta, utm)
                issues = self.qa(spec, rec)
                rej = [i for i in issues if i[1] == "reject"]
                hold = [i for i in issues if i[1] == "hold"]
                if rej:
                    summary["rejected"] += 1
                    rejects.append({"asset_id": aid, "reason": "; ".join(f"{c}:{m}" for c, _, m in rej), "hook": spec["hook"]})
                    log.warning("REJECT %s %s", aid, rej)
                    continue
                fp = sha(json.dumps([spec["hook"], spec["points"], spec["platform"], rec["caption"], cta], sort_keys=True), 12)
                prev = self.state["assets"].get(aid)
                files_ok = prev and all((self.out / f).exists() and (self.out / f).stat().st_size > 0 for f in prev.get("files", []))
                if prev and prev["fingerprint"] == fp and files_ok:
                    summary["unchanged"] += 1
                    seen_hooks[hk] = aid
                    continue
                try:
                    files = self._produce(spec, rec)
                except Exception as exc:   # one bad asset must never stop the run
                    summary["errors"] += 1
                    log.error("RENDER FAILED %s: %s (will retry on next run)", aid, exc)
                    self._cleanup_parts(aid)
                    continue
                self.state["assets"][aid] = {
                    "fingerprint": fp, "files": files, "platform": spec["platform"], "format": spec["format"],
                    "pillar": pillar, "hook": spec["hook"], "caption": rec["caption"], "cta": cta, "utm_link": utm,
                    "source_input": spec["source_input"], "held": [m for _, _, m in hold], "retired": False,
                    "points": spec["points"], "spec_file": files[0] if files else "",
                    "ai_trace": spec.get("ai_trace", {}),
                    "manual_override_reason": spec.get("manual_override_reason", "")}
                seen_hooks[hk] = aid
                self.state["hooks"] = seen_hooks
                if hold:
                    summary["held"] += 1
                summary["updated" if prev else "created"] += 1
                log.info("%s %s (%s, %s)", "UPDATED" if prev else "CREATED", aid, spec["format"], spec["platform"])
                self._save_state()
        # retire assets whose source input was processed this run but no longer produces them
        processed = {Path(i).name for i in inputs if str(i) not in {f["input"] for f in summary["failed_inputs"]}}
        for aid, a in self.state["assets"].items():
            if a["source_input"] in processed and aid not in run_ids and not a.get("retired"):
                a["retired"] = True
                summary["retired"] += 1
                log.info("RETIRED %s (no longer produced by its input)", aid)
        self.state["hooks"] = seen_hooks
        self._save_state()
        rows = self.export()
        atomic_write(self.out / "rejects.csv", self._csv(["asset_id", "reason", "hook"], rejects))
        summary["runtime_min"] = round((time.time() - t0) / 60, 2)
        summary["items_in_calendar"] = len(rows)
        summary["resume_note"] = resume_note
        summary["transformation"] = self.ai_runs or [{"mode": "deterministic_offline"}]
        atomic_write(self.out / "last_run.json", json.dumps(summary, indent=1))
        return summary

    def _cleanup_parts(self, aid):
        d = self.out / "assets" / aid
        if d.exists():
            for p in d.glob("*.part*"):
                try:
                    p.unlink()
                except OSError:
                    pass

    def _produce(self, spec, rec):
        """Render files for one asset. Returns list of paths relative to out dir (spec.json first)."""
        self._renders += 1
        if self.fail_after is not None and self._renders == self.fail_after:
            self.fail_after = None
            raise RuntimeError("simulated render failure")
        aid, fmt = spec["asset_id"], spec["format"]
        d = self.out / "assets" / aid
        d.mkdir(parents=True, exist_ok=True)
        size = self.plat[spec["platform"]]["video_size" if fmt == "Short video" else "carousel_size" if fmt == "Carousel" else "graphic_size"]
        doc = {"asset_id": aid, "format": fmt, "platform": spec["platform"], "size": size, "hook": spec["hook"],
               "caption": rec["caption"], "cta": rec["cta"], "utm_link": rec["utm_link"],
               "source_input": spec["source_input"], "points": spec["points"]}
        if spec.get("manual_override_reason"):
            doc["manual_override_reason"] = spec["manual_override_reason"]
        files = []
        if fmt == "Short video":
            doc["scenes"] = self._scenes(spec, rec["cta"])
            if spec.get("ai_trace"):
                doc["ai_trace"] = spec["ai_trace"]
            atomic_write(d / "spec.json", json.dumps(doc, indent=1))
            render.render_video(doc, d / "final.mp4", self.theme)
            files = [f"assets/{aid}/spec.json", f"assets/{aid}/final.mp4"]
        elif fmt == "Carousel":
            doc["slides"] = self._scenes(spec, rec["cta"])
            atomic_write(d / "spec.json", json.dumps(doc, indent=1))
            n = render.render_carousel(doc, d, self.theme)
            files = [f"assets/{aid}/spec.json", f"assets/{aid}/carousel.pdf"] + [f"assets/{aid}/slide_{i:02d}.png" for i in range(1, n + 1)]
        elif fmt == "Graphic":
            doc["card"] = self._scenes(spec, rec["cta"])[0]
            atomic_write(d / "spec.json", json.dumps(doc, indent=1))
            render.render_graphic(doc, d / "final.png", self.theme)
            files = [f"assets/{aid}/spec.json", f"assets/{aid}/final.png"]
        else:
            atomic_write(d / "spec.json", json.dumps(doc, indent=1))
            atomic_write(d / "final.txt", rec["caption"] + "\n")
            files = [f"assets/{aid}/spec.json", f"assets/{aid}/final.txt"]
        return files

    # ---------------------------------------------------------------- export
    @staticmethod
    def _csv(cols, rows):
        import io
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
        return buf.getvalue()

    def _final_of(self, a):
        pref = {"Short video": "final.mp4", "Carousel": "carousel.pdf", "Graphic": "final.png", "Text post": "final.txt"}[a["format"]]
        return next(f for f in a["files"] if f.endswith(pref))

    def export(self):
        live = [(k, a) for k, a in sorted(self.state["assets"].items()) if not a.get("retired")]
        # spread posts across days: one post per day per platform lane, round-robin by order
        per_day, rows, day_slot = {}, [], {}
        for idx, (aid, a) in enumerate(live):
            platform = a["platform"]
            n = day_slot.get(platform, 0)
            day_slot[platform] = n + 1
            day = self.start + dt.timedelta(days=n)
            while day.weekday() >= 5:      # skip weekends
                day += dt.timedelta(days=1)
            hhmm = self.plat[platform]["post_time_utc"]
            per_day[aid] = f"{day.isoformat()}T{hhmm}:00Z"
        for aid, a in live:
            status = "Draft" if a["held"] else "Ready"
            notes = "target: engagement rate >= 3% and CTR >= 0.5% (hypothesis, unmeasured)"
            if a["held"]:
                notes = "HELD: " + "; ".join(a["held"])
            rows.append({"asset_id": aid, "platform": a["platform"], "format": a["format"], "content_pillar": a["pillar"],
                         "hook": a["hook"], "caption": a["caption"], "cta": a["cta"], "utm_link": a["utm_link"],
                         "final_file_url": self._final_of(a), "source_file_url": a["spec_file"],
                         "source_input": a["source_input"], "tools_used": TOOLS[a["format"]],
                         "rights_checked": "Yes", "ai_label_needed": "No",
                         "scheduled_date": per_day[aid], "test_published_url": "", "impressions_or_views": "",
                         "engagement_rate": "", "clicks": "", "status": status, "notes": notes})
        ids = [r["asset_id"] for r in rows]
        need = ["platform", "format", "content_pillar", "hook", "caption", "cta", "utm_link", "final_file_url",
                "source_file_url", "rights_checked", "scheduled_date", "status"]
        for r in rows:
            r["duplicate_check"] = "DUPLICATE" if ids.count(r["asset_id"]) > 1 else "UNIQUE"
            r["completeness_check"] = "COMPLETE" if all(r.get(c) for c in need) else "MISSING FIELDS"
        atomic_write(self.out / "calendar.csv", self._csv(COLUMNS, rows))
        sched = [{"scheduled_at_utc": r["scheduled_date"], "platform": r["platform"], "text": r["caption"],
                  "media_file": r["final_file_url"], "link": r["utm_link"], "asset_id": r["asset_id"]}
                 for r in sorted(rows, key=lambda r: r["scheduled_date"]) if r["status"] == "Ready"]
        atomic_write(self.out / "scheduler_export.csv",
                     self._csv(["scheduled_at_utc", "platform", "text", "media_file", "link", "asset_id"], sched))
        return rows
