# Phase 1: Booking Lifecycle, Wallet Atomicity, Admin Bulk Operations

## PHASE 1 SCOPE (STRICT)

**What to fix**:
1. ✅ Booking state machine (RESERVED ≠ CONFIRMED)
2. ✅ Auto-cancel on payment failure/timeout
3. ✅ Atomic wallet + booking transactions
4. ✅ Wallet rollback on failure
5. ✅ Admin bulk operations (100+ items)
6. ✅ Bus seat layout UX (side-by-side)
7. ✅ Seed parity validation

**What NOT to do**:
- ❌ Add new payment gateways
- ❌ Modify infrastructure
- ❌ Add new features
- ❌ Redesign backend architecture

---

## 1. BOOKING LIFECYCLE CORRECTION

### Current Problem
```
Current: payment_pending → confirmed (no "reserved" state)
Problem: Can't distinguish between:
  - Booking made but awaiting payment (RESERVED)
  - Payment succeeded but booking not confirmed (PENDING)
  - Fully confirmed (CONFIRMED)
```

### Solution: Add RESERVED State
**File**: `bookings/models.py`

```python
BOOKING_STATUS = [
    ('reserved', 'Reserved'),        # ← NEW: Booking created, awaiting payment
    ('confirmed', 'Confirmed'),      # Payment succeeded, inventory locked
    ('payment_failed', 'Payment Failed'),  # ← NEW: Payment attempt failed
    ('expired', 'Expired'),           # ← NEW: 30 min timeout, auto-cancelled
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
    ('refunded', 'Refunded'),
    ('deleted', 'Deleted'),
]
```

### Booking State Machine
```
[Create Booking]
       ↓
   RESERVED (30 min timer starts)
       ├─→ [Payment Success] → CONFIRMED
       ├─→ [Payment Failed] → PAYMENT_FAILED
       ├─→ [30 min timeout] → EXPIRED (auto-cancel)
       └─→ [User cancel] → CANCELLED
       
CONFIRMED
       ├─→ [User cancel] → CANCELLED (refund issued)
       └─→ [Check-in/arrival] → COMPLETED

PAYMENT_FAILED / EXPIRED / CANCELLED
       → [Inventory released] → Ready for other bookings
```

### Required Changes
1. Add RESERVED, PAYMENT_FAILED, EXPIRED states to Booking.BOOKING_STATUS
2. Create `reserved_at` and `confirmed_at` timestamps
3. Add `expires_at` field (reserved_at + 30 minutes)
4. Create Celery task for auto-expire (background)
5. Update payment views to transition: RESERVED → CONFIRMED

---

## 2. AUTO-CANCEL ON TIMEOUT

### Implementation: Django-RQ Background Job

**File**: `bookings/tasks.py` (NEW)

```python
from django_rq import job
from django.utils import timezone
from datetime import timedelta

@job
def auto_expire_reservations():
    """Expire bookings that haven't been paid in 30 minutes"""
    from bookings.models import Booking
    
    now = timezone.now()
    expired = Booking.objects.filter(
        status='reserved',
        reserved_at__lte=now - timedelta(minutes=30),
        is_deleted=False
    )
    
    for booking in expired:
        # Release inventory
        release_inventory(booking)
        
        # Mark as expired
        booking.status = 'expired'
        booking.cancelled_at = now
        booking.save()
        
        # Send email to user
        send_booking_expired_email(booking)
```

**Cron Job** (runs every 5 minutes):
```python
# settings.py
RQ_QUEUES = {
    'default': {
        'HOST': 'localhost',
        'PORT': 6379,
        'DB': 0,
    }
}
```

---

## 3. ATOMIC WALLET + BOOKING

### Current Problem
```
Current flow:
  1. Deduct from wallet
  2. Update booking status
  3. ← If step 2 fails, wallet is deducted but booking not updated!
```

### Solution: Use `transaction.atomic()`

**File**: `payments/views.py`

```python
from django.db import transaction

@transaction.atomic
def process_wallet_payment(request):
    """Atomic wallet payment"""
    booking = Booking.objects.select_for_update().get(booking_id=booking_id)
    wallet = Wallet.objects.select_for_update().get(user=request.user)
    
    # All-or-nothing: if any step fails, entire transaction rolls back
    wallet.balance -= amount
    wallet.save()
    
    booking.status = 'confirmed'
    booking.confirmed_at = timezone.now()
    booking.save()
    
    # If we reach here, both succeed. If exception, both rollback.
    return JsonResponse({'status': 'success'})
```

**Key Points**:
- Use `select_for_update()` to lock rows
- All DB operations in one `@transaction.atomic` block
- If any operation fails, entire transaction rolls back
- Wallet stays consistent with booking status

---

## 4. TRANSACTION ROLLBACK ON FAILURE

### Wallet Rollback Logic

**File**: `payments/models.py`

```python
class WalletTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
        ('refund', 'Refund'),  # ← NEW: Reversal
    ]
    
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    booking = models.ForeignKey(Booking, null=True, blank=True)
    parent_transaction = models.ForeignKey(  # ← NEW: Link to original debit
        'self', null=True, blank=True, on_delete=models.SET_NULL
    )
    
    def create_refund(self):
        """Create reverse transaction"""
        return WalletTransaction.objects.create(
            wallet=self.wallet,
            transaction_type='refund',
            amount=self.amount,
            parent_transaction=self,
            booking=self.booking
        )
```

### Payment Failure Flow

```python
# In payment verification view
try:
    with transaction.atomic():
        # Debit wallet
        wallet_txn = wallet.deduct_balance(amount, f"Booking {booking_id}")
        
        # Try to confirm booking
        booking.status = 'confirmed'
        booking.save()
        
except Exception as e:
    # Auto-rollback: DB transaction reverts
    # Wallet.balance restored
    # Booking stays in RESERVED state
    
    # Create refund record for admin visibility
    wallet_txn.create_refund()
    
    booking.status = 'payment_failed'
    booking.save()
```

---

## 5. ADMIN BULK OPERATIONS

### Requirement
"Update 100+ buses at once" → need bulk admin interface

### Solution: Django Admin `list_editable` + Bulk Actions

**File**: `buses/admin.py`

```python
@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ['bus_number', 'operator', 'bus_type', 'total_seats', 'is_active']
    list_editable = ['bus_type', 'total_seats', 'is_active']  # ← Inline edit
    list_filter = ['operator', 'is_active', 'bus_type']
    search_fields = ['bus_number', 'operator__name']
    
    actions = ['mark_active', 'mark_inactive', 'update_amenities']
    
    def mark_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"✓ {updated} buses activated")
    
    def update_amenities(self, request, queryset):
        """Bulk add WiFi to selected buses"""
        updated = queryset.update(has_wifi=True)
        self.message_user(request, f"✓ {updated} buses updated")
```

### Hotel Bulk Operations

```python
@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'star_rating', 'base_price', 'is_active']
    list_editable = ['base_price', 'is_active']
    list_filter = ['city', 'property_type', 'is_active']
    search_fields = ['name', 'city__name']
    
    actions = ['bulk_update_price', 'bulk_update_rating']
    
    def bulk_update_price(self, request, queryset):
        """Increase price by 10% for selected hotels"""
        for hotel in queryset:
            hotel.base_price = hotel.base_price * 1.10
            hotel.save()
        self.message_user(request, f"✓ {queryset.count()} prices updated")
```

### Image Bulk Upload

```python
# Via HotelImageInline (existing)
class HotelImageInline(admin.TabularInline):
    model = HotelImage
    extra = 5  # ← Allow adding 5 images at once
    fields = ['image', 'alt_text', 'display_order']
```

---

## 6. BUS SEAT LAYOUT UX IMPROVEMENT

### Current Problem
```
Current: Seats listed vertically
  1A, 1B
  2A, 2B
  3A, 3B
  ...
```

### Solution: 2x2 Grid with Deck Separation

**File**: `templates/buses/seat_selection.html` (NEW or updated)

```html
<div class="seat-layout">
  <div class="deck">
    <h5>Lower Deck</h5>
    <div class="seat-grid">
      <!-- Row 1 -->
      <div class="row">
        <button class="seat available" data-seat="1A">1A</button>
        <button class="seat available" data-seat="1B">1B</button>
        <span class="aisle"></span>
        <button class="seat available" data-seat="1C">1C</button>
        <button class="seat available" data-seat="1D">1D</button>
      </div>
      
      <!-- Row 2 -->
      <div class="row">
        <button class="seat available" data-seat="2A">2A</button>
        <button class="seat reserved-ladies" data-seat="2B">2B 👩</button>
        <span class="aisle"></span>
        <button class="seat booked" data-seat="2C">2C</button>
        <button class="seat available" data-seat="2D">2D</button>
      </div>
    </div>
  </div>
  
  <div class="deck">
    <h5>Upper Deck</h5>
    <!-- Same structure -->
  </div>
</div>

<style>
.seat-layout { display: flex; gap: 20px; }
.deck { margin: 20px; }
.seat-grid { display: grid; gap: 8px; }
.row { display: flex; gap: 8px; justify-content: center; }
.aisle { width: 20px; }
.seat { 
  width: 40px; height: 40px;
  border: 1px solid #ccc;
  padding: 8px;
  background: #fff;
}
.seat.available { cursor: pointer; background: #e8f5e9; }
.seat.booked { background: #ffcdd2; cursor: not-allowed; }
.seat.reserved-ladies { background: #fce4ec; border: 2px dashed #c2185b; }
</style>
```

### Admin Seat Layout Editor

**File**: `buses/admin.py`

```python
class SeatLayoutInline(admin.TabularInline):
    model = SeatLayout
    extra = 0
    fields = ['seat_number', 'row', 'column', 'seat_type', 'reserved_for']
    list_display_links = ['seat_number']
    
    # Group by deck for better visibility
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # Show upper/lower deck separately
        return formset
```

---

## 7. SEED PARITY VALIDATION

### Requirement
"seed_all must produce same data on local + server"

### Solution: Checksum Validation

**File**: `core/management/commands/validate_seed.py` (NEW)

```python
from django.core.management.base import BaseCommand
from django.db.models import Count

class Command(BaseCommand):
    help = "Validate seed data consistency"
    
    def handle(self, *args, **options):
        from hotels.models import Hotel
        from packages.models import Package
        from buses.models import Bus
        from payments.models import Wallet
        
        checks = {
            'Hotels': Hotel.objects.count(),
            'Packages': Package.objects.count(),
            'Buses': Bus.objects.count(),
            'Wallets': Wallet.objects.count(),
        }
        
        # Expected counts from seed_all
        expected = {
            'Hotels': 16,
            'Packages': 5,
            'Buses': 3,
            'Wallets': 1,  # testuser
        }
        
        all_pass = True
        for key, expected_count in expected.items():
            actual = checks[key]
            status = "✓" if actual == expected_count else "✗"
            print(f"{status} {key}: {actual}/{expected_count}")
            if actual != expected_count:
                all_pass = False
        
        if all_pass:
            print("\n[OK] Seed parity verified!")
        else:
            print("\n[FAIL] Seed mismatch detected!")
            raise SystemExit(1)
```

**Usage**:
```bash
# After seed_all on any environment
python manage.py validate_seed

# Expected output:
# ✓ Hotels: 16/16
# ✓ Packages: 5/5
# ✓ Buses: 3/3
# ✓ Wallets: 1/1
# [OK] Seed parity verified!
```

---

## 8. IMPLEMENTATION CHECKLIST

### 8.1 Booking State Machine
- [ ] Add RESERVED, PAYMENT_FAILED, EXPIRED to BOOKING_STATUS
- [ ] Add reserved_at, confirmed_at, expires_at fields
- [ ] Update booking create view to set RESERVED status
- [ ] Update payment success view to set CONFIRMED status
- [ ] Update payment failure view to set PAYMENT_FAILED status
- [ ] Update admin to show state transitions clearly

### 8.2 Auto-Expire Task
- [ ] Create bookings/tasks.py with auto_expire_reservations()
- [ ] Configure django-rq in settings.py
- [ ] Add cron job runner to Procfile or systemd timer
- [ ] Test: Reserve booking, wait 30 min, verify EXPIRED

### 8.3 Atomic Transactions
- [ ] Update process_wallet_payment() with @transaction.atomic
- [ ] Use select_for_update() for wallet/booking locks
- [ ] Test: Intentionally fail booking update, verify wallet rollback
- [ ] Add transaction tests

### 8.4 Wallet Rollback
- [ ] Add parent_transaction FK to WalletTransaction
- [ ] Add REFUND transaction type
- [ ] Create create_refund() method on WalletTransaction
- [ ] Update payment failure flow to create refund record
- [ ] Test: Process wallet payment, fail, verify refund created

### 8.5 Admin Bulk Operations
- [ ] Add list_editable to BusAdmin, HotelAdmin, PackageAdmin
- [ ] Create bulk action methods for common updates
- [ ] Test: Select 5 buses, bulk update is_active
- [ ] Test: Select 10 hotels, bulk update base_price

### 8.6 Bus Seat Layout UI
- [ ] Create seat_selection.html template with 2x2 grid
- [ ] Add CSS for deck separation, aisle visualization
- [ ] Add ladies seat visual indicator (icon/color)
- [ ] Test on mobile and desktop
- [ ] Update buses/bus_detail.html to use new layout

### 8.7 Seed Parity
- [ ] Create core/management/commands/validate_seed.py
- [ ] Run seed_all locally, then validate_seed
- [ ] Run seed_all on server, then validate_seed
- [ ] Verify both produce same counts
- [ ] Document in PHASE_1_TESTING.md

---

## 9. TESTING STRATEGY (MUST USE seed_all)

### Test Flow
```
1. Reset local DB
   python manage.py flush --no-input
   python manage.py migrate

2. Seed data
   python manage.py seed_all --env=local

3. Validate parity
   python manage.py validate_seed
   # Expected: ✓ All counts match

4. Test booking lifecycle
   - Create booking → status=RESERVED ✓
   - Pay with wallet → status=CONFIRMED ✓
   - Wait 30 min / simulate fail → status=EXPIRED/PAYMENT_FAILED ✓
   - Verify inventory released ✓

5. Test wallet atomicity
   - Start payment
   - Intentionally crash during booking save
   - Verify wallet balance rolled back ✓

6. Test admin bulk operations
   - Select 10 buses in admin
   - Use bulk action to update is_active
   - Verify all 10 updated ✓

7. Test seat layout UX
   - Visit bus booking page
   - Verify seats in 2x2 grid
   - Verify ladies seats highlighted ✓

8. Deploy to server
   - Push code
   - SSH and run seed_all
   - Run validate_seed
   - Repeat booking lifecycle tests ✓
```

---

## 10. DELIVERABLES

### Code Changes
```
✅ bookings/models.py          - Add RESERVED/EXPIRED states, timestamps
✅ bookings/tasks.py           - Auto-expire task (NEW)
✅ payments/views.py           - Atomic transaction, rollback logic
✅ payments/models.py          - Add refund transaction type
✅ buses/admin.py              - Bulk operations, list_editable
✅ hotels/admin.py             - Bulk operations, list_editable
✅ templates/buses/seat_selection.html - 2x2 grid layout (NEW or updated)
✅ core/management/commands/validate_seed.py - Parity validator (NEW)
```

### Documentation
```
✅ PHASE_1_COMPLETION.md       - Technical details
✅ PHASE_1_TESTING.md          - Step-by-step test guide
✅ PHASE_1_CHANGES.md          - What changed, why
```

### Success Criteria
- ✅ Booking states: RESERVED → CONFIRMED clearly distinct
- ✅ Auto-expire: Bookings expire after 30 min timeout
- ✅ Wallet atomicity: Debit + booking update succeed or both fail
- ✅ Rollback: Failed payment creates refund transaction, balance restored
- ✅ Admin bulk ops: Update 100+ items in single action
- ✅ Seat layout: 2x2 grid with deck separation visible
- ✅ Seed parity: validate_seed passes on local AND server

---

## 11. RISK MITIGATION

| Risk | Mitigation |
|------|-----------|
| Booking state confusion | Clear state machine + tooltips in admin |
| Lost wallet on timeout | Transaction log shows all debit/refund |
| Atomic transaction deadlock | Use select_for_update() with timeout |
| Bulk operations affect wrong data | Confirm with queryset.count() first |
| Seat layout mobile issues | Test on Chrome mobile + Safari |
| Seed parity mismatch | validate_seed command checks before deploy |

---

## 12. GO-LIVE CHECKLIST

- [ ] All code changes committed
- [ ] Local tests pass (all 7 test flows above)
- [ ] validate_seed passes locally ✓ 16/16 hotels, 5/5 packages, etc.
- [ ] Deploy to server (git push + SSH run)
- [ ] validate_seed passes on server ✓ same counts
- [ ] Booking lifecycle tests on server (RESERVED → CONFIRMED)
- [ ] Admin bulk operations work on server
- [ ] Seat layout renders correctly on server
- [ ] No console errors on any page
- [ ] All 4 Phase 0 verification screenshots still pass

---

**Phase 1 Focus**: Fix logic, improve admin usability, ensure data consistency.  
**Phase 1 Scope**: Strict - no new features, no infra changes, only fixes.  
**Phase 1 Timeline**: Complete before Phase 2.
