# Security architecture and current review

This document describes the controls present in the repository and the work still required before exposing it to untrusted users. It is a research prototype, not a production security certification.

## Architecture observed

- **Frontend:** Next.js 15 / React 19, with UI components and API clients under `frontend/`.
- **Backend:** FastAPI routers in `app/api/`; configuration is loaded by `app/core/config.py`.
- **Data:** uploaded originals, normalized observations, manifests, and research run JSON are stored under `data/`.
- **AI:** the contextual assistant calls a configured NVIDIA-compatible endpoint; agent classes and a LangGraph workflow also exist. The current research API uses deterministic tools and does not expose the graph as an API.
- **Authentication/database:** no user authentication, authorization, or database-backed tenancy was found in the inspected application. Filesystem JSON is used for persistence.
- **External requests:** source adapters use configured provider integrations. The browser does not choose arbitrary server-side fetch URLs.

## Changes in this review

- Added API response headers (`nosniff`, frame denial, restrictive API CSP, referrer/permissions policy, and no-store).
- Sanitized request validation errors so rejected values are not echoed to the caller.
- Disabled credentialed CORS because the current API has no cookie authentication. CORS remains an origin allowlist, configured with `CORS_ALLOWED_ORIGINS`.
- Hardened dataset uploads with filename/extension checks, content signature checks for Excel, compressed workbook expansion and compression-ratio limits, row/column limits, and generic parser errors that do not reveal local parser details.
- Removed provider exception text from assistant error logs and made generic provider failures safe for clients.
- No files were deleted and no source dataset was modified as part of this review.

## Threat model and current status

| Threat | Attack surface | Current prevention | Detection / response | Remaining work |
|---|---|---|---|---|
| Unauthenticated access / privilege abuse | All API routes, especially `/data/upload`, `/research`, and `/assistant/chat` | CORS is restricted, but CORS is not authentication | No identity-aware audit trail | **Release blocker for public deployment:** add identity, server-side authorization, roles, and ownership checks without placing secrets in browser code |
| Malicious or oversized upload | `/data/upload/{series_id}` CSV/XLSX/XLSM | 20 MB request cap, allowed extensions, parser limits, Excel zip expansion checks, numeric/date/range validation | Parser failures are logged by exception class; upload manifest records source hash | Authentication, per-user quotas, parser isolation/AV scanning, robust multipart/proxy limits, and concurrency-safe writes |
| Path traversal | `X-Filename` upload header | Basename normalization and server-generated storage name | Invalid extension/name rejected | Add dedicated cross-platform path tests and upload storage outside the web root in deployment |
| Cross-site scripting / clickjacking | API responses and React-rendered content | API CSP/frame denial; React escapes text by default | No CSP report collection | Configure corresponding CSP and headers at the Next.js host/CDN; audit any future raw HTML rendering |
| CSRF / credential abuse | Browser-to-API calls | No cookie authentication; credentialed CORS disabled | None | If cookie sessions are added, require CSRF tokens and origin checks |
| API abuse / denial of service | Assistant, upload, backtest, research endpoints | Input schemas, upload byte/row/column limits, provider concurrency configuration | Basic application logs | Add distributed rate limiting, timeouts, request-body limits at the reverse proxy, quotas, and alerting |
| Prompt injection / manipulated model output | Assistant messages and page context; future agent tools | Bounded Pydantic request fields; assistant is not given executable tool access in the current API route | No security-specific prompt-injection monitoring | Treat retrieved/uploaded text as untrusted evidence; enforce tool allowlists and deterministic result validation before any tool-enabled agent rollout |
| Secret leakage | `.env`, provider calls, logs, frontend | Environment-based configuration; `.env` is gitignored; frontend only uses public API base URL | No automated secret scanner confirmed | Rotate any exposed keys; add secret scanning in CI and central secret management |
| SSRF | Provider base URL and source adapters | No endpoint accepts a user URL for server-side retrieval; provider URL is deployment configuration | Provider failures logged | Validate configured provider hosts in deployment and prevent private-network targets unless explicitly approved |
| Data poisoning / model misuse | Manual uploads and forecast/scenario inputs | Series allowlist, value ranges, duplicate/frequency checks, source manifests; forecasts are labeled research outputs | Checksums/manifests and rolling metrics | Require authorization/review for replace mode; maintain data vintages; independently verify sources and forecast performance |
| Sensitive research run exposure | UUID-addressed run/report endpoints and local JSON | UUID format validation; generated IDs are not sequential | No access audit | UUIDs are not authorization. Add owner-scoped access controls and retention policy before multi-user hosting |
| Supply-chain / container compromise | Python/npm dependencies and Docker | Lockfiles/constraints exist in the project | No vulnerability scan verified in this review | Pin and scan dependencies, build minimal non-root containers, add SBOM and image scanning |

## Deployment requirements before public use

1. Put the API behind HTTPS and a reverse proxy that enforces body-size, connection, and request-time limits. Set explicit production frontend origins.
2. Implement authentication and server-side authorization for uploads, replacement, research creation, assistant usage, and run/report retrieval. Do not treat CORS or UUIDs as access control.
3. Add distributed rate limits and quotas for expensive or persistent operations; in-process limits alone would not protect a multi-worker deployment.
4. Store uploaded files outside the static web root, scan/isolate parsers, make writes atomic, and protect replacement with an authorized confirmation workflow.
5. Configure secrets through a secret manager or protected environment, rotate credentials on exposure, and run secret/dependency scanning in CI.
6. Keep deterministic economics tools as the source of numeric results. The LLM may explain validated results, but must not invent observations or make unvalidated tool calls.
7. Add monitoring, correlation IDs, audit events, backup/restore procedures, retention rules, and an incident response owner.

## Verification scope

The code changes in this review are limited to API security headers/CORS, upload parsing bounds, and safe provider errors. Tests and application builds should be run before deployment. This review does not establish that the whole application is secure, and does not implement authentication, RBAC, distributed rate limiting, malware scanning, or an independent penetration test.
