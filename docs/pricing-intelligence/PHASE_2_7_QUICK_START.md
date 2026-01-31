# Phase 2.7 Quick Start Guide: Admin Decision Assist

## Prerequisites

✅ Phase 2.6 fully operational (migration applied, risk analyzer working)  
✅ Python environment activated  
✅ Database accessible  
✅ Superuser account created

---

## Setup Steps

### 1. Apply Migration

```bash
cd c:\Users\ravi9\Downloads\Go_code\Go_explorer_clear
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

**Expected:**
```
owner_agreements
 [X] 0001_initial
 [X] 0002_...(previous)
 [X] 0003_agreementrisksignal
 [X] 0004_adminnote
```

---

### 2. Verify DecisionAssistService

```bash
python manage.py shell
```

```python
from owner_agreements.decision_assist import DecisionAssistService
from owner_agreements.models import AgreementRiskSignal

# Initialize service
service = DecisionAssistService()

# Test with a risk signal (if any exist)
signal = AgreementRiskSignal.objects.first()
if signal:
    explanation = service.explain_risk_signal(signal)
    print("✅ DecisionAssistService working!")
    print(f"Explanation: {explanation['explanation']}")
    print(f"Confidence: {explanation['confidence']}")
else:
    print("⚠️ No risk signals in database (expected if no test data)")
```

---

### 3. Create Test Data (Optional)

If your database is empty, create test data:

```bash
python run_phase_2_6_analysis.py
```

This will:
- Run risk analyzer
- Generate risk signals (if conditions met)
- Allow testing of Phase 2.7 features

---

### 4. Start Development Server

```bash
python manage.py runserver
```

---

### 5. Access Intelligence Dashboard

Navigate to: `http://localhost:8000/admin/owner-agreements/intelligence/`

**Expected:**
- Intelligence dashboard loads
- If critical signals exist, "Top Recommended Actions" panel displays
- Each recommendation shows confidence badge
- Clicking signal → Full explainability panels

---

## Manual Testing Checklist

### ✅ Test 1: Dashboard Recommendations Panel

**Steps:**
1. Go to `http://localhost:8000/admin/owner-agreements/intelligence/`
2. Verify "Top Recommended Actions" panel exists (if critical signals present)
3. Check each recommendation has:
   - Owner name
   - Confidence badge (HIGH/MEDIUM/LOW)
   - Signal title
   - Top 2 suggested actions
   - "View Full Analysis →" link
4. Verify advisory disclaimer: "All recommendations require human review and approval before action"

**Expected Behavior:**
- Panel renders with green background
- Confidence badges color-coded (green=HIGH, yellow=MEDIUM, red=LOW)
- No automated action buttons
- All elements have `data-testid` attributes

---

### ✅ Test 2: Signals List Confidence Badges

**Steps:**
1. Go to `http://localhost:8000/admin/owner-agreements/intelligence/signals/`
2. Verify "Confidence" column exists in table header
3. Check each signal row has confidence badge
4. Verify badge colors match confidence level

**Expected Behavior:**
- Table has 9 columns (including Confidence)
- Each row shows confidence badge
- Badges: HIGH (green), MEDIUM (yellow), LOW (red)

---

### ✅ Test 3: Risk Signal Detail Explainability Panels

**Steps:**
1. Go to any risk signal detail page
2. Verify 4 explainability panels exist:
   - 📌 Why Is This Happening?
   - 🧭 What Should You Do?
   - ⚠️ Potential Consequences If Ignored
   - 🎯 Analysis Confidence
3. Click "Common Root Causes" to expand/collapse
4. Verify all elements have `data-testid` attributes
5. Verify advisory note: "These are recommendations, not automated actions"

**Expected Behavior:**
- All 4 panels render with color-coded backgrounds
- Explanation text is clear and human-readable
- Suggested actions list is actionable (no vague guidance)
- Confidence badge matches explanation confidence level
- Platform baseline comparison shows emoji indicator (🔴🟡🟢)
- No automated action buttons

---

### ✅ Test 4: Admin Notes Form

**Steps:**
1. Go to any risk signal detail page
2. Scroll to bottom: "📝 Internal Admin Notes" section
3. Read disclaimer: "Notes are for internal use only and never visible to owners"
4. Enter text in note textarea: "Test observation: Owner contacted via phone on 2024-01-15"
5. Click "Add Internal Note"
6. Verify success message displays
7. Refresh page
8. Verify note is NOT displayed (notes display not yet implemented, but creation logged)

**Expected Behavior:**
- Form renders with yellow background
- Textarea accepts input
- Submit button works
- Success message: "Internal note added successfully"
- No errors in console
- Note saved to database (check Django admin or shell)

---

### ✅ Test 5: Owner Intelligence Baseline Comparisons

**Steps:**
1. Go to owner intelligence page for an owner with active signals
2. Look for "Owner vs Platform Baseline" section (below risk score)
3. Verify baseline comparisons show for each risk type
4. Verify emoji indicators present (🔴🟡🟢)

**Expected Behavior:**
- Baseline comparisons render
- Text is human-readable: "🔴 EXTREME: <1% of owners have 4+ force-expires"
- Comparisons match risk types

---

### ✅ Test 6: Empty State Handling

**Steps:**
1. Create a test database with NO risk signals
2. Go to intelligence dashboard
3. Verify no recommendations panel displays
4. Go to risk signals list
5. Verify empty state message displays
6. Create 1 risk signal (via risk analyzer)
7. Go to signal detail page
8. Verify explainability panels render
9. Delete DecisionAssistService logic temporarily (to simulate failure)
10. Reload signal detail page
11. Verify empty state message: "No detailed explanation available for this signal type yet"

**Expected Behavior:**
- Graceful degradation
- No 500 errors
- Clear empty state messages
- No broken UI

---

### ✅ Test 7: Read-Only Verification (NO Automated Actions)

**Steps:**
1. Audit all templates for automated action buttons
2. Verify NO buttons like:
   - "Auto-Send Email"
   - "Force Expire Automatically"
   - "Trigger Renewal"
   - "Apply Recommendation"
3. Verify all suggested actions are TEXT ONLY
4. Verify no JavaScript AJAX calls to action endpoints
5. Verify no forms with action="force-expire" or similar

**Expected Behavior:**
- ZERO automated action buttons
- All guidance is advisory text only
- Admin must manually execute actions outside intelligence system

---

### ✅ Test 8: Owner Has No Access

**Steps:**
1. Log out of admin account
2. Log in as a regular owner user
3. Try to access: `http://localhost:8000/admin/owner-agreements/intelligence/`
4. Verify access denied (redirect to login or 403 Forbidden)
5. Try to access signal detail page directly (if URL known)
6. Verify access denied

**Expected Behavior:**
- Non-staff users cannot access intelligence dashboard
- `@staff_member_required` decorator enforced
- No intelligence data exposed to owners

---

### ✅ Test 9: Admin Note Validation

**Steps:**
1. Go to risk signal detail page
2. Leave note textarea empty
3. Click "Add Internal Note"
4. Verify error message: "Note text cannot be empty"
5. Enter valid note text
6. Submit form
7. Verify success message

**Expected Behavior:**
- Empty note submission rejected
- Error message displayed
- Valid note submission succeeds

---

### ✅ Test 10: Confidence Calculation Determinism

**Steps:**
```python
python manage.py shell
```

```python
from owner_agreements.decision_assist import DecisionAssistService
from owner_agreements.models import AgreementRiskSignal

service = DecisionAssistService()
signal = AgreementRiskSignal.objects.first()

# Call explain_risk_signal multiple times
explanation1 = service.explain_risk_signal(signal)
explanation2 = service.explain_risk_signal(signal)
explanation3 = service.explain_risk_signal(signal)

# Verify same output every time
assert explanation1['confidence'] == explanation2['confidence']
assert explanation1['confidence'] == explanation3['confidence']
assert explanation1['explanation'] == explanation2['explanation']

print("✅ DecisionAssistService is deterministic")
```

**Expected Behavior:**
- Same input → Same output (every time)
- No randomness in confidence calculation
- No side effects (DB unchanged)

---

## Troubleshooting

### Issue 1: "No module named 'owner_agreements.decision_assist'"

**Solution:**
```bash
python manage.py shell
```

```python
import sys
sys.path
# Verify workspace root is in sys.path
```

If not found:
```bash
cd c:\Users\ravi9\Downloads\Go_code\Go_explorer_clear
python -c "import owner_agreements.decision_assist; print('✅ Module found')"
```

---

### Issue 2: "AdminNote does not exist"

**Solution:**
```bash
python manage.py migrate owner_agreements
python manage.py showmigrations owner_agreements
```

Verify `0004_adminnote` is applied.

---

### Issue 3: Explainability Panels Not Rendering

**Check:**
1. View passes `explanation` context to template
2. Template checks `{% if explanation %}`
3. DecisionAssistService not raising exceptions (check logs)
4. Signal exists in database

**Debug:**
```python
python manage.py shell
```

```python
from owner_agreements.decision_assist import DecisionAssistService
from owner_agreements.models import AgreementRiskSignal

service = DecisionAssistService()
signal = AgreementRiskSignal.objects.first()

try:
    explanation = service.explain_risk_signal(signal)
    print("✅ Explanation generated")
    print(explanation)
except Exception as e:
    print(f"❌ Error: {e}")
```

---

### Issue 4: Confidence Badges Not Displaying

**Check:**
1. View passes `signals_with_confidence` (not `signals`) to template
2. Template loops over `signals_with_confidence` (not `signals`)
3. CSS for `.confidence-badge--high/medium/low` exists

**Debug:**
View source of rendered page, search for `data-testid="confidence-cell"`. If not found, view context is wrong.

---

### Issue 5: Admin Note Form Submission Fails

**Check:**
1. CSRF token present in form
2. Form action URL correct: `{% url 'owner_agreements_admin:admin-note-create' %}`
3. Hidden fields: `note_type`, `signal_id`, `owner_id`, `agreement_id`, `redirect_url`
4. View logs errors (check terminal output)

**Debug:**
```bash
python manage.py shell
```

```python
from owner_agreements.models import AdminNote
from django.contrib.auth.models import User

admin = User.objects.filter(is_staff=True).first()
note = AdminNote.objects.create(
    note_type='GENERAL',
    note_text='Test note from shell',
    admin_user=admin,
)
print(f"✅ Note created: {note.id}")
```

---

## Verification Commands

### Check Migration Status
```bash
python manage.py showmigrations owner_agreements
```

### Check AdminNote Table Exists
```bash
python manage.py dbshell
```

```sql
SELECT name FROM sqlite_master WHERE type='table' AND name='owner_agreements_admin_notes';
-- OR for PostgreSQL:
SELECT tablename FROM pg_tables WHERE tablename='owner_agreements_admin_notes';
```

### Count Admin Notes
```bash
python manage.py shell
```

```python
from owner_agreements.models import AdminNote
print(f"Total admin notes: {AdminNote.objects.count()}")
```

### List All Risk Signals with Confidence
```python
from owner_agreements.decision_assist import DecisionAssistService
from owner_agreements.models import AgreementRiskSignal

service = DecisionAssistService()
signals = AgreementRiskSignal.objects.filter(is_resolved=False)[:5]

for signal in signals:
    explanation = service.explain_risk_signal(signal)
    print(f"Signal #{signal.id}: {signal.title}")
    print(f"  Confidence: {explanation['confidence']}")
    print(f"  Suggested Actions: {len(explanation['suggested_actions'])}")
    print()
```

---

## Next Steps

After manual testing:
1. ✅ Run unit tests: `python -m pytest owner_agreements/tests/test_decision_assist.py`
2. ✅ Run integration tests: `python -m pytest owner_agreements/tests/test_intelligence_views_phase27.py`
3. ✅ Run Playwright tests: `npx playwright test phase_2_7_decision_assist.spec.ts`
4. ✅ Review PHASE_2_7_COMPLETION.md for deployment readiness
5. ✅ Deploy to staging environment
6. ✅ User acceptance testing

---

## Quick Reference: URLs

- Intelligence Dashboard: `/admin/owner-agreements/intelligence/`
- Signals List: `/admin/owner-agreements/intelligence/signals/`
- Signal Detail: `/admin/owner-agreements/intelligence/signals/<id>/`
- Owner Intelligence: `/admin/owner-agreements/intelligence/owner/<id>/`
- Admin Note Create: `/admin/owner-agreements/intelligence/admin-note/create/` (POST)

---

**Document Version**: 1.0  
**Created**: Phase 2.7 Implementation  
**Last Updated**: {{ current_date }}  
**Author**: GitHub Copilot (AI Agent)
