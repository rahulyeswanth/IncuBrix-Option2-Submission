# Final test summary

Only executed checks are reported as passed.

## Automated suite

- Command: `python -m unittest discover -s tests -v`
- Location: final relocated `3_Content_Engine`
- Result: **35 tests passed**
- Corrected-package suite time: **0.661 seconds**
- Exit: **0**
- Evidence: `CORRECTED_FINAL_UNIT_TESTS.txt`

Coverage includes input validation, SRT cleanup, Windows-style filenames,
minimum generation, stable IDs, exact/near duplicate prevention, reviewed
overrides, repeat, refresh, corrupt state quarantine, deleted-output rebuild,
failure isolation/recovery, scheduler filtering, complete UTM validation,
product-claim holds, caption/hashtag limits, video limit, real graphic render,
carousel bounds, optional-AI fallback/traceability, and scoped secret scanning.

## Fresh single input, repeat, and new-input refresh

Evidence: `FINAL_NORMAL_REPEAT_REFRESH.txt`

- Fresh 716-word input: 20 planned, **20 created**, 0 rejected/held/errors,
  20 calendar rows, deterministic offline, **0.78 minutes**, exit 0.
- Immediate repeat: 0 created, **20 unchanged**, 0 errors, exit 0.
- New-input refresh: 40 planned, **20 created + 20 unchanged**, 0
  rejected/held/errors, 40 calendar rows, deterministic offline,
  **0.73 minutes**, exit 0.

Direct offline engine/API cost: USD 0.

## Failure and recovery

Evidence: `FINAL_FAILURE_RECOVERY.txt`

- Simulated third-render failure: 19 created, 1 render error, 19 calendar rows,
  **0.71 minutes**, expected exit 1.
- Recovery rerun: missing 1 created, 19 unchanged, 0 errors, 20 calendar rows,
  **0.07 minutes**, exit 0.

## Final submission validator

Evidence: `FINAL_VALIDATION.json` and `ASSET_QA_REPORT.csv`

- 40 asset folders and 40 unique IDs
- 40 calendar rows, 40 draft scheduler rows, and 0 approved rows in the
  official scheduler export
- 16 videos, 8 carousels, 8 graphics, 8 text posts
- Five platforms
- Maximum video duration: 34.067 seconds
- 40/40 machine/source/claim/path checks passed; human publication approval
  remains pending for all 40
- 0 exact or near-duplicate hook pairs
- All final media and editable-source paths exist
- All UTMs and timestamps valid
- All hooks/points trace to original source input
- No technically complete asset has a claim hold
- Workbook: six sheets, 316 formulas, 15 data validations, two
  conditional-formatting blocks, no corrupt ZIP member
- Launch DOCX: no corrupt ZIP member

## Random audit

- Fixed seed: 20261030
- Initial: **16/20 (80%)**
- Four original failures preserved and corrected
- Same sample after correction: **20/20 technical/content pass (100%)**;
  publication approval remains pending

## Branding rerender

- 16 videos, 8 carousels, and 8 graphics rerendered after removing the invented
  placeholder icon.
- Runtime: **89.94 seconds**
- Text posts were not unnecessarily regenerated.

## Concurrent diagnostic

Two real-media pipelines were briefly started concurrently and produced FFmpeg
pipe closures under resource contention. They were cancelled and are not
counted as passes. The diagnostic is retained in
`CONCURRENT_RENDER_DIAGNOSTIC.txt`; all reported execution checks above were
rerun sequentially and passed as stated.

## Candidate-reported Windows test

The candidate separately reports Python 3.14.7, 34 tests, 40 assets from two
inputs in 4.42 minutes, zero errors/rejections, valid paths/timestamps/URLs, and
five platforms in deterministic offline mode. The original referenced Windows
log was absent, so this is **partially evidenced** and not merged with the local
results above.
