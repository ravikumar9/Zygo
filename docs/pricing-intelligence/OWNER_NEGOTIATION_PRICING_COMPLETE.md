# OWNER NEGOTIATION & PREMIUM PRICING CONTROL — PHASE 2.7.3.5 ✅

**Status**: PRODUCTION READY (FAST SPRINT)  
**Scope**: Negotiation-only intelligence for premium listings + strategy enforcement  
**Guarantees**: No auto price changes • Owner approval only • Floor protected

---

## ✅ WHAT SHIPPED

### 1) Pricing Strategy Flag (Hotel-level)
- **Field**: `Hotel.pricing_strategy`
- Values:
  - `SMART_NUDGE` (default for 1–3★, homestay, villa)
  - `NEGOTIATION_ONLY` (default for 4–5★ premium)
- **Enforced** in `OwnerPriceNudgeService` (premium listings never receive nudges)

### 2) OwnerNegotiationService (NEW)
- **Opportunity framing only** (no discounts suggested)
- **Triggers**: competitor pressure, soft demand, inventory availability
- **Logs** all actions via `PricingSafetyEvent`

Example output:
```json
{
  "should_notify": true,
  "context": {
    "competitor_avg_price": 8200,
    "current_price": 9000,
    "demand_trend": "SOFT",
    "inventory_available": 5
  },
  "suggested_action": "REVIEW_NEGOTIATION",
  "confidence_score": 75,
  "reasoning": "Competitive pressure detected • Demand soft • Inventory available: 5 • Floor protected at ₹7200"
}
```

### 3) Required APIs
- **GET** `/api/owner/negotiation/opportunity/<hotel_id>/`
- **POST** `/api/owner/negotiation/propose/`
- **POST** `/api/owner/negotiation/respond/`
- **GET** `/api/admin/negotiation/active/`

### 4) Event-Sourced Logging (No new tables)
`PricingSafetyEvent.EVENT_TYPES` extended with:
- `OWNER_NEGOTIATION_OPPORTUNITY`
- `OWNER_NEGOTIATION_PROPOSED`
- `OWNER_NEGOTIATION_COUNTERED`
- `OWNER_NEGOTIATION_ACCEPTED`
- `OWNER_NEGOTIATION_REJECTED`
- `OWNER_INCENTIVE_GRANTED`

### 5) Incentive Model (Event-driven)
- Calculates **revenue_generated** + **commission_earned**
- Logs `OWNER_INCENTIVE_GRANTED` when thresholds met
- No manual accounting logic

---

## 🔐 SAFETY & BRAND RULES ENFORCED

✅ 4★/5★ → Negotiation-only (no nudges)  
✅ No automatic price drops  
✅ Floor protection enforced on proposals & counters  
✅ Private, platform-only rates only  
✅ All actions event-logged  

---

## 🧪 TESTS ADDED

- ✅ Pricing strategy enforcement
- ✅ No auto price change
- ✅ Floor protection
- ✅ Negotiation event logging

---

## FILES TO REVIEW

- `hotels/models.py` (pricing strategy)
- `hotels/services/owner_negotiation_service.py`
- `hotels/dashboard_api.py` (new endpoints)
- `hotels/urls.py` (routes)
- `tests/test_owner_negotiation.py`
- `hotels/migrations/0030_hotel_pricing_strategy.py`

---

## ✅ READY TO MERGE

This phase meets all constraints:
- No architecture drift
- No auto pricing
- No breaking changes
- Event-sourced only
- SafeQuery everywhere

**Recommendation**: Merge to main.
