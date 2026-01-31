# PHASE 2.7.3 — Quick Reference Guide

## 🚀 What Was Built

**Revenue Protection & Pricing Safety Layer** — Server-side fail-safe pricing guards

**Purpose**: Protect against external failures, internal failures, and market manipulation that could cause negative margin bookings or price collapse.

---

## 📦 Core Components

### Models (3)
1. **PricingSafetyConfig** — Singleton configuration (floors, thresholds, circuit breaker settings)
2. **PricingCircuitState** — Circuit breaker state tracking (per-room or global)
3. **PricingSafetyEvent** — Append-only audit log (all safety actions)

### RoomType Extensions (3 new fields)
- `cost_price` — Supplier/cost price for floor calculations
- `min_margin_percent` — Minimum profit margin % (overrides global)
- `min_safe_price` — Absolute minimum safe price (highest priority)

### Safety Engines (5)
1. **PricingFloorEngine** — Never sell below cost + minimum margin
2. **AbsoluteKillGuard** — Never allow ANY price below hard stop (₹50 default)
3. **CompetitorPriceSanityEngine** — Reject ₹0, >95% drops, manipulation
4. **PriceVelocityGuard** — Block rapid changes (>35% drop/hr, >40% rise/hr)
5. **PricingCircuitBreaker** — Trip on 5 anomalies in 10 minutes

### Orchestrator
**PricingSafetyOrchestrator** — Runs all safety checks in order, returns first failure or success

### Integrations (2)
1. **PricePublishmentGate** — Pre-check before any price publication
2. **BookingSafetyGate** — Final check before booking creation

### Telemetry
**PricingSafetyTelemetry** — Fire-and-forget event tracking (never blocks pricing)

---

## 🎯 Success Metrics

```
✅ Zero negative margin bookings
✅ Zero price collapse from bad feeds
✅ Booking price always validated
✅ Safe fallback always exists
✅ 33 tests passing (100%)
```

---

## 🛡️ Protection Scenarios

| Threat | Guard | Action |
|--------|-------|--------|
| Competitor ₹0 | CompetitorSanity | Reject → Use baseline |
| Competitor 99% drop | CompetitorSanity | Reject → Use baseline |
| Price below cost | FloorEngine | Block → Use floor |
| Price < ₹50 | AbsoluteKillGuard | HARD BLOCK |
| Rapid price changes | VelocityGuard | Block → Use previous |
| 5 anomalies/10min | CircuitBreaker | Trip → Use fallback |
| Admin disables safety | KillSwitch | Block → Use fallback |
| Admin typo (₹10 vs ₹1000) | FloorEngine | Block → Use floor |
| Cost price bug (₹1) | AbsoluteKillGuard | Block → Use absolute min |
| Currency API failure | AbsoluteKillGuard | Block → Use absolute min |

---

## 📊 Usage Examples

### Check Price Safety
```python
from hotels.pricing_safety_engines import PricingSafetyOrchestrator
from hotels.models import PricingSafetyConfig, RoomType
from decimal import Decimal

room = RoomType.objects.get(id=123)
config = PricingSafetyConfig.get_config()

result = PricingSafetyOrchestrator.check_price_safety(
    price=Decimal('800.00'),
    room_type=room,
    config=config,
    competitor_price=Decimal('750.00'),  # Optional
    source="admin_manual"
)

if result.is_allowed:
    # Price is safe
    print(f"✅ Price allowed: {result.reason}")
else:
    # Price blocked
    print(f"❌ Price blocked: {result.reason}")
    print(f"Safe fallback: {result.safe_price}")
```

### Get Singleton Config
```python
from hotels.models import PricingSafetyConfig

config = PricingSafetyConfig.get_config()  # Auto-creates if missing
print(f"Absolute minimum: {config.absolute_min_price_hard_stop}")
print(f"Automation enabled: {config.pricing_automation_enabled}")
```

### Query Safety Events
```python
from hotels.models import PricingSafetyEvent

# Recent blocks
blocks = PricingSafetyEvent.objects.filter(
    event_type='FLOOR_BLOCK'
).order_by('-created_at')[:10]

for event in blocks:
    print(f"{event.created_at}: {event.reason}")
    print(f"  Observed: {event.observed_price}, Floor: {event.floor_price}")
```

### Check Circuit Breaker Status
```python
from hotels.models import PricingCircuitState, RoomType

room = RoomType.objects.get(id=123)
circuit = PricingCircuitState.objects.filter(
    room_type=room,
    is_tripped=True
).first()

if circuit:
    print(f"⚠️ Circuit tripped: {circuit.reason}")
    print(f"Fallback price: {circuit.safe_fallback_price}")
```

### Reset Circuit Breaker
```python
from hotels.pricing_safety_engines import PricingCircuitBreaker

success = PricingCircuitBreaker.reset_circuit(
    room_type=room,
    admin_user=request.user  # Optional
)

if success:
    print("✅ Circuit reset")
```

---

## 🔧 Configuration

### Default Values (PricingSafetyConfig)
```
global_min_price: ₹100
absolute_min_price_hard_stop: ₹50
competitor_drop_threshold_percent: 85%
competitor_hard_reject_percent: 95%
competitor_floor_multiplier: 0.65x
circuit_breaker_window_minutes: 10
circuit_breaker_trigger_count: 5
velocity_max_drop_percent_per_hour: 35%
velocity_max_rise_percent_per_hour: 40%
pricing_automation_enabled: True
```

### Adjusting Thresholds
```python
config = PricingSafetyConfig.get_config()
config.absolute_min_price_hard_stop = Decimal('100.00')  # Increase to ₹100
config.competitor_hard_reject_percent = Decimal('90.00')  # Stricter (90% vs 95%)
config.circuit_breaker_trigger_count = 3  # More sensitive (3 vs 5)
config.save()
```

### Admin Kill Switch
```python
config = PricingSafetyConfig.get_config()
config.pricing_automation_enabled = False  # Disable all automation
config.notes = "Emergency stop during incident investigation"
config.last_modified_by = request.user
config.save()

# All pricing will now use safe fallback prices only
```

---

## 🧪 Testing

```bash
# Run Phase 2.7.3 test suite
python manage.py test hotels.tests.test_pricing_safety_layer

# Expected output:
# Ran 33 tests in 0.1s
# OK
```

---

## 🚨 Monitoring

### Key Metrics to Watch

**1. Floor Blocks**
```python
from hotels.models import PricingSafetyEvent
from datetime import timedelta
from django.utils import timezone

cutoff = timezone.now() - timedelta(hours=24)
floor_blocks = PricingSafetyEvent.objects.filter(
    event_type='FLOOR_BLOCK',
    created_at__gte=cutoff
).count()

print(f"Floor blocks (24h): {floor_blocks}")
# Alert if > 10% of pricing attempts
```

**2. Circuit Breaker Trips**
```python
circuit_trips = PricingSafetyEvent.objects.filter(
    event_type='CIRCUIT_TRIP',
    created_at__gte=cutoff
).count()

print(f"Circuit trips (24h): {circuit_trips}")
# Alert if > 0 (investigate pricing algorithm)
```

**3. Absolute Kill Blocks**
```python
absolute_kills = PricingSafetyEvent.objects.filter(
    event_type='ABSOLUTE_KILL_BLOCK',
    created_at__gte=cutoff
).count()

print(f"Absolute kills (24h): {absolute_kills}")
# Alert if > 0 (CRITICAL — investigate immediately)
```

**4. Competitor Rejections**
```python
competitor_rejects = PricingSafetyEvent.objects.filter(
    event_type='COMPETITOR_REJECT',
    created_at__gte=cutoff
).count()

print(f"Competitor rejects (24h): {competitor_rejects}")
# Alert if > 20% of competitor prices
```

---

## 📁 File Locations

```
hotels/models.py
  └─ PricingSafetyConfig, PricingCircuitState, PricingSafetyEvent
  └─ RoomType (cost_price, min_margin_percent, min_safe_price)

hotels/pricing_safety_engines.py
  └─ PricingFloorEngine, AbsoluteKillGuard, CompetitorPriceSanityEngine
  └─ PriceVelocityGuard, PricingCircuitBreaker
  └─ PricingSafetyOrchestrator, PricingSafetyResult

hotels/pricing_safety_telemetry.py
  └─ PricingSafetyTelemetry (fire-and-forget event tracking)

hotels/price_publication_gate.py
  └─ PricePublishmentGate (integration point)

bookings/booking_api.py
  └─ create_hotel_booking (booking safety gate integration)

hotels/tests/test_pricing_safety_layer.py
  └─ 33 comprehensive tests

hotels/migrations/0027_pricing_safety_layer.py
  └─ Database migration
```

---

## 🎓 Design Principles

1. **Fail-Safe**: Every check has a safe fallback (never crash)
2. **Server-Side**: No client-side bypass possible
3. **Defense-in-Depth**: Multiple layers (floor → absolute → circuit)
4. **Append-Only**: All safety actions logged (immutable audit trail)
5. **Non-Blocking**: Telemetry failures never block pricing
6. **Zero UI Impact**: Server-side enforcement only
7. **Backward Compatible**: New fields nullable, no breaking changes

---

## ✅ Verification Checklist

```
✅ System check: 0 issues
✅ Migration applied: 0027_pricing_safety_layer
✅ Tests passing: 33/33 (100%)
✅ Config created: PricingSafetyConfig.get_config()
✅ Gate integration: PricePublishmentGate calls orchestrator
✅ Booking integration: create_hotel_booking() checks safety
✅ Telemetry: PricingSafetyEvent table populated
✅ Circuit breaker: Trips on 5 anomalies
✅ Floor enforcement: Blocks prices below floor
✅ Absolute minimum: Blocks prices below ₹50
```

---

## 🔗 Related Phases

- **Phase 2.7.1**: Intelligence Telemetry Layer (22 tests, 100% passing)
- **Phase 2.7.2**: Telemetry Health & Data Quality (24 tests, 100% passing)
- **Phase 2.7.3**: Revenue Protection & Pricing Safety (33 tests, 100% passing) ✅ **YOU ARE HERE**
- **Phase 2.8**: Owner Soft Intelligence (Next)

---

**Last Updated**: January 30, 2026  
**Status**: Production Ready  
**Contact**: See PHASE_2_7_3_COMPLETION_SIGN_OFF.md for full details
