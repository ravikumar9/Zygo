# DEV BROWSER TESTING CHECKLIST
## Critical UI Fixes - Browser Verification Required

**DEV Server:** https://goexplorer-dev.cloud

All code changes have been verified locally and committed to git.
**9 commits ahead** of origin/main, ready to push to DEV.

---

## ✅ VERIFIED LOCALLY (Code-Level Tests Pass)

### 1. WALLET PAGE - HTML Rendering ✅
**Status:** FIXED - Template corrected, returns HTML
**Code Changes:**
- Changed `WalletView` from APIView to TemplateView
- Created `templates/payments/wallet.html` with balance & transaction display  
- Fixed broken URL reference: `bookings:list` → `core:home`

**Local Test:** PASS
- HTTP 200 response
- Returns HTML (not JSON/API)
- Shows balance section
- Shows transaction history
- No broken URL references

**DEV Browser Test Required:**
1. Login to https://goexplorer-dev.cloud with verified email user
2. Click wallet icon in navbar
3. Verify page loads (HTTP 200, not 500)
4. Verify balance displays
5. Verify transaction history section visible
6. Take screenshot showing URL bar + page content

---

### 2. HOTEL PLACEHOLDER SVG - No "Unavailable" Text ✅
**Status:** FIXED - Replaced text with professional illustration
**Code Changes:**
- Updated `static/images/hotel_placeholder.svg`
- Removed "Hotel image unavailable" text
- Added building illustration with gradient background

**Local Test:** PASS
- SVG file contains no "unavailable" or "not available" text
- Professional building illustration renders

**DEV Browser Test Required:**
1. Browse to https://goexplorer-dev.cloud/hotels/
2. Look at hotels without images
3. Verify placeholder shows building illustration (not ugly text)
4. Check hotel detail pages
5. Take screenshot of hotel card with placeholder

**Note:** If NO hotels appear, run `seed_data_clean.py` on DEV server first

---

### 3. HOTEL DATE PICKER - Past Dates Blocked ✅
**Status:** FIXED - Added min-date validation like bus booking
**Code Changes:**
- Updated `templates/hotels/hotel_detail.html`
- Updated `templates/hotels/hotel_list.html`
- Added JavaScript to set `min` attribute to today's date

**Local Test:** PASS
- Both templates have min-date validation code
- JavaScript initializes date inputs on page load

**DEV Browser Test Required:**
1. Go to hotel search page
2. Click check-in date picker
3. Verify past dates are grayed out/disabled in calendar
4. Try manually typing past date → should be rejected
5. Behavior should match bus booking date picker
6. Take screenshot of calendar with past dates disabled

---

### 4. BUS SEAT LAYOUT - No "AISLE" Text ✅
**Status:** FIXED - Removed text label from aisle div
**Code Changes:**
- Updated `templates/buses/bus_detail.html` line 475
- Changed `<div class="aisle">AISLE</div>` → `<div class="aisle"></div>`

**Local Test:** PASS
- Empty aisle div exists (maintains spacing)
- No "AISLE" text in template

**DEV Browser Test Required:**
1. Browse to any bus detail page with seat selection
2. Verify seat layout displays correctly
3. Verify NO "AISLE" text appears between seat columns
4. Visual spacing should remain (empty div maintains layout)
5. Take screenshot of seat layout

---

### 5. LOGIN REDIRECT - No Redirect to Register ✅
**Status:** VERIFIED - Existing code correct
**Code Changes:** None needed (issue was in test environment only)

**Local Test:** PASS
- Verified users do NOT redirect to `/users/register`
- Home page loads correctly after login

**DEV Browser Test Required:**
1. Logout from DEV
2. Login with email-verified user account
3. Verify redirect goes to home page (/)
4. Verify URL is NOT `/users/register`
5. Take screenshot of page after login showing URL bar

---

## ⚠️ REQUIRES DECISION (Not Yet Implemented)

### 6. CORPORATE BOOKING
**Current Status:** Partially implemented, unclear state
**Issue:** Link in navbar but unclear if feature is complete/coming soon/should be hidden

**Options:**
A. **Complete Implementation:** Build full corporate dashboard
B. **Coming Soon Placeholder:** Create placeholder page with "Feature launching soon"
C. **Hide Feature:** Remove from navbar until ready

**Recommendation:** Choose option B or C to avoid broken user experience

**Action Required:** Make clear decision, then implement

---

### 7. ADMIN ROLLBACK - Soft Delete & Restore
**Current Status:** Code exists, needs manual UI verification
**Existing Implementation:**
- Booking model has soft delete fields (`deleted_at`)
- BookingAdmin has restore action
- Should work via Django admin UI

**Manual Test Required:**
1. Login to Django admin at https://goexplorer-dev.cloud/admin
2. Find a booking
3. Soft delete it
4. Verify "Restore" action appears in admin actions dropdown
5. Click restore
6. Verify booking is restored (not requiring manual DB edits)
7. Take screenshot of admin UI showing restore action

---

## 🚀 DEPLOYMENT STEPS

### 1. Push Code to DEV
```bash
git push origin main
```

### 2. SSH to DEV Server
```bash
ssh user@goexplorer-dev.cloud
```

### 3. Pull Latest Code
```bash
cd /path/to/project
git pull origin main
```

### 4. Restart Services
```bash
sudo systemctl restart goexplorer
# or
sudo systemctl restart nginx
sudo systemctl restart gunicorn
```

### 5. Seed Test Data (If Needed)
```bash
python manage.py shell
>>> from scripts.seed_data_clean import seed_all
>>> seed_all()
```

---

## 📸 PROOF REQUIRED

For each verified feature, provide:
1. **Screenshot** with URL bar visible
2. **Description** of what was tested
3. **Result** (Pass/Fail with explanation)

### Example Format:
```
Feature: Wallet Page
URL: https://goexplorer-dev.cloud/payments/wallet/
Test: Logged in user clicks wallet icon
Result: PASS
- Page loads (HTTP 200)
- Balance displays: ₹0
- Transaction history section visible
- No 500 error
Screenshot: [attach image]
```

---

## ✅ ACCEPTANCE CRITERIA

Task is COMPLETE when:
- [ ] All code deployed to DEV
- [ ] All 5 fixed features verified in DEV browser (with screenshots)
- [ ] Corporate booking decision made and implemented
- [ ] Admin rollback verified in Django admin UI
- [ ] Screenshots provided as proof
- [ ] No critical errors in DEV browser console
- [ ] All features work for real users (not just test scripts)

---

## 📋 STATUS SUMMARY

**Code Changes:** Complete (9 commits ready to push)
**Local Verification:** All tests PASS
**DEV Deployment:** Pending
**Browser Verification:** Pending (requires DEV access)
**Final Sign-off:** Pending browser proof

**Blocker:** Need access to DEV server for browser testing and screenshots
