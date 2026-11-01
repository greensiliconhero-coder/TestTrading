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

CONFIG = ROOT / 'config/neural_v2.json'
WORK = ROOT / 'work/neural_v2'
BUNDLE = ROOT / 'models/neural_v2'
RESULTS = ROOT / 'experiments/v2'


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
    WORK.mkdir(parents=True,exist_ok=True)
    if (WORK/'dataset.json').exists():
        print('Sequence dataset already exists; use the saved version.'); return
    base=pd.read_pickle(ROOT/'work/research_v1_samples.pkl')
    base=base.loc[base.signal_minute>=615].copy()
    manifest=pd.read_csv(ROOT/'outputs/research_v1/source_manifest.csv')
    x=np.lib.format.open_memmap(WORK/'sequences.npy',mode='w+',dtype='float32',shape=(len(base),5,60))
    rows=[]
    for n,record in enumerate(manifest.to_dict('records'),1):
        path=Path(record['copy'])
        if sha(path)!=record['sha256']: raise ValueError('Curated source changed.')
        data=pd.read_csv(path,usecols=['date','open','high','low','close','volume'])
        stamps=pd.to_datetime(data.date,format='ISO8601',utc=True).dt.tz_convert('Asia/Kolkata')
        data['day']=stamps.dt.tz_localize(None).dt.normalize()
        data['minute']=stamps.dt.hour*60+stamps.dt.minute
        data['seconds']=stamps.dt.second
        for day,group in data.groupby('day',sort=True):
            if len(group)!=375 or not np.array_equal(group.minute,np.arange(555,930)) or group.seconds.any(): continue
            a=group[['open','high','low','close','volume']].to_numpy()
            for t in range(60,345,30):
                x[len(rows)]=window_features(a[t-59:t+1])
                rows.append({'symbol':record['symbol'],'day':str(day)[:10],'signal_minute':555+t,
                             'sequence_return':float(a[t+30,3]/a[t+1,0]-1)})
                if len(rows)==1:
                    group.iloc[t-59:t+1][['date','open','high','low','close','volume']].to_csv(WORK/'example_window.csv',index=False)
        if n%20==0 or n==len(manifest): print(f'Sequences: {n}/{len(manifest)} files; {len(rows):,} windows',flush=True)
    if len(rows)!=len(base): raise ValueError('Sample count mismatch with baseline.')
    meta=pd.DataFrame(rows).merge(base,on=['symbol','day','signal_minute'],validate='one_to_one',sort=False)
    if not np.allclose(meta.sequence_return,meta.future_return,atol=1e-12): raise ValueError('Label alignment failure.')
    x.flush(); del x
    meta.to_csv(WORK/'metadata.csv',index=False)
    atomic_write(WORK/'dataset.json',encoded({'rows':len(meta),'shape':[len(meta),5,60],
        'source_manifest_sha256':sha(ROOT/'outputs/research_v1/source_manifest.csv'),
        'sequences_sha256':sha(WORK/'sequences.npy'),'metadata_sha256':sha(WORK/'metadata.csv'),
        'config_sha256':sha(CONFIG)}))


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
    if ds['config_sha256']!=sha(CONFIG) or ds['sequences_sha256']!=sha(WORK/'sequences.npy') or ds['metadata_sha256']!=sha(WORK/'metadata.csv'):
        raise ValueError('Dataset/config fingerprint changed.')
    x=np.load(WORK/'sequences.npy',mmap_mode='r')
    meta=pd.read_csv(WORK/'metadata.csv')
    years=meta.day.str[:4].astype(int)
    ti=np.flatnonzero(years.isin(config['training_years']))
    vi=np.flatnonzero(years==config['validation_year'])
    di=np.flatnonzero(years==config['development_comparison_year'])
    if (years==2025).any(): raise ValueError('Reserved year must not appear.')
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
    eligible=[c for c in candidates if c['trades']>=config['minimum_validation_trades']]
    choice=max(eligible,key=lambda c:c['mean_net_bps']) if eligible else None
    # All model/threshold selection is complete before the previously observed 2024 comparison.
    dp=probabilities(model,x,di,mean,std)
    def metrics(truth,p):
        return {'auc':float(roc_auc_score(truth,p)),'brier':float(brier_score_loss(truth,p)),'log_loss':float(log_loss(truth,p,labels=[0,1]))}
    import joblib
    baseline=joblib.load(ROOT/'models/research_v1.joblib')
    bp=baseline.predict_proba(meta.iloc[di][FEATURES])[:,1]
    result={'config':config,'signature':signature,'training_rows':len(ti),'validation_rows':len(vi),'comparison_rows':len(di),
            'parameter_count':sum(p.numel() for p in model.parameters()),'epochs_completed':len(history),'best_epoch':best_epoch,
            'validation_metrics':metrics(y[vi],vp),'validation_thresholds':candidates,'selected_threshold':choice,
            'development_2024_metrics':metrics(y[di],dp),'v1_tree_same_sample_metrics':metrics(y[di],bp),
            'constant_same_sample_metrics':metrics(y[di],np.full(len(di),y[ti].mean())),
            'cnn_quote_trade_stats':None if choice is None else trade_stats(meta.iloc[di],dp>=choice['threshold'],config['assumed_cost_bps']),
            'v1_tree_quote_trade_stats':trade_stats(meta.iloc[di],bp>=0.5,config['assumed_cost_bps']),
            'deployment':'disabled','2025_used':False}
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
