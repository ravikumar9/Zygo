# 🔴 BLOCKER #1: WALLET PAYMENT FAILS - PRICING MISMATCH

## STATUS: ❌ BROKEN (ARCHITECTURAL FLAW DISCOVERED)

## WHAT'S BROKEN

**Test Executed**: Wallet-only payment on existing reserved booking  
**Expected**: Wallet deducted, booking confirmed, payment recorded  
**Actual**: Payment rejected with error: "Payment amount mismatch. Expected ₹2784.80, got ₹2360.00"

## ROOT CAUSE (CRITICAL)

**Two different pricing logics in the codebase**:

### 1. Booking Creation (`hotels/views.py` Line 647)
```python
total = base_total - corp_discount_amount  # NO GST
booking = Booking.objects.create(
    total_amount=total,  # ← Stores BASE amount (₹2360)
    ...
)
```

### 2. Payment Finalization (`bookings/payment_finalization.py` Line 97)
```python
pricing = calculate_pricing(...)  # INCLUDES GST
expected_total = pricing['total_payable']  # ← Expects GST-inclusive (₹2784.80)

if abs(total_paid - expected_total) > Decimal('0.01'):
    return {'status': 'error', 'message': 'Payment amount mismatch'}
```

## THE MISMATCH

| Source | Amount | Includes GST? |
|--------|--------|---------------|
| booking.total_amount (stored in DB) | ₹2360.00 | ❌ NO |
| calculate_pricing() fresh calculation | ₹2784.80 | ✅ YES |
| Difference | ₹424.80 | (18% GST on ₹2360) |

## WHY THIS BREAKS PRODUCTION

1. **User books hotel** → `total_amount = ₹2360` (base only)
2. **User tries to pay** → `finalize_booking_payment()` recalculates pricing
3. **Pricing calc adds GST** → expects ₹2784.80
4. **User pays** → ₹2360 (from booking.total_amount)
5. **Payment fails** → Amount mismatch error
6. **Booking stuck** → Status remains 'reserved', never confirmed
7. **Wallet NOT deducted** → Money not processed
8. **Inventory locked** → Room unavailable for other users

## EVIDENCE

```
======================================================================
TEST #1: WALLET-ONLY PAYMENT FLOW (REAL DATABASE TEST)
======================================================================

BEFORE PAYMENT
Wallet Balance: ₹5000.00
Booking Status: reserved
Total Amount: ₹2360.00

EXECUTING WALLET-ONLY PAYMENT...
[RESULT] Message: Payment amount mismatch. Expected ₹2784.80, got ₹2360.00

AFTER PAYMENT
Wallet Balance: ₹5000.00 (NOT CHANGED)
Booking Status: reserved (NOT CHANGED)
Paid Amount: ₹0.00 (NOT CHANGED)

RESULT: ❌ FAILED (6 issues)
```

## FILES INVOLVED

1. **hotels/views.py** Line 647 - Creates booking with base total (no GST)
2. **bookings/payment_finalization.py** Line 97 - Recalculates with GST
3. **bookings/pricing_calculator.py** - Adds GST to subtotal

## POSSIBLE FIXES (CHOOSE ONE)

### Option A: Store GST-inclusive amount in booking.total_amount ✅ RECOMMENDED
**Impact**: Booking creation changes  
**Risk**: Medium (requires testing all booking flows)  
**Benefit**: Single source of truth for pricing

```python
# In hotels/views.py, BEFORE creating booking:
pricing = calculate_pricing(
    base_amount=base_total,
    promo_code=promo_code,
    user=request.user
)

booking = Booking.objects.create(
    total_amount=pricing['total_payable'],  # ← GST-inclusive
    ...
)
```

### Option B: Remove pricing recalculation in finalize_booking_payment
**Impact**: Payment finalization changes  
**Risk**: High (loses fraud detection)  
**Benefit**: Quick fix

```python
# In payment_finalization.py:
# REMOVE: fresh pricing calculation
# USE: booking.total_amount directly

expected_total = booking.total_amount  # ← Trust DB value
```

### Option C: Add GST to booking.total_amount after creation
**Impact**: Signal/post-save hook  
**Risk**: Low  
**Benefit**: Backward compatible

```python
# In bookings/signals.py:
@receiver(pre_save, sender=Booking)
def ensure_gst_in_total(sender, instance, **kwargs):
    if instance.booking_type == 'hotel' and not instance.pk:
        # Recalculate with GST on first save
        pricing = calculate_pricing(...)
        instance.total_amount = pricing['total_payable']
```

## DECISION REQUIRED

Which fix should be implemented?

**RECOMMENDATION**: **Option A** - Fix booking creation to use pricing calculator  
**Reason**: Single source of truth, prevents future mismatches, aligns with architecture

## NEXT STEPS

1. ⏸️ **PAUSE all other tasks**
2. 🔧 **Fix booking creation** to use calculate_pricing()
3. ✅ **Re-test wallet payment flow**
4. ✅ **Verify gateway payment flow** (same issue likely exists)
5. ✅ **Test with promo codes** (ensure GST calculated after discount)
6. 📋 **Update all documentation** with correct pricing flow

## BLOCKER SEVERITY

**CRITICAL - PRODUCTION STOPPER**

- ❌ All wallet payments will fail
- ❌ All bookings will be stuck in 'reserved'
- ❌ Revenue lost (users can't complete payment)
- ❌ Inventory locked unnecessarily
- ❌ User frustration (payment works → fails inexplicably)

---

**Discovered by**: Real end-to-end test execution  
**Test file**: `test_wallet_existing.py`  
**Date**: 2026-01-20 13:44 UTC
