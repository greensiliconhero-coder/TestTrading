"""Research forecasts from preserved models; no fitting, authentication or orders."""
import argparse
import json
import joblib
import numpy as np
import pandas as pd
from context_models import MODELS, candidate_signals
from context_features import event_masks
from research_v1 import sha


def predict(path):
    card = json.loads((MODELS/'bundle.json').read_text())
    if sha(MODELS/'candidates.joblib')!=card['models_sha256']:
        raise ValueError('Model file checksum mismatch.')
    bundle = joblib.load(MODELS/'candidates.joblib')
    frame = pd.read_csv(path)
    required = bundle['features']+['symbol','day','signal_minute']
    if not set(required).issubset(frame.columns) or not np.isfinite(frame[bundle['features']].to_numpy()).all():
        raise ValueError('CSV requires finite prepared feature columns, symbol, day and signal_minute.')
    output = frame[['symbol','day','signal_minute']].copy()
    for key,model in bundle['models'].items():
        family = key.rsplit('_',1)[0]
        output[key+'_event'] = event_masks(frame)[family]
        if model['kind'] in {'ridge','tree'}:
            output[key+'_expected_gross_return'] = model['estimator'].predict(frame[bundle['features']])
        output[key+'_passes_research_gate'] = output.index.isin(candidate_signals(frame,model,family,bundle['features'],bundle['config']).index)
    return {'selected_candidate':bundle['chosen'],'deployment':'disabled','rows':output.to_dict('records'),
            'note':'Prepared features required; scores are not calibrated profit probabilities. No retraining or orders.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--csv',required=True)
    args=parser.parse_args()
    print(json.dumps(predict(args.csv),indent=2))
