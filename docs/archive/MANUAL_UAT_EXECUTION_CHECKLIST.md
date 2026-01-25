# 🧪 MANUAL UAT EXECUTION CHECKLIST — PHASE-3 FINAL
## Final Verification Before Production Deployment

**Date:** January 21, 2026  
**Status:** 🔒 CODE FROZEN (Implementation Complete)  
**Phase:** Manual UAT Only (No Code Changes Without Test Failure)  
**Authority:** Post-Freeze Deployment Guidance

---

## 📋 UAT SCOPE & RULES

### ✅ WHAT IS ALLOWED NOW

Only manual verification of **existing behavior**:
- Observe features (don't modify code)
- Log results (evidence required)
- Document mismatches (if found)
- Proceed to GO/NO-GO decision

### ❌ WHAT IS NOT ALLOWED

🚫 **Code Changes Strictly Prohibited UNLESS:**
- A manual test reveals a **functional break**, OR
- A **calculation mismatch is proven with evidence**

🚫 **Forbidden Operations:**
- ✋ Change GST logic
- ✋ Touch [bookings/pricing_calculator.py](bookings/pricing_calculator.py)
- ✋ Modify tax labels
- ✋ Adjust wallet logic
- ✋ Refactor UI labels
- ✋ "Optimize" anything without failing test

---

## 🎯 MANDATORY MANUAL CHECKS (7 Categories)

### 1️⃣ TIMER (10-Minute Reservation Window)

**Objective:** Verify countdown, warning, expiry, and inventory release

**Setup:**
```
- Start new hotel booking
- Observe price detail page
- Note current time (T=0)
```

**Test 1A: Countdown Visible**
```
Expected: Timer counting down from 10:00 to 0:00
Evidence: Screenshot at T=0 min, T=5 min, T=9 min 50 sec
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Test 1B: Warning at < 2 Minutes**
```
Expected: Warning message appears at ~1:55
          Timer turns red/orange
          Additional warning text shows
Evidence: Screenshot at 1:55 mark
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Test 1C: Expiry & Auto-Cancellation**
```
Expected: At T=10:00
          - Booking auto-cancels
          - Timer disappears
          - User redirected to search/home
          - Error message: "Reservation expired"
Evidence: Screenshot of expired state
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Test 1D: Inventory Release After Expiry**
```
Expected: After expiry (T=10:00)
          - Same room available for new booking
          - No "already booked" error
          - Other users can now book
Setup:    - Book room in User A session
          - Wait for expiry
          - Try booking same room in User B session
Evidence: Screenshot showing room available in User B
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Summary for Timer:**
- ✅ All 4 sub-tests PASS → Timer verified
- ❌ Any test FAIL → NO-GO (Must fix)

---

### 2️⃣ INVENTORY LOCKING (Multi-User Concurrency)

**Objective:** Verify room lock, visibility, and release

**Setup:**
```
- Open 2 browser windows (User A & User B)
- Both logged in
- Same hotel room ₹7,500
```

**Test 2A: User A Locks Room**
```
Expected: User A clicks "Continue to Payment"
          - User A sees room locked (timer starts)
          - Payment page shows price ₹9,292.50
Evidence: Screenshot of User A locked room
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Test 2B: User B Sees Unavailable**
```
Expected: User B searches same hotel
          - Room shows "UNAVAILABLE" or "BOOKED"
          - Cannot proceed to payment
          - Calendar blocks dates
Evidence: Screenshot of unavailable status for User B
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Test 2C: User A Cancels → Releases Lock**
```
Expected: User A cancels booking (from payment page or confirmation)
          - Room becomes available instantly
          - User B refreshes → sees "Available"
Evidence: Screenshot of room becoming available
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Test 2D: User A Allows Expiry → Releases Lock**
```
Expected: User A starts booking
          - Does NOT complete within 10 min
          - Timer expires
          - User B can now book same room
Setup:    - Start booking in User A
          - Wait ~10 minutes
          - User B searches same room
Evidence: Screenshot showing room available after expiry
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Summary for Inventory:**
- ✅ All 4 sub-tests PASS → Inventory locking verified
- ❌ Any test FAIL → NO-GO (Must fix)

---

### 3️⃣ WALLET UX (Auto-Apply, Toggle, GST Preservation)

**Objective:** Verify wallet behavior, toggle, and GST integrity

**Setup:**
```
- User with ₹1,000 wallet balance
- Hotel booking ₹7,500 (expects 18% GST)
- Total expected: ₹9,292.50
- GST amount expected: ₹1,417.50
```

**Test 3A: Wallet Auto-Applies on Payment Page**
```
Expected: User reaches payment page
          - Wallet checkbox is PRE-CHECKED (auto-apply)
          - Breakdown shows:
            Total: ₹9,292.50
            Wallet: -₹1,000.00
            Gateway: ₹8,292.50
          - GST amount shown: ₹1,417.50 (unchanged)
Evidence: Screenshot of auto-applied wallet
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Test 3B: Wallet Toggle OFF**
```
Expected: User unchecks wallet checkbox
          - Breakdown updates to:
            Total: ₹9,292.50 (unchanged)
            Wallet: ₹0.00
            Gateway: ₹9,292.50
          - GST still ₹1,417.50 (unchanged)
Evidence: Screenshot of wallet unchecked
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Test 3C: Wallet Toggle ON**
```
Expected: User rechecks wallet
          - Gateway drops to ₹8,292.50
          - GST still ₹1,417.50 (preserved)
          - Total still ₹9,292.50 (preserved)
Evidence: Screenshot of wallet re-applied
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Test 3D: GST NOT Affected by Wallet**
```
Expected: Across all 3 states (auto/off/on):
          GST amount = ₹1,417.50 (always)
          Total = ₹9,292.50 (always)
          Only Gateway varies (9,292.50 or 8,292.50)
Evidence: Screenshots showing GST constant
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Summary for Wallet:**
- ✅ All 4 sub-tests PASS → Wallet verified
- ❌ Any test FAIL → NO-GO (Must fix)

---

### 4️⃣ SEARCH & GEOLOCATION (Universal + Near-Me + Distance)

**Objective:** Verify search, Near-Me filtering, geolocation fallback

**Setup:**
```
- Clear browser location
- Various hotels in different cities/distances
```

**Test 4A: Universal Search**
```
Expected: Search box accepts:
          - Hotel name
          - City name
          - Address
          - Keyword
Setup:    Type "Mumbai" → Should show Mumbai hotels
          Type "Luxury" → Should show luxury hotels
Evidence: Screenshots of search results
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Test 4B: Near-Me with Geolocation**
```
Expected: Browser asks permission
          - "Allow" geolocation
          - Results sorted by distance (nearest first)
          - Distance shown: "2.3 km away"
Setup:    Click "Near Me" or "Show Nearby"
Evidence: Screenshot showing sorted results + distances
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Test 4C: Near-Me with Fallback (No Geolocation)**
```
Expected: Browser denies location
          - System shows fallback message
          - Optional: Show all hotels (unfiltered)
          - Or: Ask user to enter city
Setup:    Click "Near Me" → Deny permission
Evidence: Screenshot of fallback behavior
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Test 4D: Date Validation (checkout > checkin)**
```
Expected: 
- Same dates (checkin = checkout) → REJECTED
  Error: "Checkout must be after check-in"
- Future dates (checkout > checkin) → ACCEPTED
  Results shown
Setup:    Try search with:
          1. Checkin: Jan 25, Checkout: Jan 25 → Should reject
          2. Checkin: Jan 25, Checkout: Jan 26 → Should accept
Evidence: Screenshots of validation
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Summary for Search:**
- ✅ All 4 sub-tests PASS → Search verified
- ❌ Any test FAIL → NO-GO (Must fix)

---

### 5️⃣ RESPONSIVE UI (4 Breakpoints)

**Objective:** Verify no truncation/overlap at mobile widths

**Setup:**
```
- Open payment page in browser dev tools
- Resize to each breakpoint
- Check all key elements
```

**Test 5A: Desktop (100% / 1920px)**
```
Expected: Full layout
          - 3-column grid (if applicable)
          - No overflow
          - All text readable
          - Buttons clickable
Evidence: Screenshot at 1920px
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Test 5B: Tablet Large (75% / 1440px)**
```
Expected: Still clear
          - Possibly 2-column layout
          - No truncation
          - "Taxes & Fees" section visible
          - Wallet toggle visible
Evidence: Screenshot at 1440px
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Test 5C: Tablet Small (50% / 768px)**
```
Expected: 1-column layout
          - Stacked elements
          - No horizontal scroll
          - Text wrap, not truncate
          - Buttons full-width or aligned
Evidence: Screenshot at 768px
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Test 5D: Mobile (375px)**
```
Expected: Minimal layout
          - Single column
          - NO overlap of text/buttons
          - NO truncation ("..." appears only intentionally)
          - "Taxes & Fees" label visible
          - Wallet checkbox accessible
          - Timer countdown visible (or in collapsible)
Evidence: Screenshot at 375px with all elements visible
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Summary for Responsive:**
- ✅ All 4 breakpoints PASS → UI verified
- ❌ Any breakpoint FAIL → NO-GO (Must fix)

---

### 6️⃣ CANCELLATION (Status, Inventory Release, Notifications)

**Objective:** Verify booking cancellation lifecycle

**Setup:**
```
- Confirm a booking (move past payment)
- Have booking in "Confirmed" status
```

**Test 6A: Cancel Confirmed Booking**
```
Expected: User navigates to booking detail
          - "Cancel Booking" button visible
          - Click → Confirmation dialog: "Sure?"
          - Click "Yes" → Booking cancelled
Evidence: Screenshot of cancel dialog
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Test 6B: Status Updates to "Cancelled"**
```
Expected: After cancellation:
          - Booking status = "CANCELLED"
          - Status page shows cancellation date/time
          - "Active" booking removed from dashboard
Evidence: Screenshot of cancelled booking detail
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Test 6C: Inventory Released**
```
Expected: Room becomes available for rebooking
          - Other users can now book same dates
          - Lock is released
Setup:    Cancel booking → Search same room in new window
Evidence: Screenshot showing room available
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Test 6D: Notification Sent**
```
Expected: Cancellation confirmation notification:
          - Email sent (check inbox or test logs)
          - In-app notification shown (if applicable)
          - Refund info displayed (if applicable)
Evidence: Screenshot of notification / Email receipt
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Summary for Cancellation:**
- ✅ All 4 sub-tests PASS → Cancellation verified
- ❌ Any test FAIL → NO-GO (Must fix)

---

### 7️⃣ INVOICE PRINT & VERIFICATION

**Objective:** Verify invoice totals match backend and show correct "Taxes & Fees"

**Setup:**
```
- Confirmed booking with:
  - ₹7,500 hotel (18% GST)
  - ₹1,000 wallet applied
```

**Test 7A: Invoice Accessible**
```
Expected: User navigates to booking detail
          - "View Invoice" or "Print Invoice" button visible
          - Click → Invoice page opens
          - Invoice shows all details
Evidence: Screenshot of invoice page
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Test 7B: Totals Match Backend**
```
Expected: Invoice shows:
          Room Tariff:     ₹7,500.00
          Platform Fee:    +₹375.00 (5%)
          Subtotal:        ₹7,875.00
          GST (18%):       +₹1,417.50
          Total:           ₹9,292.50
          Wallet Applied:  -₹1,000.00
          Gateway Payable: ₹8,292.50
Compare:  Backend pricing_calculator.py result
Evidence: Screenshots (invoice + backend logs)
Result:   ☐ PASS  ☐ FAIL (Describe mismatch if failed)
Notes:    _________________________________
```

**Test 7C: "Taxes & Fees" Breakdown**
```
Expected: Invoice clearly shows:
          "TAXES & FEES: ₹1,792.50"
          Breakdown:
          - Platform Fee: ₹375.00
          - GST (18%): ₹1,417.50
          (Or single row if format varies)
Evidence: Screenshot of breakdown section
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Test 7D: Print Functionality**
```
Expected: Print button works
          - Browser print dialog appears
          - PDF preview shows correct layout
          - No content cut off in print
Evidence: Screenshot of print preview
Result:   ☐ PASS  ☐ FAIL
Notes:    _________________________________
```

**Summary for Invoice:**
- ✅ All 4 sub-tests PASS → Invoice verified
- ❌ Any test FAIL → NO-GO (Must fix)

---

## 🚦 GO / NO-GO DECISION TREE

### ✅ GO IF:

```
Timer:        ALL 4 PASS (countdown, warning, expiry, release)
Inventory:    ALL 4 PASS (lock, visibility, cancel-release, expiry-release)
Wallet:       ALL 4 PASS (auto-apply, toggle, GST preserved constant)
Search:       ALL 4 PASS (universal, geolocation, fallback, date validation)
Responsive:   ALL 4 PASS (100%, 75%, 50%, 375px — no overlap/truncation)
Cancellation: ALL 4 PASS (button, status, inventory, notification)
Invoice:      ALL 4 PASS (accessible, totals match, breakdown, print)

AND:
- NO GST amount differs across pages
- NO UI break at mobile width
- NO wallet alters GST
```

### ❌ NO-GO IF:

```
Timer fails to expire
  → Inventory not released after 10 min
  → Room remains locked indefinitely
  
Inventory does not release
  → Other users cannot book after expiry/cancel
  → Room shows unavailable incorrectly
  
GST amount differs across pages
  → Invoice shows ₹1,417.50, payment shows ₹1,400.00
  → Totals don't match
  
Wallet alters GST
  → With wallet: GST changes from ₹1,417.50 to ₹1,300.00
  → Preserved wallet rule violated
  
UI breaks below 375px
  → Text truncated
  → Buttons overlap
  → "Taxes & Fees" label not visible
```

---

## 📊 FINAL UAT REPORT TEMPLATE

### UAT EXECUTION REPORT
**Date:** ___________  
**Tester:** ___________  
**Environment:** ___________  

#### Summary
```
PASS: ___/7 categories
FAIL: ___/7 categories
CRITICAL ISSUES: ___
MINOR ISSUES: ___
```

#### Results by Category

| Category | Status | Notes |
|----------|--------|-------|
| Timer | ☐ PASS ☐ FAIL | |
| Inventory | ☐ PASS ☐ FAIL | |
| Wallet | ☐ PASS ☐ FAIL | |
| Search | ☐ PASS ☐ FAIL | |
| Responsive | ☐ PASS ☐ FAIL | |
| Cancellation | ☐ PASS ☐ FAIL | |
| Invoice | ☐ PASS ☐ FAIL | |

#### Issues Found
```
Issue 1: ___________________________________
Severity: Critical / Major / Minor
Evidence: ___________________________________

Issue 2: ___________________________________
Severity: Critical / Major / Minor
Evidence: ___________________________________
```

#### Recommendation
```
☐ GO FOR PRODUCTION (All pass, no critical issues)
☐ GO WITH CAUTION (Minor issues, can be fixed post-launch)
☐ NO-GO (Critical issues found, must fix before launch)
```

---

## 🔒 CODE FREEZE ENFORCEMENT

**Status:** 🔴 CODE LOCKED (No Changes Without Test Failure)

**Permitted Actions:**
- ✅ Execute manual tests (observe only)
- ✅ Document results (evidence required)
- ✅ Log issues (with screenshots)
- ✅ Report findings (no modifications)

**Prohibited Actions:**
- 🚫 Modify [bookings/pricing_calculator.py](bookings/pricing_calculator.py)
- 🚫 Change GST rates or logic
- 🚫 Update UI labels or responsive styles
- 🚫 Alter wallet logic
- 🚫 "Fix" things without failing test proof

**Code Change Approval:** Only if manual test proves:
1. **Functional Break** (feature doesn't work at all), OR
2. **Calculation Mismatch** (with evidence: screenshots, logs)

**Approval Authority:** Tech Lead + QA Manager

---

## 📋 EXECUTION GUIDELINES

### Before You Start
- [ ] Read all 7 test categories
- [ ] Prepare 2 browser windows
- [ ] Have screenshot tool ready
- [ ] Have test report template open
- [ ] Note current time (start of Timer test)

### During Testing
- [ ] Take screenshots for EVERY test
- [ ] Note exact times (for Timer tests)
- [ ] Record any error messages (copy exact text)
- [ ] Test on actual device (not just browser resize)
- [ ] Check both mobile & desktop experiences

### After Testing
- [ ] Compile all screenshots
- [ ] Fill in UAT report
- [ ] Determine GO / NO-GO
- [ ] Submit report to stakeholders
- [ ] Schedule deployment (if GO) or fixes (if NO-GO)

---

## 🏁 FINAL DEPLOYMENT GATE

**All manual tests must PASS to proceed:**

```
✅ Timer:        Go / No-Go ___________
✅ Inventory:    Go / No-Go ___________
✅ Wallet:       Go / No-Go ___________
✅ Search:       Go / No-Go ___________
✅ Responsive:   Go / No-Go ___________
✅ Cancellation: Go / No-Go ___________
✅ Invoice:      Go / No-Go ___________

FINAL DECISION: ☐ GO | ☐ NO-GO

Approved By: ________________________
Date: _______________________________
```

---

**Manual UAT Checklist — Phase-3 Final**  
**Generated:** January 21, 2026  
**Status:** 🔒 CODE FROZEN (Implementation Complete)  
**Next Step:** Execute all 7 categories, report results, proceed to deployment or fixes  
