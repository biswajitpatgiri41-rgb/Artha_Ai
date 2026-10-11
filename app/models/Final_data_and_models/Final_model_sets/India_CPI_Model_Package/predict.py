#!/usr/bin/env python3
"""Display the latest forecast already stored in a trained model registry."""
import argparse, json
from pathlib import Path
import joblib
import pandas as pd

p=argparse.ArgumentParser()
p.add_argument('--registry',default='artifacts/mospi_2024_base/models/model_registry.joblib')
p.add_argument('--output',default=None)
a=p.parse_args()
registry=joblib.load(a.registry)
meta=registry['metadata'];origin=meta['forecast_origin'];models=registry['final_forecasts']
weights={int(k):v for k,v in registry['weights'].items()}
cal={int(k):v for k,v in registry['calibration'].items()}
rows=[]
for h in meta['horizons']:
    vals={m:float(v[h-1]) for m,v in models.items() if len(v)>=h and pd.notna(v[h-1])}
    w={m:v for m,v in weights.get(h,{}).items() if m in vals};den=sum(w.values())
    forecast=sum(vals[m]*w[m] for m in w)/den if den else vals.get('SeasonalNaive')
    c=cal.get(h,{})
    rows.append({'series':meta['series'],'forecast_origin':origin,'target_month':str(pd.Period(origin,freq='M')+h),
        'horizon_months':h,'ensemble_forecast_yoy_pct':forecast,
        'interval80_low':forecast-c.get('q80_abs',float('nan')),'interval80_high':forecast+c.get('q80_abs',float('nan')),
        'interval95_low':forecast-c.get('q95_abs',float('nan')),'interval95_high':forecast+c.get('q95_abs',float('nan')),
        'components_json':json.dumps(vals),'weights_json':json.dumps(w),
        'note':'Stored forecast from the saved training origin. New source observations require validated retraining.'})
df=pd.DataFrame(rows)
if a.output: df.to_csv(a.output,index=False)
print(df.to_string(index=False))
