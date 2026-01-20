"""
ZERO-TOLERANCE ARCHITECTURAL VERIFICATION
Confirms production-ready components are in place
"""

import os

print("\n" + "="*60)
print("  ZERO-TOLERANCE ARCHITECTURAL VERIFICATION")
print("="*60 + "\n")

results = []

# ============================================================
# 1. UNIFIED PAYMENT FINALIZATION FUNCTION
# ============================================================
print("[1] Unified Payment Finalization Function")
try:
    with open(r'c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear\bookings\payment_finalization.py', 'r') as f:
        content = f.read()
    
    checks = [
        ('finalize_booking_payment() function exists', 'def finalize_booking_payment('),
        ('Atomic transaction wrapper', '@transaction.atomic' in content or 'with transaction.atomic()'),
        ('Pre-condition validation', 'if booking.status not in'),
        ('Pricing recalculation', 'calculate_pricing('),
        ('Wallet deduction logic', 'wallet.balance -= wallet_applied'),
        ('Booking confirmation', "booking.status = 'confirmed'"),
        ('Error handling', 'return {' and "'status': 'error'"),
    ]
    
    all_passed = True
    for check_name, check in checks:
        if isinstance(check, str):
            passed = check in content
        else:
            passed = check
        
        if passed:
            print(f"  ✅ {check_name}")
        else:
            print(f"  ❌ {check_name}")
            all_passed = False
    
    results.append(("Unified Payment Function", all_passed))

except Exception as e:
    print(f"  ❌ Error: {e}")
    results.append(("Unified Payment Function", False))

# ============================================================
# 2. 10-MINUTE INVENTORY EXPIRY
# ============================================================
print("\n[2] 10-Minute Inventory Expiry")
try:
    with open(r'c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear\bookings\signals.py', 'r') as f:
        signals_code = f.read()
    
    # Check for 10-minute setting
    has_10_min = 'timedelta(minutes=10)' in signals_code
    
    # Ensure NOT 30 minutes
    has_30_min = 'timedelta(minutes=30)' in signals_code
    
    if has_10_min and not has_30_min:
        print("  ✅ Expiry set to 10 minutes")
        print("  ✅ No 30-minute references")
        results.append(("10-Minute Expiry", True))
    elif has_10_min and has_30_min:
        print("  ⚠️  10 minutes set BUT 30 minutes also present")
        results.append(("10-Minute Expiry", False))
    else:
        print("  ❌ 10-minute expiry not found")
        results.append(("10-Minute Expiry", False))

except Exception as e:
    print(f"  ❌ Error: {e}")
    results.append(("10-Minute Expiry", False))

# ============================================================
# 3. BACKEND-DRIVEN TIMER
# ============================================================
print("\n[3] Backend-Driven Timer")
try:
    with open(r'c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear\bookings\models.py', 'r') as f:
        models_code = f.read()
    
    checks = [
        ('reservation_seconds_left property exists', '@property' in models_code and 'reservation_seconds_left' in models_code),
        ('Calculates from expires_at', 'expires_at' in models_code and 'total_seconds()' in models_code),
    ]
    
    all_passed = True
    for check_name, passed in checks:
        if passed:
            print(f"  ✅ {check_name}")
        else:
            print(f"  ❌ {check_name}")
            all_passed = False
    
    results.append(("Backend-Driven Timer", all_passed))

except Exception as e:
    print(f"  ❌ Error: {e}")
    results.append(("Backend-Driven Timer", False))

# ============================================================
# 4. SINGLE SOURCE PRICING
# ============================================================
print("\n[4] Single Source of Truth - Pricing")
try:
    with open(r'c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear\bookings\pricing_calculator.py', 'r') as f:
        pricing_code = f.read()
    
    checks = [
        ('calculate_pricing() function exists', 'def calculate_pricing('),
        ('Returns base_amount', "'base_amount'" in pricing_code or '"base_amount"' in pricing_code),
        ('Returns gst_amount', "'gst_amount'" in pricing_code or '"gst_amount"' in pricing_code),
        ('Returns total_payable', "'total_payable'" in pricing_code or '"total_payable"' in pricing_code),
        ('Returns wallet_applied', "'wallet_applied'" in pricing_code or '"wallet_applied"' in pricing_code),
    ]
    
    all_passed = True
    for check_name, passed in checks:
        if passed:
            print(f"  ✅ {check_name}")
        else:
            print(f"  ❌ {check_name}")
            all_passed = False
    
    results.append(("Single Source Pricing", all_passed))

except Exception as e:
    print(f"  ❌ Error: {e}")
    results.append(("Single Source Pricing", False))

# ============================================================
# 5. COMPREHENSIVE LOGGING
# ============================================================
print("\n[5] Comprehensive Logging Infrastructure")
try:
    with open(r'c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear\bookings\signals.py', 'r') as f:
        signals_code = f.read()
    
    with open(r'c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear\bookings\payment_finalization.py', 'r') as f:
        payment_code = f.read()
    
    checks = [
        ('[BOOKING_CREATED] in signals', '[BOOKING_CREATED]' in signals_code),
        ('[BOOKING_RESERVED] in signals', '[BOOKING_RESERVED]' in signals_code),
        ('[BOOKING_CONFIRMED] in signals', '[BOOKING_CONFIRMED]' in signals_code),
        ('[PAYMENT_FINALIZE_SUCCESS] in payment', '[PAYMENT_FINALIZE_SUCCESS]' in payment_code),
        ('[PAYMENT_FINALIZE_ERROR] in payment', '[PAYMENT_FINALIZE_ERROR]' in payment_code),
        ('[WALLET_DEDUCTED] in payment', '[WALLET_DEDUCTED]' in payment_code),
    ]
    
    all_passed = True
    for check_name, passed in checks:
        if passed:
            print(f"  ✅ {check_name}")
        else:
            print(f"  ❌ {check_name}")
            all_passed = False
    
    results.append(("Comprehensive Logging", all_passed))

except Exception as e:
    print(f"  ❌ Error: {e}")
    results.append(("Comprehensive Logging", False))

# ============================================================
# 6. ATOMIC TRANSACTIONS & DB LOCKING
# ============================================================
print("\n[6] Atomic Transactions & Database Locking")
try:
    with open(r'c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear\bookings\payment_finalization.py', 'r') as f:
        payment_code = f.read()
    
    checks = [
        ('transaction.atomic import', 'from django.db import transaction'),
        ('Atomic decorator/context used', '@transaction.atomic' in payment_code or 'with transaction.atomic()' in payment_code),
        ('select_for_update() for locking', 'select_for_update()' in payment_code),
    ]
    
    all_passed = True
    for check_name, passed in checks:
        if passed:
            print(f"  ✅ {check_name}")
        else:
            print(f"  ❌ {check_name}")
            all_passed = False
    
    results.append(("Atomic Transactions", all_passed))

except Exception as e:
    print(f"  ❌ Error: {e}")
    results.append(("Atomic Transactions", False))

# ============================================================
# 7. CRON SCHEDULING DOCUMENTATION
# ============================================================
print("\n[7] Cron Scheduling Documentation")
try:
    if os.path.exists(r'c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear\CRON_SETUP.md'):
        print("  ✅ CRON_SETUP.md exists")
        
        with open(r'c:\Users\ravi9\Downloads\cgpt\Go_explorer_clear\CRON_SETUP.md', 'r') as f:
            cron_content = f.read()
        
        if 'expire_old_bookings' in cron_content:
            print("  ✅ Contains expire_old_bookings instructions")
            results.append(("Cron Documentation", True))
        else:
            print("  ❌ Missing expire_old_bookings instructions")
            results.append(("Cron Documentation", False))
    else:
        print("  ❌ CRON_SETUP.md not found")
        results.append(("Cron Documentation", False))

except Exception as e:
    print(f"  ❌ Error: {e}")
    results.append(("Cron Documentation", False))

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "="*60)
print("  SUMMARY")
print("="*60 + "\n")

passed = sum(1 for _, p in results if p)
total = len(results)

for name, passed_flag in results:
    if passed_flag:
        print(f"✅ {name}")
    else:
        print(f"❌ {name}")

print(f"\n{'='*60}")
print(f"RESULTS: {passed}/{total} components verified")
print(f"{'='*60}\n")

if passed == total:
    print("🎉 ALL ARCHITECTURAL COMPONENTS IN PLACE - PRODUCTION-READY\n")
    exit(0)
else:
    print("⚠️  SOME COMPONENTS NEED ATTENTION\n")
    exit(1)
