# VOC Collaboration Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add collaboration workflow, auditing, notifications, exports, and deployable external/internal environment profiles to the existing VOC archive and BM25 app.

**Architecture:** Keep `voc_cases` as the historic archive/search source. Add a collaboration schema keyed by Case ID and request round. FastAPI remains the single API boundary; Next.js consumes typed JSON APIs. Runtime configuration selects Supabase external review or local PostgreSQL internal operation.

**Tech Stack:** Next.js App Router, TypeScript, FastAPI, Pydantic, psycopg 3, PostgreSQL/Supabase PostgreSQL, pytest, Vitest, Playwright.

**Spec:** `docs/superpowers/specs/2026-08-18-voc-collaboration-platform-design.md`

## Global Constraints

- Preserve current BM25 search and `closed`-only Top 3 behavior.
- Never commit passwords, database URLs, SMTP settings, deployment tokens, or translation model files.
- External review profile stores notification previews only; internal profile alone can deliver mail or run local translation.
- Public reads do not require a password. Every write, management action, and export requires writer name and shared password.
- Use parameterized SQL, transactions, and immutable audit rows for every write.
- Do not implement user accounts, ECM file upload, Sentence Transformer runtime, or live ECM integration.

---

### Task 1: Profile Settings, Writer Gate, and Schema

**Files:**
- Create: `backend/migrations/002_collaboration.sql`, `backend/app/auth.py`, `backend/tests/test_auth.py`
- Modify: `backend/app/config.py`, `backend/app/db.py`, `backend/app/main.py`, `.env.example`, `backend/tests/test_config.py`

**Interfaces:** `Settings.runtime_profile`, `require_writer() -> WriterContext`, `change_audits`, `writer_attempts`, `voc_requests`, `department_tasks`, `task_reviews`, `voc_stage_history`, `notification_logs`, and `master_*` tables.

- [ ] Write failing tests:

```python
def test_external_profile_disables_real_mail(monkeypatch):
    monkeypatch.setenv("VOC_RUNTIME_PROFILE", "external_review")
    assert Settings().mail_delivery_enabled is False

def test_five_invalid_passwords_lock_writer_for_fifteen_minutes(client):
    for _ in range(5):
        assert client.post("/api/writer/verify", json={"writer_name": "Kim", "password": "wrong"}).status_code == 401
    assert client.post("/api/writer/verify", json={"writer_name": "Kim", "password": "wrong"}).status_code == 429
```

- [ ] Run `cd backend; uv run pytest tests/test_auth.py tests/test_config.py -v` and confirm RED.
- [ ] Implement environment profile validation, `VOC_WRITER_PASSWORD_HASH`, SHA-256 plus `hmac.compare_digest`, and five failures within 15 minutes per writer/client IP. Protected requests carry `X-Writer-Name` and `X-Writer-Password`; returned context never exposes the password.
- [ ] Add idempotent migration tables and constraints, then run `psql "$VOC_DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/002_collaboration.sql`.
- [ ] Run the task test command again and confirm GREEN.
- [ ] Commit: `git add backend .env.example && git commit -m "feat: add collaboration environment and writer gate"`.

### Task 2: VOC Rounds, Department Tasks, Approvals, and Audit API

**Files:**
- Create: `backend/app/repositories/collaboration.py`, `backend/app/services/workflow.py`, `backend/app/services/mail_parser.py`, `backend/app/routers/collaboration.py`, `backend/tests/test_workflow.py`, `backend/tests/test_collaboration_api.py`
- Modify: `backend/app/schemas.py`, `backend/app/main.py`

**Interfaces:** `POST /api/voc`, `POST /api/voc/{case_id}/rounds`, `POST /api/tasks/{task_id}`, `POST /api/tasks/{task_id}/review`, `POST /api/voc/{case_id}/stage`, `GET /api/voc/{case_id}`.

- [ ] Write failing tests:

```python
def test_follow_up_creates_second_round_and_reopens_prior_tasks(client, writer_headers):
    case_id = create_voc(client, writer_headers)
    complete_task(client, case_id, writer_headers)
    reply = client.post(f"/api/voc/{case_id}/rounds", headers=writer_headers, json={"customer_request": "additional question"})
    assert reply.status_code == 201
    assert reply.json()["round_number"] == 2
    assert reply.json()["tasks"][0]["status"] == "not_started"

def test_customer_reply_requires_all_approvals(client, writer_headers):
    assert client.post("/api/voc/VOC-2026-0001/stage", headers=writer_headers, json={"stage": "customer_reply"}).status_code == 409
```

- [ ] Run `cd backend; uv run pytest tests/test_workflow.py tests/test_collaboration_api.py -v` and confirm RED.
- [ ] Implement Case ID `VOC-YYYY-NNNN`, sender/email/company-only parser, request rounds, task states (`not_started`, `reviewing`, `in_progress`, `completed`, `delayed`, `excluded`), department-manager review, fixed final approval, reverse stage transitions, cancellation/deletion reason, and audit insert in the same transaction.
- [ ] Reject customer reply until active tasks and approvals are complete; if due date is past, set active task to `delayed` and require delay reason before completion.
- [ ] Run `cd backend; uv run pytest tests/test_workflow.py tests/test_collaboration_api.py tests/test_archive_api.py tests/test_requests_api.py -v` and confirm GREEN.
- [ ] Commit: `git add backend/app backend/tests && git commit -m "feat: add VOC collaboration workflow"`.

### Task 3: Dashboard, Alerts, Translation Boundary, and Export APIs

**Files:**
- Create: `backend/app/services/notifications.py`, `backend/app/services/translation.py`, `backend/app/routers/dashboard.py`, `backend/app/routers/export.py`, `backend/app/routers/admin.py`, `backend/tests/test_dashboard_api.py`, `backend/tests/test_notifications.py`, `backend/tests/test_export_api.py`
- Modify: `backend/app/repositories/collaboration.py`, `backend/app/main.py`, `backend/app/schemas.py`

**Interfaces:** `GET /api/dashboard`, `GET /api/notifications`, `POST /api/translate`, `GET /api/export/archive.csv`, `GET /api/export/archive.xlsx`, protected master-data APIs.

- [ ] Write failing tests:

```python
def test_external_profile_records_mail_preview_without_smtp(notification_service):
    notification_service.queue(high_priority_task())
    assert notification_service.sent_messages == []
    assert notification_service.preview_count == 1

def test_export_requires_writer_headers(client):
    assert client.get("/api/export/archive.csv").status_code == 401
```

- [ ] Run `cd backend; uv run pytest tests/test_dashboard_api.py tests/test_notifications.py tests/test_export_api.py -v` and confirm RED.
- [ ] Implement the priority recipients and schedules: high priority assignment/imminent daily to task owner, department manager, final approver; normal D-2/D-1/overdue daily to owner and department manager; re-opened tasks trigger an immediate alert. Default weekday 09:00 Asia/Seoul.
- [ ] In external profile, insert notification preview only. In internal profile, send only when SMTP configuration exists; otherwise record pending/failed delivery. Korean input bypasses translation; external review never executes a local model.
- [ ] Build CSV with `csv.DictWriter`; use an already-installed XLSX library only. Export endpoints must require writer verification.
- [ ] Run the task test command and confirm GREEN. Commit: `git add backend/app backend/tests && git commit -m "feat: add dashboards notifications and exports"`.

### Task 4: Writer-Gated New Request and VOC Management UI

**Files:**
- Create: `frontend/src/components/WriterGate.tsx`, `frontend/src/components/VocTimeline.tsx`, `frontend/src/components/DepartmentTaskBoard.tsx`, `frontend/src/components/ApprovalPanel.tsx`, `frontend/src/app/voc/[caseId]/page.tsx`
- Modify: `frontend/src/lib/types.ts`, `frontend/src/lib/api.ts`, `frontend/src/components/AppShell.tsx`, `frontend/src/app/requests/new/page.tsx`
- Test: `frontend/src/components/WriterGate.test.tsx`, `frontend/src/app/voc/[caseId]/page.test.tsx`, `frontend/src/app/requests/new/new-request.test.tsx`

**Interfaces:** UI uses the protected API headers only in memory; provides server drafts, request-round timeline, tasks, reviews, and stage actions.

- [ ] Write failing tests:

```tsx
it("requires writer verification before saving a draft", async () => {
  render(<NewRequestPage />);
  await user.click(screen.getByRole("button", { name: "임시 저장" }));
  expect(await screen.findByLabelText("작성자명")).toBeVisible();
});

it("shows task status separately from the overall VOC stage", async () => {
  render(<VocDetailPage params={{ caseId: "VOC-2026-0001" }} />);
  expect(await screen.findByText("전체 단계: 대응 중")).toBeVisible();
  expect(screen.getByText("정비부서 · 조치 중")).toBeVisible();
});
```

- [ ] Run `cd frontend; npm test -- WriterGate.test.tsx page.test.tsx new-request.test.tsx` and confirm RED.
- [ ] Reuse the CI Blue shell. Keep credentials only in component memory. Implement sequential mail paste, extracted-field confirmation, server draft, Top 3, task assignment, request rounds, approval/rejection, Korean reply draft, ECM links, and audit history.
- [ ] Run the task test command and confirm GREEN. Commit: `git add frontend/src && git commit -m "feat: build protected VOC collaboration screens"`.

### Task 5: Dashboard, Notifications, Archive Export, and Management Tool UI

**Files:**
- Create: `frontend/src/components/DashboardPanels.tsx`, `frontend/src/app/notifications/page.tsx`, `frontend/src/app/admin/page.tsx`
- Modify: `frontend/src/app/page.tsx`, `frontend/src/app/archive/page.tsx`, `frontend/src/lib/api.ts`, `frontend/src/lib/types.ts`
- Test: `frontend/src/app/page.test.tsx`, `frontend/src/app/archive/archive.test.tsx`, `frontend/src/app/admin/page.test.tsx`

**Interfaces:** dashboard consumes public data; exports and settings require `WriterGate`.

- [ ] Write failing test:

```tsx
it("shows the three equal-weight dashboard panels", async () => {
  render(<DashboardPage />);
  expect(await screen.findByRole("heading", { name: "단계별 VOC 현황" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "마감 임박/지연 부서 과제" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "최근 고객 요청" })).toBeVisible();
});
```

- [ ] Run `cd frontend; npm test -- page.test.tsx archive.test.tsx admin/page.test.tsx` and confirm RED.
- [ ] Implement recent-30-day default with week, month, and custom date filters. Add notification preview/log screens; writer-gated export buttons; and management forms for customers, products, type/subtype, people, fixed final approver, templates, and weekday notification time.
- [ ] Run the task test command and confirm GREEN. Commit: `git add frontend/src && git commit -m "feat: add VOC dashboard tools and exports"`.

### Task 6: Deployable Profiles, QA, and Runbook

**Files:**
- Create: `frontend/e2e/collaboration.spec.ts`, `backend/tests/test_profile_smoke.py`
- Modify: `README.md`, `.env.example`, `frontend/next.config.ts`

**Interfaces:** documents external Vercel/Supabase/FastAPI settings and separate internal PostgreSQL/SMTP/local-translation settings.

- [ ] Write failing e2e test:

```ts
test("writer can save a draft and inspect notification preview", async ({ page }) => {
  await page.goto("/requests/new");
  await page.getByLabel("작성자명").fill("검증자");
  await page.getByLabel("공용 비밀번호").fill("test-password");
  await page.getByRole("button", { name: "임시 저장" }).click();
  await expect(page.getByText("임시 저장됨")).toBeVisible();
});
```

- [ ] Run `cd frontend; npx playwright test e2e/collaboration.spec.ts` and confirm RED.
- [ ] Document `VOC_RUNTIME_PROFILE=external_review`, Supabase URL, `NEXT_PUBLIC_API_BASE_URL`, Vercel variables, internal PostgreSQL/SMTP/local-model variables, and a manual check that external review never dispatches email.
- [ ] Run `cd backend; uv run pytest -v` and `cd frontend; npm test; npm run build; npx playwright test`. Run live DB smoke checks only after user supplies credentials.
- [ ] Commit: `git add README.md .env.example backend/tests frontend/e2e frontend/next.config.ts && git commit -m "test: document and verify collaboration deployment"`.

## Plan Self-Review

- Tasks 1–2 cover access, audit, collaboration states, approvals, cancellation and request rounds.
- Task 3 covers dashboard data, alert rules, translation boundary, master data and protected exports.
- Tasks 4–5 cover every agreed screen and preserve public read/private mutation behavior.
- Task 6 covers verification, Vercel external review deployment and separate internal configuration.
