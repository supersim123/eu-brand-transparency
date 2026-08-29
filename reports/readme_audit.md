# README Audit

- Generated at: `2026-08-29T10:55:53.678706+00:00`
- Decision: **PASS**
- Summary: The README is mostly well-formed and source-backed. A few rows have missing country flags where a single clear owner or origin country is shown, and one row has an unusually long brand label that hurts table readability. These are minor README/data cleanup issues and do not block publishing.
- Reason: Markdown tables and source evidence are acceptable; identified issues are non-blocking formatting/readability fixes.

## Issues

- **warning / missing_flag** at `Other table, Auchan Hungary row`
  Problem: The 'Founded in' cell shows 'Hungary' without the Hungarian flag, and the 'Current owner' cell shows 'Indotek Group' without a country flag, while the source indicates a clear Hungarian owner/context.
  Suggestion: Use flags consistently, e.g. '🇭🇺 Hungary' and '🇭🇺 Indotek Group'.
- **warning / missing_flag** at `Other table, Depop row`
  Problem: The 'Current owner' cell shows 'eBay Inc.' without the US flag, while other US owners are flagged consistently.
  Suggestion: Change the owner cell to '🇺🇸 eBay Inc.'.
- **warning / missing_flag** at `Other table, Tendam row`
  Problem: The 'Current owner' cell shows 'Multiply Group' without a country flag, while the source identifies the acquirer and other rows use flags for clear owner countries.
  Suggestion: Add the appropriate owner-country flag if the dataset has a single clear country for Multiply Group.
- **warning / long_name** at `Other table, Recharge row`
  Problem: The brand label 'Recharge / Recharge.com / Startselect.com' is long and makes the table harder to scan.
  Suggestion: Consider shortening the display brand to 'Recharge' or 'Recharge.com' and keep related storefronts in the underlying data or notes.
