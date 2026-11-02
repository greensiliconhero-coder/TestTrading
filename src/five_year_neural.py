"""CPU sequence CNN with persistent checkpoints, inference and frozen evaluation."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import numpy as np
import pandas as pd
import torch
from torch import nn
from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss
from research_v1 import ROOT, sha, FEATURES, trade_stats
from kite_repair import atomic_write, encoded

CONFIG = ROOT / 'config/neural_v4.json'
WORK = ROOT / 'data/classifiers_v4'
BUNDLE = ROOT / 'models/neural_v4'
RESULTS = ROOT / 'experiments/neural_v4'


def window_features(candles):
    a = np.asarray(candles, dtype=np.float64)
    if a.shape != (60, 5) or not np.isfinite(a).all() or (a[:, :4] <= 0).any() or (a[:, 4] < 0).any():
        raise ValueError('Expected 60 finite positive OHLC candles and nonnegative volume.')
    if (a[:,1] < a[:,:4].max(axis=1)).any() or (a[:,2] > a[:,:4].min(axis=1)).any():
        raise ValueError('Inconsistent OHLC in input window.')
    # Uses only this past window; no future price or global dataset statistics.
    prices = np.log(a[:,:4] / a[0,3])
    volume = np.log1p(a[:,4] / max(a[:,4].mean(), 1.0))
    return np.column_stack([prices,volume]).T.astype(np.float32)


class SequenceCNN(nn.Module):
    def __init__(self, hidden=16):
        super().__init__()
        self.net = nn.Sequential(nn.Conv1d(5,hidden,5,padding=2),nn.GELU(),
                                 nn.Conv1d(hidden,hidden,5,padding=2),nn.GELU(),
                                 nn.AdaptiveAvgPool1d(1),nn.Flatten(),nn.Linear(hidden,1))

    def forward(self, x):
        return self.net(x).squeeze(1)


def save_torch(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.pending')
    torch.save(value, temporary)
    os.replace(temporary,path)


def prepare():
    from five_year_classifiers import prepare as build
    build()


def probabilities(model, x, indices, mean, std, batch=1024):
    model.eval(); values=[]
    with torch.inference_mode():
        for start in range(0,len(indices),batch):
            data=(np.asarray(x[indices[start:start+batch]])-mean)/std
            values.append(torch.sigmoid(model(torch.from_numpy(data))).numpy())
    return np.concatenate(values)


def load_bundle(folder=BUNDLE):
    card=json.loads((folder/'bundle.json').read_text())
    if sha(folder/'weights.pt')!=card['weights_sha256']: raise ValueError('Saved model checksum mismatch.')
    model=SequenceCNN(card['config']['hidden_channels'])
    model.load_state_dict(torch.load(folder/'weights.pt',map_location='cpu',weights_only=True))
    model.eval()
    mean=np.array(card['normalization_mean'],dtype=np.float32).reshape(1,5,1)
    std=np.array(card['normalization_std'],dtype=np.float32).reshape(1,5,1)
    return model,mean,std,card


def predict_csv(csv_path, folder=BUNDLE):
    frame=pd.read_csv(csv_path)
    stamps=pd.to_datetime(frame.date,format='ISO8601',utc=True).dt.tz_convert('Asia/Kolkata')
    if len(frame)!=60 or stamps.dt.date.nunique()!=1 or not (stamps.diff().dropna().dt.total_seconds()==60).all():
        raise ValueError('Prediction needs exactly 60 consecutive minute candles in one session.')
    minute=stamps.dt.hour*60+stamps.dt.minute
    if not minute.between(555,929).all() or stamps.dt.second.any(): raise ValueError('Use regular minute-start candles.')
    model,mean,std,card=load_bundle(folder)
    x=window_features(frame[['open','high','low','close','volume']].to_numpy())[None,:,:]
    prob=float(probabilities(model,x,np.array([0]),mean,std)[0])
    return {'probability_of_positive_quote_return':prob,'model_version':card['config']['version'],
            'note':'Research prediction only; not calibrated profit probability or an instruction to trade.'}


def train():
    torch.set_num_threads(4)
    config=json.loads(CONFIG.read_text())
    if (RESULTS/'results.json').exists():
        load_bundle()
        print('Completed model already exists and passes checksum loading. No retraining.'); return
    ds=json.loads((WORK/'dataset.json').read_text())
    if ds['sequences_sha256']!=sha(WORK/'sequences.npy') or ds['metadata_sha256']!=sha(WORK/'metadata.csv'):
        raise ValueError('Dataset/config fingerprint changed.')
    x=np.load(WORK/'sequences.npy',mmap_mode='r')
    meta=pd.read_csv(WORK/'metadata.csv')
    years=meta.day.str[:4].astype(int)
    ti=np.flatnonzero(years.isin(config['training_years']))
    vi=np.flatnonzero(years==config['validation_year'])
    di=np.flatnonzero(years==config['development_comparison_year'])
    if not years.isin([2021,2022,2023,2024,2025]).all(): raise ValueError('Unexpected period.')
    y=(meta.future_return.to_numpy()>0).astype(np.float32)
    # Channel scalers fit on training windows only.
    train_x=np.asarray(x[ti])
    mean=train_x.mean(axis=(0,2),dtype=np.float64).astype(np.float32).reshape(1,5,1)
    std=train_x.std(axis=(0,2),dtype=np.float64).clip(1e-6).astype(np.float32).reshape(1,5,1)
    del train_x
    torch.manual_seed(config['seed']); torch.use_deterministic_algorithms(True)
    model=SequenceCNN(config['hidden_channels'])
    optimizer=torch.optim.AdamW(model.parameters(),lr=config['learning_rate'],weight_decay=config['weight_decay'])
    criterion=nn.BCEWithLogitsLoss()
    best=float('inf'); stale=0; history=[]; first=1; best_epoch=0
    BUNDLE.mkdir(parents=True,exist_ok=True); RESULTS.mkdir(parents=True,exist_ok=True)
    signature={'config_sha256':sha(CONFIG),'code_sha256':sha(Path(__file__)),'dataset_sha256':sha(WORK/'dataset.json')}
    checkpoint=BUNDLE/'resume.pt'
    if checkpoint.exists():
        saved=torch.load(checkpoint,map_location='cpu',weights_only=True)
        if saved['signature']!=signature: raise ValueError('Checkpoint belongs to different code/data/config.')
        model.load_state_dict(saved['model']); optimizer.load_state_dict(saved['optimizer'])
        best,stale,history,first,best_epoch=saved['best'],saved['stale'],saved['history'],saved['epoch']+1,saved['best_epoch']
        print(f'Resuming from completed epoch {first-1}',flush=True)
    for epoch in range(first,config['epochs']+1):
        if stale>=config['patience']: break
        started=time.monotonic(); model.train(); total=0.0
        order=np.random.default_rng(config['seed']+epoch).permutation(ti)
        for start in range(0,len(order),config['batch_size']):
            idx=order[start:start+config['batch_size']]
            batch=torch.from_numpy((np.asarray(x[idx])-mean)/std)
            optimizer.zero_grad(set_to_none=True)
            loss=criterion(model(batch),torch.from_numpy(y[idx]))
            loss.backward(); optimizer.step(); total+=float(loss.detach())*len(idx)
        vp=probabilities(model,x,vi,mean,std)
        score=float(log_loss(y[vi],vp,labels=[0,1]))
        improved=score<best-config['minimum_improvement']
        if improved:
            best,stale,best_epoch=score,0,epoch
            save_torch(BUNDLE/'weights.pt',model.state_dict())
        else: stale+=1
        row={'epoch':epoch,'training_loss':total/len(ti),'validation_log_loss':score,'elapsed_seconds':time.monotonic()-started,'selected':improved}
        history.append(row); print(json.dumps(row),flush=True)
        save_torch(checkpoint,{'model':model.state_dict(),'optimizer':optimizer.state_dict(),'epoch':epoch,'best_epoch':best_epoch,
                             'best':best,'stale':stale,'history':history,'signature':signature})
        atomic_write(RESULTS/'training_history.json',encoded(history))
    model.load_state_dict(torch.load(BUNDLE/'weights.pt',map_location='cpu',weights_only=True))
    vp=probabilities(model,x,vi,mean,std)
    candidates=[dict(threshold=t,**trade_stats(meta.iloc[vi],vp>=t,config['assumed_cost_bps'])) for t in config['thresholds']]
    eligible=[c for c in candidates if c['trades']>0 and c['mean_net_bps']>0 and c['execution_zero_volume']==0]
    choice=max(eligible,key=lambda c:c['mean_net_bps']) if eligible else None
    # All model/threshold selection is complete before the previously observed 2024 comparison.
    atomic_write(RESULTS/'locked_selection.json',encoded({'selected_threshold':choice}))
    dp=probabilities(model,x,di,mean,std)
    def metrics(truth,p):
        return {'auc':float(roc_auc_score(truth,p)),'brier':float(brier_score_loss(truth,p)),'log_loss':float(log_loss(truth,p,labels=[0,1]))}
    import joblib
    baseline=joblib.load(ROOT/'models/classifiers_v4/hist_gradient_boosting.joblib')
    bp=baseline.predict_proba(meta.iloc[di][FEATURES])[:,1]
    result={'config':config,'signature':signature,'training_rows':len(ti),'validation_rows':len(vi),'comparison_rows':len(di),
            'parameter_count':sum(p.numel() for p in model.parameters()),'epochs_completed':len(history),'best_epoch':best_epoch,
            'validation_metrics':metrics(y[vi],vp),'validation_thresholds':candidates,'selected_threshold':choice,
            'test_2025_metrics':metrics(y[di],dp),'v4_tree_same_sample_metrics':metrics(y[di],bp),
            'constant_same_sample_metrics':metrics(y[di],np.full(len(di),y[ti].mean())),
            'cnn_quote_trade_stats':None if choice is None else trade_stats(meta.iloc[di],dp>=choice['threshold'],config['assumed_cost_bps']),
            'v4_tree_quote_trade_stats':trade_stats(meta.iloc[di],bp>=0.5,config['assumed_cost_bps']),
            'deployment':'disabled','2025_used':True}
    card={'config':config,'normalization_mean':mean.flatten().tolist(),'normalization_std':std.flatten().tolist(),
          'weights_sha256':sha(BUNDLE/'weights.pt'),'best_epoch':best_epoch,'signature':signature,
          'torch_version':str(torch.__version__),'numpy_version':np.__version__,'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
          'interpretation':'P(positive next-30-minute quote return), not causal explanation or net-profit guarantee.'}
    atomic_write(BUNDLE/'bundle.json',encoded(card))
    # Reload the persisted weights and scalers, then verify identical prediction values.
    reloaded,rm,rs,_=load_bundle()
    before=probabilities(model,x,di[:16],mean,std)
    after=probabilities(reloaded,x,di[:16],rm,rs)
    if not np.array_equal(before,after): raise ValueError('Saved model reload changed predictions.')
    result['save_reload_max_difference']=float(np.max(np.abs(before-after)))
    atomic_write(RESULTS/'results.json',encoded(result))
    atomic_write(RESULTS/'model_card.json',encoded(card))
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['prepare','train','predict'])
    parser.add_argument('--csv',type=Path)
    args=parser.parse_args()
    if args.command=='prepare': prepare()
    elif args.command=='train': train()
    elif args.csv: print(json.dumps(predict_csv(args.csv),indent=2))
    else: parser.error('--csv is required for prediction')
