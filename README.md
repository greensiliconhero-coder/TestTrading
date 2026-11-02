# Delivery-cost iteration v6

Branch: `research/delivery-costs-v6`. Completed: itemized fee replay, corporate-action source audit and passive ETF price benchmark. No new model fitting; v5 scores/weights reused. Original validation selection remains cash.

Each period starts with INR50,000. Active rankings allocate up to INR10,000 per position, whole shares, residual cash, buy-fee reservation. Base slippage: 5 bps each side; stress: 10. Current published resident-individual delivery fees are applied counterfactually to 2024/2025, not represented as exact historical contract notes. ETF taxes differ from individual-stock delivery taxes.

| Strategy | 2024 net return | 2025 development net return | 2025 fee total |
|---|---:|---:|---:|
| equal_weight | -19.84% | -17.71% | INR 10,647.71 |
| momentum20 | 2.88% | -11.58% | INR 6,498.64 |
| reversal5 | -9.98% | -3.40% | INR 6,601.97 |
| ridge | -3.84% | -2.18% | INR 6,932.57 |
| tree | -10.46% | 5.00% | INR 6,845.36 |
| NIFTYBEES buy and hold | 10.17% | 11.45% | INR 27.30 |

The ETF uses first active entry through last active exit: 2024-01-05 to 2024-12-24 and 2025-01-08 to 2025-12-26. It remains invested through intervening periods where active strategies may be in cash. These are not full calendar-year returns. Fee totals exclude separately modeled price slippage; benchmark excludes cash interest and personal income taxes.

Result: the passive ETF price proxy outperformed every active candidate in both windows. Momentum changed from slightly negative in v5 validation to positive under this cost replay, but still lagged the passive benchmark and lost money in 2025. Do not retroactively promote it. The tree remains negative in validation despite positive 2025 development results.

Corporate-action audit: 326 records, comprising 301 dividends, 6 bonuses, 3 splits, 2 rights, 3 demergers, 6 buybacks and 5 meetings. All 326 lack publication timestamps. Announcement timing, adjustment factors and dividend payment cashflows are not certified. The earlier exclusion of all action types—including meetings—was broad and retrospective. This iteration documents that defect rather than silently claiming it repaired.

Material limitations: original retrospective action-window exclusions remain. Historical adjusted price units may distort whole-share quantities and fixed-fee effects. Gross sell/buy legs are charged at each batch; actual retention/netting and settlement can differ. Same survivor cohort and previously explored 2025. NIFTYBEES is an investable security, but this is a market-price proxy; ETF distributions and historical adjustment continuity are not independently certified, so do not call it a verified total-return backtest.

Validation: tested stock/ETF fee amounts, cash/PnL reconciliation, whole shares, unaffordable positions, fixed-DP effects and slippage sensitivity. All six ETF source chunks checksum-verified and candle-validated with no duplicate daily dates. No live orders.

Next research gate: obtain/reconcile unadjusted prices, split/bonus factors, demerger/rights handling and dividend entitlements before removing retrospective action exclusions or claiming an executable account simulation. Reserve a genuinely unseen future period before another predictive claim. Added complexity alone is not the next step.

Reproduction: `python src/delivery_v6.py` for frozen-score replay (refuses overwrite), `python src/benchmark_v6.py` for benchmark, `python -m unittest discover -s tests -p test_delivery_v6.py`. Source protocol: [DELIVERY_V6.md](DELIVERY_V6.md). Exact scores, fee config, trades, action audit and ETF raw responses are preserved.

Sources: https://zerodha.com/charges/ ; https://support.zerodha.com/category/account-opening/resident-individual/ri-charges/articles/what-do-dp-charges-mean ; https://support.zerodha.com/category/account-opening/resident-individual/ri-charges/articles/stt-etfs .
