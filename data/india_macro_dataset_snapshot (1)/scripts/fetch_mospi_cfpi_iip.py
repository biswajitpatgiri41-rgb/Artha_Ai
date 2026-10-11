#!/usr/bin/env python3
"""Fetch official public MoSPI CFPI and IIP API pages into immutable JSON snapshots.

The eSankhyiki client package is used for its documented TLS/session setup;
requests are sent to the production API host and the raw JSON page responses
are preserved. No values are interpolated or linked across base years.
"""
from pathlib import Path
from datetime import datetime, timezone
import json, sys, time
from esankhyiki.client import MoSPI

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/mospi'
API = 'https://api.mospi.gov.in'
CPI_URL = API + '/api/cpi/getCPIIndex'
IIP_URL = API + '/api/iip/getIIPMonthly'
client = MoSPI(base_url=API)


def pages_for(name, url, params, dest):
    first_params = dict(params, page=1)
    r = client.session.get(url, params=first_params, timeout=60)
    r.raise_for_status()
    first = r.json()
    if not first.get('statusCode') or 'meta_data' not in first:
        raise RuntimeError(f'{name}: unexpected first-page response: {str(first)[:500]}')
    meta = first['meta_data']
    pages = [first]
    total_pages = int(meta.get('totalPages', 1))
    for page in range(2, total_pages + 1):
        for attempt in range(4):
            try:
                response = client.session.get(url, params=dict(params, page=page), timeout=60)
                response.raise_for_status()
                payload = response.json()
                if not payload.get('statusCode'):
                    raise RuntimeError(f'{name}: API status false on page {page}: {payload}')
                pages.append(payload)
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(1.0 * (attempt + 1))
    rows = [row for page in pages for row in page.get('data', [])]
    expected = int(meta.get('totalRecords', len(rows)))
    if len(rows) != expected:
        raise RuntimeError(f'{name}: got {len(rows)} records; metadata reports {expected}')
    dest.parent.mkdir(parents=True, exist_ok=True)
    obj = {'provider':'MoSPI eSankhyiki','api_url':url,'query':params,
           'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),
           'first_page_metadata':meta,'pages':pages}
    dest.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return {'name':name,'rows':len(rows),'pages':len(pages),'raw_file':str(dest.relative_to(ROOT))}


if __name__ == '__main__':
    results=[]
    # MoSPI classifies Consumer Food Price as group_code=7 in CPI (2012 base).
    # Keep this 2012-base series separate from the newer 2024-base CPI back series.
    cfpi_params = {'base_year':'2012','series':'Current',
                   'year':','.join(str(y) for y in range(2013,2026)),
                   'state_code':'99','group_code':'7','sector_code':'1,2,3','Format':'JSON'}
    results.append(pages_for('CFPI 2012-base All-India General/Food-price indices', CPI_URL, cfpi_params,
        RAW/'cfpi/cfpi_2012base_all_india_monthly_2013_2025.json'))
    # The long 2011-12-base series and the newer 2022-23-base series are retained
    # as distinct regimes; no computed linking factor is applied.
    for base, filename in [('2011-12','iip_general_monthly_2011-12base_2012-2026.json'),
                           ('2022-23','iip_general_monthly_2022-23base_2023-2026.json')]:
        results.append(pages_for(f'IIP General monthly base {base}', IIP_URL,
            {'base_year':base,'type':'General','Format':'JSON'}, RAW/f'iip/{filename}'))
    print(json.dumps(results, indent=2))
