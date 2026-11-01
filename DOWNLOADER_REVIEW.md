# Existing downloader review

Source confirmed by the owner: Kite historical API.

Reviewed read-only: `C:/Users/mayan/IdeaProjects/Zerodha_Trading/minute_data_fetcher.py` and the `get_historical_data` method in `zerodha_connection.py`. Neither module was imported or executed; no credentials or network calls were used.

## Findings

1. **Failed requests become indistinguishable from valid empty responses.** The connection wrapper returns `None` on failure. `fetch_chunk_with_retries`, lines 128–140, immediately returns `data or []`; the outer three-attempt loop therefore does not retry failures swallowed by the wrapper. The wrapper does attempt its own retry, but persistent failure is still reported to the fetcher as empty data.
2. **Partial years are treated as complete.** `fetch_symbol_year`, lines 176–187, continues after empty/failed chunks. The resulting partial list is saved. `file_has_nonempty_rows`, lines 56–67, and the resume checks at lines 147–154 and 227–231 treat any file with more than one line as complete. A rerun can therefore skip a partial year indefinitely.
3. **No durable chunk manifest.** CSV files do not record requested intervals, request failures, confirmed empty intervals, download time, instrument token, or completeness. Those states cannot be reconstructed from the CSV alone.
4. **Universe is a fixed list of 49 symbols.** The variable is named NIFTY50_SYMBOLS, but contains 49 entries. It is not historical index membership. `build_token_map` resolves a current NSE instrument list, and the CSV does not retain that mapping. Backtests must not describe this as the historical NIFTY 50 universe.
5. **Year selection depends on the execution date.** `years_window` excludes the current year and applies `skip_recent` relative to that date. Explicit start/end dates and a saved request manifest would be easier to reproduce. The observed missing 2020 files cannot be conclusively attributed to this function without historical invocation logs.
6. **Writes are not atomic.** `save_year_csv` writes directly to the final filename. An interruption can leave a truncated file, which the nonempty resume rule may accept as complete.

## Repair design for the separate research project

- Keep successful-empty, successful-with-data, and failed requests as distinct states.
- Retry transient failures only; surface authentication and permanent failures clearly.
- Record explicit date ranges, instrument identity, requested interval and per-chunk completion status.
- Save each validated chunk atomically; resume only verified complete chunks.
- Validate timestamps and conflicting duplicates before merging chunks.
- Write repairs to a new derived location, compare against the original, and preserve provenance.
- Establish listing history and a trading calendar before deciding whether a missing interval should contain observations.

No download repairs have been executed. This review identifies plausible mechanisms for gaps, not proof that each observed gap was caused by these defects. Provider adjustment conventions remain unverified.
