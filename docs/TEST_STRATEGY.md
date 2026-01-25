# Test Strategy (E2E)

## Layers
- Unit: models/services (pricing, cancellation rules, snapshots)
- API: DRF endpoints for search/listing/detail/checkout
- UI E2E: Playwright (JS) or Python Playwright backed by live server

## Principles
- Autonomous server start/stop; no manual preconditions
- DB isolation per run; deterministic seeding
- Screenshot-on-failure; HAR capture optional

## Enhancements
- Readiness Probe: `GET /healthz` with DB ping (simple SELECT) and cache check; retry with backoff.
- Seeds: `tests/seeds.py` providing fixed cities, hotels, rooms, operators, routes; used by fixtures.
- Parallel Safety: Use unique DB/schema per worker (sqlite temp or `pytest-xdist` + separate DBs).

## Example Fixture (Python)
```python
import pytest, requests, time

BASE = "http://127.0.0.1:8000"

@pytest.fixture(scope="session", autouse=True)
def wait_for_server():
    for _ in range(60):
        try:
            r = requests.get(f"{BASE}/healthz", timeout=1)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("Server not ready after 60s")
```

## Playwright Config (JS)
```js
// playwright.config.js
module.exports = {
  use: { baseURL: 'http://127.0.0.1:8000' },
  retries: 1,
  reporter: [['html', { outputFolder: 'playwright-report' }]]
};
```
