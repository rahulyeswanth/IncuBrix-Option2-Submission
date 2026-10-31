# Public account audit method

Observed 2026-10-30 16:05 UTC from logged-out public LinkedIn organization pages.
Profile follower counts came from each page's public meta description. Recent
post dates, URLs, and `LikeAction` interaction counts came from public
schema.org `SocialMediaPosting` data embedded in the same page.

`sample_interactions_avg` is the arithmetic mean of the exposed LikeAction
counts. `interaction_rate_proxy` divides that mean by followers. It is **not**
a full engagement rate because comments, shares, saves, impressions, and views
were not consistently public. Sample sizes differ because LinkedIn exposed
different numbers of posts per page. Instagram returned HTTP 429, so no
Instagram number was recorded.

Source snapshots are retained under
`6_Evidence_and_Audit/source_research_snapshots/`. Recheck before submission:
all figures are point-in-time and public page markup can change.
