#!/usr/bin/env python3
"""Capture or locally normalize the RBI current-rates page as a dated snapshot."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, re
import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
URL='https://m.rbi.org.in/Scripts/BS_NSDPDisplay.aspx?param=4'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--from-raw',action='store_true',help='Normalize the newest included raw HTML snapshot without network access')
args=parser.parse_args()
if args.from_raw:
    candidates=sorted((ROOT/'data/raw/rbi/policy').glob('rbi_current_rates_snapshot_*.html'))
    if not candidates: raise FileNotFoundError('No included RBI current-rates HTML snapshot found')
    raw=candidates[-1]; content=raw.read_bytes()
else:
    response=requests.get(URL,headers={'User-Agent':'Mozilla/5.0'},timeout=60,verify=False)
    response.raise_for_status(); content=response.content
text='\n'.join(line.strip().replace('\xa0',' ') for line in BeautifulSoup(content,'html.parser').get_text('\n').splitlines() if line.strip())
def rate(label):
    match=re.search(re.escape(label)+r'\s*:\s*([0-9]+(?:\.[0-9]+)?%?)',text,re.I)
    if not match: raise ValueError(f'Expected current-rate field was not found: {label}')
    return float(match.group(1).replace('%',''))
asof=re.search(r'As at\s+([^\n]+)',text,re.I)
if not asof: raise ValueError('The RBI as-of timestamp was not found in the page')
asof_dt=datetime.strptime(asof.group(1).strip().strip(')'),'%I.%M%p of %B %d, %Y')
date=asof_dt.strftime('%Y-%m-%d')
if not args.from_raw:
    raw=ROOT/f'data/raw/rbi/policy/rbi_current_rates_snapshot_{date}.html'
    raw.parent.mkdir(parents=True,exist_ok=True); raw.write_bytes(content)
record={
 'as_at_date':date,'as_at_time_ist':asof_dt.strftime('%H:%M'),
 'policy_repo_rate_pct':rate('Policy Repo Rate'),
 'sdf_rate_pct':rate('Standing Deposit Facility Rate'),
 'msf_rate_pct':rate('Marginal Standing Facility Rate'),
 'bank_rate_pct':rate('Bank Rate'),
 'fixed_reverse_repo_rate_pct':rate('Fixed Reverse Repo Rate'),
 'crr_pct':rate('CRR'),'slr_pct':rate('SLR'),
 'inr_per_usd':rate('INR / 1 USD'),'inr_per_gbp':rate('INR / 1 GBP'),
 'inr_per_eur':rate('INR / 1 EUR'),'inr_per_100_jpy':rate('INR / 100 JPY'),
 'inr_per_aed':rate('INR / 1 AED'),'inr_per_10000_idr':rate('INR / 10000 IDR'),
 'source':'RBI Current Rates page; listed FX source is FBIL','source_url':URL,'raw_file':str(raw.relative_to(ROOT))}
out=ROOT/f'data/processed/rbi_current_rates_snapshot_{date}.csv'
pd.DataFrame([record]).to_csv(out,index=False)
manifest_path=ROOT/'data/manifests/ingestion_manifest.csv'
manifest=pd.read_csv(manifest_path,low_memory=False).fillna('')
rel=str(raw.relative_to(ROOT)); manifest=manifest[manifest['raw_file']!=rel]
manifest=pd.concat([manifest,pd.DataFrame([{
 'provider':'rbi','series_or_table':f'Current policy rates and selected exchange rates snapshot as of {date} {record["as_at_time_ist"]} IST',
 'source_url':URL,'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),'raw_file':rel,
 'sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'bytes':raw.stat().st_size,'status':'downloaded',
 'notes':'Official RBI Current Rates block. FX values are attributed on-page to FBIL. One-date snapshot, not a historical event series.',
 'observation_count':1}])],ignore_index=True,sort=False)
manifest.to_csv(manifest_path,index=False)
print(pd.DataFrame([record]).to_json(orient='records',indent=2))
