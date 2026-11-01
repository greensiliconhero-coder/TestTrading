"""Summarize completed neural experiment; never changes training or selection."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'experiments/v2'
r=json.loads((folder/'results.json').read_text())
choice=r['selected_threshold']
stats=r['cnn_quote_trade_stats']
verdict='No adequately sampled validation trading rule was selected.'
if choice:
    verdict='No demonstrated after-cost trading edge.'
    if choice['mean_net_bps']>0 and stats['mean_net_bps']>0 and choice['execution_zero_volume']==0 and stats['execution_zero_volume']==0:
        verdict='Positive exploratory quote-return result; not approved for trading.'
lines=['# Neural network v2: trained and preserved', '', f'**{verdict}**', '',
       '## What was trained', '',
       '- A real one-dimensional convolutional neural network, using sequences of 60 minute OHLCV candles to predict the next 30-minute quote-return direction.',
       f'- {r["parameter_count"]:,} learned parameters; {r["training_rows"]:,} training windows; {r["validation_rows"]:,} validation windows.',
       f'- Completed {r["epochs_completed"]} epochs. Epoch {r["best_epoch"]} had the best validation loss and was preserved.',
       '- Trained on 2021–2022, selected on 2023. The 2024 comparison period was already seen in v1; it is not a fresh holdout. 2025 remains unused.',
       '- One architecture and one seed, as committed before training. No GPU or paid compute was used.', '',
       '## Comparison on identical 2024 examples', '',
       '| Metric | Neural network | Existing tree model | Constant probability |', '|---|---:|---:|---:|']
for metric in ['auc','brier','log_loss']:
    lines.append(f'| {metric} | {r["development_2024_metrics"][metric]:.6f} | {r["v1_tree_same_sample_metrics"][metric]:.6f} | {r["constant_same_sample_metrics"][metric]:.6f} |')
lines += ['', 'AUC near 0.5 means little direction-ranking ability. Lower Brier/log loss is better. These measures do not establish profitability.']
if stats:
    lines += ['',f'The threshold selected using 2023 was {choice["threshold"]:.2f}. Its 2023 mean net quote return was {choice["mean_net_bps"]:.3f} basis points under the illustrative 20 bp round-trip cost.',
              f'On 2024 it selected {stats["trades"]:,} hypothetical trades, averaging {stats["mean_gross_bps"]:.3f} bp before costs and {stats["mean_net_bps"]:.3f} bp after that assumed cost. This is not a portfolio return or an actual-fill simulation.',
              f'Zero-volume execution examples: validation {choice["execution_zero_volume"]}, comparison {stats["execution_zero_volume"]}.']
lines += ['', '## Saved model: no retraining needed', '',
          'Folder: `C:/Users/mayan/Documents/Codex/TradingResearch/models/neural_v2/`', '',
          '- `weights.pt`: the best trained neural-network weights.',
          '- `bundle.json`: input scaling, architecture, selected epoch, dependency versions and fingerprints.',
          '- `resume.pt`: optimizer and latest completed epoch for recovery from interrupted training.',
          f'- Before/after reload prediction difference: **{r["save_reload_max_difference"]}**.', '',
          'To make a prediction using the saved model:', '', '```powershell',
          'cd C:\\Users\\mayan\\Documents\\Codex\\TradingResearch',
          'python src/neural_v2.py predict --csv work/neural_v2/example_window.csv', '```', '',
          'The prediction command only loads the saved model. It does not train or place orders. For your own input, provide exactly 60 consecutive same-session minute candles with date, open, high, low, close and volume. The timestamp must include a timezone.', '',
          '## What this does not prove', '',
          'The model learns statistical associations, not why markets move. Data screening uses a surviving-stock cohort and hindsight; incomplete/special sessions are omitted; adjustment consistency is not fully independently verified. Quote-based entries/exits ignore realistic latency and fills. Calibration and cost assumptions need further work. A larger neural network is not automatically better.', '',
          'Live deployment and automatic promotion are disabled. Preserve these results even if disappointing. Do not tune against 2025; use it only after freezing a later experiment.']
(folder/'report.md').write_text('\n'.join(lines),encoding='utf-8')
print('\n'.join(lines[:18]))
