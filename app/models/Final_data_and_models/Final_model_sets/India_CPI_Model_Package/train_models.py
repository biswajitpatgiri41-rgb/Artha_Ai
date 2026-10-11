#!/usr/bin/env python3
"""Leakage-aware India CPI forecast suite. Run: python train_models.py --data data --out artifacts"""
from __future__ import annotations
import argparse, json, warnings, hashlib, sys, platform, traceback
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import joblib
from scipy.optimize import minimize
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.api import VAR
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.tools import add_constant
from statsmodels.stats.diagnostic import acorr_ljungbox
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

MONTHS = {m: i for i, m in enumerate(['January','February','March','April','May','June','July','August','September','October','November','December'],1)}
HORIZONS = [1, 3, 6, 12]
BASE_MODELS = ['SeasonalNaive','ETS','ARIMA','SARIMA','SARIMAX','VAR','XGBoost']
SEED = 20261009
TEST_START = pd.Period('2024-01', freq='M')
MIN_TRAIN = 84
XCOLS = ['brent_yoy','inr_usd_yoy','us_cpi_yoy','fed_funds']


def dump_json(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, default=str, allow_nan=False), encoding='utf-8')


def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def load_official_cpi(raw: Path):
    back=pd.read_csv(raw/'mospi/cpi_2024_back_series.csv')
    current=pd.read_csv(raw/'mospi/cpi_2024_current_all_india_detailed.csv')
    def select(d):
        d=d[(d['state']=='All India')&(d['sector']=='Combined')&(d['division']=='CPI (General)')].copy()
        d['date']=pd.to_datetime(dict(year=d['year'],month=d['month'].map(MONTHS),day=1))
        return d
    b=select(back); c=select(current)
    rows=pd.concat([b,c],ignore_index=True).sort_values('date')
    if rows['date'].duplicated().any():
        raise ValueError('Duplicate headline observations in official 2024-base CPI files')
    rows=rows.set_index('date')
    rows.index=pd.PeriodIndex(rows.index, freq='M')
    rows['target_yoy']=pd.to_numeric(rows['inflation'],errors='coerce')
    rows['target_origin']='MoSPI published YoY'
    # The current-base extract has no published YoY values for 2025. Calculate only these
    # missing rates from the same-base official back/current index levels; mark them derived.
    derived=100*(pd.to_numeric(rows['index'],errors='coerce')/pd.to_numeric(rows['index'],errors='coerce').shift(12)-1)
    missing=rows['target_yoy'].isna() & derived.notna()
    rows.loc[missing,'target_yoy']=derived[missing]
    rows.loc[missing,'target_origin']='Derived from same-base index (2024-base index precision applies)'
    rows=rows.loc[rows.index>=pd.Period('2014-01','M')]
    rows=rows[['target_yoy','target_origin','index','series']].dropna(subset=['target_yoy'])
    expected=pd.period_range(rows.index.min(),rows.index.max(),freq='M')
    if not rows.index.equals(expected):
        raise ValueError('Official target has missing/duplicate months: '+str(expected.difference(rows.index).tolist()))
    if rows.index[-1] != pd.Period('2026-08','M'):
        print('WARNING: unexpected latest official CPI month:',rows.index[-1])
    return rows


def load_oecd(raw: Path):
    p=raw/'oecd/india_monthly_cpi_yoy.csv'
    d=pd.read_csv(p)
    d=d[(d['REF_AREA']=='IND')&(d['MEASURE']=='CPI')&(d['UNIT_MEASURE']=='PA')&(d['EXPENDITURE']=='_T')&(d['TRANSFORMATION']=='GY')].copy()
    d['month']=pd.PeriodIndex(d['TIME_PERIOD'],freq='M')
    y=pd.to_numeric(d['OBS_VALUE'],errors='coerce')
    s=pd.Series(y.to_numpy(),index=d['month'],name='inflation_yoy_pct').sort_index()
    s=s[~s.index.duplicated(keep='last')].dropna()
    return s


def load_series(path: Path, value_col: str):
    d=pd.read_csv(path)
    datecol=next(c for c in d.columns if 'date' in c.lower())
    d['date']=pd.to_datetime(d[datecol],errors='coerce')
    val=pd.to_numeric(d[value_col],errors='coerce')
    x=pd.DataFrame({'date':d['date'],'value':val}).dropna()
    x['month']=x['date'].dt.to_period('M')
    return x.groupby('month')['value'].mean().sort_index()


def make_macro(raw: Path, target_index):
    fred=raw/'fred'
    brent=load_series(fred/'DCOILBRENTEU.csv','DCOILBRENTEU')
    fx=load_series(fred/'DEXINUS.csv','DEXINUS')
    us_cpi=load_series(fred/'CPIAUCSL.csv','CPIAUCSL')
    fed=load_series(fred/'FEDFUNDS.csv','FEDFUNDS')
    idx=pd.period_range(min(target_index)-13, max(target_index), freq='M')
    brent=brent.reindex(idx); fx=fx.reindex(idx); us_cpi=us_cpi.reindex(idx); fed=fed.reindex(idx)
    # A one-month published CPI gap exists in the historical FRED file. Carry the last
    # observed index by one month only; the model feature remains explicitly lagged below.
    us_cpi_gap=us_cpi.isna()
    us_cpi=us_cpi.ffill(limit=1)
    us_cpi_imputed=us_cpi_gap & us_cpi.notna()
    rawm=pd.DataFrame(index=idx)
    rawm['brent_yoy']=100*(brent/brent.shift(12)-1)
    rawm['inr_usd_yoy']=100*(fx/fx.shift(12)-1)
    rawm['us_cpi_yoy']=100*(us_cpi/us_cpi.shift(12)-1)
    rawm['fed_funds']=fed
    rawm['us_cpi_index_forward_filled_one_month']=us_cpi_imputed.astype(int)
    # One-month lag is an explicit publication-lag safeguard for all external monthly features.
    x=rawm.shift(1).reindex(target_index)
    return x[XCOLS], rawm


def feature_row(y: pd.Series, macro: pd.DataFrame, i: int):
    vals=y.to_numpy(dtype=float)
    if i<24: return None
    row={}
    for lag in [0,1,2,3,6,12,18,24]: row[f'y_lag_{lag}']=float(vals[i-lag])
    for w in [3,6,12]:
        window=vals[i-w+1:i+1]
        row[f'y_mean_{w}']=float(np.mean(window))
    row['y_std_12']=float(np.std(vals[i-11:i+1],ddof=1))
    month=y.index[i].month
    row['month_sin']=float(np.sin(2*np.pi*month/12));row['month_cos']=float(np.cos(2*np.pi*month/12))
    if macro is not None:
        for col in macro.columns: row[col]=float(macro.iloc[i][col]) if pd.notna(macro.iloc[i][col]) else np.nan
    return row


def make_xgb(seed=SEED):
    return XGBRegressor(n_estimators=120,max_depth=2,learning_rate=0.025,min_child_weight=8,
        subsample=0.85,colsample_bytree=0.85,reg_lambda=8.0,reg_alpha=0.1,
        objective='reg:squarederror',n_jobs=1,random_state=seed,tree_method='hist',verbosity=0)


def _safe_forecast(origin, y, macro, max_h=12):
    """Fit all non-direct methods once at this origin. Failures are recorded as NaN."""
    out={}
    hist=y.iloc[:origin+1].astype(float)
    arr=hist.to_numpy()
    # Seasonal naive for a YoY target: reuse the value from the corresponding month a year ago.
    sn=[]
    for h in range(1,max_h+1):
        j=origin+h-12
        sn.append(float(arr[j]) if j>=0 else float(arr[-1]))
    out['SeasonalNaive']=np.asarray(sn)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        try:
            fit=ExponentialSmoothing(arr,trend='add',damped_trend=True,seasonal='add',seasonal_periods=12,
                                      initialization_method='estimated').fit(optimized=True,remove_bias=False)
            out['ETS']=np.asarray(fit.forecast(max_h),dtype=float)
        except Exception: out['ETS']=np.full(max_h,np.nan)
        try:
            fit=ARIMA(arr,order=(1,0,1),trend='c',enforce_stationarity=False,enforce_invertibility=False).fit()
            out['ARIMA']=np.asarray(fit.forecast(max_h),dtype=float)
        except Exception: out['ARIMA']=np.full(max_h,np.nan)
        try:
            fit=SARIMAX(arr,order=(1,0,0),seasonal_order=(1,0,0,12),trend='c',
                        enforce_stationarity=False,enforce_invertibility=False).fit(disp=False,maxiter=80)
            out['SARIMA']=np.asarray(fit.forecast(max_h),dtype=float)
        except Exception: out['SARIMA']=np.full(max_h,np.nan)
        try:
            ex=macro.iloc[:origin+1].astype(float)
            if ex.isna().any().any(): raise ValueError('missing exog values')
            fit=SARIMAX(arr,exog=ex.to_numpy(),order=(1,0,0),seasonal_order=(0,0,1,12),trend='c',
                        enforce_stationarity=False,enforce_invertibility=False).fit(disp=False,maxiter=80)
            # Conservative persistence path: hold the last known one-month-lagged macro vector fixed.
            xf=np.repeat(ex.iloc[-1:].to_numpy(),max_h,axis=0)
            out['SARIMAX']=np.asarray(fit.get_forecast(max_h,exog=xf).predicted_mean,dtype=float)
        except Exception: out['SARIMAX']=np.full(max_h,np.nan)
        v=pd.DataFrame()
        try:
            varcols=list(macro.columns)
            if len(varcols)>8:
                preferred=['brent_yoy','inr_usd_yoy','global_food_yoy','wpi_food_yoy','fed_funds']
                chosen=[c for c in preferred if c in varcols]
                if len(chosen)>=2: varcols=chosen
            v=pd.concat([hist.rename('india_cpi_yoy'),macro.iloc[:origin+1][varcols]],axis=1).dropna()
            if len(v)<40: raise ValueError('too few complete observations for VAR')
            model=VAR(v.astype(float))
            sel=model.select_order(maxlags=2).selected_orders.get('aic',1)
            lag=max(1,min(int(sel or 1),2))
            vf=model.fit(lag)
            out['VAR']=np.asarray(vf.forecast(v.to_numpy()[-lag:],steps=max_h)[:,0],dtype=float)
        except Exception:
            try:
                if len(v)<40: raise ValueError('too few complete observations for VAR fallback')
                vf=VAR(v.astype(float)).fit(1)
                out['VAR']=np.asarray(vf.forecast(v.to_numpy()[-1:],steps=max_h)[:,0],dtype=float)
            except Exception: out['VAR']=np.full(max_h,np.nan)
    return out


def _direct_xgb(y, macro, origin, h, seed=SEED):
    X=[];Y=[]
    for s in range(24,origin-h+1):
        r=feature_row(y,macro,s)
        if r is None or not np.isfinite(list(r.values())).all(): continue
        X.append(r);Y.append(float(y.iloc[s+h]))
    row=feature_row(y,macro,origin)
    if row is None or not np.isfinite(list(row.values())).all() or len(Y)<24:
        return np.nan,None
    names=list(row.keys());Xdf=pd.DataFrame(X,columns=names);xrow=pd.DataFrame([row],columns=names)
    model=make_xgb(seed);model.fit(Xdf,np.asarray(Y))
    pred=float(model.predict(xrow)[0])
    return pred,model


def simplex_weights(pred: pd.DataFrame, actual: pd.Series):
    good=[c for c in pred if pred[c].notna().mean()>=0.85]
    if not good: return {}
    p=pred[good].to_numpy(dtype=float); y=actual.to_numpy(dtype=float)
    ok=np.isfinite(p).all(axis=1)&np.isfinite(y);p=p[ok];y=y[ok]
    if len(y)<5: return {c:1/len(good) for c in good}
    n=p.shape[1];u=np.full(n,1/n)
    def objective(w): return np.mean((p@w-y)**2)+0.01*np.sum((w-u)**2)
    res=minimize(objective,u,method='SLSQP',bounds=[(0,1)]*n,
                 constraints=[{'type':'eq','fun':lambda w:np.sum(w)-1}],options={'maxiter':300,'ftol':1e-12})
    w=res.x if res.success else u
    return {c:float(v) for c,v in zip(good,w)}


def ensemble_predict(frame, weights):
    valid={k:v for k,v in weights.items() if k in frame and pd.notna(frame[k])}
    if not valid: return np.nan
    total=sum(valid.values())
    if total<=0:return np.nan
    return float(sum(frame[k]*v for k,v in valid.items())/total)


def conformal_q(absres, coverage):
    a=np.asarray(absres,dtype=float);a=a[np.isfinite(a)]
    if len(a)==0:return np.nan
    rank=min(len(a),int(np.ceil((len(a)+1)*coverage)))
    return float(np.sort(a)[rank-1])


def fit_oos(y, macro, series_name, outdir):
    records=[];failures=[]
    for i in range(MIN_TRAIN,len(y)):
        # Forecast-origin information ends at y[i]; target horizon values must be observed.
        try: direct_preds={h:{} for h in HORIZONS}
        except Exception: pass
        fitted=_safe_forecast(i,y,macro,12)
        for h in HORIZONS:
            j=i+h
            if j>=len(y):continue
            rec={'series':series_name,'origin_month':str(y.index[i]),'target_month':str(y.index[j]),
                 'horizon_months':h,'actual':float(y.iloc[j]),'forecast_origin_value':float(y.iloc[i]),
                 'split':'development' if y.index[j]<TEST_START else 'test'}
            for m in BASE_MODELS[:-1]:
                a=fitted.get(m,np.full(12,np.nan));v=float(a[h-1]) if len(a)>=h else np.nan
                rec[m]=v
            try:
                xp,_=_direct_xgb(y,macro,i,h,seed=SEED+h)
                rec['XGBoost']=xp
            except Exception as e:
                rec['XGBoost']=np.nan;failures.append({'origin':str(y.index[i]),'h':h,'err':repr(e)[:250]})
            records.append(rec)
        if (i-MIN_TRAIN+1)%12==0:
            print(f'[{series_name}] rolling origin {y.index[i]} / {y.index[-1]}',flush=True)
    df=pd.DataFrame(records)
    if df.empty: raise RuntimeError('No backtest rows generated')
    allweights={}; calib={}; calib_resids={}
    for h,g in df.groupby('horizon_months'):
        dev=g[g['target_month'].map(lambda x:pd.Period(x,'M')<TEST_START)].sort_values('target_month')
        pdev=dev[BASE_MODELS]
        w=simplex_weights(pdev,dev['actual']);allweights[int(h)]=w
        # Forward-chain development residuals for conformal calibration. For each development
        # target, fit weights only on strictly earlier development forecasts (minimum 8 rows).
        cr=[]
        vals=dev.reset_index(drop=True)
        for k in range(len(vals)):
            if k<8: continue
            prior=vals.iloc[:k]
            wk=simplex_weights(prior[BASE_MODELS],prior['actual'])
            pred=ensemble_predict(vals.iloc[k][BASE_MODELS],wk)
            if np.isfinite(pred): cr.append(float(vals.iloc[k]['actual']-pred))
        # Small-series fallback is explicitly marked; never claims guaranteed time-series coverage.
        if len(cr)<8:
            for _,r in dev.iterrows():
                pr=ensemble_predict(r[BASE_MODELS],w)
                if np.isfinite(pr):cr.append(float(r['actual']-pr))
        calib_resids[int(h)]=cr
        calib[int(h)]={'n_residuals':len(cr),'q80_abs':conformal_q(np.abs(cr),0.80),'q95_abs':conformal_q(np.abs(cr),0.95),
                       'method':'forward-chaining development ensemble residual absolute quantiles; empirical calibration only'}
    for h,w in allweights.items():
        ix=df.horizon_months==h
        df.loc[ix,'Ensemble']=[ensemble_predict(r[BASE_MODELS],w) for _,r in df.loc[ix].iterrows()]
    return df,allweights,calib,calib_resids,failures


def metrics_table(bt, weights, calib):
    rows=[]
    for h,g0 in bt.groupby('horizon_months'):
        g=g0[g0['split']=='test'].copy()
        dev=g0[g0['split']=='development'].copy()
        for m in BASE_MODELS+['Ensemble']:
            z=g.dropna(subset=[m])
            if z.empty:continue
            e=z[m]-z.actual
            if m=='Ensemble':
                c80=calib.get(int(h),{}).get('q80_abs',np.nan);c95=calib.get(int(h),{}).get('q95_abs',np.nan)
                caln=calib.get(int(h),{}).get('n_residuals',0)
                calmethod='forward-chaining development ensemble residuals'
            else:
                dz=dev.dropna(subset=[m]).copy()
                absdev=np.abs(dz[m].to_numpy(dtype=float)-dz.actual.to_numpy(dtype=float))
                c80=conformal_q(absdev,0.80);c95=conformal_q(absdev,0.95)
                caln=int(np.isfinite(absdev).sum())
                calmethod='development rolling-origin absolute errors for this model'
            rows.append({'horizon_months':int(h),'model':m,'n_test':len(z),'MAE_pp':float(np.mean(np.abs(e))),
                'RMSE_pp':float(np.sqrt(np.mean(e**2))),'bias_pp':float(np.mean(e)),
                'MASE_vs_seasonal_naive':float(np.mean(np.abs(e))/max(np.mean(np.abs(z['SeasonalNaive']-z.actual)),1e-12)),
                'test_coverage80_using_dev_calibration':float(np.mean(np.abs(e)<=c80)) if np.isfinite(c80) else np.nan,
                'test_coverage95_using_dev_calibration':float(np.mean(np.abs(e)<=c95)) if np.isfinite(c95) else np.nan,
                'interval80_width_pp':float(2*c80) if np.isfinite(c80) else np.nan,
                'interval95_width_pp':float(2*c95) if np.isfinite(c95) else np.nan,
                'calibration_n':caln,'calibration_method':calmethod})
    return pd.DataFrame(rows).sort_values(['horizon_months','MAE_pp'])


def fit_final_models(y, macro, weights, calib, outdir, series_name):
    outdir.mkdir(parents=True,exist_ok=True)
    comp={};meta={'series':series_name,'target_start':str(y.index[0]),'target_end':str(y.index[-1]),
        'n_months':len(y),'forecast_origin':str(y.index[-1]),'forecast_origin_note':'latest source CPI observation; final release vintages are not available',
        'horizons':HORIZONS,'exogenous_columns':list(macro.columns),'exogenous_availability':'All external regressors are shifted one month. SARIMAX assumes the last known lagged external vector persists forward; VAR forecasts the macro panel jointly.',
        'seed':SEED}
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        arr=y.to_numpy(dtype=float)
        try:comp['ETS']=ExponentialSmoothing(arr,trend='add',damped_trend=True,seasonal='add',seasonal_periods=12,initialization_method='estimated').fit(optimized=True,remove_bias=False)
        except Exception as e: meta.setdefault('fit_errors',{})['ETS']=repr(e)
        try:comp['ARIMA']=ARIMA(arr,order=(1,0,1),trend='c',enforce_stationarity=False,enforce_invertibility=False).fit()
        except Exception as e: meta.setdefault('fit_errors',{})['ARIMA']=repr(e)
        try:comp['SARIMA']=SARIMAX(arr,order=(1,0,0),seasonal_order=(1,0,0,12),trend='c',enforce_stationarity=False,enforce_invertibility=False).fit(disp=False,maxiter=150)
        except Exception as e: meta.setdefault('fit_errors',{})['SARIMA']=repr(e)
        try:
            ex=macro.astype(float)
            if ex.isna().any().any(): raise ValueError('macro panel incomplete')
            comp['SARIMAX']=SARIMAX(arr,exog=ex.to_numpy(),order=(1,0,0),seasonal_order=(0,0,1,12),trend='c',enforce_stationarity=False,enforce_invertibility=False).fit(disp=False,maxiter=150)
            comp['SARIMAX_last_exog']=ex.iloc[-1].to_numpy()
        except Exception as e: meta.setdefault('fit_errors',{})['SARIMAX']=repr(e)
        try:
            varcols=list(macro.columns)
            if len(varcols)>8:
                preferred=['brent_yoy','inr_usd_yoy','global_food_yoy','wpi_food_yoy','fed_funds']
                chosen=[c for c in preferred if c in varcols]
                if len(chosen)>=2: varcols=chosen
            vp=pd.concat([y.rename('india_cpi_yoy'),macro[varcols]],axis=1).astype(float).dropna()
            vm=VAR(vp); lag=vm.select_order(maxlags=2).selected_orders.get('aic',1);lag=max(1,min(int(lag or 1),2))
            comp['VAR']=vm.fit(lag);comp['VAR_panel']=vp.to_numpy();comp['VAR_lag']=lag;comp['VAR_columns']=list(vp.columns)
        except Exception as e: meta.setdefault('fit_errors',{})['VAR']=repr(e)
    comp['last_target_history']=arr
    comp['SeasonalNaive']={'method':'same-month-last-year on YoY target','target_history':arr.copy(),'origin_month':str(y.index[-1])}
    comp['weights']={str(k):v for k,v in weights.items()}
    comp['calibration']={str(k):v for k,v in calib.items()}
    # Direct XGBoost models for each requested horizon; samples use only origin-time lags.
    xmods={}; xnames={}
    for h in HORIZONS:
        xx=[]; yy=[]
        for s in range(24,len(y)-h):
            r=feature_row(y,macro,s)
            if r is not None and np.isfinite(list(r.values())).all():xx.append(r);yy.append(float(y.iloc[s+h]))
        if len(yy)>=24:
            md=make_xgb(SEED+h);xfd=pd.DataFrame(xx);md.fit(xfd,np.array(yy));xmods[h]=md;xnames[h]=list(xfd.columns)
    comp['XGBoost']=xmods;comp['XGBoost_feature_names']=xnames
    meta['component_fit']=sorted(k for k in comp if k in BASE_MODELS)
    meta['future_points']=[]
    origin_i=len(y)-1; origin=y.index[-1]
    fdict={}
    sn=[]
    for h in range(1,13):
        pos=origin_i+h-12;sn.append(float(arr[pos]) if pos>=0 else float(arr[-1]))
    fdict['SeasonalNaive']=np.array(sn)
    for model in ['ETS','ARIMA','SARIMA']:
        if model in comp:
            try: fdict[model]=np.asarray(comp[model].forecast(12),dtype=float)
            except Exception: pass
    if 'SARIMAX' in comp:
        try:
            xf=np.repeat(np.asarray(comp['SARIMAX_last_exog']).reshape(1,-1),12,axis=0)
            fdict['SARIMAX']=np.asarray(comp['SARIMAX'].get_forecast(12,exog=xf).predicted_mean,dtype=float)
        except Exception as e:meta.setdefault('forecast_errors',{})['SARIMAX']=repr(e)
    if 'VAR' in comp:
        try:
            vf=comp['VAR'];lag=comp['VAR_lag'];panel=comp['VAR_panel'];fdict['VAR']=np.asarray(vf.forecast(panel[-lag:],steps=12)[:,0],dtype=float)
        except Exception as e:meta.setdefault('forecast_errors',{})['VAR']=repr(e)
    r=feature_row(y,macro,origin_i)
    for h,md in xmods.items():
        try:fdict.setdefault('XGBoost',np.full(12,np.nan));fdict['XGBoost'][h-1]=float(md.predict(pd.DataFrame([r],columns=xnames[h]))[0])
        except Exception:pass
    point_rows=[]; allnames=BASE_MODELS
    for h in HORIZONS:
        components={m:float(fdict[m][h-1]) for m in allnames if m in fdict and len(fdict[m])>=h and np.isfinite(fdict[m][h-1])}
        w=weights.get(h,{})
        use={k:v for k,v in w.items() if k in components};den=sum(use.values())
        pred=sum(components[k]*v for k,v in use.items())/den if den>0 else components.get('SeasonalNaive',np.nan)
        c=calib.get(h,{})
        point_rows.append({'series':series_name,'forecast_origin':str(origin),'target_month':str(origin+h),
            'horizon_months':h,'ensemble_forecast_yoy_pct':float(pred),
            'interval80_low':float(pred-c['q80_abs']) if np.isfinite(c.get('q80_abs',np.nan)) else np.nan,
            'interval80_high':float(pred+c['q80_abs']) if np.isfinite(c.get('q80_abs',np.nan)) else np.nan,
            'interval95_low':float(pred-c['q95_abs']) if np.isfinite(c.get('q95_abs',np.nan)) else np.nan,
            'interval95_high':float(pred+c['q95_abs']) if np.isfinite(c.get('q95_abs',np.nan)) else np.nan,
            'components_json':json.dumps(components),'weights_json':json.dumps(use),
            'interval_note':'development out-of-fold residual calibration; empirical, not a guarantee under drift'})
    fc=pd.DataFrame(point_rows)
    comp['final_forecasts']=fdict
    comp['metadata']=meta
    # Persist one file per model plus complete registry for convenient loading.
    for m in BASE_MODELS:
        if m=='XGBoost':
            for h,md in xmods.items():joblib.dump(md,outdir/f'XGBoost_direct_h{h}.joblib',compress=3)
        elif m=='SARIMAX' and m in comp:
            joblib.dump({'results':comp['SARIMAX'],'last_known_lagged_exog':comp.get('SARIMAX_last_exog'),
                         'columns':list(macro.columns),'future_path_assumption':'hold last known lagged exogenous vector fixed'},outdir/'SARIMAX.joblib',compress=3)
        elif m=='VAR' and m in comp:
            joblib.dump({'results':comp['VAR'],'last_panel':comp.get('VAR_panel'),'lag':comp.get('VAR_lag'),
                         'columns':comp.get('VAR_columns')},outdir/'VAR.joblib',compress=3)
        elif m in comp:
            joblib.dump(comp[m],outdir/f'{m}.joblib',compress=3)
    joblib.dump(comp,outdir/'model_registry.joblib',compress=3)
    dump_json(outdir/'model_metadata.json',meta)
    return comp,fc


def diagnostics(y, macro, backtest, forecasts, weights, calib, comp, outdir, series_name, raw):
    diag=outdir/'diagnostics';diag.mkdir(parents=True,exist_ok=True)
    # Input quality checks.
    idx=pd.period_range(y.index.min(),y.index.max(),freq='M')
    qa={'series':series_name,'n_observations':len(y),'first_month':str(y.index.min()),'last_month':str(y.index.max()),
        'duplicate_months':int(y.index.duplicated().sum()),'missing_months':int(len(idx.difference(y.index))),
        'missing_y':int(y.isna().sum()),'nonfinite_y':int((~np.isfinite(y.to_numpy())).sum()),
        'macro_missing_by_column':macro.isna().sum().to_dict(),'out_of_range_y_months':int(((y< -10)|(y>50)).sum()),
        'target_is_official_mospi_2024_base_yoy_except_2025_index_derived':series_name.startswith('mospi_2024_base'),
        'data_vintage_warning':'No historical release-vintage snapshots; training uses retrieved/revised observations.'}
    dump_json(diag/'data_quality.json',qa)
    # XGBoost importance and optional local SHAP explanation for each horizon.
    imp=[];shaprows=[]
    try:
        import shap
        for h,md in comp.get('XGBoost',{}).items():
            names=comp['XGBoost_feature_names'][h]
            gain=md.get_booster().get_score(importance_type='gain')
            for k,nm in enumerate(names):imp.append({'horizon_months':h,'feature':nm,'gain_importance':float(gain.get(nm,gain.get(f'f{k}',0.0)))})
            try:
                r=feature_row(y,macro,len(y)-1);xx=pd.DataFrame([r],columns=names)
                vals=shap.TreeExplainer(md)(xx).values.reshape(-1)
                for nm,v in zip(names,vals):shaprows.append({'horizon_months':h,'feature':nm,'shap_value_at_latest_origin':float(v)})
            except Exception as e: shaprows.append({'horizon_months':h,'feature':'SHAP_ERROR','shap_value_at_latest_origin':str(e)[:200]})
    except Exception as e: dump_json(diag/'shap_status.json',{'status':'unavailable','reason':repr(e)})
    if imp:pd.DataFrame(imp).to_csv(diag/'xgboost_gain_importance.csv',index=False)
    if shaprows:pd.DataFrame(shaprows).to_csv(diag/'shap_latest_origin.csv',index=False)
    # Exploratory two-state HMM on inflation level and trailing volatility; retrospective only.
    try:
        from hmmlearn.hmm import GaussianHMM
        from sklearn.preprocessing import StandardScaler
        hdata=pd.DataFrame({'inflation':y,'volatility':y.rolling(12,min_periods=6).std()}).dropna()
        scaler=StandardScaler();z=scaler.fit_transform(hdata)
        hmm=GaussianHMM(n_components=2,covariance_type='diag',n_iter=500,random_state=SEED,tol=1e-4)
        hmm.fit(z);prob=hmm.predict_proba(z);means={}
        rawmeans=scaler.inverse_transform(hmm.means_)
        hi=int(np.argmax(rawmeans[:,0]));lo=1-hi
        states=pd.DataFrame({'month':hdata.index.astype(str),'inflation_yoy_pct':hdata.inflation.to_numpy(),
             'p_high_inflation_state':prob[:,hi],'p_low_inflation_state':prob[:,lo],
             'most_likely_state':np.where(prob[:,hi]>=prob[:,lo],'higher-inflation pattern','lower-inflation pattern')})
        states.to_csv(diag/'regime_probabilities.csv',index=False)
        dump_json(diag/'regime_model_metadata.json',{'method':'two-state Gaussian HMM','states_labelled_by_fitted_mean_inflation':'exploratory descriptive patterns, not causal','probability_type':'full-sample smoothed posteriors using the entire observed history','real_time_use':'not valid as a real-time regime probability; fit/filter with only information available at each date and validate out-of-sample first','state_means_original_units':rawmeans.tolist(),'converged':bool(hmm.monitor_.converged),'n_months':len(hdata)})
        joblib.dump({'scaler':scaler,'hmm':hmm},diag/'regime_hmm.joblib',compress=3)
    except Exception as e:dump_json(diag/'regime_status.json',{'status':'failed','reason':repr(e)})
    # Historical out-of-sample residual simulation per horizon (empirical bootstrap, not a probability model).
    mc=[]
    for row in forecasts.to_dict('records'):
        h=int(row['horizon_months']);errs=np.asarray(comp['calibration'][str(h)]['_residuals'] if '_residuals' in comp['calibration'][str(h)] else [],dtype=float)
        if not len(errs): errs=np.array([0.0])
        rng=np.random.default_rng(SEED+h);draw=float(row['ensemble_forecast_yoy_pct'])+rng.choice(errs,size=10000,replace=True)
        mc.append({'horizon_months':h,'target_month':row['target_month'],'draws':10000,'p05':float(np.quantile(draw,.05)),'p50':float(np.quantile(draw,.5)),'p95':float(np.quantile(draw,.95)),
                   'method':'bootstrap development rolling-origin ensemble errors; empirical uncertainty, not causal scenario probability'})
    pd.DataFrame(mc).to_csv(diag/'monte_carlo_uncertainty.csv',index=False)
    # Deterministic Taylor-rule reference; output gap and neutral real rate are explicit assumptions.
    taylor=[]
    params={'neutral_real_rate_pct':1.5,'inflation_target_pct':4.0,'phi_inflation':0.5,'phi_output_gap':0.5,'output_gap_assumption_pct':0.0,
            'formula':'i = r* + pi + phi_pi*(pi-pi*) + phi_y*output_gap','warning':'Illustrative rule benchmark only, not an RBI recommendation or identified policy response.'}
    for row in forecasts.to_dict('records'):
        pi=float(row['ensemble_forecast_yoy_pct']);rate=params['neutral_real_rate_pct']+pi+params['phi_inflation']*(pi-params['inflation_target_pct'])+params['phi_output_gap']*params['output_gap_assumption_pct']
        taylor.append({'target_month':row['target_month'],'forecast_inflation_yoy_pct':pi,'illustrative_taylor_rate_pct':rate})
    pd.DataFrame(taylor).to_csv(diag/'taylor_rule_reference.csv',index=False);dump_json(diag/'taylor_rule_assumptions.json',params)
    # Local projections: HAC regression estimates are descriptive associations, not causal impulse responses.
    try:
        oil=load_series(raw/'fred'/'DCOILBRENTEU.csv','DCOILBRENTEU').reindex(y.index)
        fx=load_series(raw/'fred'/'DEXINUS.csv','DEXINUS').reindex(y.index)
        oilshock=100*np.log(oil/oil.shift(1));fxchg=100*np.log(fx/fx.shift(1))
        lp=[]
        for h in HORIZONS:
            d=pd.DataFrame({'response':y.shift(-h)-y,'oil_monthly_log_change_pct':oilshock,'fx_monthly_log_change_pct':fxchg,
                            'inflation_lag1':y.shift(1),'us_cpi_yoy':macro['us_cpi_yoy'],'fed_funds':macro['fed_funds']}).dropna()
            X=add_constant(d[['oil_monthly_log_change_pct','fx_monthly_log_change_pct','inflation_lag1','us_cpi_yoy','fed_funds']])
            fit=OLS(d.response,X).fit(cov_type='HAC',cov_kwds={'maxlags':max(1,h)})
            lp.append({'horizon_months':h,'response_definition':'future CPI YoY minus current CPI YoY (percentage points)',
                'oil_shock_coefficient_pp_per_1pct_oil_change':float(fit.params['oil_monthly_log_change_pct']),
                'oil_hac_se':float(fit.bse['oil_monthly_log_change_pct']),'oil_p_value':float(fit.pvalues['oil_monthly_log_change_pct']),
                'fx_coefficient_pp_per_1pct_fx_change':float(fit.params['fx_monthly_log_change_pct']),'fx_hac_se':float(fit.bse['fx_monthly_log_change_pct']),
                'n':len(d),'r_squared':float(fit.rsquared),'interpretation':'descriptive conditional association only; not causal identification'})
        pd.DataFrame(lp).to_csv(diag/'local_projection_associations.csv',index=False)
    except Exception as e:dump_json(diag/'local_projection_status.json',{'status':'failed','reason':repr(e)})
    # Drift watch using chosen development-best (not test-picked) model and latest 12 test outcomes.
    try:
        best={}
        for h,g in backtest[backtest['split']=='development'].groupby('horizon_months'):
            mae={m:float(np.mean(np.abs(g[m]-g.actual))) for m in BASE_MODELS+['Ensemble'] if m in g and g[m].notna().all()}
            best[int(h)]=min(mae,key=mae.get) if mae else 'SeasonalNaive'
        drift=[]
        for h,g in backtest[backtest['split']=='test'].groupby('horizon_months'):
            model=best[int(h)];z=g.dropna(subset=[model]).sort_values('target_month').tail(12)
            dev=backtest[(backtest.split=='development')&(backtest.horizon_months==h)].dropna(subset=[model]).copy()
            if len(z)>=6:
                roll=float(np.mean(np.abs(z[model]-z.actual)))
                devroll=[float(np.mean(np.abs(dev[model].to_numpy()[k-11:k+1]-dev.actual.to_numpy()[k-11:k+1]))) for k in range(11,len(dev))]
                threshold=float(np.quantile(devroll,.95)) if devroll else np.nan
                drift.append({'horizon_months':int(h),'development_selected_model':model,'recent_test_window_n':len(z),'recent_mae_pp':roll,'development_rolling12_mae_p95':threshold,'status':'WATCH' if np.isfinite(threshold) and roll>threshold else 'no current trigger','note':'low-power monitoring rule; review source vintages and input drift before action'})
        pd.DataFrame(drift).to_csv(diag/'drift_watch.csv',index=False)
    except Exception as e:dump_json(diag/'drift_status.json',{'status':'failed','reason':repr(e)})
    roadmap={'implemented_or_artifact':'forecast models, rolling-origin backtest, development-weighted ensemble, empirical interval calibration, XGBoost gain/SHAP when available, descriptive two-state regime detection, empirical residual bootstrap uncertainty, Taylor reference, exploratory HAC local projections, data-quality checks, drift watch.',
       'not_claimed_as_trained':'No separate live nowcast is fitted: the stored forecast starts at the latest bundled CPI month (2026-08), and no point-in-time high-frequency release panel is available. Historical counterfactuals and policy optimization: not fit because no causal identification, validated welfare/loss function, or operational constraints were supplied. Policy agents/LLM agents are orchestration and not numerical forecast models.',
       'causal_warning':'Local-projection coefficients, HMM states, Taylor-rule rates, and bootstrap intervals are diagnostics/scenario tools; none establishes causality or an optimal RBI policy.'}
    dump_json(diag/'roadmap_status.json',roadmap)
    return qa


def run_one(raw: Path, out: Path, series_name: str, y: pd.Series, macro: pd.DataFrame):
    print(f'\n=== {series_name}: {len(y)} monthly observations {y.index.min()} to {y.index.max()} ===',flush=True)
    out.mkdir(parents=True,exist_ok=True)
    if len(y)<MIN_TRAIN+24: raise ValueError(f'{series_name}: too few observations')
    bt,weights,calib,calib_resids,failures=fit_oos(y,macro,series_name,out)
    # Save residual draws to registry calibration metadata for deterministic simulation.
    for h,r in calib.items(): r['_residuals']=[float(v) for v in calib_resids[h]]
    # Save external performance and weights. Test targets are strictly >= 2024-01.
    m=metrics_table(bt,weights,calib)
    bt.to_csv(out/'backtest_predictions.csv',index=False)
    m.to_csv(out/'test_metrics.csv',index=False)
    weight_rows=[]
    for h,w in weights.items():
        for name,val in w.items():weight_rows.append({'horizon_months':h,'model':name,'weight':val})
    pd.DataFrame(weight_rows).to_csv(out/'ensemble_weights.csv',index=False)
    dump_json(out/'interval_calibration.json',{str(h):v for h,v in calib.items()})
    if failures:pd.DataFrame(failures).to_csv(out/'fit_failures.csv',index=False)
    # remove simulation residuals from calibration section for user-facing compact JSON,
    # but keep them in the binary registry.
    comp,fc=fit_final_models(y,macro,weights,calib,out/'models',series_name)
    comp['calibration']={str(h):v for h,v in calib.items()}
    joblib.dump(comp,out/'models'/'model_registry.joblib',compress=3)
    fc.to_csv(out/'forecasts.csv',index=False)
    quality=diagnostics(y,macro,bt,fc,weights,calib,comp,out,series_name,raw)
    target_definition=('India CPI Combined General Group inflation, year-over-year percent; official MoSPI 2024-base back/current files; missing 2025 YoY derived from same-base index levels.'
                      if series_name.startswith('mospi_2024_base') else
                      'OECD monthly India CPI inflation YoY series used as a separate sensitivity target; not blended with the MoSPI 2024-base series.')
    dump_json(out/'metadata.json',{'created_utc':datetime.now(timezone.utc).isoformat(),'series':series_name,
        'target_definition':target_definition,
        'test_period_definition':'Rolling-origin comparison period, forecast targets >= 2024-01; baseline and expanded feature specifications were compared on this same period, so it is not an untouched final production holdout.',
        'development_period_definition':'Forecast target months < 2024-01; used for ensemble weights and empirical interval calibration.',
        'horizons_months':HORIZONS,'min_train_months':MIN_TRAIN,'data_quality':quality,
        'python':sys.version,'platform':platform.platform(),'versions':versions(),'weights':weights,
        'known_limitations':['Only 152 monthly official 2024-base YoY targets; 2025 YoY is derived from same-base rounded index values.','No historical real-time release vintages; backtests use revised observed values and may overstate what was known at each origin.','The >=2024 comparison period was inspected to compare feature specifications and is not an independent final blind test.','Forecast origins overlap and are correlated; test sample is modest, especially by regime.','Forecast intervals are empirical calibration, not guaranteed coverage.','No claim of production readiness without external prospective monitoring, point-in-time data, and retraining governance.']})
    return m,fc


def versions():
    import sklearn,statsmodels,xgboost,scipy
    return {'numpy':np.__version__,'pandas':pd.__version__,'scikit_learn':sklearn.__version__,'statsmodels':statsmodels.__version__,'xgboost':xgboost.__version__,'scipy':scipy.__version__,'joblib':joblib.__version__}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--data',default='data',help='folder containing raw/ subfolder')
    ap.add_argument('--out',default='artifacts',help='output folder')
    args=ap.parse_args();root=Path(args.data);raw=root/'raw' if (root/'raw').exists() else root;out=Path(args.out)
    yframe=load_official_cpi(raw)
    y=yframe['target_yoy'].astype(float); y.name='india_cpi_yoy'
    macro,rawmacro=make_macro(raw,y.index)
    out.mkdir(parents=True,exist_ok=True)
    yframe.to_csv(out/'mospi_2024_base_target.csv')
    macro.to_csv(out/'macro_predictors_one_month_lag.csv')
    rawmacro.to_csv(out/'external_macro_monthly_source_panel.csv')
    m,fc=run_one(raw,out/'mospi_2024_base', 'mospi_2024_base',y,macro)
    # Longer-history OECD CPI is retained and trained separately as a sensitivity suite.
    # It is not spliced into the official India target or averaged into production forecasts.
    oecd=load_oecd(raw);oy=oecd.astype(float);oy.name='oecd_india_cpi_yoy'
    om,oraw=make_macro(raw,oy.index)
    # Reuse same training pipeline with longer warm-up and target-source-specific run settings.
    global MIN_TRAIN
    old=MIN_TRAIN; MIN_TRAIN=120
    try:
        # To control runtime, evaluate all models on the long-history series, with official source
        # held separate. Its target is OECD CPI and its test period is still the final 2024+ window.
        ometrics,ofc=run_one(raw,out/'oecd_long_history_sensitivity','oecd_long_history_sensitivity',oy,om)
    finally: MIN_TRAIN=old
    # Combined top-level report tables and data provenance.
    m.assign(series='mospi_2024_base').to_csv(out/'ALL_MOSPI_TEST_METRICS.csv',index=False)
    ometrics.assign(series='oecd_long_history_sensitivity').to_csv(out/'ALL_OECD_TEST_METRICS.csv',index=False)
    source_files=[]
    used=['mospi/cpi_2024_back_series.csv','mospi/cpi_2024_current_all_india_detailed.csv','oecd/india_monthly_cpi_yoy.csv',
          'fred/DCOILBRENTEU.csv','fred/DEXINUS.csv','fred/CPIAUCSL.csv','fred/FEDFUNDS.csv']
    for rel in used:
        p=raw/rel
        source_files.append({'path':rel,'sha256':sha256(p),'bytes':p.stat().st_size})
    dump_json(out/'source_data_checksums.json',{'source_files':source_files,'retrieved_dataset_package':'India_CPI_Forecasting_Dataset_Package','source_note':'The source ZIP is linked by the user conversation; only the files listed above are required for this training code.'})
    print('\nMOSPI TEST METRICS\n',m.to_string(index=False))
    print('\nMOSPI FORECASTS\n',fc[['target_month','horizon_months','ensemble_forecast_yoy_pct','interval80_low','interval80_high']].to_string(index=False))
    print('\nOECD sensitivity output saved. All artifacts at',out.resolve())

if __name__=='__main__': main()
