#!/usr/bin/env python3
"""Add official MoSPI CPI/CFPI/IIP series and RBI USD/INR archive data.

Run after normalize_downloaded.py. This script is idempotent for the series it
owns, expects the raw snapshots under data/raw/, and invokes the finalizer.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, subprocess, sys
import pandas as pd
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw'
PROC = ROOT / 'data/processed'
MAN = ROOT / 'data/manifests'
OBS_PATH = PROC / 'macro_observations.csv'
CPI_RAW = RAW / 'mospi/cpi/mospi_cpi_2024_back_series_all_india_2013_2024.json'
FX_RAW = RAW / 'rbi/fx/rbi_usd_reference_rates_2013-01-01_to_2026-10-05.xls'
CFPI_RAW = RAW / 'mospi/cfpi/cfpi_2012base_all_india_monthly_2013_2025.json'
IIP_OLD_RAW = RAW / 'mospi/iip/iip_general_monthly_2011-12base_2012-2026.json'
IIP_NEW_RAW = RAW / 'mospi/iip/iip_general_monthly_2022-23base_2023-2026.json'
CPI_URL = 'https://esankhyiki.mospi.gov.in/macroindicators?product=cpi'
FX_URL = 'https://www.rbi.org.in/scripts/referenceratearchive.aspx'
CPI_API_URL = 'https://api.mospi.gov.in/api/cpi/getCPIIndex'
IIP_API_URL = 'https://api.mospi.gov.in/api/iip/getIIPMonthly'
RETRIEVED_FX = (datetime.fromtimestamp(FX_RAW.stat().st_mtime, timezone.utc).isoformat()
                if FX_RAW.exists() else datetime.now(timezone.utc).isoformat())

for path in (CPI_RAW, FX_RAW, CFPI_RAW, IIP_OLD_RAW, IIP_NEW_RAW, OBS_PATH):
    if not path.exists():
        raise FileNotFoundError(f'Required input is missing: {path}')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def relative(path):
    return str(path.relative_to(ROOT))

# ---- MoSPI 2024-base Back Series, CPI (General), All India ----
raw = json.loads(CPI_RAW.read_text(encoding='utf-8'))
api_rows = [row for page in raw['pages'] for row in page.get('response', {}).get('data', [])]
sector_ids = {'Combined': 'cpi_index_2024', 'Rural': 'cpi_rural_index_2024', 'Urban': 'cpi_urban_index_2024'}
yoy_ids = {'Combined': 'cpi_yoy_2024', 'Rural': 'cpi_rural_yoy_2024', 'Urban': 'cpi_urban_yoy_2024'}
months = {name: i for i, name in enumerate(['January','February','March','April','May','June','July','August','September','October','November','December'], 1)}
retrieved_cpi = raw.get('retrieved_at_utc', RETRIEVED_FX)
cpi_records = []
for row in api_rows:
    sector = row.get('sector')
    if row.get('state') != 'All India' or row.get('division') != 'CPI (General)' or sector not in sector_ids:
        continue
    date = pd.Timestamp(int(row['year']), months[row['month']], 1).strftime('%Y-%m-%d')
    sid = sector_ids[sector]
    cpi_records.append({
        'obs_date': date, 'series_id': sid, 'value': float(row['index']),
        'unit': 'index 2024=100', 'frequency': 'monthly', 'source': 'MoSPI',
        'source_url': CPI_URL, 'release_date': '2026-02-12', 'retrieved_at': retrieved_cpi,
        'base_year': '2024', 'seasonal_adjustment': '',
        'revision_tag': 'Official 2024-base CPI (General) back series; Jan 2013–Dec 2024',
        'vintage': '2026-02',
        'provider_series_id': f"CPI (General), All India, {sector}, Back Series",
        'geography': 'India', 'quality_status': 'official_source_observation; CPI 2024-base back series',
        'raw_file': relative(CPI_RAW), 'hash': sha(CPI_RAW),
    })
    inflation = row.get('inflation')
    if inflation not in (None, ''):
        cpi_records.append({
            'obs_date': date, 'series_id': yoy_ids[sector], 'value': float(inflation),
            'unit': 'percent year-over-year', 'frequency': 'monthly', 'source': 'MoSPI',
            'source_url': CPI_URL, 'release_date': '2026-02-12', 'retrieved_at': retrieved_cpi,
            'base_year': '2024', 'seasonal_adjustment': '',
            'revision_tag': 'Official published annual inflation in the 2024-base CPI back series',
            'vintage': '2026-02',
            'provider_series_id': f"CPI (General) inflation, All India, {sector}, Back Series",
            'geography': 'India', 'quality_status': 'official_source_observation; CPI 2024-base back series',
            'raw_file': relative(CPI_RAW), 'hash': sha(CPI_RAW),
        })
index_rows = [r for r in cpi_records if r['unit'] == 'index 2024=100']
if len(api_rows) != 432 or len(index_rows) != 432 or len({(r['obs_date'],r['series_id']) for r in index_rows}) != 432:
    raise ValueError(f'CPI completeness check failed: API rows={len(api_rows)}, index rows={len(index_rows)}')

# ---- MoSPI 2012-base CFPI and IIP General monthly series ----
cfpi_raw = json.loads(CFPI_RAW.read_text(encoding='utf-8'))
cfpi_api_rows = [row for page in cfpi_raw['pages'] for row in page.get('data', [])]
cfpi_index_ids = {'Combined':'cfpi_index_2012','Rural':'cfpi_rural_index_2012','Urban':'cfpi_urban_index_2012'}
cfpi_yoy_ids = {'Combined':'cfpi_yoy_2012','Rural':'cfpi_rural_yoy_2012','Urban':'cfpi_urban_yoy_2012'}
cfpi_records=[]
for row in cfpi_api_rows:
    if row.get('state')!='All India' or row.get('group')!='Consumer Food Price' or row.get('subgroup')!='Consumer Food Price-Overall':
        continue
    sector=row['sector']; date=pd.Timestamp(int(row['year']),months[row['month']],1).strftime('%Y-%m-%d')
    retrieved=cfpi_raw.get('retrieved_at_utc',RETRIEVED_FX)
    common={'obs_date':date,'frequency':'monthly','source':'MoSPI','source_url':CPI_API_URL,
            'release_date':'','retrieved_at':retrieved,'base_year':'2012','seasonal_adjustment':'',
            'vintage':'eSankhyiki API snapshot 2026-10','geography':'India',
            'raw_file':relative(CFPI_RAW),'hash':sha(CFPI_RAW)}
    cfpi_records.append({**common,'series_id':cfpi_index_ids[sector],'value':float(row['index']),
        'unit':'index 2012=100','revision_tag':'Official CPI (2012 base) Consumer Food Price Index series; current series',
        'provider_series_id':f'CFPI Consumer Food Price-Overall, All India, {sector}, base 2012',
        'quality_status':'official_source_observation; MoSPI CFPI (2012 base)'})
    inflation=row.get('inflation')
    if inflation not in (None,''):
        cfpi_records.append({**common,'series_id':cfpi_yoy_ids[sector],'value':float(inflation),
            'unit':'percent year-over-year','revision_tag':'Official published CFPI year-over-year inflation; 2012 base',
            'provider_series_id':f'CFPI Consumer Food Price inflation, All India, {sector}, base 2012',
            'quality_status':'official_source_observation; MoSPI CFPI (2012 base)'})
cfpi_index_rows=[r for r in cfpi_records if r['unit']=='index 2012=100']
cfpi_yoy_rows=[r for r in cfpi_records if r['unit']=='percent year-over-year']
if len(cfpi_index_rows)!=468 or len(cfpi_yoy_rows)!=429:
    raise ValueError(f'CFPI completeness check failed: index={len(cfpi_index_rows)}, official y/y={len(cfpi_yoy_rows)}')

iip_records=[]
iip_raw_specs=[('2011-12',IIP_OLD_RAW,168),('2022-23',IIP_NEW_RAW,41)]
for base,raw_path,expected in iip_raw_specs:
    iip_raw=json.loads(raw_path.read_text(encoding='utf-8'))
    iip_api_rows=[row for page in iip_raw['pages'] for row in page.get('data', [])]
    if len(iip_api_rows)!=expected or any(row.get('type')!='General' for row in iip_api_rows):
        raise ValueError(f'IIP API validation failed for base {base}: got {len(iip_api_rows)} rows')
    suffix=base.replace('-','_')
    retrieved=iip_raw.get('retrieved_at_utc',RETRIEVED_FX)
    for row in iip_api_rows:
        date=pd.Timestamp(int(row['year']),months[row['month']],1).strftime('%Y-%m-%d')
        common={'obs_date':date,'frequency':'monthly','source':'MoSPI','source_url':IIP_API_URL,
                'release_date':'','retrieved_at':retrieved,'base_year':base,'seasonal_adjustment':'',
                'vintage':f'eSankhyiki API snapshot {retrieved[:10]}','geography':'India',
                'raw_file':relative(raw_path),'hash':sha(raw_path)}
        iip_records.append({**common,'series_id':f'iip_general_index_{suffix}','value':float(row['index']),
            'unit':f'index {base}=100','revision_tag':f'Official IIP General monthly index; base {base}',
            'provider_series_id':f'IIP General monthly index, base {base}',
            'quality_status':'official_source_observation; IIP General index'})
        growth=row.get('growth_rate')
        if growth not in (None,'','-'):
            iip_records.append({**common,'series_id':f'iip_general_growth_{suffix}','value':float(growth),
                'unit':'percent year-over-year','revision_tag':f'Official IIP General monthly growth rate; base {base}',
                'provider_series_id':f'IIP General monthly growth, base {base}',
                'quality_status':'official_source_observation; publisher-reported growth rate'})

# ---- RBI Reference Rate Archive: USD (INR per USD), daily ----
fx_html = FX_RAW.read_text(encoding='utf-8', errors='replace')
table = BeautifulSoup(fx_html, 'html.parser').find('table')
if table is None:
    raise ValueError('RBI export contains no HTML table')
tr_rows = table.select('tr')
values = [[c.get_text(' ', strip=True) for c in tr.select('th,td')] for tr in tr_rows]
if not values or values[0][:2] != ['Date', 'USD (INR / 1 USD)']:
    raise ValueError(f'Unexpected RBI export header: {values[0] if values else None}')
fx = pd.DataFrame(values[1:], columns=values[0])
fx['obs_date'] = pd.to_datetime(fx['Date'], format='%d/%m/%Y', errors='coerce')
fx['value'] = pd.to_numeric(fx['USD (INR / 1 USD)'].str.replace(',', '', regex=False), errors='coerce')
fx = fx.dropna(subset=['obs_date','value']).drop_duplicates('obs_date').sort_values('obs_date')
if fx.empty or fx['obs_date'].min() != pd.Timestamp('2013-01-01') or fx['obs_date'].max() != pd.Timestamp('2026-10-05'):
    raise ValueError('RBI daily coverage does not match the verified archive window: '
                     f"{fx['obs_date'].min()} to {fx['obs_date'].max()}")
fx_records = []
for _, row in fx.iterrows():
    fx_records.append({
        'obs_date': row['obs_date'].strftime('%Y-%m-%d'), 'series_id': 'usd_inr_reference_rate',
        'value': float(row['value']), 'unit': 'INR/USD', 'frequency': 'daily',
        'source': 'RBI Reference Rate Archive', 'source_url': FX_URL,
        'release_date': '', 'retrieved_at': RETRIEVED_FX, 'base_year': '',
        'seasonal_adjustment': '', 'revision_tag': '', 'vintage': '',
        'provider_series_id': 'USD (INR / 1 USD)', 'geography': 'India',
        'quality_status': 'official_source_observation; RBI reference rate',
        'raw_file': relative(FX_RAW), 'hash': sha(FX_RAW),
    })
# Full calendar-month arithmetic means only; exclude the still-open October 2026.
fx['month'] = fx['obs_date'].dt.to_period('M')
last_full_month = fx['obs_date'].max().to_period('M') - 1
monthly_fx = (fx[fx['month'] <= last_full_month]
              .groupby('month', as_index=False)
              .agg(value=('value','mean'), daily_observation_count=('value','size'),
                   first_source_date=('obs_date','min'), last_source_date=('obs_date','max')))
monthly_fx_records = []
for _, row in monthly_fx.iterrows():
    month_date = row['month'].to_timestamp()
    monthly_fx_records.append({
        'obs_date': month_date.strftime('%Y-%m-%d'), 'series_id': 'usd_inr_monthly_average',
        'value': float(row['value']), 'unit': 'INR/USD', 'frequency': 'monthly',
        'source': 'RBI Reference Rate Archive', 'source_url': FX_URL,
        'release_date': '', 'retrieved_at': RETRIEVED_FX, 'base_year': '',
        'seasonal_adjustment': '',
        'revision_tag': 'Derived arithmetic mean of daily RBI USD reference rates; complete calendar months only',
        'vintage': '', 'provider_series_id': 'USD (INR / 1 USD), monthly arithmetic mean',
        'geography': 'India', 'quality_status': 'derived_from_official_daily_observations; complete calendar month',
        'raw_file': relative(FX_RAW), 'hash': sha(FX_RAW),
    })
if len(fx) != 2415 or len(monthly_fx) != 121:
    raise ValueError(f'RBI data validation failed: daily={len(fx)}, full months={len(monthly_fx)}')

# ---- Idempotently merge canonical observations ----
new_rows = pd.DataFrame(cpi_records + cfpi_records + iip_records + fx_records + monthly_fx_records)
old = pd.read_csv(OBS_PATH, low_memory=False, dtype={'release_date':'string','revision_tag':'string'})
key = ['obs_date','series_id','frequency','geography']
owned_keys = set(map(tuple, new_rows[key].fillna('').astype(str).to_numpy()))
old_keys = old[key].fillna('').astype(str).apply(tuple, axis=1)
old = old[~old_keys.isin(owned_keys)]
merged = pd.concat([old, new_rows], ignore_index=True, sort=False)
merged = merged.drop_duplicates(key, keep='last').sort_values(['series_id','obs_date'])
merged.to_csv(OBS_PATH, index=False)

# Historical/current unified CPI panel with source regime flags and derived y/y features.
month_map = {sid: (key, col) for sid,key,col in [
    ('cpi_index_2024','Combined','combined_index'),
    ('cpi_rural_index_2024','Rural','rural_index'),
    ('cpi_urban_index_2024','Urban','urban_index'),
    ('cpi_yoy_2024','Combined','combined_yoy_official'),
    ('cpi_rural_yoy_2024','Rural','rural_yoy_official'),
    ('cpi_urban_yoy_2024','Urban','urban_yoy_official'),
]}
all_obs = pd.read_csv(OBS_PATH, low_memory=False)
cpi = all_obs[all_obs['series_id'].isin(month_map)].copy()
cpi['date'] = pd.to_datetime(cpi['obs_date'])
wide = cpi.pivot_table(index='date', columns='series_id', values='value', aggfunc='last')
wide = wide.rename(columns={sid: col for sid, (_, col) in month_map.items()})
wide.index.name='date'
wide = wide.reset_index()
wide['cpi_yoy_derived'] = wide['combined_index'].pct_change(12) * 100
wide['cpi_rural_yoy_derived'] = wide['rural_index'].pct_change(12) * 100
wide['cpi_urban_yoy_derived'] = wide['urban_index'].pct_change(12) * 100
wide['base_year'] = '2024=100'
wide['source_regime'] = wide['date'].apply(lambda d: 'official_back_series' if d.year <= 2024 else 'August_2026_Annex_IV_release')
wide['release_snapshot_date'] = wide['date'].apply(lambda d: '2026-02-12' if d.year <= 2024 else '2026-09-14')
wide['date'] = wide['date'].dt.strftime('%Y-%m-%d')
wide = wide.sort_values('date')
wide.to_csv(PROC/'mospi_cpi_2024base_all_india_monthly.csv', index=False)
# Preserve the legacy wide filename/column contract while extending its date span.
legacy_cols = ['date','rural_index','urban_index','combined_index','rural_yoy_official','urban_yoy_official','combined_yoy_official']
legacy = wide.rename(columns={'rural_yoy_official':'rural_yoy','urban_yoy_official':'urban_yoy','combined_yoy_official':'combined_yoy'})
legacy[['date','rural_index','urban_index','combined_index','rural_yoy','urban_yoy','combined_yoy']].to_csv(
    PROC/'mospi_cpi_2024base_available_months.csv', index=False)

# Keep older-base food inflation separate from the 2024-base headline CPI panel.
cfpi_ids={
    'cfpi_rural_index_2012':'rural_index','cfpi_urban_index_2012':'urban_index','cfpi_index_2012':'combined_index',
    'cfpi_rural_yoy_2012':'rural_yoy_official','cfpi_urban_yoy_2012':'urban_yoy_official','cfpi_yoy_2012':'combined_yoy_official'}
cfpi_panel=(all_obs[all_obs['series_id'].isin(cfpi_ids)].assign(date=lambda d:pd.to_datetime(d['obs_date']))
            .pivot_table(index='date',columns='series_id',values='value',aggfunc='last')
            .rename(columns=cfpi_ids).reset_index())
cfpi_panel['base_year']='2012=100'; cfpi_panel['source_series']='MoSPI Consumer Food Price Index (CFPI)'
cfpi_panel['date']=cfpi_panel['date'].dt.strftime('%Y-%m-%d')
cfpi_panel.to_csv(PROC/'mospi_cfpi_2012base_all_india_monthly.csv',index=False)

# Do not splice IIP across the old and revised bases; keep both observed panels side by side.
iip_ids=['iip_general_index_2011_12','iip_general_growth_2011_12',
         'iip_general_index_2022_23','iip_general_growth_2022_23']
iip_panel=(all_obs[all_obs['series_id'].isin(iip_ids)].assign(date=lambda d:pd.to_datetime(d['obs_date']))
           .pivot_table(index='date',columns='series_id',values='value',aggfunc='last').reset_index())
iip_panel['date']=iip_panel['date'].dt.strftime('%Y-%m-%d')
iip_panel.to_csv(PROC/'mospi_iip_general_monthly_by_base.csv',index=False)

# Separate transparent daily and monthly FX extracts for analysis and training.
fx_out = fx[['obs_date','value']].rename(columns={'obs_date':'date','value':'inr_per_usd'})
fx_out['source']='RBI Reference Rate Archive'
fx_out['raw_file']=relative(FX_RAW)
fx_out.to_csv(PROC/'rbi_usd_inr_reference_rate_daily.csv', index=False, date_format='%Y-%m-%d')
monthly_fx_out = monthly_fx.rename(columns={'month':'date','value':'monthly_mean_inr_per_usd',
    'daily_observation_count':'daily_observation_count','first_source_date':'first_source_date','last_source_date':'last_source_date'})
monthly_fx_out['date']=monthly_fx_out['date'].dt.to_timestamp()
monthly_fx_out['source']='Derived from RBI Reference Rate Archive'
monthly_fx_out['raw_file']=relative(FX_RAW)
monthly_fx_out.to_csv(PROC/'rbi_usd_inr_monthly_average.csv', index=False, date_format='%Y-%m-%d')

# Add or replace manifest entries for the two immutable raw snapshots.
manifest_path = MAN/'ingestion_manifest.csv'
manifest = pd.read_csv(manifest_path, low_memory=False).fillna('')
source_paths=[CPI_RAW,FX_RAW,CFPI_RAW,IIP_OLD_RAW,IIP_NEW_RAW]
manifest = manifest[~manifest['raw_file'].isin([relative(p) for p in source_paths])]
entries = [
    {'provider':'mospi','series_or_table':'CPI 2024-base Back Series, All India CPI (General), Rural/Urban/Combined',
     'source_url':CPI_URL,'retrieved_at_utc':retrieved_cpi,'raw_file':relative(CPI_RAW),'sha256':sha(CPI_RAW),
     'bytes':CPI_RAW.stat().st_size,'status':'downloaded','notes':'eSankhyiki public API; base_year=2024, series=Back, years=2013–2024, All India state code=1, sectors=Rural/Urban/Combined, CPI (General); five paginated JSON responses.',
     'observation_count':432},
    {'provider':'rbi','series_or_table':'Reference Rate Archive — USD (INR per USD), daily',
     'source_url':FX_URL,'retrieved_at_utc':RETRIEVED_FX,'raw_file':relative(FX_RAW),'sha256':sha(FX_RAW),
     'bytes':FX_RAW.stat().st_size,'status':'downloaded','notes':'Official Excel-compatible HTML export; USD only; requested 01/01/2013–05/10/2026; daily data retained; archive has no observations Aug 2018–Mar 2022; monthly arithmetic means separately derived for observed complete months only.',
     'observation_count':len(fx)},
    {'provider':'mospi','series_or_table':'CFPI Consumer Food Price-Overall, All India, Rural/Urban/Combined, 2012 base',
     'source_url':CPI_API_URL,'retrieved_at_utc':cfpi_raw.get('retrieved_at_utc',''),'raw_file':relative(CFPI_RAW),'sha256':sha(CFPI_RAW),
     'bytes':CFPI_RAW.stat().st_size,'status':'downloaded','notes':'Official eSankhyiki CPI API; base_year=2012, series=Current, group_code=7 Consumer Food Price, state_code=99 All India, sectors=1/2/3, years 2013–2025; paginated response preserved.',
     'observation_count':len(cfpi_index_rows)},
    {'provider':'mospi','series_or_table':'IIP General monthly, 2011-12 base',
     'source_url':IIP_API_URL,'retrieved_at_utc':json.loads(IIP_OLD_RAW.read_text(encoding='utf-8')).get('retrieved_at_utc',''),
     'raw_file':relative(IIP_OLD_RAW),'sha256':sha(IIP_OLD_RAW),'bytes':IIP_OLD_RAW.stat().st_size,'status':'downloaded',
     'notes':'Official eSankhyiki IIP monthly API; type=General; base_year=2011-12; 168 monthly index records returned. Separate from 2022-23 base.',
     'observation_count':168},
    {'provider':'mospi','series_or_table':'IIP General monthly, 2022-23 base',
     'source_url':IIP_API_URL,'retrieved_at_utc':json.loads(IIP_NEW_RAW.read_text(encoding='utf-8')).get('retrieved_at_utc',''),
     'raw_file':relative(IIP_NEW_RAW),'sha256':sha(IIP_NEW_RAW),'bytes':IIP_NEW_RAW.stat().st_size,'status':'downloaded',
     'notes':'Official eSankhyiki IIP monthly API; type=General; base_year=2022-23; 41 monthly index records returned. Separate from 2011-12 base; no backcast or linking performed.',
     'observation_count':41},
]
manifest = pd.concat([manifest,pd.DataFrame(entries)],ignore_index=True,sort=False)
manifest.to_csv(manifest_path,index=False)

# Coverage rows reflect what was actually downloaded, without implying the whole brief is complete.
coverage_path=MAN/'coverage_matrix.csv'
coverage=pd.read_csv(coverage_path,low_memory=False).fillna('')
for i,row in coverage.iterrows():
    if row['requested_area']=='MoSPI headline CPI':
        coverage.loc[i,'status']='expanded_partial'
        coverage.loc[i,'available_series_or_file']='cpi_index_2024; cpi_rural_index_2024; cpi_urban_index_2024; official CPI y/y series; mospi_cpi_2024base_all_india_monthly.csv'
        coverage.loc[i,'coverage']='2024-base general index Jan 2013–Aug 2026; official back-series y/y Jan 2014–Dec 2024 plus current-release y/y where published'
        coverage.loc[i,'limitation']='No continuous CPI component-level history. CFPI is available separately on the old 2012 base; do not splice it into the 2024-base CPI series. CPI release vintage differs by period.'
    if row['requested_area']=='MoSPI food inflation':
        coverage.loc[i,'status']='partial'
        coverage.loc[i,'available_series_or_file']='CFPI All-India rural/urban/combined 2012-base index and official y/y; mospi_cfpi_2012base_all_india_monthly.csv'
        coverage.loc[i,'coverage']='Jan 2013–Dec 2025; 468 index records and 429 publisher-reported y/y values'
        coverage.loc[i,'limitation']='CFPI series remains on 2012 base and is separate from the 2024-base headline CPI; no seamless post-2025 CFPI index panel or full component back history added.'
    if row['requested_area']=='MoSPI industrial production':
        coverage.loc[i,'status']='partial'
        coverage.loc[i,'available_series_or_file']='IIP General index and official growth rate, base 2011-12 and base 2022-23; mospi_iip_general_monthly_by_base.csv'
        coverage.loc[i,'coverage']='2011-12 base Apr 2012–Mar 2026 (168 months); 2022-23 base Apr 2023–Aug 2026 (41 months)'
        coverage.loc[i,'limitation']='General index only. Base regimes are separate and not linked; sectoral, manufacturing/use-based category panels are not included.'
    if row['requested_area']=='RBI FX':
        coverage.loc[i,'status']='partial'
        coverage.loc[i,'available_series_or_file']='usd_inr_reference_rate (daily); usd_inr_monthly_average (full-month mean); RBI raw export'
        coverage.loc[i,'coverage']='Daily available observations Jan 2013–05 Oct 2026; 121 observed complete months Jan 2013–Jul 2018 and Apr 2022–Sep 2026'
        coverage.loc[i,'limitation']='RBI archive explicitly returns “No Reference Rate Found” for 2019–2021 and has no rates Aug 2018–Mar 2022; monthly means are missing in that interval. USD reference rate is not a market close/transaction rate; other RBI FX, reserves, effective indices and external accounts remain missing.'
coverage.to_csv(coverage_path,index=False)

# Source research notes are curated separately and are not mutated by this normalizer.

# Rebuild canonical provenance, catalog, monthly feature table and quality report.
subprocess.run([sys.executable, str(ROOT/'scripts/finalize_dataset.py')], check=True, cwd=ROOT)
qpath=MAN/'data_quality_report.json'
q=json.loads(qpath.read_text(encoding='utf-8'))
q['coverage_gaps']=[
    'MoSPI 2024-base All-India CPI (General) index is continuous monthly from Jan 2013 to Aug 2026. Official CFPI is available separately on the 2012 base through Dec 2025; it is not a spliced continuation of the 2024-base CPI. Continuous CPI division/group/item histories remain missing.',
    'RBI USD reference rates are included for available dates Jan 2013 through 05 Oct 2026; the archive has no observations Aug 2018–Mar 2022 and explicitly returns “No Reference Rate Found” for 2019–2021. Complete-month means include 121 observed months through Sep 2026. This is the RBI reference rate, not a market close/transaction rate. Other exchange, reserve, credit, WPI, yield, liquidity and external accounts series remain missing.',
    'RBI Table 40 policy-event history ends in Dec 2025; selected rates and FX values are separately recorded in a one-date snapshot as of 05 Oct 2026 13:00 IST. That snapshot is not backfilled into the historical event series.',
    'MoSPI IIP General monthly index and official growth rate are included separately for the 2011-12 base (Apr 2012–Mar 2026) and 2022-23 base (Apr 2023–Aug 2026). Do not splice the bases; sectoral/manufacturing/use-based IIP panels are not included. The latest Q1 FY2026-27 NAS press-note PDF is included but is not parsed into quarterly observations.',
    'IMD actual monthly rainfall covers 1901–2024; official normals/departure series not included. Derived anomaly uses 1991–2020 mean and is clearly labeled.',
    'No supervised lags, rolling predictors or forecast target columns were created. For real-time backtests, align CPI values with release dates and vintage availability to avoid look-ahead leakage.',
    'Annual IMF/WDI observations are not monthly-upsampled. IMF WEO rows can include forecasts through 2031.'
]
q['current_snapshot_files']=['data/processed/rbi_current_rates_snapshot_2026-10-05.csv']
q['training_readiness_note']='Suitable for cautious baseline and time-based evaluation of the 2024-base India headline CPI series, with separate older-base CFPI and IIP context series. Not point-in-time/backtest-ready until historical release dates/vintages are aligned.'
qpath.write_text(json.dumps(q,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

print(json.dumps({'cpi_backseries_rows':len(cpi_records),'cpi_index_rows':len(index_rows),
                  'cpi_official_yoy_rows':len(cpi_records)-len(index_rows),
                  'cfpi_index_rows':len(cfpi_index_rows),'cfpi_official_yoy_rows':len(cfpi_yoy_rows),
                  'iip_rows':len(iip_records),
                  'rbi_daily_rows':len(fx),'rbi_complete_months':len(monthly_fx),
                  'canonical_observations':len(merged),'cpi_coverage':'2013-01 to 2026-08',
                  'fx_daily_coverage':'2013-01-01 to 2026-10-05'},indent=2))
