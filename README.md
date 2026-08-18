# Local VOC Archive

This application serves the local PostgreSQL training archive through FastAPI and a Next.js browser UI. Runtime settings accept only `학습용 Data`; keep the PostgreSQL password in the shell environment and never commit it.

## Prerequisites

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/)
- Node.js 20 or newer and npm
- PostgreSQL running locally with the training database available

`.env.example` is a reference file, not a credential store. In PowerShell, set the password for the current shell before running backend commands:

```powershell
$securePassword = Read-Host "PostgreSQL password" -AsSecureString
$env:VOC_DB_PASSWORD = [System.Net.NetworkCredential]::new("", $securePassword).Password
```

The remaining database settings have local defaults. Override them in the shell only when needed; `VOC_DB_NAME` must remain `학습용 Data`.

## 1. Create the Python environment

```powershell
cd backend
uv sync
cd ..
```

## 2. Apply the training-database migrations

With `VOC_DB_PASSWORD` set, run the guarded bootstrap from the repository root:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.bootstrap_local_training_db
cd ..
```

The bootstrap resolves the exact training database, applies `000_bootstrap_voc_cases.sql` and `001_local_search.sql`, and verifies the expected 135 historical rows. On an empty database it imports the approved historical training dataset; it refuses partial or unexpected data.

## 3. Install the frontend dependencies

```powershell
cd frontend
npm install
npx playwright install chromium
cd ..
```

## 4. Start FastAPI

In a PowerShell terminal where `VOC_DB_PASSWORD` is set:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

FastAPI is available at `http://127.0.0.1:8000`. Keep this terminal running.

## 5. Start Next.js

In another terminal:

```powershell
cd frontend
npm run dev
```

Open `http://localhost:3000/archive`. Next.js proxies `/api/*` to `VOC_API_BASE_URL`, which defaults to `http://127.0.0.1:8000`.

## 6. Run the tests

The full backend suite includes read-only checks against the local training database and therefore requires `VOC_DB_PASSWORD`:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -v
cd ..\frontend
npm test
npm run build
npx playwright test e2e/local-voc.spec.ts
```

When database credentials are intentionally unavailable, the safe backend-only subset is:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -m "not localdb" -v
```

The Playwright test uses deterministic mocked GET responses and rejects write requests. The local-database smoke test only calls `GET /api/archive`; automated QA does not submit the manual request form. The first real manual submission is reserved for the user.

## Browser QA checklist

Without submitting the manual request form, verify:

- desktop and narrow archive layouts
- archive filters and reset behavior
- relevance sorting with a keyword and latest sorting without one
- result preview, close behavior, and restored filter state
- the empty state of the manual request form

Capture a screenshot before changing any visual defect found during QA.
