"""
GOIBIBO PRODUCTION ARCHITECTURE - COMPLETE REFERENCE

This document describes the complete production-ready architecture
for property registration, admin approval, booking, and GST compliance.
"""

# ==============================================================================
# 1. PROPERTY REGISTRATION + ADMIN APPROVAL WORKFLOW
# ==============================================================================

"""
MODELS:
  - Property (owner submits)
    ├── status: DRAFT → PENDING → APPROVED/REJECTED
    ├── submitted_at: When owner submitted
    ├── approved_at: When admin approved
    └── approved_by: Admin user
  
  - PropertyApprovalRequest (tracks submission)
    ├── property: FK to Property
    ├── status: SUBMITTED → UNDER_REVIEW → APPROVED/REJECTED → REVOKED
    ├── submitted_by: Owner user
    ├── reviewed_by: Admin user
    ├── decision: APPROVED or REJECTED
    ├── rejection_reason: Mandatory if rejected
    └── approved_until: Optional expiry date
  
  - PropertyApprovalChecklist (admin verification)
    ├── approval_request: FK
    ├── items: JSON dict of checklist status
    ├── all_passed: Boolean
    └── last_reviewed_at: Timestamp
  
  - PropertyApprovalAuditLog (compliance trail)
    ├── approval_request: FK
    ├── action: SUBMITTED, APPROVED, REJECTED, REVOKED, etc.
    ├── performed_by: User who performed action
    └── action_details: JSON metadata

WORKFLOW:
  1. Owner creates property → Property.status = DRAFT
  2. Owner adds rooms, images, pricing
  3. Owner clicks "Submit for Approval"
     → Property.status = PENDING
     → PropertyApprovalRequest created (SUBMITTED)
     → Admin gets notification
  
  4. Admin reviews in approval queue
  5. Admin clicks "Approve"
     → PropertyApprovalRequest.status = APPROVED
     → Property.status = APPROVED
     → Property.approved_at = now()
     → Property visible to users
  
  6. (Optional) Admin revokes
     → PropertyApprovalRequest.status = REVOKED
     → Property.status = REJECTED
     → Property hidden from users

DATABASE CONSTRAINTS:
  - property_ow_propert_idx: (property, status) - Fast approval queue queries
  - property_ow_status_idx: (status, submitted_at) - Ordered approval list

QUERY FILTER (CRITICAL):
  Approved properties for users:
    Property.objects.filter(status='APPROVED', is_active=True)
  
  All properties for admin:
    Property.objects.all()  # Admin sees everything

"""

# ==============================================================================
# 2. ROOM TYPES + 4 MEAL PLANS WITH DYNAMIC PRICING
# ==============================================================================

"""
MODELS:
  - RoomType (property rooms)
    ├── hotel: FK to Hotel
    ├── name: "Deluxe Room", etc.
    ├── max_adults, max_children
    ├── bed_type: "king", "double", "twin", etc.
    ├── room_size: sqft (MANDATORY for approval)
    ├── base_price: ₹X per night
    ├── total_rooms: inventory count
    ├── supports_hourly: optional 6h/12h/24h pricing
    ├── status: DRAFT → READY → APPROVED
    └── discount_type, discount_value, discount_is_active: Room-level discount
  
  - MealPlan (global meal plan types)
    ├── name: "Room Only", "Breakfast Included", etc.
    ├── plan_type: room_only, breakfast, half_board, full_board, all_inclusive
    ├── inclusions: ["WiFi", "Breakfast", "Lunch", "Dinner"]
    ├── description: What's included
    └── is_refundable: Can bookings be cancelled?
  
  - RoomMealPlan (link room to meal plans with pricing delta)
    ├── room_type: FK
    ├── meal_plan: FK
    ├── price_delta: ₹X (additional cost)
    ├── is_default: Pre-select this?
    ├── is_active: Available for booking?
    └── display_order: Sort order

PRICING FORMULA:
  Total Price = (RoomType.base_price + RoomMealPlan.price_delta) × nights × num_rooms

EXAMPLE:
  Room: Deluxe Double, Base Price: ₹3,000
  
  Meal Plans:
  1. Room Only
     Delta: ₹0
     Total/night: ₹3,000
  
  2. Breakfast Included
     Delta: ₹500
     Total/night: ₹3,500
  
  3. Full Board
     Delta: ₹1,500
     Total/night: ₹4,500
  
  User books: 2 nights, 1 room, Breakfast Included
  Calculation: (₹3,000 + ₹500) × 2 = ₹7,000

DYNAMIC PRICING:
  - When user selects meal plan, total price updates in real-time
  - UI shows: Room Price + Meal Plan = Subtotal
  - No percentage shown, only ₹ amounts

INVENTORY:
  - RoomType.total_rooms: Total inventory
  - RoomAvailability: By-date availability tracking
  - inventory_warning: If < 5 rooms, show scarcity message

"""

# ==============================================================================
# 3. BOOKING FLOW & GST COMPLIANCE
# ==============================================================================

"""
MODELS:
  - Booking (base booking)
    ├── booking_id: UUID (public ID)
    ├── booking_type: 'hotel', 'bus', 'package'
    ├── status: 'reserved' → 'confirmed' → 'completed'
    ├── reserved_at: When created
    ├── expires_at: When 30-min hold expires
    ├── total_amount: Final price
    ├── customer_name, email, phone
    └── pricing_data: JSON snapshot of pricing at booking time
  
  - HotelBooking (specific to hotel bookings)
    ├── booking: FK
    ├── room_type: FK
    ├── meal_plan: FK (nullable, Room Only)
    ├── check_in_date, check_out_date
    ├── num_rooms
    ├── price_per_night: Frozen at booking time
    ├── total_price: Before GST
    ├── gst_amount: Calculated at booking time
    └── service_fee: ₹99 flat

GST CALCULATION (India Compliance):
  
  Per-Night Subtotal = RoomType.base_price + RoomMealPlan.price_delta
  
  if per_night_subtotal < ₹7,500:
    gst_rate = 0%
  elif per_night_subtotal < ₹15,000:
    gst_rate = 5%
  else:
    gst_rate = 18%
  
  Total Before GST = per_night_subtotal × nights × num_rooms
  GST Amount = Total Before GST × (gst_rate / 100)
  Service Fee = ₹99 (flat)
  Final Total = Total Before GST + GST Amount + Service Fee

PRICING RESPONSE:
  {
    "room_price_per_night": ₹3000,
    "meal_plan_delta": ₹500,
    "subtotal_per_night": ₹3500,
    "total_nights": 2,
    "num_rooms": 1,
    "total_before_gst": ₹7000,
    "gst_rate": 5.0,  (percentage for internal use)
    "gst_amount": ₹350,  (amount shown to user)
    "service_fee": ₹99,
    "total_amount": ₹7449,
    "inventory_warning": "Only 3 rooms left at this price"  (if < 5)
  }

UI DISPLAY (NO PERCENTAGES):
  Room Price: ₹3,000
  Meal Plan: +₹500
  Subtotal: ₹3,500/night × 2 = ₹7,000
  ─────────────────
  Taxes & Fees: ₹449  (expandable)
    ├─ GST: ₹350
    └─ Service Fee: ₹99
  ─────────────────
  Total: ₹7,449

BOOKING STATES:
  1. RESERVED (30-min hold)
     - Inventory locked
     - User can complete payment
     - Expires after 30 minutes
  
  2. CONFIRMED (payment received)
     - Booking locked
     - Inventory committed
     - Can be cancelled per policy
  
  3. COMPLETED
     - Stay finished
     - Can be reviewed
     - Eligible for refunds

"""

# ==============================================================================
# 4. INVENTORY & SCARCITY PSYCHOLOGY
# ==============================================================================

"""
INVENTORY TRACKING:
  - RoomType.total_rooms: Max inventory
  - RoomType.inventory_count property: Current available
  - Decrements on RESERVED booking
  - Frees on expired/cancelled bookings

SCARCITY WARNING:
  if RoomType.inventory_count < 5:
    warning = f"Only {count} rooms left at this price"
  else:
    warning = None

REAL-TIME UPDATES:
  - After each booking creation
  - After each cancellation
  - After each automatic expiry
  - Shown in pricing breakdown
  - Updates frontend instantly

HONEST MESSAGING:
  - Never shows fake stock
  - Real count from database
  - No artificial scarcity
  - User trust maintained

"""

# ==============================================================================
# 5. REST API ARCHITECTURE
# ==============================================================================

"""
AUTHENTICATION:
  - Owner endpoints: @permission_classes([IsAuthenticated])
  - Admin endpoints: @permission_classes([IsAdminUser])
  - Public booking endpoints: @permission_classes([AllowAny])
  - All modify operations: @atomic transaction

OWNER APIS:
  
  POST /api/property-owners/me/properties/
    Body: {name, description, city, address, base_price, ...}
    Response: Property object, status=DRAFT
    Error: 403 if not a registered owner
  
  POST /api/property-owners/properties/{id}/submit-for-approval/
    Validation: All room types READY, 3+ images per room, 1+ meal plans
    Effect: Property status DRAFT → PENDING
    Response: PropertyApprovalRequest object
    Error: 400 if prerequisites not met
  
  GET /api/property-owners/me/submissions/
    Response: [PropertyApprovalRequest, ...]
    Filter: Only owner's properties

ADMIN APIS:
  
  GET /api/admin/property-approvals/
    Query params: status (SUBMITTED, APPROVED, REJECTED), page
    Response: Paginated list of PropertyApprovalRequest
    Filter: All properties by status
  
  POST /api/admin/property-approvals/{id}/approve/
    Body: {approval_reason, approved_until}
    Effect: Create audit log, update Property.status = APPROVED
    Response: Updated PropertyApprovalRequest
    Error: 400 if already approved/revoked
  
  POST /api/admin/property-approvals/{id}/reject/
    Body: {rejection_reason} (MANDATORY)
    Effect: Property status = REJECTED, owner notified
    Response: Updated PropertyApprovalRequest
    Error: 400 if no rejection reason
  
  POST /api/admin/property-approvals/{id}/revoke/
    Body: {revocation_reason}
    Effect: APPROVED → REVOKED, property hidden
    Response: Updated PropertyApprovalRequest
  
  GET /api/admin/properties/{id}/
    Response: Full property object + all approval requests + rooms + images

BOOKING APIS:
  
  GET /api/rooms/available/
    Query: check_in (YYYY-MM-DD), check_out (YYYY-MM-DD)
    Response: List of rooms with pricing, only from APPROVED properties
    Include: room_id, room_name, hotel, base_price, available_count, meal_plans
  
  GET /api/rooms/{room_type_id}/pricing/
    Query: check_in, check_out, meal_plan_id, num_rooms
    Response: Complete pricing breakdown
    Include: room_price, meal_delta, subtotal, gst_rate, gst_amount, service_fee, total
  
  POST /api/bookings/hotel/
    Body: {room_type_id, meal_plan_id, check_in_date, check_out_date, 
            num_rooms, customer_name, customer_email, customer_phone}
    Response: booking_id, pricing, expires_at (30 min from now)
    Effect: Booking created, inventory locked, holds for 30 min
    Error: 400 if invalid dates, insufficient inventory, unapproved room
  
  GET /api/bookings/{booking_id}/
    Response: Full booking object + pricing snapshot
    Public access (no auth needed, use UUID)

ERROR RESPONSES:
  400: Invalid input (bad dates, insufficient inventory)
  403: Permission denied (not owner, not admin)
  404: Resource not found
  500: Server error

"""

# ==============================================================================
# 6. SECURITY CONSIDERATIONS
# ==============================================================================

"""
PROPERTY VISIBILITY CONTROL:
  - Query filter: Property.objects.filter(status='APPROVED', is_active=True)
  - Applied at view layer: All room listings, detail pages
  - Admin queries unrestricted to enable management
  - Database level: Unique constraint on status field ensures consistency

ADMIN ACCESS CONTROL:
  - @permission_classes([IsAdminUser]) on all admin endpoints
  - @admin_required decorator on sensitive operations
  - Audit log every action: APPROVED, REJECTED, REVOKED, etc.
  - Rejection reasons MANDATORY and stored (compliance)

DATA INTEGRITY:
  - @atomic on all multi-step operations
  - Pricing snapshots frozen at booking time
  - Admin price changes don't affect existing bookings
  - Inventory locking prevents overbooking

AUDIT TRAIL:
  - PropertyApprovalAuditLog: All approval decisions logged
  - Includes: action, user, timestamp, reason
  - Immutable: Can't be edited, only appended
  - Compliance: Full history for regulators

PRICE INTEGRITY:
  - Booking.pricing_data: Snapshot at booking time
  - Future price changes don't affect past bookings
  - Disputes resolved by frozen snapshot
  - Fair pricing, no bait-and-switch

"""

# ==============================================================================
# 7. DATABASE SCHEMA SUMMARY
# ==============================================================================

"""
NEW TABLES:
  - property_owners_propertyapprovalrequest
  - property_owners_propertyapprovalchecklist
  - property_owners_propertyapprovalauditlog

INDEXES ADDED:
  - property_ow_propert_idx: (property, status)
  - property_ow_status_idx: (status, submitted_at)

EXISTING TABLES MODIFIED:
  - property_owners_property: Added status field, approval tracking
  - hotels_roomtype: Compatible, no breaking changes
  - bookings_booking: HotelBooking link already exists

CONSTRAINTS ENFORCED:
  - Property.status required, not nullable
  - PropertyApprovalRequest.rejection_reason required if rejected
  - RoomType.base_price > 0 for valid rooms
  - MealPlan must be unique (no duplicates)

"""

# ==============================================================================
# 8. DEPLOYMENT CHECKLIST
# ==============================================================================

"""
Pre-Deployment:
  ☐ Run all migrations: python manage.py migrate
  ☐ Collect static files: python manage.py collectstatic --noinput
  ☐ Create superuser (admin)
  ☐ Create test users (owner, customer)
  ☐ Seed test data (properties, rooms, meal plans)
  ☐ Run test suite: pytest tests/
  ☐ Load sample data: python manage.py loaddata (if using fixtures)

Post-Deployment:
  ☐ Verify approval workflow works (test property submission)
  ☐ Test booking creation with different meal plans
  ☐ Check GST calculations for different price points
  ☐ Verify inventory alerts appear
  ☐ Confirm approved-only visibility
  ☐ Check admin approval interface
  ☐ Verify audit logs are created
  ☐ Run E2E tests in production environment

"""

# ==============================================================================
# 9. PERFORMANCE CONSIDERATIONS
# ==============================================================================

"""
QUERY OPTIMIZATION:
  - Indexes on: (property, status), (status, submitted_at)
  - select_related on: hotel, owner, approved_by
  - prefetch_related on: meal_plans, images, policies
  - Pagination for approval queue (20 per page)

CACHING (Future):
  - Cache approved property list (invalidate on approval)
  - Cache meal plans (invalidate on change)
  - Cache pricing by room_type + date

MONITORING:
  - Track approval queue length (SLA: < 48 hours)
  - Monitor booking creation latency (target: < 100ms)
  - Alert on inventory < 5 for popular rooms
  - Track rejection reasons (quality feedback)

"""

# ==============================================================================
# 10. TESTING STRATEGY
# ==============================================================================

"""
UNIT TESTS:
  - PricingService calculations
  - GST rate determination
  - Meal plan pricing
  - Inventory count

INTEGRATION TESTS:
  - Property submission flow
  - Admin approval workflow
  - Booking creation
  - Pricing snapshot storage

E2E TESTS (Playwright):
  - Owner registration → Property submission
  - Admin approval → Property visible
  - User booking → Confirmation
  - All 8 mandatory scenarios

EDGE CASES:
  - Booking on exactly 30 minutes
  - Inventory exactly at 5
  - GST exactly at ₹7500 threshold
  - Meal plan not linked to room
  - Property rejection and resubmission

"""

if __name__ == '__main__':
    print(__doc__)
