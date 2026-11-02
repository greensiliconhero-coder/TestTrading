"""Sequential local v4 processing/training continuation with durable stage status."""
import json
import subprocess
import sys
import time
from pathlib import Path
from kite_repair import atomic_write, encoded

ROOT=Path(__file__).resolve().parents[1]
STATUS=ROOT/'experiments/five_year_v4/run_status.json'


def status(stage, state, **details):
    atomic_write(STATUS,encoded(dict(stage=stage,state=state,**details)))


def run(stage,args):
    status(stage,'running')
    with (ROOT/'work'/f'five_year_{stage}.log').open('w',encoding='utf-8') as output:
        result=subprocess.run([sys.executable,'-u',*args],cwd=ROOT,stdout=output,stderr=subprocess.STDOUT)
    if result.returncode:
        status(stage,'failed',exit_code=result.returncode)
        raise SystemExit(result.returncode)
    status(stage,'complete')


def main():
    status('snapshot_audit','waiting_for_existing_process')
    deadline=time.monotonic()+7200
    while not (ROOT/'experiments/five_year_v4/snapshot_audit.json').exists():
        if time.monotonic()>deadline:
            status('snapshot_audit','timed_out');return
        time.sleep(10)
    run('quality',['src/five_year_quality.py'])
    run('classifier_prepare',['src/five_year_classifiers.py','prepare'])
    run('context_prepare',['src/five_year_context_features.py'])
    # Branch change happens only after the input datasets are fully prepared.
    subprocess.run(['git','switch','-c','experiment/five-year-v4'],cwd=ROOT,check=True)
    run('classifier_train',['src/five_year_classifiers.py','train'])
    run('neural_train',['src/five_year_neural.py','train'])
    run('context_train',['src/five_year_context_models.py'])
    status('models_and_tests','complete_pending_review_and_backup')
    paths=['experiments/classifiers_v4/results.json','experiments/neural_v4/results.json','experiments/v4/results.json']
    results={p:json.loads((ROOT/p).read_text()) for p in paths}
    atomic_write(ROOT/'experiments/five_year_v4/all_model_results.json',encoded(results))
    readme=ROOT/'README.md'
    text=readme.read_text(encoding='utf-8')
    text=text.replace('Branch: `processing/five-year-v4`.','Branch: `experiment/five-year-v4`.')
    text=text.replace('Current status: snapshot audit running; model preparation/training pending. No v4 performance results exist yet.','Current status: processing, sequential model fits and tests completed. Detailed review and external artifact backup pending. Results: `experiments/classifiers_v4/results.json`, `experiments/neural_v4/results.json`, and `experiments/v4/results.json`. Exact fitted tables live in `data/classifiers_v4` and `data/context_training_v4`; weights and scalers live in the corresponding `models/*_v4` folders.')
    readme.write_text(text,encoding='utf-8')


if __name__=='__main__':
    try:main()
    except Exception as exc:
        status('runner','failed',error_type=type(exc).__name__)
        raise
