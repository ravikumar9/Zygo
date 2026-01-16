# ADMIN PANEL VERIFICATION GUIDE

**For verifying fixes are working in production**

---

## CHECKING WALLET TRANSACTIONS

### Via Django Admin: http://localhost:8000/admin/payments/wallettransaction/

**What to verify:**

1. **Recent transactions exist:**
   - Click on any booking from today
   - Should see WalletTransaction entry
   - Look for:
     - `transaction_type = 'debit'`
     - `balance_before` field populated
     - `balance_after` field populated
     - `reference_id` matches booking ID

2. **Balance calculation is correct:**
   - `balance_after = balance_before - amount`
   - Example: 5000 - 2000 = 3000 ✓

3. **No orphaned transactions:**
   - Every transaction should have `booking` field populated
   - `reference_id` should match a real booking

---

## CHECKING INVENTORY LOCKS

### Via Django Admin: http://localhost:8000/admin/bookings/inventorylock/

**What to verify:**

1. **Locks exist for bookings:**
   - Filter by hotel
   - Should see locks with:
     - `source = 'internal'` or `'external_cm'`
     - `booking` field populated (not null)
     - `lock_id` matches pattern

2. **No orphaned locks:**
   - Every lock should have:
     - `booking` pointing to a real booking
     - OR `expires_at` timestamp in past (expired)

3. **No duplicate locks per booking:**
   - One booking = one lock (usually)
   - Multi-room bookings may have multiple

---

## CHECKING WALLET BALANCES

### Via Django Admin: http://localhost:8000/admin/payments/wallet/

**What to verify:**

1. **Balance reflects transactions:**
   - Click on a user's wallet
   - Sum of all transactions should equal current balance
   - Formula: Initial balance - (sum of debits) + (sum of credits)

2. **No negative balances (unless allowed by policy):**
   - Typically should be >= 0
   - If negative, verify it was intentional

3. **Check available_balance calculation:**
   - Click wallet detail page
   - `available_balance` should exclude used cashback
   - Formula: `balance + (sum of unused cashback)`

---

## CHECKING BOOKINGS

### Via Django Admin: http://localhost:8000/admin/bookings/booking/

**What to verify:**

1. **Status flow is correct:**
   - Booking starts with: `status = 'payment_pending'`
   - After wallet payment: `status = 'confirmed'`
   - If payment fails: `status = 'payment_failed'`

2. **Traceability fields populated:**
   - `payment_reference` matches Payment transaction_id
   - `wallet_balance_before` not empty (for wallet payments)
   - `wallet_balance_after` not empty (for wallet payments)
   - `confirmed_at` timestamp set after confirmation

3. **Lock reference exists:**
   - `lock_id` field should have value
   - Should match an InventoryLock record

4. **No duplicate bookings:**
   - Same user shouldn't have multiple bookings for same dates
   - Check by filtering: user + hotel + dates

---

## CHECKING FOR RACE CONDITIONS

### Scenario: Concurrent wallet payments

**To simulate (Admin actions):**

1. **Create booking with amount Rs 1000**
2. **User wallet balance: Rs 2000**
3. **Simultaneously POST two payments:**
   - Payment A: Rs 1000
   - Payment B: Rs 1000
   
**Expected behavior (with select_for_update()):**
- Only ONE succeeds
- Other gets "Insufficient balance" error
- Wallet balance: Rs 1000 (only one deducted)

**Without select_for_update() (broken):**
- Both would claim success
- Wallet could go negative
- Bookings could both be confirmed

---

## CHECKING MESSAGE CLEARING

### Via Browser Test:

1. **Login to user account**
   - Should see "Login successful" message (from auth)

2. **Navigate to booking**
   - `/bookings/<booking_id>/confirmation/`
   - Message should be GONE
   - Only booking details visible

3. **Navigate to payment page**
   - `/bookings/<booking_id>/payment/`
   - Message should be GONE
   - Only payment details visible

**Proof:** No auth messages leak into booking flow

---

## CHECKING BUTTON DISABLE LOGIC

### Via Browser Test (hotel_detail.html):

1. **Open hotel detail page**
2. **Initially:** Proceed button is DISABLED (grayed out)
3. **Fill room type:** Still disabled
4. **Fill check-in date:** Still disabled
5. **Fill check-out date:** Still disabled
6. **Fill guest name:** Still disabled
7. **Fill email:** Still disabled
8. **Fill phone:** Button becomes ENABLED (clickable)
9. **Delete one field:** Button becomes DISABLED again

**Proof:** Real-time validation working

---

## CHECKING ROOM TYPE VALIDATION

### Via Browser Test (hotel_detail.html) or API:

**Scenario 1: Empty room type**
```
POST /hotels/10/book/
Body: room_type=&check_in=2026-01-17&...
Result: Error message "Please select a room type"
Status: 400 or page reload with error
```

**Scenario 2: Invalid room type**
```
POST /hotels/10/book/
Body: room_type=99999&check_in=2026-01-17&...
Result: Error message "Selected room type not found"
Status: 400 or page reload with error
```

**Scenario 3: Valid room type**
```
POST /hotels/10/book/
Body: room_type=37&check_in=2026-01-17&...
Result: Booking created (201)
Booking status: payment_pending
```

**Proof:** Backend validation prevents invalid room selections

---

## CHECKING BACK BUTTON STATE

### Via Browser Test:

1. **Fill booking form completely**
   - Room, dates, guest info
   
2. **Click "Proceed to Payment"**
   - Navigate to confirmation page

3. **Click browser BACK button**
   - Should return to hotel detail page
   - Form fields should be populated (from session)

4. **Verify form has data:**
   - Room type selected
   - Dates filled
   - Guest name, email, phone present

**Proof:** Session state recovery working

---

## CHECKING IMAGE FALLBACK

### Via Browser Test (hotel_detail.html):

1. **Open hotel detail page**
2. **Images that exist:** Display normally
3. **Images with missing files:** Show placeholder

**HTML Code:**
```html
<img src="{{ image.image.url }}" 
     onerror="this.src='/static/images/placeholder.png'">
```

**Proof:** Fallback mechanism prevents broken images

---

## SQL QUERIES FOR VERIFICATION

**Check all wallet transactions today:**
```sql
SELECT * FROM payments_wallettransaction 
WHERE DATE(created_at) = CURDATE()
ORDER BY created_at DESC
LIMIT 20;
```

**Check all inventory locks for a booking:**
```sql
SELECT * FROM bookings_inventorylock 
WHERE reference_id = 'BOOKING_ID_HERE';
```

**Check for orphaned locks (booking deleted but lock remains):**
```sql
SELECT l.* FROM bookings_inventorylock l
LEFT JOIN bookings_booking b ON l.booking_id = b.id
WHERE b.id IS NULL
  AND l.expires_at > NOW();
```

**Check for negative wallet balances:**
```sql
SELECT * FROM payments_wallet 
WHERE balance < 0;
```

**Check for bookings without payment records (should be rare):**
```sql
SELECT b.* FROM bookings_booking b
LEFT JOIN payments_payment p ON p.booking_id = b.id
WHERE b.status = 'confirmed'
  AND p.id IS NULL;
```

---

## AUTOMATED MONITORING

**Create a scheduled check (cron job):**

```python
# management/commands/check_wallet_consistency.py

from django.core.management.base import BaseCommand
from bookings.models import Booking, InventoryLock
from payments.models import Wallet, WalletTransaction

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Check for orphaned locks
        orphaned = InventoryLock.objects.filter(
            booking__isnull=True,
            expires_at__gt=timezone.now()
        )
        if orphaned.exists():
            self.stdout.write(f"WARNING: {orphaned.count()} orphaned locks!")
        
        # Check for unmatched payments
        confirmed_bookings = Booking.objects.filter(status='confirmed')
        for booking in confirmed_bookings:
            if not booking.payment_set.exists():
                self.stdout.write(f"WARNING: Booking {booking.id} confirmed but no payment!")
        
        # Check for negative balances
        negative = Wallet.objects.filter(balance__lt=0)
        if negative.exists():
            for wallet in negative:
                self.stdout.write(f"WARNING: User {wallet.user.id} has negative balance!")
        
        self.stdout.write("Wallet consistency check complete")
```

**Run daily:**
```bash
0 2 * * * cd /app && python manage.py check_wallet_consistency
```

---

## CONCLUSION

**All fixes are verifiable via:**
- ✅ Admin panel (data integrity)
- ✅ Browser testing (UX flow)
- ✅ SQL queries (database consistency)
- ✅ Server logs (transaction traces)

**Monitoring ensures production stability.**
