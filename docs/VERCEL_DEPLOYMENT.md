# GitHub and Vercel deployment

This repository contains three deployable services:

- `api/` is the Vercel Python entrypoint for the FastAPI backend.
- `frontend/` is the public Next.js research UI.
- `admin-frontend/` is the Next.js admin UI.

Create three Vercel projects from the same GitHub repository. Do not deploy
the repository root as a Next.js project.

## 1. Prepare the repository

From the project directory:

```powershell
git init
git add .
git status
git commit -m "Prepare project for GitHub and Vercel deployment"
```

Review `git status` before committing. Never add `.env`, API keys, password
hashes, local uploads, Chroma data, generated manifests, or large archives.
The repository `.gitignore` and `.vercelignore` exclude these by default.

Create an empty GitHub repository, then replace the placeholder remote values:

```powershell
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

## 2. Deploy the API

In Vercel, choose **Add New Project**, import the GitHub repository, and use:

- Root Directory: `.`
- Framework Preset: `Other`
- Build Command: leave empty
- Output Directory: leave empty
- Install Command: `pip install -r requirements.txt`

The root `vercel.json` routes every request to `api/index.py`. The API health
endpoint will be:

```text
https://YOUR-API-PROJECT.vercel.app/health
```

Add these Vercel environment variables for **Production**, **Preview**, and
**Development** as appropriate:

```text
ENVIRONMENT=production
JWT_SECRET_KEY=<random secret of at least 32 characters>
ADMIN_EMAIL=<admin email>
ADMIN_PASSWORD=<argon2id password hash>
ADMIN_ROLE=ADMIN
NVIDIA_API_KEY=<provider key if assistant chat is enabled>
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=<provider model id>
EIA_API_KEY=<optional>
FRED_API_KEY=<optional>
EMBEDDING_PROVIDER=local
CORS_ALLOWED_ORIGINS=["https://YOUR-FRONTEND-PROJECT.vercel.app","https://YOUR-ADMIN-PROJECT.vercel.app"]
```

For the current production aliases, include
`https://artha-ai-beta.vercel.app`, `https://artha-ai-frontend.vercel.app`, and
`https://artha-ai-admin.vercel.app` in this JSON array. Keep the localhost
origins if local frontend development should continue to call the deployed API.
Redeploy the API after changing this setting.

Generate an Argon2id password hash locally; never put the plaintext password
in GitHub:

```powershell
python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['argon2']).hash('REPLACE_WITH_A_LONG_PASSWORD'))"
```

Generate a JWT secret with a password manager or a cryptographically secure
local generator. Do not use the example placeholder.

## 3. Deploy the public frontend

Create a second Vercel project from the same repository:

- Root Directory: `frontend`
- Framework Preset: `Next.js`
- Build Command: `npm run build`
- Install Command: `npm ci`
- Output Directory: leave the default

Set:

```text
NEXT_PUBLIC_API_BASE_URL=https://YOUR-API-PROJECT.vercel.app
```

Deploy and test the application. Then update the API project's
`CORS_ALLOWED_ORIGINS` with the final public frontend URL and redeploy the API.

## 4. Deploy the admin frontend

Create a third Vercel project from the same repository:

- Root Directory: `admin-frontend`
- Framework Preset: `Next.js`
- Build Command: `npm run build`
- Install Command: `npm ci`
- Output Directory: leave the default

Set:

```text
BACKEND_INTERNAL_URL=https://YOUR-API-PROJECT.vercel.app
NEXT_PUBLIC_API_BASE_URL=https://YOUR-API-PROJECT.vercel.app
```

`BACKEND_INTERNAL_URL` is used by the Next.js server-side rewrite and is not
exposed to browser code. After the admin deployment URL is known, add it to
the API project's `CORS_ALLOWED_ORIGINS` and redeploy the API.

## 5. Verify the deployment

Check these URLs:

```text
https://YOUR-API-PROJECT.vercel.app/health
https://YOUR-FRONTEND-PROJECT.vercel.app
https://YOUR-ADMIN-PROJECT.vercel.app
```

For the admin UI, verify login with the configured `ADMIN_EMAIL` and Argon2id
`ADMIN_PASSWORD`. Verify that the browser network requests do not show CORS
errors and that the admin API calls use the deployed API URL.

## Important free-tier limitations

Vercel functions have ephemeral local storage. Research runs, uploaded
evidence, Chroma indexes, and generated manifests written by the API are not
durable across deployments or function instances. The free deployment is
suitable for the deterministic demo and packaged read-only artifacts, but
durable multi-user research requires an external database/object store/vector
database.

The Vercel Python function also has execution-time and package-size limits.
Do not enable local Sentence Transformers or large training workflows in the
serverless API. Keep `EMBEDDING_PROVIDER=local` and use the lightweight
provider, or move evidence indexing to a persistent worker later.

Do not treat the free Vercel deployment as a production public research
service until authentication, persistent storage, abuse controls, and an
external rate limiter are in place.
