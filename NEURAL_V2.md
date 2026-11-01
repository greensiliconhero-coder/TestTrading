# First neural-network experiment: frozen protocol

One CPU convolutional neural network, one seed, at most eight epochs, and early stopping after two epochs without validation log-loss improvement of at least 0.00001. Architecture: 5 input channels, two 16-channel kernel-5 convolution/GELU layers, global average pooling, and one output logit. AdamW learning rate 0.001, weight decay 0.0001, batch size 512. Exact settings are committed in `config/neural_v2.json` before training.

Inputs are 60 consecutive minute candles within one regular session. OHLC channels are log ratios to the first close in that window. Volume is log(1 + volume / mean window volume), with a denominator floor of one. Channel mean/std are fitted only on 2021–2022 windows and saved with the model. Signals start at 10:15, every 30 minutes through 14:45; the earlier v1 09:45 signal is excluded because it lacks 60 minutes of same-session history. Labels run from next minute open to the close 30 minutes after the signal. The complete signal candle must be available before prediction.

2021–2022 trains, 2023 selects the epoch and threshold, and previously seen 2024 provides a development comparison only. 2025 is not accessed. The persisted v1 tree model is compared on the identical reduced set of timestamps; its parameters and 0.50 threshold stay fixed. Constant-probability baseline is estimated from training labels. Thresholds 0.50/0.55/0.60 use validation only with at least 1,000 selected examples; if none qualify, no rule is selected. A losing validation rule is not approved for trading. The illustrative 20 bp round-trip assumption remains unchanged.

This experiment inherits the screened survivor cohort, retrospective data-quality selection, omitted sessions, unverified corporate-action conventions, and idealized fills of v1. It cannot establish causal reasons or a deployable strategy. No additional seed/architecture search is permitted under this version. Record unsuccessful outcomes.

## Preserved model

`models/neural_v2/weights.pt` contains the best validation epoch. `bundle.json` saves scaling, architecture, data/code fingerprints, Git commit, dependency versions and weight checksum. `resume.pt` preserves the last completed epoch and optimizer state for an interrupted run. The named v1/v2 model weights and v2 checkpoint are tracked in Git alongside configuration, history, metrics and model cards. Other generated binaries stay ignored. An artifact ZIP provides an additional portable backup.

```powershell
python src/neural_v2.py prepare
python src/neural_v2.py train
python src/neural_v2.py predict --csv work/neural_v2/example_window.csv
```

`predict` loads the saved model and does not train. Supply exactly 60 consecutive OHLCV minute rows with timezone-aware `date` values. Predictions refer to quote-return direction, not probability of net profit. The program does not place orders. Calling `train` after completion verifies the saved model and skips retraining. An interrupted training command resumes from its last completed epoch only when data/code/config fingerprints match. A changed experiment requires a new version.

Windows dependencies: existing Python 3.10, NumPy 1.26.4, pandas 2.2.2, scikit-learn 1.7.1 and PyTorch 2.2.2+cpu. CPU thread count is four. Load only artifacts from this trusted project; weights are loaded with `weights_only=True`. Persistence is tested by exact prediction comparison before and after reload.
