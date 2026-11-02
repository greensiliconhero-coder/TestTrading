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
