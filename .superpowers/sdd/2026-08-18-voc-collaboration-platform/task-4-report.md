# Task 4 report

## Scope delivered

- Added a reusable writer gate that verifies a writer before protected actions and retains the writer name/password only in React component state.
- Reworked new-request registration into sequential mail paste, extracted sender confirmation, VOC classification, department task assignment, server draft creation, and closed-only Top 3 results.
- Added typed collaboration API clients and response models for VOC detail, task updates, approvals, stages, and follow-up rounds.
- Added the VOC management screen with separate overall-stage and task-state presentation, round/stage timeline, task editing, department/final approval and rejection, Korean reply draft, ECM links, stage actions, follow-up rounds, and audit history.
- Reused and extended the CI Blue `AppShell`; dashboard and admin screens remain outside Task 4.

## Integration decision

The completed backend has no separate draft route. `POST /api/voc` creates the authenticated server draft at the initial `received` stage. Top 3 uses the existing public BM25 archive query with `final_status=closed`, avoiding a duplicate legacy `/api/requests` record.

## TDD evidence

### RED

```text
npm test -- new-request.test.tsx
6 failed
```

All six failures stopped at the missing sequential mail-confirmation action, before production code was added. Focused component/detail tests were also written before their missing components and route.

### GREEN

```text
npm test -- WriterGate.test.tsx page.test.tsx new-request.test.tsx
3 test files passed, 10 tests passed

npm test
6 test files passed, 23 tests passed

npm run build
Compiled successfully; TypeScript passed; /voc/[caseId] generated as a dynamic route

uv run pytest -m "not localdb" -q
145 passed, 2 deselected

git diff --check
exit 0
```

## Credential boundary

The shared password is held only by `WriterGate`'s in-memory React state and passed directly into protected fetch headers. No local storage, session storage, cookie, URL, or server-rendered state stores credentials. The writer can explicitly clear the in-memory session with **작성자 변경**.

## Ponytail simplification

No new dependency or client-side credential store was added. Mail extraction uses the two sender/company header patterns already supported by the workflow, and the existing archive endpoint supplies Top 3 results. Add richer mail parsing only when the backend exposes a dedicated parse/preview contract.
