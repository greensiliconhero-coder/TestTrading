# Causal universe and entitlement accounting v10

## Completed

Reconstructed 2,057,943 valid EQ/INE daily records across 1,240 official NSE archives, 2021–2025; 2,612 distinct ISINs. No invalid/zero rows in the defined instrument filter. Original raw source archives were hash-checked.

The frozen rule selects up to 36 securities by trailing 20-session traded value after 61 consecutive valid sessions, every five sessions. It produced 8,496 candidate slots over 236 signal dates, covering 226 ISINs / 222 symbols. Selection uses no future prices or corporate actions. 5,005 slots (58.91%) fall outside the old stock list: the old survivor cohort was materially narrower than this historical liquidity cohort. This is not proof that either universe is profitable.

Candidate membership is saved before future-outcome auditing. Future events never delete candidates. Raw data from securities that later disappear are retained where present in the source archives. INE/EQ is an explicit instrument filter, not certified historical index membership or complete point-in-time security metadata. Identity changes can reset warmup conservatively.

## Accounting audit

277 proposed five-session holding windows intersect 285 exchange action records:

| Record type | Count |
|---|---:|
| Dividend | 238 |
| Bonus | 9 |
| Split | 8 |
| Rights | 1 |
| Demerger | 3 |
| General meeting | 20 |
| Buyback | 6 |

Meetings do not automatically change cash or shares. Buybacks require an explicit participation policy. Parsed dividends, factors and ex-dates are evidence candidates; actual payment/tradability dates and complex entitlements are not invented. All 12,014 input action records had parseable ex-dates; this does not certify completeness or correctness.

61 windows lack both expected EQ/same-ISIN endpoints: 36 extend beyond the dataset boundary, and 25 require coverage/identity review. Those 25 produce 33 endpoint findings: 14 same-ISIN quotes in another trading series, 16 same-symbol quotes with a different ISIN, and three without either match. Exact source quotes/hashes are preserved in endpoint_review.json; none was automatically substituted. Tail windows remain censored, not losses or wins.

## Ledger improvement

New EntitlementLedger extends the existing ledger to distinguish bonus shares owed from shares available for sale. Pending bonus shares contribute marked equity but cannot be sold before the supplied verified tradability session. Missing timing and fractional-entitlement policies fail explicitly. Ex-date buyers do not receive prior-holder entitlements. Existing v9 results are not rewritten.

SEBI's September 16 2024 circular specifies the shortened bonus trading timetable for issues announced on or after October 1 2024; this is not a blanket rule for older actions. Source PDF and hash saved. [Official SEBI circular](https://www.sebi.gov.in/sebi_data/attachdocs/sep-2024/1726484230463.pdf).

Full regression suite: 78 tests passed, including six new tests for past-only selection, gap handling, bonus tradability, ex-date entitlement and atomic rejection. These are engineering checks, not validation of market profitability.

## Remaining gate and next work

No new model fit, profit figure or deployable backtest is claimed for v10. The reconstruction removes the previous explicit survivor-list and future-action filters from candidate selection, but a complete causal feature/label and execution pipeline is still unfinished. Required next: verify the 17 split/bonus records and identity transitions; establish dividend entitlements/payment evidence; account for rights/demergers; certify historical fee/settlement assumptions. Prioritized evidence and endpoint queues are saved without deleting difficult windows. Then run the preregistered rolling comparison of simple models with all chronological outcomes reported.

The earlier v9 private release has now been verified against its 150,910,906-byte local archive and SHA256 bc468aa7341467a897fe8c087b41e1d3c766612117869e02b2c0150ecd013742. No credential or paid-compute access was needed for v10.

## Reproduce

Protocol: CAUSAL_UNIVERSE_V10.md. Run python src/causal_universe_v10.py (refuses completed overwrite), python src/audit_obligations_v10.py, and python -m unittest discover -s tests. Data: data/causal_universe_v10. Reports and evidence queues: experiments/causal_universe_v10. The archive receipt records the precise reproducible backup scope.
