#!/usr/bin/env python3
"""Fetch RBI's 2026 MPC resolution pages and build a dated repo decision log.

The log records policy decisions (including no-change decisions), not rate-change
events. October's scheduled 5–7 meeting is not represented because the package
snapshot is dated October 5, before that meeting concluded.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, re
import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw/rbi/policy/2026_mpc'
PROC=ROOT/'data/processed'
MAN=ROOT/'data/manifests'
SOURCES=[
 ('2026-02-06','February 4 to 6, 2026','https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=62169'),
 ('2026-04-08','April 6 to 8, 2026','https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=62514'),
 ('2026-06-05','June 3 to 5, 2026','https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=62863'),
 ('2026-08-05','August 3 to 5, 2026','https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=63287'),
]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--from-raw',action='store_true',help='Rebuild from included official HTML pages without network access')
args=parser.parse_args()
RAW.mkdir(parents=True,exist_ok=True)
s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0 (compatible; dataset-research/1.0)'})
rows=[]; manifest_rows=[]
for decision_date,meeting,url in SOURCES:
    raw=RAW/f'rbi_mpc_resolution_{decision_date}.html'
    if args.from_raw:
        if not raw.exists(): raise FileNotFoundError(raw)
        html=raw.read_bytes()
    else:
        response=s.get(url,timeout=60,verify=False); response.raise_for_status()
        html=response.content; raw.write_bytes(html)
    text=' '.join(BeautifulSoup(html,'html.parser').get_text(' ',strip=True).split())
    if 'Resolution of the Monetary Policy Committee' not in text or 'unchanged at 5.25 per cent' not in text:
        raise RuntimeError(f'Unexpected RBI resolution content at {url}')
    pub=re.search(r'Date\s*:\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})',text)
    if not pub: raise RuntimeError(f'Publication date not found at {url}')
    published=datetime.strptime(pub.group(1),'%b %d, %Y').strftime('%Y-%m-%d')
    if published!=decision_date: raise RuntimeError(f'Expected {decision_date} but RBI page says {published}: {url}')
    title=f'Monetary Policy Statement, 2026 MPC resolution ({meeting})'
    rows.append({
      'decision_date':decision_date,'meeting_dates':meeting,'published_date':published,
      'decision':'repo unchanged','policy_repo_rate_pct':5.25,'sdf_rate_pct':5.00,
      'msf_rate_pct':5.50,'bank_rate_pct':5.50,'stance':'neutral',
      'source_title':title,'source_url':url,'raw_file':str(raw.relative_to(ROOT)),
      'sha256':hashlib.sha256(html).hexdigest()})
    manifest_rows.append({'provider':'rbi','series_or_table':title,'source_url':url,
      'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),'raw_file':str(raw.relative_to(ROOT)),
      'sha256':hashlib.sha256(html).hexdigest(),'bytes':len(html),'status':'downloaded',
      'notes':'Official MPC resolution; unchanged repo 5.25%, SDF 5.00%, MSF and Bank Rate 5.50%; decision log is not a rate-change event table.',
      'observation_count':1})

df=pd.DataFrame(rows)
df.to_csv(PROC/'rbi_mpc_repo_decisions_2026.csv',index=False)
mp=MAN/'ingestion_manifest.csv'; manifest=pd.read_csv(mp,low_memory=False).fillna('')
rels={x['raw_file'] for x in manifest_rows}; manifest=manifest[~manifest['raw_file'].isin(rels)]
manifest=pd.concat([manifest,pd.DataFrame(manifest_rows)],ignore_index=True,sort=False); manifest.to_csv(mp,index=False)
cp=MAN/'coverage_matrix.csv'; coverage=pd.read_csv(cp,low_memory=False).fillna('')
for i,r in coverage.iterrows():
    if r['requested_area']=='RBI policy':
        coverage.loc[i,'available_series_or_file']='rbi_policy_rate_events.csv; rbi_mpc_repo_decisions_2026.csv; rbi_current_rates_snapshot_2026-10-05.csv; raw/rbi/policy/'
        coverage.loc[i,'coverage']='Table 40 rate-change history through Dec 2025; 2026 MPC no-change decisions through Aug 5; current snapshot as of Oct 5 13:00 IST'
        coverage.loc[i,'limitation']='The October 5–7, 2026 MPC meeting was still in progress at the snapshot time; no post-meeting decision is claimed. Decision dates and the Table 40 rate-change history are separate constructs.'
coverage.to_csv(cp,index=False)
qpath=MAN/'data_quality_report.json'; q=json.loads(qpath.read_text(encoding='utf-8'))
q['policy_decision_files']=['data/processed/rbi_mpc_repo_decisions_2026.csv']
q['coverage_gaps']=[x for x in q.get('coverage_gaps',[]) if not x.startswith('RBI Table 40 policy-event history ends')]
q['coverage_gaps'].append('RBI Table 40 policy-event history ends in Dec 2025; a separate official no-change MPC decision log covers Feb, Apr, Jun and Aug 2026, while the 5 Oct current-rates snapshot precedes the scheduled Oct 5–7 MPC conclusion.')
qpath.write_text(json.dumps(q,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(df[['decision_date','published_date','policy_repo_rate_pct','source_url']].to_string(index=False))
