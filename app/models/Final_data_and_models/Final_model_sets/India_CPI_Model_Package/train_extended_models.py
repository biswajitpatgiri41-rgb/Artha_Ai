#!/usr/bin/env python3
"""Train an alternative enriched-feature MoSPI suite using verified monthly sources.
Run from package root: python train_extended_models.py --data data --out artifacts/mospi_2024_base_extended
"""
import argparse, json, re, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
import train_models as core


def pink_index(path: Path, col: int) -> pd.Series:
    raw=pd.read_excel(path,sheet_name='Monthly Indices',header=None)
    dates=[];values=[]
    for _,row in raw.iterrows():
        cell=str(row.iloc[0]).strip()
        m=re.fullmatch(r'(\d{4})M(\d{2})',cell)
        if m:
            dates.append(pd.Period(f'{m.group(1)}-{m.group(2)}',freq='M'))
            values.append(pd.to_numeric(row.iloc[col],errors='coerce'))
    s=pd.Series(values,index=pd.PeriodIndex(dates,freq='M')).sort_index()
    s=s[~s.index.duplicated(keep='last')]
    return s


def wpi_series(path: Path, match: str) -> pd.Series:
    raw=pd.read_excel(path,sheet_name='MONTHLY_INDEX')
    cols=[c for c in raw.columns if re.fullmatch(r'INDX\d{6}',str(c))]
    periods=pd.PeriodIndex([f'{int(str(c)[-4:])}-{int(str(c)[4:6]):02d}' for c in cols],freq='M')
    row=raw[raw['COMM_NAME'].astype(str).str.strip().str.casefold()==match.casefold()]
    if len(row)!=1: raise ValueError(f'WPI source row not unique for {match!r}: {len(row)}')
    vals=pd.to_numeric(row.iloc[0][cols],errors='coerce').to_numpy(dtype=float)
    return pd.Series(vals,index=periods).sort_index()


def make_extended_macro(raw: Path, target_index):
    idx=pd.period_range(min(target_index)-18,max(target_index),freq='M')
    def obs(file,col):return core.load_series(raw/'fred'/file,col).reindex(idx)
    brent=obs('DCOILBRENTEU.csv','DCOILBRENTEU')
    wti=obs('DCOILWTICO.csv','DCOILWTICO')
    fx=obs('DEXINUS.csv','DEXINUS')
    usheadline=obs('CPIAUCSL.csv','CPIAUCSL')
    uscore=obs('CPILFESL.csv','CPILFESL')
    fed=obs('FEDFUNDS.csv','FEDFUNDS')
    dxy=obs('DTWEXBGS.csv','DTWEXBGS')
    treasury=obs('DGS10.csv','DGS10')
    headline_gap=usheadline.isna()
    core_gap=uscore.isna()
    usheadline=usheadline.ffill(limit=1);uscore=uscore.ffill(limit=1)
    wb=raw/'world_bank'/'pink_sheet_monthly_commodity_prices.xlsx'
    food=pink_index(wb,6).reindex(idx)
    energy=pink_index(wb,2).reindex(idx)
    fertilizer=pink_index(wb,13).reindex(idx)
    wpi_path=raw/'wpi'/'wpi_2011_12_monthly_from_2012.xls'
    wpi_all=wpi_series(wpi_path,'All commodities').reindex(idx)
    wpi_food=wpi_series(wpi_path,'IV FOOD INDEX').reindex(idx)
    rawm=pd.DataFrame(index=idx)
    rawm['brent_yoy']=100*(brent/brent.shift(12)-1)
    rawm['inr_usd_yoy']=100*(fx/fx.shift(12)-1)
    rawm['us_cpi_yoy']=100*(usheadline/usheadline.shift(12)-1)
    rawm['fed_funds']=fed
    rawm['wti_yoy']=100*(wti/wti.shift(12)-1)
    rawm['us_core_cpi_yoy']=100*(uscore/uscore.shift(12)-1)
    rawm['broad_usd_yoy']=100*(dxy/dxy.shift(12)-1)
    rawm['us_10y_treasury_monthly_average_pct']=treasury
    rawm['global_food_yoy']=100*(food/food.shift(12)-1)
    rawm['global_energy_yoy']=100*(energy/energy.shift(12)-1)
    rawm['global_fertilizer_yoy']=100*(fertilizer/fertilizer.shift(12)-1)
    # Latest WPI workbook month is April 2026. Four-month lag provides a conservative
    # release-delay safeguard and aligns its last available value to the 2026-08 CPI origin.
    rawm['wpi_all_yoy']=100*(wpi_all/wpi_all.shift(12)-1).shift(3)
    rawm['wpi_food_yoy']=100*(wpi_food/wpi_food.shift(12)-1).shift(3)
    rawm['us_cpi_one_month_fill_flag']=(headline_gap & usheadline.notna()).astype(int)
    rawm['us_core_cpi_one_month_fill_flag']=(core_gap & uscore.notna()).astype(int)
    x=rawm.shift(1).reindex(target_index)
    predictors=[c for c in rawm.columns if not c.endswith('_flag')]
    x=x[predictors]
    return x,rawm


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',default='data');ap.add_argument('--out',default='artifacts/mospi_2024_base_extended');a=ap.parse_args()
    root=Path(a.data);raw=root/'raw' if (root/'raw').exists() else root;out=Path(a.out)
    yframe=core.load_official_cpi(raw);y=yframe.target_yoy.astype(float);y.name='india_cpi_yoy'
    macro,rawm=make_extended_macro(raw,y.index)
    if macro.isna().any().any(): raise ValueError('Extended feature panel has missing values: '+str(macro.isna().sum().to_dict()))
    out.mkdir(parents=True,exist_ok=True);yframe.to_csv(out/'mospi_2024_base_target.csv');rawm.to_csv(out/'external_macro_monthly_source_panel.csv');macro.to_csv(out/'macro_predictors_one_month_lag.csv')
    m,fc=core.run_one(raw,out,'mospi_2024_base_extended',y,macro)
    # Replace the core collector's seven-file source list with every input used by this extension.
    used=['mospi/cpi_2024_back_series.csv','mospi/cpi_2024_current_all_india_detailed.csv',
          'fred/DCOILBRENTEU.csv','fred/DEXINUS.csv','fred/CPIAUCSL.csv','fred/FEDFUNDS.csv',
          'fred/DCOILWTICO.csv','fred/CPILFESL.csv','fred/DTWEXBGS.csv','fred/DGS10.csv',
          'world_bank/pink_sheet_monthly_commodity_prices.xlsx','wpi/wpi_2011_12_monthly_from_2012.xls']
    files=[]
    for rel in used:
        p=raw/rel;h=hashlib.sha256(p.read_bytes()).hexdigest()
        files.append({'path':rel,'sha256':h,'bytes':p.stat().st_size})
    core.dump_json(out/'source_data_checksums.json',{'source_files':files,'notes':[
       'Pink Sheet Food/Energy/Fertilizers monthly indexes are lagged one month and used as global benchmark-price proxies, not Indian retail food prices.',
       'Official 2011-12-base WPI All commodities and IV FOOD INDEX YoY predictors are lagged four months; its source workbook ends April 2026.',
       'No 2012-base CPI-food series is spliced into the official 2024-base target. Food-category CPI remains a candidate for a separate, vintage-aware component model.']})
    print('EXTENDED TEST METRICS\n',m.to_string(index=False));print('\nEXTENDED FORECASTS\n',fc[['target_month','horizon_months','ensemble_forecast_yoy_pct','interval80_low','interval80_high']].to_string(index=False));print('output',out.resolve())

if __name__=='__main__':main()
