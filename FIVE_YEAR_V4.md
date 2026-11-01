# Five-year comparison: frozen acquisition and evaluation plan

Status: downloader prepared; authentication and acquisition pending. No v4 model has been trained or tested yet.

## Data and scope

Acquire 2021-01-01 through 2025-12-31: the last five complete calendar years as of 2026-11-02. Use the same 37-stock survivor cohort and nine indices as v3, as enumerated in config/five_year_v4.json. This comparison adds a training year; it does not claim five years of training plus a separate test. Existing earlier runs trained on 2021–2022.

Store fresh, immutable raw Kite responses under data/five_year_v4/raw/{stock,index}/{minute,day}. Retain timestamped instrument snapshots, request dates, SHA-256 hashes and manifest under experiments/five_year_v4. Download 1,702 bounded requests sequentially with the existing data-only client; verified completed chunks can resume. Save malformed responses for quarantine, never silently repair. Empty responses are not successful coverage. No credentials are persisted. No orders are available through this client.

Daily data is for validation, not a replacement for minute model inputs. Same-provider daily comparisons are consistency checks, not independent verification. Before fitting, audit completeness, duplicates, OHLC, timezone, session coverage, zero-volume stock sessions, corporate-action dates including 2025, and overlapping old/new snapshot differences. Current security tokens and surviving companies do not establish historical membership. Do not mix adjusted price snapshots. Data quality checks may inspect 2025 structure but must not select rules based on its investment returns. The prior retrospective quality exclusions are a known bias; document any new exclusion rule before model evaluation.

## Sequential training and testing

1. Train 2021–2023; validate/select on 2024; evaluate frozen choices once on 2025. 2024 has already been explored and is not an untouched test. Do not tune on 2025 after reporting it. Preserve a future period for any later strategy changes.
2. Fit the same logistic and histogram-tree classifiers, then the same 1,729-parameter CNN, then the context strategy families (rules, Ridge and histogram-tree regression). Keep architecture, feature definitions, seed, hyperparameters, entry/exit timing and costs fixed to their versioned original protocols. Original logistic weights were not retained, so this is a fresh reproducible fit, not a reload.
3. Use no minimum trade count, matching the user's latest sensitivity comparison. Keep positive validation return and applicable execution-capacity gates. Zero trades cannot establish profitability. Report observation counts, uncertainty and concentration prominently; a rare win is not sufficient evidence.
4. Persist each model immediately after training, together with preprocessing, exact training input hashes, dependency versions and prediction-reload checks. Maintain distinct outputs for each family; CNN quote returns and context cash-portfolio returns have different units and cannot be ranked as though identical.
5. Report all candidates, validation-selected candidates, cash baseline, trade counts, net outcomes, drawdown where supported, costs and stress costs. Keep old v1–v3 models untouched. Add a same-snapshot 2021–2022 training control where practical to separate the extra-year effect from revised vendor history and changed test period.
6. If results remain inadequate, document the failure first. Subsequent changes get a new processing/experiment branch and a separate preregistered evaluation; do not search repeatedly on 2025 and call it unseen.

## Reproduction and branches

Dry run: `python src/five_year_download.py`

Interactive data acquisition: `powershell -ExecutionPolicy Bypass -File Run-FiveYearData.ps1`

Tests: `python -m unittest discover -s tests -p test_five_year_download.py`

Acquisition branch: data/five-year-v4. Processing and training will use separate subsequent branches. Large raw data remains outside Git and will be archived with checksums; source, configs, documentation and compact manifests belong in Git. Final training and testing commands will be added when implemented and verified.

No results or profitability claims exist for this version yet. More history can improve estimation or reveal failure; success is not guaranteed.
