# Research direction, 2 November 2026

## Decision

The best method for this dataset is not known. Our first small CNN did not establish an edge; it does not reject neural networks as a class. Start the next study with market-context features, explicit trade economics, a selective event model, and chronological portfolio evaluation. Use simple rules, regularized linear models and boosted trees as competitors. Introduce a sequence model only against the same task, data, costs and experiment budget. Reinforcement learning is a later candidate for sequential position management after validating the simulator. No compute purchase or live trading is part of this proposal.

This is a proposed research design, not a frozen training protocol. Commit the fully specified feature definitions, event cutoffs, cost schedule, allocation rules and selection criteria before running it. Do not silently expand the search after seeing results.

## What our evidence establishes

- On identical 2024 examples, CNN AUC was 0.505389 and tree AUC was 0.515524. This is ranking performance, not profit or accuracy. 2024 was already seen and is development evidence.
- The CNN produced no validation rule with the predefined minimum sample. A validation threshold with one profitable trade is insufficient evidence.
- Training windows number 181,670 but cover 491 distinct sessions across 37 correlated stocks. Adjacent windows share inputs. Bootstrap calendar blocks jointly across stocks rather than treating windows as independent observations.
- Twenty basis points was an exploratory assumed round-trip charge, not a measured cost. Calibrate actual fees and execution costs; also report breakeven costs. Do not lower assumptions simply to make results positive.
- Missing 2020, corporate-action mismatches, whole-history exclusions and a surviving-stock universe constrain conclusions. Excluding an adjusted series can discard valid data; exclusion is not independent certification of remaining files.

## Model comparison

| Method | Useful role | Next action |
|---|---|---|
| Explicit rules | Transparent momentum/reversal hypotheses and diagnostic baseline | Include |
| Regularized linear model | Check whether context adds simple, stable information | Include |
| Gradient-boosted trees | Nonlinear interactions in engineered numeric features | Primary initial learned competitor |
| CNN/LSTM | Learn sequence structure missed by engineered features | Compare later with identical evaluation; the current CNN remains saved |
| RL | Inventory, holding and rebalancing decisions with costs and delayed rewards | Defer until execution model is validated |
| Ensemble | Combine complementary out-of-sample signals | Require measured diversity and benefit after extra turnover |
| Unbounded brute force/genetic search | Find impressive retrospective winners rapidly | Reject; use a logged, finite hypothesis budget |

There is no reason to expect an ensemble of weak, correlated models to automatically create an edge. An RL agent can learn a simulator's mistakes. Simulated paths and pretrained forecasting models are research tools, not independent evidence of tradable predictability.

## Proposed next experiment

Keep the minute candles. Build context using only information available at each decision: stock return relative to an aligned broad-market index and sector; realized volatility; opening gap; trailing turnover; relative volume adjusted for time of day; lagged breadth of a defined universe; trailing market exposure. Any VWAP proxy from minute bars must be labeled approximate, not exchange trade-level VWAP.

Study three hypotheses: continuation after a directional move with participation; reversal after an unusually large move; and recovery/continuation of a stock's deviation from its market/sector. These are hypotheses to falsify, not profitable strategies already found. Restrict first implementation to long-or-cash unleveraged equity to avoid mixing direction prediction with short availability and derivatives mechanics.

Use the existing 30-minute horizon initially to isolate the value of new context and selective decisions. Longer intraday holding and multi-session ranking are separate studies with different risk/cost assumptions, not extra dimensions in a giant parameter sweep. Aggregated past context can be derived from minute data without replacing the minute dataset or inventing additional observations.

The target should include return magnitude and downside, not just direction. A simple model can predict conditional returns; a classifier can target returns above an independently specified cost hurdle. Estimate uncertainty and calibration out of sample. A positive class probability alone cannot determine expected profit.

Separate signal from decision and execution: candidate event -> forecast -> cost/risk gate -> capital allocation -> execution simulation. The gate must allow no trade. Avoid a second learned filter until there are enough out-of-sample event outcomes to train it without reuse/leakage.

Proposed initial budget: three predefined event families, each with one explicit rule, one regularized linear model and one boosted-tree configuration: nine candidates total. Threshold choices and any seeds are additional trials and must be declared and logged. Freeze numerical specifications before training. This nine-candidate design is not yet executed.

## Evaluation gates

1. Use expanding chronological training folds within 2021-2024; fit transformations only inside each training fold. Remove labels crossing boundaries; respect time overlap. Keep 2025 unopened for model selection. Existing whole-history universe screening means it is still not a pristine unbiased universe test.
2. Model portfolio cash, simultaneous exposures, whole shares, position caps and turnover. Use completed candles, delayed execution, unavailable fills, volume participation and spreads. If intrabar stop/target order is unknowable from OHLC, use a conservative resolution or declare ambiguity.
3. Separate date-effective statutory/broker fees from estimated spreads, slippage and impact. Current fee tables cannot simply be applied retrospectively to every year. Report stress scenarios and breakeven round-trip costs.
4. Report net portfolio returns, drawdowns, turnover, costs, exposure, concentration and comparison with cash and an appropriate passive benchmark. Ranking metrics alone are secondary diagnostics.
5. Estimate uncertainty using time blocks across the entire stock panel, record every trial, and use multiple-testing-aware analysis. Positive results must not depend on a few stock-days or a narrow parameter setting. Establish minimum evidence and rejection criteria before fitting.
6. Freeze the winner before one reserved-period evaluation. Later changes require fresh forward evidence, followed by paper execution. A short paper run verifies operations; it cannot by itself prove stable profitability.

## Data priorities

Now: aligned minute broad-index and relevant sector-index histories for the study dates, a corporate-action/security-identity ledger, calendar validation and an independent sample check against exchange data. Historical universe membership and delisted names are needed before generalizing beyond the current screened cohort. Stock breadth can be computed from that cohort but must carry its biased-universe limitation.

Next: repair missing dates/years consistently and acquire additional regimes; reserve newly acquired outcomes before looking at them. Begin collecting forward bid/ask snapshots and timestamps to validate spread/latency assumptions. The historical candle endpoint does not supply historical order-book snapshots; missing quotes cannot be reconstructed exactly from OHLCV.

Later: point-in-time announcements or fundamentals only if the hypothesis requires them. OI is not required for the proposed cash-equity experiment. Derivatives need contract identity, expiries, lot sizes and realistic bid/ask and settlement treatment; options additionally need strike/expiry structure and volatility information. OI alone is insufficient.

## Sources and what they do (and do not) support

1. Gu, Kelly and Xiu, *Empirical Asset Pricing via Machine Learning* (published 2020): trees and neural networks benefited from nonlinear interactions in an equity risk-premium study. This is not evidence that minute OHLCV in India is profitable. https://www.nber.org/papers/w25398
2. Zhang, Zohren and Roberts, *DeepLOB* (2019): a neural architecture learns order-book features. Our minute candles lack that information, so this is a different data task. https://arxiv.org/abs/1808.03668
3. Zhang, Zohren and Roberts, *Deep Reinforcement Learning for Trading* (2019): reports favorable results for position decisions on 50 liquid futures with volatility scaling and transaction-cost assumptions. This does not validate our execution environment or guarantee transfer. https://arxiv.org/abs/1911.10107
4. Saly-Kaufmann et al., *How do standard time series forecasting benchmarks translate to finance?* (October 2026 revision, preprint): recurrent hybrids lead several comparisons on daily multi-asset futures. Generic forecasting rankings do not reliably transfer. Its proportional-cost analysis does not fully model market impact, slippage or venue-specific frictions. https://arxiv.org/html/2603.01820v2
5. Bailey et al., *The Probability of Backtest Overfitting*: selecting strategies using repeated backtests creates selection risk. https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf
6. Bailey and Lopez de Prado, *The Deflated Sharpe Ratio* (2014): addresses multiple-testing selection and non-normality. https://doi.org/10.2139/ssrn.2460551
7. Kite historical candle documentation: OHLCV/OI and restrictions on continuous futures history; live quotes documentation describes depth separately. https://kite.trade/docs/connect/v3/historical/ and https://kite.trade/docs/connect/v3/market-quotes/
8. Zerodha charges: current fee components. A historical cost engine also needs effective-date changes. https://zerodha.com/charges/

## Local computation performed for this review

Run `python src/research_sanity.py`. Results are in `experiments/research_review_2026_11_02/sanity_checks.json`. In 10,000 synthetic null experiments, searching 100 independent candidates caused 99.46% to have at least one nominal one-sided 5% development success; independent forward success remained 4.85%. Actual strategy searches have correlated trials, so these values are an illustration, not an estimated failure probability for our models. A separate hypothetical 60%-win strategy with 10 bps wins, 20 bps losses and 3 bps costs loses 5 bps per trade on expectation.

No new trading model was trained for this review. Existing checkpoints are preserved. CPU is sufficient for the proposed first comparisons. A rentable GPU becomes relevant only after measured training runtime justifies it. Trading income remains unproven and should not be budgeted as dependable income.
