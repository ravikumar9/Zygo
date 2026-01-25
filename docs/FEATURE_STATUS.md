# Feature Status (Working vs Broken)

## Hotels
- Working: Room cards, price disclosure (`base_price`), policy accordion, booking snapshot creation, guest checkout path.
- Partial: Listing filters/data decoupling; payment finalization flow; cancellation policy locking timelines.
- Missing/Broken: Server-aligned health endpoint; deterministic search seeds for E2E.

## Buses
- Working: Operator registration/verification; routes, schedules; seat layout reserved-for logic; mixed-gender booking tests.
- Partial: Pricing rules engine integration; analytics/reporting dashboards.
- Missing/Broken: E2E UI coverage; operator portal navigation shell integration.

## Flights
- Working: Basic routes/pages present.
- Partial: APIs and pricing normalization.
- Missing/Broken: Full search→listing→detail→checkout E2E with tests.

## Identity & Auth
- Working: Django auth; global visibility; guest booking preserved.
- Partial: OTP enforcement/verification tests; SSO hooks.
- Missing/Broken: Unified cross-vertical identity events telemetry.

## Booking & Payment
- Working: Booking status machine, reservation timeout, inventory lock release; immutable snapshots in `HotelBooking`.
- Partial: Payment abstraction, wallet balancing, promo code interactions.
- Missing/Broken: Robust refund flows; end-to-end payment simulation.

## Owner & Operator Flows
- Working: Property Owner state machine, approval, completeness checks; Bus Operator dashboards.
- Partial: Availability calendar (owner), payout reports.
- Missing/Broken: Unified dashboards under one shell; cross-vertical view.
