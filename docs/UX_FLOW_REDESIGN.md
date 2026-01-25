# UX Flow Redesign (Goibibo-Informed)

## Global Rules
- Auth visible in header on all pages; no forced login during checkout (upsell optional)
- One primary CTA per page; secondary CTAs de-emphasized
- Above-the-fold: Hero/search; Below-the-fold: SEO/informational content

## 4 Templates
1. Landing Page
   - Hero with service selectors (Flights/Hotels/Bus)
   - Primary CTA: Start Search
   - Offers/SEO sections below fold
2. Search Page
   - Criteria inputs; validation; recent searches
   - Primary CTA: Search
3. Listing Page
   - Results with filters; price disclosure (base vs discounted)
   - Primary CTA: Select / Book
4. Detail Page
   - Trust signals (policies, reviews); meal plan selector
   - Primary CTA: Continue to Checkout

## Cross-Vertical Mapping
- Hotels: `RoomType.base_price`, `RoomMealPlan.price_delta`, policy accordion; instant pricing with fail-fast JS
- Bus: Route/schedule list; seat map selection; reserved-for logic surfaced in UI
- Flights: Normalize search/list/detail with price breakdown; defer to future adapter

## Checkout
- Guest-first; snapshot capture; disclosure of taxes/fees
- Optional auth upsell; payment adapter abstraction; confirmation reads snapshots only

## Sticky & SEO Behavior
- Auth and search bars sticky where applicable
- SEO blocks and rich text below the fold (from `UX_DEEP_MAP.json` observations)
