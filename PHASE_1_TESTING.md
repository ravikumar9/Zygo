# PHASE 1 TESTING GUIDE

## Overview
This document provides step-by-step test cases for validating all Phase 1 functionality:
- Booking lifecycle (RESERVED → CONFIRMED/FAILED/EXPIRED)
- Atomic wallet + booking transactions
- Auto-expire on timeout (30 min)
- Wallet rollback on failure
- Bulk admin operations
- Seed parity validation

**Testing Method:** ONLY use `seed_all` for data (as mandated by user).

---

## Prerequisites

```bash
# 1. Activate virtual environment
cd c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear
.venv-1\Scripts\activate  # Windows
# source .venv-1/bin/activate  # Linux/Mac

# 2. Apply all migrations
python manage.py migrate

# 3. Flush database and seed fresh data
python manage.py flush --noinput
python manage.py seed_all --env=local

# 4. Validate seed parity
python manage.py validate_seed
# Expected output: [OK] SEED PARITY VERIFIED!

# 5. Start development server
python manage.py runserver
```

---

## TEST 1: Seed Parity Validation

**Objective:** Ensure `seed_all` produces consistent deterministic data.

### Steps:
1. Run `python manage.py flush --noinput`
2. Run `python manage.py seed_all --env=local`
3. Run `python manage.py validate_seed`

### Expected Results:
```
============================================================
SEED DATA PARITY VALIDATION
============================================================

[OK] Hotels: 16/16
[OK] Packages: 5/5
[OK] Buses: 2/2
[OK] Bus Operators: 2/2
[OK] Wallets: 1/1

------------------------------------------------------------
Wallet Details:
------------------------------------------------------------
  Testuser exists: [OK]
  Wallet balance: 5000.00 [Expected: 5000]
    [OK] Balance matches
  Active cashback entries: 1 [Expected: 1]
    [OK] Cashback entry exists

============================================================
[OK] SEED PARITY VERIFIED!
All data matches expected counts.
============================================================
```

**✅ PASS:** All checks show [OK]  
**❌ FAIL:** Any check shows [FAIL] → reseed and check for errors

---

## TEST 2: Booking Lifecycle (RESERVED → CONFIRMED)

**Objective:** Verify new bookings start in RESERVED state, timestamps auto-set, and transition to CONFIRMED on payment.

### Steps:
1. Login as `testuser` / `testpass123`
2. Navigate to Buses → Select "Bangalore to Chennai" route
3. Select travel date (today or tomorrow)
4. Select 1 general seat (avoid ladies seats if male)
5. Fill passenger details: Name, Age (25), Gender (Male)
6. Select boarding & dropping points
7. Click "Book Now"
8. **Before payment:** Check database:
   ```bash
   python manage.py shell
   from bookings.models import Booking
   b = Booking.objects.latest('id')
   print(f"Status: {b.status}")
   print(f"Reserved at: {b.reserved_at}")
   print(f"Expires at: {b.expires_at}")
   print(f"Confirmed at: {b.confirmed_at}")
   exit()
   ```

### Expected Results (Before Payment):
- `status` = `reserved`
- `reserved_at` = current timestamp (within last 30 seconds)
- `expires_at` = `reserved_at + 30 minutes`
- `confirmed_at` = `None`

9. **Complete payment:** Select "Pay with Wallet" → Submit
10. Check database again (same commands above)

### Expected Results (After Payment):
- `status` = `confirmed`
- `confirmed_at` = current timestamp (payment completion time)
- `reserved_at` and `expires_at` unchanged

**✅ PASS:** State transitions work correctly, all timestamps set  
**❌ FAIL:** Status stuck in RESERVED, timestamps missing, or CONFIRMED without payment

---

## TEST 3: Atomic Wallet Transaction (Success Case)

**Objective:** Verify wallet debit + booking status update happen atomically (both succeed or both fail).

### Steps:
1. Login as `testuser` (wallet balance: ₹5000)
2. Create bus booking (₹899 fare + fees ≈ ₹1050 total)
3. Before payment, check wallet:
   ```bash
   python manage.py shell
   from users.models import User
   u = User.objects.get(username='testuser')
   print(f"Wallet balance: {u.wallet.balance}")
   exit()
   ```
   Expected: `5000.00`

4. Complete payment via wallet
5. Check wallet again:
   ```bash
   python manage.py shell
   from users.models import User
   u = User.objects.get(username='testuser')
   print(f"Wallet balance: {u.wallet.balance}")
   
   from payments.models import WalletTransaction
   txn = WalletTransaction.objects.filter(wallet=u.wallet).latest('id')
   print(f"Transaction type: {txn.transaction_type}")
   print(f"Amount: {txn.amount}")
   print(f"Booking ID: {txn.booking_id}")
   exit()
   ```

### Expected Results:
- Wallet balance = `5000 - total_booking_cost` (e.g., `3950.00`)
- Latest transaction type = `debit`
- Transaction.booking_id = booking ID
- Booking status = `confirmed`

**✅ PASS:** Wallet debited AND booking confirmed (both succeed)  
**❌ FAIL:** Wallet debited but booking still RESERVED, or vice versa (partial update = atomicity failure)

---

## TEST 4: Wallet Rollback on Failure

**Objective:** Verify wallet rollback if payment fails mid-transaction.

### Manual Simulation (requires code edit):
1. Open `payments/views.py`
2. Find `process_wallet_payment()` function
3. Add intentional exception AFTER wallet debit:
   ```python
   # Around line 150, after wallet.balance -= total_amount
   wallet.balance -= total_amount
   wallet.save()
   raise Exception("TEST: Simulated payment failure")  # Add this line
   ```
4. Save file, restart server
5. Try booking a bus with wallet payment

### Expected Results:
- Payment fails with error message
- Wallet balance = original (₹5000) — no debit persisted
- Booking status = `reserved` (NOT confirmed)
- Check WalletTransaction:
  ```bash
  from payments.models import WalletTransaction
  refund = WalletTransaction.objects.filter(transaction_type='refund').latest('id')
  print(f"Refund amount: {refund.amount}")
  print(f"Parent txn: {refund.parent_transaction_id}")
  ```
  Should show refund record with parent_transaction pointing to failed debit

**✅ PASS:** Wallet balance unchanged, no confirmed booking, refund record created  
**❌ FAIL:** Wallet debited without confirmed booking (rollback failed)

**⚠️ IMPORTANT:** Remove the test exception after testing:
```python
# Remove this line:
raise Exception("TEST: Simulated payment failure")
```

---

## TEST 5: Auto-Expire on Timeout (30 min)

**Objective:** Verify RESERVED bookings expire after 30 minutes and inventory is released.

### Manual Simulation (mock timeout):
1. Create a booking (don't pay)
2. Note booking ID and seat number
3. Check current reserved_at:
   ```bash
   python manage.py shell
   from bookings.models import Booking
   b = Booking.objects.get(id=<booking_id>)
   print(f"Reserved at: {b.reserved_at}")
   print(f"Expires at: {b.expires_at}")
   ```

4. **Manually set reserved_at to 31 minutes ago:**
   ```bash
   python manage.py shell
   from bookings.models import Booking
   from datetime import timedelta
   from django.utils import timezone
   
   b = Booking.objects.get(id=<booking_id>)
   b.reserved_at = timezone.now() - timedelta(minutes=31)
   b.expires_at = b.reserved_at + timedelta(minutes=30)
   b.save()
   print(f"Updated reserved_at: {b.reserved_at}")
   exit()
   ```

5. Run auto-expire task:
   ```bash
   python manage.py shell
   from bookings.tasks import auto_expire_reservations
   auto_expire_reservations()
   exit()
   ```

6. Check booking status:
   ```bash
   python manage.py shell
   from bookings.models import Booking
   b = Booking.objects.get(id=<booking_id>)
   print(f"Status: {b.status}")  # Should be 'expired'
   
   # Check inventory released (bus seat)
   from buses.models import BusBookingSeat
   seats = BusBookingSeat.objects.filter(booking=b).count()
   print(f"Seats still locked: {seats}")  # Should be 0
   exit()
   ```

### Expected Results:
- Booking status = `expired`
- BusBookingSeat count = 0 (seats released)
- Schedule.available_seats incremented back
- Email sent to user (check console/email backend)

**✅ PASS:** Booking expired, inventory released, email sent  
**❌ FAIL:** Status still RESERVED after 31 min, or inventory not released

---

## TEST 6: Bulk Admin Operations

**Objective:** Verify admin can bulk-update buses and hotels efficiently.

### Steps - Bus Bulk Operations:
1. Login to Django admin: `http://localhost:8000/admin/`
   - Username: (create superuser if needed: `python manage.py createsuperuser`)
2. Navigate to **Buses → Bus**
3. Select all buses (check boxes)
4. From "Action" dropdown, select **"Enable WiFi"**
5. Click "Go"

### Expected Results:
- Success message: "2 buses updated with WiFi enabled"
- All selected buses show `has_wifi = True` in list view
- Verify by editing any bus → WiFi checkbox is checked

### Repeat for other actions:
- Enable AC → `has_ac = True`
- Disable AC → `has_ac = False`
- Mark as Active → `is_active = True`
- Mark as Inactive → `is_active = False`

### Steps - Hotel Bulk Operations:
1. Navigate to **Hotels → Hotel**
2. Select 5 hotels (check first 5 boxes)
3. From "Action" dropdown, select **"Enable amenities (WiFi + Pool + Gym)"**
4. Click "Go"

### Expected Results:
- Success message: "5 hotels updated with amenities enabled"
- All selected hotels show `has_wifi = True`, `has_pool = True`, `has_gym = True`

### Steps - Inline Editing:
1. In Hotel list view, find "Star Rating" column
2. Change any hotel's star rating from 5 to 4 directly in list
3. Click "Save" at bottom
4. Verify change persisted (refresh page, check value)

**✅ PASS:** All bulk operations work, inline edits save correctly  
**❌ FAIL:** Bulk actions fail, inline edits don't persist, or no success messages

---

## TEST 7: Bus Seat Layout UX (2x2 Grid)

**Objective:** Verify improved bus seat layout displays correctly.

### Steps:
1. Navigate to Buses → Select any bus
2. Select a route
3. Scroll to "Seat Layout" section

### Expected Visual Results:
- **Legend:** Shows 4 colored boxes (Available, Ladies Only, Booked, Selected) with symbols (G, ♀, ✕, ✓)
- **Deck Titles:** "Lower Deck" and "Upper Deck" (if sleeper bus)
- **Driver Section:** Gray box at top showing "DRIVER" icon
- **Seat Grid:**
  - 2x2 layout: `[A] [B] | AISLE | [C] [D]` per row
  - Seats are 45x45px squares with seat numbers
  - Ladies seats have **♀ symbol** in top-right corner (pink color)
  - Available seats: Green background
  - Booked seats: Red background (disabled)
  - Selected seats: Blue background (on click)
- **Responsive:** On mobile (<768px), seats shrink to 40x40px, legend stacks vertically

### Interaction Test:
1. Click an available general seat → should highlight blue
2. Click a ladies seat (if male user) → should show warning: "Seats X are reserved for female passengers"
3. Select 2 seats → "Selected Seats" widget shows "2 seat(s): 1A, 2B"

**✅ PASS:** Layout displays in 2x2 grid, ladies seats have ♀ symbol, responsive on mobile  
**❌ FAIL:** Seats in single column, no aisle separator, missing ladies indicator, or layout breaks on mobile

---

## TEST 8: End-to-End Booking Flow

**Objective:** Complete a full booking from search to confirmation.

### Steps:
1. Logout (if logged in)
2. Navigate to Buses
3. Select route: "Mumbai to Pune" (₹499 base fare)
4. Select tomorrow's date
5. Select 2 general seats (avoid ladies seats)
6. Fill passenger details:
   - Name: Test Passenger
   - Age: 30
   - Gender: Male
7. Select boarding point: First option
8. Select dropping point: First option
9. Note total price (e.g., ₹1,200 for 2 seats with fees)
10. Click "Login to Book" → login as `testuser`
11. After redirect, click "Book Now"
12. Select "Pay with Wallet"
13. Click "Confirm Payment"

### Expected Results:
- Booking confirmation page shows:
  - Booking ID
  - Status: "Confirmed"
  - Seat numbers
  - Total paid amount
- Wallet balance reduced by exact amount
- Email confirmation sent (check console)
- Booking appears in "My Bookings" (user profile)
- Seat no longer available for other users

### Database Verification:
```bash
python manage.py shell
from bookings.models import Booking
b = Booking.objects.latest('id')
print(f"Status: {b.status}")  # confirmed
print(f"Total price: {b.total_price}")
print(f"Reserved at: {b.reserved_at}")
print(f"Confirmed at: {b.confirmed_at}")

from payments.models import Payment
p = Payment.objects.filter(booking=b).first()
print(f"Payment method: {p.payment_method}")  # wallet
print(f"Amount paid: {p.amount_paid}")
exit()
```

**✅ PASS:** Full flow works, booking confirmed, payment recorded, seat locked  
**❌ FAIL:** Any step fails, status stuck in RESERVED, or payment fails silently

---

## Troubleshooting

### Issue: Migrations Fail
**Solution:**
```bash
python manage.py migrate --fake bookings 0006  # Fake to previous
python manage.py migrate bookings  # Apply new migration
```

### Issue: Seed Parity Fails
**Solution:**
```bash
python manage.py flush --noinput
python manage.py seed_all --env=local
python manage.py validate_seed
```

### Issue: Wallet Balance Incorrect
**Solution:**
Check for orphaned transactions:
```bash
python manage.py shell
from payments.models import WalletTransaction
from users.models import User
u = User.objects.get(username='testuser')
total_credits = WalletTransaction.objects.filter(wallet=u.wallet, transaction_type='credit').aggregate(total=Sum('amount'))
total_debits = WalletTransaction.objects.filter(wallet=u.wallet, transaction_type='debit').aggregate(total=Sum('amount'))
expected = total_credits['total'] - total_debits['total']
print(f"Expected balance: {expected}, Actual: {u.wallet.balance}")
```

### Issue: Auto-Expire Not Working
**Solution:**
Check django-rq worker is running:
```bash
python manage.py rqworker default
# Then in another terminal, trigger job:
python manage.py shell
from bookings.tasks import auto_expire_reservations
auto_expire_reservations()
```

---

## Testing Checklist

### Core Functionality (Phase 1 Mandatory)
- [ ] TEST 1: Seed parity validation passes
- [ ] TEST 2: Booking lifecycle (RESERVED → CONFIRMED)
- [ ] TEST 3: Atomic wallet transactions (success case)
- [ ] TEST 4: Wallet rollback on failure
- [ ] TEST 5: Auto-expire on 30 min timeout
- [ ] TEST 6: Bulk admin operations (buses, hotels)
- [ ] TEST 7: Bus seat layout 2x2 grid UX
- [ ] TEST 8: End-to-end booking flow

### Additional Checks
- [ ] All migrations applied: `python manage.py showmigrations | grep "\[ \]"` returns nothing
- [ ] No Django check errors: `python manage.py check --deploy`
- [ ] Static files collected: `python manage.py collectstatic --noinput`
- [ ] Server starts without errors: `python manage.py runserver`

---

## Go-Live Checklist (Before Deployment)

1. **Local Testing:** All 8 tests pass ✅
2. **Database Migrations:** Applied and verified
3. **Seed Parity:** validate_seed passes on local
4. **Code Review:** No debug prints, test exceptions removed
5. **Git Commit:** All changes committed with descriptive message
6. **Server Deployment:**
   ```bash
   git push origin main
   ssh deployer@goexplorer-dev.cloud
   cd /path/to/project
   git pull origin main
   source venv/bin/activate
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py seed_all --env=local
   python manage.py validate_seed  # Must pass!
   sudo systemctl restart gunicorn
   sudo systemctl restart nginx
   ```
7. **Server Verification:** Repeat all 8 tests on production
8. **Monitor Logs:** `tail -f /var/log/gunicorn/error.log`

---

## Success Criteria

**Phase 1 is complete when:**
- All 8 test cases pass ✅ on local AND server
- Seed parity verified on both environments
- No regression in existing functionality
- Documentation complete (this file + PHASE_1_IMPLEMENTATION_GUIDE.md)

**Acceptance:** User confirms all mandatory Phase 1 goals met.
