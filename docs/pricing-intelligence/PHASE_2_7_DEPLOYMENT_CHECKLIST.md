# Phase 2.7 Deployment Checklist

**Phase**: 2.7 — Admin Decision Assist  
**Deployment Date**: {{ deployment_date }}  
**Deployed By**: {{ deployer_name }}  
**Environment**: {{ environment }} (Production/Staging/Development)

---

## Pre-Deployment Checklist

### 1. Code Review & Testing ✅

- [ ] All Phase 2.7 code reviewed and approved
- [ ] Unit tests passing (`test_decision_assist.py`)
- [ ] Integration tests passing (`test_intelligence_views_phase27.py`)
- [ ] E2E tests passing (`phase_2_7_decision_assist.spec.ts`)
- [ ] Phase 2.6 regression tests passing (`PHASE_2_6_VERIFY_OPERATIONAL.py`)
- [ ] No new linting errors
- [ ] No unresolved merge conflicts

**Verification Command:**
```bash
python manage.py test owner_agreements.tests.test_decision_assist
python manage.py test owner_agreements.tests.test_intelligence_views_phase27
npx playwright test phase_2_7_decision_assist.spec.ts
python PHASE_2_6_VERIFY_OPERATIONAL.py
```

**Expected Output:**
```
All tests passing (green checkmarks)
Phase 2.6: All 8 checks passing
```

---

### 2. Database Backup ✅

- [ ] Production database backed up
- [ ] Backup stored in secure location
- [ ] Backup integrity verified (test restore in dev)

**Backup Command (PostgreSQL):**
```bash
pg_dump -h <host> -U <user> -d goexplorer_db > backup_pre_phase27_$(date +%Y%m%d_%H%M%S).sql
```

**Backup Command (SQLite - Development):**
```bash
cp db.sqlite3 db_backup_pre_phase27_$(date +%Y%m%d_%H%M%S).sqlite3
```

**Verification:**
```bash
ls -lh backup_pre_phase27_*.sql
# Expected: File exists with reasonable size (> 0 bytes)
```

---

### 3. Environment Preparation ✅

- [ ] Python environment activated
- [ ] All dependencies installed (no new ones for Phase 2.7)
- [ ] Django system check passes
- [ ] Database connection verified

**Verification Commands:**
```bash
# Activate environment
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\Activate.ps1  # Windows

# System check
python manage.py check
# Expected: System check identified no issues (0 silenced).

# Database connection
python manage.py dbshell
\q  # PostgreSQL
.quit  # SQLite
```

---

### 4. Documentation Review ✅

- [ ] PHASE_2_7_ARCHITECTURE.md reviewed
- [ ] PHASE_2_7_QUICK_START.md reviewed
- [ ] PHASE_2_7_COMPLETION.md reviewed
- [ ] PHASE_2_7_FILE_MANIFEST.md reviewed
- [ ] This checklist reviewed

**Location:**
- All documentation files in workspace root
- Total: 5 documentation files (~5,000 lines)

---

### 5. Stakeholder Communication ✅

- [ ] Deployment scheduled and communicated
- [ ] Maintenance window announced (if applicable)
- [ ] Rollback plan shared with team
- [ ] On-call engineer identified

**Deployment Window:**
- Recommended: Off-peak hours (e.g., 2am-4am local time)
- Estimated downtime: < 5 minutes (for server restart)

---

## Deployment Steps

### Step 1: Pull Code ✅

**Production:**
```bash
cd /path/to/goexplorer
git fetch origin
git checkout release/phase-2.7
# Or:
git pull origin main
```

**Verification:**
```bash
git log -1 --oneline
# Expected: Shows Phase 2.7 commit
```

- [ ] Code pulled successfully
- [ ] On correct branch/commit

---

### Step 2: Install Dependencies ✅

**Note**: Phase 2.7 has NO new dependencies

**Verification (optional):**
```bash
pip list | grep Django
# Expected: Django version unchanged
```

- [ ] Dependencies verified (no changes)

---

### Step 3: Run Database Migration ✅

**Migration Command:**
```bash
python manage.py migrate owner_agreements
```

**Expected Output:**
```
Operations to perform:
  Apply all migrations: owner_agreements
Running migrations:
  Applying owner_agreements.0004_adminnote... OK
```

**Verification:**
```bash
python manage.py showmigrations owner_agreements
```

**Expected Output:**
```
owner_agreements
 [X] 0001_initial
 [X] 0002_...
 [X] 0003_agreementrisksignal
 [X] 0004_adminnote
```

- [ ] Migration applied successfully
- [ ] No errors in output
- [ ] All migrations marked [X]

**Rollback Command (if needed):**
```bash
python manage.py migrate owner_agreements 0003_agreementrisksignal
```

---

### Step 4: Collect Static Files ✅

**Command:**
```bash
python manage.py collectstatic --noinput
```

**Expected Output:**
```
X static files copied to '/path/to/static', Y unmodified.
```

- [ ] Static files collected
- [ ] No errors in output

---

### Step 5: Restart Application Server ✅

**Gunicorn (systemd):**
```bash
sudo systemctl restart goexplorer
sudo systemctl status goexplorer
```

**Supervisor:**
```bash
sudo supervisorctl restart goexplorer
sudo supervisorctl status goexplorer
```

**Docker Compose:**
```bash
docker-compose restart web
docker-compose ps
```

**Expected Output:**
- Server restarted successfully
- Status: Active/Running

- [ ] Server restarted
- [ ] Server status: Running
- [ ] No errors in logs

---

### Step 6: Verify Server Health ✅

**Health Check:**
```bash
curl -I https://yourapp.com/admin/
# Expected: HTTP/1.1 200 OK or 302 Found (redirect to login)
```

**Intelligence Dashboard:**
```bash
curl -I https://yourapp.com/admin/owner-agreements/intelligence/
# Expected: HTTP/1.1 200 OK or 302 Found
```

- [ ] Server responding
- [ ] Intelligence dashboard accessible
- [ ] No 500 errors

---

## Post-Deployment Verification

### 1. Database Verification ✅

**Check AdminNote Table:**
```bash
python manage.py dbshell
```

**PostgreSQL:**
```sql
-- Table exists
SELECT tablename FROM pg_tables WHERE tablename='owner_agreements_admin_notes';
-- Expected: 1 row

-- Indexes exist
SELECT indexname FROM pg_indexes WHERE tablename='owner_agreements_admin_notes';
-- Expected: 5 rows

-- Initial count (should be 0)
SELECT COUNT(*) FROM owner_agreements_admin_notes;
-- Expected: 0

\q
```

**SQLite:**
```sql
-- Table exists
.tables owner_agreements_admin_notes
-- Expected: Shows table name

-- Schema
.schema owner_agreements_admin_notes
-- Expected: Shows CREATE TABLE statement

-- Initial count
SELECT COUNT(*) FROM owner_agreements_admin_notes;
-- Expected: 0

.quit
```

- [ ] AdminNote table exists
- [ ] All 5 indexes exist
- [ ] No data corruption
- [ ] Initial count is 0

---

### 2. Functional Verification ✅

**Manual Testing (Admin User):**

#### Test 1: Dashboard Loads
- [ ] Navigate to `/admin/owner-agreements/intelligence/`
- [ ] Dashboard loads without errors
- [ ] If critical signals exist, "Top Recommended Actions" panel displays
- [ ] Confidence badges visible (if signals exist)

#### Test 2: Signals List
- [ ] Navigate to `/admin/owner-agreements/intelligence/signals/`
- [ ] Signals list loads
- [ ] "Confidence" column visible in table
- [ ] Confidence badges display (HIGH/MEDIUM/LOW)

#### Test 3: Signal Detail Explainability
- [ ] Click any risk signal
- [ ] Signal detail page loads
- [ ] 4 explainability panels visible:
  - [ ] 📌 Why Is This Happening?
  - [ ] 🧭 What Should You Do?
  - [ ] ⚠️ Potential Consequences If Ignored
  - [ ] 🎯 Analysis Confidence
- [ ] All panels render correctly (no empty/broken sections)

#### Test 4: Admin Notes Form
- [ ] On signal detail page, scroll to bottom
- [ ] "📝 Internal Admin Notes" form visible
- [ ] Enter test note: "Test note created during Phase 2.7 deployment"
- [ ] Click "Add Internal Note"
- [ ] Success message displays: "Internal note added successfully"
- [ ] No errors

**Verification in Database:**
```bash
python manage.py dbshell
```

```sql
SELECT id, note_text, admin_user_id, created_at 
FROM owner_agreements_admin_notes 
ORDER BY created_at DESC LIMIT 1;
-- Expected: Shows test note
```

- [ ] All manual tests passing
- [ ] No UI errors
- [ ] No console errors
- [ ] Test note saved to database

---

### 3. Performance Verification ✅

**DecisionAssistService Performance:**
```bash
python manage.py shell
```

```python
from owner_agreements.decision_assist import DecisionAssistService
from owner_agreements.models import AgreementRiskSignal
import time

service = DecisionAssistService()
signals = AgreementRiskSignal.objects.filter(is_resolved=False)[:10]

if signals.exists():
    start = time.time()
    for signal in signals:
        explanation = service.explain_risk_signal(signal)
    end = time.time()
    
    avg_time = (end - start) / signals.count()
    print(f"Average explanation time: {avg_time*1000:.2f}ms")
    # Target: < 100ms per signal
else:
    print("No risk signals to test (expected if database is fresh)")
```

**Expected Output:**
```
Average explanation time: 45.23ms
```

- [ ] Explanation generation < 100ms per signal
- [ ] No performance degradation

---

### 4. Regression Testing ✅

**Phase 2.6 Still Works:**
```bash
python PHASE_2_6_VERIFY_OPERATIONAL.py
```

**Expected Output:**
```
✅ All 8 checks passing
```

**Owner Flows Still Work:**
```bash
npx playwright test full_owner_flow.spec.ts
```

**Expected Output:**
```
All tests passing (green checkmarks)
```

**Verification Gates Still Work:**
```bash
npx playwright test verification_gates_e2e.spec.ts
```

**Expected Output:**
```
All tests passing (green checkmarks)
```

- [ ] Phase 2.6 verification passing
- [ ] Owner flows working
- [ ] Verification gates working
- [ ] No regressions detected

---

### 5. Error Monitoring ✅

**Check Application Logs:**
```bash
tail -n 100 /var/log/goexplorer/app.log
# Look for errors, warnings, or Phase 2.7 activity
```

**Expected Log Entries:**
```
[DECISION_ASSIST] Explaining risk signal #X (RISK_TYPE)
[ADMIN_NOTE] Created by admin_user on RISK_SIGNAL (signal=X, owner=Y)
```

**No Expected Errors:**
- ❌ No `DecisionAssistService` exceptions
- ❌ No template rendering errors
- ❌ No database query errors
- ❌ No 500 errors

- [ ] Logs reviewed
- [ ] No critical errors
- [ ] Phase 2.7 activity logged correctly

---

### 6. Security Verification ✅

**Owner Users Cannot Access Intelligence:**
```bash
# Log out of admin account
# Log in as regular owner user
# Try to access: /admin/owner-agreements/intelligence/
```

**Expected:**
- Redirected to login page OR 403 Forbidden
- No intelligence data visible to owners

**Test Admin-Only Access:**
- [ ] Owner users cannot access intelligence dashboard
- [ ] Owner users cannot access risk signals list
- [ ] Owner users cannot access signal detail pages
- [ ] Owner users cannot create admin notes

---

## Smoke Tests (Quick Verification)

### 5-Minute Smoke Test ✅

**Quick health check after deployment:**

1. [ ] **Server Responding**: `curl -I https://yourapp.com/`
2. [ ] **Admin Login**: Navigate to `/admin/`, log in successfully
3. [ ] **Intelligence Dashboard**: Navigate to `/admin/owner-agreements/intelligence/`, page loads
4. [ ] **Signal Detail**: Click any signal, explainability panels render
5. [ ] **Admin Note Creation**: Create test note, success message displays
6. [ ] **Owner Flow**: Log in as owner, verify owner dashboard works
7. [ ] **No Console Errors**: Check browser console for JavaScript errors

**Pass Criteria:**
- All 7 checks pass within 5 minutes
- No critical errors encountered

---

## Rollback Decision Tree

### When to Rollback?

**Immediate Rollback (Critical Issues):**
- ❌ Database migration failed
- ❌ Server won't start after deployment
- ❌ Intelligence dashboard returns 500 errors
- ❌ Owner flows broken (registration, login, properties)
- ❌ Payment processing affected

**Defer Rollback (Non-Critical Issues):**
- ⚠️ Minor UI styling issues
- ⚠️ Explainability panel text needs refinement
- ⚠️ Admin notes form has cosmetic bug
- ⚠️ Performance < 100ms (but still < 200ms)

**Monitor & Fix in Place (Minor Issues):**
- 💡 Confidence badge color incorrect
- 💡 Empty state message needs rewording
- 💡 Log level too verbose

---

## Rollback Procedure

### Quick Rollback (Code Only)

**If no database issues:**
```bash
cd /path/to/goexplorer
git revert <phase-2.7-commit-sha>
python manage.py collectstatic --noinput
sudo systemctl restart goexplorer
```

- [ ] Code reverted
- [ ] Static files collected
- [ ] Server restarted
- [ ] Verification: Intelligence dashboard returns 404 (expected after rollback)

---

### Full Rollback (Code + Database)

**If database issues:**
```bash
# 1. Stop server
sudo systemctl stop goexplorer

# 2. Rollback migration
python manage.py migrate owner_agreements 0003_agreementrisksignal
# Expected: Removing owner_agreements.0004_adminnote... OK

# 3. Revert code
git revert <phase-2.7-commit-sha>

# 4. Collect static
python manage.py collectstatic --noinput

# 5. Restart server
sudo systemctl start goexplorer
```

- [ ] Server stopped
- [ ] Migration rolled back
- [ ] Code reverted
- [ ] Static files collected
- [ ] Server restarted

**Verification After Rollback:**
```bash
python PHASE_2_6_VERIFY_OPERATIONAL.py
# Expected: All 8 checks passing (Phase 2.6 still works)

python manage.py showmigrations owner_agreements
# Expected: 0004_adminnote is [ ] (unchecked)
```

---

### Database Restore (Nuclear Option)

**Only if catastrophic database corruption:**
```bash
# 1. Stop server
sudo systemctl stop goexplorer

# 2. Restore backup
psql -U postgres -d goexplorer_db < backup_pre_phase27.sql

# 3. Restart server
sudo systemctl start goexplorer
```

- [ ] Backup restored successfully
- [ ] All data verified
- [ ] Server restarted

---

## Post-Deployment Monitoring

### First 24 Hours ✅

**Metrics to Monitor:**
- [ ] Server uptime (target: 99.9%)
- [ ] Dashboard load time (target: < 2s)
- [ ] Explanation generation time (target: < 100ms)
- [ ] Admin note creation success rate (target: > 99%)
- [ ] Error rate (target: < 0.1%)

**Monitoring Tools:**
- Application logs: `/var/log/goexplorer/app.log`
- Server metrics: Grafana/Prometheus (if configured)
- Error tracking: Sentry (if configured)

**Alert Thresholds:**
- 🚨 Critical: Server down > 5 minutes
- ⚠️ Warning: Dashboard load time > 5s
- 💡 Info: Explanation generation > 200ms

---

### First Week ✅

**User Feedback:**
- [ ] Admin users report no blockers
- [ ] No complaints about Phase 2.7 features
- [ ] Positive feedback on explainability clarity

**Performance Baseline:**
- [ ] Dashboard avg load time: _______s
- [ ] Signals list avg load time: _______s
- [ ] Signal detail avg load time: _______s
- [ ] Explanation avg generation: _______ms

**Usage Metrics:**
- [ ] Admin notes created: _______
- [ ] Intelligence dashboard views: _______
- [ ] Signal detail views: _______

---

## Success Criteria

### Deployment Success ✅

Phase 2.7 deployment is considered successful when:

- ✅ All pre-deployment checks passed
- ✅ Database migration applied successfully
- ✅ Server restarted without errors
- ✅ All post-deployment verifications passed
- ✅ No regressions to existing flows
- ✅ Smoke tests completed (< 5 minutes)
- ✅ No critical errors in first 24 hours
- ✅ Admin users can use Phase 2.7 features
- ✅ Owner flows unaffected

### Phase 2.7 Locked ✅

Phase 2.7 is considered **LOCKED & STABLE** when:

- ✅ Deployed to production without issues
- ✅ No rollbacks required
- ✅ User acceptance testing complete
- ✅ Performance baselines established
- ✅ Monitoring alerts configured
- ✅ Documentation complete
- ✅ Team trained on Phase 2.7 features

---

## Sign-Off

### Deployment Sign-Off

**Deployed By**: ___________________________  
**Date**: ___________________________  
**Environment**: ___________________________ (Production/Staging)

**Deployment Status**: [ ] Success [ ] Failed [ ] Rolled Back

**Notes**:
```
(Add any deployment notes, issues encountered, or special considerations here)
```

---

### Phase Lead Approval

**Phase Lead**: ___________________________  
**Date**: ___________________________  
**Approval**: [ ] Approved for Production

**Comments**:
```
(Phase lead comments, sign-off notes)
```

---

### Stakeholder Notification

**Notification Sent**: [ ] Yes [ ] No  
**Sent To**: ___________________________  
**Date**: ___________________________

**Deployment Summary**:
- Migration: ✅ Applied
- Server: ✅ Restarted
- Verification: ✅ Passed
- Status: ✅ Production-Ready

---

## Next Steps

### Immediate (Next 24 Hours)
- [ ] Monitor error logs
- [ ] Respond to user feedback
- [ ] Document any issues encountered
- [ ] Update runbook if needed

### Short-Term (Next Week)
- [ ] Collect usage metrics
- [ ] Gather admin user feedback
- [ ] Refine explainability text (if needed)
- [ ] Performance optimization (if needed)

### Medium-Term (Next Month)
- [ ] User training sessions
- [ ] Documentation updates based on feedback
- [ ] Evaluate Phase 2.8 readiness

---

**Document Version**: 1.0  
**Created**: January 27, 2026  
**Last Updated**: {{ update_date }}  
**Maintained By**: DevOps Team
