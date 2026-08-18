# Task 5 report

Implemented the Task 5 screens and their existing API integration:

- Replaced the archive redirect with a public dashboard showing equal-weight stage, due-task, and recent-request panels. The default is 30 days with week, month, and custom date-range filters; sensitive fields returned accidentally by an API response are not rendered.
- Added the public notification log screen with separate pending/preview and delivery-history panels plus on-demand subject/body previews. Recipient addresses are not rendered.
- Added writer-gated CSV and XLSX archive downloads that preserve the active archive query and keep credentials in `WriterGate` component memory.
- Added a writer-gated management screen for customers, products/equipment, VOC type/subtype, people, the fixed final approver, notification templates, and weekday notification time.
- Extended the shared shell navigation and typed API/data contracts for the new screens.

Review hardening added:

- Made `WriterGate` the single credential owner and propagated credential clearing to the admin screen.
- Bound loaded final-approver and weekday-notification-time values to their forms.
- Added accessible save progress/completion announcements and blocked repeated submissions while a save is in flight.
- Routed archive exports through the same BM25/filter/sort semantics as the public archive while exporting all matching pages.
- Kept mobile navigation inside the viewport with horizontal scrolling.

## TDD evidence

- RED: dashboard tests failed on the prior `/archive` redirect; notification/admin suites failed because their pages did not exist; archive export failed because no protected download action existed.
- RED: the custom date-range test failed while only preset options existed.
- RED: review tests reproduced stale admin access after credential clear, blank loaded singleton settings, duplicate async saves, export ranking/sort drift, and mobile viewport overflow.
- GREEN: `npm test -- page.test.tsx archive.test.tsx admin/page.test.tsx notifications/page.test.tsx` passed after implementation.

## Final verification

- `cd frontend; npm test` — 9 test files, 37 tests passed.
- `cd frontend; npm run build` — production build and TypeScript checks passed; `/`, `/admin`, and `/notifications` were generated successfully.
- `cd frontend; npx playwright test e2e/local-voc.spec.ts` — 2 Chromium tests passed, including the mobile navigation regression.
- `cd backend; uv run pytest -m "not localdb" -q` — 146 tests passed, 2 live-DB tests deselected. A full run reached 146 passes; the same 2 tests require a PostgreSQL password unavailable in this worktree.
- `git diff --check` — passed (line-ending notices only).

Deployment configuration was not changed. The unrelated untracked `outputs/고객_요청_대응_플랫폼_PPT_원고.md` file was left untouched.
