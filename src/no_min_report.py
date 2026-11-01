"""Document the completed count-gate sensitivity without fitting anything."""
import json
from pathlib import Path
from no_min_trades import OUT, ROOT


def number(x):return 'no trades / undefined' if x is None else f'{x:.4f}'


def main():
    r=json.loads((OUT/'results.json').read_text())
    lines=['# Minimum-trade requirement removed: sensitivity results','',
        'Post-hoc sensitivity on preserved model snapshots. Only the minimum sample-count eligibility requirement was removed. Model weights, preprocessing, original thresholds, forecast/cost hurdles, costs, slippage, position sizes, execution checks and selection periods stayed unchanged. No retraining, real orders or 2025 access.', '',
        '## Selection changes','',
        '| Saved snapshot | Selection without minimum count | Selection-period result | Later comparison |',
        '|---|---|---|---|',
        '| v1 classifier | None passes positive validation net return | All original tree/logistic thresholds lose after 20 bps quote costs in 2023 | No qualified strategy to carry forward |',
        '| v2 best CNN | Probability-score threshold 0.55 | 1 trade in 2023; +126.7243 bps net on that quote trade | 0 trades in 2024 |',
        '| v3 final models trained 2021-2022 | relative_tree | 11 trades; +0.2804% portfolio return in 2023 | 22 trades; -3.4463% in 2024 |',
        '| v3 earlier diagnostic fits trained 2021 | relative_ridge, hypothetical selection on 2022 | 12 trades; +0.0483% in 2022 | 14 trades; -0.4856% in 2023; 42 trades; -0.4448% in 2024 |', '',
        'Portfolio comparisons each restart with the original illustrative INR 50,000 capital; they are not a continuously compounded multi-year run. CNN/classifier figures are averages per idealized quote trade, not portfolio returns. Zero trades do not provide a per-trade return estimate. No minimum quota is imposed on trade generation.', '',
        '## V1 preserved tree: all original thresholds','',
        '| Threshold | 2023 trades | 2023 mean net bps/trade | 2024 trades | 2024 mean net bps/trade |',
        '|---|---:|---:|---:|---:|']
    for threshold in [.5,.55,.6]:
        a=next(x for x in r['v1']['tree_replayed'] if x['year']=='2023' and x['threshold']==threshold)
        b=next(x for x in r['v1']['tree_replayed'] if x['year']=='2024' and x['threshold']==threshold)
        lines.append(f'| {threshold} | {a["trades"]} | {number(a["mean_net_bps"])} | {b["trades"]} | {number(b["mean_net_bps"])} |')
    lines+=['','The earlier logistic model weights were not preserved. Its historical 2023 validation results can be evaluated for the gate change without fitting it again:','',
        '| Threshold | Historical validation trades | Mean net bps/trade |','|---|---:|---:|']
    for row in r['v1']['logistic_historical_validation']:
        lines.append(f'| {row["threshold"]} | {row["trades"]} | {number(row["mean_net_bps"])} |')
    lines+=['','All logistic validation means are negative, so it has no profitable selection even without a count floor. No fresh logistic inference or later-year replay is claimed. The original v1 rank-only selector could name a least-negative candidate; the original profitability approval check still fails.','',
        '## CNN: all original thresholds','',
        '| Threshold | 2023 trades | 2023 mean net bps/trade | 2024 trades | 2024 mean net bps/trade |','|---|---:|---:|---:|---:|']
    for threshold in [.5,.55,.6]:
        a=next(x for x in r['neural_v2']['all_thresholds'] if x['year']=='2023' and x['threshold']==threshold)
        b=next(x for x in r['neural_v2']['all_thresholds'] if x['year']=='2024' and x['threshold']==threshold)
        lines.append(f'| {threshold} | {a["trades"]} | {number(a["mean_net_bps"])} | {b["trades"]} | {number(b["mean_net_bps"])} |')
    lines+=['','Threshold 0.55 is selected from 2023 only; the 2024 zero-activity result is not replaced by another threshold. Best-epoch selection remains fixed; the optimizer recovery checkpoint was not treated as a new candidate. The score is not a calibrated probability of net profit.','',
        '## All final context-v3 candidates','',
        '| Candidate | 2023 trades | 2023 net | Exit-capacity failures | Qualifies without count floor? | 2024 trades | 2024 net | 2024 stress net |',
        '|---|---:|---:|---:|---|---:|---:|---:|']
    for key,row in r['context_v3_final']['all_candidates'].items():
        a=row['validation_2023'];b=row['development_2024']
        yes=a['net_total_return']>0 and a['exit_capacity_failures']==0
        lines.append(f'| {key} | {a["trades"]} | {a["net_total_return"]:.4%} | {a["exit_capacity_failures"]} | {"yes" if yes else "no"} | {b["trades"]} | {b["net_total_return"]:.4%} | {row["development_2024_stress"]["net_total_return"]:.4%} |')
    lines+=['','Original final selection was cash. Dropping only the 200-trade requirement selects relative_tree. Replaying that fixed candidate reproduces the original candidate-level metrics exactly; the unchanged 2024 stressed net return is -3.6796% (see exact JSON value if rounded). All other candidates remain rejected on validation profitability or execution checks.','',
        '## All earlier diagnostic snapshots','',
        '| Candidate, fitted on 2021 | 2022 trades | 2022 net | 2022 exit failures | 2023 trades | 2023 net | 2024 trades | 2024 net |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for key,row in r['context_v3_diagnostic']['all_candidates'].items():
        a=row['selection_period_2022'];b=row['later_2023'];c=row['later_2024']
        lines.append(f'| {key} | {a["trades"]} | {a["net_total_return"]:.4%} | {a["exit_capacity_failures"]} | {b["trades"]} | {b["net_total_return"]:.4%} | {c["trades"]} | {c["net_total_return"]:.4%} |')
    lines+=['','The diagnostic selection is hypothetical: those earlier models were originally reported as diagnostics, not selected for deployment. Applying the common count floor of 200 selects cash; removing it selects relative_ridge from 2022. Later metrics use the unchanged earlier weights, not the newer 2021-2022 fit.','',
        '## Reproduction, scope and limitations','',
        '- `src/no_min_trades.py` replays saved models and verifies model hashes before/after. It contains no training calls. `config/no_min_trades.json` was committed before this replay.',
        '- `results.json` records all summaries and model fingerprints. Adjacent CSVs preserve selected trade records and daily equity plus CNN trades at each original threshold.',
        '- Three policy tests passed: one observation can qualify, no activity/negative net return cannot demonstrate profit, and execution checks remain active after removing the count gate.',
        '- Original data, models, reports and selection outcomes are not overwritten. Existing inference bundles still record their original selection; this sensitivity reports counterfactual choices separately.',
        '- Earlier dataset and execution limitations still apply: retrospective survivor/quality screening, estimated fees, idealized classifier fills and ex-post bar-volume capacity proxies. Every later period here was already observed; this is not fresh validation.',
        '- Original thresholds are held fixed. No later-period winner is substituted for the selection-period choice. 2025 remains reserved.', '',
        '**Conclusion:** removing the minimum count admits rare apparent winners, but none of the newly admitted selections demonstrates repeatable profitable activity in its later comparison periods. This result does not establish that rare trading is inherently bad; it shows that the sample-count gate was not the only obstacle for these saved models.']
    # Derive the displayed stress figure from the exact stored result.
    stress=r['context_v3_final']['all_candidates']['relative_tree']['development_2024_stress']['net_total_return']
    text='\n'.join(lines).replace('-3.6796%',f'{stress:.4%}')+'\n'
    (OUT/'report.md').write_text(text,encoding='utf-8')
    print('\n'.join(lines[:15]))


if __name__=='__main__':main()
