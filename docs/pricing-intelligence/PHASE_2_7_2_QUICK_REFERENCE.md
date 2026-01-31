# PHASE 2.7.2 TELEMETRY HEALTH — QUICK REFERENCE

## What's New

**TelemetryIntegritySnapshot**: Daily data quality metrics  
**TelemetryHealthService**: Health monitoring engine (4 methods)  
**Admin Dashboard**: Health visualization (3 views)  
**Silent Guardrails**: CRITICAL alerts if error_rate > 5%  
**Sampling Verifier**: Validates 100 random events daily  

---

## Key Files Created/Modified

| File | Purpose | Status |
|------|---------|--------|
| `models.py` | TelemetryIntegritySnapshot model | ✅ |
| `telemetry_health_service.py` | Health service (NEW) | ✅ |
| `views_health.py` | Dashboard views (NEW) | ✅ |
| `urls_intelligence.py` | Health routes | ✅ |
| `migrations/0007_*` | Snapshot table | ✅ |
| `migrations/0008_*` | Index optimization | ✅ |
| `tests/test_telemetry_health.py` | Test suite (NEW) | ✅ |

---

## Quick Start

### 1. Check Status
```bash
python manage.py check           # Verify 0 issues
python manage.py showmigrations  # Verify all applied [X]
python manage.py test owner_agreements.tests.test_telemetry_health
```

### 2. Generate Daily Snapshot
```python
from owner_agreements.telemetry_health_service import get_telemetry_health
from django.utils import timezone

service = get_telemetry_health()
snapshot = service.calculate_daily_integrity(timezone.now().date())

print(f"Total events: {snapshot.total_events}")
print(f"Error rate: {snapshot.error_rate_percent}%")
print(f"Success rate: {snapshot.sampling_success_rate}%")
```

### 3. Check for Anomalies
```python
anomalies = service.detect_anomaly_spikes(days=7)
print(f"Volume spikes: {len(anomalies['volume_spikes'])}")
print(f"Error spikes: {len(anomalies['error_spikes'])}")
print(f"Version mismatches: {len(anomalies['version_mismatches'])}")
```

### 4. View Admin Dashboard
Navigate to: `/admin/owner-agreements/health/`

---

## Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Tests Passing | 100% | 24/24 ✅ |
| Error Rate | < 5% | Tracked |
| Sampling Success | > 99% | Tracked |
| Version Compliance | > 99% | Tracked |
| System Check | 0 issues | ✅ |
| Migrations | All applied | ✅ |

---

## Critical Methods

```python
# Generate daily snapshot (< 500ms)
snapshot = service.calculate_daily_integrity(date)

# Detect anomalies (last 7 days)
anomalies = service.detect_anomaly_spikes(days=7)

# Check pipeline activity
activity = service.detect_zero_activity(hours=24)

# Check version compliance
versions = service.detect_version_mismatch()
```

---

## Admin URLs

```
/admin/owner-agreements/health/              # Main dashboard
/admin/owner-agreements/health/snapshots/    # Snapshot history
/admin/owner-agreements/api/health/summary/  # JSON metrics
```

---

## What Gets Monitored

- Event volume (daily total, trend)
- Error rate (missing critical fields)
- Version tagging compliance (EXPLANATION_ENGINE_VERSION)
- Invalid signal references
- Insert latency
- Anomaly detection (volume, error, version)

---

## Silent Guardrails

**IF error_rate > 5%**: Log CRITICAL alert (no exception)  
**IF missing_version > 1%**: Log WARNING (no exception)  
**IF volume deviates > 30%**: Log INFO (no exception)  

Alert Format: Admin logs only, never blocks UI

---

## Hard Rules Enforced

✅ Never blocks production  
✅ Never mutates telemetry data  
✅ Never slows inserts (< 500ms)  
✅ Silent exceptions (always safe defaults)  
✅ Admin-only access (@staff_member_required)  
✅ Zero breaking changes  
✅ Zero UI impact  

---

## Next Steps

1. ✅ Run tests: `python manage.py test owner_agreements.tests.test_telemetry_health`
2. ✅ Verify migrations: `python manage.py showmigrations owner_agreements`
3. ✅ Check dashboard: Navigate to `/admin/owner-agreements/health/`
4. ⏳ Set up daily job: Schedule `calculate_daily_integrity()` to run daily
5. ⏳ Monitor metrics: Review daily snapshots in admin dashboard
6. ⏳ Phase 2.8: Begin Owner Soft Intelligence work

---

**Status**: 🟢 Production Ready  
**Tests**: ✅ 24/24 Passing  
**Deployment Risk**: 🟢 Very Low  
**Breaking Changes**: None
