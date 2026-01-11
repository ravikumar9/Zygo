# 🚀 SERVER DEPLOYMENT - QUICK REFERENCE

**Server:** goexplorer-dev.cloud  
**SSH User:** deployer  
**Password:** Thepowerof@9  
**Database:** goexplorer_dev

---

## OPTION 1: Automated Deployment (Recommended)

```bash
# 1. SSH to server
ssh deployer@goexplorer-dev.cloud
# Password: Thepowerof@9

# 2. Navigate to project
cd /path/to/goexplorer  # Update with actual path

# 3. Make script executable
chmod +x deploy_strict_discipline.sh

# 4. Run deployment script
bash deploy_strict_discipline.sh

# Script will:
# - Pull latest code
# - Apply migrations
# - FLUSH database (⚠️ deletes all data)
# - Seed fresh data (seed_all)
# - Validate parity (validate_seed)
# - Run E2E tests (verify_e2e.py)
# - Collect static files
# - Restart services
```

**Expected Output:**
```
✓ Code updated
✓ Migrations applied
✓ Database flushed
✓ Data seeded
✓ Seed parity validated
✓ E2E verification passed (33/33 tests)
✓ Static files collected
✓ Services restarted
✓ DEPLOYMENT COMPLETE
```

---

## OPTION 2: Manual Step-by-Step

```bash
# 1. SSH to server
ssh deployer@goexplorer-dev.cloud

# 2. Navigate to project directory
cd /path/to/goexplorer

# 3. Activate virtual environment
source venv/bin/activate

# 4. Pull latest code
git pull origin main

# 5. Install dependencies
pip install -r requirements.txt

# 6. Apply migrations
python manage.py migrate

# 7. FLUSH database (⚠️ DELETES ALL DATA)
python manage.py flush --noinput

# 8. Seed fresh data
python manage.py seed_all --env=local

# 9. MANDATORY: Validate seed parity
python manage.py validate_seed
# MUST show: [OK] SEED PARITY VERIFIED!
# If FAIL → STOP and fix locally

# 10. Run E2E verification
python verify_e2e.py
# MUST show: ✅ ALL E2E TESTS PASSED (33/33)
# If any fail → STOP and fix locally

# 11. Collect static files
python manage.py collectstatic --noinput

# 12. Restart services
sudo systemctl restart gunicorn
sudo systemctl restart nginx

# 13. Start background worker (optional)
python manage.py rqworker default &
```

---

## POST-DEPLOYMENT VERIFICATION

### 1. Check Admin Panel
```
URL: https://goexplorer-dev.cloud/admin/
Login: Your superuser credentials

Verify counts:
- Hotels: 16 ✓
- Packages: 5 ✓
- Buses: 2 ✓
- Bus Operators: 2 ✓
- Wallets: 1 ✓
```

### 2. Test Booking Flow
```
1. Login as: testuser / testpass123
2. Create bus booking
   - Select route: Bangalore to Chennai
   - Select seat (avoid ladies seats if male)
   - Fill passenger details
   - Click "Book Now"
3. VERIFY: Booking shows RESERVED status ✓
4. Complete payment with wallet
5. VERIFY: Booking shows CONFIRMED status ✓
6. VERIFY: Wallet balance decreased ✓
```

### 3. Test Bulk Admin Operations
```
1. Go to Admin → Buses → Bus
2. Select all buses (2 total)
3. Actions dropdown → "Enable WiFi"
4. Click "Go"
5. VERIFY: Success message "2 buses updated" ✓
6. VERIFY: All buses show has_wifi=True ✓
```

### 4. Monitor Logs
```bash
# Gunicorn errors
tail -f /var/log/gunicorn/error.log

# Nginx errors
tail -f /var/log/nginx/error.log

# Django logs (if configured)
tail -f /var/log/goexplorer/django.log
```

---

## ACCEPTANCE CRITERIA

**ALL must be TRUE before declaring deployment successful:**

- [ ] `validate_seed` passed on server
- [ ] `verify_e2e.py` passed 33/33 tests on server
- [ ] Admin login works
- [ ] 16 hotels visible in admin
- [ ] 5 packages visible in admin
- [ ] 2 buses visible in admin
- [ ] testuser wallet shows ₹5000 balance
- [ ] New booking creates in RESERVED state
- [ ] Payment transitions booking to CONFIRMED
- [ ] Wallet balance updates after payment
- [ ] Bulk admin operations work (enable WiFi on buses)
- [ ] No 502 errors when browsing site
- [ ] No database errors in logs

---

## ROLLBACK PROCEDURE (If Needed)

```bash
# 1. Revert to previous commit
git log --oneline -10
git reset --hard <previous_commit_hash>

# 2. Reseed database
python manage.py flush --noinput
python manage.py seed_all --env=local

# 3. Restart services
sudo systemctl restart gunicorn
sudo systemctl restart nginx

# 4. Fix issues locally, then redeploy
```

---

## COMMON ISSUES & SOLUTIONS

### Issue: validate_seed fails
**Solution:**
```bash
# Check what's different
python manage.py shell
from hotels.models import Hotel
from buses.models import Bus
print(f"Hotels: {Hotel.objects.count()}")
print(f"Buses: {Bus.objects.count()}")

# If counts wrong, reseed:
python manage.py flush --noinput
python manage.py seed_all --env=local
python manage.py validate_seed
```

### Issue: E2E tests fail
**Solution:**
```bash
# Run with verbose output
python verify_e2e.py

# Check specific section that failed
# Fix locally, commit, push, redeploy
```

### Issue: Services won't restart
**Solution:**
```bash
# Check service status
sudo systemctl status gunicorn
sudo systemctl status nginx

# Check for errors
journalctl -u gunicorn -n 50
journalctl -u nginx -n 50

# Force restart
sudo systemctl stop gunicorn
sudo systemctl start gunicorn
```

### Issue: 502 Bad Gateway
**Solution:**
```bash
# Check Gunicorn is running
ps aux | grep gunicorn

# Check Nginx config
sudo nginx -t

# Restart both services
sudo systemctl restart gunicorn nginx
```

---

## SUPPORT

**Documentation:**
- [DEPLOYMENT_READINESS.md](DEPLOYMENT_READINESS.md) - Complete deployment guide
- [PHASE_1_TESTING.md](PHASE_1_TESTING.md) - 8 comprehensive test cases
- [PHASE_1_COMPLETE.md](PHASE_1_COMPLETE.md) - Feature delivery summary

**Troubleshooting:**
- Check logs: `/var/log/gunicorn/error.log`
- Run diagnostics: `python manage.py check --deploy`
- Verify migrations: `python manage.py showmigrations`
- Test database: `python manage.py dbshell`

---

## DATA PARITY CONFIRMATION

After deployment, verify local vs server data is IDENTICAL:

| Component | Local | Server | Status |
|-----------|-------|--------|--------|
| Hotels | 16 | ? | ⏳ |
| Packages | 5 | ? | ⏳ |
| Buses | 2 | ? | ⏳ |
| Operators | 2 | ? | ⏳ |
| Wallets | 1 | ? | ⏳ |
| testuser balance | ₹5000 | ? | ⏳ |
| Active cashback | ₹1000 | ? | ⏳ |

**Fill in "?" with actual server values after deployment.**
**All "Status" must show ✅ before declaring success.**

---

## DEPLOYMENT TIMELINE

1. **SSH to server:** 2 min
2. **Run deployment script:** 5-10 min
3. **Post-deployment verification:** 5 min
4. **Testing booking flow:** 5 min

**Total estimated time: 20-25 minutes**

---

**🚨 REMINDER:** If ANY test fails on server → STOP → Fix locally → Redeploy

**✅ SUCCESS CRITERIA:** All 33 E2E tests pass + all acceptance criteria met
