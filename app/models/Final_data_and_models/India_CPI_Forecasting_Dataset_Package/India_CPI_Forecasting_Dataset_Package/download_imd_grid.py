#!/usr/bin/env python3
"""Resumably acquire IMD 0.25-degree daily rainfall grids (1901-2024).
Downloads only public form-post files, verifies classic NetCDF magic, and gzip-compresses
individual annual files so the ZIP remains practical. Failed years are recorded, never faked.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import gzip, json, os, threading, time, requests

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'raw'/'imd'/'gridded_daily_025deg'
OUT.mkdir(parents=True,exist_ok=True)
LOG=OUT/'download.log'
_lock=threading.Lock()
_tls=threading.local()


def log(msg):
 line=f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] {msg}"
 with _lock:
  print(line,flush=True)
  with LOG.open('a',encoding='utf-8') as f:f.write(line+'\n')


def sess():
 if not hasattr(_tls,'s'):
  _tls.s=requests.Session();_tls.s.headers.update({'User-Agent':'Mozilla/5.0 (compatible; IndiaInflationResearch/1.0; public-data-download)','Referer':'https://www.imdpune.gov.in/cmpg/Griddata/RF25.php'})
 return _tls.s


def get_year(y):
 dest=OUT/f'RF25_daily_0.25deg_{y}.nc.gz'
 if dest.exists() and dest.stat().st_size>10000:
  return {'year':y,'status':'existing','path':str(dest.relative_to(ROOT)),'bytes':dest.stat().st_size}
 url='https://www.imdpune.gov.in/cmpg/Griddata/RF25.php'
 err=None
 for attempt in range(4):
  try:
   r=sess().post(url,data={'RF25':str(y)},timeout=300)
   r.raise_for_status()
   data=r.content
   if len(data)<1000000 or not data.startswith(b'CDF\x01'):
    raise RuntimeError(f'invalid/too-short response: {len(data)} bytes, {r.headers.get("content-type")}, {data[:32]!r}')
   tmp=dest.with_suffix(dest.suffix+'.tmp')
   with gzip.open(tmp,'wb',compresslevel=1) as f:f.write(data)
   tmp.replace(dest)
   return {'year':y,'status':'downloaded','path':str(dest.relative_to(ROOT)),'bytes':dest.stat().st_size,'source_bytes':len(data),'source_url':url}
  except Exception as e:
   err=f'{type(e).__name__}: {e}'
   time.sleep(min(2**attempt,16))
 return {'year':y,'status':'failed','error':err,'source_url':url}


def main():
 start=int(os.environ.get('IMD_GRID_START','2012'))
 end=int(os.environ.get('IMD_GRID_END','2024'))
 workers=int(os.environ.get('IMD_GRID_WORKERS','3'))
 years=range(start,end+1)
 results=[];done=0
 LOG.write_text('',encoding='utf-8')
 log(f'Starting IMD daily rainfall grid collection: {years.start}-{years.stop-1}; workers={workers}')
 with ThreadPoolExecutor(max_workers=workers) as ex:
  futs={ex.submit(get_year,y):y for y in years}
  for fut in as_completed(futs):
   y=futs[fut]
   try:r=fut.result()
   except Exception as e:r={'year':y,'status':'failed','error':str(e)}
   results.append(r);done+=1
   if r['status']=='failed':log(f"FAILED year={y} {r.get('error')}")
   if done%5==0 or done==len(futs):
    ok=sum(x['status'] in ('downloaded','existing') for x in results)
    total=sum(x.get('bytes',0) for x in results)
    log(f'Progress {done}/{len(futs)} years; complete={ok}; compressed_bytes={total}')
 manifest={'source':'India Meteorological Department, 0.25 degree daily rainfall grids','years':[start,end],
           'url':'https://www.imdpune.gov.in/cmpg/Griddata/RF25.php','retrieved_utc':datetime.now(timezone.utc).isoformat(),
           'file_format':'gzip-compressed NetCDF classic annual files (.nc.gz)','files':sorted(results,key=lambda x:x['year'])}
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 log(f"Finished: successful={sum(x['status'] in ('downloaded','existing') for x in results)}/{len(results)}")

if __name__=='__main__':main()
