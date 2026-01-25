# GoExplorer Architecture Review (Current State)

## Stack & Structure
- Backend: Django 4.2.9, DRF, PostgreSQL (fallback: SQLite via dj-database-url)
- Frontend: Server-rendered Django templates + jQuery/Bootstrap; Playwright E2E (external config)
- Async/Infra: Celery + Redis (present), Whitenoise, Gunicorn (production)
- Auth: Django auth; OTP flows referenced; global auth surfaced in header

## Key Domains & Modules
- Hotels: models, views, pricing/service helpers, channel manager stubs; `RoomType.base_price` canonical; `RoomMealPlan.price_delta + is_default` enforced.
- Bookings: `Booking` + `HotelBooking` with immutable `room_snapshot` and `price_snapshot`; reservation timeout, inventory lock release; status transitions.
- Property Owners: approval workflow with `Property.status` state machine; required-field completeness; owner dashboards/views present.
- Buses: operator registration, routes, schedules, seat layout and reserved-for rules; operator dashboards/views present.
- Core: cities, mixins, soft-delete, corporate routes; caching/session via DB cache.

## Page Templates (Mapping)
- Landing: Implemented (home) with global auth CTA; Goibibo-style hero + offers below the fold.
- Search: Implemented per service; inputs JS-driven; hotels search uses aggregated `RoomType.base_price`.
- Listing: Implemented/partial; price disclosure helpers; filters exist; coupling to live data observed.
- Detail: Implemented/partial; conversion elements present; policy + pricing shown; snapshot enforced at booking.
- Checkout: Partial; guest-first flow enabled; payment abstraction present but not fully stabilized.

## Tests & Tooling
- Django `TestCase` suites across buses, booking features, owners.
- Playwright spec present (`tests/e2e_hotels.spec.js`) assuming base URL; no repo-local Playwright config or server orchestration.
- PyTest not declared in `requirements.txt`.

## Observations (Aligned to Phase‑1)
- One primary CTA per page respected; auth visible globally.
- Pricing normalized to `base_price`; fail-fast JS implemented on room card.
- Booking confirmation uses immutable snapshots; guest flow without forced login.
- Tests fail intermittently due to absent server lifecycle orchestration and DB state isolation.
