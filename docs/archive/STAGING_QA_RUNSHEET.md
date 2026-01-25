# STAGING QA RUN-SHEET (FINAL GATE)
**Date:** January 22, 2026  
**Scope:** Hotels + Bus Bookings  
**Goal:** Prove survivability, correctness, and zero silent failures  
**Rule:** If any single ID fails → ❌ STOP → FIX → RESTART FULL PASS

---

## 0️⃣ PRE-CHECK (5 minutes)

### Environment Setup
- [ ] **Environment:** STAGING
- [ ] **DB:** Latest migrations applied
- [ ] **Browser cache:** Cleared
- [ ] **DevTools:** Open (Console + Network tabs)

### Required Seed Data
- [ ] At least 1 hotel with rooms + meal plans
- [ ] At least 1 hotel with rooms but NO meal plans
- [ ] At least 1 hotel with NO rooms
- [ ] At least 1 hotel with NO images
- [ ] At least 1 bus booking created before snapshot fix

---

## 1️⃣ SURVIVABILITY TESTS (NON-NEGOTIABLE)

### 1.1 Hotel with NO rooms
**URL:** `/hotels/<id-with-no-rooms>/`

**Expected:**
- [ ] Page loads (HTTP 200)
- [ ] Visible message: "No rooms available at this property"
- [ ] ❌ No JS errors
- [ ] ❌ No template crash
- [ ] Booking form disabled or hidden

**Result:** ✅ Pass / ❌ Fail  
**Notes:**

---

### 1.2 Hotel with NO meal plans
**Action:** Select a room

**Expected:**
- [ ] Meal plan dropdown hidden OR shows "Room Only (No Meal Plan)"
- [ ] Booking proceeds without meal_plan_id
- [ ] ❌ No "Select room first" deadlock

**Result:** ✅ Pass / ❌ Fail  
**Notes:**

---

### 1.3 Hotel with NO images
**Expected:**
- [ ] Placeholder image/block visible
- [ ] Layout intact
- [ ] ❌ No broken `<img>` icons

**Result:** ✅ Pass / ❌ Fail  
**Notes:**

---

### 1.4 Hotel with NO cancellation policy
**Expected:**
- [ ] Alert: "Cancellation Policy Not Available"
- [ ] No stack trace
- [ ] No duplicated policy text

**Result:** ✅ Pass / ❌ Fail  
**Notes:**

---

## 2️⃣ HOTEL BOOKING FLOW (CRITICAL PATH)

### 2.1 Invalid date submission
**Action:**
- Check-in = today
- Check-out = today

**Expected:**
- [ ] Network response: **400**
- [ ] JSON body: `{ "error": "Minimum 1 night stay required" }`
- [ ] UI shows error inline
- [ ] ❌ No HTML returned
- [ ] ❌ No redirect

**Result:** ✅ Pass / ❌ Fail  
**Notes:**

---

### 2.2 Valid 1-night booking
**Action:**
- Check-in: Today
- Check-out: Tomorrow
- Select room
- (Optional) Select meal plan
- Click "Book Now"

**Expected:**
- [ ] Network response: **200**
- [ ] JSON: `{ "booking_url": "/bookings/<uuid>/confirm/" }`
- [ ] Browser redirects correctly
- [ ] Confirmation page loads

**Result:** ✅ Pass / ❌ Fail  
**Notes:**

---

### 2.3 Confirmation page validation
**Expected:**
- [ ] Pricing breakdown visible:
  - [ ] Base price
  - [ ] Service fee (≤ ₹500)
  - [ ] GST (18%)
  - [ ] Total
- [ ] Cancellation policy visible ONCE
- [ ] No policy shown again on payment page

**Result:** ✅ Pass / ❌ Fail  
**Notes:**

---

## 3️⃣ BUS BOOKING DATA INTEGRITY

### 3.1 OLD booking (pre-snapshot)
**Action:** Open existing bus booking created before fixes

**Expected:**
- [ ] Operator name visible
- [ ] Bus name visible
- [ ] Route visible
- [ ] Contact phone visible
- [ ] ❌ No empty labels like "Phone: "

**Result:** ✅ Pass / ❌ Fail  
**Notes:**

---

### 3.2 Deleted operator test
**Action:**
- Delete bus operator record (admin)
- Reload booking confirmation

**Expected:**
- [ ] Booking still shows `operator_name` snapshot
- [ ] No FK errors
- [ ] No missing data

**Result:** ✅ Pass / ❌ Fail  
**Notes:**

---

## 4️⃣ BROWSER MATRIX (MANDATORY)

### 4.1 Desktop (Chrome / Edge)
- [ ] No console errors
- [ ] Booking flow works end-to-end

**Result:** ✅ Pass / ❌ Fail  
**Notes:**

---

### 4.2 Mobile (375px width)
- [ ] Room cards stack correctly
- [ ] Booking widget usable
- [ ] Buttons clickable
- [ ] No overflow / hidden text

**Result:** ✅ Pass / ❌ Fail  
**Notes:**

---

### 4.3 Tablet (768px)
- [ ] Two-column layout behaves correctly
- [ ] No broken components

**Result:** ✅ Pass / ❌ Fail  
**Notes:**

---

## 5️⃣ PERFORMANCE & SANITY

### Metrics
- [ ] Page load < 2s
- [ ] **Network tab:** ❌ No N+1 room/meal queries
- [ ] **Console:** ❌ No JS warnings
- [ ] **Logs:** ❌ No silent exceptions

**Result:** ✅ Pass / ❌ Fail  
**Notes:**

---

## 🟥 STOP CONDITIONS (HARD RULES)

**Immediately STOP and FIX if:**
- ❌ Any page returns HTML instead of JSON for AJAX
- ❌ Any ID crashes page render
- ❌ Any booking proceeds with missing snapshot data
- ❌ Any JS error appears in console
- ❌ Any survivability case fails

---

## 🟢 EXIT CRITERIA (ONLY WAY TO PRODUCTION)

**Production Readiness = 100% ONLY if:**
- ✔️ All sections 1 → 5 = PASS
- ✔️ No manual overrides
- ✔️ No "edge case, but acceptable" thinking

**Then and only then:**
- Production deployment approved

---

## 🎯 FINAL ARCHITECT NOTE

**At this stage:**
- ❌ No more refactors
- ❌ No feature adds
- ❌ No "quick fixes"

**Only truth verification.**

---

## EXECUTION LOG

**Tester:**  
**Date Started:**  
**Date Completed:**  
**Overall Result:** ⬜ PASS / ⬜ FAIL  
**Blockers Found:**

---

**Next Action:** Production deployment OR fix blockers and re-run full pass
