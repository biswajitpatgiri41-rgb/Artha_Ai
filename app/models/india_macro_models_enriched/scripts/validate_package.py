#!/usr/bin/env python3
"""Validate the self-contained enriched model package and write a JSON report."""
import hashlib
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def require(condition, message, failures):
    if not condition:
        failures.append(message)


def main():
    failures = []
    checks = []
    source_manifest = pd.read_csv(ROOT / 'source_data_manifest.csv')
    hash_results = {}
    for row in source_manifest.to_dict(orient='records'):
        path = ROOT / row['file']
        actual = sha256(path) if path.is_file() else None
        ok = actual == row['sha256']
        hash_results[row['file']] = {'expected': row['sha256'], 'actual': actual, 'ok': ok}
        require(ok, f'Source checksum mismatch/missing file: {row["file"]}', failures)
    checks.append('all raw/input source hashes match source_data_manifest.csv')

    panel = pd.read_csv(ROOT / 'data/processed/enriched_training_panel.csv')
    targets = pd.to_numeric(panel['observed_cpi_yoy_pct'], errors='coerce').dropna()
    require(len(targets) == 152, f'Expected 152 observed CPI YoY labels; found {len(targets)}', failures)
    require(panel['period'].is_unique, 'Monthly feature panel has duplicate period keys', failures)
    checks.append('observed target count and unique monthly panel keys')

    series = {}
    for filename in ['wpi_all_commodities_2011_12.csv', 'wpi_all_commodities_2022_23.csv', 'rbi_nonfood_credit_monthly.csv']:
        d = pd.read_csv(ROOT / 'data/processed' / filename)
        require(d['period'].is_unique, f'Duplicate periods in {filename}', failures)
        series[filename] = {'rows': len(d), 'first_period': str(d['period'].min()), 'last_period': str(d['period'].max())}
    require(series['wpi_all_commodities_2011_12.csv']['rows'] == 169, 'Unexpected old-base WPI row count', failures)
    require(series['wpi_all_commodities_2022_23.csv']['rows'] == 41, 'Unexpected current-base WPI row count', failures)
    require(series['rbi_nonfood_credit_monthly.csv']['rows'] == 91, 'Unexpected RBI credit row count', failures)
    checks.append('WPI base regimes and monthly RBI credit export retain expected row counts')

    forecasts = pd.read_csv(ROOT / 'results/rolling_origin_forecasts.csv')
    metrics = pd.read_csv(ROOT / 'results/rolling_origin_metrics.csv')
    require(len(metrics) == 51, f'Expected 51 model/horizon metric rows; found {len(metrics)}', failures)
    require(metrics['n_test'].eq(24).all(), 'At least one rolling metric does not contain 24 test cases', failures)
    counts = forecasts.groupby(['model', 'variant', 'horizon_months']).size()
    require(counts.eq(24).all(), 'At least one rolling model/variant/horizon lacks 24 forecasts', failures)
    require(not forecasts.duplicated(['model', 'variant', 'horizon_months', 'target_month']).any(), 'Duplicate rolling forecast keys', failures)
    checks.append('all rolling-origin model/variant/horizon groups have 24 unique test predictions')

    compare = pd.read_csv(ROOT / 'results/previous_baseline_reproduction_check.csv')
    delta_cols = [c for c in compare.columns if c.endswith('_difference')]
    max_delta = float(compare[delta_cols].abs().to_numpy().max())
    require(max_delta < 1e-8, f'Baseline metrics differ from prior model by {max_delta}', failures)
    checks.append('baseline model metrics reproduce the previous package within 1e-8')

    variants = ['base', 'wpi_old', 'wpi_current', 'credit', 'wpi_old_credit', 'wpi_current_credit', 'all']
    model_files = []
    for v in variants:
        for family in ['ridge', 'xgboost']:
            for h in [1, 3, 6]:
                f = ROOT / f'models/{v}/{family}_cpi_yoy_h{h}.json'
                require(f.is_file() and f.stat().st_size > 0, f'Missing/empty model artifact: {f.relative_to(ROOT)}', failures)
                if f.is_file(): model_files.append(f)
    arima = ROOT / 'models/arima_cpi_yoy.pkl'
    require(arima.is_file() and arima.stat().st_size > 0, 'Missing/empty ARIMA artifact', failures)
    require(len(model_files) == 42, f'Expected 42 Ridge/XGBoost artifacts; found {len(model_files)}', failures)
    checks.append('42 Ridge/XGBoost artifacts and one ARIMA artifact exist')

    sample = pd.read_csv(ROOT / 'results/example_scoring_output_all.csv')
    require(len(sample) == 3 and sample['horizon_months'].tolist() == [1, 3, 6], 'Scoring smoke-test output does not contain horizons 1, 3, 6', failures)
    require(sample[['ridge_forecast_cpi_yoy_pct', 'xgboost_forecast_cpi_yoy_pct']].notna().all().all(), 'Scoring smoke test contains missing predictions', failures)
    checks.append('packaged scorer successfully emitted three finite sample forecasts')

    report = {
        'validation_status': 'passed' if not failures else 'failed',
        'checks': checks,
        'failures': failures,
        'observed_cpi_yoy_labels': int(len(targets)),
        'target_period': [str(panel.loc[pd.to_numeric(panel['observed_cpi_yoy_pct'], errors='coerce').notna(), 'period'].min()),
                          str(panel.loc[pd.to_numeric(panel['observed_cpi_yoy_pct'], errors='coerce').notna(), 'period'].max())],
        'rolling_metric_rows': int(len(metrics)),
        'rolling_forecast_rows': int(len(forecasts)),
        'max_abs_baseline_metric_difference': max_delta,
        'processed_series': series,
        'verified_source_hashes': hash_results,
        'saved_direct_model_count': len(model_files),
        'arima_artifact_bytes': int(arima.stat().st_size) if arima.is_file() else 0,
        'synthetic_rows_used': 0
    }
    out = ROOT / 'results/validation_report.json'
    out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
