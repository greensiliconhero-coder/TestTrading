"""Apply frozen, outcome-blind independent-source quality quarantine."""
import json
import shutil
from pathlib import Path
import pandas as pd
from context_features import ROOT, FOLDER, RESULTS
from research_v1 import sha


def main():
    if (FOLDER/'dataset_pre_quality.json').exists():
        raise ValueError('Quality screen already applied; preserve this version.')
    quality = ROOT/'config/context_v3_quality.json'
    config = json.loads(quality.read_text())
    daily = ROOT/'experiments/context_sources_v1/official_daily_comparison.csv'
    comparison = pd.read_csv(daily)
    errors = comparison[['high_difference_bps','low_difference_bps']].abs().max(axis=1)
    dates = sorted(comparison.loc[errors>config['maximum_daily_index_high_low_disagreement_bps'],'day'].unique())
    before = json.loads((FOLDER/'dataset.json').read_text())
    if sha(FOLDER/'samples.csv.gz')!=before['dataset_sha256']:
        raise ValueError('Original feature table changed.')
    data = pd.read_csv(FOLDER/'samples.csv.gz')
    # The filter uses only source disagreement and date, never return labels.
    omitted = data.loc[data.day.isin(dates),['day','symbol','signal_minute']]
    filtered = data.loc[~data.day.isin(dates)]
    shutil.copyfile(FOLDER/'samples.csv.gz',FOLDER/'samples_pre_quality.csv.gz')
    shutil.copyfile(FOLDER/'dataset.json',FOLDER/'dataset_pre_quality.json')
    filtered.to_csv(FOLDER/'samples.csv.gz',index=False,float_format='%.12g',compression={'method':'gzip','mtime':0})
    omitted.to_csv(FOLDER/'independent_quality_omitted_rows.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    source_manifest = pd.read_csv(FOLDER/'source_manifest.csv')
    source_rows = []
    for record in json.loads((ROOT/'experiments/context_sources_v1/official_daily_manifest.json').read_text()):
        if record['status']!='downloaded' or sha(ROOT/record['path'])!=record['sha256']:
            raise ValueError('Independent daily source missing or changed.')
        source_rows.append({'path':record['path'],'sha256':record['sha256'],'role':'independent_daily_quality_screen'})
    source_rows.append({'path':daily.relative_to(ROOT).as_posix(),'sha256':sha(daily),'role':'independent_quality_comparison'})
    pd.concat([source_manifest,pd.DataFrame(source_rows)],ignore_index=True).to_csv(FOLDER/'source_manifest.csv',index=False)
    desc = dict(before)
    desc.update(rows=len(filtered),split_rows=filtered.split.value_counts().to_dict(),
        split_sessions=filtered.groupby('split').day.nunique().to_dict(),
        dataset_sha256=sha(FOLDER/'samples.csv.gz'),source_manifest_sha256=sha(FOLDER/'source_manifest.csv'),
        source_count=len(source_manifest)+len(source_rows),quality_config_sha256=sha(quality),
        finalizer_sha256=sha(Path(__file__)),pre_quality_dataset_sha256=before['dataset_sha256'],
        quarantined_dates=dates,quality_removed_rows=len(omitted),
        retrospective_quality_screen=True,independent_provider_calendar_compared=True,
        independent_prices_certified=False)
    (FOLDER/'dataset.json').write_text(json.dumps(desc,indent=2)+'\n')
    (RESULTS/'dataset.json').write_text(json.dumps(desc,indent=2)+'\n')
    print(json.dumps({k:desc[k] for k in ['rows','split_rows','split_sessions','quality_removed_rows','source_count']},indent=2))


if __name__=='__main__':
    main()
