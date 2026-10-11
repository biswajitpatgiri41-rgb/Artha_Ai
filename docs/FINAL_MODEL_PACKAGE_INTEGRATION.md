# Final model package integration

The runtime reads the model and dataset bundle in `app/models/Final_data_and_models/Final_model_sets/India_CPI_Model_Package`.

## Runtime routes

- `GET /forecast/final/models` returns model metrics, ensemble weights, and recorded interval coverage from the package evaluation CSVs.
- `GET /forecast/final?model=ensemble&variant=mospi_2024_base&horizon=6` returns a stored forecast row with its model, data origin, interval, and warnings.
- `GET /forecast/final/explainability?model=xgboost&variant=mospi_2024_base&horizon=6` returns stored SHAP values when present.
- `GET /models/registry` exposes package model artifacts as `CANDIDATE` records with checksummed artifact-set hashes and stored evaluation metrics. Nothing is automatically promoted.
- `GET /series` and `GET /series/cpi_yoy` use the bundled MoSPI CPI target as a fallback only when no project CPI YoY observations are available.

The Data Explorer replaces its headline CPI mock series with this packaged series when the API and data are available. Other series remain marked as mock. If the endpoint or packaged target is unavailable, the existing mock catalog remains visible.

Set `FINAL_MODEL_PACKAGE_DIR` to the directory containing `SHA256SUMS.txt` if a deployment stores the bundle outside the Python package. The package is also declared as setuptools package data so it is included in built distributions.

## Runtime and model safety

The API validates each consumed CSV/JSON file against the bundle's SHA-256 manifest. It reads exported forecast/evaluation records and does not load the included `.joblib` files. The output is an archived forecast from the package origin, not a fresh inference from current inputs. The normal `/forecast` and `/backtest` contracts remain unchanged.

## Production limitations

The package's latest CPI observation is 2026-08. Its comparison period was used to compare feature variants, so it is not an untouched final holdout. It has no historical real-time release vintages, its 2025 YoY target includes values derived from rounded CPI index levels, and its interval coverage is imperfect at longer horizons. The API surfaces these caveats in forecast responses. These artifacts are research outputs and do not by themselves establish production model readiness. Live inference, prospective validation, release-vintage data, monitoring, and model-promotion controls remain separate work.
