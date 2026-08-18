# VOC Collaboration Platform

FastAPI and Next.js provide a searchable VOC archive plus writer-gated collaboration, audit, notification-preview, and export workflows. The same codebase supports two deliberately separate runtime profiles:

- `external_review`: hosted review with Supabase PostgreSQL. Notifications are preview records only, and local translation never runs.
- `internal`: internal PostgreSQL with optional SMTP delivery and an optional local CPU translation command.

Never commit a database URL, writer password/hash, SMTP credential, deployment token, or model file. `.env.example` is a variable inventory, not a credential store.

## Prerequisites

- Python 3.11 or newer and [uv](https://docs.astral.sh/uv/)
- Node.js 20 or newer and npm
- PostgreSQL or Supabase PostgreSQL
- Chromium installed with `npx playwright install chromium` for browser QA

Install dependencies from the repository root:

```powershell
cd backend
uv sync
cd ..\frontend
npm install
npx playwright install chromium
cd ..
```

## Writer password hash

Protected writes use a shared password, but the backend accepts only its lowercase SHA-256 hash. Generate the hash locally and place only the result in the backend secret store as `VOC_WRITER_PASSWORD_HASH`:

```powershell
$secureWriterPassword = Read-Host "Shared writer password" -AsSecureString
$plainWriterPassword = [System.Net.NetworkCredential]::new("", $secureWriterPassword).Password
$writerHash = [Convert]::ToHexString(
  [Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($plainWriterPassword))
).ToLowerInvariant()
$writerHash
Remove-Variable plainWriterPassword, secureWriterPassword
```

Do not place the plaintext password in an environment file or deployment setting.

## External review: Vercel, Supabase, and FastAPI

External review needs three separately configured services. It is safe-by-default only when `VOC_RUNTIME_PROFILE` is exactly `external_review`.

### 1. Supabase PostgreSQL

Create a Supabase project, copy its PostgreSQL connection string into the FastAPI secret `VOC_DATABASE_URL`, and apply the migrations in order from a trusted terminal:

```powershell
psql "$env:VOC_DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/migrations/000_bootstrap_voc_cases.sql
psql "$env:VOC_DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/migrations/001_local_search.sql
psql "$env:VOC_DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/migrations/002_collaboration.sql
```

Preserve existing archive rows. Do not run a destructive reset or seed over review data.

### 2. Public FastAPI service

Configure these variables on the FastAPI host, not in Vercel:

```text
VOC_RUNTIME_PROFILE=external_review
VOC_DATABASE_URL=<Supabase PostgreSQL URL>
VOC_WRITER_PASSWORD_HASH=<64-character SHA-256 hash>
```

Leave every `VOC_SMTP_*`, `VOC_TRANSLATION_COMMAND`, and `VOC_TRANSLATION_MODEL_PATH` variable unset. Start the service with:

```powershell
cd backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Terminate TLS at the hosting platform and record the resulting HTTPS origin, for example `https://voc-api.example.com`.

### 3. Vercel frontend

Create a Vercel project with `frontend` as its root directory and the Next.js framework preset. Configure:

```text
VOC_API_BASE_URL=https://voc-api.example.com
NEXT_PUBLIC_API_BASE_URL=
```

`VOC_API_BASE_URL` is read by the Next.js server rewrite. Keep `NEXT_PUBLIC_API_BASE_URL` empty so browser requests remain same-origin under `/api`; setting it to a different origin requires a separately reviewed FastAPI CORS policy. Do not put `VOC_DATABASE_URL` or the writer hash in Vercel.

The production build is:

```powershell
cd frontend
npm run build
```

The generated standalone output also supports an internal Node deployment; Vercel handles it automatically.

### External-review no-mail check

Before sharing the review URL:

1. Confirm the FastAPI environment reports `VOC_RUNTIME_PROFILE=external_review` and has no `VOC_SMTP_*` values.
2. Create a high-priority test draft and assign a department task.
3. Open **Notifications** and confirm the generated record is shown as a preview.
4. Query the latest `notification_logs` row and confirm `runtime_profile = 'external_review'`, `delivery_status = 'preview'`, and `real_delivery = false`.
5. Confirm no message arrived at the test recipient.

If any row reports `real_delivery = true`, stop the review and investigate the backend profile before continuing.

## Internal profile

Configure the backend on the internal network:

```text
VOC_RUNTIME_PROFILE=internal
VOC_DATABASE_URL=postgresql://<user>:<password>@<internal-host>/<database>
VOC_WRITER_PASSWORD_HASH=<64-character SHA-256 hash>
VOC_SMTP_HOST=<internal SMTP host>
VOC_SMTP_PORT=25
VOC_SMTP_USERNAME=<optional username>
VOC_SMTP_PASSWORD=<optional password>
VOC_SMTP_FROM=<sender address>
VOC_TRANSLATION_COMMAND=<local executable>
VOC_TRANSLATION_MODEL_PATH=<local model directory>
```

SMTP delivery activates only when both `VOC_SMTP_HOST` and `VOC_SMTP_FROM` are present. Without them, notifications remain pending. The local translation command receives `--model <VOC_TRANSLATION_MODEL_PATH>`, reads source text from standard input, and must write the translation to standard output. Model files stay on the internal host and outside the repository.

Run the internal Next.js service with `VOC_API_BASE_URL` pointing to the internal FastAPI origin and keep `NEXT_PUBLIC_API_BASE_URL` empty. Apply all three migrations before starting either service.

## Local development

For the approved local training database, set `VOC_DB_PASSWORD` in the current shell. The remaining legacy connection values default to PostgreSQL on localhost and database `학습용 Data`:

```powershell
$secureDatabasePassword = Read-Host "PostgreSQL password" -AsSecureString
$env:VOC_DB_PASSWORD = [System.Net.NetworkCredential]::new("", $secureDatabasePassword).Password
cd backend
uv run python -m app.bootstrap_local_training_db
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm run dev
```

Open `http://localhost:3000`. Next.js proxies same-origin `/api/*` requests to `VOC_API_BASE_URL`, which defaults to `http://127.0.0.1:8000`.

## Verification runbook

The credential-free suite uses in-memory repositories and mocked browser APIs:

```powershell
cd backend
uv run pytest -m "not localdb" -v
cd ..\frontend
npm test
npm run build
npx playwright test
```

The collaboration Playwright test mocks writer verification, draft creation, archive search, and notification previews. It does not contact Supabase, submit a real draft, or dispatch mail.

Run live database smoke checks only after an operator supplies credentials intentionally:

```powershell
cd backend
uv run pytest -v
```

For browser QA, verify the dashboard date filters, archive search and export gate, writer-gated draft flow, VOC round/task/approval views, notification previews, and management forms. In external review, repeat the no-mail check above after any profile or hosting change.
