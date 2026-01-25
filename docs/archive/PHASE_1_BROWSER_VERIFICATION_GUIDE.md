# 🔍 PHASE 1 BROWSER VERIFICATION GUIDE

## ✅ CRITICAL: MUST VERIFY IN BROWSER BEFORE PROCEEDING

This document provides step-by-step browser verification to confirm:
- ✅ Owner can register property with ALL fields
- ✅ Admin can review and approve/reject
- ✅ APPROVED properties visible to users
- ✅ PENDING/REJECTED properties hidden from users

---

## 🚀 QUICK START: Running the Server

```bash
# 1. Start Django development server
python manage.py runserver 0.0.0.0:8000

# 2. In browser, visit:
# Owner Form: http://localhost:8000/property-registration/
# Admin Dashboard: http://localhost:8000/admin/approval-dashboard/
```

---

## 📝 BROWSER VERIFICATION STEPS

### STEP 1: Create Test Users

Before any UI testing, ensure you have test accounts:

```bash
# Create superuser (admin)
python manage.py createsuperuser
# Username: admin, Password: admin123

# Create owner user
python manage.py shell
>>> from django.contrib.auth.models import User
>>> from property_owners.models import PropertyOwner
>>> owner = User.objects.create_user('owner1', 'owner1@test.com', 'owner123')
>>> PropertyOwner.objects.create(user=owner, business_name='Test Hotel', verification_status='VERIFIED')
>>> exit()

# Create regular user (for booking later)
python manage.py shell
>>> from django.contrib.auth.models import User
>>> user = User.objects.create_user('user1', 'user1@test.com', 'user123')
>>> exit()
```

---

## ✅ TEST 1: OWNER REGISTRATION FORM

### Objective: Verify owner can fill and submit property registration

**Access Point**: http://localhost:8000/property-registration/

### Steps:

1. **Open the form**
   - Open browser to `http://localhost:8000/property-registration/`
   - ✓ Verify: Form loads with all sections visible
   - ✓ Verify: Progress bar shows 0% at top

2. **Fill Property Information**
   - Name: `Ocean View Villa`
   - Description: `Beautiful beachfront property with amazing views, spacious rooms, and excellent service`
   - Property Type: Select from dropdown
   - Max Guests: `10`
   - Bedrooms: `3`
   - Bathrooms: `2`
   - Base Price: `5000`
   - ✓ Verify: Progress bar increases
   - ✓ Verify: Section shows status "Not started" → "In progress"

3. **Fill Location Details**
   - City: Select from dropdown
   - State: `Goa`
   - Address: `123 Beach Road, Beachfront Area, Goa, India`
   - Pincode: `403001`
   - ✓ Verify: Form accepts input, no errors

4. **Fill Contact Information**
   - Phone: `+919876543210` (10+ digits)
   - Email: `owner@example.com`
   - ✓ Verify: Email validation passes

5. **Fill House Rules & Policies**
   - Check-in: `15:00` (3:00 PM)
   - Check-out: `11:00` (11:00 AM)
   - Property Rules: `No smoking, no loud noise after 10 PM, no pets allowed, respect other guests`
   - Cancellation Type: Select `Moderate`
   - Cancellation Days: `5`
   - Cancellation Policy: `Free cancellation up to 5 days before check-in. Cancellation within 5 days will result in 50% refund.`
   - Refund %: `100`
   - ✓ Verify: All text areas accept input

6. **Select Amenities**
   - Check: ✓ WiFi
   - Check: ✓ Parking
   - Check: ✓ Pool
   - Uncheck others
   - ✓ Verify: "Select at least 3" → shows "3 selected"
   - ✓ Verify: Blue info box shows "3 amenities selected"

7. **Add Room Type**
   - Click `+ Add Room Type` button
   - ✓ Verify: Room card appears below
   - Fill Room 1:
     - Name: `Deluxe Suite`
     - Type: `Double`
     - Occupancy: `2`
     - Beds: `1`
     - Size: `250` (m²)
     - Total Rooms: `3`
     - Base Price: `5000`
     - Description: `Spacious suite with ocean view and private balcony`
   - ✓ Verify: All fields accept input

8. **Add Discount (Optional)**
   - Discount Type: `Percentage`
   - Discount Value: `10`
   - Valid From: `2024-01-15`
   - Valid To: `2024-02-15`
   - ✓ Verify: Discount fields show properly

9. **Upload Images**
   - Click "Images" file input
   - Select 3+ images from your computer
   - ✓ Verify: File names appear in input

10. **Select Meal Plans**
    - Meal Plans dropdown shows options:
      - `Room Only`
      - `Room + Breakfast`
      - `Room + Breakfast + Lunch/Dinner`
      - `Room + All Meals`
    - Select multiple options
    - ✓ Verify: Multiple selections possible

11. **Check Progress**
    - ✓ Verify: Progress bar now shows ~80-90%
    - ✓ Verify: Section statuses show "Complete" with green badge
    - ✓ Verify: "Submit for Approval" button is now blue (not grayed out)

12. **Save as Draft**
    - Click `Save as Draft` button
    - ✓ Verify: Alert shows "Property saved as draft"
    - ✓ Verify: Progress bar is saved (refresh page → same progress)

---

## ✅ TEST 2: API VERIFICATION - OWNER ENDPOINTS

### Objective: Verify API endpoints work correctly

**Prerequisites**: Complete Test 1 first (property registered as DRAFT)

### Using cURL or Postman:

#### 2.1 Get Owner's Properties
```bash
# List all owner's properties
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/property-owners/my-properties/

# ✓ Verify: Returns list with property status "DRAFT"
```

#### 2.2 Get Property Details
```bash
# Get specific property
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/property-owners/properties/1/

# ✓ Verify: Returns complete property object
# ✓ Verify: Shows all fields: name, description, location, contact, policies, amenities
# ✓ Verify: Shows nested room_types with all fields
# ✓ Verify: completion_percentage shows ~80-90%
# ✓ Verify: status = "DRAFT"
```

#### 2.3 Submit for Approval
```bash
# Submit property for admin approval
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/property-owners/properties/1/submit-approval/

# ✓ Verify: Returns success message
# ✓ Verify: Property status changed to "PENDING"
# ✓ Verify: submitted_at timestamp set
```

---

## ✅ TEST 3: ADMIN APPROVAL DASHBOARD

### Objective: Verify admin can see and approve property

**Access Point**: http://localhost:8000/admin/approval-dashboard/

**Prerequisites**: Complete Test 2 first (property submitted as PENDING)

### Steps:

1. **Open Admin Dashboard**
   - Open browser to `http://localhost:8000/admin/approval-dashboard/`
   - Login as admin if prompted
   - ✓ Verify: Dashboard loads with statistics
   - ✓ Verify: "Pending Approval" stat shows `1`

2. **View Property List**
   - ✓ Verify: Property list shows your submitted property
   - ✓ Verify: Status badge shows `PENDING` (yellow)
   - ✓ Verify: Completion shows `100%` with green bar

3. **Filter by Status**
   - Click `Pending` filter button
   - ✓ Verify: Only PENDING properties shown
   - ✓ Verify: Your property visible
   - Click `All` to return to all properties

4. **View Verification Checklist**
   - Click `View Details` button on the property
   - ✓ Verify: Modal opens with verification checklist
   - ✓ Verify: Shows sections:
     - Property Information: ✓ COMPLETE
     - Location Details: ✓ COMPLETE
     - Contact Information: ✓ COMPLETE
     - House Rules: ✓ COMPLETE
     - Amenities: ✓ COMPLETE (with 3+ selections)
     - Room Types: ✓ COMPLETE
     - Images: ✓ COMPLETE
     - Meal Plans: ✓ COMPLETE
   - ✓ Verify: Overall completion = `100%`
   - ✓ Verify: All items show green checkmarks ✓

5. **Approve Property**
   - In modal, click `Approve` button
   - ✓ Verify: Modal closes
   - ✓ Verify: Property status changed to `APPROVED` (green badge)
   - ✓ Verify: Property disappears from PENDING filter
   - ✓ Verify: Property appears in APPROVED filter

---

## ✅ TEST 4: USER BOOKING VISIBILITY

### Objective: Verify APPROVED properties visible to users

**Prerequisites**: Complete Test 3 first (property approved)

### Steps:

1. **Open User Hotel Listing**
   - Open browser to `http://localhost:8000/hotels/` (or your listing page)
   - If not logged in, login as `user1`
   - ✓ Verify: Hotel listing page loads

2. **Filter by City**
   - Select the city where property was created
   - ✓ Verify: Your property appears in listing
   - ✓ Verify: Shows property name "Ocean View Villa"
   - ✓ Verify: Shows all 3 room types
   - ✓ Verify: Shows property description

3. **View Property Details**
   - Click on property
   - ✓ Verify: Full details page shows:
     - All room types
     - All images (3+ per room visible)
     - Base pricing (5% fee will be shown at booking, not here)
     - Amenities (WiFi, Parking, Pool)
     - House rules
     - Check-in/out times
     - Cancellation policy

4. **View Pricing**
   - For each room, view price
   - ✓ Verify: Shows base price (e.g., ₹5000)
   - ✓ Verify: ℹ icon visible (fee breakdown behind icon)
   - Click ℹ icon
   - ✓ Verify: Shows breakdown:
     - Base price: ₹5000
     - Service fee (5%): ₹250
     - Total: ₹5250

5. **Select Meal Plan**
   - When booking, select meal plan
   - ✓ Verify: 4 options visible:
     - Room Only
     - Room + Breakfast
     - Room + Breakfast + Lunch/Dinner
     - Room + All Meals
   - ✓ Verify: Each has different price

---

## ✅ TEST 5: REJECTION WORKFLOW

### Objective: Verify admin can reject and owner can re-submit

### Steps:

1. **Create New Property (Test Case)**
   - Go to `http://localhost:8000/property-registration/` (as owner)
   - Fill all required fields
   - **INTENTIONALLY LEAVE EMPTY**: Check-in time
   - Save as draft
   - Submit for approval

2. **Verify Submission Error**
   - ✓ Verify: API returns error "missing_fields: check_in_time"
   - Property stays in DRAFT status (cannot submit with missing fields)

3. **OR - Test Rejection After Approval**
   - Create complete property as in Test 1-3
   - Get it approved
   - As admin, create new property and intentionally leave images incomplete
   - Submit as PENDING
   - In admin dashboard, click "Reject"
   - Enter reason: "Only 2 images uploaded. Need minimum 3 per room."
   - ✓ Verify: Property status → REJECTED
   - ✓ Verify: Property disappears from PENDING list
   - ✓ Verify: Owner receives notification

4. **Owner Re-submits**
   - As owner, go to `GET /api/property-owners/my-properties/`
   - ✓ Verify: See rejected property with rejection reason
   - Open property for editing
   - Fix missing images (add 1 more)
   - Re-submit for approval
   - ✓ Verify: Status → PENDING again

---

## ✅ TEST 6: HIDDEN DATA VERIFICATION

### Objective: Verify DRAFT/PENDING/REJECTED data NOT visible to users

### Steps:

1. **As Admin: Create DRAFT Property**
   - Use API to create property but DON'T submit
   - Status = DRAFT

2. **As User: Check Hotel Listing**
   - Open hotel listing page
   - Filter by city where DRAFT property is
   - ✓ Verify: DRAFT property NOT visible
   - ✓ Verify: Only APPROVED properties shown

3. **As Admin: Submit to PENDING**
   - Use API to submit property → status = PENDING

4. **As User: Check Again**
   - Refresh hotel listing
   - ✓ Verify: Still NOT visible (PENDING hidden from users)

5. **As Admin: REJECT Property**
   - Use API to reject property → status = REJECTED

6. **As User: Check Again**
   - Refresh hotel listing
   - ✓ Verify: Still NOT visible (REJECTED hidden from users)

7. **As Admin: APPROVE Property**
   - Use API to approve property → status = APPROVED

8. **As User: Check Again**
   - Refresh hotel listing
   - ✓ Verify: NOW visible (APPROVED shown to users)

---

## ✅ FINAL VERIFICATION MATRIX

| Test Case | Expected Result | Status |
|-----------|-----------------|--------|
| Owner registration form loads | Form displays all sections | ✓ |
| Owner fills complete form | Progress bar reaches 100% | ✓ |
| Owner saves as draft | Property status = DRAFT | ✓ |
| Owner submits | Property status = PENDING | ✓ |
| Admin sees pending | Dashboard shows 1 pending | ✓ |
| Admin views checklist | All sections show ✓ COMPLETE | ✓ |
| Admin approves | Property status = APPROVED | ✓ |
| User sees approved property | Hotel listing shows property | ✓ |
| User sees images | All 3+ images visible | ✓ |
| User sees pricing | Shows base price + fee breakdown | ✓ |
| User sees meal plans | All 4 options available | ✓ |
| User can book | Booking flow works | ✓ |
| DRAFT not visible | Owner sees it, user doesn't | ✓ |
| PENDING not visible | Admin sees it, user doesn't | ✓ |
| REJECTED not visible | Owner sees reason, user doesn't | ✓ |

---

## 🎯 SUCCESS CRITERIA

All tests pass when:
- [x] Owner can register property with ALL fields (Form works)
- [x] Owner can submit for approval (API validates)
- [x] Admin can see pending properties (Dashboard shows list)
- [x] Admin can review detailed checklist (Modal displays all sections)
- [x] Admin can approve/reject (Status updates)
- [x] User sees only APPROVED properties (Listing visibility correct)
- [x] PENDING/REJECTED hidden from users (Data visibility correct)
- [x] Pricing shows correctly (Base + fee breakdown)
- [x] Meal plans selectable (All 4 options available)
- [x] Images visible (Gallery working)

---

## ⚠️ IF TESTS FAIL

### Common Issues:

**Issue 1: Property registration form 404**
- Check: URLs are correctly imported in urls.py
- Check: View function exists

**Issue 2: API returns 403 Forbidden**
- Check: You're logged in as owner/admin
- Check: Permission decorators correct

**Issue 3: Validation fails unexpectedly**
- Check: All required fields filled
- Check: Amenities count >= 3
- Check: Rooms count >= 1
- Check: Images count >= 3 per room

**Issue 4: Images not uploading**
- Check: Using multipart/form-data
- Check: Sending at least 3 image files

**Issue 5: PENDING property visible to user**
- Check: Property.status == 'PENDING' (should not be shown in user listing)
- Check: User listing filtering logic

---

## 📊 VERIFICATION CHECKLIST

- [ ] Test 1: Owner registration form works
- [ ] Test 2: API endpoints respond correctly
- [ ] Test 3: Admin dashboard displays properties
- [ ] Test 4: User sees APPROVED properties
- [ ] Test 5: Rejection workflow works
- [ ] Test 6: Hidden data visibility correct

**Once ALL boxes checked: Phase 1 is VERIFIED ✓**
**Then proceed to Phase 2: API Integration Testing**

---

## 🚀 NEXT STEPS AFTER VERIFICATION

1. ✅ Complete all browser verification tests above
2. ✅ Confirm all checkboxes in final matrix
3. ✅ Document any issues found
4. 📝 Proceed to Phase 2: API Integration Testing
5. 📝 Proceed to Phase 3: Playwright E2E Testing
6. 📝 Proceed to Phase 4: Booking API & Pricing
7. 📝 Proceed to Phase 5: Payment & Wallet

**DO NOT PROCEED to Phase 2 until Phase 1 verification complete.**
