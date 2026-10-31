"""Run:  python -m unittest discover -s tests -v      (from the 3_Engine folder)

Rendering is stubbed in most tests so the suite runs in seconds; test_real_graphic_render and
test_video_limit exercise the real renderer.
"""
import csv
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source_code"))

from engine import ai, extract, pipeline, render, security  # noqa: E402

INPUT_A = ROOT / "inputs" / "episode_one_recording_a_week_of_content.md"
INPUT_B = ROOT / "inputs" / "episode_two_hooks_and_captions.md"


def fake_video(spec, out, theme):
    Path(out).write_bytes(b"mp4")
    return 30.0


def fake_carousel(spec, out_dir, theme, make_pdf=True):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    n = len(spec["slides"])
    for i in range(1, n + 1):
        (out_dir / f"slide_{i:02d}.png").write_bytes(b"png")
    (out_dir / "carousel.pdf").write_bytes(b"pdf")
    return n


def fake_graphic(spec, out, theme):
    Path(out).write_bytes(b"png")
    return 1


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.out = self.tmp / "out"
        self.patches = [mock.patch.object(render, "render_video", fake_video),
                        mock.patch.object(render, "render_carousel", fake_carousel),
                        mock.patch.object(render, "render_graphic", fake_graphic)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def engine(self, out=None):
        return pipeline.Engine(out or self.out, ROOT / "configuration", "2026-11-02")

    def rows(self, out=None):
        with open((out or self.out) / "calendar.csv", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))


class ExtractTests(unittest.TestCase):
    def test_short_input_rejected(self):
        f = Path(tempfile.mkdtemp()) / "short.txt"
        f.write_text("Too short.")
        with self.assertRaises(extract.InputError):
            extract.load_text(f)

    def test_missing_file_rejected(self):
        with self.assertRaises(extract.InputError):
            extract.load_text("/nonexistent/file.txt")

    def test_srt_timestamps_removed(self):
        body = " ".join(["This is a spoken sentence about editing a video."] * 30)
        f = Path(tempfile.mkdtemp()) / "t.srt"
        f.write_text("1\n00:00:01,000 --> 00:00:04,000\n" + body + "\n")
        text = extract.load_text(f)
        self.assertNotIn("-->", text)

    def test_hooks_are_standalone_and_short(self):
        info = extract.analyse(extract.load_text(INPUT_A), 12)
        self.assertGreaterEqual(len(info["hooks"]), 12)
        for h in info["hooks"]:
            self.assertLessEqual(len(h.split()), 12)
            self.assertTrue(h.endswith((".", "?", "!")))
            self.assertFalse(re.match(r"^(because|and|but|so|that|this|it)\b", h, re.I))

    def test_windows_style_input_name_has_stable_id(self):
        self.assertEqual(pipeline.stem_code(Path("C:/content/my_episode.md")),
                         pipeline.stem_code(Path("D:/other/my_episode.md")))


class PipelineTests(Base):
    def test_human_reviewed_asset_overrides_are_applied(self):
        specs = {s["asset_id"]: s for s in self.engine().plan(INPUT_A)}
        self.assertEqual(
            specs["EORC57-G02"]["points"][0],
            "A claim becomes a video on Monday, a quote card on Tuesday and a carousel on Wednesday.",
        )
        self.assertIn("consent", specs["EORC57-C04"]["manual_override_reason"])

    def test_one_input_makes_at_least_20_assets(self):
        s = self.engine().run([INPUT_A])
        self.assertGreaterEqual(s["created"], 20)
        rows = self.rows()
        self.assertGreaterEqual(len(rows), 20)
        self.assertGreaterEqual(sum(r["format"] == "Short video" for r in rows), 8)

    def test_calendar_has_workbook_columns_and_utm(self):
        self.engine().run([INPUT_A])
        rows = self.rows()
        self.assertEqual(list(rows[0].keys()), pipeline.COLUMNS)
        for r in rows:
            self.assertIn("utm_source=", r["utm_link"])
            self.assertIn(f"utm_content={r['asset_id']}", r["utm_link"])
            self.assertEqual(r["duplicate_check"], "UNIQUE")
            self.assertEqual(r["completeness_check"], "COMPLETE")
            self.assertRegex(r["scheduled_date"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:00Z$")

    def test_no_duplicate_hooks_or_ids(self):
        self.engine().run([INPUT_A, INPUT_B])
        rows = self.rows()
        self.assertEqual(len({r["asset_id"] for r in rows}), len(rows))
        self.assertEqual(len({pipeline.norm(r["hook"]) for r in rows}), len(rows))

    def test_near_duplicate_similarity(self):
        self.assertGreaterEqual(
            pipeline.hook_similarity("Write the hook before editing the video.",
                                     "Write your hook before editing a video."),
            .86,
        )

    def test_repeat_run_changes_nothing(self):
        self.engine().run([INPUT_A])
        before = (self.out / "calendar.csv").read_text()
        s = self.engine().run([INPUT_A])
        self.assertEqual(s["created"], 0)
        self.assertEqual(s["updated"], 0)
        self.assertEqual(s["unchanged"], s["planned"])
        self.assertEqual(before, (self.out / "calendar.csv").read_text())

    def test_refresh_updates_in_place_without_duplicates(self):
        work = self.tmp / "in"
        work.mkdir()
        f = work / "episode.md"
        text = INPUT_A.read_text(encoding="utf-8")
        f.write_text(text, encoding="utf-8")
        self.engine().run([f])
        n1 = len(self.rows())
        ids1 = {r["asset_id"] for r in self.rows()}
        # edit the input: add a strong new sentence + change an existing hook
        f.write_text(text.replace("Never start a clip with a greeting.", "Skip the greeting and start on the point."),
                     encoding="utf-8")
        s = self.engine().run([f])
        self.assertGreater(s["updated"] + s["created"], 0)
        rows = self.rows()
        ids2 = {r["asset_id"] for r in rows}
        self.assertEqual(len(ids2), len(rows))                 # no duplicate ids
        self.assertEqual(ids1, ids2)                            # same slots, updated in place
        self.assertEqual(len(rows), n1)

    def test_shrunk_input_does_not_crash_run(self):
        f = self.tmp / "ep.md"
        f.write_text(INPUT_A.read_text(encoding="utf-8"), encoding="utf-8")
        self.engine().run([f])
        # a much shorter input may be rejected as unusable; the run must log it and carry on, never raise
        sentences = INPUT_A.read_text(encoding="utf-8").split("\n\n")
        f.write_text("\n\n".join(sentences[:12]), encoding="utf-8")
        try:
            self.engine().run([f])
        except extract.InputError:
            self.fail("run() must not raise for a bad input; it logs and continues")

    def test_failure_is_isolated_and_recovered(self):
        eng = self.engine()
        eng.fail_after = 3
        s = eng.run([INPUT_A])
        self.assertEqual(s["errors"], 1)
        self.assertEqual(s["created"], 19)
        s2 = self.engine().run([INPUT_A])
        self.assertEqual(s2["created"], 1)
        self.assertEqual(s2["unchanged"], 19)
        self.assertEqual(s2["errors"], 0)
        self.assertEqual(len(self.rows()), 20)
        self.assertEqual(list(self.out.rglob("*.part*")), [])

    def test_bad_input_does_not_stop_good_input(self):
        bad = self.tmp / "bad.txt"
        bad.write_text("nope")
        s = self.engine().run([bad, INPUT_A])
        self.assertEqual(len(s["failed_inputs"]), 1)
        self.assertGreaterEqual(s["created"], 20)

    def test_deleted_output_file_is_rebuilt(self):
        self.engine().run([INPUT_A])
        victim = next(self.out.glob("assets/*/final.mp4"))
        victim.unlink()
        s = self.engine().run([INPUT_A])
        self.assertEqual(s["created"] + s["updated"], 1)
        self.assertTrue(victim.exists())

    def test_corrupt_state_is_quarantined(self):
        self.engine().run([INPUT_A])
        (self.out / "state.json").write_text("{not json")
        s = self.engine().run([INPUT_A])
        self.assertTrue((self.out / "state.corrupt.json").exists())
        self.assertGreaterEqual(s["created"], 20)

    def test_scheduler_export_only_ready(self):
        self.engine().run([INPUT_A])
        with open(self.out / "scheduler_export.csv", encoding="utf-8") as fh:
            sched = list(csv.DictReader(fh))
        self.assertEqual(len(sched), len([r for r in self.rows() if r["status"] == "Ready"]))
        self.assertEqual(list(sched[0].keys()), ["scheduled_at_utc", "platform", "text", "media_file", "link", "asset_id"])


class QATests(Base):
    def _check(self, hook, caption=None, platform="LinkedIn", fmt="Short video", points=None):
        eng = self.engine()
        spec = {"asset_id": "T-V01", "format": fmt, "platform": platform, "hook": hook,
                "points": points or ["Point one is a calm sentence.", "Point two is also calm."],
                "source_title": "t", "source_input": "t.md", "keywords": []}
        rec = {"cta": "Save this.", "utm_link": "https://incubrix.com/?utm_source=x&utm_content=T-V01"}
        rec["caption"] = caption or eng._caption(spec, "Hooks and openings", rec["cta"], rec["utm_link"])
        return eng.qa(spec, rec)

    def test_banned_phrase_rejected(self):
        codes = [c for c, sev, _ in self._check("This guaranteed trick helps you.") if sev == "reject"]
        self.assertIn("BANNED_PHRASE", codes)

    def test_hook_too_long_rejected(self):
        codes = [c for c, _, _ in self._check("one two three four five six seven eight nine ten eleven twelve thirteen")]
        self.assertIn("HOOK_LENGTH", codes)

    def test_unverified_feature_is_held_not_published(self):
        issues = self._check("Translate your captions into many tongues.")
        self.assertIn(("UNVERIFIED_FEATURE", "hold"), [(c, s) for c, s, _ in issues])

    def test_product_claim_held(self):
        issues = self._check("IncuBrix finds your best clips fast.")
        self.assertIn("PRODUCT_CLAIM", [c for c, _, _ in issues])

    def test_missing_utm_rejected(self):
        eng = self.engine()
        spec = {"asset_id": "T", "format": "Graphic", "platform": "LinkedIn", "hook": "A clear four word hook.",
                "points": ["x y z."], "source_title": "", "source_input": "", "keywords": []}
        issues = eng.qa(spec, {"cta": "c", "utm_link": "https://incubrix.com/", "caption": "A clear four word hook."})
        self.assertIn("NO_UTM", [c for c, _, _ in issues])

    def test_wrong_utm_asset_rejected(self):
        eng = self.engine()
        spec = {"asset_id": "T-V01", "format": "Graphic", "platform": "LinkedIn",
                "hook": "A clear four word hook.", "points": ["One supported point."],
                "source_title": "", "source_input": "", "keywords": []}
        link = ("https://incubrix.com/?utm_source=linkedin&utm_medium=organic_social"
                "&utm_campaign=test&utm_content=WRONG&utm_term=hooks")
        issues = eng.qa(spec, {"cta": "Save this.", "utm_link": link, "caption": spec["hook"]})
        self.assertIn("BAD_UTM_ASSET", [c for c, _, _ in issues])

    def test_x_caption_fits_280_with_link_counted_as_23(self):
        self.engine().run([INPUT_A, INPUT_B])
        for r in self.rows():
            if r["platform"] == "X":
                n = len(r["caption"]) - len(r["utm_link"]) + 23
                self.assertLessEqual(n, 280, r["asset_id"])

    def test_hashtag_limits_respected(self):
        self.engine().run([INPUT_A, INPUT_B])
        limits = pipeline.load_json(ROOT / "configuration" / "platforms.json")
        for r in self.rows():
            self.assertLessEqual(len(re.findall(r"#\w+", r["caption"])), limits[r["platform"]]["max_hashtags"])


class RealRenderTests(unittest.TestCase):
    def setUp(self):
        self.theme = render.Theme(pipeline.load_json(ROOT / "configuration" / "brand.json"))

    def test_real_graphic_render(self):
        out = Path(tempfile.mkdtemp()) / "g.png"
        render.render_graphic({"size": [1080, 1350], "card": {"text": "One clear idea per post.", "sub": "Then ship it."}},
                              out, self.theme)
        self.assertGreater(out.stat().st_size, 5000)

    def test_video_limit(self):
        long_scene = {"kind": "point", "n": 1, "text": " ".join(["word"] * 30)}
        spec = {"size": [1080, 1920], "scenes": [long_scene] * 6}
        with self.assertRaises(render.RenderError):
            render.render_video(spec, Path(tempfile.mkdtemp()) / "v.mp4", self.theme)

    def test_carousel_slide_bounds(self):
        with self.assertRaises(render.RenderError):
            render.render_carousel({"size": [1080, 1350], "slides": [{"kind": "cover", "text": "x"}]},
                                   Path(tempfile.mkdtemp()), self.theme)


class RepoHygiene(unittest.TestCase):
    def test_no_secrets_in_repo(self):
        self.assertEqual(security.scan_repository(ROOT), [])

    def test_fake_secret_fixture_is_detected(self):
        root = Path(tempfile.mkdtemp())
        try:
            fake = "sk-" + "FAKEONLYFORTESTS1234567890"
            (root / "config.py").write_text(f'TEST_VALUE = "{fake}"')
            findings = security.scan_repository(root)
            self.assertEqual([p.name for p, _ in findings], ["config.py"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_third_party_dependencies_are_excluded(self):
        root = Path(tempfile.mkdtemp())
        try:
            dep = root / "venv" / "Lib" / "site-packages" / "PIL"
            dep.mkdir(parents=True)
            fake = "sk-" + "DEPENDENCYONLY123456789012"
            (dep / "ImageFont.py").write_text(f'EXAMPLE = "{fake}"')
            self.assertEqual(security.scan_repository(root), [])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_no_env_files(self):
        self.assertEqual(
            [p for p in ROOT.rglob(".env*") if not security.is_excluded(p, ROOT)],
            [],
        )


class OptionalAITests(unittest.TestCase):
    def test_ai_is_optional_and_requires_environment(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ai.AIUnavailable):
                ai.transform_hooks([], "A source sentence.", 12)

    def test_ai_traceability_rejects_new_numbers(self):
        self.assertFalse(ai._safe_rewrite(
            "Use one idea.", "Use 99 ideas today.", "Use one idea.",
            "Use one idea.", 12,
        ))


if __name__ == "__main__":
    unittest.main()
