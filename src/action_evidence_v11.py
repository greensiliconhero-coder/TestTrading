"""Archive primary notices and reconcile quote identities; never infer fills."""
import io,json,sys,time
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request,urlopen
from datetime import datetime,timezone
from collections import Counter
from research_v1 import ROOT,sha
from kite_repair import atomic_write,encoded
sys.path.insert(0,str(ROOT/'work/pdf_reader'))

DATA=ROOT/'data/action_evidence_v11'
OUT=ROOT/'experiments/action_evidence_v11'

def fetch(rec):
    from pypdf import PdfReader
    p=DATA/(rec['id']+'.pdf');r=dict(rec)
    try:
        if not p.exists():
            req=Request(rec['url'],headers={'User-Agent':'Mozilla/5.0'})
            with urlopen(req,timeout=30) as response:b=response.read()
            if not b.startswith(b'%PDF'):raise ValueError('Expected PDF')
            atomic_write(p,b)
        text='\n'.join(page.extract_text() or '' for page in PdfReader(p).pages)
        (DATA/(rec['id']+'.txt')).write_text(text,encoding='utf-8')
        if rec['kind']=='split_identity' and (rec['symbol'] not in text or rec['new_isin'] not in text):raise ValueError('Required identity fields absent from extracted notice')
        r.update(status='archived',path=str(p.relative_to(ROOT)),sha256=sha(p),retrieved_utc=datetime.now(timezone.utc).isoformat(),human_review_scope=rec['scope'])
    except Exception as e:r.update(status='failed',error=type(e).__name__+': '+str(e))
    return r

def classify(r,documents):
    result=dict(r);result['execution_approved']=False
    if r['status']=='right_censored_dataset_end':result['resolution']='right_censored';return result
    if r['status']=='same_isin_other_series':
        quotes=r['same_isin_quotes']
        result['resolution']='identity_and_quote_verified_other_series' if len(quotes)==1 and quotes[0]['isin']==r['isin'] else 'ambiguous_quotes'
        result['remaining']='Series-specific delivery/settlement and actual fill availability; quote presence is not a fill.'
    elif r['status']=='same_symbol_different_isin':
        matches=[d for d in documents if d['kind']=='split_identity' and d['status']=='archived' and d['symbol']==r['symbol'] and d['ex_day']<=r['day']]
        d=max(matches,key=lambda d:d['ex_day']) if matches else None
        quotes=[q for q in r['same_symbol_quotes'] if d and q['isin']==d['new_isin']]
        if d and len(quotes)==1:
            result.update(resolution='new_isin_corroborated_by_primary_notice',notice=d['path'],notice_sha256=d['sha256'],split_multiplier=d['split_multiplier'],economic_ex_day=d['ex_day'])
            result['remaining']='Apply full entitlements, including any simultaneous bonus, before account replay; preserve source ISIN versus economic effective date.'
        else:result['resolution']='identity_notice_unresolved'
    elif r['symbol']=='HDFC':
        d=next((d for d in documents if d['id']=='HDFC_ALLOTMENT' and d['status']=='archived'),None)
        result['resolution']='merger_terms_archived_execution_unresolved' if d else 'merger_source_unresolved'
        if d:result.update(successor='HDFCBANK',numerator=42,denominator=25,record_day='2023-07-13',allotment_day='2023-07-14',notice=d['path'],notice_sha256=d['sha256'])
        result['remaining']='Actual successor trading availability, fractional cash amount/payment, and no old-security purchase after suspension.'
    else:result['resolution']='unresolved'
    return result

def main():
    DATA.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    records=json.loads((ROOT/'config/action_evidence_v11.json').read_text())
    with ThreadPoolExecutor(max_workers=3) as pool:docs=list(pool.map(fetch,records))
    atomic_write(OUT/'document_manifest.json',encoded(docs))
    source=ROOT/'experiments/causal_universe_v10/endpoint_review.json';rows=json.loads(source.read_text())
    # Validate quote evidence itself before promoting identity status.
    for r in rows:
        if r.get('source_path') and sha(ROOT/r['source_path'])!=r['source_sha256']:raise ValueError('Quote evidence changed')
    resolved=[classify(r,docs) for r in rows]
    atomic_write(OUT/'endpoint_resolutions.json',encoded(resolved))
    queue=json.loads((ROOT/'experiments/causal_universe_v10/prioritized_action_queue.json').read_text());structural=[]
    for r in queue:
        if r['kind'] not in ['split','bonus','rights','demerger']:continue
        raw_source=ROOT/r['source_path'];original=json.loads(raw_source.read_text())[r['source_row']]
        if original['subject']!=r['subject']:raise ValueError('Action source mismatch')
        corroborating=[d for d in docs if d['status']=='archived' and ((d.get('symbol')==r['candidate_symbol'] and d.get('ex_day')==r['ex_day']) or d['id']==r['candidate_symbol']+'_COMBINED')]
        structural.append({**r,'raw_source_sha256':sha(raw_source),'record_date_from_source':original.get('recDate'),'announcement_timestamp_from_source':original.get('caBroadcastDate'),'corroborating_notices':[d['path'] for d in corroborating],'execution_ready':False,'bonus_tradability_verified':False,'payment_date_verified':False})
    atomic_write(OUT/'structural_evidence_register.json',encoded(structural))
    summary={'documents_archived':sum(d['status']=='archived' for d in docs),'documents_requested':len(docs),'document_failures':[d['id'] for d in docs if d['status']!='archived'],'endpoint_resolution_counts':dict(Counter(r['resolution'] for r in resolved)),'automatic_execution_approvals':0,'source_endpoint_sha256':sha(source),'remaining':'Dividend payments, bonus tradability, rights/demergers, merger fractional settlement, historical execution rules. Identity evidence alone does not clear the market gate.'}
    atomic_write(OUT/'summary.json',encoded(summary));print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
