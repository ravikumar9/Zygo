# 🔍 UI-API WIRING AUDIT – HARD RESET VERIFICATION

**Date**: January 25, 2026  
**Status**: COMPREHENSIVE AUDIT IN PROGRESS  
**Requirement**: 100% Verified Wiring Before E2E Tests Run

---

## 📋 CRITICAL FLOWS AUDIT

### Flow 1: Hotel Search & Browse

| URL Path | Django View | Template | APIs Called | Permissions | Status |
|----------|------------|----------|------------|------------|--------|
| `/hotels/` | `hotel_list` | `hotels/hotel_list.html` | `/api/hotels/list/`, `/api/hotels/search/` | None (public) | ✓ |
| `/hotels/detail/<id>/` | `hotel_detail` | `hotels/hotel_detail.html` | `/api/hotels/<id>/`, `/api/check-availability/`, `/api/calculate-price/` | None (public) | ✓ |

**Expected API Responses**:
- `/api/hotels/list/` → `{ hotels: [...], count: N }`
- `/api/hotels/<id>/` → `{ id, name, address, price, images, ratings }`
- `/api/check-availability/` → `{ available: bool, inventory: N }`
- `/api/calculate-price/` → `{ base_price, service_fee, gst, total }`

---

### Flow 2: Hotel Booking Creation

| URL Path | Django View | Template | APIs Called | Permissions | Status |
|----------|------------|----------|------------|------------|--------|
| `/bookings/my-bookings/` | `my_bookings` | `bookings/my_bookings.html` | `/api/bookings/list/`, `/api/bookings/<id>/` | User logged in | ✓ |
| `/bookings/<uuid>/payment/` | `payment_page` | `bookings/payment.html` | `/api/create-razorpay-order/`, `/api/verify-payment/` | User logged in | ✓ |
| `/bookings/api/create-order/` | `create_razorpay_order` | (AJAX API) | Razorpay API (stub) | User logged in | ✓ |
| `/bookings/api/verify-payment/` | `verify_payment` | (AJAX API) | Razorpay verify | User logged in | ✓ |

**Expected API Responses**:
- `/api/create-razorpay-order/` → `{ order_id, amount, currency }`
- `/api/verify-payment/` → `{ success: bool, booking_id, transaction_id }`

---

### Flow 3: Finance Admin Dashboard

| URL Path | Django View | Template | APIs Called | Permissions | Status |
|----------|------------|----------|------------|------------|--------|
| `/finance/admin/dashboard/` | `admin_dashboard` | `finance/admin_dashboard.html` | `/api/finance/dashboard/metrics/` | FINANCE_ADMIN | ✓ |
| `/finance/admin/bookings/` | `booking_table` | `finance/booking_table.html` | `/api/finance/bookings/` | FINANCE_ADMIN | ✓ |
| `/finance/owner/earnings/` | `owner_earnings` | `finance/owner_earnings.html` | `/api/finance/owner/earnings/` | PROPERTY_ADMIN | ✓ |

**Expected API Responses**:
- `/api/finance/dashboard/metrics/` → `{ total_revenue, total_bookings, total_payouts, pending_payouts }`
- `/api/finance/bookings/` → `[ { booking_id, total, status, date, customer } ]`
- `/api/finance/owner/earnings/` → `[ { period, gross_amount, fees, net_payout, status } ]`

---

### Flow 4: Payout Management (Phase-4)

| URL Path | Django View | Template | APIs Called | Permissions | Status |
|----------|------------|----------|------------|------------|--------|
| `/finance/admin/dashboard/` | `admin_dashboard` | `finance/admin_dashboard.html` | `/api/finance/payouts/list/` | FINANCE_ADMIN | ⚠️ NEEDS CHECK |
| `/finance/admin/payouts/` | (TBD - NEED TO CREATE) | `finance/payout_list.html` | `/api/finance/payouts/` | FINANCE_ADMIN | ❌ MISSING |
| `/finance/approve-payout/<id>/` | (TBD - NEED TO CREATE) | (MODAL) | `/api/finance/payouts/<id>/approve/` | FINANCE_ADMIN | ❌ MISSING |

**ACTION REQUIRED**: Create payout UI endpoints if not present

---

## 🔧 REQUIRED IMPLEMENTATIONS

### Missing Endpoints (Must Create):

1. **Payout List Page**: `/finance/admin/payouts/`
   - Template: `finance/payout_list.html`
   - API: `/api/finance/payouts/` (list all payouts)
   - Data shown: Payout ID, Owner, Amount, Status, Bank Details (masked), Actions

2. **Payout Approval Modal**: `/api/finance/payouts/<id>/approve/`
   - Method: POST
   - Data: `{ action: "approve|reject", reason? }`
   - Response: `{ success, new_status, message }`

3. **Payout Retry Action**: `/api/finance/payouts/<id>/retry/`
   - Method: POST
   - Response: `{ success, retry_count, last_retry_at }`

4. **Payout Details View**: `/finance/admin/payouts/<id>/`
   - Template: `finance/payout_detail.html`
   - Shows: Full payout info, bank details (masked), transaction history

---

## ✅ VERIFICATION CHECKLIST

- [ ] All URLs resolve correctly (no 404s)
- [ ] All views return correct templates
- [ ] All APIs return expected JSON structure
- [ ] Permissions are enforced (401/403 if unauthorized)
- [ ] Database queries execute successfully
- [ ] No missing `reverse()` calls
- [ ] No circular imports
- [ ] All static files referenced exist
- [ ] All templates extend from valid base templates

---

## 🧪 E2E BOOKING FLOW (COMPLETE IMPLEMENTATION REQUIRED)

### Complete Flow: Search → Book → Pay → Invoice → Payout

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Search Hotels (PUBLIC)                              │
│ GET /hotels/                                                │
│ → Call /api/hotels/search/?city=TestCity&date=...          │
│ → Assert: Page shows hotels, prices, availability           │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: View Hotel Details                                  │
│ GET /hotels/detail/<hotel_id>/                              │
│ → Call /api/hotels/<hotel_id>/                              │
│ → Call /api/check-availability/                             │
│ → Assert: Price breakdown shown, room details visible       │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Create Booking                                      │
│ POST /api/bookings/create/ (mock endpoint)                  │
│ → Response: booking_id, total_amount, price_snapshot        │
│ → Assert: Price calculation correct (base + fee + gst)      │
│ → Assert: Inventory decreases by 1                          │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Payment Page & Wallet Top-up                        │
│ GET /bookings/<booking_id>/payment/                         │
│ → Show price breakdown                                      │
│ → Call /api/verify-payment/ (mock wallet payment)           │
│ → Assert: Booking status changes to CONFIRMED              │
│ → Assert: Invoice generated in DB                           │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Verify Invoice in Admin Dashboard                   │
│ GET /finance/admin/bookings/                                │
│ → Call /api/finance/bookings/                               │
│ → Assert: New booking appears in list                       │
│ → Assert: Invoice row shown with correct amount             │
│ → Assert: Status = CONFIRMED                                │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 6: Verify Payout Eligibility (Phase-4)                 │
│ GET /finance/admin/payouts/                                 │
│ → Call /api/finance/payouts/                                │
│ → Assert: Owner payout visible                              │
│ → Assert: Status = PENDING or KYC_PENDING                   │
│ → Assert: Amount = ₹ calculation correct                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 REQUIRED ASSERTIONS FOR EACH STEP

### Step 1: Search Results
```javascript
// Assert API request fired
await page.waitForResponse(resp => 
  resp.url().includes('/api/hotels/search/') && 
  resp.status() === 200
);

// Assert data rendered
await expect(page.locator('text=/Hotel|Guest House/i')).toBeVisible();
await expect(page.locator('[data-price]')).toBeVisible();

// Assert business value visible
await expect(page.locator('text=₹')).toBeVisible();
```

### Step 2: Hotel Details
```javascript
// Assert API calls for availability & price
await page.waitForResponse(resp => 
  resp.url().includes('/api/check-availability/') && 
  resp.status() === 200
);

// Assert price breakdown rendered
await expect(page.locator('text=/Base Price|Service Fee|Total/i')).toBeVisible();

// Assert correct calculation (₹5000 + ₹500 fee = ₹5500)
const priceText = await page.locator('[data-total-price]').textContent();
expect(priceText).toContain('₹5500');
```

### Step 3: Booking Creation
```javascript
// Assert POST request fired
const bookingResponse = await page.waitForResponse(resp => 
  resp.url().includes('/api/bookings/create/') && 
  resp.status() === 201
);

// Assert response contains booking_id
const bookingData = await bookingResponse.json();
expect(bookingData.booking_id).toBeDefined();

// Assert inventory changed in DB
const inventoryAfter = await getInventoryCount(hotelId);
expect(inventoryAfter).toBe(inventoryBefore - 1);
```

### Step 4: Payment & Invoice
```javascript
// Assert invoice created
const invoiceResponse = await page.waitForResponse(resp => 
  resp.url().includes('/api/finance/invoices/') && 
  resp.status() === 201
);

// Assert booking status updated
const bookingStatus = await getBookingStatus(bookingId);
expect(bookingStatus).toBe('confirmed');

// Assert invoice amount matches
const invoice = await invoiceResponse.json();
expect(invoice.total).toBe(5500);
```

### Step 5 & 6: Admin Verification
```javascript
// Assert admin sees new booking
await expect(page.locator(`text=${bookingId}`)).toBeVisible();

// Assert financial data displayed
await expect(page.locator('text=₹5500')).toBeVisible();

// Assert payout record exists
const payoutResponse = await page.waitForResponse(resp => 
  resp.url().includes('/api/finance/payouts/') && 
  resp.status() === 200
);
const payouts = await payoutResponse.json();
expect(payouts.some(p => p.booking_id === bookingId)).toBe(true);
```

---

## 🔐 SERVER LOG REQUIREMENTS

During Playwright test execution, server logs MUST NOT contain:

```
❌ 404 Not Found
❌ 500 Internal Server Error
❌ PermissionDenied
❌ Template not found
❌ AttributeError
❌ KeyError
❌ IntegrityError
❌ Database errors
```

**Capture command**:
```bash
python manage.py runserver --verbosity 2 > server.log 2>&1
```

**Verify command**:
```bash
grep -i "error\|exception\|404\|500" server.log
# Should return EMPTY for clean run
```

---

## 📋 TEST EXECUTION MATRIX

| Test | Command | Expected | Actual | Status |
|------|---------|----------|--------|--------|
| **API Tests** | `pytest tests/api/test_phase4_payouts.py -v` | 19/19 PASS | ? | ⏳ |
| **E2E (Headless)** | `npx playwright test --headless` | ALL PASS | ? | ⏳ |
| **E2E (Headed)** | `npx playwright test --headed` | ALL PASS | ? | ⏳ |
| **Server Logs** | `grep -i "error" server.log` | (empty) | ? | ⏳ |
| **Payment Flow** | Complete booking E2E | Booking → Invoice → Payout | ? | ⏳ |
| **Inventory Check** | Compare before/after | Decremented | ? | ⏳ |
| **Invoice Generated** | Query Invoice model | Row exists | ? | ⏳ |
| **Payout Created** | Query OwnerPayout model | Row exists | ? | ⏳ |

---

## 🚨 ABSOLUTE RULES

❌ **NO**: Page opens = test passes  
✅ **YES**: API response verified + Data rendered + Business value asserted

❌ **NO**: Skipping broken pages  
✅ **YES**: Every page tested with real assertions

❌ **NO**: Mocking browser automation  
✅ **YES**: Real Chromium browser, real HTTP requests

❌ **NO**: Summary without proof  
✅ **YES**: Screenshots, logs, response payloads

---

## 📝 NEXT STEPS

1. [ ] Verify all URLs resolve (no 404s)
2. [ ] Verify all APIs return correct JSON
3. [ ] Create missing Payout endpoints
4. [ ] Implement real Playwright tests (with assertions)
5. [ ] Run with server log capture
6. [ ] Generate test report with screenshots
7. [ ] Verify reconciliation (inventory, invoices, payouts)

---

*This audit drives acceptance testing. No shortcuts allowed.*
