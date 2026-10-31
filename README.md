# IncuBrix 2027 Growth Engineer — Option 2 Final Submission

This evidence-first package contains 40 social assets, a reproducible content
engine, a 30-day launch kit, an audience-test framework, workbook, audits, and
demo guides. It does not claim product use, audience results, publications, or
recordings that have not occurred.

Start with `FINAL_SUBMISSION_CHECKLIST.md` and
`6_Evidence_and_Audit/requirement_matrix.csv`.

## Structure

- `1_Submission_Workbook/` — final workbook with preserved formulas and a new
  `05_DISCLOSURE` sheet.
- `2_Final_Content/` — final media, editable JSON sources, calendar, a
  40-row scheduler draft, and an approval-gated official scheduler export.
- `3_Content_Engine/` — Python source, configuration, tests, inputs, and tools.
- `4_Launch_Kit/` — standalone DOCX/Markdown kit, calendar, and account audit.
- `5_Audience_Test/` — protocol, randomized assignments, empty results template,
  validator, and report template.
- `6_Evidence_and_Audit/` — requirement matrix, QA, test evidence, correction
  history, disclosure, blockers, and candidate actions.
- `7_Demo_Guides/` — product and technical recording scripts.

## Architecture

`extract.py` cleans Markdown/transcript text and extracts source-backed hooks and
points. `pipeline.py` assigns formats/platforms, applies reviewed overrides,
builds captions/CTAs/UTMs, runs claim and platform gates, deduplicates, persists
state atomically, and exports CSVs. `render.py` creates PNG, PDF, and MP4 media
with Pillow/FFmpeg. `ai.py` optionally rewrites hooks through an
OpenAI-compatible endpoint, accepting only source-traceable results.
`security.py` scans first-party files while excluding dependencies and caches.

## Prerequisites

- Python 3.9+
- FFmpeg with `libx264` on `PATH`
- Internet/API access is not required for deterministic offline mode

## Windows PowerShell installation

```powershell
cd .\3_Content_Engine
py -3 -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r .\requirements.txt
ffmpeg -version
```

## Exact execution commands

```powershell
# Tests
python -m unittest discover -s .\tests -v

# One long input -> 20 assets
python .\run.py .\inputs\episode_one_recording_a_week_of_content.md `
  --out .\output\ `
  --start-date 2026-11-02

# Two inputs -> 40 assets
python .\run.py .\inputs\ `
  --out .\output\ `
  --start-date 2026-11-02

# Simulated failure and recovery
python .\run.py .\inputs\episode_one_recording_a_week_of_content.md `
  --out .\failure_demo\ `
  --simulate-failure 3

python .\run.py .\inputs\episode_one_recording_a_week_of_content.md `
  --out .\failure_demo\
```

Inputs may be `.md`, `.txt`, `.srt`, or `.vtt`, must contain at least 150
words, and should contain enough standalone source sentences.

## Outputs

Each `output/assets/<asset_id>/` contains editable `spec.json` plus MP4, PNG,
PDF/slide PNGs, or TXT. The output root contains `calendar.csv`,
`scheduler_export.csv`, `rejects.csv`, `run.log`, `last_run.json`, and
crash-safe `state.json`.

## Refresh, duplicates, and recovery

- Same input and filename: unchanged assets are skipped.
- Edited content with same filename: affected slots update in place.
- New input: new stable IDs are added.
- Exact and ≥0.86 token-similarity hooks are rejected as duplicates.
- Missing media is rebuilt.
- Partial writes use `.part` then atomic rename.
- One failed render is logged without stopping other assets; rerun builds only
  the missing asset.
- Corrupt state is quarantined.

## AI and offline modes

Offline mode is the default, deterministic, network-free mode. The candidate-
reported Windows fresh run used `deterministic_offline`; no model
transformation is claimed for it.

Optional AI mode requires all three environment variables and `--ai`:

```powershell
$env:INCUBRIX_AI_API_KEY = "<paste provider key at runtime>"
$env:INCUBRIX_AI_BASE_URL = "https://provider.example/v1"
$env:INCUBRIX_AI_MODEL = "provider-model"
python .\run.py .\inputs\ --out .\ai_output\ --ai
```

Missing credentials, provider failure, invalid JSON, unsafe numbers, or failed
source trace cause a logged deterministic fallback. No keys are stored here.

## Branding, media, and rights

The final visuals use a plain typographic IncuBrix name treatment; they do not
invent or claim an official logo. Replace it only with authorized artwork.
Media is programmatic and uses bundled Inter under SIL OFL. No external stock
image, music, face, or voice is bundled. Optional voiceover requires an adjacent
rights JSON file. Candidate human rights/brand approval remains required.

## Verified results in this workspace

- Corrected-package engine suite: 35 tests passed in 0.661 seconds, exit 0.
- Fresh final single-input run: 20 assets in 0.78 minutes; refresh added the
  second input's 20 assets in 0.73 minutes.
- Final validator: 40 technically complete assets, 40 calendar rows, 40 draft
  scheduler rows, 0 approved rows in the official scheduler, 40 machine-QA
  passes, 5 platforms, no duplicate/near-duplicate hooks, max video 34.067 s.
- Workbook: six sheets, 316 formulas, 15 data validations, two conditional-
  formatting blocks, and no corrupt package member.
- Random sample seed 20261030: initial 16/20; four preserved corrections; same
  sample after correction 20/20.
- Full typographic-brand rerender: 16 videos, 8 carousels, and 8 graphics in
  89.94 seconds.

Candidate-reported Windows results are separately disclosed and remain
partially evidenced because the original referenced log was not supplied.

## Known limitations

- Original assessment PDF and separately updated workbook were not present in
  the supplied workspace; the current upgraded workbook was used as source.
- Signed-in product behavior is unverified.
- Instagram account metrics were rate-limited; unavailable values are not zero.
- Competitor interaction proxies are limited public LikeAction samples, not
  complete engagement rates.
- All 40 assets remain `Pending human approval`; technical QA is not
  publication approval. `scheduler_export_DRAFT_FOR_REVIEW.csv` preserves the
  proposed schedule, while `scheduler_export.csv` has headers only.
- Real audience test/publication, demo recordings, final editorial/rights
  signoff, repository remote, and sharing links remain candidate actions.
- Text-motion videos benefit from future original screen/voice footage.
- Generic scheduler CSV may require field mapping in the selected platform.

## Contribution disclosure

This is AI-assisted, not accurately described as entirely AI-generated. Claude
assisted code, debugging, drafting, strategy, test design, workbook preparation,
and QA recommendations. Candidate-directed and candidate-reported activities,
agent-executed local checks, and pending human work are separated in
`6_Evidence_and_Audit/AI_MANUAL_DISCLOSURE.md` and workbook `05_DISCLOSURE`.

## Private Git repository

Do not push without candidate authorization. After reviewing files:

```powershell
git init
git add .
git commit -m "Finalize IncuBrix Option 2 submission"
gh repo create incubrix-option2-assessment --private --source . --remote origin
git push -u origin main
```

Grant reviewer access privately and test permissions. Never commit local
credentials, private participant data, or unredacted product/account recordings.
