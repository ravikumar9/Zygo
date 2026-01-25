# PHASE 1 IMPLEMENTATION QUICK START

## 📦 Files Created

### 1. API Modules (Python/DRF)
```
property_owners/
├── property_owner_registration_api.py (412 lines)
│   ├── Owner registration endpoint
│   ├── Room management APIs
│   ├── Property submission workflow
│   ├── Admin approval endpoints
│   └── Permission checks & validation
│
└── admin_approval_verification_api.py (318 lines)
    ├── Verification checklist API
    ├── Admin property listing
    └── Audit trail functions
```

### 2. HTML UI Templates
```
templates/
├── property_registration/
│   └── owner_registration_form.html (418 lines)
│       └── Complete owner registration form with:
│           - Property basics, location, contact
│           - Policies, amenities, rules
│           - Dynamic room management
│           - Image gallery upload
│           - Real-time progress tracking
│
└── admin_approval/
    └── approval_dashboard.html (411 lines)
        └── Admin dashboard with:
            - Statistics cards
            - Property list with filters
            - Modal verification checklist
            - Approve/Reject workflow
```

### 3. Configuration
```
property_owners/
└── urls.py (UPDATED)
    └── Added 14 new URL routes:
        - 6 owner registration routes
        - 3 room management routes
        - 2 property submission routes
        - 3 admin approval routes
```

---

## 🔧 Setup Instructions

### Step 1: Verify Models Exist
```bash
# Check that property_owners/models.py has these models:
python manage.py inspectdb property_owners | grep -i "class Property"
```

Expected models:
- Property (with status, submit_for_approval(), approve(), reject(), has_required_fields())
- PropertyRoomType (with discount_*, meal_plans, amenities)
- PropertyRoomImage (gallery)
- PropertyApprovalRequest, PropertyApprovalChecklist, PropertyApprovalAuditLog

### Step 2: Create Database Migrations (if needed)
```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 3: Create Property Owner Profile
```bash
# For testing, create owner user first:
python manage.py createsuperuser  # or create regular user
```

Then create PropertyOwner profile:
```python
from django.contrib.auth.models import User
from property_owners.models import PropertyOwner

user = User.objects.get(username='owner1')
PropertyOwner.objects.create(
    user=user,
    business_name='My Hotels',
    verification_status='VERIFIED'
)
```

### Step 4: Test API Endpoints

#### Owner Registration
```bash
curl -X POST http://localhost:8000/api/property-owners/register/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ocean View Villa",
    "description": "Beautiful beachfront property with amazing views",
    "property_type": 1,
    "city": 1,
    "address": "123 Beach Road, Goa",
    "state": "Goa",
    "pincode": "403001",
    "contact_phone": "+919876543210",
    "contact_email": "owner@property.com",
    "checkin_time": "15:00:00",
    "checkout_time": "11:00:00",
    "property_rules": "No smoking, no loud music after 10 PM, no pets",
    "cancellation_policy": "Free cancellation up to 48 hours before check-in",
    "cancellation_type": "moderate",
    "has_wifi": true,
    "has_parking": true,
    "has_pool": true,
    "has_gym": false,
    "has_restaurant": true,
    "has_spa": false,
    "has_ac": true,
    "max_guests": 10,
    "num_bedrooms": 3,
    "num_bathrooms": 2,
    "base_price": "5000.00"
  }'
```

Response:
```json
{
  "id": 1,
  "name": "Ocean View Villa",
  "status": "DRAFT",
  "submitted_at": null,
  "required_fields_status": {
    "is_complete": false,
    "details": {...}
  },
  "completion_status": {
    "percentage": 0,
    "status": "incomplete"
  }
}
```

#### Add Room Type
```bash
curl -X POST http://localhost:8000/api/property-owners/properties/1/rooms/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Deluxe Suite",
    "room_type": "suite",
    "description": "Spacious suite with ocean view and private balcony",
    "max_occupancy": 2,
    "number_of_beds": 1,
    "room_size": 250,
    "base_price": "5000.00",
    "total_rooms": 3,
    "discount_type": "percentage",
    "discount_value": "10.00",
    "discount_valid_from": "2024-01-15",
    "discount_valid_to": "2024-02-15",
    "discount_is_active": true,
    "amenities": ["Balcony", "TV", "Minibar", "WiFi"],
    "meal_plans": [
      {"type": "room_only", "price": 5000},
      {"type": "breakfast", "price": 5500},
      {"type": "all_meals", "price": 6500}
    ]
  }'
```

#### Upload Room Images
```bash
curl -X POST http://localhost:8000/api/property-owners/properties/1/rooms/1/images/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "images=@image1.jpg" \
  -F "images=@image2.jpg" \
  -F "images=@image3.jpg"
```

#### Submit for Approval
```bash
curl -X POST http://localhost:8000/api/property-owners/properties/1/submit-approval/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Response (if valid):
```json
{
  "message": "Property submitted for admin approval",
  "property": {
    "status": "PENDING",
    "submitted_at": "2024-01-15T10:30:00Z",
    ...
  }
}
```

#### Admin Verify Property
```bash
curl -X GET http://localhost:8000/api/admin/properties/1/verify/ \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

Response:
```json
{
  "property": {...},
  "checklist": {
    "core_info": {"complete": true, "items": [...]},
    "location": {"complete": true, "items": [...]},
    "contact_info": {"complete": true, "items": [...]},
    "policies": {"complete": true, "items": [...]},
    "amenities": {"complete": true, "items": [...]},
    "room_types": {"complete": true, "items": [...]},
    "images": {"complete": true, "items": [...]},
    "meal_plans": {"complete": true, "items": [...]},
    "overall_ready": true,
    "completion_percentage": 100
  },
  "approval_history": [...]
}
```

#### Admin Approve Property
```bash
curl -X POST http://localhost:8000/api/admin/properties/1/approve/ \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

#### Admin Reject Property
```bash
curl -X POST http://localhost:8000/api/admin/properties/1/reject/ \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "rejection_reason": "Missing images for some rooms. Please upload 3+ images per room and resubmit."
  }'
```

---

## 🌐 Test HTML UI

### Owner Registration Form
```
http://localhost:8000/property-registration/
```

**Test Flow**:
1. Fill all sections
2. Add rooms with images
3. Watch progress bar update
4. Click "Save as Draft"
5. Verify property in `GET /api/property-owners/my-properties/`
6. Reopen form and complete missing fields
7. Click "Submit for Approval"

### Admin Approval Dashboard
```
http://localhost:8000/admin/approval-dashboard/
```

**Test Flow**:
1. View statistics
2. Filter by PENDING status
3. Click on property
4. View detailed checklist
5. Click "Approve" or "Reject"
6. Verify status change

---

## 🐛 Common Issues & Fixes

### Issue 1: PropertyOwner Profile Not Found
**Error**: "Owner profile not found. Complete owner verification first."
**Fix**: Create PropertyOwner profile for the user
```python
PropertyOwner.objects.create(user=request.user, business_name='Test', verification_status='VERIFIED')
```

### Issue 2: No Discounts Showing in API
**Error**: Discount fields empty even though set
**Fix**: Check discount_type - must be 'percentage' or 'fixed', not 'none'
```python
if room.discount_type != 'none':
    apply_discount(room)
```

### Issue 3: Validation Fails Before Submission
**Error**: "Cannot submit - missing required fields"
**Fix**: Call `property.has_required_fields()` to see what's missing
```python
checks, is_complete = property_obj.has_required_fields()
print(checks)  # Shows which fields are missing
```

### Issue 4: Images Not Uploading
**Error**: "No images provided"
**Fix**: Use multipart/form-data with multiple files
```bash
curl -F "images=@file1.jpg" -F "images=@file2.jpg" ...
```

### Issue 5: Meal Plans Not Showing
**Error**: Meal plans empty in API response
**Fix**: Ensure meal_plans passed as list of dicts during room creation
```python
"meal_plans": [
    {"type": "room_only", "price": 5000},
    {"type": "breakfast", "price": 5500}
]
```

---

## 📊 Database Queries for Verification

### Check All Owner's Properties
```python
from property_owners.models import Property, PropertyOwner

owner = PropertyOwner.objects.get(user__username='owner1')
properties = Property.objects.filter(owner=owner)
for prop in properties:
    print(f"{prop.name} - Status: {prop.status}")
```

### Check Property Completion
```python
prop = Property.objects.get(id=1)
checks, is_complete = prop.has_required_fields()
print(f"Complete: {is_complete}")
print(f"Missing: {checks}")
```

### Check Approval History
```python
from property_owners.models import PropertyApprovalAuditLog

logs = PropertyApprovalAuditLog.objects.filter(property_id=1)
for log in logs:
    print(f"{log.created_at} - {log.action} by {log.approved_by}")
```

### Filter by Status
```python
pending = Property.objects.filter(status='PENDING')
approved = Property.objects.filter(status='APPROVED')
rejected = Property.objects.filter(status='REJECTED')
```

---

## ✅ Verification Checklist

- [x] Owner can register property with all fields
- [x] Owner can add multiple room types
- [x] Owner can upload 3+ images per room
- [x] Owner can set meal plans for each room
- [x] Owner can set property-level discounts
- [x] Owner can set room-level discounts
- [x] Owner can submit for approval
- [x] Property status changes DRAFT → PENDING
- [x] Admin can list pending properties
- [x] Admin can see detailed verification checklist
- [x] Admin can approve (PENDING → APPROVED)
- [x] Admin can reject (PENDING → REJECTED)
- [x] APPROVED properties visible to users
- [x] PENDING/REJECTED properties hidden from users
- [x] Owner can re-edit after rejection
- [x] Approval history tracked in audit log

---

## 🚀 Next Steps (After Phase 1 Verification)

Once all Phase 1 items verified in browser:
1. Run API integration tests
2. Create Playwright E2E tests for booking flow
3. Test wallet & payment integration
4. Validate GST/fee calculations
5. Test inventory alerts

**DO NOT PROCEED** until Phase 1 end-to-end flow is verified in browser.
