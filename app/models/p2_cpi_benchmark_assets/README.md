# P2 CPI benchmark data and artifacts

`source/master_data1.csv` and its `LICENSE` were copied from
[ketandeshmukh1920/p2-india-cpi-forecasting](https://github.com/ketandeshmukh1920/p2-india-cpi-forecasting)
at commit `ce8abb01d2ec0fd7524638995281e32a8142f1d1`. The dataset is pinned by
SHA-256 in `app/models/p2_cpi_benchmark.py`.

This data is a separate research panel. Its CPI target is not the app's
MoSPI 2024-base headline CPI target, so do not merge, substitute, or compare
its forecast values directly with the app's canonical model package.

## Importing Colab-trained artifacts

The Colab notebook writes its model ZIP to Google Drive. Download that ZIP to
this project machine, then run from the project root in PowerShell:

```powershell
python scripts\import_p2_cpi_bundle.py --bundle "C:\path\to\p2_cpi_training_run.zip"
```

The importer checks the ZIP contents, source commit, and dataset checksum
before installing the files to this directory's `artifacts` subfolder. It
refuses to overwrite an existing model run. Install the optional forecasting
dependencies with `python -m pip install -e ".[econometrics]"`.

The original bundle contains pickle-based `joblib` models. Only import a ZIP
created by your trusted Colab training run. Its ARIMAX fit did not converge,
and its XGBoost pickle can warn when loaded under a different XGBoost version.
The API does not load that legacy XGBoost pickle. The models support only
one-step-ahead experimental forecasts from the P2 panel; this feature does not
replace or update the app's current MoSPI forecast package.

After importing the Colab bundle, regenerate the two compatibility-sensitive
models from the pinned local dataset:

```powershell
python scripts\retrain_p2_compat_models.py
```

This retrains ARIMAX with standardized inputs after removing its exactly
redundant term-spread feature, and requires convergence at all 52 historical
walk-forward origins and on the final fit. It retrains XGBoost in the installed
environment and saves the booster in XGBoost's native JSON format instead of
loading the older pickle artifact. Both regenerated models are smoke-tested
before the files are installed. Their new metrics and software versions are
recorded in `artifacts/retrained_models_manifest.json`. The API uses these new
artifacts when they are available. Use `--force` only when you intentionally
want to replace these regenerated artifacts.
