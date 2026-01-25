# ZERO-TOLERANCE MANUAL TESTING CHECKLIST

## PREPARATION

1. **Run Test Data Seeding:**
   ```bash
   python seed_test_data.py
   ```
   Expected Output:
   - ✅ Wallet seeded: ₹2000.00
   - ✅ Promo codes seeded: WELCOME500, USER1000
   - ✅ Test bookings ready

2. **Start Server:**
   ```bash
   python manage.py runserver --noreload --verbosity 3
   ```

3. **Login Credentials:**
   - Email: `qa_both_verified@example.com`
   - Password: `Test@1234`

---

## TEST SCENARIO 1: BASE + GST (No Promo, No Wallet)

**Create new hotel booking (₹8000 base amount)**

### ✅ CONFIRMATION PAGE (`/bookings/{id}/confirm/`)
- [ ] Base Amount shows: ₹8000.00
- [ ] GST (18%) shows: ₹1440.00
- [ ] Total Payable shows: ₹9440.00
- [ ] Wallet Balance shows: ₹2000.00
- [ ] Promo input field visible

### ✅ PAYMENT PAGE (`/bookings/{id}/payment/`)
- [ ] Base Amount shows: ₹8000.00
- [ ] GST (18%) shows: ₹1440.00
- [ ] Total Payable shows: ₹9440.00
- [ ] **SAME AS CONFIRM PAGE**

### ✅ BOOKING DETAIL PAGE (`/bookings/{id}/`)
- [ ] Base Amount shows: ₹8000.00
- [ ] GST (18%) shows: ₹1440.00
- [ ] Total Payable shows: ₹9440.00
- [ ] **SAME AS CONFIRM & PAYMENT**

**❌ FAIL IF:** Any page shows different numbers

---

## TEST SCENARIO 2: PROMO + GST (WELCOME500)

**On confirmation page:**

### ✅ PROMO APPLICATION
- [ ] Enter promo code: `WELCOME500`
- [ ] Click "Apply"
- [ ] Green success message: "✓ WELCOME500 applied"

### ✅ CONFIRMATION PAGE PRICING
- [ ] Base Amount: ₹8000.00
- [ ] Promo Discount: -₹500.00
- [ ] Subtotal: ₹7500.00
- [ ] GST (18% on ₹7500): ₹1350.00
- [ ] Total Payable: ₹8850.00

### ✅ PAYMENT PAGE (Click "Proceed to Payment")
- [ ] Base Amount: ₹8000.00
- [ ] Promo Discount: -₹500.00
- [ ] Subtotal: ₹7500.00
- [ ] GST (18%): ₹1350.00
- [ ] Total Payable: ₹8850.00
- [ ] **MATCHES CONFIRM PAGE EXACTLY**

### ✅ CALCULATION ORDER VERIFICATION
```
Base: ₹8000
- Promo: -₹500
= Subtotal: ₹7500
+ GST (18% of ₹7500): +₹1350
= Total: ₹8850
```

**❌ FAIL IF:** 
- GST calculated on ₹8000 instead of ₹7500
- Any page shows different total

---

## TEST SCENARIO 3: WALLET CHECKBOX

**On payment page with ₹8850 total:**

### ✅ WALLET UNCHECKED (Default)
- [ ] Checkbox is UNCHECKED
- [ ] Wallet breakdown HIDDEN
- [ ] Button text: "Pay ₹8850.00 via RAZORPAY"
- [ ] Gateway amount: ₹8850.00

### ✅ WALLET CHECKED
- [ ] Check the "Use Wallet Balance" checkbox
- [ ] Page reloads with `?use_wallet=true`
- [ ] Wallet breakdown VISIBLE
- [ ] Wallet Applied: -₹2000.00 (green)
- [ ] Gateway Payable: ₹6850.00 (orange)
- [ ] Button text: "Pay ₹6850.00 via RAZORPAY"

### ✅ WALLET TOGGLE
- [ ] Uncheck wallet checkbox
- [ ] Page reloads with `?use_wallet=false`
- [ ] Wallet breakdown HIDDEN
- [ ] Button text: "Pay ₹8850.00 via RAZORPAY"

**❌ FAIL IF:**
- Wallet is a radio button (not checkbox)
- Cannot combine wallet + gateway
- Button text doesn't update
- Gateway amount incorrect

---

## TEST SCENARIO 4: WALLET EDGE CASES

### ✅ CASE A: Wallet > Total (Wallet ₹2000, Total ₹1500)
**Create booking with ₹1000 base → ₹1180 total**
- [ ] Check wallet
- [ ] Wallet Applied: ₹1180.00
- [ ] Gateway Payable: ₹0.00
- [ ] Button text: "Confirm using Wallet"

### ✅ CASE B: Wallet < Total (Wallet ₹2000, Total ₹10000)
**Create booking with ₹8000 base → ₹9440 total**
- [ ] Check wallet
- [ ] Wallet Applied: ₹2000.00
- [ ] Gateway Payable: ₹7440.00
- [ ] Button text: "Pay ₹7440.00 via RAZORPAY"

**❌ FAIL IF:** Wallet applied > min(wallet_balance, total)

---

## TEST SCENARIO 5: PROMO VALIDATION

### ✅ VALID PROMO
- [ ] Enter `WELCOME500`
- [ ] Shows success message
- [ ] Discount applied correctly

### ✅ INVALID PROMO
- [ ] Enter `INVALID123`
- [ ] Shows error: "Invalid promo code"
- [ ] No discount applied

### ✅ MINIMUM AMOUNT CHECK
- [ ] Create booking < ₹1000 base
- [ ] Apply WELCOME500
- [ ] Should show error: "Minimum booking amount required"

### ✅ REMOVE PROMO
- [ ] Apply WELCOME500
- [ ] Click "Remove" button
- [ ] Discount removed
- [ ] Total recalculates to base + GST

**❌ FAIL IF:** Invalid promo accepted OR minimum amount not enforced

---

## TEST SCENARIO 6: CONFIRMED BOOKING GUARD (403)

**Use existing confirmed booking:**

### ✅ PAYMENT PAGE ACCESS
- [ ] Get booking_id of confirmed booking
- [ ] Try to access `/bookings/{id}/payment/`
- [ ] Receives HTTP 403 Forbidden
- [ ] Error message: "Booking is in Confirmed status. Payment is no longer allowed."

### ✅ DETAIL PAGE BUTTONS
- [ ] On booking detail page
- [ ] "Proceed to Payment" button NOT VISIBLE (for confirmed status)
- [ ] Only "Back to Dashboard" and "Cancel Booking" visible

**❌ FAIL IF:** Can access payment page for confirmed booking

---

## TEST SCENARIO 7: CROSS-PAGE CONSISTENCY

**Pick ANY booking and verify:**

### ✅ SAME TOTAL EVERYWHERE
- [ ] Record total from `/confirm/`: ₹________
- [ ] Check total on `/payment/`: ₹________
- [ ] Check total on `/bookings/{id}/`: ₹________
- [ ] **ALL THREE MUST MATCH EXACTLY**

### ✅ GST VISIBLE EVERYWHERE
- [ ] Confirm page shows GST line
- [ ] Payment page shows GST line
- [ ] Detail page shows GST line

### ✅ PROMO VISIBLE EVERYWHERE (if applied)
- [ ] Confirm page shows promo discount
- [ ] Payment page shows promo discount
- [ ] Detail page shows promo discount

**❌ FAIL IF:** ANY page shows different amount

---

## EXPECTED VALUES REFERENCE

| Scenario | Base | Promo | Subtotal | GST (18%) | Total |
|----------|------|-------|----------|-----------|-------|
| No Promo | ₹8000 | ₹0 | ₹8000 | ₹1440 | ₹9440 |
| WELCOME500 | ₹8000 | -₹500 | ₹7500 | ₹1350 | ₹8850 |
| USER1000 (>₹5000) | ₹8000 | -₹1000 | ₹7000 | ₹1260 | ₹8260 |

**With Wallet ₹2000:**
| Total | Wallet Used | Gateway Pay |
|-------|-------------|-------------|
| ₹9440 | ₹2000 | ₹7440 |
| ₹8850 | ₹2000 | ₹6850 |
| ₹1500 | ₹1500 | ₹0 |

---

## HANDOFF CONDITION

✅ **MARK FIXED ONLY IF:**
- All 7 scenarios PASS
- Numbers match across all 3 pages
- GST calculated on post-discount amount
- Wallet is checkbox (not radio)
- 403 guard works for confirmed bookings

❌ **NOT FIXED IF:**
- ANY number mismatch between pages
- ANY scenario fails
- GST calculated on wrong base
- Wallet cannot combine with gateway

---

## REPORTING FORMAT

For each failed test, provide:

1. **Test Scenario:** [Number and name]
2. **Page URL:** [Exact URL]
3. **Expected Value:** [From table above]
4. **Actual Value:** [Screenshot or copy-paste]
5. **Screenshot:** [Attach image showing pricing breakdown]

**Example:**
```
TEST SCENARIO 2: FAILED
Page: /bookings/abc123/payment/
Expected GST: ₹1350 (18% of ₹7500)
Actual GST: ₹1440 (calculated on ₹8000 - WRONG)
Screenshot: [payment_gst_wrong.png]
```

---

**NO ISSUE IS FIXED WITHOUT UI EVIDENCE**
