# First minute-data learning experiment

**Result: No demonstrated trading edge after the assumed costs.**

## What was built

- Copied 148 source files for 37 companies into `C:/Users/mayan/Documents/Codex/TradingResearch/data/curated_minute_v1/`.
- Every copy was verified by SHA-256. Original files were not changed.
- Generated 395,769 examples from minute candles; omitted 482 nonstandard/incomplete sessions without filling them.
- Trained on 2021–2022, selected on 2023, evaluated on 2024. No 2025 prices or outcomes were used in learning/evaluation.
- The model predicts the next 30-minute direction. It learns associations, not causal explanations.

## Results

| Measure | Result |
|---|---:|
| Selected model | hist_gradient_boosting |
| Selected threshold | 0.50 |
| Validation average net return per hypothetical trade | -18.479 bps |
| Test AUC (0.5 is random ranking) | 0.5165 |
| Test probability Brier score (lower is better) | 0.24970 |
| Constant-probability baseline Brier | 0.24986 |
| Hypothetical selected test trades | 17,027 |
| Test average gross return per hypothetical trade | 0.280 bps |
| Test average net return with 20 bps costs | -19.720 bps |
| Always-long same-times baseline, net | -20.049 bps |
| Selected test trades with zero-volume execution bars | 0 |

One basis point (bp) is 0.01%. The 20 bp round-trip cost is a declared illustrative assumption, not a verified brokerage/slippage estimate. These are average hypothetical trade returns, not account or annual returns.

## Cost sensitivity

| Round-trip cost | Test mean net return per trade |
|---|---:|
| 0 bps | 0.280 bps |
| 10 bps | -9.720 bps |
| 20 bps | -19.720 bps |
| 50 bps | -49.720 bps |

Conditional 95% block-bootstrap interval at 20 bps costs: -20.791 to -18.519 bps per hypothetical trade. It accounts for some day clustering, but not universe bias, data errors, or unrealistic fills.

## Excluded companies

- ADANIENT: Pilot revealed revised OHLCV history; do not mix data snapshots.
- BAJAJFINSV: nonpositive_price_rows
- BAJFINANCE: nonpositive_price_rows
- BHARTIARTL: invalid_ohlc_rows
- BRITANNIA: invalid_ohlc_rows
- DIVISLAB: invalid_ohlc_rows
- HDFCBANK: invalid_ohlc_rows
- HDFCLIFE: nonpositive_price_rows
- ICICIBANK: invalid_ohlc_rows, nonpositive_price_rows
- ITC: nonpositive_price_rows
- SBILIFE: invalid_ohlc_rows
- UPL: invalid_ohlc_rows

## What you should challenge

1. **Unseen data:** was this evaluated after all model choices were fixed? Here the model and threshold used validation only. Do not retune against these 2024 results.
2. **Costs and fills:** can the claimed opening/closing prices actually be traded? Here they are idealized quotes, not verified fills. No live return claim is justified.
3. **Data selection:** would the result survive missing stocks and excluded sessions? The supplied survivor cohort and whole-history cleaning create retrospective selection.
4. **Evidence versus explanation:** importance scores are predictive associations, not reasons markets move. A confident model can be confidently wrong.
5. **Baseline:** does complexity beat simple alternatives and doing nothing? A positive directional score is insufficient if average net trades lose money.
6. **Stopping:** negative validation results are a reason to reject deployment, not to keep trying thresholds on the test set until one wins.

## Data investigation carried forward

ADANIENT pilot revisions closely match the published rights factor 0.969485: all 1,504 compared price fields are within 0.051 rupees of that factor. This supports a corporate-action explanation; it does not certify all historical records. The company remains excluded from this first frozen cohort.
[Zerodha rights-adjustment bulletin](https://zerodha.com/marketintel/bulletin/433585/adjustment-of-futures-and-options-contracts-of-adanient-due-to-rights-issue)

Zerodha documents opening-price corrections using exchange pre-market prices. That is a plausible explanation for first-minute conventions, not confirmation of the seven specific inconsistent candles. Those companies remain excluded.
[Zerodha opening-price documentation](https://support.zerodha.com/category/trading-and-markets/charts-and-orders/charts/articles/value-of-historical-candles-on-refresh)

ITC daily-versus-minute revision differences remain unresolved. The attempted public NSE archive download timed out, so no independent exchange-data certification is claimed.

## Boundaries

Live trading and automatic model promotion remain disabled. No GPU spending, subscriptions or external messages were initiated. Further experiments must be versioned and count the 2024 results as already observed; 2025 remains reserved for a later final check.