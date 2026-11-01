# Neural network v2: trained and preserved

**No adequately sampled validation trading rule was selected.**

## What was trained

- A real one-dimensional convolutional neural network, using sequences of 60 minute OHLCV candles to predict the next 30-minute quote-return direction.
- 1,729 learned parameters; 181,670 training windows; 89,530 validation windows.
- Completed 3 epochs. Epoch 1 had the best validation loss and was preserved.
- Trained on 2021–2022, selected on 2023. The 2024 comparison period was already seen in v1; it is not a fresh holdout. 2025 remains unused.
- One architecture and one seed, as committed before training. No GPU or paid compute was used.

## Comparison on identical 2024 examples

| Metric | Neural network | Existing tree model | Constant probability |
|---|---:|---:|---:|
| auc | 0.505389 | 0.515524 | 0.500000 |
| brier | 0.249889 | 0.249779 | 0.249893 |
| log_loss | 0.692926 | 0.692707 | 0.692934 |

AUC near 0.5 means little direction-ranking ability. Lower Brier/log loss is better. These measures do not establish profitability.

## Saved model: no retraining needed

Folder: `C:/Users/mayan/Documents/Codex/TradingResearch/models/neural_v2/`

- `weights.pt`: the best trained neural-network weights.
- `bundle.json`: input scaling, architecture, selected epoch, dependency versions and fingerprints.
- `resume.pt`: optimizer and latest completed epoch for recovery from interrupted training.
- Before/after reload prediction difference: **0.0**.

To make a prediction using the saved model:

```powershell
cd C:\Users\mayan\Documents\Codex\TradingResearch
python src/neural_v2.py predict --csv work/neural_v2/example_window.csv
```

The prediction command only loads the saved model. It does not train or place orders. For your own input, provide exactly 60 consecutive same-session minute candles with date, open, high, low, close and volume. The timestamp must include a timezone.

## What this does not prove

The model learns statistical associations, not why markets move. Data screening uses a surviving-stock cohort and hindsight; incomplete/special sessions are omitted; adjustment consistency is not fully independently verified. Quote-based entries/exits ignore realistic latency and fills. Calibration and cost assumptions need further work. A larger neural network is not automatically better.

Live deployment and automatic promotion are disabled. Preserve these results even if disappointing. Do not tune against 2025; use it only after freezing a later experiment.