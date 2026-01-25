# Fix Plan (P0 → P1 → P2)

## P0 – Stability (Blockers)
- Server Orchestration: Add repo-local Playwright config (JS) that starts Django via `manage.py runserver` and sets `baseURL`, or use `pytest-django` `live_server` with Python Playwright fixtures.
- Health Check: Implement `/healthz` (lightweight view) returning 200 OK; probe before UI tests.
- Clean DB Helper: Add `tests/utils/db_reset.py` to `flush` + `migrate` + idempotent seeds; run per test session.

## P1 – Architecture Cleanup
- Domain Separation: Move pricing/identity helpers to `core/services` or `bookings/utils` consistently; expose stable APIs.
- Test Decoupling: Replace hard-coded test data assumptions with deterministic seed factory; use `factory_boy` or in-repo factories.
- API Normalization: Ensure consistent status codes/shape for search, listing, detail, checkout across verticals.

## P2 – Feature Completion
- Booking Lifecycle: Confirm/expire/cancel flows end-to-end; admin overrides audited.
- Payment Simulation: Pluggable payment adapter with sandbox; trace wallet before/after consistently.
- User History: My bookings list/cancellations; snapshot-based display and immutable totals.

## Concrete Tasks
- Add `tests/conftest.py` or Django `LiveServerTestCase` Playwright bridge; wait-on `/healthz`.
- Introduce `.env.test` + `pytest.ini` (or `settings_test.py`) for DB isolation.
- Provide `scripts/test_server.ps1` (Windows) and `scripts/test_server.sh` (Unix) to start/stop for CI.
