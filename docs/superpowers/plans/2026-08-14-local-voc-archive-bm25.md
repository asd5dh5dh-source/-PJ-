# Local VOC Archive and BM25 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 로컬 PostgreSQL의 `학습용 Data.public.voc_cases` 135건만 사용해 아카이브 검색, 신규 요청 등록, BM25 Top 3가 동작하는 Next.js·FastAPI 웹 서비스를 구축한다.

**Architecture:** Next.js App Router 프론트엔드가 FastAPI JSON API를 호출하고, FastAPI는 psycopg를 통해 로컬 PostgreSQL에 접근한다. 아카이브의 일반 목록은 SQL 필터·정렬로 처리하고, 검색어가 있을 때만 메모리에 적재한 BM25 인덱스로 관련도를 계산한다. 신규 입력은 기존 `voc_cases`에 `record_origin='user_input'`으로 저장하며 Top 3 후보는 `final_status='closed'`인 사례로 제한한다.

**Tech Stack:** Next.js, TypeScript, FastAPI, Pydantic, psycopg 3, Python 표준 라이브러리 기반 BM25, pytest, Vitest, Playwright/gstack QA, PostgreSQL 18

## Global Constraints

- 연결 DB 이름은 정확히 `학습용 Data`만 허용한다.
- `테스트용 Data` DB와 `work/voc_test.csv`는 애플리케이션·테스트·QA에서 읽거나 연결하지 않는다.
- 초기 기준 데이터는 `public.voc_cases`의 학습용 135건이다.
- Sentence Transformer와 임베딩 열은 런타임 검색에 사용하지 않는다.
- 통합 검색 대상은 `customer_request + original_mail_body + full_response_history`이다.
- 아카이브는 모든 상태를 기본 표시하며 검색어가 없으면 최신 접수일 순이다.
- 검색어가 있으면 BM25 관련도 순이며 `BM25 × (1 + subtype_match × 0.1)`을 적용한다.
- Top 3 추천 후보는 `final_status='closed'`인 사례만 사용한다.
- 고객사가 달라도 VOC Subtype, 제품·설비, 요청 내용의 관련도가 높으면 상위에 배치한다.
- PostgreSQL 비밀번호는 Git에 저장하지 않고 `VOC_DB_PASSWORD` 환경변수로만 주입한다.
- 현재 폴더는 Git 저장소가 아니므로 Task 1에서 저장소를 초기화한 뒤 작업 단위별로 커밋한다.

---

## Planned File Structure

```text
backend/
  pyproject.toml                 # Python 의존성과 pytest 설정
  app/
    main.py                      # FastAPI 앱과 라우터 조립
    config.py                    # 학습용 DB 전용 환경 설정 검증
    db.py                        # psycopg 연결 컨텍스트
    schemas.py                   # API 입력·출력 모델
    repositories/voc_cases.py   # SQL 조회와 저장
    services/text.py             # 검색 텍스트 정제와 토큰화
    services/bm25.py             # BM25 인덱스와 Subtype 가점
    services/search.py           # DB 후보와 BM25 결과 조합
    routers/archive.py           # 아카이브 API
    routers/requests.py          # 신규 요청·Top 3 API
  migrations/001_local_search.sql
  tests/
    test_config.py
    test_text.py
    test_bm25.py
    test_archive_api.py
    test_requests_api.py
    test_local_training_db.py
frontend/
  package.json
  src/app/layout.tsx             # 공통 앱 레이아웃
  src/app/page.tsx               # 대시보드 시작 화면
  src/app/archive/page.tsx       # 아카이브 검색 화면
  src/app/requests/new/page.tsx  # 신규 요청·Top 3 화면
  src/components/AppShell.tsx
  src/components/ArchiveFilters.tsx
  src/components/ArchiveResults.tsx
  src/components/ArchivePreview.tsx
  src/components/NewRequestForm.tsx
  src/components/SimilarCases.tsx
  src/lib/api.ts                 # FastAPI 호출 함수
  src/lib/types.ts               # API 타입
  src/**/*.test.tsx
.env.example
README.md
```

---

### Task 1: Local Project and Database Safety Boundary

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `backend/pyproject.toml`
- Create: `backend/app/config.py`
- Create: `backend/tests/test_config.py`

**Interfaces:**
- Consumes: `VOC_DB_HOST`, `VOC_DB_PORT`, `VOC_DB_NAME`, `VOC_DB_USER`, `VOC_DB_PASSWORD`
- Produces: `Settings.database_dsn() -> str`, `get_settings() -> Settings`

- [ ] **Step 1: Initialize version control and ignore secrets/build output**

```powershell
git init
```

Create `.gitignore` with `.env`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `node_modules/`, `.next/`, and `test-results/`.

- [ ] **Step 2: Write the failing configuration tests**

```python
def test_only_training_database_is_allowed(monkeypatch):
    monkeypatch.setenv("VOC_DB_NAME", "테스트용 Data")
    with pytest.raises(ValueError, match="학습용 Data"):
        Settings()

def test_training_database_builds_dsn(monkeypatch):
    monkeypatch.setenv("VOC_DB_NAME", "학습용 Data")
    monkeypatch.setenv("VOC_DB_PASSWORD", "local-secret")
    settings = Settings()
    assert "%ED%95%99%EC%8A%B5%EC%9A%A9%20Data" in settings.database_dsn()
```

- [ ] **Step 3: Run the configuration tests and verify failure**

Run: `cd backend; python -m pytest tests/test_config.py -v`

Expected: FAIL because `Settings` does not exist.

- [ ] **Step 4: Implement strict local DB settings**

```python
class Settings(BaseSettings):
    voc_db_host: str = "localhost"
    voc_db_port: int = 5432
    voc_db_name: str = "학습용 Data"
    voc_db_user: str = "postgres"
    voc_db_password: SecretStr

    @model_validator(mode="after")
    def reject_non_training_database(self):
        if self.voc_db_name != "학습용 Data":
            raise ValueError("VOC_DB_NAME must be 학습용 Data")
        return self

    def database_dsn(self) -> str:
        password = quote(self.voc_db_password.get_secret_value(), safe="")
        database = quote(self.voc_db_name, safe="")
        return f"postgresql://{self.voc_db_user}:{password}@{self.voc_db_host}:{self.voc_db_port}/{database}"
```

- [ ] **Step 5: Run tests and commit**

Run: `cd backend; python -m pytest tests/test_config.py -v`

Expected: 2 passed.

```powershell
git add .gitignore .env.example backend/pyproject.toml backend/app/config.py backend/tests/test_config.py
git commit -m "chore: lock local app to training database"
```

---

### Task 2: Training Database Migration and Repository

**Files:**
- Create: `backend/migrations/001_local_search.sql`
- Create: `backend/app/db.py`
- Create: `backend/app/repositories/voc_cases.py`
- Create: `backend/tests/test_local_training_db.py`

**Interfaces:**
- Consumes: `Settings.database_dsn()`
- Produces: `database_connection()`, `VocCaseRepository.list_candidates(filters)`, `get(case_id)`, `create(payload)`

- [ ] **Step 1: Add a read-only integration test for the existing 135 records**

```python
@pytest.mark.localdb
def test_training_database_contains_only_expected_seed_rows(repository):
    summary = repository.dataset_summary()
    assert summary.database_name == "학습용 Data"
    assert summary.historical_count == 135
    assert summary.duplicate_case_ids == 0
    assert summary.missing_product_equipment == 0
```

- [ ] **Step 2: Run the integration test and verify failure**

Run after setting `VOC_DB_PASSWORD`: `cd backend; python -m pytest -m localdb tests/test_local_training_db.py -v`

Expected: FAIL because the repository does not exist.

- [ ] **Step 3: Add the idempotent local migration**

```sql
ALTER TABLE public.voc_cases
    ADD COLUMN IF NOT EXISTS product_equipment text,
    ADD COLUMN IF NOT EXISTS record_origin text NOT NULL DEFAULT 'historical',
    ADD COLUMN IF NOT EXISTS search_document text;

UPDATE public.voc_cases
SET record_origin = 'historical'
WHERE record_origin IS NULL OR record_origin = '';

UPDATE public.voc_cases
SET search_document = concat_ws(' ', customer_request, original_mail_body, full_response_history)
WHERE search_document IS NULL;

UPDATE public.voc_cases
SET product_equipment = (regexp_match(
    customer_request,
    '(?i)\\m(NCM811|NCM9|NCA|LMFP|LFP)\\M'
))[1]
WHERE product_equipment IS NULL;

CREATE INDEX IF NOT EXISTS idx_voc_cases_received_at ON public.voc_cases (received_at DESC);
CREATE INDEX IF NOT EXISTS idx_voc_cases_filters ON public.voc_cases (voc_type, voc_subtype, final_status);
```

- [ ] **Step 4: Implement psycopg connection and parameterized repository queries**

```python
@contextmanager
def database_connection():
    with psycopg.connect(get_settings().database_dsn(), row_factory=dict_row) as connection:
        yield connection

def get(self, case_id: str) -> dict[str, Any] | None:
    with database_connection() as connection:
        return connection.execute(
            "SELECT * FROM public.voc_cases WHERE case_id = %s",
            (case_id,),
        ).fetchone()
```

All filters use psycopg parameters; database, schema, and table names remain constants.

- [ ] **Step 5: Apply migration only to `학습용 Data` and verify**

Run: `psql -U postgres -d "학습용 Data" -v ON_ERROR_STOP=1 -f backend/migrations/001_local_search.sql`

Run: `cd backend; python -m pytest -m localdb tests/test_local_training_db.py -v`

Expected: database name `학습용 Data`, historical count 135, duplicate count 0, missing product/equipment count 0.

- [ ] **Step 6: Commit**

```powershell
git add backend/migrations backend/app/db.py backend/app/repositories backend/tests/test_local_training_db.py
git commit -m "feat: connect training VOC database"
```

---

### Task 3: Text Normalization and BM25 Ranking

**Files:**
- Create: `backend/app/services/text.py`
- Create: `backend/app/services/bm25.py`
- Create: `backend/tests/test_text.py`
- Create: `backend/tests/test_bm25.py`

**Interfaces:**
- Produces: `normalize_text(value: str | None) -> str`, `tokenize(value: str | None) -> list[str]`, `Bm25Index.rank(query, candidates, query_subtype, limit) -> list[RankedCase]`

- [ ] **Step 1: Write failing normalization tests**

```python
def test_normalize_text_removes_html_and_repeated_spaces():
    assert normalize_text("<p>Cell  Low</p>\nVoltage") == "cell low voltage"

def test_tokenize_accepts_empty_values():
    assert tokenize(None) == []
```

- [ ] **Step 2: Write failing BM25 and Subtype boost tests**

```python
def test_subtype_match_adds_exactly_ten_percent():
    ranked = index.rank("cell low voltage", candidates, "Cell Low Voltage", 3)
    matched = next(item for item in ranked if item.case_id == "COM-001")
    assert matched.final_score == pytest.approx(matched.bm25_score * 1.1)

def test_customer_name_does_not_override_stronger_request_match():
    ranked = index.rank("gas generation", candidates, "Gas Generation", 3)
    assert ranked[0].case_id == "REQ-GAS-CONTENT-MATCH"
```

- [ ] **Step 3: Run unit tests and verify failure**

Run: `cd backend; python -m pytest tests/test_text.py tests/test_bm25.py -v`

Expected: FAIL because the service modules do not exist.

- [ ] **Step 4: Implement normalization and BM25 formula**

```python
def normalize_text(value: str | None) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[^0-9A-Za-z가-힣._+-]+", " ", text.lower())
    return " ".join(text.split())

final_score = bm25_score * (1.1 if case.voc_subtype == query_subtype else 1.0)
```

The index stores tokenized `customer_request`, `original_mail_body`, and `full_response_history` once during refresh and reports query tokens that occur in each result as `matched_keywords`.

- [ ] **Step 5: Run tests and commit**

Run: `cd backend; python -m pytest tests/test_text.py tests/test_bm25.py -v`

Expected: all tests pass.

```powershell
git add backend/app/services backend/tests/test_text.py backend/tests/test_bm25.py
git commit -m "feat: rank VOC cases with boosted BM25"
```

---

### Task 4: Archive Search API

**Files:**
- Create: `backend/app/schemas.py`
- Create: `backend/app/services/search.py`
- Create: `backend/app/routers/archive.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/test_archive_api.py`

**Interfaces:**
- Produces: `GET /api/archive`, `GET /api/archive/{case_id}`, `ArchivePage`, `ArchiveDetail`

- [ ] **Step 1: Write failing API tests with a fake repository**

```python
def test_archive_without_query_defaults_to_all_statuses_and_latest(client):
    response = client.get("/api/archive")
    assert response.status_code == 200
    assert response.json()["sort"] == "latest"
    assert response.json()["items"][0]["received_at"] >= response.json()["items"][1]["received_at"]

def test_archive_query_defaults_to_relevance_and_keeps_filters(client):
    response = client.get("/api/archive", params={"q": "gas generation", "voc_subtype": "Gas Generation"})
    assert response.status_code == 200
    assert response.json()["sort"] == "relevance"
    assert response.json()["items"][0]["matched_keywords"]
```

- [ ] **Step 2: Run tests and verify failure**

Run: `cd backend; python -m pytest tests/test_archive_api.py -v`

Expected: FAIL with missing FastAPI application.

- [ ] **Step 3: Implement validated query models and conditional search**

```python
@router.get("", response_model=ArchivePage)
def list_archive(query: Annotated[ArchiveQuery, Query()]):
    effective_sort = query.sort or ("relevance" if query.q else "latest")
    return search_service.search_archive(query, effective_sort)
```

Allowed sorts are `relevance`, `latest`, and `oldest`; `relevance` without a keyword returns HTTP 422. Page size is 20 with a maximum of 100.

- [ ] **Step 4: Implement detail lookup and not-found behavior**

```python
@router.get("/{case_id}", response_model=ArchiveDetail)
def get_archive_case(case_id: str):
    case = repository.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="사례를 찾을 수 없습니다.")
    return case
```

- [ ] **Step 5: Run tests and commit**

Run: `cd backend; python -m pytest tests/test_archive_api.py -v`

Expected: all tests pass.

```powershell
git add backend/app backend/tests/test_archive_api.py
git commit -m "feat: expose archive search API"
```

---

### Task 5: Manual Request Entry and Closed-Case Top 3 API

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/repositories/voc_cases.py`
- Create: `backend/app/routers/requests.py`
- Create: `backend/tests/test_requests_api.py`

**Interfaces:**
- Produces: `POST /api/requests`, `GET /api/requests/{case_id}/similar-cases`

- [ ] **Step 1: Write failing creation and recommendation tests**

```python
def test_manual_request_is_stored_as_user_input(client):
    response = client.post("/api/requests", json=VALID_REQUEST)
    assert response.status_code == 201
    assert response.json()["record_origin"] == "user_input"
    assert response.json()["final_status"] == "received"

def test_top_three_uses_closed_cases_only(client):
    case_id = client.post("/api/requests", json=VALID_REQUEST).json()["case_id"]
    response = client.get(f"/api/requests/{case_id}/similar-cases")
    assert len(response.json()["items"]) <= 3
    assert all(item["final_status"] == "closed" for item in response.json()["items"])
```

- [ ] **Step 2: Run tests and verify failure**

Run: `cd backend; python -m pytest tests/test_requests_api.py -v`

Expected: FAIL because request routes do not exist.

- [ ] **Step 3: Implement manual insertion without embedding generation**

```python
case_id = f"WEB-{uuid4().hex[:12].upper()}"
values = {
    "case_id": case_id,
    "record_origin": "user_input",
    "final_status": "received",
    "search_document": " ".join(filter(None, [payload.customer_request, payload.original_mail_body])),
}
```

The insert statement writes only confirmed form fields and leaves both legacy embedding columns null.

- [ ] **Step 4: Implement Top 3 filtering and refresh the index after creation**

```python
candidates = repository.list_candidates(final_status="closed", exclude_case_id=case_id)
items = search_service.rank_similar(source_case, candidates, limit=3)
```

Creating a request triggers one index refresh; normal archive queries reuse the loaded index.

- [ ] **Step 5: Run tests and commit**

Run: `cd backend; python -m pytest tests/test_requests_api.py -v`

Expected: all tests pass.

```powershell
git add backend/app backend/tests/test_requests_api.py
git commit -m "feat: save manual VOC requests and return top three"
```

---

### Task 6: Next.js App Shell and Archive Split View

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/src/app/layout.tsx`
- Create: `frontend/src/app/globals.css`
- Create: `frontend/src/components/AppShell.tsx`
- Create: `frontend/src/lib/types.ts`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/app/archive/page.tsx`
- Create: `frontend/src/components/ArchiveFilters.tsx`
- Create: `frontend/src/components/ArchiveResults.tsx`
- Create: `frontend/src/components/ArchivePreview.tsx`
- Create: `frontend/src/app/archive/archive.test.tsx`

**Interfaces:**
- Consumes: `GET /api/archive`, `GET /api/archive/{case_id}`
- Produces: URL-backed archive filters and split-view UI

- [ ] **Step 1: Scaffold the frontend and write a failing archive interaction test**

```tsx
it("keeps filters while opening and closing the preview", async () => {
  render(<ArchivePage />);
  await user.type(screen.getByRole("searchbox"), "gas generation");
  await user.click(screen.getByRole("button", { name: "검색" }));
  await user.click(await screen.findByText("COM-001"));
  expect(screen.getByRole("complementary")).toHaveTextContent("원본 메일");
  expect(screen.getByRole("searchbox")).toHaveValue("gas generation");
});
```

- [ ] **Step 2: Run the frontend test and verify failure**

Run: `cd frontend; npm test -- archive.test.tsx`

Expected: FAIL because the archive page does not exist.

- [ ] **Step 3: Implement the CI Blue application shell**

Use `#005eb8` for active navigation and primary actions, `#f9f9ff` for the page background, 260px fixed sidebar, a top search/header area, 6–10px radii, thin borders, and no decorative shadows.

- [ ] **Step 4: Implement URL-backed filters and conditional sort controls**

```ts
export type ArchiveQuery = {
  q?: string;
  customer_name?: string;
  product_equipment?: string;
  voc_type?: string;
  voc_subtype?: string;
  final_status?: string;
  responsible_department?: string;
  received_from?: string;
  received_to?: string;
  sort?: "relevance" | "latest" | "oldest";
  page?: number;
};
```

The page serializes these values into `URLSearchParams`; returning from detail restores the same URL.

- [ ] **Step 5: Implement results and right-side preview**

The left pane renders 20-row pages with Case ID, customer, product/equipment, VOC Type/Subtype, request summary, department, status, received date, score, and matched keywords. The right pane fetches the selected detail and exposes `상세 화면에서 보기`.

- [ ] **Step 6: Run tests and commit**

Run: `cd frontend; npm test -- archive.test.tsx`

Expected: all tests pass.

```powershell
git add frontend
git commit -m "feat: build searchable VOC archive screen"
```

---

### Task 7: New Request and Top 3 Screen

**Files:**
- Create: `frontend/src/app/requests/new/page.tsx`
- Create: `frontend/src/components/NewRequestForm.tsx`
- Create: `frontend/src/components/SimilarCases.tsx`
- Create: `frontend/src/app/requests/new/new-request.test.tsx`
- Modify: `frontend/src/lib/api.ts`

**Interfaces:**
- Consumes: `POST /api/requests`, `GET /api/requests/{case_id}/similar-cases`
- Produces: manual mail entry, confirmed structured fields, saved case, Top 3 cards

- [ ] **Step 1: Write a failing user-flow test**

```tsx
it("saves a manually entered request and shows top three closed cases", async () => {
  render(<NewRequestPage />);
  await user.type(screen.getByLabelText("원본 메일"), "Gas generation inquiry...");
  await user.type(screen.getByLabelText("고객사"), "Sample Customer");
  await user.selectOptions(screen.getByLabelText("VOC Type"), "Inquiry");
  await user.click(screen.getByRole("button", { name: "저장 및 유사 사례 검색" }));
  expect(await screen.findAllByTestId("similar-case")).toHaveLength(3);
});
```

- [ ] **Step 2: Run the test and verify failure**

Run: `cd frontend; npm test -- new-request.test.tsx`

Expected: FAIL because the page does not exist.

- [ ] **Step 3: Implement manual entry and user confirmation form**

Required fields are customer name, VOC Type, VOC Subtype, customer request, and original mail body. Product/equipment and responsible department are optional at initial entry. The user can edit all extracted/entered values before submission.

- [ ] **Step 4: Implement Top 3 result cards**

Each card displays relative score, matched keywords, customer, product/equipment, VOC Type/Subtype, request summary, responsible department, received date, and a link to the archive detail.

- [ ] **Step 5: Run tests and commit**

Run: `cd frontend; npm test -- new-request.test.tsx`

Expected: all tests pass.

```powershell
git add frontend/src/app/requests frontend/src/components frontend/src/lib/api.ts
git commit -m "feat: add manual request and top three workflow"
```

---

### Task 8: Local Integration, QA, and Runbook

**Files:**
- Create: `backend/tests/test_local_archive_smoke.py`
- Create: `frontend/e2e/local-voc.spec.ts`
- Create: `README.md`
- Modify: `.env.example`

**Interfaces:**
- Verifies: PostgreSQL → FastAPI → Next.js → browser workflow
- Produces: repeatable local commands and QA evidence

- [ ] **Step 1: Add a local DB smoke test that never names the test database**

```python
@pytest.mark.localdb
def test_archive_reads_training_rows_without_writing(client):
    archive = client.get("/api/archive").json()
    assert archive["total"] == 135
    assert all(item["case_id"] for item in archive["items"])
```

- [ ] **Step 2: Add an end-to-end browser test**

```ts
test("training archive can be searched without creating records", async ({ page }) => {
  await page.goto("/archive");
  await page.getByRole("searchbox").fill("gas generation");
  await page.getByRole("button", { name: "검색" }).click();
  await expect(page.getByTestId("archive-result").first()).toBeVisible();
  await expect(page.getByText("관련도순")).toBeVisible();
});
```

- [ ] **Step 3: Run backend, frontend, and integration tests**

Run: `cd backend; python -m pytest -v`

Run: `cd frontend; npm test`

Run: `cd frontend; npx playwright test e2e/local-voc.spec.ts`

Expected: all tests pass; no command connects to `테스트용 Data`.

- [ ] **Step 4: Perform gstack browser QA**

Verify desktop and narrow layouts, archive filters, relevance/latest sort, result preview, detail return-state preservation, and the empty-state behavior of the manual request form. Do not submit synthetic records to the local database; the user will perform the first real manual submission. Capture screenshots for any defect before fixing it.

- [ ] **Step 5: Write the local runbook**

Document these exact stages in `README.md`: set `VOC_DB_PASSWORD`, apply migration to `학습용 Data`, create the Python environment, install Node dependencies, start FastAPI at `http://127.0.0.1:8000`, start Next.js at `http://localhost:3000`, and run all tests.

- [ ] **Step 6: Commit**

```powershell
git add README.md .env.example backend/tests frontend/e2e
git commit -m "test: verify local training-data workflow"
```

---

## Plan Self-Review Result

- Spec coverage: archive filters, all-status default, conditional BM25, Subtype boost, preview, detail navigation, state restoration, local/Supabase-compatible DB boundary, manual entry, and closed-only Top 3 all map to explicit tasks.
- Data safety: every runtime configuration path rejects DB names other than `학습용 Data`; automated write tests use fakes, while real training-DB checks are read-only and never connect to the test DB.
- Type consistency: archive query fields and sort values are identical in backend schemas, frontend types, and tests.
- Scope: this plan intentionally excludes department assignment, progress tracking, notifications, attachments, authentication, Docker, and deployment; they require a separate implementation plan after the local archive and Top 3 vertical slice works.
