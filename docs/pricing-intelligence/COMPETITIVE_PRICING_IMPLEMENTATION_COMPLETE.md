# Competitive Pricing Intelligence v1 - Implementation Complete

**Date:** January 26, 2026  
**Status:** ✅ **READY FOR MIGRATION & PLAYWRIGHT EXECUTION**

---

## Executive Summary

Implemented a **legal, evidence-backed, guardrailed competitive pricing system** with four locked-in principles:

1. ✅ **EEP (Estimated Effective Price) model** — First-class DB persistence with TTL, confidence scoring, and reliability checks
2. ✅ **Discount band configuration** — DB-backed (not hardcoded), editable per platform (Agoda, MMT, Goibibo)
3. ✅ **Auto soft coupon generator** — Ephemeral `AUTO-SAVE-<hash>` coupons, ₹500 flat cap, 15-min expiry, guardrails
4. ✅ **Playwright evidence gates** — 4 mandatory headed tests + CI deployment blocker

---

## Data Models Implemented

### 1. **CompetitorPriceSnapshot** (already existing, enhanced)
- Captures logged-out competitor prices with immutable evidence
- Fields: `source_name`, `source_url`, `total_price`, `evidence_url`, `source_requires_login` (validation: MUST be False)

### 2. **CompetitorDiscountBandConfig** ⭐ NEW
DB-backed configuration (not hardcoded):
- `platform` (Agoda, MMT, Goibibo)
- `min_percent`, `max_percent` — Discount band range
- `confidence_weight` — For multi-source aggregation
- `enabled` — Toggle per platform
- `updated_by`, `updated_at` — Audit trail

**Formula:** EEP = PublicPrice × (1 − DiscountFactor)  
**Example:** Agoda 8–15% band → midpoint 11.5%

### 3. **EstimatedEffectivePrice** ⭐ NEW
First-class pricing truth model:
- `snapshot` (FK) — Source competitor snapshot
- `platform` (string) — Competitor identifier
- `public_price` — Original price from snapshot
- `discount_band_min/max` — Applied band
- `discount_factor_used` — Actual % applied
- `eep_price` — Computed EEP
- `confidence_score` (0–100) — Reliability (<50% = unreliable)
- `ttl_expires_at` — Validity window (default 30 min)
- `is_expired` (property) — Boolean validity check
- `is_reliable` (property) — Confidence ≥ 50 AND not expired

### 4. **PricingDecisionAudit** (enhanced)
Now tracks:
- `eep` (FK) — Link to EstimatedEffectivePrice
- `margin_before_percent` — Margin before decision
- `margin_after_percent` — Margin after decision
- `playwright_run_id` — Evidence linkage (string, required for publish)
- `coupon_generated` (FK) — Link to auto-generated PromoCode
- `publish_block_reason` — "LOGGED_IN_CAPTURE" | "MISSING_EVIDENCE" | "EEP_EXPIRED" | "UNRELIABLE_EEP" | "COOLDOWN_ACTIVE"

---

## Services Implemented

### 1. **EEPComputationService** (`hotels/eep_service.py`)
```python
eep = EEPComputationService.compute_eep(
    snapshot=snapshot,
    platform='agoda',
    discount_factor=None,  # Defaults to band midpoint
    ttl_minutes=30,
    confidence_score=Decimal('75')
)
```
- Validates band config exists and is enabled
- Computes midpoint if factor not provided
- Stores with TTL and confidence
- Returns saved EstimatedEffectivePrice instance

### 2. **AutoCouponGenerator** (`hotels/auto_coupon_generator.py`)
```python
coupon_value = AutoCouponGenerator.compute_coupon_value(
    our_price=Decimal('5500'),
    eep_price=Decimal('4425'),
    margin_floor_percent=Decimal('8')
)

if coupon_value:
    coupon = AutoCouponGenerator.create_auto_coupon(
        hotel_id=hotel.id,
        our_price=Decimal('5500'),
        eep=eep,
        margin_floor_percent=Decimal('8')
    )
    AutoCouponGenerator.link_coupon_to_audit(audit, coupon)
```
**Guardrails:**
- No coupon if gap ≤ 0 (our price ≤ EEP)
- Soft coupon only (`flat` type)
- Flat cap: ₹500
- Percentage cap: 5%
- Margin safe cap: gap − (our_price × margin_floor%)
- Coupon value = min(all caps)
- Non-stackable (max_discount_amount = coupon_value)
- 15-min expiry

### 3. **PricingDecisionEngine** (enhanced) (`hotels/pricing_decision_engine.py`)
```python
result, audit = engine.decide_and_record(
    hotel=hotel,
    baseline_price=Decimal('5500'),
    snapshot=snapshot,
    eep=eep,
    triggered_by=user
)
```
**Guardrails enforced:**
- ❌ Logged-in captures → BLOCKED (publish_block_reason='LOGGED_IN_CAPTURE')
- ❌ Missing evidence → BLOCKED (publish_block_reason='MISSING_EVIDENCE')
- ❌ EEP expired → BLOCKED (publish_block_reason='EEP_EXPIRED')
- ❌ EEP confidence < 50% → BLOCKED (publish_block_reason='UNRELIABLE_EEP')
- ❌ Cooldown active → BLOCKED (publish_block_reason='COOLDOWN_ACTIVE')
- ❌ Margin < floor → HOLD (preserve floor)

**Decisions:**
- MATCH — Our price ≈ EEP
- UNDERCUT — Cut to EEP (within guardrails)
- HOLD — Protect margin / competitor too cheap
- REJECT — No reliable EEP
- BLOCKED — Legal/compliance gate failed

---

## Database Migrations

### Migration: `0024_eep_and_discount_band_config.py`
Creates:
- `CompetitorDiscountBandConfig` table
- `EstimatedEffectivePrice` table
- Adds FK fields to `PricingDecisionAudit`:
  - `eep` (FK)
  - `margin_before_percent`, `margin_after_percent`
  - `playwright_run_id`
  - `coupon_generated` (FK to PromoCode)
- Removes old `margin_percent` field (replaced by before/after split)
- Adds indexes on snapshot/platform, ttl_expires_at, confidence_score

**To apply:**
```bash
python manage.py migrate hotels 0024_eep_and_discount_band_config
```

---

## Playwright Evidence Suite

### Directory: `tests/e2e/competitive_pricing/`

#### Test 1: `competitor_snapshot.spec.ts`
**Goal:** Prove reference prices exist (logged-out)
- Opens Google Hotel Ads (logged-out)
- Captures competitor prices (Agoda, etc.)
- Stores screenshots + DOM dumps
- Verifies no auth required (401/403 = FAIL)
- **Artifacts:** `artifacts/competitive_pricing/screenshots/`, `dom_dumps/`

#### Test 2: `pricing_decision.spec.ts`
**Goal:** Prove decision logic is correct
- Computes EEP from band (midpoint)
- Tests UNDERCUT decision (margin safe)
- Tests HOLD decision (margin floor breach)
- Tests MATCH decision (gap negligible)
- Tests REJECT decision (confidence < 50%)
- Logs audit trail with full inputs/outputs
- **Artifacts:** `artifacts/competitive_pricing/decision_logs/`

#### Test 3: `checkout_consistency.spec.ts` ⚠️ **CRITICAL**
**Goal:** Search ≈ Detail ≈ Confirm ≈ Payment (±1% variance)
- Captures prices at 4 stages
- Validates no mismatch across journey
- **Any mismatch = HARD FAIL (blocks deployment)**
- Saves consistency report
- **Artifacts:** `artifacts/competitive_pricing/checkout_consistency/`

#### Test 4: `regression_stability.spec.ts`
**Goal:** Price unchanged unless competitor changed
- Runs pricing at T0
- Waits 15 sec (simulated 15 min)
- Re-runs pricing
- Asserts stable OR competitor_signal_changed
- Logs all changes with reasons
- **Artifacts:** `artifacts/competitive_pricing/regression_stability/`

**Execution (mandatory `--headed`):**
```bash
npx playwright test tests/e2e/competitive_pricing --headed
```

---

## CI Deployment Gate

### Script: `ci_deployment_gate.py`

**Hard blockers (FAIL = no deploy):**
1. ❌ Any audit with `publish_block_reason` NOT NULL
2. ❌ Any publishable audit missing `playwright_run_id`
3. ❌ Active audit using expired EEP
4. ❌ Active audit using unreliable EEP (confidence < 50%)
5. ❌ Publishable audit missing `evidence_url`
6. ❌ Any snapshot with `source_requires_login=True`
7. ❌ Non-soft coupon generated (not `AUTO-SAVE-*`)

**Warnings (logged, not blocking):**
- Audits with margin < 8% (but blocked)

**Artifacts checked:**
- `artifacts/competitive_pricing/screenshots/` (populated?)
- `artifacts/competitive_pricing/dom_dumps/` (populated?)
- `artifacts/competitive_pricing/decision_logs/` (populated?)

**Usage:**
```bash
python ci_deployment_gate.py
```
**Exit codes:**
- 0 = PASS (deploy OK)
- 1 = FAIL (do not deploy)

---

## Next Steps (To Wire Into Booking Flow)

### 1. Pricing API Enhancement (Implement in bookings/views.py)
```python
# In booking confirmation calculate_pricing():
# 1. Fetch latest EEP for hotel + dates
# 2. Call PricingDecisionEngine.decide_and_record()
# 3. Check audit.publish_block_reason
# 4. If blocked: return {publish_blocked: true, reason: ...}
# 5. If not blocked: try AutoCouponGenerator.create_auto_coupon()
# 6. Return coupon in pricing response
```

### 2. UI Rendering Gate
```python
# In template: Only render price if NOT blocked
if not pricing.get('publish_blocked'):
    # Show price + auto coupon badge "Smart Saving"
else:
    # Show error: "Price calculation pending evidence"
```

### 3. Booking Creation Flow
```python
# Before confirm: Audit exists with playwright_run_id
# If missing: block booking ("Evidence required")
```

### 4. Admin Panel
```python
# Add admin views for:
# - CompetitorDiscountBandConfig (CRUD + toggle enabled)
# - EstimatedEffectivePrice (view, filter by TTL)
# - PricingDecisionAudit (view, filter by publish_block_reason)
```

### 5. Management Commands
```bash
# Seed initial discount band configs
python manage.py seed_discount_bands

# Cleanup expired EEPs
python manage.py cleanup_expired_eeps --older_than=60

# Run Playwright suite
npx playwright test tests/e2e/competitive_pricing --headed

# Run CI gate
python ci_deployment_gate.py
```

---

## Legal Compliance Checklist (Enforced)

✅ **Logged-out only** — snapshot.source_requires_login MUST be False  
✅ **Evidence mandatory** — snapshot.evidence_url required; blocks publish if missing  
✅ **Margin preserved** — margin_floor_percent ≥ 8% enforced  
✅ **Soft coupon only** — AUTO-SAVE-* prefix, no hard discount stacking  
✅ **Explainable** — Every decision logged in PricingDecisionAudit with reasoning  
✅ **Reproducible** — EEP computation deterministic; EEP model auditable  
✅ **Playwright proof** — playwright_run_id required for publish  

---

## Architecture Diagram (Locked)

```
Logged-Out Competitor Price
          ↓
CompetitorPriceSnapshot (evidence_url required)
          ↓
CompetitorDiscountBandConfig (DB-backed)
          ↓
EstimatedEffectivePrice (EEP = PublicPrice × (1 − DiscountFactor))
          ↓
PricingDecisionEngine (margin floor, cooldown, EEP reliability checks)
          ↓
PricingDecisionAudit (margin_before/after, playwright_run_id, publish_block_reason)
          ↓
AutoCouponGenerator (guardrailed coupon creation)
          ↓
PromoCode (AUTO-SAVE-* soft coupon, 15 min expiry)
          ↓
Booking UI (render price OR error if publish_blocked=true)
```

---

## Testing Checklist

- [ ] Run migrations: `python manage.py migrate hotels 0024_*`
- [ ] Seed discount bands (admin or management command)
- [ ] Create test CompetitorPriceSnapshot (logged-out only)
- [ ] Compute EEP via EEPComputationService
- [ ] Run PricingDecisionEngine.decide_and_record()
- [ ] Verify PricingDecisionAudit created with all fields
- [ ] Generate AUTO-SAVE coupon via AutoCouponGenerator
- [ ] Run Playwright suite: `npx playwright test tests/e2e/competitive_pricing --headed`
- [ ] Run CI gate: `python ci_deployment_gate.py` (should PASS)
- [ ] Verify evidence artifacts in `artifacts/competitive_pricing/`

---

## Key Files

| File | Purpose |
|------|---------|
| `hotels/models.py` | CompetitorDiscountBandConfig, EstimatedEffectivePrice, PricingDecisionAudit (enhanced) |
| `hotels/migrations/0024_*` | DB schema for new models + field additions |
| `hotels/eep_service.py` | EEP computation (formula, TTL, confidence) |
| `hotels/auto_coupon_generator.py` | Soft coupon generation with guardrails |
| `hotels/pricing_decision_engine.py` | Decision logic with legal guards |
| `tests/e2e/competitive_pricing/competitor_snapshot.spec.ts` | Test 1: Evidence capture |
| `tests/e2e/competitive_pricing/pricing_decision.spec.ts` | Test 2: Decision correctness |
| `tests/e2e/competitive_pricing/checkout_consistency.spec.ts` | Test 3: Price journey consistency |
| `tests/e2e/competitive_pricing/regression_stability.spec.ts` | Test 4: Stability over time |
| `ci_deployment_gate.py` | CI blocker for non-compliant prices |

---

## Definition of Done ✅

- [x] Models: EEP + discount band config + audit enrichment
- [x] Services: EEP computation, coupon generation, decision engine
- [x] Migrations: All schema changes
- [x] Playwright tests: 4 mandatory headed suites with evidence capture
- [x] CI gate: Deployment blocker with hard checks
- [x] Legal guardrails: Logged-out, evidence-gated, margin-safe, soft-coupon-only
- [x] Audit trail: All decisions logged with before/after margins + playwright_run_id

**SYSTEM IS READY FOR BOOKING FLOW INTEGRATION & E2E VALIDATION** 🚀

---

## Non-Negotiable Rules (Final)

🔒 **No price lives without evidence.**  
🔒 **No evidence without Playwright proof.**  
🔒 **No publish without clean audit.**  
🔒 **No deploy without CI gate passing.**  
🔒 **No margin below floor.**  
🔒 **No hard coupons, only soft AUTO-SAVE.**  
🔒 **No logged-in scraping, ever.**

---

*Last updated: January 26, 2026*
