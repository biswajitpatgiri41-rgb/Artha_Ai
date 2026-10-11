# India CPI forecasting prototype — Kaggle data + final MoSPI target

## What is included

This package contains the original Kaggle dataset archive and extracted CSV, the matching MoSPI/data.gov.in 2012-base sector/category archive through August 2025, MoSPI’s December 2025 CPI release and February 2026 finalization release, normalized datasets, five model families, rolling-origin forecasts, metrics, scorecard, reproducible scripts, and SHA-256 provenance records.

The target is **MoSPI-published All-India General CPI year-over-year inflation on the 2012=100 base**. The target table covers January 2014–December 2025 and contains 142 published values. MoSPI marks April and May 2020 with dashes; those targets remain missing. The model never trains on synthetic inflation observations, and it never interpolates a missing CPI target. [1] [2]

## Data selection and vintage caveat

The Kaggle listing attributes the index data to MoSPI/data.gov.in and describes coverage through October 2023. The downloaded Kaggle CSV actually ends in May 2023 for Rural and Urban and April 2023 for Rural+Urban. Across the Kaggle file’s 371 overlapping sector-month rows and 27 measures, the values and missingness match the archived first-party data.gov.in file exactly (10,017 cells). [3] [4]

MoSPI’s later final 2012-base time-series tables revise some historical values relative to the older Kaggle/data.gov.in archive: 10 of 149 overlapping Combined General index values differ, with a maximum difference of 2.1 index points. The published YoY target is therefore taken directly from the later MoSPI release. The older Kaggle/data.gov.in category and sector indices are preserved separately as observed model features; no source vintage is silently blended. The detailed comparison and hashes are in `source_research_notes.md` and `data/processed/source_manifest.json`. [1] [4]

The old 2012=100 CPI series ends in December 2025. MoSPI introduced a 2024=100 series in February 2026. This package does **not** mix the new base into the older target. The included model is not production-ready for the current 2024-base CPI; it requires new-base data, a fresh training window, and revalidation before deployment. [2]

## Backtest results

I evaluated Persistence, Seasonal Naive, ARIMA(1,0,0), Ridge, and XGBoost with monthly expanding-window rolling origins. Forecast issue months begin January 2018. Each horizon predicts the target at `origin month + horizon`; the model only receives values dated at or before the origin. The test spans 94, 92, and 89 observed target months for 1-, 3-, and 6-month forecasts, respectively.

The best learned family by pooled rolling-origin MAE is **ARIMA(1,0,0)** (0.990 percentage points across 275 forecasts). It does not clear every horizon’s prototype gate. By horizon, the lowest-MAE backtest strategy was ARIMA for 1 month, Persistence for 3 months, and ARIMA for 6 months. The six-month ARIMA skill over persistence is 4.8%; the one-month ARIMA result is effectively a tie. Ridge did not beat persistence at any tested horizon. XGBoost only marginally beat persistence at six months.

The scorecard uses a minimum of 60 forecasts and MAE skill versus Persistence of at least zero. These are internal prototype gates, not official or regulatory standards.

| Model | Horizon | Forecasts / 60 minimum | MAE (pp) | Persistence MAE (pp) | MAE skill vs persistence | Result |
|---|---:|---:|---:|---:|---:|---|
| ARIMA(1,0,0) | 1 month | 94 / 60 | 0.572 | 0.572 | 0.001 | Pass, effectively tied |
| Ridge | 1 month | 94 / 60 | 0.636 | 0.572 | -0.111 | Fail |
| XGBoost | 1 month | 94 / 60 | 0.733 | 0.572 | -0.280 | Fail |
| ARIMA(1,0,0) | 3 months | 92 / 60 | 1.097 | 1.096 | -0.001 | Fail |
| Persistence | 3 months | 92 / 60 | 1.096 | 1.096 | 0.000 | Pass |
| Ridge | 3 months | 92 / 60 | 1.347 | 1.096 | -0.229 | Fail |
| XGBoost | 3 months | 92 / 60 | 1.298 | 1.096 | -0.184 | Fail |
| ARIMA(1,0,0) | 6 months | 89 / 60 | 1.322 | 1.389 | 0.048 | Pass |
| Ridge | 6 months | 89 / 60 | 1.672 | 1.389 | -0.204 | Fail |
| XGBoost | 6 months | 89 / 60 | 1.376 | 1.389 | 0.009 | Pass, marginal |

The complete MAE, RMSE, bias, median absolute error, and both benchmark skills for every model and horizon are in `reports/metrics_by_model_horizon.csv`. The full threshold comparison is in `reports/threshold_scorecard.csv`. The backtest is evidence for a prototype only; it does not establish “perfect,” reliable future, or production performance.

## Main files

- `data/raw/kaggle/`: Kaggle ZIP and extracted CSV.
- `data/raw/official/`: data.gov.in CSV and the two MoSPI source PDFs plus extracted text.
- `data/processed/india_cpi_observations_long.csv`: normalized observation-level records with source lineage.
- `data/processed/india_cpi_monthly_panel.csv`: 156-month monthly panel, category/sector values, final official index and target.
- `data/processed/india_headline_cpi_target.csv`: target and source-vintage comparison series.
- `data/processed/source_manifest.json`: raw-file hashes, coverage, and reconciliation checks.
- `models/best_trained_model.pkl`: selected best learned candidate, ARIMA(1,0,0), with 1/3/6-month horizon results.
- `models/`: horizon-specific `.pkl` files for Persistence, Seasonal Naive, ARIMA, Ridge, and XGBoost, plus best-model bundles and SHA-256 manifest.
- `reports/evaluation_summary.md`: detailed results and thresholds.
- `reports/artifact_validation.json`: dataset-count checks, hashes and successful loading of all 17 model pickles.
- `reports/archived_2012_base_forecasts.csv`: reproducible 1/3/6-month example forecasts, marked not comparable with the new CPI base.
- `reports/training_config.json`: training, backtest, feature, threshold, and library-version details.
- `scripts/`: downloader, normalizer, feature builder, trainer, and inference utility.

## Reproduce and use

The raw snapshots required to reproduce the delivered models are included. To install the Python dependencies, run `pip install -r requirements.txt`; PDF extraction uses Poppler’s `pdftotext`. To rebuild the normalized panel and models, run:

```bash
python3 scripts/normalize_india_kaggle.py
python3 scripts/train_india_models.py
```

To refresh sources from public URLs, run `python3 scripts/download_source_data.py` first. A refresh may produce changed source revisions; compare its hashes with `data/processed/source_manifest.json` before retraining.

To load and run the selected learned model, use:

```bash
python3 scripts/predict_india_cpi.py
```

That command emits projections for the discontinued 2012-base series and warns that they are not comparable with the current 2024-base CPI. Pickle files should only be loaded from a trusted source. Training-library versions are recorded in `reports/training_config.json`; install compatible versions before unpickling.

## References

[1]: https://www.mospi.gov.in/uploads/latestReleases/latest_release_1768213461321_53cd35fd-1bbc-4b43-b92d-8fb67474ee74_Press_Release_of_CPI_for_December_2025.pdf "MoSPI: CPI release for December 2025, Annexures VI–VII"
[2]: https://www.mospi.gov.in/uploads/latestReleases/latest_release_1770891893893_6b458c0a-c327-4fef-a554-41131ea67273_Press_Relase_of_CPI_for_Jan26.pdf "MoSPI: January 2026 CPI release finalizing December 2025 at base 2012=100"
[3]: https://www.kaggle.com/datasets/yatharthgupta18/all-india-consumer-price-index20132023 "Kaggle: All India Consumer Price Index (2013–2023)"
[4]: https://www.data.gov.in/resource/all-india-consumer-price-index-ruralurban-upto-august-2025 "MoSPI/data.gov.in: All India CPI through August 2025"
