# Context v3 frozen experiment protocol

This protocol and `config/context_v3.json` are committed before fitting. This is a bounded exploratory study, not a deployment approval. The nine candidates are three predefined event families times three model types. No threshold grid, architecture search or post-result retuning is authorized by this protocol.

## Data and information boundary

Use the 148 immutable screened stock files for 37 companies in 2021-2024 and the 225 verified index-history chunks. Check every source hash before processing. Build a new dataset under `data/context_training_v3/`; never modify earlier training sets. Save all model feature columns, labels, entry/exit quote prices and volumes, split labels, exclusions, source fingerprints and configuration/code fingerprints. Back up this dataset, its original source files and models in a private release, so inference and training input reproduction do not depend on re-downloading revised history.

Retain only exact 375-minute regular sessions for stocks and all nine indices, with no filling. Exclude stock ex-dates in the obtained corporate-action ledger, to avoid mixing adjustment uncertainty into this first study. This retrospective screen and the prior surviving-stock cohort remain limitations. No overnight stock-return features are used. Every feature uses candles through the completed signal minute only. Inputs are returns, trailing volatility, participation proxies and aligned panel breadth; labels and fill fields must never enter model feature selection.

All nine index series enter as a joint context vector. No current sector membership or industry label is assigned to past stocks. This avoids pretending that today's sector classification is historical information. Index identity across history remains subject to limited independent sample checks.

## Timing and models

Signal times run from 10:15 to 14:45 every 30 minutes. A signal using candle t is executable at candle t+2 open, leaving one full minute for processing. Exit is t+32 open, 30 minutes after entry. Execution fields are evaluated only by the simulator; forecast decisions use completed signal-time information.

Features: the previous baseline's eight stock features; 5-, 15-, 30-minute and since-open returns and trailing 30-minute volatility for each index; stock minus Nifty 30-minute return; median sector-index return; contemporaneous breadth and mean stock return of the available research panel; volume divided by the mean same-signal-time volume over the preceding 20 available sessions (minimum five). The current session is excluded from that denominator. Availability of the screened panel is retrospective and disclosed.

Each event family has an explicit rule, standardized ridge return regression and one fixed gradient-boosted regression. Regressors predict gross executable 30-minute return. The forecast hurdle uses known fixed notional and fee assumptions, not a future entry price. Parameters, event cutoffs and gates are in the config. Rule scores and ordering use only event-time data.

Use a chronological diagnostic fit on 2021 with 2022 evaluation, then fit final saved candidates on 2021-2022 and select on 2023. No labels cross a session or year boundary. All learned scaling is training-only. Each of the nine final candidate models and its 2023 predictions are preserved. Then evaluate the fixed candidates on already-seen 2024 development data and compare selected candidate with cash. Report every result, including losses. Reserve 2025 completely; no new holdout evaluation in this version.

## Portfolio simulator and uncertainty

Illustrative capital is INR 50,000 with INR 10,000 maximum per position and at most five concurrent positions, whole shares and no leverage/shorting. Capital is an experiment assumption, not the owner's declared investment budget. At execution times, process exits before entries, then rank eligible signals by predicted return (rule candidates use specified event strength); break ties by symbol. Reserve room for estimated entry fees and never allow negative cash. Cash is zero-yield for this simulation. Report daily flat-position equity and close-to-close drawdown; these do not capture every intraday drawdown.

Apply adverse 2 bps slippage per side, with fixed 5 bps per-side stress. Use date-effective NSE transaction rates and the fee assumptions listed in config. Fees are estimates without exact contract-note rounding or complete IPFT reconciliation. Bar-volume participation at 1% bounds assumed entry quantity. This uses realized execution-bar volume as a retrospective feasibility proxy, not information the decision model can observe or proof of a fill. Exit participation failures are recorded and make a candidate ineligible; they are never silently removed to improve returns.

Choose a 2023 candidate only if it has at least 200 filled trades, positive net total return and zero exit-capacity failures. Maximize net total return among eligible candidates; otherwise choose cash. A selected candidate is still research-only. Report block-bootstrap uncertainty for mean daily returns with five-session blocks, jointly reflecting the whole portfolio, and a Bonferroni-adjusted lower bound for nine candidates. Any positive trading claim would additionally need forward confirmation, cost stress, concentration review and independently verified execution.

## Independent evidence and unresolved limitations

Official NSE daily index files were collected for 2021-01-04, 2022-01-03, 2023-01-02 and 2024-01-02. Compare each available named index with aggregated minute high/low and final quote. Daily official close and last-minute quote need not be equal: preserve the differences, do not automatically adjust prices. Four dates are sample checks, not independent certification of all history.

An official SEBI account of the 2021-02-24 outage supports treating that date as exceptional; NSE's special-session circular supports the nonstandard 2024-03-02 session. The strict session rule excludes these without treating every missing minute as vendor corruption. Other short or missing sessions remain recorded, not explained away.

Sources for date-effective exchange-fee revisions:

- https://zerodha.com/marketintel/bulletin/347967/revision-in-transaction-charges-and-stt-from-1st-april-2023
- https://zerodha.com/marketintel/bulletin/373933/revision-in-nse-transaction-charges-from-april-1-2024
- https://zerodha.com/marketintel/bulletin/391488/revision-in-transactions-charges-from-1st-october-2024
- https://zerodha.com/charges/
- https://www.sebi.gov.in/sebi_data/attachdocs/feb-2021/1614256948318.pdf
- https://nsearchives.nseindia.com/content/circulars/MSD60677.pdf

Stop on source checksum mismatches or invalid numeric inputs. Missing independent certification limits conclusions and deployment; it does not justify inventing a successful validation. Existing models and all failed versions remain preserved.
