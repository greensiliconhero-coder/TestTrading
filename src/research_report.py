"""Describe a completed experiment without modifying or selecting its model."""
import json
from pathlib import Path
import pandas as pd
import numpy as np
from research_v1 import ROOT

folder=ROOT/'outputs/research_v1'
c=json.loads((folder/'curation.json').read_text())
r=json.loads((folder/'model_results.json').read_text())
chosen=r['chosen_on_validation']
m=r['test_metrics']
pred=pd.read_csv(folder/'test_predictions.csv')
selected=pred.loc[pred.selected_by_rule]
stock=selected.groupby('symbol').agg(trades=('future_return','size'),mean_gross_return=('future_return','mean'))
stock['mean_net_bps_at_20']=stock.mean_gross_return*10000-20
stock.to_csv(folder/'test_by_stock.csv')
daily=selected.groupby('day').future_return.agg(['sum','count']).sort_index()
# Five-observed-day moving blocks retain short-range dependence. Conditional on the chosen cohort and rule.
ci=None
if len(daily)>=10:
    rng=np.random.default_rng(7)
    a=daily.to_numpy()
    means=[]
    for _ in range(1000):
        starts=rng.integers(0,len(a)-4,size=int(np.ceil(len(a)/5)))
        indices=np.concatenate([np.arange(s,s+5) for s in starts])[:len(a)]
        batch=a[indices]
        means.append(batch[:,0].sum()/batch[:,1].sum()*10000-20)
    ci=[float(x) for x in np.quantile(means,[.025,.975])]
    (folder/'conditional_uncertainty.json').write_text(json.dumps({'net_bps_95_percent_interval':ci,'method':'1000 moving-block resamples of five observed days','limitations':'Conditional on fixed model, universe and quote-fill assumptions; not protection against structural data errors or selection bias.'},indent=2))

verdict='No demonstrated trading edge after the assumed costs.'
if chosen['mean_net_bps']>0 and m['selected_rule']['mean_net_bps']>0:
    verdict='Positive exploratory result under assumed costs; independent validation and execution modelling are still required.'
lines=['# First minute-data learning experiment', '', f'**Result: {verdict}**', '',
       '## What was built', '',
       f'- Copied {c["copied_files"]} source files for {c["company_count"]} companies into `C:/Users/mayan/Documents/Codex/TradingResearch/data/curated_minute_v1/`.',
       '- Every copy was verified by SHA-256. Original files were not changed.',
       f'- Generated {c["examples"]:,} examples from minute candles; omitted {c["omitted_sessions"]} nonstandard/incomplete sessions without filling them.',
       '- Trained on 2021–2022, selected on 2023, evaluated on 2024. No 2025 prices or outcomes were used in learning/evaluation.',
       '- The model predicts the next 30-minute direction. It learns associations, not causal explanations.', '',
       '## Results', '', '| Measure | Result |', '|---|---:|',
       f'| Selected model | {chosen["model"]} |',f'| Selected threshold | {chosen["threshold"]:.2f} |',
       f'| Validation average net return per hypothetical trade | {chosen["mean_net_bps"]:.3f} bps |',
       f'| Test AUC (0.5 is random ranking) | {m["test_auc"]:.4f} |',
       f'| Test probability Brier score (lower is better) | {m["test_brier"]:.5f} |',
       f'| Constant-probability baseline Brier | {m["constant_probability_brier"]:.5f} |',
       f'| Hypothetical selected test trades | {m["selected_rule"]["trades"]:,} |',
       f'| Test average gross return per hypothetical trade | {m["selected_rule"]["mean_gross_bps"]:.3f} bps |',
       f'| Test average net return with 20 bps costs | {m["selected_rule"]["mean_net_bps"]:.3f} bps |',
       f'| Always-long same-times baseline, net | {m["always_long_same_times"]["mean_net_bps"]:.3f} bps |',
       f'| Selected test trades with zero-volume execution bars | {m["selected_rule"]["execution_zero_volume"]} |', '',
       'One basis point (bp) is 0.01%. The 20 bp round-trip cost is a declared illustrative assumption, not a verified brokerage/slippage estimate. These are average hypothetical trade returns, not account or annual returns.', '',
       '## Cost sensitivity', '', '| Round-trip cost | Test mean net return per trade |', '|---|---:|']
for cost,stats in r['cost_sensitivity'].items():
    lines.append(f'| {cost} bps | {stats["mean_net_bps"]:.3f} bps |')
if ci:
    lines += ['', f'Conditional 95% block-bootstrap interval at 20 bps costs: {ci[0]:.3f} to {ci[1]:.3f} bps per hypothetical trade. It accounts for some day clustering, but not universe bias, data errors, or unrealistic fills.']
lines += ['', '## Excluded companies', '']
lines += [f'- {symbol}: {reason}' for symbol,reason in sorted(c['excluded_companies'].items())]
lines += ['', '## What you should challenge', '',
          '1. **Unseen data:** was this evaluated after all model choices were fixed? Here the model and threshold used validation only. Do not retune against these 2024 results.',
          '2. **Costs and fills:** can the claimed opening/closing prices actually be traded? Here they are idealized quotes, not verified fills. No live return claim is justified.',
          '3. **Data selection:** would the result survive missing stocks and excluded sessions? The supplied survivor cohort and whole-history cleaning create retrospective selection.',
          '4. **Evidence versus explanation:** importance scores are predictive associations, not reasons markets move. A confident model can be confidently wrong.',
          '5. **Baseline:** does complexity beat simple alternatives and doing nothing? A positive directional score is insufficient if average net trades lose money.',
          '6. **Stopping:** negative validation results are a reason to reject deployment, not to keep trying thresholds on the test set until one wins.', '',
          '## Data investigation carried forward', '',
          'ADANIENT pilot revisions closely match the published rights factor 0.969485: all 1,504 compared price fields are within 0.051 rupees of that factor. This supports a corporate-action explanation; it does not certify all historical records. The company remains excluded from this first frozen cohort.',
          '[Zerodha rights-adjustment bulletin](https://zerodha.com/marketintel/bulletin/433585/adjustment-of-futures-and-options-contracts-of-adanient-due-to-rights-issue)', '',
          'Zerodha documents opening-price corrections using exchange pre-market prices. That is a plausible explanation for first-minute conventions, not confirmation of the seven specific inconsistent candles. Those companies remain excluded.',
          '[Zerodha opening-price documentation](https://support.zerodha.com/category/trading-and-markets/charts-and-orders/charts/articles/value-of-historical-candles-on-refresh)', '',
          'ITC daily-versus-minute revision differences remain unresolved. The attempted public NSE archive download timed out, so no independent exchange-data certification is claimed.', '',
          '## Boundaries', '',
          'Live trading and automatic model promotion remain disabled. No GPU spending, subscriptions or external messages were initiated. Further experiments must be versioned and count the 2024 results as already observed; 2025 remains reserved for a later final check.']
(folder/'learning_report.md').write_text('\n'.join(lines),encoding='utf-8')
print('\n'.join(lines[:30]))
