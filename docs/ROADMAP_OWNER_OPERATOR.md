# Roadmap – Owner & Operator Flows

## Property Owner
- Dashboard: Summary cards (approval status, bookings, payout pending)
- Inventory: Rooms, pricing, availability calendar (drag-to-block, bulk update)
- Bookings: Snapshot-based view; CSV export; cancellation policies applied
- Payouts: Razorpay/Stripe payout simulation; statements; tax/GST download
- Reports: Occupancy, ADR, RevPAR; filters by date/source

## Bus Operator
- Registration: Self-serve onboarding; verification workflow
- Routes & Schedules: CRUD routes; add daily/weekly schedules
- Seat Layout: Visual editor; reserved-for sections (ladies/general)
- Pricing Rules: Peak/day-of-week/seat-type deltas; promo codes
- Operations: Booking management; seat hold/release; boarding/dropping points
- Analytics: Load factors, revenue, cancellations; export

## Integration into Main UX
- Single shell nav: Services in header; dashboards under `/owner/` and `/operator/`
- Consistent 4-page template: Search → Listing → Detail → Checkout for each vertical
- Identity: Unified session; cross-vertical permissions
