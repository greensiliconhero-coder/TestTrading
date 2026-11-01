# GitHub backup and restore

Target repository: https://github.com/greensiliconhero-coder/TestTrading

Included: source code, configuration, tests, experiment results, compact data-audit evidence, source-file hash manifest, v1 trained model, v2 trained weights, v2 preprocessing bundle, optimizer checkpoint, and an example inference window. All local branches and tags should be pushed.

Excluded: original and curated market-data CSV collections, downloaded Kite payloads, large row-level audit/prediction outputs, prepared training arrays, environments, caches, and credentials. This is a code-and-model backup, not a complete backup of the training datasets. Original dataset paths in configuration must be updated on a different machine; the source manifest records the curated file hashes. Retain a separate private backup of those datasets if you need to reproduce training.

## Restore inference without retraining

Clone the repository, switch to `experiment/neural-v2`, and install dependencies from `requirements-neural.txt` in a Python 3.10 environment. The recorded training environment used PyTorch 2.2.2+cpu. Then run:

```powershell
python src/neural_v2.py predict --csv examples/neural_v2_window.csv
```

Expected example probability: approximately 0.47951847. The command loads `models/neural_v2/weights.pt` and `bundle.json`; no training dataset or Kite credentials are required. The output is a research direction score, not a calibrated profit probability. No validated profitable strategy was established.

`resume.pt` is the latest optimizer checkpoint; `weights.pt` is the best validation checkpoint used for inference. Only load model artifacts from trusted sources.
