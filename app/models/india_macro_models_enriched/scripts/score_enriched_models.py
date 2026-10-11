#!/usr/bin/env python3
"""Score packaged direct CPI models from a CSV of observed-lag features."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

HORIZONS = [1, 3, 6]
VARIANTS = ['base', 'wpi_old', 'wpi_current', 'credit', 'wpi_old_credit', 'wpi_current_credit', 'all']


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', required=True, type=Path, help='CSV with forecast_origin_month, horizon_months, and the model features')
    ap.add_argument('--output', required=True, type=Path)
    ap.add_argument('--variant', choices=VARIANTS, default='all')
    ap.add_argument('--model-root', type=Path, default=Path(__file__).resolve().parents[1] / 'models')
    a = ap.parse_args()

    d = pd.read_csv(a.input)
    for c in ['forecast_origin_month', 'horizon_months']:
        if c not in d.columns:
            raise ValueError(f'Missing required metadata column {c!r}')
    d['horizon_months'] = pd.to_numeric(d['horizon_months'], errors='raise').astype(int)
    if not d['horizon_months'].isin(HORIZONS).all():
        raise ValueError('horizon_months must be 1, 3, or 6')
    origin = pd.PeriodIndex(d['forecast_origin_month'].astype(str), freq='M')
    target = origin + d['horizon_months'].to_numpy()
    angle = 2 * np.pi * (target.month.to_numpy() - 1) / 12
    d['target_month_sin'] = np.sin(angle)
    d['target_month_cos'] = np.cos(angle)
    d['target_month'] = target.astype(str)
    d['ridge_forecast_cpi_yoy_pct'] = np.nan
    d['xgboost_forecast_cpi_yoy_pct'] = np.nan

    for h in HORIZONS:
        ix = np.flatnonzero(d['horizon_months'].to_numpy() == h)
        if not len(ix):
            continue
        folder = a.model_root / a.variant
        rp = json.loads((folder / f'ridge_cpi_yoy_h{h}.json').read_text())
        cols = rp['feature_order']
        missing = [c for c in cols if c not in d.columns]
        if missing:
            raise ValueError(f'Missing feature columns for variant={a.variant}, horizon={h}: {missing}')
        frame = d.iloc[ix][cols].apply(pd.to_numeric, errors='coerce')
        med = pd.Series(rp['median']).reindex(cols)
        vals = frame.fillna(med).to_numpy(dtype=float)
        mu = np.array([rp['mean'][c] for c in cols], dtype=float)
        scale = np.array([rp['scale'][c] for c in cols], dtype=float)
        beta = np.array([rp['coefficients'][c] for c in cols], dtype=float)
        d.loc[ix, 'ridge_forecast_cpi_yoy_pct'] = ((vals - mu) / scale) @ beta + float(rp['target_intercept'])
        booster = xgb.Booster()
        booster.load_model(str(folder / f'xgboost_cpi_yoy_h{h}.json'))
        dm = xgb.DMatrix(frame.to_numpy(dtype=float), feature_names=cols, missing=np.nan)
        d.loc[ix, 'xgboost_forecast_cpi_yoy_pct'] = booster.predict(dm)

    d['model_variant'] = a.variant
    d['target_is_observed'] = 0
    d['is_real_world_forecast'] = 0
    a.output.parent.mkdir(parents=True, exist_ok=True)
    d.to_csv(a.output, index=False)
    print(f'Wrote {len(d)} illustrative forecasts to {a.output}')


if __name__ == '__main__':
    main()
