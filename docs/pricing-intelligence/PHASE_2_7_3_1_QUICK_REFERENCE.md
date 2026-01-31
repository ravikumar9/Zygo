# PHASE 2.7.3.1 QUICK REFERENCE
## Pricing Safety Shadow Mode

---

## WHAT IS SHADOW MODE?

**Shadow Mode = Observation Without Blocking**

Runs all 5 safety engines, logs violations, but **never blocks prices**. Enables safe 7-14 day observation period before ENFORCE mode activation.

---

## THREE MODES EXPLAINED

| Mode | Behavior | Use Case |
|------|----------|----------|
| **SHADOW** | Run all checks → Log risks → Always allow | Observation period (default) |
| **ENFORCE** | Run all checks → Block on violations | Production enforcement |
| **OFF** | Skip all checks → Always allow | Emergency bypass or testing |

---

## HOW TO USE IN CODE

### Check Price Safety
```python
from hotels.pricing_safety_engines import PricingSafetyOrchestrator
from hotels.models import PricingSafetyConfig

config = PricingSafetyConfig.get_config()
result = PricingSafetyOrchestrator.check_price_safety(
    price=Decimal('1500.00'),
    room_type=room_type,
    config=config,
    source='manual_admin'
)

if result.is_allowed:
    # Price is allowed (or in SHADOW/OFF mode)
    publish_price()
else:
    # Price is blocked (only in ENFORCE mode)
    use_safe_fallback(result.safe_price)
```

### Track Shadow Risk Manually
```python
from hotels.pricing_safety_telemetry import PricingSafetyTelemetry

telemetry = PricingSafetyTelemetry()
telemetry.track_shadow_would_block_floor(
    room_type=room_type,
    proposed_price=Decimal('400.00'),
    floor_price=Decimal('600.00'),
    reason='Below floor',
    potential_revenue_impact=Decimal('150.00'),
    booking_count_impact=5
)
```

### Switch Modes (Admin Only)
```python
from hotels.models import PricingSafetyConfig

config = PricingSafetyConfig.get_config()

# Switch to ENFORCE after observation
config.pricing_safety_mode = 'ENFORCE'
config.save()

# Or disable all checks (emergency)
config.pricing_safety_mode = 'OFF'
config.save()
```

---

## DATABASE MODELS

### PricingSafetyConfig
```
Fields:
  pricing_safety_mode: CharField[SHADOW, ENFORCE, OFF]  (default: SHADOW)
  shadow_mode_enabled_at: DateTimeField (when mode started)
  ... other config fields ...
```

### ShadowRiskEvent
```
Fields:
  risk_category: CharField[FLOOR_RISK, ABSOLUTE_RISK, COMPETITOR_RISK, ...]
  hotel: ForeignKey(Hotel)
  room_type: ForeignKey(RoomType)
  proposed_price: Decimal
  safe_price: Decimal
  reason: TextField
  potential_revenue_impact: Decimal (nullable)
  booking_count_impact: Integer
  severity: CharField[LOW, MEDIUM, HIGH, CRITICAL]
  metadata_json: JSONField
  created_at, updated_at: auto
```

### PricingSafetyEvent
```
Added event types:
  SHADOW_FLOOR_BLOCK → Floor violation in shadow
  SHADOW_COMPETITOR_REJECT → Competitor anomaly in shadow
  SHADOW_VELOCITY_BLOCK → Velocity violation in shadow
  SHADOW_ABSOLUTE_KILL → Absolute min violation in shadow
  SHADOW_CIRCUIT_TRIP → Circuit breaker in shadow
```

---

## QUERY EXAMPLES

### Get Recent Shadow Risks
```python
from hotels.models import ShadowRiskEvent
from django.utils import timezone
from datetime import timedelta

# Last 7 days
seven_days_ago = timezone.now() - timedelta(days=7)
recent_risks = ShadowRiskEvent.objects.filter(
    created_at__gte=seven_days_ago
)

# For specific hotel
hotel_risks = recent_risks.filter(hotel=hotel)

# By severity
critical_risks = recent_risks.filter(severity='CRITICAL')

# By category
floor_risks = recent_risks.filter(risk_category='FLOOR_RISK')
```

### Aggregate Statistics
```python
# Total would-block events
total_events = ShadowRiskEvent.objects.filter(...).count()

# Revenue impact
revenue_impact = sum(
    e.potential_revenue_impact or 0 
    for e in ShadowRiskEvent.objects.filter(...)
)

# Booking impact
booking_impact = sum(
    e.booking_count_impact 
    for e in ShadowRiskEvent.objects.filter(...)
)

# Distribution by category
distribution = ShadowRiskEvent.objects.filter(...).values(
    'risk_category'
).annotate(
    count=Count('id'),
    avg_revenue=Avg('potential_revenue_impact')
)
```

### Get SHADOW_* Events
```python
from hotels.models import PricingSafetyEvent

shadow_events = PricingSafetyEvent.objects.filter(
    event_type__startswith='SHADOW_'
)

# Or specific shadow events
floor_shadows = PricingSafetyEvent.objects.filter(
    event_type='SHADOW_FLOOR_BLOCK'
)
```

---

## TELEMETRY METHODS

All fire-and-forget (never block, never raise exceptions):

```python
from hotels.pricing_safety_telemetry import PricingSafetyTelemetry

telemetry = PricingSafetyTelemetry()

# Floor violations
telemetry.track_shadow_would_block_floor(
    room_type, proposed, floor_price, reason,
    potential_revenue_impact, booking_count_impact
)

# Competitor anomalies
telemetry.track_shadow_would_block_competitor(
    room_type, competitor_price, safe_price, reason,
    potential_revenue_impact, booking_count_impact
)

# Velocity violations
telemetry.track_shadow_would_block_velocity(
    room_type, proposed, safe_price, reason,
    velocity_percent, potential_revenue_impact, booking_count_impact
)

# Absolute minimum violations
telemetry.track_shadow_would_block_absolute(
    room_type, proposed, absolute_min, reason,
    potential_revenue_impact, booking_count_impact
)

# Circuit breaker near-trips
telemetry.track_shadow_would_trip_circuit(
    room_type, reason, near_trip_percent,
    potential_revenue_impact, booking_count_impact
)
```

---

## EXECUTION FLOW (SHADOW MODE)

```
check_price_safety() called
  ↓
Is mode = OFF?
  Yes → Skip all checks, return True ✓
  No → Continue
  ↓
Is pricing automation disabled?
  Yes → Return blocked (force use fallback)
  No → Continue
  ↓
Circuit breaker tripped?
  Yes (in SHADOW) → Log event, create ShadowRiskEvent, continue
  Yes (in ENFORCE) → Return blocked
  No → Continue
  ↓
Absolute minimum check
  Violated (in SHADOW) → Log SHADOW_ABSOLUTE_KILL, continue
  Violated (in ENFORCE) → Return blocked
  OK → Continue
  ↓
Floor price check
  Violated (in SHADOW) → Log SHADOW_FLOOR_BLOCK, continue
  Violated (in ENFORCE) → Return blocked
  OK → Continue
  ↓
Competitor price check (if provided)
  Violated (in SHADOW) → Log SHADOW_COMPETITOR_REJECT, continue
  Violated (in ENFORCE) → Log and reject (no block)
  OK → Continue
  ↓
Velocity check (if previous price provided)
  Violated (in SHADOW) → Log SHADOW_VELOCITY_BLOCK, continue
  Violated (in ENFORCE) → Return blocked
  OK → Continue
  ↓
All checks done
  → Return is_allowed=True (SHADOW/OFF always allow)
  → Return result (ENFORCE blocks if any violation)
```

---

## KEY DIFFERENCES: SHADOW vs ENFORCE

### SHADOW Mode
```
check_price_safety(price=₹400, floor=₹600)
  ↓
Floor violation detected
  → Create SHADOW_FLOOR_BLOCK event
  → Create ShadowRiskEvent record
  → Continue checking
  ↓
Return: is_allowed=True ✓ (STILL ALLOWED)
```

### ENFORCE Mode
```
check_price_safety(price=₹400, floor=₹600)
  ↓
Floor violation detected
  → Create FLOOR_BLOCK event
  → Continue
  ↓
Return: is_allowed=False ✗ (BLOCKED)
  safe_price: ₹600
```

---

## ADMIN SWITCH PROCESS (SHADOW → ENFORCE)

**Step 1: Review 7-day shadow data**
```python
shadow_risks = ShadowRiskEvent.objects.filter(
    created_at__gte=timezone.now() - timedelta(days=7)
)
total_events = shadow_risks.count()
revenue_impact = sum(e.potential_revenue_impact or 0 for e in shadow_risks)
```

**Step 2: Approve switch with stats**
- "Would have blocked: {total_events} prices"
- "Estimated revenue impact: ₹{revenue_impact}"
- "Risk breakdown by category: {distribution}"

**Step 3: Enable enforcement**
```python
config = PricingSafetyConfig.get_config()
config.pricing_safety_mode = 'ENFORCE'
config.save()
```

**Step 4: Monitor blocking**
- Track FLOOR_BLOCK, COMPETITOR_REJECT, etc. events
- Monitor merchant complaints
- Be ready to switch back to SHADOW if needed

---

## TESTING

Run shadow mode tests:
```bash
pytest hotels/tests/test_shadow_mode.py -v
```

Expected: 25/25 PASSING

---

## DEFAULT CONFIGURATION

```python
PricingSafetyConfig defaults:
  pricing_safety_mode = 'SHADOW'  # Conservative default
  global_min_price = ₹100
  absolute_min_price_hard_stop = ₹50
  velocity_max_drop_percent_per_hour = 35%
  velocity_max_rise_percent_per_hour = 40%
  # ... other settings ...
```

---

## TROUBLESHOOTING

### Q: Prices not being logged in shadow mode?
A: Check:
1. `config.pricing_safety_mode == 'SHADOW'` ✓
2. Price is actually unsafe (below floor, etc.)
3. Check PricingSafetyEvent for SHADOW_* events
4. Check ShadowRiskEvent for records

### Q: Why are bookings still being accepted in ENFORCE mode?
A: check_price_safety() returns False, but booking_api needs to check this result. Make sure to:
```python
result = PricingSafetyOrchestrator.check_price_safety(...)
if not result.is_allowed:
    reject_booking()  # Not automatic!
```

### Q: How to estimate revenue impact?
A: `(proposed_price - safe_price) × booking_estimate_for_period`

---

## NEXT PHASE

Phase 2.7.3.2 will add:
- Admin dashboard for shadow metrics
- Charts: would-block counts, revenue impact, anomaly rates
- Safety mode switch button with confirmation
- Daily shadow risk report generation

---

Reference: Phase 2.7.3.1 (Shadow Mode Implementation)  
Generated: 2026-01-30  
Tests: 25/25 PASSING ✅
