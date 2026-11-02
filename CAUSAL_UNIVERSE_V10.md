# Causal universe reconstruction v10 — frozen protocol

Purpose: replace the current-survivor list and future-action exclusions with date-local candidates. This is a data/accounting milestone, not a new profitability backtest.

Use all 1,240 saved official NSE archives for 2021–2025. Keep exchange EQ rows with INE-prefixed ISINs (an explicit instrument filter, not a certified ordinary-share classification). Validate dates, identity, OHLCV and traded value. Do not impute invalid rows; preserve issues. Track by ISIN, keep that day's trading symbol, and require 61 consecutive valid sessions ending on the signal date. Rank by the trailing 20-session mean reported traded value, descending, ISIN tie-break; take at most 36. Signal schedule: every five official sessions starting at index60. Decisions require no future price or corporate-action input. Orders, if later simulated, would execute no earlier than the next session.

Never remove candidates because a later dividend, bonus, rights issue, delisting or missing execution price makes evaluation inconvenient. Keep missing future coverage and actions as explicit unresolved obligations in a separate audit. Identity changes from splits can restart the 61-session history: this is a past-data eligibility rule, not future screening. Preserve the resulting conservatism.

Audit proposed next-open through five-session-later-open windows against all-market corporate-action records, by available ISIN identity with symbol fallback. Missing announcements do not justify future exclusion. Raw ex-date records and parsed factors/amounts are evidence candidates, not automatically verified entitlements or payment/credit dates. Bonus shares may be economic entitlements before they are tradable; future execution must distinguish them. No live account simulation or model selection until relevant action handling is resolved.

This does not claim complete point-in-time exchange metadata, exhaustive action coverage, or historical index membership. Calendar comes from the saved official index calendar; EQ/INE filtering and 61-session warmup can omit other securities. No paid data, API authentication or GPU is required for this phase.
