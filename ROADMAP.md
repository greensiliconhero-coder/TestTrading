# Research roadmap and versioning

## Completed: v0.1.0-baseline

First Git snapshot of the work already completed: data audit, staged Kite downloads and browser login, data comparison, copied screened minute files, logistic/tree models and exploratory results. Earlier development was not individually committed; this snapshot does not invent earlier history. No useful after-cost edge was demonstrated.

## Next: v0.2.0 sequence-data pipeline

Build sequences of the preceding 60 minute candles with normalized OHLC and volume. Keep source values unchanged; fit any learned scaling only on training data. Restrict windows and 30-minute labels to one complete session. Use the same eligible companies and decision times when comparing with the baseline; the longer context may require a smaller common sample, which must be reported.

Tests must show that future candles cannot affect an earlier input, labels do not overlap split boundaries, windows cannot cross sessions, and model inputs can be reproduced from source checksums. Record all excluded examples and dataset/config/code fingerprints. Commit this pipeline before model selection.

## Then: v0.3.0 first neural network

Use one small one-dimensional convolutional neural network. It will learn patterns across the candle sequence rather than relying only on eight engineered features. It is supervised learning from future-return labels, not causal discovery or autonomous trading.

Before training, commit architecture, seed, learning rate, maximum epochs, stopping rule, validation metric and a small fixed experiment budget. Start on CPU. Do not rent GPUs unless measured runtime justifies it and the owner approves spending. Log unsuccessful runs as well as successful ones. Save model weights outside Git with checksums and a model card inside Git.

Train with 2021–2022; select/early-stop with 2023. Compare the network, logistic/tree baselines and constant-probability/no-trade alternatives on a common sample. 2024 is already observed: it can supply a development comparison but must never be described as a new holdout. Do not tune using 2025. No promise that a neural network will improve results.

## v0.4.0 execution and robustness

Before a final evaluation, specify an execution simulator that accounts for delayed orders, unavailable fills, spreads, costs, position sizing and simultaneous exposures. Current quote-return averages are not portfolio returns. Validate calendar, historical security identity and adjustment assumptions to the level required by the chosen strategy. Evaluate per-stock/per-period concentration and uncertainty. Record a reject/defer decision when evidence fails.

## Final evaluation gate

Only after freezing the research choices should the reserved 2025 window be evaluated. It ends on 3 October 2025 in the supplied data and is not a full-year test. Whole-history data screening and survivor-universe bias remain limitations even with an untouched outcome period. A failed holdout is not permission to repeatedly retune against it. New changes require new forward evidence.

## Version-control workflow

- Use a descriptive branch for each meaningful change, such as `experiment/sequence-v2`.
- Commit working, tested implementation increments and experiment protocols before running model selection.
- Commit compact results under `experiments/vN/` separately from implementation. Include command, dependency versions, data fingerprint, config, metrics and limitations.
- Tag completed milestones. Keep unsuccessful versions; never rewrite them into successes.
- Data copies, raw downloads, credentials, generated caches and large model weights remain local and ignored. A Git checkout alone does not recreate excluded data; use dataset manifests and local artifacts.
- No remote repository is configured. Publishing requires a destination and review for private paths/data and licensing.

Useful local commands:

```powershell
git log --oneline --decorate
git show v0.1.0-baseline --stat
git diff v0.1.0-baseline HEAD
git status
```

## Owner's challenge points

Ask whether the result is truly out of sample, survives actual costs, depends on a few stocks/days, uses hindsight in data selection, and assumes fills that were impossible. Ask what would cause rejection before authorizing more experiments. Feature importance is association, not an explanation of market causes.

Owner involvement is needed for fresh local login, data not already accessible, paid compute/data purchases, publication, and any move toward trading real money. Ordinary code changes, local analysis and tests can proceed under the existing project authorization.
