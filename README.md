# Research API and current integration status

The existing research terminal already contains the page shell, agent modules,
source adapters, canonical observation schema, feature-building scripts, and
provenance snapshots. The API exposes the following deterministic research
tools so the interface can distinguish available observations from placeholders:

| Route | Purpose |
| --- | --- |
| `GET /series` | Registry metadata plus local observation availability and latest value |
| `GET /series/{series_id}` | Local observations with date, source, and unit |
| `GET /sources` | Source registry summary and local availability |
| `GET /forecast?series_id=cpi_yoy&horizon=6` | Seasonal-naive benchmark based on project observations |
| `GET /forecast?model=ridge&variant=base&horizon=6` | Packaged CPI model forecast (Ridge, XGBoost, ARIMA, or Ridge/XGBoost average; direct horizons 1, 3, 6) |
| `POST /forecast` | Same forecast options using a JSON request body |
| `GET /backtest?series_id=cpi_yoy&horizon=1` | Expanding-window rolling-origin MAE, RMSE, and bias |
| `POST /backtest` | Same evaluation using a JSON request body |
| `POST /simulate` | Transparent scenario sensitivity using explicitly supplied baseline and shocks |
| `POST /research` | Run the deterministic evidence pipeline and persist its audit record |
| `GET /research/{run_id}` | Retrieve a persisted research run |
| `GET /research/{run_id}/events` | Retrieve operational events without hidden reasoning |
| `GET /reports/{run_id}` | Retrieve the structured run report |
| `POST /assistant/chat` | Page-aware language-model assistant (requires provider configuration) |

Run the backend from this directory with `uvicorn app.api.main:app --reload`.
Run the terminal from `frontend` with `npm run dev`; configure
`NEXT_PUBLIC_API_BASE_URL` when the backend is not at `http://localhost:8000`.

For a reproducible deployment, copy `.env.example` to `.env`, replace every
placeholder secret, set `ENVIRONMENT=production`, and run
`docker compose up --build`. The API is exposed on port 8000, the research
frontend on port 3000, and the admin frontend on port 3001. Set
`BACKEND_INTERNAL_URL` to the API service URL used by the admin frontend when
deploying the services separately. Do not expose the API directly to the
internet without configuring production authentication, HTTPS at the reverse
proxy, and restrictive `CORS_ALLOWED_ORIGINS`.

For GitHub and Vercel deployment, follow
[docs/VERCEL_DEPLOYMENT.md](docs/VERCEL_DEPLOYMENT.md). The Vercel setup uses
three projects from this repository: the FastAPI API at the repository root,
the public frontend with root directory `frontend`, and the admin frontend
with root directory `admin-frontend`.

See [docs/security-review.md](docs/security-review.md) for the current security
controls, threat model, and deployment blockers. The application does not yet
implement user authentication or authorization and must not be exposed as a
public multi-user service until those controls are added.

Install the Python project with `python -m pip install -e ".[econometrics,evidence-local,local-storage]"`
and frontend packages with `npm install` from `frontend`. The backend can also
be installed with `python -m pip install -r requirements.txt`.

Forecast and backtest routes return a data-unavailable response when the
requested registered series has no local observations or too little history.
They do not substitute dashboard mock values. The scenario endpoint is an
illustrative teaching calculation: its coefficients are not estimated from
Indian data and do not support causal or policy claims. The simulator sends
inputs to that API and has a clearly labeled local fallback. The forecast page
shows API model/benchmark and rolling-origin outputs alongside a separately labeled
mock chart. The data explorer still labels its static table as illustrative
while displaying whether project observations are available.

### Packaged CPI research models

The Forecasts page and `/forecast` API can serve the trained artifacts in
`app/models/india_macro_models_enriched`. Select `model=ridge`, `xgboost`,
`arima`, or `ensemble`; choose one of the `base`, WPI, credit, or combined
feature variants. Example:

```text
GET /forecast?series_id=cpi_yoy&model=xgboost&variant=base&horizon=6
```

These forecasts use the frozen `enriched_training_panel.csv` shipped with the
model package. New project uploads do not automatically rebuild the trained
feature panel or retrain these models. Responses include this limitation and
the model package's small-holdout warning. Horizon 12 remains available for the
seasonal-naive benchmark only. XGBoost and ARIMA require the optional
`econometrics` dependencies (`python -m pip install -e ".[econometrics]"`).
The separate seasonal-naive backtest shown in the UI is not a backtest of the
selected trained model.

### Optional P2 CPI benchmark

The project includes a separately labeled P2 CPI/macro dataset from the
MIT-licensed `ketandeshmukh1920/p2-india-cpi-forecasting` repository, pinned to
its source commit and dataset checksum. It is intentionally isolated from the
MoSPI 2024-base package because the target series and data vintage differ.

To install the models trained by `notebooks/train2.ipynb`, download that run's
ZIP from Google Drive and import it from the project root:

```powershell
python scripts\import_p2_cpi_bundle.py --bundle "C:\path\to\p2_cpi_training_run.zip"
```

Install `python -m pip install -e ".[econometrics]"` before serving models.
The optional API endpoints are `GET /forecast/p2/models` and
`GET /forecast/p2?model=p2_arima`; forecasts are one month ahead and explicitly
use the external P2 panel. The ARIMAX artifact from the checked training run
did not converge. The artifacts in this workspace have been regenerated with
`python scripts\retrain_p2_compat_models.py`: it removes an exactly redundant
ARIMAX predictor, standardizes the remaining inputs, requires convergence
across all evaluation origins, and saves XGBoost in native JSON format. Run
that command after importing the bundle in a fresh checkout. These research
models do not replace or alter the existing packaged forecast endpoints. See
[`app/models/p2_cpi_benchmark_assets/README.md`](app/models/p2_cpi_benchmark_assets/README.md)
for provenance, import, and trust guidance.

PDF evidence uploads use the `/evidence/upload` endpoint. Text extraction uses
`pypdf`; local semantic indexing uses the `evidence-local` extra, which installs
Sentence Transformers and downloads its embedding model on first use. On
Windows, the project installs the `python-magic-bin` MIME detector.

## Remaining integration work

- Connect verified MoSPI, RBI, and IMD source adapters and confirm provider IDs.
- Add CPI history with release and retrieval timestamps before treating model
  outputs as empirical.
- Replace the illustrative scenario coefficients with documented estimates,
  add uncertainty calibration, and validate across rolling origins.
- Complete the orchestration graph and connect the critic/report agents to
  calculated evidence. Language-model agents should explain results, not create
  economic observations.
- Persist research runs, reports, and audit events for the research terminal.

## Downloading project data

Configure `FRED_API_KEY` and `EIA_API_KEY` in the local `.env`, then run from
the project root:

```powershell
python -m scripts.download_project_data --sources all
```

Choose `fred`, `eia`, or `world_bank` to fetch one provider. Each run appends
raw snapshots under `data/raw`, canonical observations under `data/interim`,
and provenance plus a per-run status report under `data/manifests`. Do not put
`.env` in source control. World Bank CPI and GDP series are annual context only;
they are not interpolated into the monthly model panel.

The current downloader does not claim the model is training-ready. MoSPI
headline CPI, food CPI, and IIP still need more history. RBI repo-rate history
uses the official DBIE export/import workflow below; RBI credit/M3 and IMD
rainfall still need verified sources and mappings. Monthly model training
remains blocked until the India CPI target history is sufficient.

### Import the official RBI repo-rate history

RBI's official DBIE identifies the policy-rate history under **Statistics →
Financial Sector → Key Rates → Major Monetary Policy Measures – Bank Rate,
CRR & SLR**. RBI documents CSV/Excel export from DBIE, but does not publish a
stable public API contract for this report. The project therefore does not use
an invented series ID, API key, or undocumented gateway call. Open the official
portal and save the unmodified CSV/Excel export in `data/raw/rbi`:

```powershell
python -m scripts.download_rbi_data --open-portal
```

Then import and validate it:

```powershell
python -m scripts.download_rbi_data
```

Or pass a specific export with `--input path/to/export.xlsx`. The importer
preserves the source file, verifies effective-date and policy-repo-rate
columns, checks duplicate dates and plausible percent values, and writes
canonical effective-date observations to `data/interim` plus a provenance
manifest to `data/manifests`. There is no RBI API key requirement for this
public DBIE export. Because RBI policy rates change on irregular effective
dates, the monthly builder carries the last effective rate forward when it
constructs the monthly panel. No missing repo observations are fabricated.

### Import manually downloaded MoSPI Excel releases

Copy original MoSPI CPI press-release workbooks into `data/raw/mospi`, then run:

```powershell
python -m scripts.import_mospi_excel
```

The importer reads combined headline CPI index history from Annex-IV and the
combined Food and Beverages division index from Annex-I. It writes canonical
monthly JSON observations and source-file checksums to `data/interim` and
`data/manifests`. It does not fill missing months. The current files in the
folder provide only 19 headline observations (Jan 2025–Jul 2026) and 3 food
observations (Jun–Aug 2026); they are not enough history to train or backtest
the planned monthly models. No IIP workbook is present yet.

The PDF guides define the requirements source. The architecture image included
with the project request summarizes the intended flow: source adapters and
provenance, canonical data, feature creation, deterministic forecasts and
backtests, scenario comparison, and agent-written explanations over tool
results. This implementation adds and persists the deterministic evidence run;
it does not claim the specialist LangGraph/LLM workflow or live streaming is
complete yet.

### Uploading and updating project datasets

The Data Explorer includes a dataset management section. It accepts CSV and
`.xlsx`/`.xlsm` files with `date,value` columns and optional `release_date`,
`source`, `unit`, `base_year`, `seasonal_adjustment`, and `revision_tag` columns.
The API retains the uploaded original under `data/raw/<source>/`, writes
normalized observations under `data/interim/`, and records a checksum/provenance
manifest under `data/manifests/`. Use **Update matching dates and add new dates**
for regular refreshes; **Replace this series history** changes the active
history while keeping older raw uploads for audit. The upload limit is 20 MB.
Monthly series require at most one observation per month. Do not combine
incompatible index bases.

The endpoints are `GET /data/requirements` and
`POST /data/upload/{series_id}?mode=upsert|replace`. The browser sends the file
as a raw request body with an `X-Filename` header, so the backend needs no
additional multipart package.

After a data refresh, rebuild the research tables from the project root:

```powershell
python -m scripts.build_macro_monthly
python -m scripts.build_cpi_features
```

`data/demo/synthetic_repo_rate_preview.csv` is reproducible simulated sample
data for UI demonstration only. It is never read as `repo_rate`, included in
forecast readiness, or represented as RBI data. Import the official RBI DBIE
export through the Data Explorer when you have it.
