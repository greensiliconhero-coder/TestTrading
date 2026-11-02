# Corporate-action evidence and compound accounting v11

## Completed

Archived and extracted 13 primary exchange/company notices, with source URLs and SHA256 hashes. Eight split/ISIN mappings are corroborated: JUBLFOOD, TATASTEEL, BAJAJFINSV, MAZDOCK, COFORGE, BAJFINANCE, ADANIPOWER and TATAINVEST. MAZDOCK uses an MSE exchange notice corroborated by NSE raw quotes; the other identity notices are NSE notices. This verifies specified identity/terms only, not account-specific delivery or a fill.

Reclassified the 33 in-range endpoint findings without changing candidate membership:

| Finding | Count | Status |
|---|---:|---|
| Same ISIN, different trading series | 14 | Quote identity verified; execution rules still required |
| Different ISIN, primary split notice found | 15 | New identity corroborated; entitlements still required |
| HDFC absent following merger | 3 | Merger terms archived; successor tradability/fractions unresolved |
| IRCTC change | 1 | Effective identity notice still unresolved |

The separate 36 end-of-dataset windows remain right-censored. Counts are endpoint findings, not unique stocks or trades. No finding was turned into an assumed fill or removed from the candidate list.

## Accounting changes

New CompoundLedger processes a verified split followed by bonus as one atomic event. It distinguishes split-adjusted available units from pending bonus units. A missing tradability date rejects the entire event, including the split mutation. Unknown ordering and pre-existing unresolved entitlements are rejected.

Bajaj Finserv's exchange circular corroborates a fivefold split followed by a twofold total-share bonus factor (combined tenfold economic entitlement). Bajaj Finance's exchange circular corroborates factors two and five, also tenfold. These derivatives circulars verify corporate-action terms; they do not prove when cash-equity bonus shares became tradable. No immediate credit is inferred from them.

HDFC Bank's July 14, 2023 company filing confirms allotment at 42 successor shares per 25 HDFC shares held on the July 13 record date. The October filing documents later fractional-entitlement sale/distribution. We do not substitute July 14 allotment for a verified exchange trading date or assume a personal bank-credit date.

83 regression tests passed, including five new checks for compound ordering, pending-share sale restrictions, atomic rollback, future-effective mappings and ambiguous quotes. The source PDFs, extracted text, configurations, endpoint resolutions and structural evidence register are preserved. No model was retrained and no new profit result is claimed.

## Remaining work

The current 21-record structural evidence register preserves the eight splits, nine bonuses, three demergers and one rights record intersecting candidate windows. Evidence dimensions remain separate: identity, factor, record date, announcement, credit/tradability and cash payment. These records are not automatically marked execution-ready. Dividend payment evidence for 238 window records, bonus tradability, complex entitlements, historical fees/settlement and the IRCTC notice remain unfinished. The next market evaluation remains gated; a quote or action ratio alone is insufficient.

## Reproduce and backup

Install requirements.txt and requirements-evidence.txt (the evidence reader can also be installed locally under work/pdf_reader). Run python src/action_evidence_v11.py and python -m unittest discover -s tests -p test_action_v11.py. Complete existing regression suite: python -m unittest discover -s tests. Official documents are reused from disk on rerun; failed downloads are recorded explicitly.

The v10 release is now verified: 208,857,117 bytes, SHA256 c6d258cf6f43622720237bc360a5f969fa8bc69df7db665e6e0e44c064c782a4. The v11 archive adds primary notices, code/tests, evidence queues, relevant original quote archives and all-market action source files. The complete full-market reconstructed panel remains in the v10 release; v11 fits no new model.

Primary sources: [Bajaj Finserv combined action](https://archives.nseindia.com/content/circulars/FAOP53644.pdf), [Bajaj Finance combined action](https://www.msei.in/SX-Content/Circulars/2025/June/Circular-17322.pdf), [HDFC allotment filing](https://nsearchives.nseindia.com/corporate/HDFCBANK_14072023103007_SEIntimationforEquitysharesandWarrants140723.pdf), [HDFC fractional settlement filing](https://nsearchives.nseindia.com/corporate/HDFCBANK_19102023184408_Intimation_Fractional_Entitlement.pdf). Complete source list: experiments/action_evidence_v11/document_manifest.json.
