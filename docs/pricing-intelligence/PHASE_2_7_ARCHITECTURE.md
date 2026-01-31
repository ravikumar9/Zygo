# Phase 2.7 Architecture: Admin Decision Assist (AI-Augmented, Read-Only)

## Overview

Phase 2.7 enhances the Phase 2.6 Risk Monitoring system with **explainability and human decision support**. This is a **READ-ONLY** intelligence layer that provides context, explanations, and suggested actions for risk signals **WITHOUT taking any automated actions**.

### Key Principle: Advisory, Not Automated

🚫 **NO automated actions**: System provides recommendations only  
👤 **Human approval required**: All decisions require manual admin review  
📝 **Transparent explanations**: Clear "why" and "what" for every signal  
🔒 **Admin-only**: Zero owner-facing exposure

---

## Architecture Components

### 1. DecisionAssistService (Explainability Engine)

**File**: `owner_agreements/decision_assist.py` (~550 lines)

#### Purpose
Generate human-readable explanations and suggested actions for risk signals based on historical patterns and platform baselines.

#### Design Principles
- ✅ **Pure functions**: No side effects, deterministic output
- ✅ **No database writes**: Read-only analysis
- ✅ **Unit testable**: All logic isolated and testable
- ✅ **Reusable**: Can be extended for future AI models

#### Core Methods

**`explain_risk_signal(signal: AgreementRiskSignal) -> Dict`**
- Routes to specific risk type handler
- Returns comprehensive explanation with:
  - `explanation`: Human-readable "why" text
  - `root_causes`: List of common causes
  - `consequences`: What happens if ignored
  - `suggested_actions`: Recommended admin steps (TEXT ONLY)
  - `confidence`: LOW/MEDIUM/HIGH confidence level
  - `baseline_comparison`: How this compares to platform average
  - `metadata`: Additional context (view counts, days pending, etc.)

**Risk Type Handlers:**
- `_explain_expiring_soon()`: Agreements near expiration (14 days)
- `_explain_long_pending()`: GENERATED agreements 30+ days old
- `_explain_repeated_force_expire()`: 2+ force-expires in 90 days
- `_explain_repeated_regeneration()`: 3+ regenerations in 90 days
- `_explain_inactive_owner()`: EXPIRED + 60+ days inactive
- `_explain_failed_acceptance()`: Multiple views, no acceptance

**Confidence Calculation:**
- Uses weighted factors (conditions + weights)
- Returns score 0.0-1.0
- Thresholds: HIGH (≥0.8), MEDIUM (≥0.5), LOW (<0.5)

**Baseline Comparisons:**
- Uses emoji indicators (🔴🟡🟢) for quick visual scanning
- Compares owner behavior to platform-wide averages
- Examples:
  - "🔴 EXTREME: <1% of owners have 4+ force-expires"
  - "🟢 NORMAL: Within typical acceptance window"

#### Example Output

```python
{
    'explanation': "Owner 'ABC Properties' has an agreement expiring in 5 days. This owner has active properties and will be unable to operate them after expiration.",
    'root_causes': [
        "Agreement approaching natural expiration date",
        "No renewal triggered yet",
        "Time-based expiration policy"
    ],
    'consequences': [
        "🚫 Owner cannot publish new properties after expiration",
        "🚫 Existing published properties become invisible to customers",
        "💰 Lost revenue from owner's properties",
        "😟 Poor owner experience if caught off-guard"
    ],
    'suggested_actions': [
        "📧 Send proactive renewal email to owner",
        "🔄 Trigger agreement regeneration if owner is responsive",
        "📊 Review owner performance: 2 previous renewals"
    ],
    'confidence': "HIGH",
    'baseline_comparison': "🟡 MODERATE: Standard renewal window, but close",
    'metadata': {
        'days_until_expiration': 5,
        'has_active_properties': True,
        'previous_renewals': 2,
        'confidence_score': 0.9
    }
}
```

---

### 2. AdminNote Model (Audit Trail)

**File**: `owner_agreements/models.py` (lines ~510-620)

#### Purpose
Allow admins to document internal observations, decisions, and context about risk signals, owners, or agreements.

#### Schema

```python
class AdminNote(models.Model):
    # Relationships (all nullable for flexibility)
    risk_signal = ForeignKey(AgreementRiskSignal, CASCADE, null=True)
    owner = ForeignKey('property_owners.PropertyOwner', CASCADE, null=True)
    agreement = ForeignKey(OwnerAgreement, CASCADE, null=True)
    
    # Note content
    note_type = CharField(choices=['RISK_SIGNAL', 'OWNER', 'AGREEMENT', 'GENERAL'])
    note_text = TextField()  # Admin's observation
    
    # Audit fields
    admin_user = ForeignKey(User, PROTECT)  # Who created the note
    created_at = DateTimeField(auto_now_add=True, indexed)
    metadata = JSONField(default=dict)  # IP, user agent, etc.
    
    class Meta:
        db_table = 'owner_agreements_admin_notes'
        ordering = ['-created_at']
        indexes = [
            Index(['risk_signal', 'created_at']),
            Index(['owner', 'created_at']),
            Index(['agreement', 'created_at']),
            Index(['admin_user', 'created_at']),
            Index(['created_at'])
        ]
```

#### Design Principles
- ✅ **Immutable**: Notes cannot be edited after creation (append-only)
- ✅ **Timestamped**: Auto-recorded creation timestamp
- ✅ **Audit trail**: Records admin user, IP, user agent
- ✅ **Staff-only**: Never exposed to owners
- ✅ **Flexible relationships**: Can link to signal, owner, agreement, or none

#### Use Cases
- Document why a specific action was taken
- Record phone conversation outcomes
- Note context for future reference
- Track admin decision-making process

---

### 3. Enhanced Intelligence Views

**File**: `owner_agreements/views_intelligence.py` (modified, 4 views enhanced)

#### Changes Made

**`intelligence_dashboard()`**
- Added: `top_recommendations` context
- Generates explanations for top 3 critical alerts
- Shows suggested actions (top 2 per alert)
- Template receives: `[{signal, suggested_actions, confidence}, ...]`

**`risk_signals_list()`**
- Added: `signals_with_confidence` context
- Attaches confidence indicator to each signal
- Template receives: `[{signal, confidence}, ...]`
- Displays confidence badge in table column

**`risk_signal_detail()`** (most important)
- Added: Full `explanation` context from DecisionAssistService
- Template receives entire explanation dict:
  - Why signal exists
  - Root causes
  - Consequences if ignored
  - Suggested actions
  - Confidence level
  - Baseline comparison
- Explainability panels render in template

**`owner_intelligence()`**
- Added: `owner_vs_baseline` context
- Generates baseline comparisons for owner's top 3 signals
- Template receives: `{risk_type: baseline_comparison_text, ...}`

**`admin_note_create()` (NEW)**
- POST-only view for creating admin notes
- Validates note_text not empty
- Links note to signal/owner/agreement based on form data
- Records admin user, IP, user agent
- Logs action and redirects back to referrer

---

### 4. Updated Templates

#### **intelligence_dashboard.html**

**Added:**
- Top Recommendations Panel (after critical alerts, before stats grid)
- Shows top 3 critical signals with AI-suggested actions
- Confidence badges (HIGH/MEDIUM/LOW)
- Advisory disclaimer: "All recommendations require human review"
- `data-testid` attributes for Playwright testing

**Styles:**
- Green background for recommendations card
- Confidence badges color-coded (green/yellow/red)
- Collapsible/expandable recommendations
- Mobile-responsive

---

#### **risk_signals_list.html**

**Added:**
- "Confidence" column in signals table
- Confidence badge for each signal (HIGH/MEDIUM/LOW)
- `data-testid="confidence-cell"` for testing

**Styles:**
- Confidence badges: Same color scheme as severity
- Aligned center in table column

---

#### **risk_signal_detail.html** (MOST SIGNIFICANT CHANGES)

**Added (4 new panels):**

1. **📌 Why Is This Happening?**
   - Explanation text
   - Root causes list (collapsible)
   - `data-testid="explainability-panel"`

2. **🧭 What Should You Do?**
   - Advisory note: "These are recommendations, not automated actions"
   - Suggested actions list (bullet points)
   - `data-testid="suggested-actions-panel"`

3. **⚠️ Potential Consequences If Ignored**
   - Consequences list (emoji-prefixed)
   - `data-testid="consequences-panel"`

4. **🎯 Analysis Confidence**
   - Confidence badge (HIGH/MEDIUM/LOW)
   - Platform baseline comparison
   - `data-testid="confidence-panel"`

5. **📝 Internal Admin Notes Form** (NEW)
   - Textarea for note_text
   - Hidden fields: note_type, signal_id, owner_id, agreement_id, redirect_url
   - Submit button: "Add Internal Note"
   - Disclaimer: "Notes are for internal use only and never visible to owners"
   - `data-testid="admin-notes-card"`

**Styles:**
- Color-coded panels:
  - Explainability: Blue (#eff6ff)
  - Suggested actions: Green (#f0fdf4)
  - Consequences: Yellow (#fef3c7)
  - Confidence: Purple (#f5f3ff)
  - Admin notes: Yellow (#fefce8)
- All panels have 4px left border
- Responsive, mobile-friendly
- Empty state handling (if no explanation available)

---

#### **owner_intelligence.html**

**Added:**
- Owner vs Baseline section (below risk score)
- Shows comparison text for each active risk type
- `data-testid="owner-vs-baseline"`

**Styles:**
- Baseline comparisons with emoji indicators
- Grouped by risk type

---

### 5. URL Routing

**File**: `owner_agreements/urls_intelligence.py` (1 route added)

**New Route:**
```python
path(
    'intelligence/admin-note/create/',
    views_intelligence.admin_note_create,
    name='admin-note-create'
)
```

**Access:**
- POST-only
- Staff-required (`@staff_member_required`)
- CSRF protected
- Redirects back to referrer after creation

---

## Data Flow

### 1. Risk Signal Explanation Flow

```
Risk Signal Detected (Phase 2.6)
        ↓
Admin Views Risk Detail Page
        ↓
risk_signal_detail() view calls DecisionAssistService.explain_risk_signal(signal)
        ↓
Service routes to risk-type-specific handler
        ↓
Handler gathers context (view counts, admin actions, owner history)
        ↓
Handler calculates confidence score
        ↓
Handler generates explanation dict
        ↓
View passes explanation to template context
        ↓
Template renders 4 explainability panels
        ↓
Admin reviews recommendations (NO automated actions)
```

### 2. Admin Note Creation Flow

```
Admin views risk signal detail page
        ↓
Admin writes note in "Internal Admin Notes" form
        ↓
Form submits POST to admin_note_create() view
        ↓
View validates note_text (not empty)
        ↓
View retrieves signal/owner/agreement objects
        ↓
View creates AdminNote record
        ↓
Note saved to database (immutable)
        ↓
View logs action
        ↓
View redirects back to detail page
        ↓
Success message displayed
```

---

## Security & Compliance

### Owner Privacy
- ✅ All explainability content is admin-only
- ✅ No owner-facing exposure of explanations
- ✅ Admin notes never visible to owners
- ✅ No automated emails/notifications triggered

### Access Control
- ✅ All views: `@staff_member_required` decorator
- ✅ All forms: CSRF protection
- ✅ All notes: Staff-only creation, no editing/deletion

### Audit Trail
- ✅ All admin note creations logged
- ✅ IP address and user agent recorded
- ✅ Admin user recorded on every note
- ✅ Timestamps immutable (auto_now_add)

### No Automated Actions
- ✅ DecisionAssistService: Pure functions, no DB writes
- ✅ Explainability: TEXT ONLY, no side effects
- ✅ Suggested actions: Advisory only, require human execution
- ✅ No automated emails, force-expires, or regenerations

---

## Testing Strategy

### 1. Unit Tests
**File**: `owner_agreements/tests/test_decision_assist.py`

**Coverage:**
- Test each risk type explanation handler
- Test confidence calculation logic
- Test baseline comparison generation
- Test no side effects (DB unchanged after call)
- Test deterministic output (same input → same output)
- Test edge cases (null values, empty data)

### 2. Integration Tests
**File**: `owner_agreements/tests/test_intelligence_views_phase27.py`

**Coverage:**
- Test intelligence_dashboard renders recommendations
- Test risk_signals_list includes confidence badges
- Test risk_signal_detail renders explainability panels
- Test owner_intelligence renders baseline comparisons
- Test admin_note_create view (POST)
- Test admin_note_create validation (empty text)
- Test admin_note_create redirect

### 3. Playwright E2E Tests
**File**: `tests/e2e/phase_2_7_decision_assist.spec.ts`

**Coverage:**
- `test_dashboard_recommendations_visible()`: Top recommendations panel exists
- `test_risk_detail_explainability_panel_exists()`: All 4 panels rendered
- `test_confidence_badge_displays()`: Confidence badges in list view
- `test_admin_note_form_creates_note()`: Form submission works
- `test_empty_state_when_no_explanations()`: Empty state handled gracefully
- `test_read_only_no_action_buttons()`: No automated action buttons
- `test_owner_has_no_access_to_intelligence()`: Owner cannot access admin views

---

## Performance Considerations

### DecisionAssistService Optimization
- ✅ No N+1 queries (all prefetching done in views)
- ✅ Lightweight computations (no heavy ML models)
- ✅ Caching-friendly (pure functions, deterministic)
- ✅ Graceful degradation (try/except in views)

### Database Indexes
AdminNote model has 5 indexes:
- `(risk_signal, created_at)` - Fast signal notes lookup
- `(owner, created_at)` - Fast owner notes lookup
- `(agreement, created_at)` - Fast agreement notes lookup
- `(admin_user, created_at)` - Fast user activity lookup
- `(created_at)` - Fast recent notes lookup

### Template Rendering
- ✅ All explanation generation happens in view (not template)
- ✅ No template-side queries
- ✅ Progressive disclosure (collapsible sections)
- ✅ Mobile-optimized (no heavy JS frameworks)

---

## Rollback Plan

### If Phase 2.7 Needs Rollback

**Step 1: Remove New Views**
- Comment out `admin_note_create()` in `views_intelligence.py`
- Remove route from `urls_intelligence.py`

**Step 2: Revert Templates**
- Remove explainability panels from `risk_signal_detail.html`
- Remove recommendations panel from `intelligence_dashboard.html`
- Remove confidence column from `risk_signals_list.html`
- Remove admin notes form from `risk_signal_detail.html`

**Step 3: Revert Views**
- Remove DecisionAssistService imports from views
- Remove `explanation` context from `risk_signal_detail()`
- Remove `top_recommendations` context from `intelligence_dashboard()`
- Remove `signals_with_confidence` context from `risk_signals_list()`
- Remove `owner_vs_baseline` context from `owner_intelligence()`

**Step 4: Database Migration Rollback (if needed)**
```bash
python manage.py migrate owner_agreements 0003_agreementrisksignal
```
This removes AdminNote model.

**Step 5: Remove Files**
- Delete `owner_agreements/decision_assist.py`
- Delete Phase 2.7 documentation files

**Phase 2.6 will remain fully operational after rollback.**

---

## Future Enhancements (Out of Scope for Phase 2.7)

### Potential Phase 2.8+ Features
- **Machine Learning Models**: Replace heuristic confidence calculation with ML-based scoring
- **Predictive Analytics**: Predict which owners are most likely to churn
- **Automated Escalation**: Auto-escalate critical signals to Slack/email (with opt-in)
- **Historical Trend Analysis**: Chart how owner risk scores evolve over time
- **Bulk Actions**: Allow admins to mark multiple signals as reviewed
- **Note Templates**: Pre-defined note templates for common scenarios
- **Note Search**: Full-text search across all admin notes

---

## Conclusion

Phase 2.7 completes the **Intelligence + Explainability** story:
- ✅ Phase 2.6: Detect and monitor risks (DONE)
- ✅ Phase 2.7: Explain and suggest actions (DONE)
- 🔮 Phase 2.8+: Predictive analytics and automation (FUTURE)

**Key Success Metrics:**
- Admins can understand "why" a risk signal exists in <30 seconds
- Admins have clear action steps without guessing
- No manual interpretation of raw data required
- Zero automated actions (human approval always required)
- All intelligence visible via Playwright tests

---

**Document Version**: 1.0  
**Created**: Phase 2.7 Implementation  
**Last Updated**: {{ current_date }}  
**Author**: GitHub Copilot (AI Agent)
