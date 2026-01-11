# SERVER BUGFIX VERIFICATION CHECKLIST

**Purpose:** Verify all 8 critical bugs are fixed on server
**Date:** January 11, 2026
**Phase:** Post Phase 3.1 Bug Fixes

---

## 📋 PRE-DEPLOYMENT CHECKLIST

Before pushing to server, verify locally:

- [ ] `python manage.py test` - All tests pass
- [ ] `python manage.py migrate` - No new migrations
- [ ] `python manage.py send_test_email` - Command works
- [ ] Login without OTP - Blocked with redirect to verification
- [ ] Login with OTP - Successful
- [ ] Admin panel - No 500 errors
- [ ] Logout - Session cleared

---

## 🚀 DEPLOYMENT STEPS

### Step 1: Push Code to Server
```bash
git add -A
git commit -m "BUGFIX: Critical server validation fixes (8 bugs)"
git push origin main
```

### Step 2: Pull on Server
```bash
ssh user@server
cd /path/to/Go_explorer_clear
git pull origin main
```

### Step 3: Configure Environment (.env)
```env
# Add these to .env file
EMAIL_SMTP_ENABLED=True
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=alerts.goexplorer@gmail.com
EMAIL_HOST_PASSWORD=<app-password-here>
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=alerts.goexplorer@gmail.com
```

### Step 4: Migration Check
```bash
python manage.py migrate
# Expected: "No migrations to apply" ✓
```

### Step 5: Collect Static
```bash
python manage.py collectstatic --noinput
```

### Step 6: Restart Application
```bash
sudo systemctl restart gunicorn
# OR
sudo systemctl restart apache2
# OR
kill existing python process and restart runserver
```

---

## ✅ VERIFICATION TESTS (Server)

### TEST 1: Email Configuration ✉️

**Steps:**
1. SSH to server
2. Run: `python manage.py send_test_email --to your@email.com`

**Expected Output:**
```
Email Configuration Check
------------------------------------------------------------
Backend: django.core.mail.backends.smtp.EmailBackend
From: alerts.goexplorer@gmail.com
To: your@email.com
SMTP Host: smtp.gmail.com
SMTP Port: 587
SMTP User: alerts.goexplorer@gmail.com
SMTP TLS: True
------------------------------------------------------------

Sending test email...

✓ Test email sent successfully to your@email.com
Check your inbox (and spam folder)
```

**Screenshot Required:**
- [ ] Terminal output showing success
- [ ] Email inbox showing received test email

**Pass Criteria:**
- ✅ Command runs without errors
- ✅ Email received in inbox (or spam)
- ✅ Email subject: "GoExplorer Test Email - Configuration Check"

---

### TEST 2: OTP Enforcement (CRITICAL) 🔒

**Steps:**
1. Create new user: `testuser@example.com` / `Test@1234`
2. Complete registration (DO NOT verify OTP yet)
3. Try to login with email + password

**Expected Behavior:**
- ❌ Login BLOCKED
- ↗️ Redirected to `/users/verify-registration-otp/`
- 📧 Message: "Please verify your email and mobile number before logging in"

**Then:**
4. Verify email OTP
5. Verify mobile OTP
6. Try login again

**Expected Behavior:**
- ✅ Login SUCCESS
- ↗️ Redirected to homepage
- ✅ Message: "Login successful!"

**Screenshot Required:**
- [ ] Login blocked screen with error message
- [ ] OTP verification page
- [ ] Successful login after OTP

**Pass Criteria:**
- ✅ Cannot login without email OTP verification
- ✅ Cannot login without mobile OTP verification
- ✅ Can login after BOTH verifications

---

### TEST 3: Admin Panel - Hotel Bookings 🏨

**Steps:**
1. Login to admin: `/admin/`
2. Navigate to: **Bookings → Hotel bookings**
3. Click on any hotel booking

**Expected Behavior:**
- ✅ Page loads without 500 error
- ✅ Hotel name displays correctly
- ✅ Room count shows (not empty/None)
- ✅ No "object has no attribute 'hotel'" error

**Screenshot Required:**
- [ ] Hotel booking list page
- [ ] Hotel booking detail page showing hotel name

**Pass Criteria:**
- ✅ No 500 errors
- ✅ Hotel name visible
- ✅ All fields render correctly

---

### TEST 4: Admin Panel - Reviews 📝

**Steps:**
1. Admin panel → **Reviews → Hotel reviews**
2. Click "Add hotel review"

**Expected Behavior:**
- ✅ Page loads
- ✅ Booking field visible (optional reference)
- ✅ Hotel dropdown populated
- ✅ No crashes

**Then:**
3. Go to **Reviews → Hotel reviews** list
4. Check entity name column

**Expected Behavior:**
- ✅ Hotel names display (not "—" or errors)

**Screenshot Required:**
- [ ] Review list showing hotel names
- [ ] Add review page

**Pass Criteria:**
- ✅ No admin crashes
- ✅ Entity names render correctly
- ✅ Can add/edit reviews

---

### TEST 5: Hotel Images 🖼️

**Steps:**
1. Visit homepage: `/`
2. Scroll to "Featured Hotels" section
3. Check hotel cards

**Expected Behavior:**
- ✅ Hotel images load (not "image unavailable" text)
- ✅ Either real images OR placeholder SVG
- ✅ No broken image icons

**Then:**
4. Click "View Details" on any hotel
5. Check hotel detail page

**Expected Behavior:**
- ✅ Main hotel image displays
- ✅ No "unavailable" text in image area

**Screenshot Required:**
- [ ] Homepage with hotel cards showing images
- [ ] Hotel detail page with main image

**Pass Criteria:**
- ✅ Images load correctly
- ✅ No "image unavailable" text visible
- ✅ Placeholder SVG shows if no image

---

### TEST 6: Password Reset Email 🔑

**Steps:**
1. Go to login page: `/users/login/`
2. Click "Forgot Password?"
3. Enter email: `testuser@example.com`
4. Submit form

**Expected Behavior:**
- ✅ Success message: "Password reset email sent"
- ✅ Email received in inbox

**Then:**
5. Check email inbox
6. Click password reset link
7. Set new password

**Expected Behavior:**
- ✅ Reset link works
- ✅ Can set new password
- ✅ Can login with new password

**Screenshot Required:**
- [ ] Password reset success page
- [ ] Email inbox showing reset email
- [ ] Password reset confirmation page

**Pass Criteria:**
- ✅ Email sent successfully
- ✅ Reset link works
- ✅ Can change password

---

### TEST 7: Session Isolation (Logout → Register) 🔄

**Steps:**
1. Login as existing user
2. Click "Logout"
3. Check homepage

**Expected Behavior:**
- ✅ Message: "Logged out successfully!"
- ✅ No other messages (no "Welcome back...")

**Then:**
4. Click "Register"
5. Complete registration
6. Verify OTP
7. Login

**Expected Behavior:**
- ✅ No message contamination
- ✅ Clean registration flow
- ✅ No "Welcome back" on booking pages

**Screenshot Required:**
- [ ] Logout success message
- [ ] Clean registration page
- [ ] Clean booking page (no auth messages)

**Pass Criteria:**
- ✅ Logout clears session
- ✅ No cross-flow messages
- ✅ Auth and booking isolated

---

### TEST 8: Aligned Seed Data 🌱

**Steps:**
1. SSH to server
2. Run: `python manage.py seed_bugfix_data --users 5 --bookings 10`

**Expected Output:**
```
Bug-Fix Data Seeding
============================================================

[1/4] Creating 5 verified users...
  ✓ Created 5 verified users

[2/4] Fixing hotel images...
  ✓ Fixed X hotel image assignments

[3/4] Creating 10 bookings...
  ✓ Created 10 bookings

[4/4] Creating aligned reviews...
  ✓ Created X booking-linked reviews

✓ Bug-fix seeding complete!
  Users created: 5 (all OTP verified)
  Bookings created: 10
  Reviews aligned with bookings
  Hotels with primary images verified
```

**Then:**
3. Admin panel → **Reviews → Hotel reviews**
4. Check "Booking ID" and "Verified Booking" columns

**Expected Behavior:**
- ✅ Reviews have booking_id set
- ✅ "Verified Booking" badge shows ✓
- ✅ Reviews linked to real bookings

**Screenshot Required:**
- [ ] Seed command output
- [ ] Admin reviews showing verified bookings

**Pass Criteria:**
- ✅ Seed data creates verified users
- ✅ Reviews linked to bookings
- ✅ All data aligned correctly

---

## 📊 VERIFICATION SUMMARY

| Test # | Feature | Status | Screenshot |
|--------|---------|--------|------------|
| 1 | Email Configuration | ⏳ | ⏳ |
| 2 | OTP Enforcement | ⏳ | ⏳ |
| 3 | Admin - Hotel Bookings | ⏳ | ⏳ |
| 4 | Admin - Reviews | ⏳ | ⏳ |
| 5 | Hotel Images | ⏳ | ⏳ |
| 6 | Password Reset Email | ⏳ | ⏳ |
| 7 | Session Isolation | ⏳ | ⏳ |
| 8 | Aligned Seed Data | ⏳ | ⏳ |

**Legend:**
- ⏳ = Pending
- ✅ = Pass
- ❌ = Fail

---

## 📸 REQUIRED SCREENSHOTS

Minimum screenshots to capture:

1. **Email Test Success** - Terminal + inbox
2. **OTP Enforcement** - Login blocked + verification page
3. **Admin Panel** - Hotel bookings page (no errors)
4. **Review Admin** - List showing verified bookings
5. **Hotel Images** - Homepage cards + detail page
6. **Password Reset** - Email received + reset page
7. **Session Cleanup** - Logout success
8. **Seed Data** - Command output + admin reviews

**Total:** 8 screenshots minimum

---

## ✅ ACCEPTANCE CRITERIA

**Phase is acceptable ONLY IF:**

- ✅ All 8 tests PASS
- ✅ No 500 errors in admin
- ✅ OTP enforcement works (cannot bypass)
- ✅ Email configuration verified (test email sent)
- ✅ Hotel images load correctly
- ✅ Reviews tied to real bookings
- ✅ Session isolation working
- ✅ Screenshots provided for all tests

**If ANY test fails → Phase is REJECTED**

---

## 🚨 ROLLBACK PLAN

If critical bugs found:

```bash
# 1. Revert to previous commit
git log --oneline  # Find previous commit hash
git reset --hard <previous-commit-hash>

# 2. Force push (if needed)
git push origin main --force

# 3. Restart server
sudo systemctl restart gunicorn
```

---

## 📞 SUPPORT

**Issues Found?**

1. Check `BUGFIX_CHANGELOG.md` for detailed fix explanations
2. Review `.env` configuration (especially email)
3. Check logs: `tail -f /path/to/logs/error.log`
4. Verify migrations: `python manage.py showmigrations`

**Critical Errors:**

- Admin 500: Check `bookings/admin.py` changes applied
- OTP bypass: Check `users/views.py` login_view() updated
- Email fail: Check `.env` SMTP settings

---

**Verification Date:** _________________
**Verified By:** _________________
**Status:** ⏳ PENDING / ✅ PASS / ❌ FAIL
