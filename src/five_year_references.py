import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import context_sources as cs
import context_independent_daily as cd
from concurrent.futures import ThreadPoolExecutor
root=Path.cwd();cs.STAGE=root/'data/five_year_processing_v4/references';cd.STAGE=cs.STAGE
sources=[(f'nse_actions_{y}',f'https://www.nseindia.com/api/corporates-corporateActions?index=equities&from_date=01-01-{y}&to_date=31-12-{y}','json',None,'Ex-date records, not adjustment factors or point-in-time announcements.') for y in range(2021,2026)]
with ThreadPoolExecutor(max_workers=3) as pool: actions=list(pool.map(cs.fetch,sources))
(root/'experiments/five_year_v4/actions_manifest.json').write_text(json.dumps(actions,indent=2))
print('Actions',[(x['name'],x['status']) for x in actions],flush=True)
c=json.loads((root/'config/five_year_v4.json').read_text())
with ThreadPoolExecutor(max_workers=3) as pool: records=list(pool.map(cd.collect,[(s,y) for s in c['indices'] for y in range(2021,2026)]))
(root/'experiments/five_year_v4/official_daily_manifest.json').write_text(json.dumps(records,indent=2))
print('Official daily',sum(x['status']=='downloaded' for x in records),'/',len(records),flush=True)
