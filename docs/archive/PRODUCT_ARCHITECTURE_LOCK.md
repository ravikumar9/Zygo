# 🔒 PRODUCT ARCHITECTURE LOCK (Permanent Decisions)

**Date:** January 23, 2026  
**Status:** PERMANENT — Do not debate these again  

---

## 1️⃣ GUEST BOOKING — ALLOWED (CORE PRODUCT DECISION)

### Decision
✅ Guests **MUST** be able to book WITHOUT creating an account first.

### Mandatory Fields Only
- Name
- Email
- Phone
- Check-in date
- Check-out date
- Room selection

### Backend Rule
- Create `GuestBooking` immediately
- Link user account later if they register
- No forced login to complete booking

### Rationale
- **MMT/Goibibo Standard**: Industry leaders allow guest checkout
- **Conversion Impact**: Removing login friction increases conversions
- **User Agency**: Let users decide when/if to create account

---

## 2️⃣ MEAL PLANS — STATE-DRIVEN VISIBILITY

### Rule
```
NO ROOM SELECTED        → HIDE MEALS SECTION
ROOM SELECTED + NO MEALS → HIDE MEALS SECTION
ROOM SELECTED + MEALS EXIST → SHOW DROPDOWN
```

### Technical Implementation
- Meal plans are **RoomType-driven**, not Hotel-driven
- JS guards ALL null checks (no assumptions about DOM)
- If `meal-plans-data` missing → silently hide, don't error
- If dropdown container missing → silently return, don't crash

### Code Pattern (Defensive)
```javascript
var mealPlanGroup = document.getElementById('meal-plan-group');
if (!mealPlanGroup) return;  // Defensive: don't assume it exists
```

---

## 3️⃣ CONSOLE ERRORS — ZERO TOLERANCE (RELEASE BLOCKER)

### Rule
**Console errors = Hard blocker. No exceptions.**

### Current Fixes Applied

#### Fix 1: ES6 Export Syntax Error
**Problem:** 
```javascript
export const BookingState = {...}  // ❌ Causes "Unexpected token 'export'"
```

**Solution:**
```javascript
window.BookingState = {...}  // ✅ Use window namespace
```

#### Fix 2: Null Reference Guards
**Problem:**
```javascript
document.getElementById('meal-plans').innerHTML = ...  // ❌ Crashes if element doesn't exist
```

**Solution:**
```javascript
var el = document.getElementById('meal-plans');
if (!el) return;  // ✅ Defensive null check
el.innerHTML = ...
```

#### Fix 3: Safe Error Rendering
**Problem:**
```javascript
errorDiv.innerHTML = message  // ❌ XSS risk if message contains HTML
```

**Solution:**
```javascript
var safeMsg = String(message).replace(/</g, '&lt;').replace(/>/g, '&gt;');
errorDiv.innerHTML = safeMsg;  // ✅ HTML-escaped
```

---

## 4️⃣ BOOKING STATE MACHINE — PERMANENT ARCHITECTURE

### State Transitions
```
INITIAL
  ├─ No dates selected
  └─ Button: DISABLED
     
DATES_SELECTED
  ├─ Check-in + Check-out valid
  ├─ Check-out > Check-in
  └─ Button: DISABLED
  
READY
  ├─ Dates valid
  ├─ Room selected
  └─ Button: ENABLED
```

### UI Gating Rule
```
if (state !== READY) {
  hidePriceSummary()
  disableBookButton()
}
```

### Permanent Implementation
- **File**: `static/js/booking_state.js` (window namespace)
- **Trigger**: Date change, room change, page load
- **Guarantee**: Button state always mirrors booking state

---

## 5️⃣ PRICING VISIBILITY — TRUST-FIRST UX

### Rule
**Price appears ONLY when booking state is READY**

### What's Hidden on Load
- ❌ Room base price (e.g., "From ₹5000")
- ❌ Taxes & Fees breakdown
- ❌ Total amount
- ❌ ₹N/A placeholder text

### What's Shown on Load
✅ "Pick dates to see price for this room"  
✅ Hotel description, amenities, policies  
✅ Room images, capacity, specs

---

## 6️⃣ PROPERTY REGISTRATION — INCOMPLETE (KNOWN GAP)

### Current Flow
- [x] Basic info (name, type, location)
- [ ] **MISSING**: Room types (name, capacity, price, images)
- [ ] **MISSING**: Property rules (check-in, check-out, pets, ID)
- [ ] **MISSING**: Admin approval before live

### Correct MMT-Style Flow (To Be Implemented)
```
Step 1: Property basic info
Step 2: Rooms (MANDATORY for each room type)
Step 3: Property rules & policies
Step 4: Submit for approval
Step 5: Admin review & approval
```

### Permanent Rule
Only **APPROVED** property data goes live.

---

## 7️⃣ TEST DATA VS. ADMIN DATA

### Development (OK to use seeds)
- ✅ Seeded test hotels
- ✅ Fixtures for pytest
- ✅ Timestamped data to avoid conflicts

### Production (Seeds are irrelevant)
- ❌ UI MUST NOT depend on seeds
- ✅ UI MUST handle:
  - No rooms available
  - No meal plans
  - Partial/missing data
  - Pending approval status

### Permanent Rule
```
Admin-approved data = ONLY source of truth
Seeds = Dev/test only
```

---

## 8️⃣ DATE PICKER — PAST DATES BLOCKED

### Frontend Rule
```javascript
const today = new Date().toISOString().split('T')[0];
checkInInput.min = today;  // Prevents past date selection
checkOutInput.min = today; // Prevents past date selection
```

### Backend Validation
Always validate on server (frontend is not enough).

---

## 9️⃣ FINAL SANITY CHECK — SINGLE RUN (Permanent Gate)

### Scope
1. Open hotel detail page as **guest user**
2. **Do NOT select** anything
3. Assume **no seeded data**, only admin-approved data

### Pass Criteria (ALL must pass)
- ✅ No price visible
- ✅ No taxes/fees visible
- ✅ No ₹N/A placeholder
- ✅ Book button disabled
- ✅ No console errors
- ✅ No backend errors visible

### Current Status
✅ **PASS** (as of Jan 23, 2026 14:32 UTC)

---

## 🔟 RELEASE CHECKLIST

- [x] No console errors (zero tolerance)
- [x] Guest booking allowed
- [x] Pricing gated by state
- [x] Date picker blocks past dates
- [x] Book button disabled until READY
- [x] Meal plans hidden until room selected
- [ ] Property registration flow complete
- [ ] Admin approval required before live
- [ ] E2E tests passing (22/22)

---

## 📝 Reference Files

| File | Purpose |
|------|---------|
| `static/js/booking_state.js` | State machine (window namespace) |
| `templates/hotels/includes/booking-form.html` | Form with state gating & defensive JS |
| `templates/hotels/includes/pricing-calculator.html` | Pricing (hidden until READY) |
| `templates/hotels/includes/room-card.html` | Room cards (no prices on load) |

---

## 🚀 Next Steps (Priority)

1. **Complete property registration flow** (Step 2-5)
2. **Admin approval system** (properties can't go live without approval)
3. **Run full E2E suite** (`pytest qa_e2e/ -v`)
4. **Deploy to production** (when property registration done)

---

**Locked by:** Product Architecture (Permanent)  
**Status:** ✅ ENFORCED  
**No further changes without explicit override vote**
