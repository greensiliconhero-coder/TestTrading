# Five-year model results

Training: 2021–2023. Validation: 2024. Test: 2025. No minimum validation trade count. Data: 36 retained stocks and nine indices; TATAMOTORS excluded pending demerger continuity review.

| Context candidate | 2024 net return | Trades | 2025 net return | Trades |
|---|---:|---:|---:|---:|
| continuation_rule | -80.18% | 3815 | -78.88% | 4080 |
| continuation_ridge | 1.28% | 8 | -0.11% | 3 |
| continuation_tree | -0.15% | 6 | -0.01% | 2 |
| reversal_rule | -66.38% | 2904 | -65.92% | 2892 |
| reversal_ridge | -0.05% | 11 | 0.00% | 0 |
| reversal_tree | -0.33% | 41 | -0.56% | 11 |
| relative_rule | -77.71% | 3171 | -72.25% | 3392 |
| relative_ridge | -0.62% | 7 | 0.18% | 10 |
| relative_tree | -0.83% | 29 | 0.08% | 9 |

Selected using validation: **continuation_ridge**. Context returns are simulated net portfolio returns on INR 50,000 starting capital, reset for each period. Rule strategies also had exit-capacity proxy failures; their performance is not evidence of executable fills.

Logistic and histogram-tree classifiers: all tested validation thresholds lost money after the assumed 20-bps round-trip cost; no rule selected. CNN: four epochs completed, best epoch two, no profitable validation threshold; 2025 AUC 0.49994. AUC measures ranking of direction labels, not accuracy or profit probability.

Small positive 2025 results for the relative Ridge/tree candidates were not validation-selected and cannot be substituted after seeing the test. No repeatable profitable edge demonstrated.

Limitations: surviving-stock cohort, retrospective session and independent-source filters (73 dates), ex-date exclusions, changed cohort and stricter stock-only quality filters, estimated costs, no historical bid/ask execution simulation. Added data is not the only change versus earlier versions. 2025 is now observed and cannot serve as an untouched test for further tuning.

Models and exact inputs are saved locally. Full data/model GitHub release archive and detailed review remain pending.
