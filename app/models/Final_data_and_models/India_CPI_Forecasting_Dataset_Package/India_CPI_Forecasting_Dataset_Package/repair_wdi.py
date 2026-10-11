#!/usr/bin/env python3
"""Retry transient World Bank API failures and append recovered annual indicators.

The original collector writes the all-country, long-form WDI panel. This helper retries
only the nine valid indicators that failed during the first six-worker batch; it does
not fabricate values or replace missing observations. It updates the manifest and writes
an itemized retry manifest.
"""
from __future__ import annotations
import csv, gzip, json, time
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'raw/world_bank/wdi_selected_all_countries_long.csv.gz'
MANIFEST=ROOT/'metadata/download_manifest.json'
OUTMAN=ROOT/'metadata/wdi_retry_manifest.json'
CODES=[
    'NE.CON.GOVT.ZS', 'NE.GDI.TOTL.ZS', 'NE.EXP.GNFS.ZS', 'NE.IMP.GNFS.ZS',
    'NV.IND.MANF.KD.ZG', 'NV.SRV.TOTL.ZS', 'AG.PRD.FOOD.XD', 'AG.PRD.CROP.XD',
    'NV.IND.TOTL.ZS',
]
FIELDS=['country_iso3','country_id','country_name','year','indicator_code','indicator_name','value','unit','observation_status','decimal']

def api_rows(code, session):
    url=f'https://api.worldbank.org/v2/country/all/indicator/{code}'
    params={'date':'1960:2025','format':'json','per_page':20000}
    last=None
    for attempt in range(5):
        try:
            r=session.get(url,params=params,timeout=120); r.raise_for_status(); js=r.json()
            if not isinstance(js,list) or len(js)<2 or not isinstance(js[1],list):
                raise RuntimeError(str(js)[:300])
            rows=[]
            for x in js[1]:
                c=x.get('country') or {}; ind=x.get('indicator') or {}
                rows.append([x.get('countryiso3code'),c.get('id'),c.get('value'),x.get('date'),code,ind.get('value'),x.get('value'),x.get('unit'),x.get('obs_status'),x.get('decimal')])
            if not rows: raise RuntimeError('empty indicator response')
            return {'indicator_code':code,'status':'downloaded','rows':rows,'row_count':len(rows),'source_url':r.url}
        except Exception as e:
            last=f'{type(e).__name__}: {e}'
            print(f'{code}: attempt {attempt+1}/5 failed: {last}',flush=True)
            if attempt<4: time.sleep(min(3*(2**attempt),30))
    return {'indicator_code':code,'status':'failed','error':last,'source_url':url}

def main():
    with gzip.open(DATA,'rt',newline='',encoding='utf-8') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=FIELDS: raise RuntimeError(f'unexpected WDI schema: {reader.fieldnames}')
        existing_codes={r['indicator_code'] for r in reader}
    s=requests.Session();s.headers.update({'User-Agent':'Mozilla/5.0 (compatible; IndiaInflationResearch/1.0; public-data-download)'})
    results=[];new_rows=[]
    for code in CODES:
        if code in existing_codes:
            results.append({'indicator_code':code,'status':'already_present','row_count':0})
        else:
            result=api_rows(code,s)
            if result['status']=='downloaded': new_rows.extend(result.pop('rows'))
            results.append(result)
        time.sleep(1.0)
    if new_rows:
        tmp=DATA.with_suffix(DATA.suffix+'.tmp')
        with gzip.open(DATA,'rt',newline='',encoding='utf-8') as src, gzip.open(tmp,'wt',newline='',encoding='utf-8') as dst:
            reader=csv.reader(src); writer=csv.writer(dst)
            writer.writerow(next(reader))
            writer.writerows(reader)
            writer.writerows(new_rows)
        tmp.replace(DATA)
    recovered={r['indicator_code'] for r in results if r['status']=='downloaded'}
    m=json.loads(MANIFEST.read_text(encoding='utf-8'))
    for d in m.get('datasets',[]):
        if d.get('source')=='World Bank WDI':
            d['indicators_ok']=len(existing_codes|recovered)
            d['indicators_recovered']=sorted(recovered)
            d['rows']=d.get('rows',0)+len(new_rows)
            d['bytes_after_retry']=DATA.stat().st_size
    MANIFEST.write_text(json.dumps(m,indent=2,ensure_ascii=False),encoding='utf-8')
    retry={'source':'World Bank WDI API','retrieved_utc':datetime.now(timezone.utc).isoformat(),
           'range':'1960-2025','added_rows':len(new_rows),'indicators_present_before_retry':sorted(existing_codes),
           'results':[{k:v for k,v in x.items() if k!='rows'} for x in results],
           'note':'The failed/deleted indicator PA.NUS.PPPC.RF is intentionally not substituted or imputed.'}
    OUTMAN.write_text(json.dumps(retry,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'added_rows':len(new_rows),'recovered':sorted(recovered),'failed':[x for x in results if x['status']=='failed'],'file_bytes':DATA.stat().st_size},indent=2),flush=True)

if __name__=='__main__': main()
