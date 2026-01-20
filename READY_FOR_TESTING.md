# ✅ READY FOR ZERO-TOLERANCE TESTING

**Server Status:** ✅ Running at http://127.0.0.1:8000/  
**Commit:** c5708d6  
**Test Date:** January 20, 2026  
**Tester Role:** QA Lead (Real Chrome browser required)

---

## 🔐 LOGIN CREDENTIALS

```
Email: qa_both_verified@example.com
Password: Test@1234
```

**Pre-seeded Test Data:**
- ✅ Wallet Balance: ₹2000.00
- ✅ Promo Codes: WELCOME500 (₹500 off), USER1000 (₹1000 off)
- ✅ Test Hotel: ₹8000 base price
- ✅ GST: 18%

---

## 📋 7 TEST SCENARIOS (FROM CHECKLIST)

### TEST 1: BASE + GST (No Promo, No Wallet)
**Expected:** ₹9440 total everywhere

1. Open http://127.0.0.1:8000/
2. Login with above credentials
3. Create hotel booking: ₹8000 base
4. On `/bookings/{id}/confirm/`:
   - [ ] Base Amount: ₹8000.00
   - [ ] GST: ₹1440.00
   - [ ] Total: ₹9440.00
5. Click "Proceed to Payment"
6. On `/bookings/{id}/payment/`:
   - [ ] Base: ₹8000.00
   - [ ] GST: ₹1440.00
   - [ ] Total: ₹9440.00 ← **MUST MATCH CONFIRM**
7. Back arrow → View booking `/bookings/{id}/`:
   - [ ] Base: ₹8000.00
   - [ ] GST: ₹1440.00
   - [ ] Total: ₹9440.00 ← **MUST MATCH PAYMENT**

**PASS CRITERIA:** All three pages show ₹9440

---

### TEST 2: PROMO + GST (WELCOME500)
**Expected:** ₹8850 total (base ₹8000 - promo ₹500 = ₹7500, +18% GST = ₹8850)

1. Create new ₹8000 hotel booking
2. On confirmation page, enter: `WELCOME500`
3. Click "Apply"
   - [ ] Green message: "✓ WELCOME500 applied"
4. Verify breakdown:
   - [ ] Base: ₹8000.00
   - [ ] Promo: -₹500.00
   - [ ] Subtotal: ₹7500.00
   - [ ] GST: ₹1350.00 ← **KEY: 18% of ₹7500, NOT ₹1440**
   - [ ] Total: ₹8850.00
5. "Proceed to Payment"
6. Payment page MUST show:
   - [ ] Base: ₹8000.00
   - [ ] Promo: -₹500.00
   - [ ] Subtotal: ₹7500.00
   - [ ] GST: ₹1350.00
   - [ ] Total: ₹8850.00

**FAIL CONDITION:** If GST = ₹1440 (wrong calculation)

---

### TEST 3: WALLET CHECKBOX BEHAVIOR
**Expected:** Checkbox toggles; breakdown shows/hides; button updates

1. On payment page (₹8850 total):
2. **DEFAULT STATE:**
   - [ ] Checkbox is UNCHECKED
   - [ ] Wallet breakdown HIDDEN
   - [ ] Button: "Pay ₹8850.00 via RAZORPAY"
3. **CHECK Wallet:**
   - [ ] Page reloads with `?use_wallet=true` in URL
   - [ ] Wallet breakdown appears:
     - [ ] Wallet Applied: -₹2000.00 (shown)
     - [ ] Gateway Payable: ₹6850.00 (shown)
   - [ ] Button changes: "Pay ₹6850.00 via RAZORPAY"
4. **UNCHECK Wallet:**
   - [ ] Page reloads with `?use_wallet=false`
   - [ ] Breakdown disappears
   - [ ] Button: "Pay ₹8850.00 via RAZORPAY"

**FAIL CRITERIA:**
- Wallet is radio button (should be checkbox)
- Cannot toggle
- Button doesn't update
- Amount calculation wrong

---

### TEST 4A: WALLET > TOTAL (NEW FIX - CRITICAL)
**Expected:** Auto-confirm without gateway payment

1. Create booking with ₹1000 base → ₹1180 total (with 18% GST)
2. On payment page:
   - [ ] **Gateway options are COMPLETELY HIDDEN**
   - [ ] Green message: "Wallet balance covers full amount"
   - [ ] Button text: "Confirm Booking (₹1180 from Wallet)"
3. Click button
   - [ ] NO Razorpay popup appears
   - [ ] Page redirects to booking detail
4. Verify booking detail:
   - [ ] Booking Status: **CONFIRMED** (not reserved)
   - [ ] Payment Status: **PAID**
   - [ ] Shows "Payment: Wallet"
5. Check wallet:
   - [ ] Wallet reduced from ₹2000 → ₹820

**FAIL CRITERIA:**
- Gateway still visible
- Button says "Pay via Razorpay"
- Booking still reserved after confirmation

---

### TEST 4B: WALLET < TOTAL
**Expected:** Partial wallet + gateway payment

1. Booking: ₹8000 → ₹9440 total
2. On payment page (wallet ₹2000):
   - [ ] Wallet breakdown VISIBLE
   - [ ] Wallet Applied: ₹2000
   - [ ] Gateway Payable: ₹7440
   - [ ] Button: "Pay ₹7440.00 via RAZORPAY"
3. Gateway options VISIBLE (razorpay/upi/netbanking)
4. User must select gateway

---

### TEST 5: PROMO VALIDATION
**Valid Promo:**
1. Enter `WELCOME500` → Green success
2. Discount applied → Total reduced

**Invalid Promo:**
1. Enter `INVALID123` → Red error: "Invalid promo code"
2. No discount applied

**Minimum Amount:**
1. Create ₹500 booking (too small)
2. Enter `WELCOME500` → Error: "Minimum booking amount required"

**Remove Promo:**
1. Apply `WELCOME500` → Applied
2. Click "Remove" button
3. Promo clears
4. Total recalculates: Back to ₹1090 (₹500 + 18% GST)

---

### TEST 6: CONFIRMED BOOKING 403 GUARD
**Expected:** Cannot access payment page for confirmed booking

1. Use confirmed booking ID
2. Try: http://127.0.0.1:8000/bookings/{id}/payment/
3. **Expected Response:** HTTP 403 Forbidden
4. **Error Message:** "Booking is in Confirmed status. Payment is no longer allowed."

**FAIL:** If page loads normally

---

### TEST 7: CROSS-PAGE CONSISTENCY
**Expected:** Same total on all three pages

1. Create ANY booking with promo
2. Record from `/bookings/{id}/confirm/`: `₹________`
3. Record from `/bookings/{id}/payment/`: `₹________`
4. Record from `/bookings/{id}/`: `₹________`

**PASS ONLY IF:** All three values IDENTICAL

Also verify:
- [ ] All pages show GST line
- [ ] All pages show Promo line (if applied)

---

## 📊 ADDITIONAL VERIFICATION

### Countdown Timer
1. On confirmation page: Timer shows (MM:SS format)
2. On payment page: Timer shows
3. Timer counts down every second
4. At 0: Button disables, page redirects

### Cancel Booking
1. On any confirmed booking detail page:
2. Click "Cancel Booking"
3. Shows success message
4. Booking status: CANCELLED
5. Wallet increased by refund amount

### Room Selection
1. On hotel detail page:
2. **NO "Select Room" buttons** visible on room cards
3. Only ONE room dropdown exists below
4. Select room from dropdown updates:
   - [ ] Room details
   - [ ] Pricing
   - [ ] Meal plans

---

## 🔍 LOGS TO MONITOR

Open new terminal, run:
```powershell
Get-Content "c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear\logs\django.log" -Tail 30 -Wait
```

**Look for (Good Signs):**
- `[CONFIRM_PAGE_PRICING]` - pricing calculated
- `[PAYMENT_PAGE_PRICING]` - wallet included
- `[WALLET_ONLY_CONFIRMED]` - wallet-only worked
- `[CONFIRM_PROMO_APPLIED]` - promo registered
- No errors or exceptions

**Red Flags:**
- `[PRICING_CALC_ERROR]` - calculation crashed
- `[WALLET_ONLY_CONFIRM_ERROR]` - confirmation failed
- Exception tracebacks

---

## 📸 SCREENSHOT REQUIREMENTS

For each test, capture:
1. **Full page screenshot** at 100% zoom
2. **Pricing breakdown** (confirm page)
3. **Payment page** with wallet/gateway options
4. **Booking detail** page
5. **Any error messages** (if failure)

---

## ✍️ REPORTING FORMAT

For each **PASSED** test:
```
✅ TEST SCENARIO 1: PASSED
Evidence: All three pages show ₹9440
Screenshot: [test1_100zoom.png, test1_payment.png]
```

For each **FAILED** test:
```
❌ TEST SCENARIO 2: FAILED
Issue: GST calculated incorrectly
Expected: ₹1350 (18% of ₹7500)
Actual: ₹1440 (on ₹8000 base)
Page: /bookings/abc123/payment/
Screenshots: [gst_wrong.png, detail_wrong.png]
Logs: [error_excerpt.txt]
```

---

## 🎯 ACCEPTANCE CRITERIA

**System PASSES if:**
- ✅ All 7 test scenarios PASS
- ✅ No crashes or exceptions
- ✅ Cross-page consistency verified
- ✅ Wallet-only confirmation works
- ✅ Promo validation prevents invalid entries
- ✅ 403 guard blocks confirmed booking re-payment

**System FAILS if:**
- ❌ ANY test scenario fails
- ❌ ANY page shows different amount
- ❌ GST calculated on wrong base
- ❌ Wallet checkout doesn't auto-confirm
- ❌ Crashes or exceptions in logs

---

## 📞 EMERGENCY CHECKLIST

If tests fail:

1. **Clear browser cache:** Ctrl+Shift+Delete → Clear all
2. **Hard refresh:** Ctrl+Shift+R
3. **Use Incognito:** Ctrl+Shift+N (fresh session)
4. **Check logs:** Are there errors?
5. **Verify test data:** Wallet still ₹2000?
6. **Re-seed if needed:** `python seed_test_data.py`
7. **Restart server:** Stop and start Django

---

## 🚀 READY?

1. ✅ Server running at http://127.0.0.1:8000/
2. ✅ Login: qa_both_verified@example.com / Test@1234
3. ✅ 7 test scenarios ready in ZERO_TOLERANCE_TEST_CHECKLIST.md
4. ✅ Backend implementation complete

**BEGIN TESTING NOW** → No more code work possible without your browser verification.

