# ✅ PRODUCTION DEPLOYMENT CHECKLIST - GoExplorer

## Pre-Deployment (Local Testing)

### Phase 1: Code Verification
- [ ] All files modified (check git status)
- [ ] No syntax errors: `python manage.py check`
- [ ] All imports working: `python manage.py shell` → no ImportError
- [ ] Templates load: `python manage.py shell` → render templates
- [ ] Run tests: `python manage.py test`

### Phase 2: Local Database Reset
```bash
# Clean slate
rm db.sqlite3
python manage.py migrate
python manage.py create_e2e_test_data --clean  # Creates fresh data
```

### Phase 3: Manual Local Testing

#### Login & Authentication (5 min)
- [ ] `/users/login/` loads
- [ ] Invalid creds → RED fields
- [ ] Valid creds → Home page
- [ ] `/users/password-reset/` works
- [ ] `/users/logout/` works (GET)
- [ ] After logout → not authenticated

#### Hotel Booking (5 min)
- [ ] `/hotels/search/` loads
- [ ] URL params work: `?checkin=2026-01-15&checkout=2026-01-17`
- [ ] Dates populate form
- [ ] Submit booking
- [ ] Confirmation page shows real data

#### Bus Booking (5 min)
- [ ] `/buses/list/` loads
- [ ] Search with all filters
- [ ] Empty search → "No buses found" message
- [ ] Select bus → seat layout displays
- [ ] Realistic 3+2 layout OR upper/lower deck
- [ ] Select boarding + dropping (required)
- [ ] Submit booking
- [ ] Confirmation shows no placeholder

#### User Profile (2 min)
- [ ] Login → navbar shows profile link
- [ ] Click profile → HTML page loads
- [ ] Personal info displays
- [ ] Booking history shows
- [ ] Can navigate back

### Phase 4: Run Verification Script
```bash
python verify_production.py
```
Expected: All tests PASS ✓

---

## Deployment Steps

### Step 1: Code Commit & Push
```bash
cd ~/Go_explorer_clear
git add -A
git commit -m "Production fixes: Auth, Hotel dates, Bus filters, Seat layouts, Confirmation"
git push origin main
```

### Step 2: Server Pre-Deployment
```bash
ssh user@server
cd /app/Go_explorer_clear  # Adjust path
```

### Step 3: One-Command Deploy
```bash
git pull origin main && \
source venv/bin/activate && \
pip install -r requirements.txt && \
python manage.py migrate && \
python manage.py create_e2e_test_data && \
python manage.py collectstatic --noinput && \
sudo systemctl restart gunicorn && \
sudo systemctl reload nginx
```

### Step 4: Verify Deployment
```bash
# Check services
sudo systemctl status gunicorn
sudo systemctl status nginx

# Check logs
sudo tail -f /var/log/gunicorn/error.log
sudo tail -f /var/log/nginx/error.log

# Test endpoints
curl http://localhost/users/login/
curl http://localhost/buses/list/
curl http://localhost/admin/
```

---

## Post-Deployment (Production Testing)

### Smoke Tests (10 min)
- [ ] Site loads: `http://yourdomain.com`
- [ ] No 500 errors in error logs
- [ ] Static files load (CSS/JS)
- [ ] Login page works
- [ ] Password reset page works
- [ ] Admin panel accessible

### Functional Tests (15 min)

#### 1. Complete E2E Flow
```
1. Logout any existing session
2. Visit http://yourdomain.com/users/login/
3. Try wrong password → Fields turn RED ✓
4. Login with test@example.com
5. Visit http://yourdomain.com/buses/list/
6. Search: Bangalore → Hyderabad, Tomorrow
7. Select bus → Seat layout shows
8. Pick seats + boarding + dropping
9. Submit → Confirmation page
10. NO placeholder text! ✓
11. Click "My Profile" → Shows bookings
12. Logout → Works
```

#### 2. Hotel Flow
- [ ] Visit hotel search
- [ ] Add URL params for dates
- [ ] Book hotel
- [ ] Confirmation shows dates

#### 3. Error Handling
- [ ] Try invalid email login → Error message
- [ ] Try empty search → "No buses found"
- [ ] Try booking without seats → Error
- [ ] Try booking without boarding/dropping → Error

### Database Integrity Checks
```bash
python manage.py shell << EOF
from hotels.models import City
from buses.models import Bus, BusRoute, BoardingPoint, DroppingPoint, SeatLayout, BusSchedule

print("Cities:", City.objects.count())
print("Buses:", Bus.objects.count())
print("Routes:", BusRoute.objects.count())
print("Boarding:", BoardingPoint.objects.count())
print("Dropping:", DroppingPoint.objects.count())
print("Seats:", SeatLayout.objects.count())
print("Schedules:", BusSchedule.objects.count())

# Check no route is missing points
routes_with_no_boarding = BusRoute.objects.filter(boarding_points__isnull=True).count()
routes_with_no_dropping = BusRoute.objects.filter(dropping_points__isnull=True).count()
print(f"Routes without boarding: {routes_with_no_boarding}")
print(f"Routes without dropping: {routes_with_no_dropping}")
EOF
```

### Performance Checks
- [ ] Page load < 2 seconds
- [ ] No database query timeouts
- [ ] API responses < 500ms
- [ ] No memory leaks

### Security Spot Checks
- [ ] CSRF token in forms ✓
- [ ] Password fields are masked ✓
- [ ] No credentials in response headers ✓
- [ ] HTTPS working (if enabled)

---

## Rollback Plan (If Issues Found)

### If Something Breaks
```bash
# Check recent logs
sudo tail -50 /var/log/gunicorn/error.log
sudo tail -50 /var/log/nginx/error.log

# Restart services
sudo systemctl restart gunicorn
sudo systemctl reload nginx

# If still broken, rollback
git revert HEAD
git push origin main

# Then redeploy previous version
cd /app/Go_explorer_clear
git pull origin main
source venv/bin/activate
python manage.py migrate
sudo systemctl restart gunicorn
```

---

## Monitoring (Post-Deployment)

### Daily Checks (Automated)
- [ ] Gunicorn process running
- [ ] Nginx responding
- [ ] No 500 errors in logs
- [ ] Database connection working

### Weekly Checks
- [ ] All critical flows still working
- [ ] No unhandled exceptions
- [ ] Performance metrics stable
- [ ] No security warnings

### Red Flags (Alert If Seen)
- ⚠️ Any "placeholder" text on confirmation page
- ⚠️ Login redirects to 404
- ⚠️ Booking without boarding/dropping allowed
- ⚠️ Database errors in logs
- ⚠️ Gunicorn crashes

---

## Critical URLs to Test

### Authentication
```
GET  /users/login/               → Login form
POST /users/login/               → Process login
GET  /users/login/?next=/hotels/ → Preserve next
GET  /users/password-reset/      → Password reset form
GET  /users/logout/              → Logout (should work!)
GET  /users/profile/             → User profile (after login)
```

### Hotels
```
GET /hotels/search/                                    → Hotel search
GET /hotels/<id>/?checkin=2026-01-15&checkout=2026-01-17 → Hotel detail with dates
```

### Buses
```
GET /buses/list/                                               → Bus search
GET /buses/list/?source_city=1&destination_city=2             → With filters
GET /buses/list/?source_city=1&destination_city=2&date=tomorrow → With date filter
GET /buses/<id>/detail/                                        → Bus detail + seats
```

### Bookings
```
GET  /bookings/<uuid>/confirm/  → Booking confirmation (should show REAL data)
POST /bookings/<uuid>/confirm/  → Process and redirect to payment
GET  /bookings/<uuid>/payment/  → Payment page
```

### Admin
```
GET /admin/  → Django admin panel
```

---

## Final Sign-Off

| Item | Status | Tested By | Date |
|------|--------|-----------|------|
| Code reviewed | ✅ | - | - |
| Local tests pass | ✅ | - | - |
| Deploy script works | ✅ | - | - |
| Server deployment | [ ] | - | - |
| E2E flow verified | [ ] | - | - |
| Performance checked | [ ] | - | - |
| Security verified | [ ] | - | - |
| Monitoring set up | [ ] | - | - |

---

## Documentation Links

- **Detailed Fixes**: [PRODUCTION_FIXES_COMPLETE.md](PRODUCTION_FIXES_COMPLETE.md)
- **Final Report**: [FINAL_DELIVERY_REPORT.md](FINAL_DELIVERY_REPORT.md)
- **Verification Script**: `python verify_production.py`
- **Deploy Script**: `bash deploy_production.sh`
- **Pre-Deploy Check**: `bash PRE_DEPLOYMENT_CHECK.sh`

---

## Contact & Support

If issues arise:
1. Check error logs
2. Run `verify_production.py` to identify issue
3. Refer to [PRODUCTION_FIXES_COMPLETE.md](PRODUCTION_FIXES_COMPLETE.md)
4. Consider rollback if critical

---

**✅ READY FOR PRODUCTION DEPLOYMENT**

Date: January 9, 2026
Version: 1.0 - Final Release
