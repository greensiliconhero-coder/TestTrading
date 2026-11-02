# NSE raw-price reconciliation v8 — completed

Saved 1,240 official NSE daily archives (2021–2025), 139,499,534 bytes. Selected panel: 47,120 rows, no invalid selected rows, zero unmatched comparison records. Nine of nine split/bonus ratio changes agree within 0.2%. All 301 dividend descriptions produce amount review candidates; payment dates remain unverified. A 2026 Kotak Bank split explains its fivefold historical price-unit difference. These checks do not certify every corporate action.

## Frozen-score net-position replay

No model retraining or strategy reselection. Same v5 survivor universe and retrospectively screened action-free sample windows. INR50,000, INR10,000 ranked-position cap, whole shares, current counterfactual fees, 5bps slippage each side, one-session settlement delay. Retain unchanged quantities; trade only net changes. Period returns, not annualized: 2024 Jan5–Dec24 and 2025 Jan8–Dec26.

| Candidate | 2024 validation | 2025 development |
|---|---:|---:|
| NIFTYBEES | 10.17% | 11.45% |
| equal_weight | -2.00% | 0.30% |
| momentum20 | 8.20% | -4.89% |
| reversal5 | -7.17% | -3.06% |
| ridge | -1.20% | 7.33% |
| tree | -7.30% | 3.17% |

No active candidate beats the ETF in both periods under the primary assumptions. Original selected strategy remains cash. Zero-delay and 10bps sensitivity results are preserved in raw_execution_results.json; they must not be chosen after seeing performance.

## Paired source control

raw_gross_control.json keeps the previous gross-roundtrip accounting and frozen scores, changing only execution prices to official raw prices. paired_sample_comparison.csv.gz preserves all 4,444 samples. 231 targets differ by more than 5bps, maximum 60.676bps, one return sign changes. Largest differences include BPCL and TATASTEEL. Exact attribution of every source difference remains unresolved; do not attribute all changes solely to whole-share rounding. The next controlled refit will replace inputs and targets while keeping model definitions and sample keys fixed.

## Constraints and reproducibility

2025 is already observed development data. Survivor selection and retrospective corporate-action exclusions remain; current fees and simplified settlement are not historical certification. Observed-open sizing is an approximation. Dividend payment accounting and rights/demergers remain unresolved. ETF is a market-price proxy, not certified total return. The market deployment gate remains closed.

Run src/nse_raw_v8.py, src/nse_reconcile_v8.py, src/raw_execution_v8.py; completed evaluations refuse overwrite. Full suite: 70 tests passed, including exchange format/date validation, split parsing, retained positions, cash settlement, atomic failures and planted/null learning controls. Exact request URLs and SHA256 values are in experiments/nse_raw_v8/manifest.json. See NSE_RAW_V8.md for protocol and config/raw_execution_v8.json for frozen assumptions.


---

# Backtest validation v7

Branch: `research/backtest-validation-v7`. Engineering validation completed; market-data gate FAILED. No new market strategy was trained or promoted.

## What changed

Added a stateful research ledger that retains unchanged positions and trades net quantity differences, reserves buy fees, prevents borrowing, delays spendable sale proceeds by a configurable session lag, and accounts for verified dividends as receivables until their payment session. Split/bonus unit changes preserve wealth on raw-price synthetic fixtures. Missing evidence, unsupported rights/demergers, ambiguous fractional entitlements, adjusted execution-price basis and missing held-asset marks fail closed. Rejected steps are atomic. Dividend/other cashflow taxes, fractional cash-in-lieu, exchange/broker settlement nuances and intraday actions remain outside supported scope.

Tests: 64 existing/regression tests passed before adding the explicit market gate test; all 13 ledger tests passed after that addition. Known-payoff, retained-position, net-rebalance, settlement, split/bonus conservation, dividend timing, same-bar signal rejection and split-boundary label purge were checked.

## Synthetic learning controls

20 paired fixed seeds, 6,000 samples per control; 3,599 training and 1,199 validation after one-step boundary purging, 1,200 held-out synthetic test samples. Unchanged Ridge and histogram-tree regressors; validation threshold selection followed by test evaluation, 20 bps cost. 80 fitted estimators and exact input/prediction arrays preserved.

| Control/model | Mean test correlation | Validation-selected runs | Positive selected test runs |
|---|---:|---:|---:|
| null_ridge | -0.0032 | 0/20 | 0/20 |
| null_tree | 0.0035 | 6/20 | 2/20 |
| planted_ridge | 0.8947 | 20/20 | 20/20 |
| planted_tree | 0.8887 | 20/20 | 20/20 |

All predefined engineering acceptance checks passed. Positive control learners recovered the deliberately strong linear signal. Null-tree controls still produced positive selected test means in 2/20 runs: random apparent winners remain possible. Correlation is not prediction accuracy, and these tests do not establish market profitability, exhaustive leakage detection or validity of real-world execution assumptions.

## Confirmed historical price-basis problem

| Symbol/date | NSE traded close | Saved Kite close | NSE/Kite ratio |
|---|---:|---:|---:|
| TATASTEEL 2022-07-27 | 959.40 | 90.25 | 10.6305 |
| TATASTEEL 2022-07-28 | 100.35 | 94.55 | 1.0613 |
| NESTLEIND 2024-01-04 | 27116.40 | 1355.80 | 20.0003 |
| NESTLEIND 2024-01-05 | 2666.40 | 1333.20 | 2.0000 |

Four official NSE bhavcopy archives were downloaded and checked against the saved snapshot. The differences demonstrate that vendor-adjusted values cannot be treated as original traded rupee prices for historical whole-share quantities and fixed DP fees. Nestle 2024-01-04 differs by approximately 20 times, consistent with cumulative later unit adjustments; the exact complete adjustment chain has not been certified. Do not rescale the entire dataset from these four ratios.

This materially limits the v6 whole-share cost replay; those figures remain provisional and cannot be called an executable historical account simulation. Prior quote-return diagnostics are a separate representation, also subject to their documented sampling and adjustment limitations.

## Remaining data requirements

Market gate is intentionally closed: full verified unadjusted execution prices; action factors, ex-dates and dividend payment dates; historical fee and settlement calendars. A complete adjustment history must extend through the 2026 vendor snapshot, not stop at the 2025 evaluation year. Announcement timestamps matter when decisions depend on advance action knowledge, whereas ex-date and payment-date evidence drive the accounting itself. We have not silently treated missing timestamps as proof that all historical action accounting is impossible.

The public NSE raw-price samples establish a promising source for the next data-reconciliation step without requiring another model architecture. Preserve raw execution prices and separately construct causally adjusted signal features. Do not double-apply split entitlements to already adjusted prices. The next market strategy experiment stays gated until this is resolved; 2025 remains observed development data.

Reproduce: `python -m unittest discover -s tests -p test_ledger_v7.py`; `python src/synthetic_v7.py` (refuses to overwrite completed controls); `python src/price_basis_probe_v7.py`. Full frozen scope: [BACKTEST_VALIDATION_V7.md](BACKTEST_VALIDATION_V7.md).

Provider sources: [Kite chart adjustments](https://support.zerodha.com/category/trading-and-markets/charts-and-orders/charts/articles/kite-charts-not-matching-as-per-the-records-in-nse-or-bse), [Kite historical API adjustment explanation](https://kite.trade/forum/discussion/15971/getting-the-right-closing-prices-adjusted-for-corporate-actions). Exchange URLs and hashes are in `experiments/backtest_validation_v7/price_probe_manifest.json`.
