# Causal universe and entitlement accounting v10

## Completed

Reconstructed 2,057,943 valid EQ/INE daily records across 1,240 official NSE archives, 2021–2025; 2,612 distinct ISINs. No invalid/zero rows in the defined instrument filter. Original raw source archives were hash-checked.

The frozen rule selects up to 36 securities by trailing 20-session traded value after 61 consecutive valid sessions, every five sessions. It produced 8,496 candidate slots over 236 signal dates, covering 226 ISINs / 222 symbols. Selection uses no future prices or corporate actions. 5,005 slots (58.91%) fall outside the old stock list: the old survivor cohort was materially narrower than this historical liquidity cohort. This is not proof that either universe is profitable.

Candidate membership is saved before future-outcome auditing. Future events never delete candidates. Raw data from securities that later disappear are retained where present in the source archives. INE/EQ is an explicit instrument filter, not certified historical index membership or complete point-in-time security metadata. Identity changes can reset warmup conservatively.

## Accounting audit

277 proposed five-session holding windows intersect 285 exchange action records:

| Record type | Count |
|---|---:|
| Dividend | 238 |
| Bonus | 9 |
| Split | 8 |
| Rights | 1 |
| Demerger | 3 |
| General meeting | 20 |
| Buyback | 6 |

Meetings do not automatically change cash or shares. Buybacks require an explicit participation policy. Parsed dividends, factors and ex-dates are evidence candidates; actual payment/tradability dates and complex entitlements are not invented. All 12,014 input action records had parseable ex-dates; this does not certify completeness or correctness.

61 windows lack both expected EQ/same-ISIN endpoints: 36 extend beyond the dataset boundary, and 25 require coverage/identity review. Those 25 produce 33 endpoint findings: 14 same-ISIN quotes in another trading series, 16 same-symbol quotes with a different ISIN, and three without either match. Exact source quotes/hashes are preserved in endpoint_review.json; none was automatically substituted. Tail windows remain censored, not losses or wins.

## Ledger improvement

New EntitlementLedger extends the existing ledger to distinguish bonus shares owed from shares available for sale. Pending bonus shares contribute marked equity but cannot be sold before the supplied verified tradability session. Missing timing and fractional-entitlement policies fail explicitly. Ex-date buyers do not receive prior-holder entitlements. Existing v9 results are not rewritten.

SEBI's September 16 2024 circular specifies the shortened bonus trading timetable for issues announced on or after October 1 2024; this is not a blanket rule for older actions. Source PDF and hash saved. [Official SEBI circular](https://www.sebi.gov.in/sebi_data/attachdocs/sep-2024/1726484230463.pdf).

Full regression suite: 78 tests passed, including six new tests for past-only selection, gap handling, bonus tradability, ex-date entitlement and atomic rejection. These are engineering checks, not validation of market profitability.

## Remaining gate and next work

No new model fit, profit figure or deployable backtest is claimed for v10. The reconstruction removes the previous explicit survivor-list and future-action filters from candidate selection, but a complete causal feature/label and execution pipeline is still unfinished. Required next: verify the 17 split/bonus records and identity transitions; establish dividend entitlements/payment evidence; account for rights/demergers; certify historical fee/settlement assumptions. Prioritized evidence and endpoint queues are saved without deleting difficult windows. Then run the preregistered rolling comparison of simple models with all chronological outcomes reported.

The earlier v9 private release has now been verified against its 150,910,906-byte local archive and SHA256 bc468aa7341467a897fe8c087b41e1d3c766612117869e02b2c0150ecd013742. No credential or paid-compute access was needed for v10.

## Reproduce

Protocol: CAUSAL_UNIVERSE_V10.md. Run python src/causal_universe_v10.py (refuses completed overwrite), python src/audit_obligations_v10.py, and python -m unittest discover -s tests. Data: data/causal_universe_v10. Reports and evidence queues: experiments/causal_universe_v10. The archive receipt records the precise reproducible backup scope.


---

# Corrected-input five-day refit v9 — completed

Same Ridge and histogram-tree architectures and hyperparameters as v5; trained on 2021–2023. All 4,444 original sample keys retained: 2,566 training, 879 validation, 929 development and 70 purged. Eight features rebuilt from raw NSE prices/volume and official NIFTY 50 context; labels rebuilt from raw entry/exit opens. Models, exact samples, evaluation predictions and all equity/order logs saved.

## Primary results

INR50,000 initial capital, INR10,000 ranked position cap, whole-share retained positions, current fee assumptions, one-session cash settlement, 5bps each-side slippage. These are period returns, not annualized: 2024 Jan5–Dec24 and 2025 Jan8–Dec26.

| Candidate | 2024 validation | 2025 development |
|---|---:|---:|
| NIFTYBEES | 10.17% | 11.45% |
| equal_weight | -2.00% | 0.30% |
| momentum20 | 8.20% | -4.89% |
| reversal5 | -7.17% | -3.06% |
| ridge | 0.26% | 14.47% |
| tree | -9.76% | 1.87% |

The validation rule required a positive return above NIFTYBEES before selecting an active strategy. No candidate qualified: selection was locked to cash before computing development predictions. Therefore the selected policy's return is 0% in both periods, with opportunity cost versus the ETF. Ridge's +14.46% in 2025 is an unselected, already-seen development result; it does not override the failed 2024 selection.

## What changed and what it means

Frozen-score v8 Ridge returned -1.20% / +7.33%; corrected-input refit v9 returned +0.26% / +14.46%. This is a combined input/target-source correction, not proof that more model complexity helps. Source differences can change fitted rankings substantially. Tree remained negative in validation. No neural network or reinforcement learning was trained in this version. No hyperparameters were searched.

Full sensitivity results (zero/one-session settlement, 5/10bps slippage) and daily-open drawdowns are in experiments/raw_five_day_v9/results.json. Do not confuse buy/sell order counts with completed profitable trades; retained inventory has not been assigned roundtrip win-rate attribution.

## Constraints

2025 has already been examined. Sample eligibility still uses retrospective corporate-action exclusions and a survivor universe. Current fee rates and simplified settlement are counterfactual, not certified historical accounting. Quantity sizing at observed open is approximate. Dividend payment dates, rights/demergers and ETF total-return certification remain unresolved. This diagnostic does not pass the deployment gate and supports no income or profitability promise.

The next substantive change should remove retrospective eligibility with verified action accounting and causal features, then evaluate a small preregistered strategy set with chronological folds. Do not choose Ridge just because 2025 looks better or spend money on GPUs for this small dataset. Preserve any future holdout until rules are locked.

## Reproduction and preservation

Protocol: RAW_FIVE_DAY_V9.md (committed before fitting). Run python src/raw_five_day_v9.py; it refuses to overwrite a locked run. Model reload predictions matched exactly. Two new tests verify feature causality under future-price perturbations and exact sample identity/label boundaries; both passed, following the 70-test v8 suite.

Private release raw-refit-v9 contains the full v8 raw NSE collection and v9 samples/models/logs plus supporting daily vendor/reference inputs. It excludes earlier minute datasets, which remain in their existing local storage. The archive member hashes and receipt define the precise backup scope.


---

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
