# Real-audience preference test protocol — NOT YET RUN

No responses or results are included. Run this only with at least 20 genuine
members of the target audience.

## Eligibility and consent

Eligible participants currently publish, edit, manage, or approve podcasts,
YouTube videos, or expert-led creator content at least monthly. Participants
must be 18+, able to review English-language content, and must not be the
candidate or an IncuBrix employee.

Read before starting:

> You are invited to a short content preference study for a hiring assessment.
> Participation is voluntary and takes about 8 minutes. You will compare five
> pairs of social posts. We collect a participant code, broad role, primary
> platform, and your answers; we do not need your name, email, or account
> handle. Your anonymous answers will be analyzed in aggregate. You may stop at
> any time or skip an optional free-text question. There is no sales contact and
> no reward tied to your answers. By selecting “I consent,” you confirm that you
> are 18+, meet the eligibility rule, and agree to this use.

Record `consent=Yes` and `eligible=Yes`; exclude all other rows before analysis.

## Materials and randomization

`pair_definitions.csv` fixes five comparisons and the hypothesis for each.
Create reproducible presentation order:

```powershell
python .\randomize_assignments.py --participants 20 --seed 20261102 --out .\assignments.csv
```

The script assigns each participant all five pairs in a randomized pair order
and randomizes whether canonical asset A or B appears first. The collector must
show media/copy from `2_Final_Content/assets/<asset_id>` and must not reveal the
hypothesis. Do not alter the assets midway through data collection.

## Survey questions

Ask once: consent, eligibility screen, role, primary platform, publishing
frequency. For each pair:

1. Which would make you stop in your feed? A / B / Neither
2. Which is clearer? A / B / Same
3. Which is more useful? A / B / Same
4. How likely are you to save or share your preferred option? 1–5
5. Why? (optional, one sentence)

Ask once at the end:

6. Would you try a tool that helps produce content like this? Yes / Maybe / No
7. What would make the content more credible or useful? (optional)

Use participant IDs such as P01; never collect names or contact details in the
results CSV. Enter one row per participant per pair using
`results_TEMPLATE.csv`.

## Analysis

```powershell
python .\analyze_test.py .\results.csv --report .\results_report.md
```

The script checks consent, eligibility, duplicate participant/pair rows,
coverage, allowed answers, and the 20-person threshold. It reports preference
shares and Wilson 95% intervals. With 20 people, results are directional, not
proof. Do not claim a benchmark win unless the same metric and a dated source
are documented.

Alternative: publish at least 10 assets across at least 5 days on accounts you
own, retain URLs and native analytics after a consistent observation window,
and report every result including weak outcomes.
