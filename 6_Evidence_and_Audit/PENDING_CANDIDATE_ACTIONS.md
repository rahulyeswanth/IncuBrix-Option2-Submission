# Pending candidate actions

Each item remains open until its stated evidence exists.

## 1. Attach authoritative source files

- **Do:** Add the original assessment PDF and the genuine
  `WINDOWS_FRESH_RUN_20261030.log`.
- **Why:** The assessment source and Windows evidence were referenced but absent.
- **Update:** `6_Evidence_and_Audit/`.
- **Collect:** Original files with dates/checksums.
- **Complete when:** Matrix rows can point to the actual files rather than a blocker note.

## 2. Complete signed-in product testing

- **Do:** Use the invitation account, test relevant Creator Studio functions,
  record what works/fails, and keep timestamps.
- **Why:** Public website observations are not product-use evidence.
- **Update:** Workbook `01_INSIGHT` and
  `3_Content_Engine/configuration/claims.json`.
- **Collect:** Dated screenshots and product walkthrough timestamps.
- **Complete when:** Every product claim marked verified has direct evidence.

## 3. Recheck social and competitor metrics

- **Do:** Open IncuBrix’s active channels and the five peer pages on submission
  day; confirm account identity and visible numbers.
- **Why:** Social figures are point-in-time; Instagram was unavailable.
- **Update:** `4_Launch_Kit/account_audit_COMPLETED.csv`.
- **Collect:** Profile URLs, observation time, screenshots, sample post URLs,
  and visible metrics. Write `unavailable`, never zero, when hidden.
- **Complete when:** Every audited row has dated evidence or an explicit
  unavailable explanation.

## 4. Perform final editorial, brand, and rights review

- **Do:** Review all 40 assets, confirm the typographic name treatment is
  acceptable, and replace it only with authorized IncuBrix artwork.
- **Why:** Machine inspection cannot grant brand authorization or publication rights.
- **Update:** `6_Evidence_and_Audit/ASSET_QA_REPORT.csv`,
  `2_Final_Content/calendar.csv`, workbook `02_ASSETS`, and
  `2_Final_Content/scheduler_export.csv`.
- **Collect:** Candidate signoff and any supplied logo/license file.
- **Complete when:** Each approved asset has evidence, its status is changed
  from `Pending human approval` to `Ready`, and only approved rows are copied
  from `scheduler_export_DRAFT_FOR_REVIEW.csv` into `scheduler_export.csv`.

## 5. Run the real-audience requirement

- **Do:** Either collect genuine responses from at least 20 eligible target
  participants using `5_Audience_Test/`, or publish at least 10 assets across
  at least five days on candidate-owned accounts.
- **Why:** This is a minimum assessment requirement.
- **Update:** `5_Audience_Test/results/`, workbook self-check, and asset URLs/metrics.
- **Collect:** Anonymous response CSV or real post URLs and native analytics.
- **Complete when:** Validation passes with genuine data and the method is documented.

## 6. Fill candidate and submission fields

- **Do:** Enter candidate ID, name, registered email, college/degree, start and
  submission times, personal tool costs, repository/folder/video URLs, and declaration.
- **Why:** These values cannot be inferred.
- **Update:** Workbook `00_START`.
- **Collect:** Final URLs and truthful cost/manual-work notes.
- **Complete when:** All yellow identity/link fields and checklist items are accurate.

## 7. Record both unedited demos

- **Do:** Personally record the product walkthrough (≤5 min) and technical demo
  (≤8 min) using `7_Demo_Guides/`.
- **Why:** Scripts are not recordings and product use must be personal.
- **Update:** Workbook video URL fields.
- **Collect:** Viewable unedited video links with correct permissions.
- **Complete when:** Both links open for a reviewer and durations comply.

## 8. Create private repository and reviewer access

- **Do:** Create/select a private remote, review files for privacy, push, and
  grant the required reviewer access.
- **Why:** No remote URL or authorization was supplied.
- **Update:** Workbook repository URL.
- **Collect:** Private repository URL and tested reviewer access.
- **Complete when:** Reviewer can clone without exposing secrets publicly.

## 9. Upload and submit

- **Do:** Upload this final folder, test cloud permissions, add video links,
  verify workbook formulas in Excel, and submit the official Google Form.
- **Why:** Local files are not a completed submission.
- **Update:** Workbook links and `FINAL_SUBMISSION_CHECKLIST.md`.
- **Collect:** Shared folder URL and submission confirmation.
- **Complete when:** All links work in a signed-out/reviewer context and the
  official form confirms receipt.
