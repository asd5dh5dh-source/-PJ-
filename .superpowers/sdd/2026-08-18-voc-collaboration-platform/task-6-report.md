# Task 6 report

Deployment configuration and the external-review runbook remain safe by default: browser API calls stay same-origin and are rewritten by Next.js to `VOC_API_BASE_URL`; the public browser suite uses mocked API responses and does not contact a live database, SMTP server, or deployment.

## Verification

- `cd backend; uv run pytest -m "not localdb" -v` — 152 passed, 2 live-DB tests deselected.
- `cd frontend; npm test` — 9 files, 37 tests passed.
- `cd frontend; npm run build` — production build and TypeScript checks passed.
- `cd frontend; npx playwright test` — 3 Chromium tests passed.

## Writer-header follow-up

- Added a test-first regression for `X-Writer-Name: %00`. It failed with HTTP 200 before the change and now returns HTTP 401.
- `WriterCredentials` now rejects NUL characters at the shared validation boundary, preventing decoded header values from reaching PostgreSQL `TEXT` writes. Existing ASCII and percent-encoded Korean writer-name coverage remains green.

## Proxy integration coverage

No new rewrite-to-FastAPI browser test was added. The current Playwright route fulfillment verifies browser-side percent encoding, but it intercepts requests before Next's server rewrite. Exercising the real rewrite and FastAPI decoding together requires deployment-style Next and FastAPI process configuration; a fake or live-network substitute would not verify that runtime boundary reliably. Run that smoke check against the configured deployment environment when it is available.
