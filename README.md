# TradingResearch

**Branch: `experiment/neural-v2` — Completed first neural-network experiment.**

This branch contains the actual CNN, saved weights, preprocessing, earlier tree baseline, v1/v2 results and research review. Context-v3 details below are cross-branch references, not a claim that context-v3 models live on this branch.

Documentation audited on 2 November 2026. The sections below summarize completed studies across the repository; each source link identifies the branch that actually contains the artifact. All simulated strategies remain research-only. No live orders were placed. 2025 remains unused for model fitting/selection/evaluation.

## Minimum-trade sensitivity follow-up

A separate post-hoc replay removes only the minimum-trade-count requirement; weights, thresholds, costs and execution checks remain fixed. The CNN qualifies on one 2023 trade but has no 2024 trades. Final context relative_tree qualifies on 11 trades (+0.2804% in 2023), then loses 3.4463% over 22 trades in 2024. The earlier relative_ridge snapshot qualifies on 12 trades in 2022, then loses in both later years. Original model selections and artifacts are preserved; no retraining or 2025 access.

See the [complete sensitivity report](https://github.com/greensiliconhero-coder/TestTrading/blob/experiment/no-min-trades/experiments/no_min_trades/report.md) on `experiment/no-min-trades`, including every original threshold, all final/diagnostic model snapshots and unchanged model hashes. These are already-observed comparison periods, not fresh validation.

## Branch directory

| Branch | Purpose |
|---|---|
| [experiment/no-min-trades](https://github.com/greensiliconhero-coder/TestTrading/tree/experiment/no-min-trades) | Completed count-floor sensitivity; original models unchanged |
| [main](https://github.com/greensiliconhero-coder/TestTrading/tree/main) | Project index; code snapshot through neural v2 |
| [experiment/neural-v2](https://github.com/greensiliconhero-coder/TestTrading/tree/experiment/neural-v2) | Completed first neural-network experiment |
| [data/context-sources-v1](https://github.com/greensiliconhero-coder/TestTrading/tree/data/context-sources-v1) | Completed context-source download and first structural audit |
| [research/context-v3](https://github.com/greensiliconhero-coder/TestTrading/tree/research/context-v3) | Context-model proposal plus audited source collection |
| [processing/context-features-v3](https://github.com/greensiliconhero-coder/TestTrading/tree/processing/context-features-v3) | Completed feature processing; exact dataset fingerprints frozen |
| [experiment/context-v3-trained](https://github.com/greensiliconhero-coder/TestTrading/tree/experiment/context-v3-trained) | Completed context-v3 fitting, evaluation and saved models |

## Experiment history and decisions

| Version | What was performed | Evidence and outcome |
|---|---|---|
| v1 | Logistic and gradient-boosted direction classifiers using minute-derived features | 2024 tree AUC 0.516464; selected-rule mean net quote return -19.7202 bps with assumed 20 bps costs. Validation rule failed. |
| Neural v2 | Small sequence CNN on 60-minute OHLCV windows | 2024 AUC 0.505389 vs same-sample tree 0.515524. No eligible validation threshold. |
| Context v3 | Three event families, each with rule/ridge/tree competitors, context and execution constraints | No candidate satisfied frozen 2023 validation requirements; selected cash. |

These are different experiments with different eligible rows, labels and execution assumptions. Do not rank their AUC and portfolio returns as directly comparable measures. AUC is ranking discrimination, not win rate or probability of profit.

## v1: minute-direction baseline

**Question:** do recent stock-only price/volume features predict the direction of the next 30-minute quote return?

- Data: immutable screened minute copies for 37 surviving companies, 148 files for 2021-2024. Training 2021-2022: 199,837 examples; validation 2023: 98,483; initial 2024 evaluation: 97,449.
- Inputs: 5/15/30-minute return, trailing 30-minute volatility, last-five vs last-30 volume ratio, five-minute high/low range, since-open return and session fraction.
- Models: standardized logistic regression and one fixed histogram gradient-boosting classifier. Targets are positive/negative future quote return. Scaling is fit on training only.
- Signals: 09:45-14:45 every 30 minutes; idealized entry next-minute open and exit candle t+30 close. No overnight label.
- Candidate thresholds: 0.50, 0.55, 0.60; at least 1,000 validation trades. Cost assumption 20 bps per round trip; sensitivities at 0/10/20/50 bps.
- Constraints/limits: complete regular sessions only, fixed retrospectively screened survivor cohort, ideal quote fills; no portfolio cash, spread, realistic order latency or independent historical-universe certification.
- Result: validation rule failed; deployment disabled. The reported selected-rule diagnostic had 17,027 2024 quote trades, mean gross 0.279848 bps and mean net -19.720152 bps. These are averages per quote trade, not annual portfolio returns.
- Evidence: [protocol](https://github.com/greensiliconhero-coder/TestTrading/blob/experiment/neural-v2/RESEARCH_V1.md), [full machine-readable results](https://github.com/greensiliconhero-coder/TestTrading/blob/experiment/neural-v2/experiments/v1/model_results.json), [learning report](https://github.com/greensiliconhero-coder/TestTrading/blob/experiment/neural-v2/experiments/v1/learning_report.md).

## Neural v2: first real neural-network experiment

- Data: preceding 60 minute OHLCV candles, normalized prices and relative volume. 181,670 training windows from 2021-2022; 89,530 validation windows from 2023; 88,590 common-sample 2024 development windows. Signals 10:15-14:45 every 30 minutes.
- Architecture: 1D CNN, 5 input channels, two 16-channel convolution layers with kernel 5 and GELU, global average pooling and one output; 1,729 trainable parameters. Predicts positive next-30-minute quote return, not calibrated net profit.
- Training: one architecture/seed (17), AdamW learning rate 0.001, weight decay 0.0001, batch 512, maximum 8 epochs, patience 2, training-only channel scaling. CPU, no paid GPU.
- Selection/execution assumptions: validation loss selects checkpoint; thresholds 0.50/0.55/0.60 require at least 1,000 validation trades. Same idealized quote timing and 20 bps cost diagnostic as the sequence comparison; no realistic portfolio/fill claim.
- Result: 3 epochs completed; epoch 1 retained. Validation AUC 0.507456. 2024 development AUC 0.505389 vs tree 0.515524 and constant 0.5. Validation threshold 0.50 generated 199 trades; 0.55 generated one; 0.60 generated none. No eligible threshold; no approved trading strategy.
- Persistence: best weights, input scales, model card and last optimizer checkpoint are saved. Exact save/reload prediction difference was 0.0. 2024 had already been observed in v1 and is not a fresh holdout.
- Evidence: [specification](https://github.com/greensiliconhero-coder/TestTrading/blob/experiment/neural-v2/NEURAL_V2.md), [results](https://github.com/greensiliconhero-coder/TestTrading/blob/experiment/neural-v2/experiments/v2/results.json), [report](https://github.com/greensiliconhero-coder/TestTrading/blob/experiment/neural-v2/experiments/v2/report.md), [saved bundle](https://github.com/greensiliconhero-coder/TestTrading/blob/experiment/neural-v2/models/neural_v2/bundle.json).

## Context v3: strategies actually performed

At each completed signal candle, evaluate three fixed hypotheses. Every family has one explicit rule, one standardized ridge return regressor (alpha 100), and one histogram gradient-boosted regressor (100 iterations, 15 leaves, learning rate 0.05, L2 10, minimum leaf 100, seed 31). Six final learned models plus three rule baselines; earlier chronological diagnostic models are also saved. No reinforcement learning, neural-network retraining or parameter sweep was performed in this version.

| Family | Event condition, using only completed signal-time inputs | Rule ranking |
|---|---|---|
| Continuation | Stock 30-minute return > 0; Nifty 50 30-minute return > 0; five-vs-30-minute stock volume ratio >= 1.2 | Highest stock 30-minute return |
| Reversal | Stock five-minute return < minus trailing 30-minute log-return volatility times sqrt(5); Nifty 50 30-minute return >= 0 | Largest negative five-minute move |
| Relative move | Stock minus Nifty 50 30-minute return > trailing stock volatility times sqrt(30); median other-index 30-minute return > 0 | Highest stock-minus-market return |

Regressors predict gross executable return. A learned candidate considers a trade only if its forecast exceeds estimated fees on a fixed INR 10,000 notional, 4 bps round-trip slippage, and a further 2 bps margin. Rules take all qualifying events subject to portfolio constraints. Candidate ranking and prediction never use future entry/exit fields or labels.

### Exact data and splits

- Sources: the 148 preserved stock files plus 225 Kite minute-history chunks for nine indices; 36 official Nifty daily year-series for independent date/high-low checks; corporate-action records. The full backup fingerprints 415 source payloads.
- Indices: NIFTY 50, BANK, IT, FMCG, AUTO, PHARMA, METAL, ENERGY and FIN SERVICE. All enter jointly; current sector memberships are not backdated into historical stock features.
- Features: eight stock features from v1, five past features per index (5/15/30-minute returns, since-open return and 30-minute volatility), prior-20-session time-of-day relative volume (minimum five past sessions), panel mean return/breadth, stock-minus-market return and median other-index return: 58 total.
- Eligibility: exact 375-minute regular sessions, no imputation; stock zero-volume sessions and corporate-action ex-dates excluded. Independent index daily high/low differences above 10 bps quarantine the whole date. The pre-screen table had 352,520 rows; 25,640 were quarantined, leaving 326,880 rows.

| Partition | Period | Rows | Sessions | Use |
|---|---|---:|---:|---|
| Training partition | 2021-2022 | 158,020 | 432 | Fit final models on each family's event subset; scalers training-only |
| Validation | 2023 | 81,410 | 224 | Frozen candidate-selection gate |
| Development comparison | 2024 | 87,450 | 245 | Report fixed candidates after selection; not a fresh holdout |
| Reserved | 2025 | Not accessed | Not accessed | Not used in this version |

An earlier diagnostic fit trains on 2021 and evaluates 2022 before the final 2021-2022 fit. Labels stay within one session/year. The source cohort and full-day quality screens are retrospective; these are exploratory results, not a point-in-time investable-universe test.

### Timing, capital, costs and selection constraints

- Ten signal times: 10:15 to 14:45 every 30 minutes. A signal uses candle t, enters at t+2 open (one full processing minute after candle completion), and exits at t+32 open, 30 minutes after entry.
- Illustrative initial capital INR 50,000; up to INR 10,000 per position; whole shares, at most five positions, long/cash only, no leverage. Exits settle before next-batch entries. Cash earns zero. This was not the owner's declared investment budget.
- Entry size capped at 1% of realized entry-bar volume. Exit-capacity failures are recorded, not silently discarded. This is an ex-post feasibility proxy; bid/ask, queues, actual fills and all intraday risks are not reconstructed.
- Base adverse slippage 2 bps per side; stress 5 bps per side. Brokerage min(INR 20, 0.03% of notional) each side; STT 0.025% sell; stamp 0.003% buy; SEBI 0.0001% both; GST 18% on brokerage/exchange/SEBI. Fees are estimated and unrounded; full contract-note/IPFT reconciliation is unresolved.
- Modeled exchange charge each side: 0.00345% from 2021-01-01; 0.00325% from 2023-04-01; 0.00322% from 2024-04-01; 0.00297% from 2024-10-01. These are historical experiment assumptions, not a statement of today's applicable fees.
- Select on 2023 only: at least 200 filled trades, positive net return, zero exit-capacity failures; then highest validation net return. Otherwise select cash. No 2024-based replacement of the selected outcome.
- Uncertainty: 2,000 circular block-bootstrap repetitions with five-session portfolio-return blocks; one-sided lower bounds and a nine-candidate Bonferroni adjustment. This does not correct every earlier project trial or retrospective data-selection bias.

### All context-v3 results

Net returns below are simulated portfolio returns on the stated initial capital, after modeled fees/slippage. They are not AUC, per-trade returns or guaranteed realizable returns. Baselines also have flagged execution-proxy failures; inspect full JSON before interpreting their paths.

| Candidate | 2022 diagnostic net | 2023 validation net | Validation trades | Validation exit-capacity failures | 2024 development net | 2024 stress net |
|---|---:|---:|---:|---:|---:|---:|
| continuation_rule | -78.6109% | -78.6755% | 3673 | 243 | -79.7501% | -90.6213% |
| continuation_ridge | -0.4818% | -0.2621% | 9 | 1 | 1.2410% | 0.9692% |
| continuation_tree | -0.6390% | -0.5976% | 11 | 2 | 0.0008% | -0.1979% |
| reversal_rule | -62.6741% | -65.1832% | 2886 | 241 | -66.2727% | -81.5068% |
| reversal_ridge | -0.2034% | -0.1589% | 10 | 3 | 0.7219% | 0.5048% |
| reversal_tree | -1.2335% | -0.8877% | 7 | 2 | 0.2435% | -0.1762% |
| relative_rule | -69.5019% | -69.7350% | 3061 | 195 | -78.1798% | -89.0686% |
| relative_ridge | 0.0483% | -0.2127% | 12 | 1 | -3.0241% | -3.4024% |
| relative_tree | -2.3514% | 0.2804% | 11 | 0 | -3.4463% | -3.6780% |

**Decision: cash / no qualifying trading strategy.** The only positive learned 2023 result was relative_tree (+0.2804%) with 11 trades, below the frozen minimum of 200. Later positive-looking 2024 candidates do not qualify retroactively. Rule baselines lost heavily after costs. No live deployment or profitable-product claim is supported.

### Material limitations

The fixed survivor cohort, whole-history eligibility checks, corporate-action screening and full-day source-disagreement exclusions use retrospective information. A full-day quality failure cannot be known at an earlier trade time and may remove volatile/difficult sessions. Historical security identity, adjustment consistency, point-in-time membership and execution costs are not fully independently certified. Daily official closing values need not equal final minute quotes. Drawdowns use daily closing equity and miss some intraday risk. The simulator omits queue dynamics, historical spreads, full market impact, exact fee rounding and complete liquidity/halting mechanics. These limits remain even when a number is positive.

## Evidence, exact trained-on data and restore

- [Executed protocol](https://github.com/greensiliconhero-coder/TestTrading/blob/experiment/context-v3-trained/CONTEXT_V3_PROTOCOL.md) and [frozen configuration](https://github.com/greensiliconhero-coder/TestTrading/blob/experiment/context-v3-trained/config/context_v3.json).
- [Quality-screen rule](https://github.com/greensiliconhero-coder/TestTrading/blob/experiment/context-v3-trained/config/context_v3_quality.json); [source manifest](https://github.com/greensiliconhero-coder/TestTrading/blob/experiment/context-v3-trained/experiments/v3/source_manifest.csv); [dataset fingerprint, splits and all 58 feature names](https://github.com/greensiliconhero-coder/TestTrading/blob/experiment/context-v3-trained/experiments/v3/dataset.json).
- [Full results with costs, turnover, drawdowns and uncertainty](https://github.com/greensiliconhero-coder/TestTrading/blob/experiment/context-v3-trained/experiments/v3/results.json); [plain-language report](https://github.com/greensiliconhero-coder/TestTrading/blob/experiment/context-v3-trained/experiments/v3/report.md); daily equity CSVs are in [the results directory](https://github.com/greensiliconhero-coder/TestTrading/tree/experiment/context-v3-trained/experiments/v3).
- [All saved final models](https://github.com/greensiliconhero-coder/TestTrading/blob/experiment/context-v3-trained/models/context_v3/candidates.joblib), [earlier diagnostic fits](https://github.com/greensiliconhero-coder/TestTrading/blob/experiment/context-v3-trained/models/context_v3/diagnostic_2021.joblib), [model card and dependency versions](https://github.com/greensiliconhero-coder/TestTrading/blob/experiment/context-v3-trained/models/context_v3/bundle.json).
- [Complete private training backup](https://github.com/greensiliconhero-coder/TestTrading/releases/tag/context-v3-trained): 369,759,440-byte ZIP, 536 hashed files and 415 original source payloads. Includes code, exact learning table, pre-screen table, targets, split labels, predictions, trades and models. Credentials are excluded.
- Inside that archive, `data/context_training_v3/samples.csv.gz` is the exact fitted/evaluated table. `samples_pre_quality.csv.gz` is retained for audit and was not the final fitted input. Each model uses its predefined event subset of the training partition.
- [Archive receipt and SHA-256](https://github.com/greensiliconhero-coder/TestTrading/blob/experiment/context-v3-trained/experiments/v3/archive_receipt.json). Remote archive digest/size and archive CRC were verified. Save/reload and fresh-process prediction differences were 0.0; portable model restore passed. All 38 tests passed on the completed training version.

The complete data lives in the private release, not as large blobs on every Git branch. Branch names and machine-readable fingerprints identify which snapshot was used. Historical tags and already published archives remain immutable; these README improvements are new branch commits.

## Run this branch

For the saved CNN, install `requirements-neural.txt`, then run:

```powershell
python src/neural_v2.py predict --csv examples/neural_v2_window.csv
```

This loads the saved CNN without fitting or orders. Local historical-data access uses `Run-KitePilot.ps1 -Login`; enter secrets only in hidden local prompts. For context-v3 inference, switch to its trained branch.

## Documentation required for every future version

Before fitting, commit the exact hypothesis, feature/target definitions, data/source fingerprints, chronological splits, numerical model parameters, candidate budget, execution/cost assumptions and acceptance/rejection rule. After execution, update that branch's README with all candidate results, exclusions, failures, decision, limitations, reproduction commands and artifact locations. Collection/proposal branches must say when no model was trained there. Keep failed versions; do not overwrite their outcomes, move historical tags or retune against an observed holdout without recording it. README-only updates do not retrain or alter model/data artifacts.
