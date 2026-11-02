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
