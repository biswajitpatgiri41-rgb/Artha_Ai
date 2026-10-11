# Advanced Upgrade Audit and Implementation Plan

## Purpose and guardrails

This document records the repository state before any roadmap implementation. It is an audit and plan only. No existing functionality, source adapters, agents, API contracts, frontend pages, theme, training workflow, or model artifacts should be removed or overwritten during later work. Proposed changes should be additive and backward compatible.

The repository contains code, data snapshots, packaged model artifacts, and a frontend architecture visualization. A box in the visualization is not treated as proof that the corresponding runtime path is implemented.

## Status definitions

- **IMPLEMENTED** — usable implementation is present in the current project/runtime.
- **PARTIALLY IMPLEMENTED** — a working portion exists, but the roadmap capability is incomplete, prototype-only, or not connected end to end.
- **NOT IMPLEMENTED** — no substantive implementation was found.
- **BLOCKED BY MODEL ARTIFACT** — implementation depends on a compatible trained/validated artifact or model-specific evaluation output that is not present or not available to the runtime.
- **BLOCKED BY DATA** — the required verified, sufficiently long, or appropriately versioned input data is unavailable.

## Repository areas inspected

Reviewed the project README and security review; FastAPI route registration and research/evidence routes; the agent modules and their runtime call sites; source adapter and data-building areas; evidence parsers, retrieval, vector storage, and lifecycle service; frontend routes, sidebar, architecture model, and evidence workspace; requirements/configuration; processed/raw/interim data layout; and both packaged CPI model directories and their manifests/results. Raw provider snapshots and individual model files were inventoried by directory and package manifests, not manually revalidated against their upstream publishers.

## Current-state classification

| Roadmap feature | Status | What exists now | Gap / constraint |
|---|---|---|---|
| Data ingestion and source adapters | **PARTIALLY IMPLEMENTED** | Provider modules and downloader/import scripts exist for EIA, FRED, World Bank, MoSPI, RBI DBIE import, IMF/OECD, and market data. Normalized observations, raw snapshots, and manifests are organized under `data/`. CSV/XLSX series upload/update endpoints exist. | Provider/source coverage is uneven; some sources are manual or not verified/mapped for the intended series. Existing imported MoSPI CPI history is short and IIP is absent. Adapters should be extended additively; do not rewrite working adapters. |
| Canonical data, feature engineering, and provenance | **PARTIALLY IMPLEMENTED** | Series registry and observation schemas, feature/table build scripts, raw/interim/processed layouts, checksums and source manifests exist. Data routes report local availability. | Full release/retrieval vintage handling is not consistently integrated into the model-serving path. Availability and provenance coverage varies by series/source. |
| Forecasting runtime | **PARTIALLY IMPLEMENTED** | Seasonal-naive benchmark plus frozen CPI Ridge, XGBoost, ARIMA(1,0,0), and unweighted Ridge/XGBoost ensemble are served via `/forecast`. Direct packaged horizons are 1, 3, and 6 months; benchmark supports other bounded horizons. | Packaged model forecasts use their frozen feature panel and do not rebuild predictors from current uploaded observations. This is a research snapshot, not a live retraining pipeline. The complete proposed model menu is not served. |
| Proposed additional model families / deployable artifacts | **BLOCKED BY MODEL ARTIFACT** | `app/models/` contains two CPI artifact packages, model manifests, validation reports, and rolling-origin evaluation files. The active enriched inference adapter supports the families listed above. | No complete, registered, validated ETS/SARIMA/SARIMAX/VAR/XGBoost/ensemble production inventory with compatible runtime artifacts and evaluation metadata was found. Existing ARIMA support is not equivalent to a validated SARIMA/SARIMAX suite. Do not synthesize numerical outputs for missing artifacts. |
| Data sufficiency for refreshed model training and vintage-aware scoring | **BLOCKED BY DATA** | Frozen training panels provide historical data for the packaged research models. Local canonical data can be extended through source imports. | README records only 19 recent MoSPI headline CPI observations, 3 food observations, and no current IIP workbook in the local import set. Verified coverage and release vintages needed for a trustworthy refreshed monthly panel are incomplete. |
| Backtesting and evaluation | **PARTIALLY IMPLEMENTED** | `/backtest` computes expanding-window rolling-origin MAE, RMSE, and bias for the seasonal-naive runtime path. Packaged models expose recorded rolling-origin metrics and a 24-month test-period record. | The live endpoint does not backtest whichever packaged model is selected. A separate final holdout workflow, interval coverage metrics, and a promotion/registry lifecycle are not demonstrated as active runtime capabilities. |
| Final holdout and interval coverage | **BLOCKED BY MODEL ARTIFACT** | Some frozen package evaluation results and holdout summaries exist. | A supported interval-producing forecast artifact and compatible coverage evaluation are not integrated into the active forecast/evaluation API. Any future interval claims require appropriate artifacts and evaluation outputs. |
| Scenario simulation | **PARTIALLY IMPLEMENTED** | `/simulate` provides an explicit-input CPI sensitivity calculation for oil, FX, food, repo-rate, and horizon assumptions; the UI calls the API and labels a local fallback. | README describes coefficients as illustrative, not estimated or causal. A Monte Carlo engine, calibrated shock distributions, and a validated baseline-versus-shocked forecast pipeline are not implemented. |
| Monte Carlo / calibrated scenario outputs | **NOT IMPLEMENTED** | Scenario controls and deterministic sensitivity exist. | No simulation distribution engine or calibrated uncertainty layer was found. Calibration depends on adequate historical shock/response data and a defined validated model. |
| Policy scorecard | **PARTIALLY IMPLEMENTED** | Policy page and scorecard components render policy dimensions and alternatives. | Score inputs/content in `frontend/lib/mock-data.ts` are explicitly mock/illustrative; no production policy scoring API or verified empirical scoring method was found. |
| LangGraph agents and orchestration | **PARTIALLY IMPLEMENTED** | Planner, data, inflation, growth, external, econometrics, policy, critic, and report agent modules exist. NVIDIA-backed assistant configuration exists separately. | The research API explicitly records that agent orchestration is not connected; `POST /research` calls deterministic tools and the critic directly with empty specialist-agent outputs. No active LangGraph graph integration was found in the runtime route. Preserve all agent modules and existing assistant behavior when later wiring this. |
| FastAPI backend | **IMPLEMENTED** | App/router structure exposes data, forecast, backtest, scenario, research/report, assistant, and evidence endpoints. Research runs are persisted as JSON; response schemas and bounded request validation are present. | API event streaming is not live (`/research/{run_id}/stream` returns persisted events with `streaming: false`). Authentication/authorization and user identity are absent; UUID/run scoping is not production multi-tenant security. |
| Evidence uploads and format routing | **IMPLEMENTED** | `/evidence` supports run-scoped upload/list/metadata/delete/search/config/events. PDF, TXT/MD, CSV, XLSX, and JSON use format-specific parsing and schemas; upload limits, generated storage names, lifecycle/retention, parser warnings, and deletion cleanup exist. | Local run IDs do not authenticate a user. Saved evidence is local filesystem persistence rather than a multi-user knowledge base. Operational deployment still needs owner-scoped authorization and robust storage controls. |
| Document RAG and citations | **PARTIALLY IMPLEMENTED** | PDF/TXT/MD extraction, chunk metadata, configurable embedding interface, persistent vector-store abstraction, run-scoped search, relevance filtering, and citation fields are present. Structured CSV/XLSX/JSON paths use deterministic bounded operations rather than embedding entire tables. | Local embedding dependencies/model availability affect setup; structured search is bounded and query-term based, not a full natural-language query planner. Retrieval and storage are local-development infrastructure, not a tenant-secure production service. |
| Critic quantitative/evidence validation | **PARTIALLY IMPLEMENTED** | `run_critic` receives separate forecast/backtest/scenario inputs and `RetrievedEvidence`; research output preserves model and document evidence separately and emits critic events. Uploaded document text is treated as untrusted data in the evidence/assistant flow. | Research specialist-agent outputs are empty, so validation does not yet cover outputs from a connected full orchestration run. The research prototype critic does not establish forecast correctness from document evidence. |
| Report generation and citations | **PARTIALLY IMPLEMENTED** | Research records include observed data, model evidence, document evidence, critic output, warnings, and report fields; report agent module exists. | Runtime research report is assembled directly in the API route rather than produced through the report agent. Citations depend on returned retrieval metadata; broader report-agent workflow is not connected. |
| Frontend and existing routes | **PARTIALLY IMPLEMENTED** | Existing dark glassmorphism terminal routes cover dashboard, analysis, forecasts, data, simulator, policy, logs, reports, architecture, and evidence. API-backed areas coexist with explicitly labeled mock/demo areas. Sidebar includes Evidence Workspace. | Several dashboard/policy/analysis visualizations and source/status cards use static mock data. Forecast page separately labels mock chart content; API connectivity varies by page. Preserve current route behavior and theme during upgrades. |
| System Architecture visualization | **IMPLEMENTED** | Architecture is represented as a React Flow graph with categorized nodes/edges, event activity, evidence paths, operational status UI, and viewport pan/zoom. Node movement is not enabled in the current graph. | It visualizes target/runtime concepts and should not be read as evidence that the disconnected LangGraph or model-evaluation paths are complete. Keep its live evidence event flow and viewport behavior. |
| Evidence Workspace UI | **IMPLEMENTED** | `/evidence` provides upload progress, configured limits/privacy notice, file list/status, metadata, delete, search preview, lifecycle selection, and explicit selection for current-run use. | No authentication-backed user/session identity exists; selected run state is a local browser/session mechanism. |
| Model artifact provenance and integrity | **PARTIALLY IMPLEMENTED** | Both model packages include manifests, validation/evaluation reports, and the enriched package includes checksums. The active forecast response identifies frozen package mode and limitations. | Runtime registry/promotion and automated artifact compatibility checks across all candidate families are incomplete. Artifacts must remain immutable until a separately authorized training/release process creates new versioned outputs. |
| Authentication, authorization, and public multi-user deployment | **NOT IMPLEMENTED** | Security review documents origin allowlisting, input controls, and local run-scoped storage. | No identity or ownership enforcement exists. Do not describe current run UUID isolation as production tenant security; public deployment is blocked pending authorization and deployment controls. |

## Implementation plan (sequenced; no implementation performed here)

### Phase 0 — Preserve and baseline

1. Keep existing agents, source adapters, API routes/contracts, frontend routes/theme, assistant page-context behavior, Colab/training workflows, and artifacts intact.
2. Record baseline API schemas, route behavior, artifact checksums/manifests, and current frontend navigation before additive work.
3. Treat the architecture diagram as documentation of intended flows; only mark runtime wiring complete after tracing the actual call path.

### Phase 1 — Data readiness and provenance

1. Complete source verification and mappings for the needed CPI, food, IIP, policy-rate, external, and growth series, reusing current adapters/importers.
2. Increase official monthly target history and capture source/release/retrieval dates and revision/vintage identity before rebuilding any model panel.
3. Add explicit series readiness and provenance checks at feature-build and forecast boundaries. Missing or stale inputs should return clear unavailable/warning states, never substitute mock or invented observations.

**Gate:** data coverage and provenance are sufficient for the chosen target, frequency, forecast horizon, and evaluation design.

### Phase 2 — Forecast and evaluation registry

1. Document the currently supported benchmark and packaged-model options and their exact artifact/version/horizon constraints.
2. Add only model families for which versioned, compatible artifacts or a separately approved deterministic runtime implementation exist; preserve old model IDs and response contracts.
3. Connect selected-model rolling backtests, untouched final holdout reporting, bias/MAE/RMSE, and prediction-interval coverage where valid intervals are available.
4. Add registry metadata for artifact checksum, training-data vintage, feature schema, evaluation period, and status; never overwrite existing package artifacts.

**Gate:** every exposed numerical forecast maps to a real registered computation and carries enough provenance to reproduce its inputs/model version.

### Phase 3 — Scenario engine

1. Preserve the current illustrative simulator contract and label while adding any new versioned scenario method alongside it.
2. Specify baseline and shock input definitions, causal/association assumptions, model linkage, uncertainty calibration, and scenario provenance.
3. Implement Monte Carlo only after a validated response model and defensible shock distributions are available; report baseline, shocked outputs, and uncertainty separately.

**Gate:** scenario results are reproducible and clearly distinguished from observed data and model forecasts.

### Phase 4 — Agent orchestration and research records

1. Trace existing agent modules, prompts, configured NVIDIA provider, and any LangGraph dependency before connecting nodes; do not replace agents or change provider configuration.
2. Add an orchestration entry point that reuses deterministic tools and existing agent classes. Keep existing `/research` request/response shape working; introduce optional fields or a versioned path only when needed.
3. Pass bounded, typed model outputs, metrics, provenance, scenario assumptions, and selected run-scoped `RetrievedEvidence` into the existing critic/report roles.
4. Maintain separate quantitative and document-evidence checks. Uploaded documents may support narrative claims, never establish that a future forecast is correct.
5. Persist completed run/report/audit records safely and add live streaming only as a compatible additional capability.

**Gate:** deterministic computations remain the sole source of economic numerical outputs; no raw unbounded documents or hidden model reasoning enter reports/events.

### Phase 5 — Policy scorecard and frontend integration

1. Define a documented deterministic scorecard method and its data/model inputs before replacing any mock values. Keep demo labels when live data is unavailable.
2. Connect pages incrementally through existing API clients, retaining routes, controls, component behavior, and the dark glassmorphism theme.
3. Use explicit loading/unavailable states and preserve the existing Evidence Workspace run selection, assistant evidence toggle, and independent page context.
4. Keep the architecture event visualization and pan/zoom interaction; only show operational events emitted by actual completed/active backend work.

**Gate:** each live number or status has a traceable API/source, while mock/demo content remains visibly identified.

### Phase 6 — Security and deployment readiness

1. Add authentication and server-side ownership checks before claiming multi-user privacy; run IDs alone are not authorization.
2. Define retention, backup, quotas, parser isolation, request limits, and audit ownership for deployment storage.
3. Follow the remaining deployment blockers in `docs/security-review.md` before any public deployment.

## Explicit data and model blockers

- **Data:** current MoSPI imported history is too short for a refreshed monthly CPI model panel; IIP and verified RBI/IMD mappings/history are incomplete; release/vintage-aware predictor construction is not consistently connected to model inference.
- **Artifacts:** current runtime supports a constrained set of frozen CPI artifacts. New family/horizon/interval claims require compatible versioned artifacts and evaluation results. Current files should not be overwritten or silently retrained.
- **Security:** evidence/run scope is local-development isolation, not authenticated user/session isolation. Multi-user exposure requires identity-aware authorization.

## Audit outcome

This file is the only change made for this audit. No new feature was implemented, no existing file was deleted or modified, and no model/data artifact was changed. Tests and builds were not run because this task requested repository inspection and a plan only.
