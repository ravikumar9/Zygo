# 🎯 DEV TESTING CHECKLIST - MANDATORY BROWSER VERIFICATION

**Date:** January 15, 2026  
**Requirement:** All features MUST work on DEV with seeded data  
**Evidence Format:** DEV URL + Screenshot + DB Record ID  

---

## 📋 PRE-DEPLOYMENT CHECKLIST

### Step 1: Deploy Code to DEV
```bash
# SSH into DEV server
ssh user@goexplorer-dev.cloud

# Navigate to project
cd /path/to/goexplorer

# Pull latest code
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install dependencies (if any new)
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Run seed script
python run_seed.py

# Restart server
sudo systemctl restart goexplorer

# Setup cron for booking expiry
crontab -e
# Add line: */1 * * * * cd /path/to/goexplorer && /path/to/venv/bin/python manage.py expire_bookings >> /var/log/goexplorer_expiry.log 2>&1
```

### Step 2: Verify Seed Data
```bash
# Check corporate account
python manage.py shell
>>> from core.models import CorporateAccount
>>> corp = CorporateAccount.objects.get(email_domain='testcorp.com')
>>> print(f"Status: {corp.status}, Coupon: {corp.corporate_coupon.code if corp.corporate_coupon else 'None'}")
>>> exit()

# Check wallet balances
python manage.py shell
>>> from payments.models import Wallet
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> for email in ['qa_email_verified@example.com', 'qa_both_verified@example.com', 'admin@testcorp.com']:
...     user = User.objects.get(email=email)
...     wallet = Wallet.objects.get(user=user)
...     print(f"{email}: ₹{wallet.balance}")
>>> exit()

# Check hotel policies
python manage.py shell
>>> from hotels.models import Hotel
>>> hotel = Hotel.objects.first()
>>> print(f"Check-in: {hotel.checkin_time}, Check-out: {hotel.checkout_time}")
>>> print(f"Cancellation: {hotel.cancellation_policy[:50]}...")
>>> print(f"Rules: {hotel.property_rules[:50]}...")
>>> exit()
```

---

## ✅ TEST 1: CORPORATE ACCOUNT SIGNUP & APPROVAL

### Test 1A: Corporate Signup (Pending Status)
**DEV URL:** `https://goexplorer-dev.cloud/corporate/signup/`

**Steps:**
1. Logout if logged in
2. Register new user: `test_corp_user@newcorp.com` / `TestPassword123!`
3. Login as test_corp_user@newcorp.com
4. Navigate to `/corporate/signup/`
5. Fill form:
   - Company Name: New Corp Pvt Ltd
   - Email Domain: newcorp.com
   - GST Number: TESTGST987654
   - Contact Person: John Doe
   - Contact Email: john@newcorp.com
   - Contact Phone: 9876543210
   - Account Type: Business
6. Submit form
7. Verify redirect to `/corporate/status/`
8. Check status badge: "🟡 Pending Verification"

**Screenshot Required:**
- Form filled and submitted
- Status page showing "Pending Verification"
- Navbar showing "Corporate (Pending)" badge

**DB Verification:**
```bash
python manage.py shell
>>> from core.models import CorporateAccount
>>> corp = CorporateAccount.objects.get(email_domain='newcorp.com')
>>> print(f"Status: {corp.status}, Coupon: {corp.corporate_coupon}")  # Should be: pending_verification, None
>>> exit()
```

**Evidence Format:**
```
✅ TEST 1A: Corporate Signup
DEV URL: https://goexplorer-dev.cloud/corporate/status/
Screenshot: [Attach] - Status page showing pending
DB Record: CorporateAccount ID = X, status = pending_verification, corporate_coupon = None
```

---

### Test 1B: Admin Approval (Auto-Coupon Generation)
**DEV URL:** `https://goexplorer-dev.cloud/admin/core/corporateaccount/`

**Steps:**
1. Login to admin panel as superuser
2. Navigate to Core → Corporate Accounts
3. Find "New Corp Pvt Ltd" with status "Pending"
4. Select checkbox for this account
5. From "Action" dropdown: Select "✅ Approve selected accounts"
6. Click "Go"
7. Verify success message: "Successfully approved X corporate account(s)"
8. Click on "New Corp Pvt Ltd" to view details
9. Verify:
   - Status changed to "Approved"
   - Corporate Coupon field shows: "CORP_NEWCORP"
   - Approved At timestamp present
   - Approved By shows admin username

**Screenshot Required:**
- Corporate Accounts list showing approved status
- Detail page showing coupon created
- Success message after approval

**DB Verification:**
```bash
python manage.py shell
>>> from core.models import CorporateAccount, PromoCode
>>> corp = CorporateAccount.objects.get(email_domain='newcorp.com')
>>> print(f"Status: {corp.status}")  # approved
>>> print(f"Coupon Code: {corp.corporate_coupon.code}")  # CORP_NEWCORP
>>> print(f"Discount: {corp.corporate_coupon.discount_value}%")  # 10
>>> print(f"Max Cap: ₹{corp.corporate_coupon.max_discount_amount}")  # 1000
>>> print(f"Valid Until: {corp.corporate_coupon.valid_until}")  # 1 year from now
>>> exit()
```

**Evidence Format:**
```
✅ TEST 1B: Corporate Approval
DEV URL: https://goexplorer-dev.cloud/admin/core/corporateaccount/X/change/
Screenshot: [Attach] - Admin showing approved status + coupon
DB Record: CorporateAccount ID = X, status = approved
PromoCode ID = Y, code = CORP_NEWCORP, discount_value = 10, max_discount_amount = 1000
```

---

### Test 1C: Corporate Dashboard (Approved User)
**DEV URL:** `https://goexplorer-dev.cloud/corporate/dashboard/`

**Steps:**
1. Login as test_corp_user@newcorp.com
2. Navbar should now show "Corporate" (no "Pending" badge)
3. Click "Corporate" menu item
4. Verify dashboard displays:
   - ✅ Status: APPROVED (green badge)
   - 💰 Wallet Balance: ₹10,000.00 (seeded)
   - 📊 Total Bookings: 0
   - 🏢 Corporate Bookings: 0
   - 💵 Total Spent: ₹0.00
   - 🎁 Corporate Savings: ₹0.00
   - 🎟️ Corporate Coupon Card:
     - Code: CORP_NEWCORP (badge)
     - Discount: 10% off (max ₹1,000)
     - Valid Until: [1 year from approval date]
   - Recent Bookings: "No bookings yet"
   - CTAs: "Book Hotels", "Book Bus Tickets", "Book Packages"

**Screenshot Required:**
- Full dashboard with all sections visible
- Coupon code badge showing CORP_NEWCORP
- Wallet balance ₹10,000
- Status badge showing APPROVED

**Evidence Format:**
```
✅ TEST 1C: Corporate Dashboard
DEV URL: https://goexplorer-dev.cloud/corporate/dashboard/
Screenshot: [Attach] - Dashboard showing approved status, wallet, coupon
User: test_corp_user@newcorp.com
Corporate Account: New Corp Pvt Ltd (approved)
Coupon: CORP_NEWCORP
```

---

## ✅ TEST 2: WALLET SEEDED BALANCE & BOOKING FLOW

### Test 2A: Wallet Page (Seeded Balance)
**DEV URL:** `https://goexplorer-dev.cloud/payments/wallet/`

**Steps:**
1. Login as qa_email_verified@example.com / TestPassword123!
2. Navigate to `/payments/wallet/`
3. Verify page displays:
   - Current Balance: ₹10,000.00
   - Transaction history (if any)
   - No broken links
   - No redirect loops
   - Renders as HTML (not JSON)

**Screenshot Required:**
- Wallet page showing ₹10,000 balance
- Transaction history section visible (even if empty)

**Evidence Format:**
```
✅ TEST 2A: Wallet Seeded Balance
DEV URL: https://goexplorer-dev.cloud/payments/wallet/
Screenshot: [Attach] - Wallet showing ₹10,000 balance
User: qa_email_verified@example.com
DB Record: Wallet ID = X, balance = 10000.00
```

---

### Test 2B: Hotel Booking with Wallet Payment
**DEV URL:** `https://goexplorer-dev.cloud/hotels/` (then select any hotel)

**Steps:**
1. Login as qa_email_verified@example.com
2. Go to Hotels listing page
3. Click on any hotel (e.g., "Taj Exotica Goa")
4. Select dates:
   - Check-in: [7 days from today]
   - Check-out: [9 days from today]
5. Click "Search Rooms"
6. Select a room type, enter 1 room, 2 guests
7. Click "Book Now"
8. On booking form:
   - Enter guest details
   - Select Payment Method: "Pay with Wallet"
   - Note Total Amount (e.g., ₹5,000)
9. Click "Confirm Booking"
10. Verify:
    - Booking Status: "PAYMENT_PENDING" (10-min hold)
    - Expires At: [10 minutes from now]
    - NO success alert yet (critical!)
11. On payment page, click "Pay Now"
12. Verify:
    - Wallet balance reduced from ₹10,000 to ₹5,000
    - Booking status changed to "CONFIRMED"
    - NOW shows success message
    - WalletTransaction created with:
      - Type: debit
      - Amount: ₹5,000
      - balance_before: ₹10,000
      - balance_after: ₹5,000
      - reference_id: [booking_id]
      - status: success

**Screenshot Required:**
- Booking form with wallet payment selected
- Payment pending page (BEFORE payment, showing 10-min timer, NO success alert)
- Payment success page (AFTER payment, showing success alert)
- Wallet page showing reduced balance
- Admin booking detail showing status = confirmed
- Admin WalletTransaction showing all tracking fields

**DB Verification:**
```bash
python manage.py shell
>>> from bookings.models import Booking
>>> from payments.models import WalletTransaction
>>> booking = Booking.objects.filter(user__email='qa_email_verified@example.com').latest('created_at')
>>> print(f"Status: {booking.status}, Total: ₹{booking.total_amount}, Expires: {booking.expires_at}")
>>> txn = WalletTransaction.objects.filter(booking_id=booking.booking_id).first()
>>> print(f"Type: {txn.transaction_type}, Amount: ₹{txn.amount}, Balance Before: ₹{txn.balance_before}, Balance After: ₹{txn.balance_after}, Ref ID: {txn.reference_id}, Status: {txn.status}")
>>> exit()
```

**Evidence Format:**
```
✅ TEST 2B: Hotel Booking with Wallet
DEV URL: https://goexplorer-dev.cloud/bookings/[booking_id]/confirm/
Screenshot 1: [Attach] - Payment pending (NO success alert, showing 10-min timer)
Screenshot 2: [Attach] - Payment success (showing success alert)
Screenshot 3: [Attach] - Wallet reduced balance
Screenshot 4: [Attach] - Admin booking showing confirmed status
Screenshot 5: [Attach] - Admin WalletTransaction showing tracking fields
DB Record: Booking ID = X, status = confirmed, total_amount = 5000
WalletTransaction ID = Y, balance_before = 10000, balance_after = 5000, reference_id = [booking_id], status = success
```

---

## ✅ TEST 3: BOOKING EXPIRY & INVENTORY RESTORE

### Test 3A: Create Payment Pending Booking (Don't Pay)
**DEV URL:** `https://goexplorer-dev.cloud/hotels/[hotel_id]/`

**Steps:**
1. Login as qa_both_verified@example.com
2. Book any hotel (same steps as Test 2B)
3. On payment page: **DO NOT CLICK "Pay Now"**
4. Note:
   - Booking ID
   - Booking Status: payment_pending
   - Expires At: [timestamp, should be reserved_at + 10 min]
   - Room Type Availability (e.g., "8 rooms available")
5. Wait exactly 11 minutes OR manually trigger expiry (see Test 3B)

**Screenshot Required:**
- Payment pending page showing booking details
- Expires At timestamp visible
- Hotel room availability count BEFORE expiry

**Evidence Format:**
```
✅ TEST 3A: Payment Pending Booking
DEV URL: https://goexplorer-dev.cloud/bookings/[booking_id]/confirm/
Screenshot: [Attach] - Payment pending showing expires_at
DB Record: Booking ID = X, status = payment_pending, reserved_at = [timestamp], expires_at = [timestamp + 10 min]
Room Availability Before: [count]
```

---

### Test 3B: Manual Expiry Trigger (Admin)
**DEV URL:** SSH into DEV server

**Steps:**
1. SSH into DEV: `ssh user@goexplorer-dev.cloud`
2. Navigate to project: `cd /path/to/goexplorer`
3. Activate venv: `source venv/bin/activate`
4. Run expiry command: `python manage.py expire_bookings`
5. Check output:
   ```
   Expired booking [booking_id] (status changed from payment_pending to expired)
   Successfully processed 1 booking(s)
   ```
6. Verify in admin panel:
   - Booking status = expired
   - Inventory restored (room count increased)

**Screenshot Required:**
- Terminal showing expiry command output
- Admin booking showing status = expired
- Hotel room availability count AFTER expiry (should be +1)

**DB Verification:**
```bash
python manage.py shell
>>> from bookings.models import Booking
>>> booking = Booking.objects.get(booking_id='[booking_id_from_test_3a]')
>>> print(f"Status: {booking.status}")  # Should be: expired
>>> exit()
```

**Evidence Format:**
```
✅ TEST 3B: Booking Expiry
Terminal Output: [Attach] - Command showing "Expired booking X"
Screenshot 1: [Attach] - Admin showing status = expired
Screenshot 2: [Attach] - Hotel showing inventory restored
DB Record: Booking ID = X, status = expired
Room Availability After: [count + 1]
```

---

### Test 3C: Cron Job Verification (Automated Expiry)
**DEV URL:** SSH into DEV server

**Steps:**
1. Verify cron job is set up: `crontab -l`
2. Should show: `*/1 * * * * cd /path && python manage.py expire_bookings >> /var/log/goexplorer_expiry.log 2>&1`
3. Create another payment_pending booking
4. Wait 11 minutes (cron will run automatically)
5. Check log: `tail -f /var/log/goexplorer_expiry.log`
6. Verify booking auto-expired

**Screenshot Required:**
- Cron configuration: `crontab -l`
- Log file showing automated expiry
- Admin showing booking auto-expired

**Evidence Format:**
```
✅ TEST 3C: Cron Automation
Cron Config: [Copy crontab -l output]
Log: [Copy tail /var/log/goexplorer_expiry.log]
Screenshot: [Attach] - Admin showing booking auto-expired by cron
```

---

## ✅ TEST 4: HOTEL PROPERTY RULES UI

### Test 4A: Hotel Detail Page Policies
**DEV URL:** `https://goexplorer-dev.cloud/hotels/[hotel_id]/`

**Steps:**
1. Navigate to any hotel detail page
2. Scroll to "Hotel Policies" section
3. Verify displays:
   - **Check-in Time:** 2:00 PM (from DB: hotel.checkin_time)
   - **Check-out Time:** 11:00 AM (from DB: hotel.checkout_time)
   - **Cancellation Policy:** "Free cancellation up to 24 hours before check-in. 50% refund within 24 hours. No refund after check-in." (from DB: hotel.cancellation_policy)
   - **House Rules:** (from DB: hotel.property_rules)
     - Valid ID required at check-in
     - No pets allowed
     - No smoking in rooms
     - Quiet hours: 10 PM - 7 AM
4. Verify:
   - ✅ NO hardcoded text (all from DB)
   - ✅ NO "Image unavailable" or missing sections
   - ✅ Proper formatting with icons

**Screenshot Required:**
- Full hotel detail page
- Policies section clearly visible with all 4 subsections
- Icons displayed correctly

**DB Verification:**
```bash
python manage.py shell
>>> from hotels.models import Hotel
>>> hotel = Hotel.objects.get(id=[hotel_id])
>>> print(f"Check-in: {hotel.checkin_time}")
>>> print(f"Check-out: {hotel.checkout_time}")
>>> print(f"Cancellation: {hotel.cancellation_policy}")
>>> print(f"Rules: {hotel.property_rules}")
>>> exit()
```

**Evidence Format:**
```
✅ TEST 4A: Hotel Property Rules
DEV URL: https://goexplorer-dev.cloud/hotels/[hotel_id]/
Screenshot: [Attach] - Hotel detail showing policies section
DB Record: Hotel ID = X
- checkin_time = 14:00:00
- checkout_time = 11:00:00
- cancellation_policy = [full text from DB]
- property_rules = [full text from DB]
```

---

## ✅ TEST 5: CORPORATE BOOKING WITH AUTO-DISCOUNT

### Test 5A: Corporate User Booking (Auto-Apply Coupon)
**DEV URL:** `https://goexplorer-dev.cloud/hotels/`

**Steps:**
1. Login as admin@testcorp.com (corporate admin user)
2. Book any hotel (total price: e.g., ₹5,000)
3. On booking page, verify:
   - Corporate coupon CORP_TESTCORP auto-selected
   - Discount applied: 10% (₹500)
   - Final Price: ₹4,500
   - Wallet balance sufficient
4. Complete booking with wallet payment
5. On corporate dashboard (`/corporate/dashboard/`):
   - Total Bookings: 1
   - Corporate Bookings: 1
   - Total Spent: ₹4,500
   - Corporate Savings: ₹500

**Screenshot Required:**
- Booking form showing corporate discount auto-applied
- Payment success page
- Corporate dashboard showing updated stats
- Admin booking showing corporate coupon used

**DB Verification:**
```bash
python manage.py shell
>>> from bookings.models import Booking
>>> booking = Booking.objects.filter(user__email='admin@testcorp.com').latest('created_at')
>>> print(f"Total Amount: ₹{booking.total_amount}")
>>> # Check channel_reference JSON for corporate discount info
>>> import json
>>> ref = json.loads(booking.channel_reference) if booking.channel_reference else {}
>>> print(f"Corporate Savings: ₹{ref.get('corporate_discount', 0)}")
>>> exit()
```

**Evidence Format:**
```
✅ TEST 5A: Corporate Booking
DEV URL: https://goexplorer-dev.cloud/corporate/dashboard/
Screenshot 1: [Attach] - Booking form with corporate discount
Screenshot 2: [Attach] - Dashboard showing savings
DB Record: Booking ID = X, user = admin@testcorp.com
Corporate Savings: ₹500 (10% of ₹5,000)
```

---

## ✅ TEST 6: ADMIN UI STATUS DISPLAY

### Test 6A: Bookings Admin List
**DEV URL:** `https://goexplorer-dev.cloud/admin/bookings/booking/`

**Steps:**
1. Login to admin as superuser
2. Navigate to Bookings → Bookings
3. Verify list displays:
   - Booking ID column
   - User column
   - Status column with badges:
     - 🟡 Payment Pending
     - 🟢 Confirmed
     - 🔴 Expired
     - ⚫ Cancelled
   - Total Amount
   - Created At
   - Expires At (for payment_pending bookings)
4. Use status filter:
   - Filter by "Payment Pending" → shows only pending
   - Filter by "Confirmed" → shows only confirmed
   - Filter by "Expired" → shows only expired

**Screenshot Required:**
- Bookings list showing different status badges
- Status filter dropdown
- Filtered results

**Evidence Format:**
```
✅ TEST 6A: Admin Bookings List
DEV URL: https://goexplorer-dev.cloud/admin/bookings/booking/
Screenshot: [Attach] - List with multiple booking statuses
Status Badges Visible: payment_pending, confirmed, expired
```

---

### Test 6B: Wallet Transactions Admin
**DEV URL:** `https://goexplorer-dev.cloud/admin/payments/wallettransaction/`

**Steps:**
1. Login to admin as superuser
2. Navigate to Payments → Wallet Transactions
3. Verify list displays:
   - Transaction ID
   - User (wallet owner)
   - Transaction Type (credit/debit)
   - Amount
   - **Balance Before**
   - **Balance After**
   - **Reference ID** (booking ID)
   - **Status** (success/pending/failed)
   - Payment Gateway (internal/cashfree)
   - Created At
4. Click on any debit transaction
5. Verify detail page shows all fields populated

**Screenshot Required:**
- Transaction list showing balance_before, balance_after, reference_id columns
- Detail page of a wallet debit transaction

**Evidence Format:**
```
✅ TEST 6B: Wallet Transactions Admin
DEV URL: https://goexplorer-dev.cloud/admin/payments/wallettransaction/
Screenshot: [Attach] - Transaction list with tracking fields
DB Record: WalletTransaction ID = X
- balance_before = [amount]
- balance_after = [amount]
- reference_id = [booking_id]
- status = success
```

---

## ✅ TEST 7: MEDIA/IMAGES ON DEV

### Test 7A: Hotel Images Load Correctly
**DEV URL:** `https://goexplorer-dev.cloud/hotels/`

**Steps:**
1. Navigate to Hotels listing page
2. For hotels WITH images:
   - Verify image loads from MEDIA_URL
   - No broken image icons
3. For hotels WITHOUT images:
   - Verify placeholder image appears
   - **CRITICAL:** NO "Image unavailable" TEXT appears
   - Placeholder should be clean default image

**Screenshot Required:**
- Hotels listing showing mix of real images and placeholders
- Hotel detail page showing images loading correctly
- Browser console showing no 404 errors for images

**Evidence Format:**
```
✅ TEST 7A: Hotel Images
DEV URL: https://goexplorer-dev.cloud/hotels/
Screenshot 1: [Attach] - Hotels listing with images
Screenshot 2: [Attach] - Hotel with placeholder (NO "unavailable" text)
Console: [Attach] - No image 404 errors
```

---

## 🚫 CRITICAL FAILURES (MUST FIX BEFORE ACCEPTANCE)

1. **"Image unavailable" text appears** → REJECT
2. **Success alert shows before payment** → REJECT
3. **Booking status doesn't change** → REJECT
4. **Wallet balance doesn't update** → REJECT
5. **Corporate coupon not auto-generated on approval** → REJECT
6. **Hotel policies missing or hardcoded** → REJECT
7. **Inventory not restored after expiry** → REJECT
8. **WalletTransaction missing tracking fields** → REJECT

---

## 📸 FINAL EVIDENCE PACKAGE

After completing all tests, compile evidence in this format:

```
# ACCEPTANCE EVIDENCE - [Date]

## TEST 1: Corporate Dashboard
- [x] 1A: Signup (Pending) - Screenshot: test1a.png, DB ID: X
- [x] 1B: Admin Approval - Screenshot: test1b.png, DB ID: Y, Coupon: CORP_NEWCORP
- [x] 1C: Dashboard (Approved) - Screenshot: test1c.png

## TEST 2: Wallet & Booking
- [x] 2A: Wallet Seeded - Screenshot: test2a.png, Balance: ₹10,000
- [x] 2B: Hotel Booking - Screenshots: test2b_pending.png, test2b_success.png, test2b_wallet.png

## TEST 3: Booking Expiry
- [x] 3A: Payment Pending - Screenshot: test3a.png
- [x] 3B: Manual Expiry - Screenshot: test3b.png
- [x] 3C: Cron Automation - Screenshot: test3c.png

## TEST 4: Hotel Policies
- [x] 4A: Policies Display - Screenshot: test4a.png

## TEST 5: Corporate Booking
- [x] 5A: Auto-Discount - Screenshot: test5a.png, Savings: ₹500

## TEST 6: Admin UI
- [x] 6A: Bookings List - Screenshot: test6a.png
- [x] 6B: Wallet Transactions - Screenshot: test6b.png

## TEST 7: Media
- [x] 7A: Images Load - Screenshot: test7a.png

ALL TESTS PASSED ✅
```

---

## 🎯 ACCEPTANCE CRITERIA MET

Once all 7 tests pass with screenshots + DB verification:

✅ **Corporate Dashboard** - FULL implementation working  
✅ **Wallet Seeded Balance** - ₹10,000 for all test users  
✅ **Booking Lifecycle** - payment_pending → confirmed/expired  
✅ **Auto-Expiry** - 10-min timeout with inventory restore  
✅ **Hotel Property Rules** - All policies from DB displayed  
✅ **Wallet Tracking** - balance_before/after, reference_id working  
✅ **Admin UI** - Status badges, real-time updates  
✅ **Media** - Images load, clean placeholders  

**READY FOR PRODUCTION** 🚀
