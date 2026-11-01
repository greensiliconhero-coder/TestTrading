# Minimum-trade requirement removed: sensitivity results

Post-hoc sensitivity on preserved model snapshots. Only the minimum sample-count eligibility requirement was removed. Model weights, preprocessing, original thresholds, forecast/cost hurdles, costs, slippage, position sizes, execution checks and selection periods stayed unchanged. No retraining, real orders or 2025 access.

## Selection changes

| Saved snapshot | Selection without minimum count | Selection-period result | Later comparison |
|---|---|---|---|
| v1 classifier | None passes positive validation net return | All original tree/logistic thresholds lose after 20 bps quote costs in 2023 | No qualified strategy to carry forward |
| v2 best CNN | Probability-score threshold 0.55 | 1 trade in 2023; +126.7243 bps net on that quote trade | 0 trades in 2024 |
| v3 final models trained 2021-2022 | relative_tree | 11 trades; +0.2804% portfolio return in 2023 | 22 trades; -3.4463% in 2024 |
| v3 earlier diagnostic fits trained 2021 | relative_ridge, hypothetical selection on 2022 | 12 trades; +0.0483% in 2022 | 14 trades; -0.4856% in 2023; 42 trades; -0.4448% in 2024 |

Portfolio comparisons each restart with the original illustrative INR 50,000 capital; they are not a continuously compounded multi-year run. CNN/classifier figures are averages per idealized quote trade, not portfolio returns. Zero trades do not provide a per-trade return estimate. No minimum quota is imposed on trade generation.

## V1 preserved tree: all original thresholds

| Threshold | 2023 trades | 2023 mean net bps/trade | 2024 trades | 2024 mean net bps/trade |
|---|---:|---:|---:|---:|
| 0.5 | 14884 | -18.4789 | 17027 | -19.7202 |
| 0.55 | 450 | -16.8671 | 788 | -15.4500 |
| 0.6 | 52 | -38.2032 | 71 | -15.4042 |

The earlier logistic model weights were not preserved. Its historical 2023 validation results can be evaluated for the gate change without fitting it again:

| Threshold | Historical validation trades | Mean net bps/trade |
|---|---:|---:|
| 0.5 | 6366 | -18.5212 |
| 0.55 | 333 | -15.2006 |
| 0.6 | 76 | -1.8906 |

All logistic validation means are negative, so it has no profitable selection even without a count floor. No fresh logistic inference or later-year replay is claimed. The original v1 rank-only selector could name a least-negative candidate; the original profitability approval check still fails.

## CNN: all original thresholds

| Threshold | 2023 trades | 2023 mean net bps/trade | 2024 trades | 2024 mean net bps/trade |
|---|---:|---:|---:|---:|
| 0.5 | 199 | -19.7662 | 369 | -31.6134 |
| 0.55 | 1 | 126.7243 | 0 | no trades / undefined |
| 0.6 | 0 | no trades / undefined | 0 | no trades / undefined |

Threshold 0.55 is selected from 2023 only; the 2024 zero-activity result is not replaced by another threshold. Best-epoch selection remains fixed; the optimizer recovery checkpoint was not treated as a new candidate. The score is not a calibrated probability of net profit.

## All final context-v3 candidates

| Candidate | 2023 trades | 2023 net | Exit-capacity failures | Qualifies without count floor? | 2024 trades | 2024 net | 2024 stress net |
|---|---:|---:|---:|---|---:|---:|---:|
| continuation_rule | 3673 | -78.6755% | 243 | no | 3816 | -79.7501% | -90.6213% |
| continuation_ridge | 9 | -0.2621% | 1 | no | 26 | 1.2410% | 0.9692% |
| continuation_tree | 11 | -0.5976% | 2 | no | 18 | 0.0008% | -0.1979% |
| reversal_rule | 2886 | -65.1832% | 241 | no | 2920 | -66.2727% | -81.5068% |
| reversal_ridge | 10 | -0.1589% | 3 | no | 20 | 0.7219% | 0.5048% |
| reversal_tree | 7 | -0.8877% | 2 | no | 38 | 0.2435% | -0.1762% |
| relative_rule | 3061 | -69.7350% | 195 | no | 3176 | -78.1798% | -89.0686% |
| relative_ridge | 12 | -0.2127% | 1 | no | 34 | -3.0241% | -3.4024% |
| relative_tree | 11 | 0.2804% | 0 | yes | 22 | -3.4463% | -3.6780% |

Original final selection was cash. Dropping only the 200-trade requirement selects relative_tree. Replaying that fixed candidate reproduces the original candidate-level metrics exactly; the unchanged 2024 stressed net return is -3.6780% (see exact JSON value if rounded). All other candidates remain rejected on validation profitability or execution checks.

## All earlier diagnostic snapshots

| Candidate, fitted on 2021 | 2022 trades | 2022 net | 2022 exit failures | 2023 trades | 2023 net | 2024 trades | 2024 net |
|---|---:|---:|---:|---:|---:|---:|---:|
| continuation_rule | 3681 | -78.6109% | 172 | 3673 | -78.6755% | 3816 | -79.7501% |
| continuation_ridge | 13 | -0.4818% | 1 | 27 | -0.9100% | 52 | 2.1042% |
| continuation_tree | 23 | -0.6390% | 0 | 4 | -0.3142% | 22 | -0.1906% |
| reversal_rule | 2707 | -62.6741% | 168 | 2886 | -65.1832% | 2920 | -66.2727% |
| reversal_ridge | 12 | -0.2034% | 2 | 13 | -0.6244% | 14 | -0.1366% |
| reversal_tree | 36 | -1.2335% | 4 | 6 | -0.1035% | 16 | -0.0957% |
| relative_rule | 2841 | -69.5019% | 142 | 3061 | -69.7350% | 3176 | -78.1798% |
| relative_ridge | 12 | 0.0483% | 0 | 14 | -0.4856% | 42 | -0.4448% |
| relative_tree | 39 | -2.3514% | 0 | 27 | -0.4308% | 39 | -0.7591% |

The diagnostic selection is hypothetical: those earlier models were originally reported as diagnostics, not selected for deployment. Applying the common count floor of 200 selects cash; removing it selects relative_ridge from 2022. Later metrics use the unchanged earlier weights, not the newer 2021-2022 fit.

## Reproduction, scope and limitations

- `src/no_min_trades.py` replays saved models and verifies model hashes before/after. It contains no training calls. `config/no_min_trades.json` was committed before this replay.
- `results.json` records all summaries and model fingerprints. Adjacent CSVs preserve selected trade records and daily equity plus CNN trades at each original threshold.
- Three policy tests passed: one observation can qualify, no activity/negative net return cannot demonstrate profit, and execution checks remain active after removing the count gate.
- Original data, models, reports and selection outcomes are not overwritten. Existing inference bundles still record their original selection; this sensitivity reports counterfactual choices separately.
- Earlier dataset and execution limitations still apply: retrospective survivor/quality screening, estimated fees, idealized classifier fills and ex-post bar-volume capacity proxies. Every later period here was already observed; this is not fresh validation.
- Original thresholds are held fixed. No later-period winner is substituted for the selection-period choice. 2025 remains reserved.

**Conclusion:** removing the minimum count admits rare apparent winners, but none of the newly admitted selections demonstrates repeatable profitable activity in its later comparison periods. This result does not establish that rare trading is inherently bad; it shows that the sample-count gate was not the only obstacle for these saved models.
