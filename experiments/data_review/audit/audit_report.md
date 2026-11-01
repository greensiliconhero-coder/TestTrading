# Trading data audit

Read-only scan; original data was not modified. No model has been trained and no trading performance is claimed.

## Daily

- files: 490
- symbols: 49
- rows: 116710
- empty_files: 4
- error_files: 0
- invalid_timestamps: 0
- timestamps_without_offset: 0
- duplicate_timestamps: 0
- out_of_order_steps: 0
- invalid_numeric_rows: 0
- nonpositive_price_rows: 0
- invalid_ohlc_rows: 0
- negative_volume_rows: 0
- zero_volume_rows: 5
- outside_regular_session_rows: 0
- sessions_short_of_375_reference: 0
- first_day: 2015-01-01
- last_day: 2025-10-03

## Minute

- files: 374
- symbols: 49
- rows: 32729261
- empty_files: 2
- error_files: 0
- invalid_timestamps: 0
- timestamps_without_offset: 0
- duplicate_timestamps: 0
- out_of_order_steps: 0
- invalid_numeric_rows: 0
- nonpositive_price_rows: 16864
- invalid_ohlc_rows: 7
- negative_volume_rows: 0
- zero_volume_rows: 76137
- outside_regular_session_rows: 21423
- sessions_short_of_375_reference: 1129
- first_day: 2015-02-02
- last_day: 2025-10-03

## Cross-frequency comparison

- matched_symbol_days: 87516
- daily_only_days: 29192
- minute_only_days: 122
- open_different_days: 18901
- high_different_days: 22159
- low_different_days: 24211
- close_different_days: 84318
- volume_different_days: 87503

## Files requiring attention

- daily: HDFCLIFE_2015.csv (empty)
- daily: HDFCLIFE_2016.csv (empty)
- daily: SBILIFE_2015.csv (empty)
- daily: SBILIFE_2016.csv (empty)
- minute: CIPLA_2015.csv (empty)
- minute: HDFCLIFE_2016.csv (empty)

## Interpretation and remaining work

- This is a structural audit, not validation against an independent market-data vendor.
- The 375-minute reference assumes 09:15 through 15:29 IST, minute-start labels, and normal cash sessions. Special sessions, trading halts and intervals without trades can differ. No exchange calendar has been applied.
- Session aggregates are diagnostic only. They include source rows, even when flagged; they are not cleaned model inputs. Duplicate rows can inflate aggregate volume.
- Daily close can differ from the final minute close due to official closing-price methodology. Auctions and vendor conventions can also affect comparisons; disagreement alone does not establish corruption.
- Confirm source, timestamp conventions, minute-volume semantics and corporate-action adjustment policy before modelling.
- Symbol names are inferred from filenames and require verification against instrument identifiers. Historical index membership and delisted securities have not been established.
- Entire missing trading days require a verified exchange calendar and instrument listing history to diagnose.
- Missing OI is not a blocker for cash-equity research.
- Do not select a model or trading horizon using the final held-out evaluation period.

Detailed evidence: file_audit.csv, daily_sessions.csv, minute_sessions.csv, daily_minute_comparison.csv, summary.json.
