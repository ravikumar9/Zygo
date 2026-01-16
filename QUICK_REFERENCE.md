# ⚡ QUICK START - DEV TESTING

## 🚀 Deploy in 5 Minutes

```bash
# SSH to DEV
ssh user@goexplorer-dev.cloud
cd /path/to/goexplorer

# Deploy
git pull origin main
python manage.py migrate
python run_seed.py
sudo systemctl restart goexplorer

# Setup Cron
crontab -e
# Add: */1 * * * * python manage.py expire_bookings
```

---

## 🧪 7 Tests You Must Run (Browser)

### Test 1: Corporate Signup → Approval
```
URL: https://goexplorer-dev.cloud/corporate/signup/
Action: Signup as newcorp@newcorp.com → Admin approves
Result: Coupon CORP_NEWCORP auto-generated
Screenshot: signup_form.png, admin_approval.png
```

### Test 2: Corporate Dashboard
```
URL: https://goexplorer-dev.cloud/corporate/dashboard/
Action: Login as admin@testcorp.com (seeded: ₹10,000)
Result: Shows wallet, bookings, coupon, savings
Screenshot: dashboard.png
```

### Test 3: Hotel Booking + Wallet Payment
```
URL: https://goexplorer-dev.cloud/hotels/
Action: Book hotel, pay with wallet
Result: Status=payment_pending, then confirmed, wallet reduced
Screenshot: pending.png, success.png, wallet.png
```

### Test 4: Booking Expiry (11 min)
```
URL: https://goexplorer-dev.cloud/admin/bookings/booking/
Action: Create payment_pending booking, wait 11 min
Result: Status → expired, inventory restored
Screenshot: before_expiry.png, after_expiry.png
```

### Test 5: Hotel Policies
```
URL: https://goexplorer-dev.cloud/hotels/[id]/
Action: Scroll to Hotel Policies card
Result: Check-in (2PM), checkout (11AM), cancellation, rules visible
Screenshot: policies.png
```

### Test 6: Wallet Transactions
```
URL: https://goexplorer-dev.cloud/admin/payments/wallettransaction/
Action: View wallet transaction after booking
Result: balance_before, balance_after, reference_id, status all filled
Screenshot: transaction.png
```

### Test 7: Bookings Admin
```
URL: https://goexplorer-dev.cloud/admin/bookings/booking/
Action: Filter by status (payment_pending, confirmed, expired)
Result: Status badges show correctly, inventory reflected
Screenshot: admin_list.png
```

---

## 🔐 Login Credentials (Seeded)

```
CORPORATE (Approved):
  admin@testcorp.com / TestPassword123!
  Wallet: ₹10,000
  Coupon: CORP_TESTCORP (10% off, max ₹1,000)

EMAIL VERIFIED:
  qa_email_verified@example.com / TestPassword123!
  Wallet: ₹10,000

BOTH VERIFIED:
  qa_both_verified@example.com / TestPassword123!
  Wallet: ₹10,000
```

---

## ✅ Checklist

- [ ] Deploy code to DEV
- [ ] Run migrations: `python manage.py migrate`
- [ ] Run seed: `python run_seed.py`
- [ ] Setup cron: `crontab -e`
- [ ] Test 1: Corporate signup+approval (screenshot)
- [ ] Test 2: Corporate dashboard (screenshot)
- [ ] Test 3: Hotel booking+wallet (screenshot)
- [ ] Test 4: Booking expiry (screenshot)
- [ ] Test 5: Hotel policies (screenshot)
- [ ] Test 6: Wallet transactions (screenshot)
- [ ] Test 7: Admin booking list (screenshot)
- [ ] Verify: No "Image unavailable" text
- [ ] Verify: No success alerts before payment
- [ ] Verify: Corporate coupon auto-applies
- [ ] Document all evidence
- [ ] Mark features as FIXED

---

## 🚫 MUST NOT HAPPEN

❌ "Image unavailable" text  
❌ Success alerts before payment  
❌ Booking status doesn't change  
❌ Wallet balance doesn't update  
❌ Coupon not auto-generated  
❌ Hotel policies missing  
❌ Inventory not restored after expiry  

---

## 📸 Evidence Format (Per Test)

```
TEST X: [Feature Name]
URL: https://goexplorer-dev.cloud/[path]/
Screenshot: [filename.png]
DB Record: [Model ID, key fields]
Status: PASS ✅
```

---

## 🎯 Done When

All 7 tests PASS with:
✅ DEV URL visible in browser  
✅ Screenshot captured  
✅ DB record ID documented  
✅ Status changed correctly (before/after)  
✅ No errors in browser console  

---

**Ready?** → Copy URLs above → Login with seeded credentials → Start testing! 🚀
