"""Create a complete private backup of exact inputs, sources and fitted models."""
import hashlib
import json
import zipfile
from pathlib import Path
import pandas as pd
from context_features import ROOT, FOLDER, RESULTS
from context_models import MODELS
from research_v1 import sha


def main():
    out = Path(r'C:\Users\mayan\Documents\Codex\2026-11-01\te\outputs')
    out.mkdir(parents=True,exist_ok=True)
    target = out/'Context_v3_complete_training_backup.zip'
    sources = pd.read_csv(FOLDER/'source_manifest.csv')
    paths = set()
    for record in sources.to_dict('records'):
        path = ROOT / record['path']
        if sha(path)!=record['sha256']:
            raise ValueError('Cannot archive changed source: '+record['path'])
        paths.add(path)
    for folder in [FOLDER,MODELS,RESULTS,ROOT/'src',ROOT/'tests']:
        paths.update(p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths.update([ROOT/'config/context_v3.json',ROOT/'requirements.txt',ROOT/'CONTEXT_V3_PROTOCOL.md',ROOT/'examples/context_v3_features.csv'])
    checksums = {}
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as archive:
        for number,path in enumerate(sorted(paths),1):
            name = path.relative_to(ROOT).as_posix()
            checksums[name] = sha(path)
            compression = zipfile.ZIP_STORED if path.suffix=='.gz' else zipfile.ZIP_DEFLATED
            archive.write(path,'TradingResearch/'+name,compress_type=compression)
            if number%50==0:
                print(f'Archived {number}/{len(paths)} files',flush=True)
        archive.writestr('TradingResearch/SHA256SUMS.json',json.dumps(checksums,indent=2))
        archive.writestr('TradingResearch/RESTORE_CONTEXT_V3.md',
            '# Restore saved context models and exact training inputs\n\n'
            'Extract the archive. In its TradingResearch folder, install requirements.txt in a compatible Python environment '
            '(recorded versions are in models/context_v3/bundle.json). Then run:\n\n'
            'python src/context_predict.py --csv examples/context_v3_features.csv\n\n'
            'This uses saved models without training or credentials. The data/context_training_v3 folder contains the exact learning table, '
            'splits, predictions, trade records and source manifest. Original source payloads are also included at their manifest paths. '
            'SHA256SUMS.json fingerprints the contents. SHA-256 hashes are integrity checks, not a security signature. '
            'Only load model artifacts from trusted sources. No profitable strategy or live execution is guaranteed.\n')
    with zipfile.ZipFile(target) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError('Archive CRC failure: '+bad)
    receipt = {'archive':target.name,'bytes':target.stat().st_size,'sha256':sha(target),
        'files_with_sha256':len(checksums),'original_source_payloads':len(sources),
        'dataset_sha256':sha(FOLDER/'samples.csv.gz'),'models_sha256':sha(MODELS/'candidates.joblib'),
        'release_tag':'context-v3-trained','release_url':'https://github.com/greensiliconhero-coder/TestTrading/releases/tag/context-v3-trained',
        'credentials_included':False,'2025_used':False}
    (RESULTS/'archive_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2),flush=True)


if __name__=='__main__':
    main()
