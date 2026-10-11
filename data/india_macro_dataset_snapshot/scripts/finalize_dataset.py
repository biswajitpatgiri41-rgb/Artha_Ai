#!/usr/bin/env python3
"""Attach raw provenance, derive documented monthly fields, and validate the package."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, glob
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw'; PROC=ROOT/'data/processed'; MAN=ROOT/'data/manifests'
OBS=PROC/'macro_observations.csv'
manifest=pd.read_csv(MAN/'ingestion_manifest.csv').fillna('')
df=pd.read_csv(OBS).fillna({'geography':'','provider_series_id':'','base_year':'','seasonal_adjustment':''})

def newest(pattern):
    found=sorted(glob.glob(str(ROOT/pattern)))
    return Path(found[-1]) if found else None

def choose(row):
    source=str(row.get('source','')); sid=str(row.get('series_id','')); pid=str(row.get('provider_series_id','')); freq=str(row.get('frequency','')); geo=str(row.get('geography',''))
    if source=='FRED': p=newest(f'data/raw/fred/{pid}_*.csv')
    elif source=='EIA': p=newest('data/raw/eia/RBRTEm_*.xls' if freq=='monthly' else 'data/raw/eia/RBRTEd_*.xls')
    elif source=='IMF WEO DataMapper': p=newest(f'data/raw/imf/{pid}_*.json')
    elif source=='World Bank WDI':
        iso='IND' if geo=='India' else 'WLD'
        p=newest(f'data/raw/world_bank/{iso}_{pid}_*.json')
    elif source=='IMD': p=newest('data/raw/imd/whole_india_rainfall_*.html')
    elif source=='MoSPI': p=newest('data/raw/mospi/cpi/*Annex-IV*.xlsx')
    elif source=='RBI HSIE': p=ROOT/'data/raw/rbi/policy/table40_policy_rates.xlsx'
    else: p=None
    if p and p.exists():
        b=p.read_bytes()
        return str(p.relative_to(ROOT)),hashlib.sha256(b).hexdigest()
    return '',''

paths=[]; hashes=[]
for _,r in df.iterrows():
    p,h=choose(r); paths.append(p); hashes.append(h)
df['raw_file']=paths; df['hash']=hashes
# Release-date and revision provenance for the current CPI snapshot only.
df['release_date']=df['release_date'].fillna('').astype(str)
df['revision_tag']=df['revision_tag'].fillna('').astype(str)
mospi=df['source'].eq('MoSPI')
df.loc[mospi,'release_date']='2026-09-14'
df.loc[mospi,'revision_tag']='August 2026 release; Aug-2026 provisional'
df.to_csv(OBS,index=False)

# Build monthly dataset from native monthly observations, with explicit transforms only.
mon=df[df['frequency'].eq('monthly')].pivot_table(index='obs_date',columns='series_id',values='value',aggfunc='last')
mon.index=pd.to_datetime(mon.index)
# Add daily yield monthly means (business-day observations averaged by calendar month).
daily=df[df['frequency'].eq('daily') & df['series_id'].isin(['us_10y_yield','us_2y_yield','us_3m_yield'])].copy()
if not daily.empty:
    daily['month']=pd.to_datetime(daily['obs_date']).dt.to_period('M').dt.to_timestamp()
    av=daily.pivot_table(index='month',columns='series_id',values='value',aggfunc='mean')
    av=av.rename(columns={c:c+'_monthly_average' for c in av.columns})
    mon=mon.join(av,how='outer')
# Effective month-end policy settings are stepwise only between official event dates.
events=PROC/'rbi_policy_rate_events.csv'
if events.exists():
    ev=pd.read_csv(events,parse_dates=['effective_date']).sort_values('effective_date')
    cols={'bank_rate_pct':'bank_rate','repo_rate_pct':'repo_rate','reverse_repo_rate_pct':'reverse_repo_rate','sdf_rate_pct':'sdf_rate','msf_rate_pct':'msf_rate','crr_pct':'crr','slr_pct':'slr'}
    monthends=pd.date_range(ev.effective_date.min().to_period('M').to_timestamp(),ev.effective_date.max().to_period('M').to_timestamp(),freq='ME')
    expanded=pd.DataFrame({'month_end':monthends})
    for c,name in cols.items():
        series=ev[['effective_date',c]].dropna().sort_values('effective_date')
        if series.empty: continue
        temp=pd.merge_asof(expanded[['month_end']].sort_values('month_end'),series,left_on='month_end',right_on='effective_date',direction='backward')
        # Keep values only through the latest event in the source; never extrapolate after last event month.
        temp.loc[temp['month_end']>series['effective_date'].max().to_period('M').to_timestamp('M'),'value']=np.nan
        mon[name]=mon.reindex(mon.index.union(pd.DatetimeIndex(temp.month_end))).sort_index()[name] if name in mon else np.nan
        month_starts=temp['month_end'].dt.to_period('M').dt.to_timestamp()
        mon.loc[month_starts.values,name]=temp[c].values
# Explicit derived values.
if 'brent_price' in mon: mon['oil_yoy']=100*mon['brent_price'].pct_change(12)
if 'us_cpi_index' in mon: mon['us_cpi_yoy']=100*mon['us_cpi_index'].pct_change(12)
if 'us_10y_yield_monthly_average' in mon and 'us_2y_yield_monthly_average' in mon:
    mon['us_yield_curve_10y_minus_2y']=mon['us_10y_yield_monthly_average']-mon['us_2y_yield_monthly_average']
if 'repo_rate' in mon:
    mon['repo_change_1m']=mon['repo_rate'].diff(1)
    mon['repo_change_3m']=mon['repo_rate'].diff(3)
month_num=mon.index.month
mon['month_sin']=np.sin(2*np.pi*month_num/12); mon['month_cos']=np.cos(2*np.pi*month_num/12)
# Derived rainfall anomaly: calendar-month actual minus the 1991–2020 mean, not an official IMD departure.
if 'rainfall_actual' in mon:
    baseline=mon.loc[(mon.index.year>=1991)&(mon.index.year<=2020),'rainfall_actual'].groupby(mon.loc[(mon.index.year>=1991)&(mon.index.year<=2020)].index.month).mean()
    mon['rainfall_anomaly_1991_2020_mm']=[(v-baseline.get(d.month,np.nan)) if pd.notna(v) else np.nan for d,v in mon['rainfall_actual'].items()]
mon.index.name='obs_date'; mon=mon.sort_index(); mon.reset_index().to_csv(PROC/'macro_monthly_available.csv',index=False,date_format='%Y-%m-%d')

# Catalog of canonical series with observation span and exact raw snapshot provenance.
cat=[]
for sid,g in df.groupby('series_id',sort=True):
    first=g.iloc[0]
    cat.append({'series_id':sid,'provider_series_id':first.get('provider_series_id',''),'source':first.get('source',''),
                'source_url':first.get('source_url',''),'frequency':first.get('frequency',''),'unit':first.get('unit',''),
                'geography':first.get('geography',''),'base_year':first.get('base_year',''),
                'seasonal_adjustment':first.get('seasonal_adjustment',''),'observations':len(g),
                'earliest_observation':g['obs_date'].min(),'latest_observation':g['obs_date'].max(),
                'raw_file':first.get('raw_file',''),'sha256':first.get('hash','')})
pd.DataFrame(cat).to_csv(MAN/'series_catalog.csv',index=False)

# Reconcile raw-file SHA-256 values recorded in manifest.
for idx,row in manifest.iterrows():
    rel=str(row.get('raw_file',''))
    if rel and rel not in ('nan',''):
        p=ROOT/rel
        if p.exists():
            actual=hashlib.sha256(p.read_bytes()).hexdigest()
            if str(row.get('sha256','')) not in ('', 'nan', actual):
                raise ValueError(f'Checksum mismatch in manifest for {rel}')
        else:
            raise FileNotFoundError(f'Manifest raw_file does not exist: {rel}')

# Build concise data-quality and coverage totals.
key=['obs_date','series_id','frequency','geography']
q={'generated_at_utc':datetime.now(timezone.utc).isoformat(),'observation_rows':len(df),'unique_series':int(df.series_id.nunique()),
   'duplicate_canonical_keys':int(df.duplicated(key).sum()),'unmapped_raw_file_rows':int((df.raw_file=='').sum()),
   'raw_file_hash_rows':int((df.hash!='').sum()),'monthly_table_rows':len(mon),'monthly_features':list(pd.read_csv(PROC/'macro_monthly_available.csv',nrows=0).columns),
   'source_coverage':df.groupby('source').size().to_dict(),
   'coverage_gaps':['MoSPI full historical CPI/CFPI/IIP and parsed quarterly GDP/GVA history were not obtained; current CPI Annex-IV has 20 2024-base index months (Jan-2025–Aug-2026), with official y/y only Jan–Aug 2026; latest Q1 FY2026-27 NAS press-note PDF is included but not parsed.',
   'RBI Table 40 policy event data included; requested WPI, exchange rates, M3, credit, WACR, Indian yields, forex reserves and external accounts not downloaded in this pass.',
   'IMD actual monthly rainfall covers 1901–2024; official normals/departure series not included. Derived anomaly uses 1991–2020 mean and is clearly labeled.',
   'Forecast targets and supervised lag/rolling features were not generated because the required continuous Indian CPI target history is unavailable.',
   'Annual IMF/WDI observations are not monthly-upsampled. IMF WEO rows can include forecasts through 2031.']}
(MAN/'data_quality_report.json').write_text(json.dumps(q,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'rows':len(df),'series':df.series_id.nunique(),'unmapped_raw_file_rows':q['unmapped_raw_file_rows'],'duplicates':q['duplicate_canonical_keys'],'monthly_rows':len(mon),'monthly_columns':list(mon.columns)},indent=2))
