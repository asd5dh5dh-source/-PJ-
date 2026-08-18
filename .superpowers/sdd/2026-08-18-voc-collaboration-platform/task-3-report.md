# Task 3 report

## Scope delivered

- Added public dashboard aggregates with recent-30-day, current-week, current-month, and custom date filters.
- Added public notification history and translation preview APIs.
- Added notification scheduling/delivery boundaries for high priority, normal D-2/D-1/overdue, and immediate reopened-task alerts.
- Enforced external-review preview-only mail and translation behavior; internal mail stays pending without SMTP configuration.
- Added writer-gated CSV/XLSX archive exports using the existing Task 1 writer dependency.
- Added writer-gated, whitelisted master-data list/create/upsert APIs with audit history for changes.
- Preserved Task 1 writer lockout/authentication and Task 2 collaboration/approval behavior. No frontend files were changed.

## TDD evidence

### RED

Initial Task 3 command:

```text
uv run pytest tests/test_dashboard_api.py tests/test_notifications.py tests/test_export_api.py -v
```

Observed collection failure for the missing notification service. After adding the service boundary, the API suites produced 11 expected 404 failures for the missing dashboard, notification, translation, export, and admin routes.

Additional focused RED cycles were observed for:

- current-week/current-month dashboard ranges and blank master-data rejection (`3 failed`);
- singleton final-approver upsert/audit behavior (`1 failed`);
- configurable notification time/timezone (`1 failed`).

Each failed for the named missing behavior before its production change.

### GREEN

```text
uv run pytest tests/test_dashboard_api.py tests/test_notifications.py tests/test_export_api.py -v
24 passed in 0.85s

uv run pytest -m "not localdb" -q
130 passed, 2 deselected in 2.35s
```

`uv run python -m compileall -q app tests`, XML parsing of every generated XLSX XML part, and `git diff --check` also exited successfully.

## Security and environment boundaries

- Both export formats and every master-data route depend on `require_writer`; missing headers return 401 and use the existing lockout store.
- External review returns before any SMTP sender or local translation callable can execute and records mail as `preview` with `real_delivery=false`.
- Internal mail executes only when both SMTP host and sender address are configured; otherwise it records `pending`. Delivery exceptions are recorded as `failed`.
- Korean input bypasses translation. External foreign-language input returns a preview without running a model.
- Master-data table names and writable columns are server-side whitelists; writer identity and before/after values are written to `change_audits`.

## Ponytail simplification

No XLSX dependency was installed in the existing backend environment, and the brief prohibited adding dependencies. The XLSX endpoint therefore writes one valid, unstyled worksheet with standard-library `zipfile` and XML utilities. Add a workbook library only if future requirements need styling, formulas, multiple sheets, or large streaming exports.

## Known environment limitation

The two pre-existing `@pytest.mark.localdb` tests still require local PostgreSQL credentials unavailable in this worktree (`fe_sendauth: no password supplied`). They were not changed; the agreed non-local regression suite passes.
