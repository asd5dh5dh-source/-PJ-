# Task 5 report

Implemented the Task 5 frontend surfaces only:

- Replaced the archive redirect with a public dashboard showing equal-weight stage, due-task, and recent-request panels. The default is 30 days with week, month, and custom date-range filters; sensitive fields returned accidentally by an API response are not rendered.
- Added the public notification log screen with separate pending/preview and delivery-history panels plus on-demand subject/body previews. Recipient addresses are not rendered.
- Added writer-gated CSV and XLSX archive downloads that preserve the active archive query and keep credentials in `WriterGate` component memory.
- Added a writer-gated management screen for customers, products/equipment, VOC type/subtype, people, the fixed final approver, notification templates, and weekday notification time.
- Extended the shared shell navigation and typed API/data contracts for the new screens.

## TDD evidence

- RED: dashboard tests failed on the prior `/archive` redirect; notification/admin suites failed because their pages did not exist; archive export failed because no protected download action existed.
- RED: the custom date-range test failed while only preset options existed.
- GREEN: `npm test -- page.test.tsx archive.test.tsx admin/page.test.tsx notifications/page.test.tsx` passed after implementation.

## Final verification

- `cd frontend; npm test` — 9 test files, 34 tests passed.
- `cd frontend; npm run build` — production build and TypeScript checks passed; `/`, `/admin`, and `/notifications` were generated successfully.
- `git diff --check` — passed (line-ending notices only).

Deployment configuration was not changed. The unrelated untracked `outputs/고객_요청_대응_플랫폼_PPT_원고.md` file was left untouched.
