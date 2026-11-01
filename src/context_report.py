"""Explain completed context-v3 results without changing any research choices."""
import json
from context_features import ROOT, RESULTS


def main():
    r=json.loads((RESULTS/'results.json').read_text())
    desc=r['dataset']
    lines=['# Context v3: completed bounded study','',r['verdict'],'',
        f'Selected on 2023: **{r["selected_on_2023"] or "cash / no eligible strategy"}**. Live deployment remains disabled. 2025 was not accessed.', '',
        '## Exact preserved learning inputs','',
        f'{desc["rows"]:,} rows, {len(desc["features"])} feature columns, {len(desc["symbols"])} companies.',
        f'Split rows: {desc["split_rows"]}. Split sessions: {desc["split_sessions"]}.',
        '`data/context_training_v3/samples.csv.gz` contains exact features, targets, split assignments and execution fields used for fitting and evaluation. `source_manifest.csv` fingerprints original source payloads; `dataset.json` fingerprints configuration, builder and table.', '',
        '## All nine candidates','',
        '| Candidate | 2022 diagnostic net | 2023 net | Validation trades | 2024 development net | 2024 stressed net |',
        '|---|---:|---:|---:|---:|---:|']
    for key,value in r['candidates'].items():
        lines.append(f'| {key} | {value["earlier_2022"]["net_total_return"]:.2%} | {value["validation_2023"]["net_total_return"]:.2%} | {value["validation_2023"]["trades"]} | {value["development_2024"]["net_total_return"]:.2%} | {value["development_2024_stress"]["net_total_return"]:.2%} |')
    lines += ['', 'Results use INR 50,000 illustrative initial capital, whole-share long positions, INR 10,000 position limits, at most five positions, historical estimated fees and 2 bps adverse slippage per side. Stress uses 5 bps per side. Cash earns zero. Returns are simulated portfolio results, not guaranteed fills or income.', '',
        '## Selection and uncertainty','',
        'The rule was committed before fitting: require at least 200 validation trades, positive validation net return and no exit-capacity proxy failures; then select highest validation net return. Otherwise choose cash. 2024 was already seen in previous research and is a development comparison, not a fresh holdout. Every candidate is reported; later profitable-looking development candidates cannot replace the validation choice.', '']
    if r['selected_on_2023']:
        candidate=r['candidates'][r['selected_on_2023']]
        lines += [f'Selected candidate 2024 close-to-close maximum drawdown: {candidate["development_2024"]["daily_close_max_drawdown"]:.2%}.',
            'Selected development block-bootstrap results: '+json.dumps(candidate['development_2024']['uncertainty']), '']
    lines += ['Five-session circular block-bootstrap bounds are in results.json for all candidates. The nine-candidate Bonferroni adjustment does not erase selection across earlier project versions. Small samples and regime dependence limit the inference.', '',
        '## Persistence and reproduction','',
        '- `models/context_v3/candidates.joblib`: all fitted final candidates, their preprocessing, features and selection outcome.',
        '- `models/context_v3/bundle.json`: model, data, configuration and training-code hashes.',
        '- Exact saved/reloaded prediction difference: '+str(r['save_reload_max_difference'])+'.',
        '- `python src/context_predict.py --csv examples/context_v3_features.csv` loads saved models without fitting.',
        '- `python src/context_models.py` detects completed results and checks model hash instead of retraining.', '',
        '## Material limitations','',
        'The cohort survives to the modern instrument list and was screened using its history. Corporate-action ex-dates, zero-volume stock sessions and incomplete index sessions are excluded retrospectively. Historical membership and all security adjustments are not independently certified. Four official daily-index samples provide checks, not complete historical verification. The comparison CSV records differences between official daily values and intraday aggregates; the official close need not equal the final minute quote.', '',
        'Bar-volume participation is an ex-post execution feasibility proxy. Historical spread, queue, market impact, exchange halts and actual fill availability are not known. Exit-capacity failures are counted rather than silently omitted. Estimated fees omit full contract-note reconciliation and may omit minor levies. Reported drawdowns use daily closes, not full intraday marks. These limitations prohibit treating a positive result as demonstrated deployable profitability.', '',
        'No hyperparameter sweep, reinforcement learning, neural-network retraining, paid compute or live orders was performed. The next decision must follow the evidence; a failed experiment should be retained and not retuned against the same comparison period.']
    (RESULTS/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines[:24]))


if __name__=='__main__':
    main()
