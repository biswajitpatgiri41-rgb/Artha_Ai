#!/usr/bin/env python3
"""Retrain India CPI forecast prototypes with official WPI and RBI credit data.

Only observed source data are used. Synthetic scenarios, unreleased future labels,
and unverified source routes are excluded. This is an experimental retraining
and feature-ablation script, not a production model-selection claim.
"""
from __future__ import annotations
import hashlib
import json
import pickle
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels
import xgboost as xgb
from statsmodels.tsa.arima.model import ARIMA

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/source/macro_monthly_available.csv'
RAW = ROOT / 'data/raw'
OUT = ROOT
HORIZONS = [1, 3, 6]
HOLDOUT_MONTHS = 24
RIDGE_ALPHA = 10.0
XGB_PARAMS = {
    'objective': 'reg:squarederror', 'eval_metric': 'rmse', 'tree_method': 'hist',
    'max_depth': 2, 'eta': 0.04, 'min_child_weight': 5,
    'subsample': 0.8, 'colsample_bytree': 0.8,
    'lambda': 10.0, 'alpha': 1.0, 'seed': 20261005, 'nthread': 2
}
XGB_ROUNDS = 50
BASE_FEATURES = [
    'cpi_yoy_lag_1', 'cpi_yoy_lag_2', 'cpi_yoy_lag_3',
    'cpi_yoy_lag_6', 'cpi_yoy_lag_12', 'cfpi_yoy_lag_1',
    'brent_yoy_lag_1', 'repo_change_3m_lag_1',
    'usd_inr_yoy_lag_1', 'iip_growth_2022_23_lag_1'
]
EXTRA_FEATURES = {
    'wpi_old': ['wpi_all_commodities_yoy_2011_12_lag_1'],
    'wpi_current': ['wpi_all_commodities_yoy_2022_23_lag_1'],
    'credit': ['rbi_nonfood_credit_yoy_lag_2']
}
VARIANTS = {
    'base': [],
    'wpi_old': EXTRA_FEATURES['wpi_old'],
    'wpi_current': EXTRA_FEATURES['wpi_current'],
    'credit': EXTRA_FEATURES['credit'],
    'wpi_old_credit': EXTRA_FEATURES['wpi_old'] + EXTRA_FEATURES['credit'],
    'wpi_current_credit': EXTRA_FEATURES['wpi_current'] + EXTRA_FEATURES['credit'],
    'all': EXTRA_FEATURES['wpi_old'] + EXTRA_FEATURES['wpi_current'] + EXTRA_FEATURES['credit'],
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def parse_indian_number(value):
    if value is None or pd.isna(value):
        return np.nan
    text = str(value).strip().replace(',', '')
    if text in ('', '-', 'NA', 'N.A.', 'nan'):
        return np.nan
    try:
        return float(text)
    except ValueError:
        return np.nan


def read_wpi_old() -> pd.DataFrame:
    path = RAW / 'wpi_2011_12_monthly_202606.xls'
    raw = pd.read_excel(path, sheet_name='MONTHLY_INDEX', engine='xlrd')
    mask = raw['COMM_NAME'].astype(str).str.strip().str.casefold().eq('all commodities')
    if int(mask.sum()) != 1:
        raise ValueError(f'Expected exactly one All commodities row in {path.name}')
    row = raw.loc[mask].iloc[0]
    records = []
    for col in raw.columns:
        m = re.fullmatch(r'INDX(\d{2})(\d{4})', str(col))
        if not m:
            continue
        month, year = map(int, m.groups())
        value = pd.to_numeric(row[col], errors='coerce')
        if pd.notna(value):
            records.append({'period': pd.Period(year=year, month=month, freq='M'),
                            'index_2011_12': float(value)})
    out = pd.DataFrame(records).sort_values('period')
    if out.empty or out['period'].duplicated().any():
        raise ValueError('Old-base WPI contains no observations or duplicate months')
    out['yoy_pct'] = out['index_2011_12'].pct_change(12, fill_method=None) * 100
    out.to_csv(ROOT / 'data/processed/wpi_all_commodities_2011_12.csv', index=False)
    return out.set_index('period')['yoy_pct']


def read_wpi_current() -> pd.DataFrame:
    path = RAW / 'wpi_2022_23_monthly_202609.xlsx'
    raw = pd.read_excel(path, sheet_name=0, engine='openpyxl')
    name_col = 'Commodity Name'
    if name_col not in raw.columns:
        raise ValueError(f'Missing {name_col!r} in current WPI workbook')
    mask = raw[name_col].astype(str).str.strip().str.casefold().eq('all commodities')
    if 'Level' in raw.columns:
        mask &= raw['Level'].astype(str).str.strip().str.casefold().eq('all')
    if int(mask.sum()) != 1:
        raise ValueError(f'Expected exactly one current-base All Commodities row in {path.name}')
    row = raw.loc[mask].iloc[0]
    records = []
    for col in raw.columns:
        try:
            period = pd.Period(pd.to_datetime(str(col), format='%b-%y'), freq='M')
        except (ValueError, TypeError):
            continue
        value = pd.to_numeric(row[col], errors='coerce')
        if pd.notna(value):
            records.append({'period': period, 'index_2022_23': float(value)})
    out = pd.DataFrame(records).sort_values('period')
    if out.empty or out['period'].duplicated().any():
        raise ValueError('Current-base WPI contains no observations or duplicate months')
    out['yoy_pct'] = out['index_2022_23'].pct_change(12, fill_method=None) * 100
    out.to_csv(ROOT / 'data/processed/wpi_all_commodities_2022_23.csv', index=False)
    return out.set_index('period')['yoy_pct']


def read_credit() -> pd.DataFrame:
    """Parse RBI DBIE r539 New Format; values are Indian-grouped rupee crores."""
    path = RAW / 'rbi_credit_new_format.json'
    obj = json.loads(path.read_text())
    rows = obj.get('rows', [])
    dates_row = next((r for r in rows if str(r[3]) == '7'), None)
    credit_row = next((r for r in rows if len(r) > 5 and 'Non-food Credit' in str(r[5])), None)
    if dates_row is None or credit_row is None:
        raise ValueError('Could not find date row or Non-food Credit row in RBI DBIE JSON')
    records = []
    for date_cell, value_cell in zip(dates_row[6:], credit_row[6:]):
        if date_cell in (None, '') or value_cell in (None, ''):
            continue
        date = pd.to_datetime(str(date_cell), format='%d %B %Y', errors='coerce')
        value = parse_indian_number(value_cell)
        if pd.isna(date) or not np.isfinite(value):
            continue
        records.append({'period': date.to_period('M'), 'as_of_date': date.date().isoformat(),
                        'non_food_credit_rs_crore': float(value)})
    out = pd.DataFrame(records).sort_values('period')
    if out.empty or out['period'].duplicated().any():
        raise ValueError('RBI credit observations are empty or have duplicate monthly periods')
    periods = pd.PeriodIndex(out['period'], freq='M')
    expected = pd.period_range(periods.min(), periods.max(), freq='M')
    if not periods.equals(expected):
        missing = expected.difference(periods)
        raise ValueError(f'RBI credit monthly gaps detected: {list(map(str, missing[:12]))}')
    out['yoy_pct'] = out['non_food_credit_rs_crore'].pct_change(12, fill_method=None) * 100
    out.to_csv(ROOT / 'data/processed/rbi_nonfood_credit_monthly.csv', index=False)
    return out.set_index('period')


def load_data():
    d = pd.read_csv(SOURCE, low_memory=False)
    d['period'] = pd.to_datetime(d['obs_date']).dt.to_period('M')
    if d['period'].duplicated().any():
        d = d.drop_duplicates('period', keep='last')
    d = d.set_index('period').sort_index()
    start = pd.Period('2013-01', 'M')
    end = d.index.max()
    idx = pd.period_range(start, end, freq='M')
    p = d.reindex(idx).copy()
    y = pd.to_numeric(p['cpi_index_2024'], errors='coerce').pct_change(12, fill_method=None) * 100
    y.name = 'cpi_yoy_pct'

    usd_yoy = pd.to_numeric(p['usd_inr_monthly_average'], errors='coerce').pct_change(12, fill_method=None) * 100
    X = pd.DataFrame(index=idx)
    for lag in [1, 2, 3, 6, 12]:
        X[f'cpi_yoy_lag_{lag}'] = y.shift(lag)
    X['cfpi_yoy_lag_1'] = pd.to_numeric(p['cfpi_yoy_2012'], errors='coerce').shift(1)
    X['brent_yoy_lag_1'] = pd.to_numeric(p['oil_yoy'], errors='coerce').shift(1)
    X['repo_change_3m_lag_1'] = pd.to_numeric(p['repo_change_3m'], errors='coerce').shift(1)
    X['usd_inr_yoy_lag_1'] = usd_yoy.shift(1)
    X['iip_growth_2022_23_lag_1'] = pd.to_numeric(p['iip_general_growth_2022_23'], errors='coerce').shift(1)

    wpi_old = read_wpi_old()
    wpi_current = read_wpi_current()
    credit = read_credit()
    X['wpi_all_commodities_yoy_2011_12_lag_1'] = wpi_old.reindex(idx).shift(1)
    X['wpi_all_commodities_yoy_2022_23_lag_1'] = wpi_current.reindex(idx).shift(1)
    X['rbi_nonfood_credit_yoy_lag_2'] = credit['yoy_pct'].reindex(idx).shift(2)
    return p, y, X, {'wpi_old': wpi_old, 'wpi_current': wpi_current, 'credit': credit}


def features_for_horizon(X: pd.DataFrame, h: int, variant: str) -> pd.DataFrame:
    cols = BASE_FEATURES + VARIANTS[variant]
    z = X[cols].copy()
    target_periods = z.index + h
    angle = 2 * np.pi * (target_periods.month.to_numpy() - 1) / 12
    z['target_month_sin'] = np.sin(angle)
    z['target_month_cos'] = np.cos(angle)
    return z.replace([np.inf, -np.inf], np.nan)


def fit_ridge(Xtrain: pd.DataFrame, ytrain: np.ndarray, Xpred: pd.DataFrame):
    med = Xtrain.median(axis=0).fillna(0.0)
    a = Xtrain.fillna(med).to_numpy(dtype=float)
    b = Xpred.fillna(med).to_numpy(dtype=float)
    mu = a.mean(axis=0)
    sd = a.std(axis=0)
    sd = np.where(sd < 1e-8, 1.0, sd)
    za = (a - mu) / sd
    zb = (b - mu) / sd
    ym = float(np.mean(ytrain))
    beta = np.linalg.solve(za.T @ za + RIDGE_ALPHA * np.eye(za.shape[1]), za.T @ (ytrain - ym))
    pred = zb @ beta + ym
    model = {'feature_order': list(Xtrain.columns), 'median': med.to_dict(),
             'mean': dict(zip(Xtrain.columns, mu.tolist())),
             'scale': dict(zip(Xtrain.columns, sd.tolist())),
             'coefficients': dict(zip(Xtrain.columns, beta.tolist())),
             'target_intercept': ym, 'alpha': float(RIDGE_ALPHA)}
    return pred, model


def fit_xgb(Xtrain: pd.DataFrame, ytrain: np.ndarray, Xpred: pd.DataFrame):
    cols = list(Xtrain.columns)
    dtrain = xgb.DMatrix(Xtrain.to_numpy(dtype=float), label=ytrain, feature_names=cols, missing=np.nan)
    dpred = xgb.DMatrix(Xpred.to_numpy(dtype=float), feature_names=cols, missing=np.nan)
    booster = xgb.train(XGB_PARAMS, dtrain, num_boost_round=XGB_ROUNDS, verbose_eval=False)
    return booster.predict(dpred), booster


def fit_arima_forecast(history: np.ndarray, steps: int) -> float:
    clean = np.asarray(history, dtype=float)
    clean = clean[np.isfinite(clean)]
    if len(clean) < 36:
        raise ValueError(f'ARIMA requires >=36 actual CPI YoY observations, got {len(clean)}')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        result = ARIMA(clean, order=(1, 0, 0), trend='c', enforce_stationarity=False,
                       enforce_invertibility=False).fit(method_kwargs={'maxiter': 80})
        forecast = np.asarray(result.forecast(steps=steps), dtype=float)
    return float(forecast[-1])


def metric_row(model, variant, horizon, frame):
    a = frame['actual_cpi_yoy_pct'].to_numpy(dtype=float)
    q = frame['forecast_cpi_yoy_pct'].to_numpy(dtype=float)
    ok = np.isfinite(a) & np.isfinite(q)
    err = q[ok] - a[ok]
    return {'model': model, 'variant': variant, 'horizon_months': int(horizon),
            'n_test': int(ok.sum()),
            'mae_pp': float(np.mean(np.abs(err))) if ok.any() else np.nan,
            'rmse_pp': float(np.sqrt(np.mean(err ** 2))) if ok.any() else np.nan,
            'bias_pp': float(np.mean(err)) if ok.any() else np.nan,
            'test_start': frame['target_month'].min() if len(frame) else '',
            'test_end': frame['target_month'].max() if len(frame) else ''}


def main():
    for d in ['data/processed', 'results']:
        (ROOT / d).mkdir(parents=True, exist_ok=True)
    p, y, X, sources = load_data()
    valid_target = np.flatnonzero(y.notna().to_numpy())
    if len(valid_target) < 100:
        raise RuntimeError(f'Expected at least 100 observed CPI YoY targets, got {len(valid_target)}')
    last_target = int(valid_target[-1])
    test_start = max(int(valid_target[0]), last_target - HOLDOUT_MONTHS + 1)
    fold_rows = []

    for h in HORIZONS:
        feature_sets = {v: features_for_horizon(X, h, v) for v in VARIANTS}
        for target_i in range(test_start, last_target + 1):
            origin_i = target_i - h
            if origin_i < 0 or not np.isfinite(y.iloc[target_i]):
                continue
            actual = float(y.iloc[target_i])
            latest_known_i = origin_i - 1
            train_origins = np.arange(len(y), dtype=int)
            train_target_idx = train_origins + h
            bounded = np.minimum(train_target_idx, len(y) - 1)
            train_mask = (train_target_idx <= latest_known_i) & (train_target_idx < len(y))
            train_mask &= y.iloc[bounded].notna().to_numpy()
            train_origins = train_origins[train_mask]
            yt_idx = train_origins + h
            ytrain = y.iloc[yt_idx].to_numpy(dtype=float)
            if len(ytrain) < 36:
                continue
            target_month = str(y.index[target_i])
            origin_month = str(y.index[origin_i])
            common = {'target_month': target_month, 'forecast_origin_month': origin_month,
                      'horizon_months': h, 'actual_cpi_yoy_pct': actual,
                      'training_pairs': int(len(ytrain))}
            persist_i = origin_i - 1
            pers = float(y.iloc[persist_i]) if persist_i >= 0 and np.isfinite(y.iloc[persist_i]) else np.nan
            seasonal_i = target_i - 12
            seas = float(y.iloc[seasonal_i]) if seasonal_i >= 0 and np.isfinite(y.iloc[seasonal_i]) else np.nan
            hist = y.iloc[:origin_i].to_numpy(dtype=float)
            try:
                arima_pred = fit_arima_forecast(hist, h + 1)
            except Exception:
                arima_pred = np.nan
            fold_rows.extend([
                {**common, 'model': 'persistence', 'variant': 'benchmark', 'forecast_cpi_yoy_pct': pers},
                {**common, 'model': 'seasonal_naive', 'variant': 'benchmark', 'forecast_cpi_yoy_pct': seas},
                {**common, 'model': 'ARIMA_1_0_0', 'variant': 'univariate', 'forecast_cpi_yoy_pct': arima_pred},
            ])
            for variant, Xh in feature_sets.items():
                xtrain = Xh.iloc[train_origins]
                xpred = Xh.iloc[[origin_i]]
                try:
                    pred = float(fit_ridge(xtrain, ytrain, xpred)[0][0])
                except Exception:
                    pred = np.nan
                fold_rows.append({**common, 'model': 'Ridge', 'variant': variant,
                                  'forecast_cpi_yoy_pct': pred})
                try:
                    pred = float(fit_xgb(xtrain, ytrain, xpred)[0][0])
                except Exception:
                    pred = np.nan
                fold_rows.append({**common, 'model': 'XGBoost', 'variant': variant,
                                  'forecast_cpi_yoy_pct': pred})

    folds = pd.DataFrame(fold_rows)
    if folds.empty:
        raise RuntimeError('No rolling-origin folds were produced')
    folds.to_csv(ROOT / 'results/rolling_origin_forecasts.csv', index=False)
    metrics = []
    for (model, variant, h), group in folds.groupby(['model', 'variant', 'horizon_months'], sort=True):
        metrics.append(metric_row(model, variant, h, group))
    metrics_df = pd.DataFrame(metrics).sort_values(['horizon_months', 'model', 'variant'])
    metrics_df.to_csv(ROOT / 'results/rolling_origin_metrics.csv', index=False)

    # Compatibility table for direct comparison with the previous package's exact models.
    comp = metrics_df[((metrics_df.model.isin(['persistence', 'seasonal_naive', 'ARIMA_1_0_0'])) |
                       ((metrics_df.model.isin(['Ridge', 'XGBoost'])) & (metrics_df.variant == 'base')))].copy()
    comp.drop(columns=['variant']).to_csv(ROOT / 'results/baseline_compatible_metrics.csv', index=False)
    prev_path = ROOT / 'data/reference/previous_rolling_origin_metrics.csv'
    prev = pd.read_csv(prev_path)
    reproduced = comp.merge(prev, on=['model', 'horizon_months'], suffixes=('_new', '_previous'))
    for m in ['mae_pp', 'rmse_pp', 'bias_pp']:
        reproduced[f'{m}_difference'] = reproduced[f'{m}_new'] - reproduced[f'{m}_previous']
    reproduced.to_csv(ROOT / 'results/previous_baseline_reproduction_check.csv', index=False)

    # Feature-ablation deltas are descriptive: the holdout was not used to pick a winner.
    ablation = metrics_df[metrics_df.model.isin(['Ridge', 'XGBoost'])].pivot_table(
        index=['model', 'horizon_months'], columns='variant', values=['mae_pp', 'rmse_pp', 'bias_pp'])
    ablation.columns = [f'{metric}_{variant}' for metric, variant in ablation.columns]
    ablation = ablation.reset_index()
    for variant in VARIANTS:
        if variant == 'base':
            continue
        if f'rmse_pp_{variant}' in ablation:
            ablation[f'rmse_delta_{variant}_minus_base'] = ablation[f'rmse_pp_{variant}'] - ablation['rmse_pp_base']
    ablation.to_csv(ROOT / 'results/feature_ablation_summary.csv', index=False)

    # Train the full suite on all available observed target pairs; retain each feature variant.
    last_y = int(valid_target[-1])
    final_model_meta = {}
    final_forecasts = []
    origins_all = np.arange(len(y), dtype=int)
    issue_i = last_y + 1
    if issue_i >= len(X):
        raise RuntimeError('No input feature row after the latest observed target month')
    issue_month = y.index[issue_i]
    for h in HORIZONS:
        tix = origins_all + h
        mask = (tix < len(y))
        mask &= y.iloc[np.minimum(tix, len(y) - 1)].notna().to_numpy()
        origins = origins_all[mask]
        tix = origins + h
        ytrain = y.iloc[tix].to_numpy(dtype=float)
        arima_hist = y.iloc[:last_y + 1].dropna().to_numpy(dtype=float)
        arima_prediction = fit_arima_forecast(arima_hist, h + 1)
        final_forecasts.append({'forecast_origin_month': str(issue_month),
                                'latest_observed_cpi_month': str(y.index[last_y]),
                                'target_month': str(issue_month + h), 'horizon_months': h,
                                'model': 'ARIMA_1_0_0', 'variant': 'univariate',
                                'forecast_cpi_yoy_pct': arima_prediction,
                                'target_is_observed': 0, 'is_real_world_forecast': 0})
        for variant in VARIANTS:
            Xh = features_for_horizon(X, h, variant)
            xtrain = Xh.iloc[origins]
            xpred = Xh.iloc[[issue_i]]
            ridge_prediction, ridge_model = fit_ridge(xtrain, ytrain, xpred)
            ridge_path = ROOT / f'models/{variant}/ridge_cpi_yoy_h{h}.json'
            ridge_path.write_text(json.dumps(ridge_model, indent=2, allow_nan=False) + '\n')
            xgb_prediction, booster = fit_xgb(xtrain, ytrain, xpred)
            xgb_path = ROOT / f'models/{variant}/xgboost_cpi_yoy_h{h}.json'
            booster.save_model(str(xgb_path))
            final_model_meta[f'{variant}_h{h}'] = {
                'feature_order': list(Xh.columns), 'training_pairs': int(len(ytrain)),
                'ridge_file': str(ridge_path.relative_to(ROOT)),
                'xgboost_file': str(xgb_path.relative_to(ROOT)),
                'xgboost_feature_importance_gain': booster.get_score(importance_type='gain')
            }
            for model_name, prediction in [('Ridge', float(ridge_prediction[0])),
                                           ('XGBoost', float(xgb_prediction[0]))]:
                final_forecasts.append({'forecast_origin_month': str(issue_month),
                                        'latest_observed_cpi_month': str(y.index[last_y]),
                                        'target_month': str(issue_month + h), 'horizon_months': h,
                                        'model': model_name, 'variant': variant,
                                        'forecast_cpi_yoy_pct': prediction,
                                        'target_is_observed': 0, 'is_real_world_forecast': 0})
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        arima_result = ARIMA(y.dropna().to_numpy(dtype=float), order=(1, 0, 0), trend='c',
                             enforce_stationarity=False, enforce_invertibility=False).fit(method_kwargs={'maxiter': 100})
    with (ROOT / 'models/arima_cpi_yoy.pkl').open('wb') as f:
        pickle.dump(arima_result, f, protocol=pickle.HIGHEST_PROTOCOL)
    pd.DataFrame(final_forecasts).to_csv(ROOT / 'results/illustrative_future_forecasts.csv', index=False)

    # Persist a compact actual-data panel and a source inventory with file hashes.
    panel = pd.DataFrame({'period': X.index.astype(str), 'cpi_index_2024': p['cpi_index_2024'].to_numpy(),
                          'observed_cpi_yoy_pct': y.to_numpy()})
    for c in X.columns:
        panel[c] = X[c].to_numpy()
    panel.to_csv(ROOT / 'data/processed/enriched_training_panel.csv', index=False)
    source_rows = [
        {'series': 'CPI target and prior official features', 'agency': 'MoSPI and sources documented in original macro package',
         'file': 'data/source/macro_monthly_available.csv', 'url': 'Inherited from the user-provided India macro data package',
         'coverage_used': f'{y.dropna().index.min()} to {y.dropna().index.max()}', 'frequency': 'Monthly',
         'unit': 'Mixed original units; CPI target is derived YoY percent', 'sha256': sha256(SOURCE),
         'notes': 'Observed source panel only; no synthetic scenarios used.'},
        {'series': 'All-commodities WPI, base 2011-12', 'agency': 'Office of the Economic Adviser, DPIIT, Government of India',
         'file': 'data/raw/wpi_2011_12_monthly_202606.xls', 'url': 'https://eaindustry.nic.in/indx_download_1112/monthly_index_202606.xls',
         'coverage_used': f"{sources['wpi_old'].index.min()} to {sources['wpi_old'].index.max()}", 'frequency': 'Monthly',
         'unit': 'Index points, 2011-12=100; YoY percent derived within base',
         'sha256': sha256(RAW / 'wpi_2011_12_monthly_202606.xls'),
         'notes': 'Old-base series is kept separate from the 2022-23 base. Latest two months in OEA downloads can be provisional.'},
        {'series': 'All-commodities WPI, base 2022-23', 'agency': 'Office of the Economic Adviser, DPIIT, Government of India',
         'file': 'data/raw/wpi_2022_23_monthly_202609.xlsx', 'url': 'https://eaindustry.nic.in/indx_download_2223/wpi_monthly_index_202609.xlsx',
         'coverage_used': f"{sources['wpi_current'].index.min()} to {sources['wpi_current'].index.max()}", 'frequency': 'Monthly',
         'unit': 'Index points, 2022-23=100; YoY percent derived within base',
         'sha256': sha256(RAW / 'wpi_2022_23_monthly_202609.xlsx'),
         'notes': 'A distinct base regime, never linked or concatenated with the old-base series; recent values may be provisional.'},
        {'series': 'SCB non-food gross bank credit', 'agency': 'Reserve Bank of India, Database on Indian Economy',
         'file': 'data/raw/rbi_credit_new_format.json',
         'url': 'https://data-api.dbie.rbihub.in/api/tables/financial_sector/r539_deployment_of_bank_credit_by_major_sectors/rows?src_file=539--deployment-of-bank-credit-by-major-sectors--new-format.csv',
         'coverage_used': f"{sources['credit'].index.min()} to {sources['credit'].index.max()}", 'frequency': 'Monthly reporting-date stock',
         'unit': '₹ crore outstanding; YoY percent derived from same-source monthly levels',
         'sha256': sha256(RAW / 'rbi_credit_new_format.json'),
         'notes': 'Uses New Format selected on the public RBI DBIE table; values are provisional/revisable, dates are RBI reporting dates, not always calendar month-end.'}
    ]
    pd.DataFrame(source_rows).to_csv(ROOT / 'source_data_manifest.csv', index=False)

    arima_summary = {'order': [1, 0, 0], 'trend': 'c', 'n_observations': int(y.notna().sum()),
                     'aic': float(arima_result.aic), 'bic': float(arima_result.bic),
                     'params': {str(k): float(v) for k, v in zip(arima_result.param_names, arima_result.params)}}
    report = {
        'package_name': 'India CPI forecast model retraining with official WPI and RBI credit predictors',
        'target': 'MoSPI India headline CPI year-over-year percent change derived from the 2024-base CPI index',
        'target_observations': int(y.notna().sum()), 'target_start': str(y.dropna().index.min()),
        'target_end': str(y.dropna().index.max()), 'forecast_horizons_months': HORIZONS,
        'test_period': {'months': HOLDOUT_MONTHS, 'start': str(y.index[test_start]), 'end': str(y.index[last_target])},
        'method': 'Expanding rolling-origin validation; training targets restricted to those assumed known before each issue month. No random split.',
        'real_data_only': True, 'synthetic_rows_used': 0,
        'feature_variants': {k: BASE_FEATURES + v + ['target_month_sin', 'target_month_cos'] for k, v in VARIANTS.items()},
        'added_series': {
            'wpi_2011_12': {'observations': int(sources['wpi_old'].notna().sum()), 'coverage': [str(sources['wpi_old'].index.min()), str(sources['wpi_old'].index.max())], 'feature_lag_months': 1},
            'wpi_2022_23': {'observations': int(sources['wpi_current'].notna().sum()), 'coverage': [str(sources['wpi_current'].index.min()), str(sources['wpi_current'].index.max())], 'feature_lag_months': 1},
            'rbi_nonfood_credit': {'observations': int(sources['credit']['non_food_credit_rs_crore'].notna().sum()), 'coverage': [str(sources['credit'].index.min()), str(sources['credit'].index.max())], 'feature_lag_months': 2}
        },
        'model_settings': {'ridge_alpha': RIDGE_ALPHA, 'xgboost_parameters': XGB_PARAMS, 'xgboost_rounds': XGB_ROUNDS, 'arima': arima_summary},
        'metrics': metrics_df.to_dict(orient='records'),
        'baseline_reproduction_check_file': 'results/previous_baseline_reproduction_check.csv',
        'feature_ablation_file': 'results/feature_ablation_summary.csv',
        'final_model_files': final_model_meta,
        'source_panel_sha256': sha256(SOURCE),
        'software_versions': {'python': __import__('sys').version.split()[0], 'pandas': pd.__version__, 'numpy': np.__version__, 'xgboost': xgb.__version__, 'statsmodels': statsmodels.__version__},
        'important_limitations': [
            'This is an experimental prototype, not a deployment-ready model; the real target has only a short monthly history and the final 24-month test has just 24 cases per horizon.',
            'Source release vintages are unavailable. Lagging reduces obvious leakage but does not prove each value was available on the historical forecast date.',
            'RBI credit values are provisional/revisable and dated by reporting date; the current-format series begins in Jan 2019, leaving earlier model rows missing for this feature.',
            'The two WPI bases are distinct official regimes and are modeled as separate features. Their historical downloads are current snapshots, not first-release vintage archives.',
            'Recent WPI/credit features may be missing near the latest CPI observation because publisher release schedules differ.',
            'Feature ablation on the same rolling test is descriptive and not an unbiased hyperparameter/feature selection procedure; no winner is declared deployment-ready.',
            'M3 was excluded because its official XLSX route returned a human-verification challenge; no attempt was made to bypass it. FX backfill was excluded because its download path was account/OTP gated or unverified.',
            'The separate 10-million-row synthetic scenario data were excluded completely from fitting, validation, and feature construction.'
        ]
    }
    (ROOT / 'model_card_and_training_manifest.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'target_n': report['target_observations'], 'target_span': [report['target_start'], report['target_end']],
                      'test_span': [report['test_period']['start'], report['test_period']['end']],
                      'metrics_rows': len(metrics_df), 'WPI_old_span': [str(sources['wpi_old'].index.min()), str(sources['wpi_old'].index.max())],
                      'WPI_current_span': [str(sources['wpi_current'].index.min()), str(sources['wpi_current'].index.max())],
                      'credit_span': [str(sources['credit'].index.min()), str(sources['credit'].index.max())],
                      'package': str(ROOT)}, indent=2))


if __name__ == '__main__':
    main()
