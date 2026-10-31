# 30-day execution and measurement plan

The row-level schedule is `30_day_content_calendar.csv`. Targets are planning
assumptions, not results, and must be reset after the first seven days.

## Daily workflow and responsibility

| When | Owner | Action | Evidence |
|---|---|---|---|
| 09:00 UTC | Growth owner | Check due rows and approval status | Calendar status |
| 30 min pre-post | Approver | Check claim, rights, copy, link, and platform preview | Approval note |
| Scheduled slot | Growth owner | Publish and verify media/link | Public URL |
| Within 24 h | Growth owner | Reply to genuine comments; log issues | Comment log |
| 48 h after post | Growth owner | Record reach, engagement, clicks, sign-ups | Native analytics + UTM |
| Friday | Growth + approver | Review by platform/pillar/hook; keep/change/stop | Weekly decision note |

Creator/founder supplies one original voice or screen recording weekly. The
approver owns product-claim sign-off. No post with an unverified claim ships.

## Budget

Baseline is USD 0: offline engine and native scheduling. Optional test budget is
up to USD 200 in weeks 3–4, approved by IncuBrix, applied only to a proven
organic post with one variable held constant. Record spend and attributed
results; zero spend is acceptable.

## Measurement

- Reach: platform impressions/views, summed only with labels by platform.
- Engagement rate: interactions divided by impressions using a documented,
  consistent interaction definition.
- Clicks: UTM analytics grouped by `utm_content=asset_id`.
- Sign-ups: only conversions retaining UTM values; otherwise mark unavailable.
- Decision thresholds: after at least three comparable posts, keep top half by
  clicks/post, revise weak hooks, and stop formats with repeated zero signal.

Never compare unlike windows or call the LinkedIn follower-based proxy a true
engagement rate.

## Risk register

| Risk | Likelihood / impact | Owner | Mitigation | Trigger |
|---|---|---|---|---|
| Generic text-only creative | High / High | Growth | Add original voice/screen proof weekly | Two posts below baseline |
| False product claim | Medium / High | Approver | Evidence-linked claim register; Draft hold | Any unsupported feature wording |
| Rights/privacy issue | Low / High | Approver | Written rights record; no private data | Missing consent/license |
| UTM loss at sign-up | Medium / High | Analytics owner | Test conversion before launch | Click exists, attribution absent |
| Platform spec change | Medium / Medium | Growth | Monthly help-center check | Rejection/crop warning |
| Low new-account reach | High / Medium | Growth | Consistent cadence, community replies, no bought engagement | Week-1 reach below target |
| AI provider outage/unsafe rewrite | Low / Medium | Engineer | Offline default and validated fallback | Provider or traceability error |
