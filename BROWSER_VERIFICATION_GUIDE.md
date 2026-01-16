# BROWSER VERIFICATION GUIDE - ALL 5 FIXES

**Date:** January 16, 2026  
**URL:** https://goexplorer-dev.cloud  
**Final Commit:** `47bfdf5`

---

## 🚨 CRITICAL REQUIREMENT

**NO claims without screenshots.** This is production-grade code.  
**Every fix must be verified in REAL browser, not test client.**

---

## 📸 VERIFICATION FLOW

### FLOW-1: FIX-1 + FIX-5 (Proceed to Payment + Inventory Hold/Confirm/Release)

#### Step 1: Create Hotel Booking (Inventory HOLD)
1. Open https://goexplorer-dev.cloud/hotels/
2. Click any hotel → "Book Now"
3. **SCREENSHOT-1:** Hotel detail page (shows cancellation policy)
4. Leave room type empty
5. **SCREENSHOT-2:** Red error message shows "Please select a room type"
6. Select room type
7. **SCREENSHOT-3:** Error message disappears, button still disabled
8. Select check-in date
9. Fill all 5 required fields: room_type, check_in, check_out, guest_name, email, phone
10. **SCREENSHOT-4:** Button becomes ENABLED, no errors
11. Click "Proceed to Payment"
12. **SCREENSHOT-5:** Confirmation page loads with all booking details
13. Verify in admin: `http://localhost:8000/admin/bookings/inventorylock/`
14. **SCREENSHOT-6:** InventoryLock entry created (inventory HELD)

---

### FLOW-2: FIX-2 (Wallet Cashfree)

#### Step 1: Open Wallet Page
1. Login user
2. Click profile icon → "Wallet" or `/payments/wallet/`
3. **SCREENSHOT-7:** Wallet page shows current balance (e.g., Rs 0)

#### Step 2: Add Money (Before Payment)
1. Click "Add Money" button
2. Modal opens
3. Enter amount: `10000`
4. **SCREENSHOT-8:** No browser validation error (NOT "nearest valid values")
5. Click "Add Money" in modal
6. **SCREENSHOT-9:** Redirected to Cashfree checkout page
7. **SCREENSHOT-10:** Page shows:
   - Order ID: WALLET-{user_id}-{timestamp}
   - Amount: ₹10000
   - User email
   - "Confirm Payment" button
8. **CRITICAL:** Check wallet balance BEFORE clicking Confirm
9. **SCREENSHOT-11:** Wallet balance still UNCHANGED (NOT credited yet)

#### Step 3: Confirm Payment
1. Click "Confirm Payment"
2. **SCREENSHOT-12:** Success message "₹10000 added to your wallet successfully"
3. Redirected back to wallet page
4. **SCREENSHOT-13:** Wallet balance NOW increased by 10000
5. Check transactions: `http://localhost:8000/admin/payments/wallettransaction/`
6. **SCREENSHOT-14:** New WalletTransaction entry shows:
   - Type: credit
   - Amount: 10000
   - Description: Wallet top-up (via Cashfree)
   - Reference ID: WALLET-{user_id}-{timestamp}
   - Status: success

---

### FLOW-3: FIX-3 (Images)

#### Step 1: Hotel Images
1. Open any hotel detail page
2. Scroll to "Hotel Gallery" section
3. **SCREENSHOT-15:** Multiple hotel images displayed (NOT placeholder)
4. Right-click each image → "Inspect Element"
5. **SCREENSHOT-16:** Verify `alt` and `title` are UNIQUE for each image
6. Verify media path: `/media/hotels/gallery/...`

#### Step 2: Room Images
1. Scroll to "Available Room Types" section
2. **SCREENSHOT-17:** Each room has room-specific image (NOT hotel image)
3. Right-click room image → "Inspect"
4. **SCREENSHOT-18:** Verify `alt="[Room Name] - Room Image"`

---

### FLOW-4: FIX-4 (Cancellation Policy)

#### Step 1: Display on Booking Page
1. Open any hotel detail page
2. Scroll down to "About This Hotel"
3. **SCREENSHOT-19:** Cancellation policy displays as blue info box:
   - "Free cancellation until check-in" OR
   - "Free cancellation until X days before check-in" OR
   - "No cancellations allowed"

#### Step 2: Admin Configuration
1. Go to http://localhost:8000/admin/hotels/hotel/
2. Edit any hotel (e.g., "Taj Exotica Goa")
3. Scroll to "Cancellation Rules" section
4. **SCREENSHOT-20:** See fields:
   - Cancellation Type (dropdown)
   - Cancellation Days (number)
   - Refund Percentage (0-100)
   - Refund Mode (dropdown)
5. Change cancellation type (e.g., from UNTIL_CHECKIN to X_DAYS_BEFORE)
6. Set Cancellation Days = 7
7. Set Refund Percentage = 80
8. Click "Save"
9. **SCREENSHOT-21:** Hotel saved successfully
10. Go back to hotel detail page, refresh
11. **SCREENSHOT-22:** Policy updated to "Free cancellation until 7 days before check-in - Get 80% refund"

---

### FLOW-5: FIX-5 (Inventory Hold/Release)

#### Step 1: Create Booking (HOLD)
1. Create a booking (see FLOW-1, Step 1)
2. Go to admin: http://localhost:8000/admin/bookings/booking/
3. **SCREENSHOT-23:** New booking appears with status "payment_pending"
4. Go to http://localhost:8000/admin/bookings/inventorylock/
5. **SCREENSHOT-24:** InventoryLock entry shows:
   - source: internal
   - status: locked
   - expires_at: (in 10 minutes)

#### Step 2: Confirm Booking (CONFIRM)
1. Go back to booking confirmation page
2. Click "Proceed to Payment"
3. Select payment method: "Pay with Wallet"
4. Click "Pay Now"
5. **SCREENSHOT-25:** Payment success
6. Go to admin booking list
7. **SCREENSHOT-26:** Booking status changed to "confirmed"
8. Go to InventoryLock admin
9. **SCREENSHOT-27:** Lock status (verify finalized or completed)

#### Step 3: Cancel Booking (RELEASE)
1. Go to booking detail page
2. Click "Cancel Booking"
3. Confirm cancellation
4. **SCREENSHOT-28:** Cancellation success + refund amount
5. Go to admin: Bookings
6. **SCREENSHOT-29:** Booking status now "cancelled"
7. Go to InventoryLock admin
8. **SCREENSHOT-30:** Lock released (status shows completion)
9. Check wallet: http://localhost:8000/admin/payments/wallet/
10. **SCREENSHOT-31:** Wallet balance increased by refund amount
11. Check WalletTransaction
12. **SCREENSHOT-32:** New credit transaction with refund amount

---

## 📋 SCREENSHOT CHECKLIST (32 Total)

| # | Description | Section | Required |
|----|-------------|---------|----------|
| 1 | Hotel detail with cancellation policy | FIX-4 | ✅ |
| 2 | Red error: "Please select a room type" | FIX-1 | ✅ |
| 3 | Error clears when field filled | FIX-1 | ✅ |
| 4 | Button ENABLED after all 5 fields | FIX-1 | ✅ |
| 5 | Confirmation page loads | FIX-1 | ✅ |
| 6 | InventoryLock created (HOLD) | FIX-5 | ✅ |
| 7 | Wallet page initial balance | FIX-2 | ✅ |
| 8 | Add Money modal, amount 10000 accepted | FIX-2 | ✅ |
| 9 | Redirected to Cashfree page | FIX-2 | ✅ |
| 10 | Cashfree checkout page | FIX-2 | ✅ |
| 11 | **CRITICAL:** Wallet balance UNCHANGED before payment | FIX-2 | ✅ |
| 12 | Payment success message | FIX-2 | ✅ |
| 13 | Wallet balance INCREASED after payment | FIX-2 | ✅ |
| 14 | WalletTransaction logged (credit) | FIX-2 | ✅ |
| 15 | Hotel images load | FIX-3 | ✅ |
| 16 | Hotel images have unique alt/title | FIX-3 | ✅ |
| 17 | Room images specific to room | FIX-3 | ✅ |
| 18 | Room image alt shows room name | FIX-3 | ✅ |
| 19 | Cancellation policy displays | FIX-4 | ✅ |
| 20 | Admin cancellation config form | FIX-4 | ✅ |
| 21 | Hotel saved | FIX-4 | ✅ |
| 22 | Policy updated on detail page | FIX-4 | ✅ |
| 23 | Booking created (payment_pending) | FIX-5 | ✅ |
| 24 | InventoryLock locked | FIX-5 | ✅ |
| 25 | Payment success | FIX-5 | ✅ |
| 26 | Booking status: confirmed | FIX-5 | ✅ |
| 27 | InventoryLock finalized | FIX-5 | ✅ |
| 28 | Cancellation success | FIX-5 | ✅ |
| 29 | Booking status: cancelled | FIX-5 | ✅ |
| 30 | InventoryLock released | FIX-5 | ✅ |
| 31 | Wallet balance: refund credited | FIX-5 | ✅ |
| 32 | WalletTransaction (refund) logged | FIX-5 | ✅ |

---

## 🚫 WHAT SHOULD NOT HAPPEN

❌ **BLOCKER:** Wallet auto-credits without payment  
❌ **BLOCKER:** Browser error "nearest valid values" for 10000  
❌ **BLOCKER:** Button enables before all 5 fields filled  
❌ **BLOCKER:** Back button redirects to wrong page  
❌ **BLOCKER:** My Bookings button goes to Home  
❌ **BLOCKER:** Images are placeholders (if media permissions fixed)  
❌ **BLOCKER:** Cancellation policy not visible  
❌ **BLOCKER:** Inventory not locked after booking  

---

## ✅ SUCCESS CRITERIA

**All 32 screenshots captured AND pass criteria** =  
**READY FOR STAGING / PRODUCTION**

---

## 📞 TROUBLESHOOTING

| Issue | Solution |
|-------|----------|
| Images show placeholder | Run: `sudo chown -R deployer:www-data ~/media && sudo chmod -R 755 ~/media` |
| Wallet auto-credits immediately | Code has auto-credit bug. Check if fix is deployed. |
| Button doesn't enable | Check browser console for JS errors. |
| Cashfree page not loading | Check `/payments/cashfree-checkout/` view and template. |
| InventoryLock not created | Check `hotels/views.py` line 490-530. |

---

## 🎯 FINAL APPROVAL

**After ALL screenshots are captured and ALL tests PASS:**

1. ✅ Push final commit to GitHub
2. ✅ Deploy to staging
3. ✅ Run staging verification (same 5 flows)
4. ✅ Deploy to production
5. ✅ Monitor production logs for errors

**WITHOUT this verification, DO NOT deploy to production.**
