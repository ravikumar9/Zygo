# COMPETITIVE_PRICING_ARCHITECTURE.md

**Objective (Non-Negotiable)**
- Build a legal, auditable, real-time competitive pricing system that:
  - Beats Agoda, MMT, Goibibo without illegal scraping
  - Avoids margin bleed with guardrails
  - Produces evidence-backed pricing decisions
  - Is provable via Playwright E2E execution
  - Scales to channel managers (RateGain, AxisRooms, Staah)
- Rule: If pricing cannot be explained with evidence → it must not go live.

**Core Principle (Frozen)**
- There is no single “final competitor price.” We compute an Estimated Effective Price (EEP) using only legal signals.

## System Architecture (High-Level)
```
External Price Signals (Google Hotel Ads, OTA logged-out pages, Channel parity feeds)
           ↓
Normalization Engine (Room | Date | Meal | Cancellation parity)
           ↓
Discount Modeling (Platform discount confidence bands)
           ↓
Pricing Decision Engine (Match / Beat / Value; soft coupons only)
           ↓
Evidence & Audit Layer (Screenshots | Logs | Playwright proof)
```

## Data Sources (Allowed Only)
- ✅ Legal primary sources: Google Hotel Ads, OTA logged-out pages, Channel managers (parity + availability)
- ❌ Forbidden: Logged-in OTA accounts, bank-offer scraping, app reverse-engineering, user-specific coupons or personalized prices

## Estimated Effective Price (EEP)
- Discount bands (configurable):
  - Agoda: 8–15%
  - Goibibo: 10–18%
  - MMT: 12–20%
- Formula: `EEP = PublicPrice × (1 − DiscountFactor)`
- Each EEP stored with: source, timestamp, confidence score

## Pricing Strategy Rules
| Scenario              | Action                      |
|-----------------------|-----------------------------|
| Our price > EEP       | Apply soft coupon           |
| Our price == EEP      | Highlight value             |
| Our price < EEP       | Lock rate                   |
| Margin < threshold    | Stop discount               |

## Playwright Evidence Test Design (Mandatory)
1) Competitor Snapshot Test
   - Goal: Prove reference prices exist
   - Steps: Open Google Hotel Ads (logged-out); capture competitor prices; store screenshot + DOM extract
2) Pricing Decision Test
   - Goal: Prove logic correctness
   - Steps: Feed competitor prices; validate EEP calculation; assert decision rule applied
3) Checkout Consistency Test (CRITICAL)
   - Search price == Detail page price == Checkout price == Charged price; any mismatch → block deployment
4) Regression Guard Test
   - Re-run pricing after 15 minutes; assert price stability unless competitor changed

Playwright hard rules: `--headed` mandatory; screenshots mandatory; logs saved per run; any 4xx/5xx = FAIL.

## Pricing Decision Flow (Text Diagram)
```
START
 ↓
Fetch competitor reference prices (legal, logged-out)
 ↓
Normalize room/date/meal
 ↓
Compute EEP per platform
 ↓
Compare with our base price
 ↓
Margin OK?
  ├─ NO → Stop discount / hold price
  └─ YES → Apply decision rule (Match/Beat/Value with soft coupon only)
 ↓
Store evidence (screenshots + logs + inputs)
 ↓
Expose price to UI
 ↓
END
```

## Legal & Compliance SOP
- Allowed: Logged-out access, aggregated public data, statistical modeling, channel parity feeds
- Forbidden: Login automation, coupon harvesting, bank-offer extraction, user-specific pricing inference
- Compliance checklist (every release):
  - No authenticated scraping
  - Evidence stored
  - Pricing explainable
  - Channel parity respected
  - Playwright proof attached

## Agent-Ready Implementation Tasks (EPIC: Competitive Pricing Intelligence)
- **Sprint 1 – Foundation**: competitor_price_snapshot model; Google Hotel Ads ingestion; logged-out OTA price capture (manual first)
- **Sprint 2 – Modeling**: discount band config; EEP computation service; confidence scoring
- **Sprint 3 – Decision Engine**: pricing rule engine; margin guardrails; soft-coupon application only
- **Sprint 4 – Evidence Layer**: screenshot storage; pricing audit logs; explainability API
- **Sprint 5 – Validation**: Playwright E2E tests; checkout consistency guard; regression alerts

## Definition of Done (Strict)
A feature is DONE only if:
- Pricing decision is reproducible and explainable
- Evidence exists (screenshots + logs + inputs)
- Playwright run shows no errors (all mandatory tests pass)
- Legal checklist is passed
