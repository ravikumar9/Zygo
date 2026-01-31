# Phase 2.7.3.2: Revenue Risk Intelligence Dashboard

## Quick Start

```bash
# 1. Verify database migrations are applied
python manage.py migrate hotels

# 2. Check system is ready
python manage.py check

# 3. Access the dashboard
# Admin user: http://localhost:8000/admin/
# API: GET http://localhost:8000/hotels/api/admin/dashboard/summary/
```

## What This Phase Does

Provides executives and admins with comprehensive visibility into pricing safety metrics and enables data-driven decisions about transitioning from shadow mode to enforcement mode.

### Key Features

- 📊 **Executive Risk Summary**: 7/30-day metrics showing revenue at risk, bookings, occupancy, anomalies
- 🎯 **Safety Confidence Score**: Composite metric (0-100) determining enforcement readiness
- 🔥 **Risk Heatmap**: Aggregates anomalies by hotel, city, room type, or booking channel
- 🎪 **Enforcement Simulation**: What-if analysis showing impact before enabling enforcement
- 🎛️ **Enforcement Switch**: Admin-controlled mode changes with confirmation and audit trail

## Architecture Overview

```
Shadow Mode → Collects ShadowModeEvents → 
SafetyConfidenceScore (calculated from 3 components) →
If Score >= 85%, Admin can switch to ENFORCEMENT mode
```

## 7 API Endpoints

All require admin authentication (`is_staff=True`)

1. **GET /hotels/api/admin/dashboard/summary/**
   - Returns: Revenue at risk, booking metrics, anomalies
   - Params: `period` (7 or 30 days)

2. **GET /hotels/api/admin/dashboard/confidence/**
   - Returns: Confidence score (0-100) and enforcement readiness
   - Calculation: 40% data quality + 35% pattern recognition + 25% risk coverage

3. **GET /hotels/api/admin/dashboard/heatmap/**
   - Returns: Risk aggregation by dimension
   - Params: `dimension` (hotel, city, room_type, channel), `period`

4. **GET /hotels/api/admin/dashboard/simulation/**
   - Returns: What-if impact analysis
   - Shows: Revenue protected, bookings affected, anomalies prevented

5. **GET /hotels/api/admin/dashboard/current-mode/**
   - Returns: Current enforcement mode and last change info

6. **GET /hotels/api/admin/dashboard/full-status/**
   - Returns: All dashboard data combined

7. **POST /hotels/api/admin/dashboard/switch-mode/**
   - Action: Enable/disable enforcement
   - Requires: `confirm=true`, `action` (enable/disable), `reason`
   - Validates: Confidence >= 85% for ENFORCEMENT

## Database Models

### ShadowModeEvent
Tracks anomalies detected without enforcement.
```
- room_type (FK)
- booking (FK, optional)
- shadow_price, actual_price
- anomaly_type, anomaly_severity
- confidence_score
- detection_source
```

### SafetyConfidenceScore
System confidence in enforcement capability.
```
- overall_score (0-100)
- data_quality_score, pattern_recognition_score, risk_coverage_score
- is_enforcement_ready (>= 85%)
- recommendation text
```

### EnforcementMode
Audit trail of mode changes.
```
- mode (SHADOW, ENFORCEMENT, OFF)
- changed_by (FK to User)
- reason
- timestamp
```

### PricingException
Pricing rule violations and exceptions.
```
- room_type (FK)
- exception_type (margin_violation, etc.)
- violation_value, threshold_value
- severity (low, medium, high)
- is_resolved
```

## Hard Rules

✅ **Dashboard is READ-ONLY**
- No pricing mutations through dashboard
- Only switch-mode endpoint allows POST

✅ **Explicit Mode Switching**
- Requires admin authentication
- Requires `confirm=true`
- Requires reason text
- Audit logged

✅ **Confidence Threshold**
- Cannot enable ENFORCEMENT if score < 85%
- Calculation: 40% data + 35% pattern + 25% coverage

✅ **No Data Exposure**
- Aggregated data only
- No customer PII
- No owner details

✅ **Audit Trail**
- All mode changes logged
- Admin user recorded
- Timestamp recorded
- Reason recorded

## Example Workflow

```
Day 1: Admin enables shadow mode (Phase 2.7.3.1)
  → System starts collecting ShadowModeEvent records

Day 7: Check confidence score
  GET /api/admin/dashboard/confidence/
  → Returns: score = 87% (READY), data_quality = 85%, pattern = 90%

Day 7: Preview impact
  GET /api/admin/dashboard/simulation/
  → Shows: 3 anomalies prevented, ₹625 revenue protected

Day 7: Enable enforcement
  POST /api/admin/dashboard/switch-mode/
  {
    "action": "enable",
    "confirm": true,
    "reason": "7-day observation complete"
  }
  → System switches to enforcement mode

Day 8+: Monitor in enforcement mode
  → Can switch back to SHADOW anytime if needed
```

## Admin Interface

Access via Django admin: http://localhost:8000/admin/

New sections:
- **Shadow Mode Events**: Shows anomalies detected (read-only)
- **Pricing Exceptions**: Tracks rule violations (editable: is_resolved)
- **Safety Confidence Scores**: Historical score calculations (read-only)
- **Enforcement Mode**: Audit log of mode changes (read-only)

## Testing

Run tests:
```bash
pytest tests/test_dashboard_api.py -v
```

Test coverage includes:
- Admin access enforcement
- Confidence score calculation
- Heatmap aggregation
- Enforcement switch with confirmation
- Read-only constraints
- Model creation and queries

## Documentation Files

1. **DASHBOARD_API_DOCUMENTATION.md**
   - Complete API reference
   - Request/response examples
   - Architecture explanation
   - Hard rules and constraints

2. **DASHBOARD_QUICK_REFERENCE.md**
   - Quick start guide
   - Common use cases
   - curl examples
   - Troubleshooting

3. **DASHBOARD_IMPLEMENTATION_CHECKLIST.md**
   - Implementation status
   - Deployment steps
   - Success metrics

4. **PHASE_2_7_3_2_SUMMARY.md**
   - Comprehensive summary
   - All components listed
   - Test results
   - Performance info

## Performance

- Summary endpoint: < 1 second
- Confidence endpoint: < 500ms
- Heatmap endpoint: < 2-3 seconds
- Full status: < 5 seconds

## Security

- Admin authentication required on all endpoints
- Mode switch requires explicit confirmation
- Comprehensive audit trail
- No customer PII exposed
- No CSRF/XSS vulnerabilities

## Files Added

```
hotels/
  ├── dashboard_api.py (7 endpoints)
  ├── dashboard_intelligence.py (4 intelligence classes)
  ├── migrations/0029_*.py (4 new models)
  ├── models.py (+4 models)
  ├── urls.py (+7 routes)
  └── admin.py (+4 admin registrations)

tests/
  └── test_dashboard_api.py (13 test classes)

Documentation/
  ├── DASHBOARD_API_DOCUMENTATION.md
  ├── DASHBOARD_QUICK_REFERENCE.md
  ├── DASHBOARD_IMPLEMENTATION_CHECKLIST.md
  └── PHASE_2_7_3_2_SUMMARY.md
```

## Next Steps

1. **Phase 2.7.4**: Use confidence score in enforcement
2. **Phase 2.7.5**: Build UI dashboard with charts
3. **Phase 2.7.6**: Add alerting (email/Slack)

## Support

For questions or issues:
1. Check the quick reference guide
2. Review API documentation
3. Check test cases for examples
4. Review admin interface

---

**Status**: ✅ COMPLETE
**Last Updated**: 2026-02-10
**Ready for Production**: YES
