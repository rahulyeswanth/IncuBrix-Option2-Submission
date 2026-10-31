# Reproducible random 20-asset audit

- Population: 40 delivered assets
- Sampling algorithm: `random.Random(20261030).sample(sorted(asset_ids), 20)`
- Seed fixed before review: `20261030`
- Initial result: **16/20 passed (80%)**, below the 85% threshold.
- Failed IDs: `EORC57-C03`, `EORC57-V06`, `EORC57-C04`, `EORC57-G02`.
- Original failed assets are preserved under `asset_correction_history/originals/` with hashes.
- Corrections use only verbatim source-input sentences and are persisted in `configuration/asset_overrides.json`.
- Second technical audit of the unchanged sample after corrections:
  **20/20 passed (100%)**.

The first result was not discarded or resampled. These are technical/content
audit results, not publication approvals. Rights checks verify file composition
and documented font licensing; candidate authorization of brand treatment,
editorial copy, accounts, and final publication rights remains pending for all
40 assets.
