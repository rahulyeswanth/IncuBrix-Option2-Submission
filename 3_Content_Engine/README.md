# IncuBrix content engine

This Python engine turns one `.md`, `.txt`, `.srt`, or `.vtt` input into 20
platform-specific assets: 8 short videos, 4 carousels, 4 graphics, and 4 text
posts. Offline mode is deterministic, costs USD 0, and is the default.

## Architecture

1. `extract.py` decodes UTF-8/UTF-16/Latin-1, removes transcript markup, and
   extracts source-backed hooks, points, and keywords.
2. `pipeline.py` assigns platforms and pillars, creates captions/CTAs/UTMs,
   rejects exact and near-duplicate hooks, applies QA gates, and persists state.
3. `render.py` creates editable JSON specs, PNG/PDF media, and MP4 videos with
   transitions, karaoke highlighting, progress bars, and CTA end screens.
4. `ai.py` is an optional OpenAI-compatible hook rewriter. It accepts only
   rewrites tied to a verbatim source sentence and falls back offline on error.
5. `security.py` scans first-party source/configuration while excluding virtual
   environments, `site-packages`, caches, evidence, and generated media.

## Prerequisites

- Python 3.9 or newer
- FFmpeg with `libx264`, available on `PATH`
- No account, network, or paid API for offline mode

### Windows PowerShell setup

```powershell
cd .\3_Content_Engine
py -3 -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
ffmpeg -version
python .\run.py .\inputs\ --out .\output\ --start-date 2026-11-02
```

Install FFmpeg with either `winget install Gyan.FFmpeg` or a trusted manual
distribution, then reopen PowerShell. Confirm with `ffmpeg -version`.

### macOS/Linux setup

```bash
cd 3_Content_Engine
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python run.py inputs/ --out output/ --start-date 2026-11-02
```

## Exact commands

```powershell
# Normal deterministic run
python .\run.py .\inputs\episode_one_recording_a_week_of_content.md --out .\demo\

# Repeat: should report 20 unchanged
python .\run.py .\inputs\episode_one_recording_a_week_of_content.md --out .\demo\

# Refresh: adds only assets for the new input
python .\run.py .\inputs\ --out .\demo\

# Failure simulation, then recovery
python .\run.py .\inputs\episode_one_recording_a_week_of_content.md --out .\failure_demo\ --simulate-failure 3
python .\run.py .\inputs\episode_one_recording_a_week_of_content.md --out .\failure_demo\

# Tests
python -m unittest discover -s .\tests -v
```

Exit codes are `0` for success, `1` when one or more inputs/assets failed, and
`2` when no usable input exists. Files are written atomically; rerunning builds
only missing or changed assets. Corrupt `state.json` is quarantined.

## Optional AI mode

AI is disabled unless `--ai` is supplied. Any OpenAI-compatible endpoint can be
used; no provider package is required.

```powershell
$env:INCUBRIX_AI_API_KEY = "<paste provider key at runtime>"
$env:INCUBRIX_AI_BASE_URL = "https://your-provider.example/v1"
$env:INCUBRIX_AI_MODEL = "your-model"
python .\run.py .\inputs\ --out .\ai_demo\ --ai
```

If credentials, network, output JSON, or traceability validation fail, the run
logs the reason and uses deterministic offline copy. The provider can rewrite
hooks only; source points, IDs, claims, links, and facts remain immutable.

## Input and output

Inputs must contain at least 150 words and enough standalone sentences. Speaker
labels, SRT/VTT timestamps, and Markdown headings are handled automatically.

Output:

- `assets/<asset_id>/spec.json`: editable source and source trace
- `final.mp4`, `carousel.pdf` + slide PNGs, `final.png`, or `final.txt`
- `calendar.csv`: 23 workbook-compatible metadata fields
- `scheduler_export.csv`: engine-QA-passing assets only. The delivered final
  package intentionally keeps its official scheduler empty until human
  rights, brand, editorial, and publication approval is recorded.
- `rejects.csv`, `run.log`, `last_run.json`, and crash-safe `state.json`

UTMs include source, medium, campaign, asset ID, and pillar. X URL length is
counted as 23 characters. Unverified product features are held as Draft; a
claim is not considered verified without both `verified: true` and evidence.

## Voiceover

The renderer supports an optional `voiceover_path` in a video spec. The audio
must be original or licensed and must have an adjacent
`<audio-extension>.rights.json` file (for example `narration.wav.rights.json`)
before rendering. No music, stock imagery, or synthetic voice is bundled.

## Refresh and duplicate behavior

Asset IDs derive from the input filename and slot. Same input means unchanged
assets; edited content updates in place; new files add new IDs; missing outputs
are rebuilt. Exact hooks and near-duplicates at or above 0.86 token similarity
are removed before export.

## Configuration

- `configuration/brand.json`: colors, fonts, voice, banned phrases, CTAs
- `configuration/platforms.json`: dimensions, limits, times
- `configuration/claims.json`: claim register and human evidence
- `configuration/pillar_overrides.json`: reviewed hook-to-pillar mapping
- `configuration/asset_overrides.json`: source-backed human review corrections

## Known limitations

- Offline copy is extractive and depends on input quality.
- Videos are programmatic text/motion until a rights-documented voiceover or
  original screen recording is added.
- Visuals use a plain typographic IncuBrix name treatment, not an invented or
  unauthorized official logo. Replace it only with artwork IncuBrix supplies.
- Scheduler CSV is generic and requires field mapping in the chosen scheduler.
- Platform limits and posting-time assumptions must be rechecked before launch.
- Windows path behavior is unit-tested here, but this environment did not run
  the full render on Windows.

Inter is supplied under SIL OFL. Pillow is installed from `requirements.txt`;
FFmpeg is a system dependency and is not bundled.
