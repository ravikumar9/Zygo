# PRICING AUDIT PHASE - QUICK REFERENCE GUIDE

**Status**: ✋ **AUDIT PHASE - NO NEW FEATURES**
**Duration**: March 15-21, 2024 (1 week)
**Approval Required Before**: EPIC-2 (Inventory Locking) starts

---

## 🎯 One-Liner Summary

> We're auditing pricing logic before scaling. Verify current implementation is correct, competitive, and edge-case safe. 4 red flags need investigation. EPIC-2 blocked until approval.

---

## 📊 What You Need to Know

### Your Role in This Audit

**👨‍💼 Product Manager**
- **Task**: Review competitive positioning & approve messaging
- **Time**: 30 mins to read PRICING_COMPETITIVE_ANALYSIS.md
- **Decision**: Red flags - accept risk or require fixes?
- **Deadline**: March 20 approval sign-off

**👨‍💻 Backend Engineer**
- **Task**: Code review pricing_service.py, run tests
- **Time**: 1 hour to review code + run tests
- **Decision**: Any bugs or regressions found?
- **Deadline**: March 19 all tests passing

**👩‍🔬 QA Engineer**
- **Task**: Collect competitor screenshots, verify edge cases
- **Time**: 2-3 hours to collect evidence
- **Decision**: Is pricing consistent across platforms?
- **Deadline**: March 18 all 10 screenshots

**👔 Audit Lead**
- **Task**: Coordinate all teams, track progress
- **Time**: 1 hour daily to sync
- **Decision**: Ready for approval on March 21?
- **Deadline**: March 21 final sign-off

---

## 🗂️ Key Documents (In Read Order)

```
START HERE ↓

1. PRICING_AUDIT_SUMMARY.md (THIS FILE)
   └─ 5-min overview ✓

2. PRICING_AUDIT_FRAMEWORK.md
   └─ Detailed audit framework (30 mins)

3. PRICING_COMPETITIVE_ANALYSIS.md
   └─ Competitive positioning (20 mins)

4. COMPETITOR_AUDIT_TRACKER.md
   └─ Evidence collection template (10 mins)

5. Test Files (3 files in tests/e2e/)
   └─ pricing_audit_budget.spec.ts
   └─ pricing_audit_premium.spec.ts
   └─ pricing_audit_edge_cases.spec.ts
```

---

## 🚨 Critical Red Flags (Need Decisions)

### 1️⃣ Multi-room Booking Fee Cap
**Question**: Is ₹500 cap per-room or per-booking?
- ❓ If per-room: 3 rooms = ₹1,500 (WRONG)
- ✅ Should be: Total = ₹500 (CORRECT)
**Deadline**: Investigate by March 17
**Owner**: Backend Engineer

### 2️⃣ Long Stay Incentive Misalignment
**Problem**: 30-night stay = 0.17% fee rate (too cheap)
- 📊 Current: ₹500 on ₹150K = only 0.33% effective rate
- 🎯 Better: Tiered cap (₹500 per 7 days) = 3.3% rate
**Deadline**: Decide by March 20
**Owner**: Product Manager

### 3️⃣ Promo Code Fee Calculation
**Question**: Fee on original or discounted price?
- ❌ Wrong: Fee on ₹50K (promo doesn't apply to fee)
- ✅ Right: Fee on ₹45K (promo reduces subtotal)
**Deadline**: Verify by March 18
**Owner**: Backend Engineer

### 4️⃣ Group Booking Wholesale
**Problem**: 10-room booking = ₹500 cap (seems too low)
- 📊 Current: ₹300K base gets ₹500 fee (0.17%)
- 🎯 Consider: Minimum fee for wholesale
**Deadline**: Decide by March 20
**Owner**: Product Manager

---

## ✅ Simple Approval Checklist

- [ ] **Code**: pricing_service.py reviewed, no bugs found
- [ ] **Tests**: All 3 test files passing (no failures)
- [ ] **Evidence**: 10 competitor screenshots collected
- [ ] **Red Flags**: 4 flags reviewed, decisions made
- [ ] **Competitive**: Positioning approved by product
- [ ] **Ready**: Engineering confirms EPIC-2 can start

**Sign-off**: When ALL boxes checked → EPIC-2 approved

---

## 🧪 How to Run Tests

```bash
# Install dependencies (if needed)
npm install

# Run all pricing audits
npx playwright test pricing_audit

# Run specific tier
npx playwright test pricing_audit_budget
npx playwright test pricing_audit_premium
npx playwright test pricing_audit_edge_cases

# Generate HTML report
npx playwright show-report

# Run with detailed output
npx playwright test pricing_audit --reporter=list
```

**Expected Result**: All tests passing, nice console output showing competitor comparisons

---

## 📸 How to Collect Screenshots

### For Each Platform:

1. **Navigate**: Go to platform website
2. **Search**: Same hotel as GoExplorer test
3. **Enter Dates**: March 15-18 (3 nights)
4. **Capture**: Full pricing breakdown screenshot
5. **File**: `screenshots/competitor_[PLATFORM]_budget_20240315.png`
6. **Note**: Final total in COMPETITOR_AUDIT_TRACKER.md

### Platforms to Audit:
- [ ] Booking.com
- [ ] Agoda
- [ ] Goibibo
- [ ] MMT (MakeMyTrip)
- [ ] OYO

### For Each Tier (10 total):
- [ ] Budget hotels × 5 platforms = 5 screenshots
- [ ] Premium hotels × 5 platforms = 5 screenshots

---

## 💰 Competitive Positioning (Quick Facts)

### Budget Tier (₹3.5K/night, 3 nights)
```
Cheapest: Agoda (₹10,200)
GoExplorer: ₹11,025 (+8% vs Agoda)
Most expensive: MMT (₹12,296)
Our advantage: Transparent pricing + wallet
```

### Premium Tier (₹25K/night, 2 nights)
```
Cheapest: Agoda (₹49,000)
GoExplorer: ₹50,500 (+3% vs Agoda)
Most expensive: MMT (₹62,466)
Our advantage: Service fee cap (saves ₹9,000 vs Booking)
```

### Messaging
- **Budget**: "Best value with transparent pricing"
- **Premium**: "Save thousands with our fee cap"
- **Both**: "Zero GST Phase-2 advantage"

---

## 🎯 Pricing Components (Reference)

### What We Charge

```
Base Room Price (from database)
  +
Meal Plan Delta (optional)
  =
Subtotal Per Night

Subtotal × Nights × Rooms
  =
Total Before Fee

Total × 5% (capped at ₹500)
  =
Service Fee

Total Before Fee + Service Fee
  =
FINAL PRICE

Final Price - Wallet Balance (optional)
  =
Gateway Payment Amount
```

### What Competitors Charge

| Platform | Service Fee | GST | Total |
|----------|------------|-----|-------|
| GoExplorer | 5% (cap ₹500) | 0% | ✅ Lower |
| Booking | 0% | 12-18% | ❌ Higher |
| Agoda | 0% | Included | ✅ Lower |
| MMT | 3-5% | 12-18% | ❌ Highest |
| OYO | 0% | Included | ✅ Similar |
| Goibibo | 0% | 12-18% | ❌ Higher |

---

## 🔍 Investigation Checklist

### For Backend Engineer

- [ ] Open `backend/pricing_service.py`
- [ ] Find: Service fee calculation line
- [ ] Verify: `min(subtotal * 0.05, 500)` is correct
- [ ] Check: Multi-room fee cap logic
- [ ] Review: Promo code fee calculation
- [ ] Test: Run `pricing_audit_*.spec.ts` files
- [ ] Document: Any issues found

### For QA/Product

- [ ] Open COMPETITOR_AUDIT_TRACKER.md
- [ ] Plan: Which 5 hotels to audit (3-star and 5-star)
- [ ] Schedule: 2-3 hours for screenshot collection
- [ ] Collect: All 10 screenshots
- [ ] Document: In tracker table
- [ ] Verify: Competitor data matches tests

---

## 📱 Next Phase Timeline

```
Week of Mar 15-21: AUDIT PHASE
├─ Mar 15-17: Code review + screenshot collection
├─ Mar 18-19: All tests passing
├─ Mar 19-20: Red flags reviewed
├─ Mar 20: Approval meeting
└─ Mar 21: Final sign-off

Week of Mar 24: EPIC-2 STARTS
├─ Mar 24-31: Inventory locking implementation
├─ Apr 1-7: Integration testing
├─ Apr 8-11: Final QA
└─ Apr 12: Production deployment
```

---

## 🎁 What Success Looks Like

✅ **Code Review Complete**
- No bugs in pricing_service.py
- Service fee cap correctly implemented
- No regressions from current code

✅ **Tests Passing**
- budget test suite: all green
- premium test suite: all green
- edge cases test suite: all green

✅ **Competitor Evidence**
- All 10 screenshots collected
- Prices documented in tracker
- Competitive advantage verified

✅ **Red Flags Resolved**
- Multi-room cap: understood & verified
- Long stay: decision made on next steps
- Promo fee: calculation verified
- Group booking: decision made on wholesale

✅ **Approval Given**
- Product signs off on positioning
- Engineering confirms EPIC-2 ready
- No blockers remain

---

## 🆘 If Something Breaks

**Q: A test is failing**
- A: Check `tests/e2e/[test_file].spec.ts`
- Run with `--reporter=list` for details
- Report issue with console output

**Q: Screenshot collection is slow**
- A: Use desktop browser (faster than mobile)
- Automate with Playwright if possible
- Focus on speed, not perfection

**Q: Red flags aren't clear**
- A: Create GitHub issue: `audit/red-flag-[number]`
- Tag @backend-lead or @product-lead
- Escalate if not resolved in 24 hours

**Q: Can we start EPIC-2 early?**
- A: NO - audit must complete first
- Risk: Pricing regressions, lost trust, refunds
- Worth: 1 week delay for safe scaling

---

## 📞 Quick Contacts

| Role | Name | Slack | Escalation |
|------|------|-------|------------|
| Audit Lead | [TBD] | @[slack] | CTO |
| Backend | [TBD] | @[slack] | Tech Lead |
| QA | [TBD] | @[slack] | QA Manager |
| Product | [TBD] | @[slack] | Head of Product |

**Status Updates**: Daily standup via Slack
**Blockers**: Report immediately to Audit Lead

---

## 💡 Pro Tips

1. **Use this document as a reference** - bookmark it
2. **Run tests locally before committing** - catch regressions early
3. **Screenshot one platform per day** - don't try all 5 at once
4. **Document everything** - helps next audit
5. **Ask questions early** - don't wait until deadline

---

## 📋 Sign-Off

**When you're done with your part**, reply in Slack:

> ✅ [Role]: [Task completed] - [Brief status]

Example:
> ✅ Backend: Pricing code review complete - No bugs found, all tests passing

Once all roles report complete → Audit phase is done → EPIC-2 approved ✅

---

**Document Version**: 1.0
**Last Updated**: March 15, 2024
**Status**: ✅ Ready to Use
**Question?**: Check PRICING_AUDIT_FRAMEWORK.md or ask Audit Lead

