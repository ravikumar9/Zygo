# 🚀 UAT QUICK START GUIDE — MANUAL TESTING READY

**Date:** January 21, 2026  
**Status:** Ready for Manual UAT Execution  
**Tester Role:** Manual validation (no code changes)

---

## ⚡ 30-SECOND SUMMARY

```
✅ Phase-3 implementation COMPLETE
✅ 10/10 automated tests PASSING
✅ GST rules LOCKED & compliant
✅ Code FROZEN (no changes without approval)
✅ You are here: Manual UAT begins NOW
```

---

## 📋 YOUR 7 MANDATORY TESTS

**Test 1: Timer**
- Book hotel, watch 10-min countdown
- Confirm warning appears at <2 min
- Confirm booking expires, inventory releases
- **Expected:** Room available after 10 minutes

**Test 2: Inventory Lock**
- Open 2 browser windows (User A & User B)
- User A books room → User B sees "Unavailable"
- User A cancels → User B sees "Available"
- **Expected:** No overbooking possible

**Test 3: Wallet**
- Book with ₹1,000 wallet balance
- Verify wallet auto-applies
- Verify GST amount NEVER changes (₹1,417.50 stays ₹1,417.50)
- Toggle wallet ON/OFF
- **Expected:** GST constant, only gateway varies

**Test 4: Search**
- Search by name, city, keyword
- Use Near-Me (allow geolocation)
- Use Near-Me (deny geolocation) → fallback works
- Search with dates: same date → reject, future → accept
- **Expected:** All searches work, dates validated

**Test 5: Responsive UI**
- View payment page at 4 widths: 1920px, 1440px, 768px, 375px
- No text truncation, no button overlap
- "Taxes & Fees" visible at 375px
- **Expected:** Perfect layout at all sizes

**Test 6: Cancellation**
- Confirm a booking
- Click "Cancel Booking"
- Verify status changes to "Cancelled"
- Verify room becomes available for rebooking
- Verify notification sent
- **Expected:** Complete cancellation flow works

**Test 7: Invoice**
- View invoice for booked hotel (₹7,500 base)
- Verify totals: ₹9,292.50 (18% GST, ₹1,417.50)
- Verify "Taxes & Fees" breakdown shows ₹1,792.50 (fee + GST)
- Print invoice
- **Expected:** Totals match backend exactly

---

## 🎯 GO / NO-GO RULE

### GO if:
- ✅ All 7 tests PASS
- ✅ No totals mismatches
- ✅ No UI breaks at 375px
- ✅ No GST changes with wallet

### NO-GO if:
- ❌ Timer doesn't expire
- ❌ Inventory doesn't release
- ❌ GST alters with wallet
- ❌ Totals don't match
- ❌ UI breaks at mobile

---

## 📸 WHAT YOU NEED

### Tools:
- [ ] 2 browser windows (Firefox + Chrome, or 2 Chrome windows)
- [ ] Screenshot tool (built-in: Win+Print or browser tools)
- [ ] Spreadsheet (track results)
- [ ] This checklist

### Test Data:
- [ ] Test user account (already created)
- [ ] Test hotel ₹7,500 (for slab switch test)
- [ ] Test bus ₹1,000 (for AC/Non-AC test)
- [ ] Test package ₹5,000 (for composite GST)

### Environment:
- [ ] Staging server running (or production if pre-launch UAT)
- [ ] Database with test bookings
- [ ] Payment gateway in test mode (if testing payments)

---

## ⏱️ TIME ESTIMATE

| Test | Duration | Notes |
|------|----------|-------|
| Timer | 12 min | Must wait for expiry |
| Inventory | 5 min | 2 users, quick |
| Wallet | 5 min | Toggle & verify |
| Search | 5 min | 4 scenarios |
| Responsive | 10 min | 4 breakpoints |
| Cancellation | 5 min | Single flow |
| Invoice | 5 min | View & verify |
| **TOTAL** | **52 min** | Less if parallel |

---

## 🔍 DETAILED CHECKLIST (Copy This)

### Test 1: Timer (12 min)
```
☐ Start new hotel booking
☐ Note current time: _______
☐ Screenshot at 0 min (timer shows 10:00)
☐ Screenshot at 5 min (timer shows 5:00)
☐ Screenshot at 9:50 (timer shows 0:10)
☐ Wait for warning at <2 min
☐ Screenshot warning (timer turns red)
☐ Wait for expiry at 10:00
☐ Screenshot expiry message
☐ Search same hotel in new window
☐ Confirm room now available
Result: ☐ PASS  ☐ FAIL
```

### Test 2: Inventory (5 min)
```
☐ Open Window A (logged in User A)
☐ Open Window B (logged in User B)
☐ User A: Search hotel, click "Continue to Payment"
☐ User B: Search same hotel
☐ Verify in Window B: Room shows "UNAVAILABLE" or "BOOKED"
☐ Confirm User B cannot proceed to payment
☐ User A: Cancel booking
☐ User B: Refresh page
☐ Confirm room now shows "AVAILABLE"
Result: ☐ PASS  ☐ FAIL
```

### Test 3: Wallet (5 min)
```
☐ Start hotel booking ₹7,500 (18% slab)
☐ Reach payment page
☐ Screenshot wallet auto-applied (checked)
☐ Note GST amount: _______
☐ Note total: _______
☐ Uncheck wallet
☐ Screenshot wallet off
☐ Verify GST amount UNCHANGED
☐ Recheck wallet
☐ Screenshot wallet on again
☐ Verify GST amount still UNCHANGED
Result: ☐ PASS  ☐ FAIL
```

### Test 4: Search (5 min)
```
☐ Type hotel name → results shown
☐ Type city name → results shown
☐ Type keyword → results shown
☐ Click "Near Me" → allow geolocation
☐ Screenshot results sorted by distance
☐ Deny geolocation → fallback works
☐ Search with checkin=checkout (same date)
☐ Screenshot error message (should reject)
☐ Search with checkout > checkin
☐ Screenshot results accepted
Result: ☐ PASS  ☐ FAIL
```

### Test 5: Responsive (10 min)
```
☐ Payment page at 1920px → screenshot
  ☐ All elements visible? ☐ Yes ☐ No
  ☐ No horizontal scroll? ☐ Yes ☐ No
☐ Payment page at 1440px → screenshot
  ☐ All elements visible? ☐ Yes ☐ No
  ☐ Layout reflows? ☐ Yes ☐ No
☐ Payment page at 768px → screenshot
  ☐ Single column? ☐ Yes ☐ No
  ☐ No truncation? ☐ Yes ☐ No
☐ Payment page at 375px → screenshot
  ☐ No overlap? ☐ Yes ☐ No
  ☐ "Taxes & Fees" visible? ☐ Yes ☐ No
  ☐ Wallet checkbox accessible? ☐ Yes ☐ No
  ☐ Timer visible? ☐ Yes ☐ No
Result: ☐ PASS  ☐ FAIL
```

### Test 6: Cancellation (5 min)
```
☐ Complete a hotel booking
☐ Navigate to booking detail
☐ Click "Cancel Booking" button
☐ Confirm dialog appears
☐ Click "Yes, Cancel"
☐ Screenshot cancelled status
☐ Verify status shows "CANCELLED"
☐ Search same hotel/dates in new window
☐ Confirm room available for rebooking
☐ Check email for cancellation notification
Result: ☐ PASS  ☐ FAIL
```

### Test 7: Invoice (5 min)
```
☐ Complete booking with ₹7,500 hotel
☐ View booking detail
☐ Click "View Invoice" or "Print Invoice"
☐ Screenshot invoice page
☐ Verify breakdown:
  ☐ Room: ₹7,500.00
  ☐ Platform Fee: ₹375.00
  ☐ Taxable: ₹7,875.00
  ☐ GST (18%): ₹1,417.50
  ☐ Total: ₹9,292.50
☐ Screenshot "Taxes & Fees" section
☐ Verify label visible
☐ Verify breakdown shows ₹1,792.50 (fee + GST)
☐ Click Print → confirm preview
Result: ☐ PASS  ☐ FAIL
```

---

## 🚨 IF YOU FIND A PROBLEM

### Step 1: Screenshot It
```
Take screenshot showing:
- Exact error message
- Page/form where it happened
- Time of occurrence
```

### Step 2: Document It
```
Issue Description:
  What did you expect? _________________
  What actually happened? _________________
  Steps to reproduce: _________________
  
Severity:
  ☐ Critical (feature completely broken)
  ☐ Major (feature works but incorrectly)
  ☐ Minor (cosmetic or small impact)
```

### Step 3: Report It
```
To: Tech Lead, QA Manager
Subject: Manual UAT Issue — [Test Category] [Critical/Major/Minor]
Attachments: Screenshots, error logs

Do NOT:
  ❌ Fix the code yourself
  ❌ Try to work around it
  ❌ Change anything
  ⏸️ Just wait for approval
```

---

## ✅ COMPLETION CHECKLIST

When all 7 tests done:

```
☐ All 7 tests executed
☐ All results documented (PASS or FAIL)
☐ All screenshots collected
☐ No critical issues found (or documented)
☐ GO/NO-GO decision made:
    ☐ GO → Ready for production
    ☐ NO-GO → Issues must be fixed first
☐ Report submitted to stakeholders
☐ Date/time recorded: _______
```

---

## 💡 TIPS

### Timer Test
- Start at a :00 second mark for easy tracking
- Screenshot at exactly 5-min mark
- Don't miss the warning between 1:50-2:00

### Inventory Test
- Use 2 completely separate browser windows
- Clear cache between tests if needed
- Don't use incognito/private (can share sessions)

### Wallet Test
- Hotel ₹7,500 should have GST ₹1,417.50 (18% slab)
- Don't use wallet with smaller amounts (rounding confuses)
- Check exact decimals: ₹1,417.50 must stay ₹1,417.50

### Responsive Test
- Use browser DevTools (F12) → Toggle Device Toolbar
- Test on real mobile device if possible
- Check at exactly 375px (minimum mobile width)

### Cancellation Test
- Must use a completed booking (past payment)
- Can't cancel unconfirmed bookings
- Check email spam folder for notifications

### Invoice Test
- Download PDF if available (check math on PDF too)
- Print preview may show different formatting
- Compare with backend pricing_calculator.py output

---

## 📞 SUPPORT

### Questions?
- Check [MANUAL_UAT_EXECUTION_CHECKLIST.md](MANUAL_UAT_EXECUTION_CHECKLIST.md) for detailed test steps
- Check [CODE_FREEZE_ENFORCEMENT_NOTICE.md](CODE_FREEZE_ENFORCEMENT_NOTICE.md) if you need to report a bug

### Stuck?
- Slack: #uat-testing channel
- Email: [qa-team@company.com](mailto:qa-team@company.com)
- Critical: Contact Tech Lead directly

### Reference Docs:
- [FINAL_COMPLIANCE_SEAL_INDIA_GST.md](FINAL_COMPLIANCE_SEAL_INDIA_GST.md) — Tax rules
- [DEPLOYMENT_GO_NO_GO_FINAL.md](DEPLOYMENT_GO_NO_GO_FINAL.md) — GO/NO-GO criteria
- [PRICING_TAX_VALIDATION.md](PRICING_TAX_VALIDATION.md) — Sample invoices

---

## 🏁 YOU'RE READY

```
✅ Code is locked (nothing will change)
✅ Tests are prepared (7 scenarios)
✅ Tools are ready (screenshots, checklist)
✅ Success criteria are clear (GO/NO-GO)
✅ Support is available (if issues)

BEGIN MANUAL UAT NOW
```

---

**UAT Quick Start Guide — Phase-3 Final**  
**Generated:** January 21, 2026  
**Estimated Duration:** 52 minutes  
**Status:** Ready to Execute  
