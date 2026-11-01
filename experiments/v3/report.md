# Context v3: completed bounded study

No validation-eligible profitable candidate; selected cash.

Selected on 2023: **cash / no eligible strategy**. Live deployment remains disabled. 2025 was not accessed.

## Exact preserved learning inputs

326,880 rows, 58 feature columns, 37 companies.
Split rows: {'train': 158020, 'development': 87450, 'validation': 81410}. Split sessions: {'development': 245, 'train': 432, 'validation': 224}.
Independent-source quality quarantine removed 25,640 rows. The pre-quarantine table is preserved separately and was not the fitted input.
`data/context_training_v3/samples.csv.gz` contains exact features, targets, split assignments and execution fields used for fitting and evaluation. `source_manifest.csv` fingerprints original source payloads; `dataset.json` fingerprints configuration, builder and table.

## All nine candidates

| Candidate | 2022 diagnostic net | 2023 net | Validation trades | 2024 development net | 2024 stressed net |
|---|---:|---:|---:|---:|---:|
| continuation_rule | -78.61% | -78.68% | 3673 | -79.75% | -90.62% |
| continuation_ridge | -0.48% | -0.26% | 9 | 1.24% | 0.97% |
| continuation_tree | -0.64% | -0.60% | 11 | 0.00% | -0.20% |
| reversal_rule | -62.67% | -65.18% | 2886 | -66.27% | -81.51% |
| reversal_ridge | -0.20% | -0.16% | 10 | 0.72% | 0.50% |
| reversal_tree | -1.23% | -0.89% | 7 | 0.24% | -0.18% |
| relative_rule | -69.50% | -69.74% | 3061 | -78.18% | -89.07% |
| relative_ridge | 0.05% | -0.21% | 12 | -3.02% | -3.40% |
| relative_tree | -2.35% | 0.28% | 11 | -3.45% | -3.68% |

Results use INR 50,000 illustrative initial capital, whole-share long positions, INR 10,000 position limits, at most five positions, historical estimated fees and 2 bps adverse slippage per side. Stress uses 5 bps per side. Cash earns zero. Returns are simulated portfolio results, not guaranteed fills or income.

## Selection and uncertainty

The rule was committed before fitting: require at least 200 validation trades, positive validation net return and no exit-capacity proxy failures; then select highest validation net return. Otherwise choose cash. 2024 was already seen in previous research and is a development comparison, not a fresh holdout. Every candidate is reported; later profitable-looking development candidates cannot replace the validation choice.

Five-session circular block-bootstrap bounds are in results.json for all candidates. The nine-candidate Bonferroni adjustment does not erase selection across earlier project versions. Small samples and regime dependence limit the inference.

## Persistence and reproduction

- `models/context_v3/candidates.joblib`: all fitted final candidates, their preprocessing, features and selection outcome.
- `models/context_v3/bundle.json`: model, data, configuration and training-code hashes.
- Exact saved/reloaded prediction difference: 0.0.
- `python src/context_predict.py --csv examples/context_v3_features.csv` loads saved models without fitting.
- `python src/context_models.py` detects completed results and checks model hash instead of retraining.

## Material limitations

The cohort survives to the modern instrument list and was screened using its history. Corporate-action ex-dates, zero-volume stock sessions, incomplete index sessions and independent-source high/low disagreement dates are excluded retrospectively. Historical membership and all security adjustments are not independently certified. Official daily histories for all nine indices over four years provide calendar/price checks; these do not certify intraday observations. Full-day quality quarantines would not be knowable at decision time and can remove volatile dates. The screen therefore prevents an unbiased live-performance claim. The comparison CSV records differences between official daily values and intraday aggregates; the official close need not equal the final minute quote.

Bar-volume participation is an ex-post execution feasibility proxy. Historical spread, queue, market impact, exchange halts and actual fill availability are not known. Exit-capacity failures are counted rather than silently omitted. Estimated fees omit full contract-note reconciliation and may omit minor levies. Reported drawdowns use daily closes, not full intraday marks. These limitations prohibit treating a positive result as demonstrated deployable profitability.

No hyperparameter sweep, reinforcement learning, neural-network retraining, paid compute or live orders was performed. The next decision must follow the evidence; a failed experiment should be retained and not retuned against the same comparison period.
