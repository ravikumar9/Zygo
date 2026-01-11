# PHASE 3.1 - SERVER VALIDATION CHECKLIST

**Status:** 🔄 PENDING SERVER TESTING  
**Code Pushed:** ✅ YES (commit: aeee8ba)  
**Date:** January 11, 2026

---

## Pre-Deployment Steps (On Server)

### 1. Pull Latest Code
```bash
cd /path/to/goexplorer
git pull origin main
```

### 2. Activate Virtual Environment
```bash
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies (if any new)
```bash
pip install -r requirements.txt
```

### 4. Run Migrations
```bash
python manage.py migrate
```

### 5. Collect Static Files
```bash
python manage.py collectstatic --noinput
```

### 6. Restart Application
```bash
# For Gunicorn
sudo systemctl restart gunicorn

# OR for development server
python manage.py runserver 0.0.0.0:8000
```

---

## Server Validation Tests

### ✅ TEST 1: Admin Login & Pages
**URL:** `https://your-server.com/admin/`

**Steps:**
1. Navigate to admin login
2. Login with admin credentials
3. Verify admin dashboard loads
4. Check Users admin page
5. Check Hotels admin page
6. Check Buses admin page
7. Check Reviews admin pages

**Expected:**
- ✓ All pages load without errors
- ✓ No FieldError or 500 errors
- ✓ Admin interface functional

**Screenshot Required:** Yes (admin dashboard)

---

### ✅ TEST 2: User Registration (Email + Mobile OTP)
**URL:** `https://your-server.com/users/register/`

**Steps:**
1. Navigate to registration page
2. Fill form:
   - Email: test-phase31@example.com
   - First Name: Phase
   - Last Name: Three
   - Phone: 9876543210 (10-digit numeric)
   - Password: TestPass123!
   - Confirm Password: TestPass123!
3. Click "Register" button
4. **Verify:** Redirected to OTP verification page
5. **Check:** Email OTP section visible with "Send OTP" button
6. **Check:** Mobile OTP section visible with "Send OTP" button
7. **Check:** Status cards show "Pending" for both
8. Click "Send Email OTP"
9. **Verify:** OTP sent (check email or console logs)
10. Enter email OTP code
11. Click "Verify Email OTP"
12. **Verify:** Email status card changes to "Verified" (green)
13. Click "Send Mobile OTP"
14. **Verify:** OTP sent (check SMS or console logs)
15. Enter mobile OTP code
16. Click "Verify Mobile OTP"
17. **Verify:** Mobile status card changes to "Verified" (green)
18. **Verify:** "Complete Registration" button becomes enabled
19. Click "Complete Registration"
20. **Verify:** Redirected to success page or login page

**Expected:**
- ✓ Registration form accepts data
- ✓ Redirects to OTP verification page
- ✓ Email OTP can be sent and verified
- ✓ Mobile OTP can be sent and verified
- ✓ Status cards update correctly
- ✓ "Complete Registration" button enables after both verified

**Screenshots Required:**
1. Registration form filled
2. OTP verification page (both pending)
3. Email OTP verified (status card green)
4. Mobile OTP verified (both status cards green)
5. Complete registration button enabled

---

### ✅ TEST 3: Login After Verification
**URL:** `https://your-server.com/users/login/`

**Steps:**
1. Navigate to login page
2. Enter credentials:
   - Email: test-phase31@example.com
   - Password: TestPass123!
3. Click "Login" button
4. **Verify:** Redirected to dashboard/home page
5. **Check:** User is authenticated (check navbar for logout button)

**Expected:**
- ✓ Login successful
- ✓ Redirected to dashboard
- ✓ User authenticated

**Screenshot Required:** Yes (dashboard after login)

---

### ✅ TEST 4: Bus Seat Layout (Single Deck)
**URL:** `https://your-server.com/buses/` → Select a single-deck bus (AC Seater, Seater)

**Steps:**
1. Navigate to bus list
2. Find a single-deck bus (AC Seater, Non-AC Seater)
3. Click "View Details" or "Book Now"
4. Scroll to seat layout section
5. **Verify:** NO "Lower Deck" or "Upper Deck" labels visible
6. **Check:** Seat grid displays correctly (2x2 layout)
7. **Check:** Seats show correct availability (green/gray)

**Expected:**
- ✓ Single-deck bus has NO deck labels
- ✓ Seat layout displays correctly
- ✓ Seats are clickable and show availability

**Screenshot Required:** Yes (single-deck bus seat layout without deck labels)

---

### ✅ TEST 5: Bus Seat Layout (Multi-Deck)
**URL:** `https://your-server.com/buses/` → Select a multi-deck bus (Volvo, Luxury)

**Steps:**
1. Navigate to bus list
2. Find a multi-deck bus (Volvo, Luxury sleeper)
3. Click "View Details" or "Book Now"
4. Scroll to seat layout section
5. **Verify:** "Lower Deck" label visible above lower deck seats
6. **Verify:** "Upper Deck" label visible above upper deck seats
7. **Check:** Seat grids display correctly for both decks

**Expected:**
- ✓ Multi-deck bus shows deck labels
- ✓ "Lower Deck" label present
- ✓ "Upper Deck" label present
- ✓ Both deck seat layouts display correctly

**Screenshot Required:** Yes (multi-deck bus with deck labels)

---

### ✅ TEST 6: Hotel Image Rendering
**URL:** `https://your-server.com/hotels/` → Select any hotel

**Steps:**
1. Navigate to hotel list
2. Click on a hotel with images
3. **Verify:** Primary image displays first
4. **Check:** Image carousel/gallery works
5. **Check:** No "image unavailable" messages
6. **Check:** Images load without 404 errors

**Expected:**
- ✓ Primary image displays correctly
- ✓ All hotel images load
- ✓ No broken image links
- ✓ No "image unavailable" messages

**Screenshot Required:** Yes (hotel detail with images)

---

### ✅ TEST 7: Favicon Display
**URL:** `https://your-server.com/` (any page)

**Steps:**
1. Navigate to any page on the site
2. Check browser tab
3. **Verify:** Bus icon favicon displays
4. Open browser console (F12)
5. Check Network tab for favicon.svg
6. **Verify:** No 404 error for favicon.svg

**Expected:**
- ✓ Favicon displays in browser tab
- ✓ No 404 error for favicon.svg
- ✓ Favicon loads from static/images/favicon.svg

**Screenshot Required:** Yes (browser tab showing favicon)

---

## Regression Testing

### ✅ TEST 8: Existing Features Still Work
**Areas to Verify:**

1. **Bus Booking Flow**
   - Search buses
   - Select seats
   - Enter passenger details
   - Proceed to payment
   - **Expected:** No errors, flow unchanged

2. **Hotel Booking Flow**
   - Search hotels
   - View hotel details
   - Book room
   - **Expected:** No errors, flow unchanged

3. **Package Booking Flow**
   - View packages
   - Book package
   - **Expected:** No errors, flow unchanged

4. **Payment Flow**
   - Razorpay integration
   - Payment confirmation
   - **Expected:** No errors, flow unchanged

5. **Admin Reviews**
   - Moderate hotel reviews
   - Moderate bus reviews
   - Approve/reject reviews
   - **Expected:** No errors, bulk actions work

**Screenshot Required:** Optional (if any issues found)

---

## Error Checking

### Check Server Logs
```bash
# For Gunicorn
sudo journalctl -u gunicorn -f

# OR check error logs
tail -f /var/log/goexplorer/error.log
```

**Look for:**
- ✓ No 500 Internal Server Errors
- ✓ No FieldError exceptions
- ✓ No migration warnings
- ✓ No static file 404s

---

## Performance Check

### Page Load Times
- Homepage: < 2 seconds
- Bus list: < 2 seconds
- Hotel list: < 2 seconds
- Admin pages: < 3 seconds
- OTP verification page: < 1 second

**Expected:** No significant performance degradation from Phase 3.1 changes

---

## Screenshot Checklist

**Required Screenshots (minimum 7):**

1. ✓ Admin dashboard (after login)
2. ✓ Registration form (filled)
3. ✓ OTP verification page (both pending)
4. ✓ OTP verification page (email verified)
5. ✓ OTP verification page (both verified, complete button enabled)
6. ✓ Single-deck bus seat layout (no deck labels)
7. ✓ Multi-deck bus seat layout (with deck labels)
8. ✓ Hotel detail page (with images)
9. ✓ Browser tab (showing favicon)

**Optional Screenshots:**
- Dashboard after login
- Bus booking flow
- Payment confirmation
- Admin reviews page

---

## Validation Summary Template

```
PHASE 3.1 SERVER VALIDATION REPORT
Date: [Date]
Server: [Server URL]
Tester: [Your Name]

TEST RESULTS:
[ ] TEST 1: Admin Login & Pages - PASS/FAIL
[ ] TEST 2: User Registration (Dual OTP) - PASS/FAIL
[ ] TEST 3: Login After Verification - PASS/FAIL
[ ] TEST 4: Bus Seat Layout (Single Deck) - PASS/FAIL
[ ] TEST 5: Bus Seat Layout (Multi-Deck) - PASS/FAIL
[ ] TEST 6: Hotel Image Rendering - PASS/FAIL
[ ] TEST 7: Favicon Display - PASS/FAIL
[ ] TEST 8: Regression Testing - PASS/FAIL

ISSUES FOUND:
[List any issues]

SCREENSHOTS:
[Attach all screenshots]

OVERALL STATUS: APPROVED / NEEDS FIXES
```

---

## Next Steps After Validation

### If All Tests Pass ✅
1. Mark Phase 3.1 as "Deployed & Validated"
2. Share screenshots with stakeholders
3. Review Phase 3.2 proposal
4. Approve/modify Phase 3.2 scope
5. Begin Phase 3.2 implementation

### If Issues Found ❌
1. Document issues with screenshots
2. Create bug fix branch
3. Fix issues locally
4. Test fixes
5. Re-deploy and re-validate

---

**Status:** 🔄 AWAITING SERVER VALIDATION  
**Next:** Share validation screenshots and approve Phase 3.2
