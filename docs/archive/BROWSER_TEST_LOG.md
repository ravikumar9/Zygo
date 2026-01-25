# 🔴 REAL BROWSER TESTING ON DEV SERVER
# https://goexplorer-dev.cloud

## Testing Status Log

### Issue 1️⃣: MOBILE NUMBER VALIDATION
**Status:** ⏳ TESTING...
- [ ] Mobile field only accepts 10 digits
- [ ] Field rejects 11+ digits
- [ ] Placeholder shows "10-digit"
- [ ] maxlength=10 enforced
- [ ] Helper text visible

### Issue 2️⃣: WALLET ICON & PAGE
**Status:** ⏳ TESTING...
- [ ] Wallet icon visible in navbar after login
- [ ] /payments/wallet/ returns 200 (not 404)
- [ ] Wallet page loads without errors
- [ ] All wallet services accessible

### Issue 3️⃣: CORPORATE BOOKING FEATURE
**Status:** ⏳ TESTING...
- [ ] Corporate section visible on home
- [ ] Corporate icon present
- [ ] No broken URLs / 404s
- [ ] Safe fallback links

### Issue 4️⃣: LOGIN REDIRECTION BUG
**Status:** ⏳ TESTING...
- [ ] After login, user redirected to HOME (not /register)
- [ ] No infinite redirect loop
- [ ] Session flags clear

### Issue 5️⃣: EMAIL VERIFICATION FLOW
**Status:** ⏳ TESTING...
- [ ] After email OTP, Continue button ENABLED
- [ ] Email-verified user can book
- [ ] Mobile verification NOT required
- [ ] Payment proceeds without mobile

### Issue 6️⃣: HOTEL IMAGES
**Status:** ⏳ TESTING...
- [ ] No "Hotel image unavailable" text
- [ ] Images load or show placeholder
- [ ] Fallback working

### Issue 7️⃣: HOTEL DATE LOGIC
**Status:** ⏳ TESTING...
- [ ] Past dates NOT selectable
- [ ] Checkout > checkin enforced
- [ ] Calendar validation working

### Issue 8️⃣: ADMIN ROLLBACK
**Status:** ⏳ TESTING...
- [ ] Admin panel accessible
- [ ] Restore action visible
- [ ] Deleted items recoverable

### Issue 9️⃣: BUS SEAT LAYOUT
**Status:** ⏳ TESTING...
- [ ] Seat layout displays
- [ ] NO "AISLE" text visible
- [ ] Spacing preserved

### Issue 🔟: TEST DATA SEEDING
**Status:** ⏳ TESTING...
- [ ] seed_data_clean.py runs without error
- [ ] Test hotels visible on UI
- [ ] Bus routes seeded
- [ ] Data meaningful for testing

### Issue 1️⃣1️⃣: PAYMENT HOLD TIMER
**Status:** ⏳ TESTING...
- [ ] Timer visible on booking
- [ ] Timer continues on payment page
- [ ] Auto-cancel after expiry confirmed

---

## Screenshots Collected

(Will add as testing progresses)

