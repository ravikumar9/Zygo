# Phase 1-4 Feature File Mapping & Quick Reference

**Generated:** January 25, 2026 | **Platform:** Go Explorer

---

## 📁 FILE STRUCTURE BY FEATURE

### 1️⃣ BOOKING & RESERVATION SYSTEM

#### Core Models
```
bookings/models.py
├── Booking (Main model)
│   ├── status: [reserved, payment_pending, confirmed, expired, cancelled, completed, refunded, deleted]
│   ├── booking_type: [hotel, bus, package]
│   ├── State transitions: reserved_at, confirmed_at, expires_at, completed_at
│   └── Soft delete: is_deleted, deleted_at, deleted_by, deleted_reason
│
├── HotelBooking (OneToOne)
│   ├── room_snapshot: JSONField (frozen room specs)
│   ├── price_snapshot: JSONField (frozen pricing)
│   ├── Cancellation policy lock: policy_locked_at
│   └── Booking details: check_in, check_out, num_rooms, num_nights
│
├── BusBooking (Partial)
│   └── Bus-specific fields
│
└── PackageBooking (Partial)
    └── Package-specific fields
```

#### APIs & Views
```
bookings/booking_api.py
├── PricingService
│   ├── calculate_service_fee() - 5% capped ₹500
│   └── calculate_booking_price() - Full pricing breakdown
│
├── HotelBookingViewSet
│   ├── POST /api/bookings/create/ - Create booking
│   ├── GET /api/bookings/<id>/details/ - Fetch details
│   ├── POST /api/bookings/<id>/confirm/ - Confirm after payment
│   ├── POST /api/bookings/<id>/cancel/ - Cancel booking
│   └── POST /api/bookings/pricing/calculate/ - Dynamic pricing
│
└── PromoAPIViewSet
    └── POST /api/bookings/promo/validate/ - Validate code
```

#### Utilities
```
bookings/inventory_utils.py
├── reserve_inventory(room_type, check_in, check_out, num_rooms) ✅
├── restore_inventory(room_type, check_in, check_out, num_rooms) ✅
└── _date_range() helper

bookings/pricing_calculator.py
├── Room + Meal plan pricing
├── Service fee calculation
└── Inventory warnings

bookings/cancellation_views.py
├── Cancellation policy enforcement
└── Refund calculation
```

#### URLs
```
bookings/urls.py
├── /api/bookings/
├── /api/bookings/create/
├── /api/bookings/<id>/details/
├── /api/bookings/<id>/cancel/
├── /api/bookings/<id>/confirm/
└── /api/bookings/pricing/
```

#### Tests
```
tests/api/test_phase1_execution.py
├── test_api_9_permissions_system
└── Other booking tests

tests/test_complete_workflow.py
├── End-to-end booking flow
└── Inventory validation

bookings/tests_e2e.py
├── Hotel booking lifecycle
└── User flows
```

#### Migrations (Latest)
```
bookings/migrations/
├── 0019_add_booking_snapshots.py (Price + room snapshot)
├── 0020_promocode_promocodeusage.py (Promo tracking)
└── Previous: channel fields, timestamps, meal plans
```

---

### 2️⃣ INVENTORY & AVAILABILITY SYSTEM

#### Core Models
```
hotels/models.py
├── RoomAvailability
│   ├── room_type (FK)
│   ├── date
│   ├── available_rooms
│   ├── price (optional override)
│   └── block_reason (block out dates)
│
├── RoomType
│   ├── hotel (FK)
│   ├── name, description
│   ├── base_price
│   ├── total_rooms
│   ├── capacity (beds, max_adults, max_children)
│   └── amenities_list (JSONField)
│
├── Hotel
│   ├── gst_percentage: default 18%
│   ├── inventory_source: [internal_cm, external_cm]
│   └── channel_manager_name (for external)
│
├── ChannelManagerRoomMapping
│   ├── hotel (FK)
│   ├── external_cm_room_id
│   └── sync_status
│
└── RoomBlock
    ├── room_type (FK)
    ├── block_from, block_to (dates)
    └── reason (blocked by owner)
```

#### Channel Manager Integration
```
hotels/channel_manager_service.py
├── ChannelManagerService class
│   ├── lock_inventory(mapping, check_in, check_out, num_rooms, hold_minutes)
│   ├── confirm_booking(lock_id, reference_id)
│   ├── release_lock(lock_id)
│   └── ChannelManagerSimulator (for testing)
│
└── InventoryLock model (tracks holds)
    ├── lock_id
    ├── room_type (FK)
    ├── booking (FK)
    ├── expires_at
    └── source: [internal, external_cm]
```

#### URLs
```
hotels/urls.py
├── /api/hotels/search/
├── /api/hotels/<id>/
├── /api/hotels/<id>/rooms/
└── /api/hotels/<id>/availability/
```

#### Tests
```
tests/test_inventory_lock_simple.py
├── Basic lock/restore

tests/test_inventory_lock_2users.py
├── Concurrent user scenarios

tests/test_concurrent_inventory.py
├── Race condition handling
```

---

### 3️⃣ PRICING & GST SYSTEM

#### Core Models
```
bookings/models.py
├── HotelBooking.price_snapshot (JSONField) ✅
│   ├── room_price_per_night
│   ├── meal_plan_delta
│   ├── subtotal_per_night
│   ├── service_fee (5% capped ₹500)
│   └── total_amount
│
└── HotelBooking.room_snapshot (JSONField)
    ├── room_name, description
    ├── capacity
    └── amenities

hotels/models.py
├── RoomMealPlan
│   ├── meal_plan (FK)
│   ├── room_type (FK)
│   └── price_delta (extra charge)
│
├── MealPlan
│   ├── name: [Room Only, Breakfast, Half Board, Full Board]
│   ├── plan_type
│   ├── inclusions (JSONField)
│   └── is_refundable
│
└── SeasonalPricing (Partial - not integrated)
    ├── room_type (FK)
    ├── season_start, season_end
    ├── base_price_override
    └── gst_override
```

#### Pricing Service
```
bookings/booking_api.py::PricingService ✅
├── SERVICE_FEE_PERCENT = 5.00%
├── SERVICE_FEE_CAP = ₹500
│
├── calculate_service_fee(subtotal)
│   └── Returns: min(subtotal * 5%, ₹500)
│
└── calculate_booking_price(room_type, meal_plan, num_nights, num_rooms)
    ├── room_price_per_night ✅
    ├── meal_plan_delta ✅
    ├── subtotal_per_night ✅
    ├── service_fee (5% capped) ✅
    ├── total_amount ✅
    └── inventory_warning ✅
```

#### GST Implementation
```
payments/models.py::Invoice ✅ (Structure only)
├── cgst: Central GST (field only, no calc)
├── sgst: State GST (field only, no calc)
└── igst: Integrated GST (field only, no calc)

⚠️ ISSUE: No GST calculation logic
   - No slab system (18% flat only)
   - No tier-based rates
   - No meal plan GST variance
```

#### Tests
```
tests/test_pricing.py
├── Basic pricing calculation

tests/test_gst_compliance.py
├── GST field verification (not calculation)

tests/test_gst_tiers.py
├── Incomplete - tiers not implemented
```

---

### 4️⃣ PAYMENT & WALLET SYSTEM

#### Core Models
```
payments/models.py
├── Payment
│   ├── booking (FK)
│   ├── amount, currency
│   ├── payment_method: [razorpay, stripe, upi, card, netbanking, wallet, cash]
│   ├── status: [pending, processing, success, failed, refunded]
│   ├── gateway_payment_id, gateway_order_id, gateway_signature
│   ├── transaction_id, transaction_date
│   ├── gateway_response (JSONField)
│   ├── refund_id, refund_amount, refund_date
│   └── notes
│
├── Wallet
│   ├── user (OneToOne)
│   ├── balance (current)
│   ├── cashback_earned
│   ├── currency
│   ├── is_active
│   ├── add_balance(amount, description) ✅
│   └── deduct_balance(amount, description) ✅
│
├── WalletTransaction
│   ├── wallet (FK)
│   ├── transaction_type: [credit, debit]
│   ├── amount
│   ├── balance_before, balance_after
│   ├── description
│   ├── status
│   └── payment_gateway
│
└── Invoice (immutable snapshot) ✅
    ├── booking (OneToOne)
    ├── invoice_number (auto-generated)
    ├── Billing info: name, email, phone, address
    ├── Property snapshot: name, check_in, check_out, num_rooms, meal_plan
    ├── Amount breakdown:
    │   ├── subtotal
    │   ├── service_fee
    │   ├── tax_amount
    │   ├── discount_amount
    │   ├── wallet_used
    │   └── total_amount
    ├── Tax fields: cgst, sgst, igst
    ├── Payment info: payment_mode, payment_timestamp
    └── pdf_file (storage, generation incomplete)
```

#### APIs
```
payments/views.py
├── POST /api/payments/initiate/ - Start payment
├── POST /api/payments/callback/ - Gateway webhook
├── GET /api/payments/wallet/balance/ - Check balance
└── GET /api/payments/wallet/transactions/ - History

payments/cashfree_service.py
├── Payment gateway integration
└── Signature verification
```

#### URLs
```
payments/urls.py
├── /api/payments/initiate/
├── /api/payments/callback/
├── /api/payments/wallet/
└── /api/payments/wallet/transactions/
```

#### Tests
```
tests/test_wallet_payment_flow.py
├── Wallet payment integration

tests/test_partial_wallet_payment.py
├── Hybrid payment (wallet + gateway)

tests/test_partial_wallet_split.py
├── Split payment scenarios
```

---

### 5️⃣ INVOICING SYSTEM

#### Core Model
```
payments/models.py::Invoice ✅
├── booking (OneToOne FK)
├── invoice_number (unique, auto-generated)
├── invoice_date (auto_now_add)
│
├── Billing Details:
│   ├── billing_name
│   ├── billing_email
│   ├── billing_phone
│   └── billing_address
│
├── Property Snapshot:
│   ├── property_name
│   ├── check_in, check_out
│   ├── num_rooms
│   ├── meal_plan
│
├── Amount Breakdown:
│   ├── subtotal (room + meal)
│   ├── service_fee (5% capped ₹500)
│   ├── tax_amount (GST)
│   ├── discount_amount (promo)
│   ├── wallet_used
│   └── total_amount
│
├── Tax Details:
│   ├── cgst (Central GST)
│   ├── sgst (State GST)
│   └── igst (Integrated GST)
│
├── Payment Info:
│   ├── payment_mode
│   ├── payment_timestamp
│
├── pdf_file (FileField, generation TBD)
│
└── Class Methods:
    └── create_for_booking(booking, payment=None) ✅
        ├── Auto-generates invoice_number
        ├── Captures booking snapshot
        ├── Extracts pricing from price_snapshot
        └── Calculates totals
```

#### Serializers
```
finance/serializers.py::InvoiceSerializer
├── Serializes invoice data for API responses
└── Read-only fields
```

#### APIs
```
finance/api_views.py
├── GET /api/admin/invoices/ - List all (admin)
├── GET /api/admin/invoices/<id>/ - Details (admin)
└── GET /api/invoices/<booking_id>/ - User's invoice (authenticated)
```

#### Tests
```
tests/api/test_phase3_finance.py::TestInvoiceGeneration
├── Invoice creation tests

tests/api/test_phase3_finance.py::TestInvoiceAPI
├── API endpoint tests
```

#### Gaps ⚠️
- PDF generation not implemented
- Email delivery not automated
- Invoice resend API missing

---

### 6️⃣ OWNER PAYOUT SYSTEM

#### Core Model
```
finance/models.py::OwnerPayout ✅
├── booking (OneToOne FK)
├── hotel (FK)
├── owner (FK to User)
│
├── Amounts:
│   ├── gross_booking_value (100% of booking)
│   ├── platform_service_fee (5% platform cut)
│   ├── net_payable_to_owner (95% to owner)
│
├── Status:
│   ├── booking_status (confirmed/cancelled)
│   ├── settlement_status: [pending, processing, paid, failed]
│
├── Settlement Tracking:
│   ├── settled_at (timestamp)
│   ├── settlement_reference (transfer ID)
│   └── notes (dispute notes, etc.)
│
└── Class Methods:
    └── create_for_booking(booking) ✅
        ├── Triggered when booking confirmed
        ├── Extracts owner from hotel relationship
        ├── Calculates net amount after fees
        └── Sets initial status to 'pending'
```

#### APIs
```
finance/api_views.py
├── GET /api/admin/payouts/ - List all payouts (admin)
├── GET /api/admin/payouts/<id>/ - Details (admin)
├── POST /api/admin/payouts/<id>/settle/ - Settle payout (admin) ⚠️ Partial
└── GET /api/owner/earnings/ - Owner's payout history (owner)
```

#### Tests
```
tests/api/test_phase3_finance.py::TestOwnerEarningsAPI
├── Owner earnings endpoint tests

tests/api/test_phase3_finance.py::TestRevenueAccuracy
├── Payout calculation accuracy
```

#### Gaps ⚠️
- No automated payout scheduling
- Bank transfer integration missing
- Bulk settlement not implemented
- Dispute/refund payout logic missing

---

### 7️⃣ FINANCE DASHBOARD & REPORTING

#### Core Models
```
finance/models.py::PlatformLedger ✅
├── date (unique, DateField)
│
├── Metrics (aggregated daily):
│   ├── total_bookings (count)
│   ├── total_revenue (sum of amounts)
│   ├── total_service_fee_collected (platform fees)
│   ├── wallet_liability (total wallet balance)
│   ├── total_refunds (refund amounts)
│   ├── net_revenue (profit)
│   └── total_cancellations (count)
│
└── Class Methods:
    └── compute_for_date(target_date) ✅
        ├── Aggregates confirmed bookings
        ├── Sums service fees
        ├── Calculates wallet liability
        ├── Tracks refunds
        └── Updates or creates ledger entry
```

#### Serializers
```
finance/serializers.py
├── DashboardMetricsSerializer ✅
│   ├── total_bookings
│   ├── total_revenue
│   ├── total_service_fee
│   ├── total_wallet_used
│   ├── cancellations_count
│   ├── active_properties
│   └── pending_approvals
│
├── OwnerPayoutSerializer
│   ├── Payout data + status
│
├── PlatformLedgerSerializer
│   └── Daily ledger data
│
└── BookingListSerializer
    └── Booking list for dashboard
```

#### APIs
```
finance/api_views.py
├── GET /api/admin/dashboard/metrics/ - Summary (admin)
│   ├── Query filters: date_from, date_to
│   ├── Response: metrics snapshot
│   └── Permission: SUPER_ADMIN or FINANCE_ADMIN
│
├── GET /api/admin/dashboard/bookings/ - Booking list (admin)
│   ├── Filters: status, property, date range
│   └── Pagination support
│
└── GET /api/admin/dashboard/ledger/ - Platform ledger (admin)
    ├── Query filter: date
    └── Returns aggregated daily metrics
```

#### Roles (Permission Checks)
```
finance/api_views.py::has_admin_role()
├── SUPER_ADMIN - All features
├── FINANCE_ADMIN - Metrics, invoices, payouts
├── OPERATIONS_ADMIN - Bookings, cancellations
└── SUPPORT_ADMIN - View-only access
```

#### Tests
```
tests/api/test_phase3_finance.py::TestDashboardFilters
├── Dashboard filtering tests

tests/test_sprint1.py::DashboardMetricsTest
├── Ledger computation tests
```

#### Gaps ⚠️
- No real-time dashboard (only daily)
- No hourly/monthly breakdowns
- No property-level drill-down
- No cohort analysis/KPIs
- No export functionality

---

### 8️⃣ ROLE-BASED ACCESS CONTROL (RBAC)

#### Setup Command
```
finance/management/commands/setup_admin_roles.py ✅
└── Creates 4 admin role groups:

    1. SUPER_ADMIN
       ├── All permissions across platform
       └── Can manage all features
    
    2. FINANCE_ADMIN
       ├── view_ownerpayout
       ├── view_invoice
       ├── view_platformledger
       └── Can see financial data
    
    3. OPERATIONS_ADMIN
       ├── change_booking
       ├── delete_booking
       └── Can manage bookings/cancellations
    
    4. SUPPORT_ADMIN
       └── View-only permissions for support team
```

#### Permission System
```
Django's built-in:
├── User.groups (M2M to Group)
├── Group.permissions (M2M to Permission)
├── User.has_perm() method
└── User.user_permissions (direct perms)
```

#### API Permission Decorators
```
All API files use:

@permission_classes([AllowAny])
├── Public endpoints (booking creation, search)

@permission_classes([IsAuthenticated])
├── User-specific endpoints (own bookings, wallet)

@permission_classes([IsAdminUser])
├── Admin-only endpoints (full management)

has_admin_role(user, *roles)
├── Helper to check group membership
├── Used in finance/api_views.py
└── Returns: boolean (user in role or not)
```

#### RBAC Implementation Locations
```
property_owners/property_owner_registration_api.py
├── @permission_classes([IsAuthenticated])
└── Owner registration endpoints

property_owners/approval_api.py
├── @permission_classes([IsAdminUser])
└── Admin approval endpoints

finance/api_views.py
├── has_admin_role(user, 'SUPER_ADMIN', 'FINANCE_ADMIN')
└── Dashboard/finance endpoints

bookings/booking_api.py
├── @permission_classes([AllowAny]) - Public search
├── @permission_classes([IsAuthenticated]) - User booking
└── @permission_classes([AllowAny]) - Pricing calc
```

#### Tests
```
tests/api/test_phase1_execution.py
├── test_api_9_permissions_system() ✅
    └── Verifies permission checks work

tests/api/test_phase3_admin_finance.py::TestRoleBasedAccess
├── Role-specific access tests
└── 403 Forbidden tests for unauthorized users
```

#### Gaps ⚠️
- No field-level access control (FLS)
- No ownership-based access (owner can see all)
- Limited per-endpoint granularity
- No permission denial audit logging

---

### 9️⃣ TESTING INFRASTRUCTURE

#### API Tests
```
tests/api/test_phase1_execution.py ✅
├── TestPhase1APIExecution class
├── 9 test methods covering core flows
├── Permission system tests
└── Integration tests

tests/api/test_phase3_finance.py ✅
├── TestInvoiceGeneration - Invoice creation
├── TestRoleBasedAccess - Permission checks
├── TestOwnerEarningsAPI - Payout APIs
├── TestRevenueAccuracy - Calculation verification
├── TestInvoiceAPI - Invoice endpoints
├── TestLedgerAPI - Ledger aggregation
└── TestDashboardFilters - Dashboard queries

tests/api/test_phase3_admin_finance.py ✅
├── Admin-specific API tests
├── Dashboard filtering
├── Endpoint availability checks
└── Role-based access validation
```

#### E2E Tests
```
tests/e2e/test_phase3_admin_ui.py
├── TestFinanceDashboard - Dashboard UI
├── TestInvoiceUI - Invoice display
├── TestDashboardNavigation - UI navigation
└── Playwright-based UI automation

tests/e2e/test_phase3_playwright_ui.py
├── TestFinanceDashboardUI
├── TestInvoiceUI
└── TestDashboardNavigation
```

#### Component Tests
```
tests/test_complete_workflow.py
├── End-to-end booking flow
├── Inventory validation
└── Payment integration

tests/test_sprint1.py
├── DashboardMetricsTest - Ledger computation
└── Other feature tests

tests/test_inventory_lock_simple.py
├── Basic inventory operations

tests/test_inventory_lock_2users.py
├── Concurrent user scenarios

tests/test_concurrent_inventory.py
├── Race condition handling

tests/test_pricing.py
├── Pricing calculations

tests/test_gst_compliance.py
├── GST field verification

tests/test_wallet_payment_flow.py
├── Wallet payment flow
```

#### Test Configuration
```
tests/api/conftest.py ✅
├── Pytest fixtures
├── Test database setup
├── Test users/data creation
└── API client configuration

pytest.ini
├── Test runner configuration
├── Plugin setup
└── Marker definitions
```

#### Test Gaps ⚠️
- Bulk settlement not tested
- Dispute scenarios not covered
- Multi-property interactions partial
- Load testing not performed
- E2E coverage incomplete

---

### 🔟 DATABASE SCHEMA & MIGRATIONS

#### Migration History
```
bookings/migrations/
├── 0001_initial.py - Base Booking model
├── 0002_initial.py - Alternative initial version
├── 0003_booking_deleted_at - Soft delete fields
├── 0004_add_channel_fields.py - External CM support
├── 0005_booking_cm_booking_id - Channel manager booking ID
├── 0006_alter_booking_status - Status field adjustments
├── 0007_booking_confirmed_at - Lifecycle timestamps (reserved_at, confirmed_at, expires_at, completed_at)
├── 0008_merge_20260116_0728 - Merge migration
├── 0009_hotelbooking_meal_plan - Meal plan linkage
├── 0010_populate_meal_plans - Data migration
├── 0011_make_meal_plan_required - Required constraint
├── 0012_add_completed_at_timestamp - Completion timestamp
├── 0013_add_promo_code_to_booking - Promo code FK
├── 0013_make_meal_plan_optional - Alternative - make optional
├── 0014_hotelbooking_policy_snapshot - Cancellation policy lock
├── 0015_merge_20260121_1826 - Merge migration
├── 0016_busbooking_contact_phone - Bus booking fields
├── 0017_busbooking_bus_name - Bus name field
├── 0018_alter_booking_user - User FK adjustment
├── 0019_add_booking_snapshots.py - Pricing & room snapshots ✅
├── 0020_promocode_promocodeusage.py - Promo tracking
└── __init__.py
```

#### payments/migrations/
```
├── 0001_initial.py - Payment, Invoice, Wallet models
├── 0002_wallet_balance_tracking.py - Wallet transaction tracking
└── Dependencies on bookings migrations
```

#### finance/migrations/
```
├── OwnerPayout model
├── PlatformLedger model
└── Depends on bookings models
```

#### Core Database Tables
```
Booking Model:
├── id (PK)
├── booking_id (UUID, unique)
├── user_id (FK)
├── status (CharField)
├── booking_type (CharField)
├── total_amount (DecimalField)
├── paid_amount (DecimalField)
├── State transitions: reserved_at, confirmed_at, expires_at, completed_at
├── Soft delete: is_deleted, deleted_at, deleted_by_id
├── Timestamps: created_at, updated_at
└── External CM: cm_booking_id, channel_manager_name, lock_id

HotelBooking Model:
├── id (PK)
├── booking_id (FK OneToOne)
├── room_type_id (FK)
├── meal_plan_id (FK, nullable)
├── cancellation_policy_id (FK, nullable)
├── price_snapshot (JSONField)
├── room_snapshot (JSONField)
├── Cancellation: policy_type, policy_locked_at
└── Details: check_in, check_out, number_of_rooms, total_nights

Payment Model:
├── id (PK)
├── booking_id (FK)
├── amount (DecimalField)
├── payment_method (CharField)
├── status (CharField)
├── gateway_payment_id (CharField)
├── gateway_response (JSONField)
└── Refund: refund_id, refund_amount, refund_date

Invoice Model:
├── id (PK)
├── booking_id (FK OneToOne)
├── invoice_number (CharField, unique)
├── Billing info: name, email, phone, address
├── Property snapshot: name, check_in, check_out, num_rooms, meal_plan
├── Amounts: subtotal, service_fee, tax_amount, discount, wallet_used, total, paid
├── Tax: cgst, sgst, igst
└── pdf_file (FileField)

Wallet Model:
├── id (PK)
├── user_id (FK OneToOne)
├── balance (DecimalField)
├── cashback_earned (DecimalField)
└── is_active (BooleanField)

WalletTransaction Model:
├── id (PK)
├── wallet_id (FK)
├── transaction_type (CharField: credit/debit)
├── amount (DecimalField)
├── balance_before, balance_after
├── status (CharField)
└── payment_gateway (CharField)

OwnerPayout Model:
├── id (PK)
├── booking_id (FK OneToOne)
├── hotel_id (FK)
├── owner_id (FK)
├── gross_booking_value (DecimalField)
├── platform_service_fee (DecimalField)
├── net_payable_to_owner (DecimalField)
├── settlement_status: [pending, processing, paid, failed]
└── settled_at (DateTimeField, nullable)

PlatformLedger Model:
├── id (PK)
├── date (DateField, unique)
├── total_bookings (IntegerField)
├── total_revenue (DecimalField)
├── total_service_fee_collected (DecimalField)
├── wallet_liability (DecimalField)
├── total_refunds (DecimalField)
├── net_revenue (DecimalField)
└── total_cancellations (IntegerField)
```

#### Schema Gaps ⚠️
- No database indexes on frequently queried fields
- No partition strategy for large tables
- No archival strategy for old data

---

## 📊 QUICK STATUS TABLE

| Component | Status | Coverage | Location |
|-----------|--------|----------|----------|
| **Booking Models** | ✅ 95% | Complete | bookings/models.py |
| **Inventory Lock** | ✅ 90% | Complete | bookings/inventory_utils.py |
| **Pricing Service** | ✅ 90% | Complete | bookings/booking_api.py |
| **GST System** | ⚠️ 60% | Partial | payments/models.py |
| **Invoice Gen** | ✅ 85% | Complete | payments/models.py |
| **Owner Payouts** | ✅ 75% | Complete | finance/models.py |
| **Dashboard** | ✅ 70% | Partial | finance/api_views.py |
| **RBAC** | ✅ 90% | Complete | finance/mgmt/setup_admin_roles.py |
| **APIs** | ✅ 85% | Complete | */api_views.py, */booking_api.py |
| **Tests** | ⚠️ 75% | Partial | tests/ |
| **Migrations** | ✅ 95% | Complete | */migrations/ |

---

## 🎯 QUICK FILE REFERENCE

### To Understand: [Booking Lifecycle]
→ Start with: [bookings/models.py](bookings/models.py#L14) (Booking class)
→ Then read: [bookings/booking_api.py](bookings/booking_api.py#L1) (API flow)
→ Tests: [tests/api/test_phase1_execution.py](tests/api/test_phase1_execution.py)

### To Understand: [Inventory Lock/Restore]
→ Start with: [bookings/inventory_utils.py](bookings/inventory_utils.py)
→ Usage: [bookings/booking_api.py](bookings/booking_api.py) (in booking creation)
→ Tests: [tests/test_inventory_lock_simple.py](tests/test_inventory_lock_simple.py)

### To Understand: [Pricing]
→ Start with: [bookings/booking_api.py](bookings/booking_api.py#L23) (PricingService)
→ Models: [bookings/models.py](bookings/models.py#L256) (price_snapshot)
→ Tests: [tests/test_pricing.py](tests/test_pricing.py)

### To Understand: [Invoicing]
→ Start with: [payments/models.py](payments/models.py#L64) (Invoice class)
→ Creation: [payments/models.py](payments/models.py#L113) (create_for_booking method)
→ APIs: [finance/api_views.py](finance/api_views.py#L93)

### To Understand: [Payouts]
→ Start with: [finance/models.py](finance/models.py#L10) (OwnerPayout class)
→ Creation: [finance/models.py](finance/models.py#L49) (create_for_booking method)
→ APIs: [finance/api_views.py](finance/api_views.py#L150)

### To Understand: [Dashboard]
→ Start with: [finance/models.py](finance/models.py#L76) (PlatformLedger)
→ Computation: [finance/models.py](finance/models.py#L111) (compute_for_date method)
→ APIs: [finance/api_views.py](finance/api_views.py#L24)

### To Understand: [RBAC]
→ Start with: [finance/management/commands/setup_admin_roles.py](finance/management/commands/setup_admin_roles.py)
→ Usage: [finance/api_views.py](finance/api_views.py#L21) (has_admin_role function)
→ Tests: [tests/api/test_phase3_admin_finance.py](tests/api/test_phase3_admin_finance.py#L176)

---

**Last Updated:** 2026-01-25  
**Current Version:** Phase 1-4 (85% Complete)  
**Next Update:** After Phase-4 completion
