# TradingResearch

This repository is backed up privately at https://github.com/greensiliconhero-coder/TestTrading. The initial completed-work snapshot is tagged `v0.1.0-baseline`. See `ROADMAP.md` for the research history and commit/versioning workflow. Large training datasets are preserved in private release archives; small trained model binaries and compact evidence are versioned in Git.

## Context v3 completed and preserved

The bounded study used 326,880 rows and 58 features across 37 companies. Six final supervised models (ridge regression and boosted trees) and three rule baselines were compared, with earlier chronological diagnostic fits also saved. No candidate met the frozen validation requirements; the selected outcome is cash. No real orders or 2025 outcomes were used.

Processing is on `processing/context-features-v3`; completed models and results are on `experiment/context-v3-trained`. See `experiments/v3/report.md` and `CONTEXT_V3_PROTOCOL.md`. Exact model inputs, labels, splits, predictions and original source payloads are preserved in the private release https://github.com/greensiliconhero-coder/TestTrading/releases/tag/context-v3-trained. The pre-quality-screen table is retained separately. Full-day retrospective source screening remains a material limitation.

`python src/context_predict.py --csv examples/context_v3_features.csv` loads the saved models without training. The example contains prepared numeric features, not raw candles. `models/context_v3/bundle.json` records versions and hashes; `candidates.joblib` and `diagnostic_2021.joblib` preserve final and diagnostic fits.

## Neural network v2 completed and preserved

The first actual sequence CNN is saved in `models/neural_v2/weights.pt`, with input scaling and provenance in `bundle.json`. Training stopped after three epochs; epoch one was best on validation. Its 2024 development-comparison AUC was 0.5054 versus 0.5155 for the existing tree on identical examples. No threshold met the predefined minimum validation sample size; no trading rule is approved. 2025 remains unused.

`python src/neural_v2.py predict --csv examples/neural_v2_window.csv` loads the saved model without training. `train` also skips retraining when completed results and a valid model bundle exist. See `NEURAL_V2.md` and `experiments/v2/report.md`. The trained models and optimizer checkpoint are now stored in Git. See BACKUP.md for restore instructions and backup coverage.

Personal Indian cash-equity research, including data audits, staged historical downloads and saved learning models. Live trading is disabled. Simulated results do not establish deployable profitability.

## First learning experiment completed

`RESEARCH_V1.md` documents the fixed 30-minute prediction experiment. Structurally screened minute CSVs for 37 companies are copied into `data/curated_minute_v1/`. A trained gradient-boosting classifier is in `models/research_v1.joblib`. It has not demonstrated a useful net trading edge; deployment is disabled. This is supervised learning from future-return labels, not causal reasoning or autonomous live adaptation.

Results, excluded-company reasons, file checksums, calibration, feature importance and test predictions are in `outputs/research_v1/`. Start with `learning_report.md`. 2024 has now been used for evaluation and must not be treated as a fresh holdout in future experiments. 2025 remains unused for learning/evaluation.

See `KITE_SETUP.md` for the ready-to-run pilot and `Run-KitePilot.ps1` for the Windows launcher. Downloaded records are staged separately and never automatically merged into source files.

## Run on Windows

Python 3.10+ is required. From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe src/audit.py
.\.venv\Scripts\python.exe src/coverage.py
.\.venv\Scripts\python.exe src/extract_issues.py
```

For an existing environment with pandas 2.2.2, use `python` directly. The initial audit used the existing environment; no global packages were installed.

Dataset locations are in `config/datasets.json`. The scanner loads one CSV at a time and retains compact daily summaries, keeping memory use suitable for a 16 GB machine. Raw minute data remains unchanged. Daily aggregation is used only to compare the two provided sources, not to choose a trading frequency.

## Outputs

`outputs/audit/audit_report.md` explains results and limitations. CSV evidence provides file-level issues, session coverage and cross-frequency comparisons. `summary.json` records source paths and runtime versions. File sizes and modification times are recorded; these are not cryptographic integrity hashes.

Regular-session coverage is a diagnostic against 375 minute-start timestamps, not a verified exchange calendar. No missing candles are filled. Flagged records are not automatically removed. Cross-file symbol/day ambiguity is excluded from comparison and counted. Sessions from invalid source rows are diagnostic aggregates, not training data.

## Research gates

1. Audit actual coverage and establish data provenance, adjustments, timestamp conventions and instrument identity.
2. Resolve material issues and define an eligible universe without silently selecting only surviving winners.
3. Predefine a small hypothesis set, prediction horizons, execution assumptions, costs and chronological train/validation/final-test windows. Account for overlapping labels.
4. Compare simple baselines with a modest ML model. Fit preprocessing only on training data. Record all experiments, not just winners.
5. Consider forward simulation only if held-out results justify it. No automated live orders are part of this project stage.

The owner confirmed Kite historical API as the provider. Corporate-action adjustment policy, minute volume semantics, historical instrument identity and candle timestamp conventions still require verification. Never commit broker credentials or tokens.
