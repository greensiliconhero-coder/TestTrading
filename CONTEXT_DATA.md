# Context data collection v1

Branch: `data/context-sources-v1`. All newly fetched source payloads are isolated under `data/context_sources_v1/`. The initial small public reference snapshots in `raw/` and their study subset in `review/` are explicitly versioned on this branch. Bulk authenticated minute histories remain excluded from Git. Source URLs, retrieval timestamps, SHA-256 hashes, success/failure states and row counts are versioned under `experiments/context_sources_v1/`. Nothing is automatically merged into training data.

## Collected public references

- Official NSE corporate actions for ex-dates in 2021, 2022, 2023 and 2024: 10,088 records. The local review subset contains 258 records for the 37 screened research symbols. These are action notices, not validated price-adjustment factors or a complete point-in-time information feed. The collector verifies requested ex-date years and hashes.
- Nifty Indices current constituent lists: 50 Nifty 50 records and 501 records in the supplied Nifty 500 file. The latter count is the actual provider response, not silently forced to 500. Current industry labels and membership must not be backdated into historical features.
- Kite's current NSE instrument list: 10,412 records at collection. Nine exact `INDICES` mappings resolved: NIFTY 50, BANK, IT, FMCG, AUTO, PHARMA, METAL, ENERGY and FIN SERVICE. Current identifiers do not independently prove historical identity.
- Official historical-index and corporate-action source pages for provenance. HTML pages are not historical price datasets.

Raw payload hashes permit detection of changed files. A successful HTTP response and schema check do not certify economic correctness or complete calendar coverage.

## Authenticated minute histories

Run `./Run-ContextData.ps1` in PowerShell. Enter the API key and secret only in local hidden prompts, then sign in in the browser. This uses the existing callback helper at `http://localhost:8080/`. No credentials are written to files. An already running login helper must release port 8080 before retrying.

The fixed scope is nine indices, 2021-01-01 through 2024-12-31, in 59-calendar-day chunks: 225 historical requests, plus one current instrument refresh. No 2025 price outcomes are requested. Broker historical-data entitlement is required; the tool does not purchase it. The client limits request rate and retries transient errors. It has a historical-data-only endpoint allowlist.

Each raw response is stored in `data/context_sources_v1/kite_minute/` with a content hash in its name. A request manifest is atomically checkpointed after each chunk. Nonempty, structurally accepted chunks are reused only after their stored hash matches. Index volume may legitimately be zero. Empty responses remain unverified and are retried on a later run. Invalid data stops collection and remains staged for review. The manifest records per-session minute counts and out-of-session rows without inventing a complete calendar.

After collection: verify calendar, align timestamps with stock candles, inspect coverage gaps and action dates, and independently sample-check prices. Only then propose a curated feature dataset on a separate branch.

## Still missing

- Point-in-time sector classifications and historical universe membership, including departures/delistings.
- Corporate-action factor reconciliation and security identity across changes.
- Independent historical price sample checks and verified exchange calendars.
- Historical spreads/quotes: minute OHLCV cannot recover these. Forward quote recording is a separate authenticated task, not enabled by this download.
- Additional market regimes and missing 2020 stock data: not included in this initial index-context scope.

No paid provider has been selected and no purchase is needed for the public files already downloaded. Nifty historical reports and exchange archives remain candidates for further independent checks; their existence is not a claim that full historical constituents or every required series has already been obtained.

## Reproduce public collection and review

`python src/context_sources.py` stages new snapshots and updates the public manifest. Existing content-addressed payloads are retained. Do not rerun it concurrently with the authenticated downloader because it refreshes the index-map file. `python -m unittest discover -s tests -p test_context.py` verifies chunk boundaries, date/duplicate rejection and acceptance of zero-volume index candles.

The initial public reference snapshots can be restored from this Git branch and also have a separate ZIP backup. Future bulk minute-data backups are separate from Git; copy `data/context_sources_v1/` together with its versioned manifests to restore those payloads without fetching them again. Model checkpoints and previously collected stock files are unchanged.
