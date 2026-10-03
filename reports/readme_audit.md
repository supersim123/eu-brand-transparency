# README Audit

- Generated at: `2026-10-03T09:46:05.650023+00:00`
- Decision: **PASS**
- Summary: The tables are well formed and the current-owner claims reviewed are supported by the supplied evidence. A few missing flags and lengthy owner labels could be cleaned up; these are non-blocking.
- Reason: The issues are minor presentation improvements and do not make the README unsafe to publish automatically.

## Issues

- **warning / missing_flag** at `Other table: Auchan Hungary and Habitat rows`
  Problem: The country names "Hungary" and "France operations" appear without their flags, unlike the other country labels in the tables.
  Suggestion: Add 🇭🇺 before Hungary and 🇫🇷 before France.
- **warning / missing_flag** at `Other table: Depop, Layla, and CarTrawler rows`
  Problem: The owner cells for eBay Inc. and Expedia Group omit flags, while the README uses flags for other clearly US-based owners.
  Suggestion: Add 🇺🇸 before eBay Inc. and Expedia Group for consistency.
- **warning / long_name** at `Other table: Huel and Cocoli.com rows`
  Problem: The owner labels "Danone Holdings (UK) Limited / Danone S.A." and "The Platform Group SE & Co. KGaA" are lengthy legal names that make the owner column harder to scan.
  Suggestion: Use shorter display names such as "Danone" and "The Platform Group," retaining the legal names in the source records if needed.
