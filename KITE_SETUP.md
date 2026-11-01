# Kite pilot: ready for local authentication

This workflow is a diagnostic download, not a trading bot. It has no order endpoints and does not modify the source CSVs. Standard-library Python handles the downloader; no additional packages are required beyond the existing audit dependencies.

## First batch

The generated `config/repair_plan.json` contains 32 historical requests: paired minute/day responses for 16 stock-sessions. It covers all seven 25 June 2024 opening-candle inconsistencies, representative zero-price sessions, two overlap controls, and three 2020 probes. It is not a complete backfill. Requests are explicit dates and capped at 50 per plan.

7,862 rows labelled HDFCLIFE before its 17 November 2017 listing are excluded from requests. Original files remain untouched. The listing-date guard currently covers HDFCLIFE only; it is not a complete security master. Other historical identities, corporate-action adjustments and exchange calendars still require verification.

## Preview without credentials or network

From `C:/Users/mayan/Documents/Codex/TradingResearch`:

```powershell
python src/kite_repair.py fetch
```

Regenerate the pilot from the audited issues with `python src/kite_repair.py plan`.

## When historical API access is active

### Recommended: browser login using API key and secret

Run `.\Run-KitePilot.ps1 -Login`. It prompts for API key and API secret with hidden input, opens the official Kite login, and waits for the callback on `http://localhost:8080/`. This must match the app's configured Redirect URL. Sign in yourself in the browser. The helper exchanges the request token for an access token and runs the pilot in the same process. Credentials and access tokens are not written to files. Callback state is checked, callback URLs are not logged, and the local listener times out after five minutes. Port 8080 must be free.

### Alternative: existing access token

Obtain a fresh access token through the normal Kite login flow or your existing local login helper. The downloader needs the API key and access token, not the account password, TOTP seed or API secret. Do not paste credentials into chat or save them in project files. Kite sessions expire daily; the downloader stops on authentication failure rather than disguising it as missing data.

Run:

```powershell
.\Run-KitePilot.ps1 -Execute
```

The `-Execute` launcher prompts for an API key and existing ACCESS TOKEN, not an API secret. It passes them only through process environment variables and clears credentials it created when finished. Existing process credentials are left unchanged. If you use a virtual environment, specify `-Python '.\.venv\Scripts\python.exe'`. Without `-Execute` or `-Login`, the command is a dry-run. If execution policy blocks a local script, use the documented Python commands from an authenticated local shell; do not change machine-wide policy just for this tool.

Equivalent commands after local environment variables are configured:

```powershell
python src/kite_repair.py instruments --execute
python src/kite_repair.py fetch --execute
python src/compare_downloads.py
```

## Storage and recovery

- `work/kite/instruments/`: immutable, checksummed instrument snapshots. A current snapshot identifies the request but does not prove historical identity.
- `work/kite/chunks/`: raw successful JSON responses and per-request manifests. Request metadata includes token, company name when supplied, explicit bounds, OI setting, snapshot checksum, response checksum and retrieval time.
- `work/kite/latest_run.json`: completed request records and current run status.
- `outputs/repair/`: old/new comparison tables. A value change is evidence for investigation, not proof that the new value is correct.

Files are written through a temporary file and atomic replacement. A clean-shape response can resume only when the request, snapshot, validator version and checksum match and validation still passes. `downloaded_unverified` does **not** mean calendar-complete, adjustment-consistent or approved for modelling. Short sessions remain visible through row counts and the regular-minute diagnostic.

`empty_unverified`, `quarantined` and `failed` are separate states and are not silently accepted as complete. Re-running fetch retries these requests. If an interruption leaves an `active.lock`, ensure no downloader is running before removing that individual stale lock. Retain the same snapshot to resume the same batch; retrieving a different snapshot creates distinct request identities. Avoid simultaneous runs using the same work directory.

Requests are paced at least 0.4 seconds apart. Network failures, HTTP 429 and selected 5xx responses retry up to three attempts. Authentication and other permanent HTTP errors are not retried. Redirects and endpoints outside the data-only allowlist are refused. Failed requests return a nonzero command status.

No response is merged automatically. Before a broad backfill, inspect comparisons, establish listing dates and calendars, confirm provider adjustment conventions, and decide whether a stock requires a consistent full-history refresh instead of a small patch.

## Validation status and sources

Offline tests exercise retries, expired authentication, empty and malformed responses, duplicate/invalid candles, checksum-based resumption, source preservation, listing guards and comparisons. Live authentication and data quality remain untested until access is available.

- Historical API: https://kite.trade/docs/connect/v3/historical/
- Errors and rate limits: https://kite.trade/docs/connect/v3/exceptions/
- Instruments: https://kite.trade/docs/connect/v3/market-quotes/
- Authentication: https://kite.trade/docs/connect/v3/user/
- HDFC listing disclosure: https://www.hdfc.com/content/dam/housingdevelopmentfinancecorp/pdf/investors/services/qualified-institutions-placement/qualified-instiutions-placement-2018/project_tragopan_Final_Placement_Document_March_5_2018_0.pdf
