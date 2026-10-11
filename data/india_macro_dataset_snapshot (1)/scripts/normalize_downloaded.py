#!/usr/bin/env python3
"""Normalize already-downloaded official source snapshots; performs no network I/O."""
from pathlib import Path
from datetime import datetime, timezone
import glob, hashlib, json, re, shutil, io
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw'; PROC=ROOT/'data/processed'; MAN=ROOT/'data/manifests'
PROC.mkdir(parents=True,exist_ok=True); MAN.mkdir(parents=True,exist_ok=True)
URL_IMD='https://dsp.imdpune.gov.in/home_ogd_rainfall.php'
URL_RBI40='https://rbi.org.in/Scripts/PublicationsView.aspx?id=23865'
URL_CPI='https://esankhyiki.mospi.gov.in/catalogue-main/catalogue?product=CPI'
retrieved=datetime.now(timezone.utc).isoformat()
obs=[]
def add(date,sid,value,unit,freq,source,url,provider_id='',geo='',base='',sa='',vintage='',quality='official_source_observation'):
    if value is None or pd.isna(value): return
    obs.append({'obs_date':pd.Timestamp(date).strftime('%Y-%m-%d'),'series_id':sid,'value':float(value),'unit':unit,
                'frequency':freq,'source':source,'source_url':url,'release_date':'','retrieved_at':retrieved,
                'base_year':base,'seasonal_adjustment':sa,'revision_tag':'','vintage':vintage,
                'provider_series_id':provider_id,'geography':geo,'quality_status':quality})

# EIA workbooks: the actual data are on Data 1; row 3 in Excel contains headers.
eia_urls={'monthly':'https://www.eia.gov/dnav/pet/hist_xls/RBRTEm.xls','daily':'https://www.eia.gov/dnav/pet/hist_xls/RBRTEd.xls'}
for freq,url in eia_urls.items():
    matches=glob.glob(str(RAW/'eia'/('RBRTEm_*.xls' if freq=='monthly' else 'RBRTEd_*.xls')))
    if not matches: continue
    p=Path(sorted(matches)[-1]); tab=pd.read_excel(p,sheet_name='Data 1',header=2)
    dc=next(c for c in tab if str(c).strip().lower()=='date'); vc=next(c for c in tab if c!=dc)
    out=[]
    for _,r in tab.iterrows():
        dt=pd.to_datetime(r[dc],errors='coerce')
        if pd.isna(dt) or pd.isna(r[vc]): continue
        dt=dt.to_period('M').to_timestamp() if freq=='monthly' else dt
        add(dt,'brent_price',r[vc],'USD/barrel',freq,'EIA',url,'RBRTE')
        out.append({'obs_date':dt.date().isoformat(),'brent_price_usd_per_barrel':float(r[vc])})
    pd.DataFrame(out).to_csv(PROC/f'eia_brent_{freq}.csv',index=False)

# IMD all-India free monthly/seasonal series: header is the first row inside the data table.
for p in sorted((RAW/'imd').glob('whole_india_rainfall_*.html')):
    html=p.read_text(errors='ignore'); tables=pd.read_html(io.StringIO(html))
    source_table=next(t for t in tables if t.shape[0]>100 and str(t.iloc[0,0]).strip().lower()=='year')
    rain=source_table.copy(); rain.columns=[str(x).strip() for x in rain.iloc[0].tolist()]; rain=rain.iloc[1:].reset_index(drop=True)
    rain=rain.rename(columns={rain.columns[0]:'year'}); rain['year']=pd.to_numeric(rain['year'],errors='coerce'); rain=rain.dropna(subset=['year']); rain['year']=rain['year'].astype(int)
    rain.to_csv(PROC/'imd_whole_india_monthly_and_seasonal_wide.csv',index=False)
    months=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    monthly=[]; seasonal=[]
    for _,r in rain.iterrows():
        y=int(r['year'])
        for i,m in enumerate(months,1):
            if m in rain.columns and pd.notna(r[m]):
                dt=pd.Timestamp(y,i,1)
                val=float(r[m]); monthly.append({'obs_date':dt.date().isoformat(),'series_id':'rainfall_actual','value_mm':val,'frequency':'monthly','source':'IMD','source_url':URL_IMD,'geography':'Whole India'})
                add(dt,'rainfall_actual',val,'mm','monthly','IMD',URL_IMD,'Whole India monthly rainfall','Whole India')
        for c in rain.columns:
            if c in ('Annual','Winter Season Jan-Feb','Pre-Monsoon Season Mar-May','Monsoon Season Jun-Sep','Post-Monsoon Season Oct-Dec') and pd.notna(r[c]):
                seasonal.append({'year':y,'period':c,'rainfall_mm':float(r[c]),'source':'IMD','source_url':URL_IMD})
    pd.DataFrame(monthly).to_csv(PROC/'imd_whole_india_monthly_long.csv',index=False)
    pd.DataFrame(seasonal).to_csv(PROC/'imd_whole_india_seasonal.csv',index=False)
    break

# RBI HSIE table 40: event-date observations. An initial source workbook was downloaded successfully.
rbi=RAW/'rbi'/'policy'/'table40_policy_rates.xlsx'
if rbi.exists():
    wb=pd.ExcelFile(rbi); rows=[]
    for sn in wb.sheet_names:
        t=pd.read_excel(rbi,sheet_name=sn,header=None)
        for _,r in t.iterrows():
            dt=pd.to_datetime(r.iloc[1],errors='coerce') if len(r)>1 else pd.NaT
            if pd.isna(dt): continue
            values=[]
            for i in range(2,9):
                v=r.iloc[i] if len(r)>i else None
                if isinstance(v,str) and v.strip() in ('-','–','—',''): v=None
                n=pd.to_numeric(v,errors='coerce'); values.append(None if pd.isna(n) else float(n))
            if any(v is not None for v in values): rows.append([dt.date().isoformat(),*values])
    cols=['effective_date','bank_rate_pct','repo_rate_pct','reverse_repo_rate_pct','sdf_rate_pct','msf_rate_pct','crr_pct','slr_pct']
    ev=pd.DataFrame(rows,columns=cols).drop_duplicates().sort_values('effective_date')
    ev.to_csv(PROC/'rbi_policy_rate_events.csv',index=False)
    for _,r in ev.iterrows():
        for col,sid in [('bank_rate_pct','bank_rate'),('repo_rate_pct','repo_rate'),('reverse_repo_rate_pct','reverse_repo_rate'),('sdf_rate_pct','sdf_rate'),('msf_rate_pct','msf_rate'),('crr_pct','crr'),('slr_pct','slr')]:
            add(r['effective_date'],sid,r[col],'percent','event','RBI HSIE',URL_RBI40,'HSIE Table 40',quality='official_source_observation; event-date table')

# MoSPI CPI Annex-IV provides the 2024-base all-India monthly general index and published inflation where present.
mospi_dir=RAW/'mospi'/'cpi'
for p in sorted(mospi_dir.glob('*Annex-IV*.xlsx')):
    t=pd.read_excel(p,sheet_name=0,header=None)
    rows=[]
    for _,r in t.iloc[5:].iterrows():
        rawdate=r.iloc[0]
        if pd.isna(rawdate): continue
        try:
            if isinstance(rawdate,(datetime,pd.Timestamp)): dt=pd.Timestamp(rawdate)
            else: dt=pd.to_datetime(str(rawdate).replace('*','').strip(),format='%b-%y')
        except Exception: continue
        rows.append({'date':dt,'rural_index':r.iloc[1],'urban_index':r.iloc[2],'combined_index':r.iloc[3],
                     'rural_yoy':r.iloc[4],'urban_yoy':r.iloc[5],'combined_yoy':r.iloc[6]})
    cpi=pd.DataFrame(rows).sort_values('date')
    cpi.to_csv(PROC/'mospi_cpi_2024base_available_months.csv',index=False,date_format='%Y-%m-%d')
    for _,r in cpi.iterrows():
        for col,sid,unit in [('rural_index','cpi_rural_index_2024','index 2024=100'),('urban_index','cpi_urban_index_2024','index 2024=100'),('combined_index','cpi_index_2024','index 2024=100'),('rural_yoy','cpi_rural_yoy_2024','percent'),('urban_yoy','cpi_urban_yoy_2024','percent'),('combined_yoy','cpi_yoy_2024','percent')]:
            add(r['date'],sid,r[col],unit,'monthly','MoSPI',URL_CPI,'eSankhyiki Annex-IV','India',base='2024',vintage='August 2026 release; provisional for Aug-2026')
    break

# Preserve all MoSPI August 2026 base-2024 group/division rows as source-shaped snapshots.
for patt,outname in [('*Annex-I*.xlsx','mospi_cpi_aug2026_division_snapshot.csv'),('*Annex-II*.xlsx','mospi_cpi_aug2026_group_snapshot.csv')]:
    found=sorted(mospi_dir.glob(patt))
    if not found: continue
    df=pd.read_excel(found[-1],sheet_name=0,header=None)
    # Data start after title, multi-row heading and column labels.
    if 'Annex-I' in patt:
        data=df.iloc[5:].copy(); data=data.iloc[:,:8]; data.columns=['division_code','division_name','index_rural','index_urban','index_combined','inflation_rural_yoy','inflation_urban_yoy','inflation_combined_yoy']
        data=data.dropna(subset=['division_name'])
    else:
        data=df.iloc[5:].copy(); data=data.iloc[:,:9]; data.columns=['serial','group_code','group_name','index_rural','index_urban','index_combined','inflation_rural_yoy','inflation_urban_yoy','inflation_combined_yoy']
        data=data.dropna(subset=['group_name'])
    data['reference_period']='2026-08'; data['provisional']=True; data['base_year']=2024; data['source_url']=URL_CPI
    data.to_csv(PROC/outname,index=False)

# Merge new observations with those created by the successful first ingestion pass.
obsfile=PROC/'macro_observations.csv'
old=pd.read_csv(obsfile) if obsfile.exists() else pd.DataFrame()
new=pd.DataFrame(obs)
allobs=pd.concat([old,new],ignore_index=True,sort=False)
if not allobs.empty:
    keys=['obs_date','series_id','frequency','geography']
    allobs=allobs.drop_duplicates(keys,keep='last').sort_values(['series_id','obs_date'])
    allobs.to_csv(obsfile,index=False)

# Create documented monthly wide view: preserve only monthly native series, plus explicitly averaged daily US yields.
monthly=allobs[allobs.get('frequency',pd.Series(dtype=str))=='monthly'].copy()
if not monthly.empty:
    monthly=monthly.pivot_table(index='obs_date',columns='series_id',values='value',aggfunc='last').reset_index()
    monthly.columns.name=None
    if 'obs_date' in monthly:
        months=pd.to_datetime(monthly['obs_date']).dt.month
        import numpy as np
        monthly['month_sin']=np.sin(2*np.pi*months/12); monthly['month_cos']=np.cos(2*np.pi*months/12)
    # Daily yields are summarized explicitly as monthly means; no forward fill.
    daily=allobs[(allobs.get('frequency',pd.Series(dtype=str))=='daily') & allobs['series_id'].isin(['us_10y_yield','us_2y_yield','us_3m_yield'])].copy()
    if not daily.empty:
        daily['month']=pd.to_datetime(daily['obs_date']).dt.to_period('M').astype(str)
        av=daily.pivot_table(index='month',columns='series_id',values='value',aggfunc='mean').reset_index()
        av=av.rename(columns={c:c+'_monthly_average' for c in av.columns if c!='month'}).rename(columns={'month':'obs_date'})
        monthly=monthly.merge(av,on='obs_date',how='outer').sort_values('obs_date')
    monthly.to_csv(PROC/'macro_monthly_available.csv',index=False)

# Add checksums and sources for hand-downloaded files not present in the first manifest.
manifest_path=MAN/'ingestion_manifest.csv'
manifest=pd.read_csv(manifest_path) if manifest_path.exists() else pd.DataFrame()
existing=set(manifest.get('raw_file',pd.Series(dtype=str)).dropna().tolist())
def manifest_add(path,provider,series,source,notes):
    rel=str(path.relative_to(ROOT))
    if rel in existing: return
    b=path.read_bytes(); manifest.loc[len(manifest)]={'provider':provider,'series_or_table':series,'source_url':source,'retrieved_at_utc':retrieved,'raw_file':rel,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'status':'downloaded','notes':notes,'observation_count':None}
    existing.add(rel)
for p in [rbi,ROOT/'data/raw/mospi/nas/nas_q1_fy2026_27_official_release.pdf']:
    if p.exists():
        provider='RBI' if 'rbi' in str(p) else 'MoSPI'
        src=URL_RBI40 if provider=='RBI' else 'https://www.mospi.gov.in/uploads/acts_and_policies/acts_and_policies1778231030122_a1a3ee77-e36d-4895-8da5-b294751cbb1a_272304_(1).pdf'
        manifest_add(p,provider,p.name,src,'Official public workbook/PDF; source-preserved')
# Record that the direct catalogue workbook route failed, while the public IIP API snapshots are preserved separately.
iip_note='IIP latest monthly index workbook (Aug 2026)'
if not (manifest['series_or_table'].astype(str)==iip_note).any():
    manifest.loc[len(manifest)]={'provider':'MoSPI','series_or_table':iip_note,'source_url':'https://esankhyiki.mospi.gov.in/catalogue-main/catalogue?product=IIP','retrieved_at_utc':retrieved,'raw_file':None,'sha256':None,'bytes':None,'status':'superseded_by_api','notes':'The catalogue XLSX route returned File not found. Official IIP General observations were subsequently retrieved from the public eSankhyiki API; see raw/mospi/iip/ and the separate base-year series manifest rows.','observation_count':None}
manifest.to_csv(manifest_path,index=False)

# Final compact report.
counts=allobs.groupby('series_id').size().to_dict() if not allobs.empty else {}
report={'retrieved_at_utc':retrieved,'manifest_rows':len(manifest),'successful_raw_files':int((manifest['status']=='downloaded').sum()),
        'canonical_observation_rows':int(len(allobs)),'unique_series':len(counts),'series_counts':counts,
        'coverage_gaps':['The extension step adds the official CPI back series, CFPI and IIP General API snapshots. CPI component back histories, IIP sectoral/use-based category panels and a parsed quarterly NAS series remain incomplete.',
        'RBI DBIE requested high-frequency tables were not downloadable in this pass because official file-host TLS connections closed; historical policy events are from Table 40, with a separate current-rate snapshot. Reattempt RBI DBIE UI/export for remaining series.',
        'IMD whole-India historical table supplies actual monthly rainfall (1901–2024), not monthly normal/departure; those are not imputed.',
        'No monthly interpolation/forward-fill of annual series; GDP/GVA context remains in source PDF only.',
        'FRED daily yields remain daily in canonical store; monthly means are separately named and explicitly aggregated.'],
        'validation':{'duplicate_keys_removed':True,'missing_values_kept_missing':True,'quarterly_or_annual_upsampled':False}}
(MAN/'data_quality_report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'observations':len(allobs),'series':len(counts),'manifest':len(manifest),'monthly_file':str(PROC/'macro_monthly_available.csv'),'rainfall_monthly_rows':sum(1 for x in obs if x['series_id']=='rainfall_actual'),'cpi_release_rows':sum(1 for x in obs if x['series_id'].startswith('cpi_'))},indent=2))
