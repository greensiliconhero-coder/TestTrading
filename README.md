# Five-day iteration v5

Status: completed exploratory run. Selected on 2024: cash. No live trading.

Train: 2021–2023, 2,566 stock-date samples in 111 nonoverlapping batches. Validation: 2024, 40 batches. Previously observed development period: 2025, 41 batches. Five-session holds, next-open entry, equal-weight fractional baskets; 50 bps assumed round-trip cost, stressed at 75 and 100.

| Candidate | 2024 net basket | 2025 development net basket | 2025 profitable / trades | 2025 net at 100 bps |
|---|---:|---:|---:|---:|
| equal_weight | -12.33% | -10.18% | 425/929 | -26.91% |
| momentum20 | -0.52% | -13.39% | 86/205 | -29.53% |
| reversal5 | -8.75% | -9.08% | 99/205 | -26.01% |
| ridge | -4.06% | -4.12% | 101/205 | -21.95% |
| tree | -13.51% | 7.34% | 99/205 | -12.57% |

Interpretation: none was profitable on validation, so cash was selected before development evaluation. The tree development gain cannot be chosen in hindsight. Five-session rotation still incurs substantial recurring costs; 40 rotations at 50 bps imply roughly 20 percentage points of annual turnover cost before compounding and market returns. This does not establish that the holding period is optimal or that learning has failed in general.

Limitations: same surviving-stock universe; no untouched test available. 3,807 stock-window observations were retrospectively excluded for corporate actions across lookback through exit. This is a major selection bias and reduces usable observations. Results are fractional basket diagnostics, not capital-account simulations. Equal-weight uses all eligible stocks and therefore a different position count; the fixed cost assumption is not an exact DP-fee comparison at a common capital amount. NIFTY comparison is a price-index return on matching windows, not an investable total-return benchmark. Overnight gaps and executable fills remain unresolved.

Next iteration should first resolve corporate-action-adjusted total-return data and use explicit capital-dependent delivery costs and an investable passive benchmark. A longer holding horizon may reduce turnover further, but it should be preregistered and evaluated without repeatedly calling 2025 unseen. No automatic parameter search has been launched.

Validation: future-bar changes did not alter prior features; known-payoff basket/cost arithmetic passed; saved estimators reproduced predictions exactly. Exact input tables, raw-source hashes, fitted models, scores and trade records are preserved.

Reproduce: `python src/five_day_v5.py` (refuses to overwrite completed results). Protocol: [FIVE_DAY_V5.md](FIVE_DAY_V5.md).
