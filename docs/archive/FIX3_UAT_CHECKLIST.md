# FIX-3 UAT CHECKLIST

**Project**: GoExplorer Hotel & Bus Booking  
**Phase**: Fix-3: Price Disclosure & Transparency UX  
**Date**: January 21, 2026  
**Status**: Ready for User Testing

---

## PRE-UAT VERIFICATION

### ✅ Development Complete
- [x] All code changes implemented
- [x] All calculations verified
- [x] All templates updated
- [x] Automated tests passing (7/7)
- [x] Verification script passing (all checks)

### ✅ Documentation Complete
- [x] FIX3_PRICE_DISCLOSURE_COMPLETE.md
- [x] FIX3_FINAL_TEST_REPORT.md
- [x] FIX3_IMPLEMENTATION_DETAILS.md
- [x] FIX3_QUICK_REFERENCE.md
- [x] This UAT checklist

### ✅ System Ready
- [x] Django server running on port 8000
- [x] Test data seeded (45 cities, 108 rooms)
- [x] All hotels showing with correct pricing
- [x] All search features working

---

## UAT TEST SCENARIOS

### Scenario 1: Search Results Price Display

**Objective**: Verify that search results show correct pricing format

**Steps**:
1. [ ] Navigate to `http://localhost:8000/hotels/`
2. [ ] Observe hotel search results cards
3. [ ] Look for pricing line on each card

**Expected Results**:
- [ ] Price shows as "From ₹X/night" format
- [ ] Amount is an integer (no decimals)
- [ ] Currency symbol is ₹ (Rupee)
- [ ] No GST or service fees shown
- [ ] Discount badge visible if discount active
- [ ] Format consistent across all hotels

**Actual Results**: ___________________

**Pass**: [ ] **Fail**: [ ] **Comments**: _____________

---

### Scenario 2: Hotel Detail - Base Price & Discount

**Objective**: Verify hotel detail page shows pricing correctly

**Steps**:
1. [ ] Click on any hotel from search results
2. [ ] Scroll down to "Available Room Types" section
3. [ ] Look at the first room card

**Expected Results**:
- [ ] Base price shown clearly (e.g., "₹2,500/night")
- [ ] If discounted, original price has strikethrough
- [ ] If discounted, discounted price shown in green
- [ ] Discount expiry date shown (if applicable)
- [ ] "Taxes & Services" button visible with info icon

**Actual Results**: ___________________

**Pass**: [ ] **Fail**: [ ] **Comments**: _____________

---

### Scenario 3: Taxes & Services Collapsible (Collapsed)

**Objective**: Verify collapsible section is collapsed by default

**Steps**:
1. [ ] Look at room card on hotel detail page
2. [ ] Verify "Taxes & Services" button is visible
3. [ ] Check that tax breakdown area is NOT expanded

**Expected Results**:
- [ ] Button visible with chevron icon (▼)
- [ ] No tax details shown initially
- [ ] Button is clickable
- [ ] Background color of button is subtle (not prominent)

**Actual Results**: ___________________

**Pass**: [ ] **Fail**: [ ] **Comments**: _____________

---

### Scenario 4: Taxes & Services Collapsible (Expanded)

**Objective**: Verify collapsible section expands correctly

**Steps**:
1. [ ] Click the "Taxes & Services" button
2. [ ] Observe the expansion animation
3. [ ] Look at the displayed tax information

**Expected Results**:
- [ ] Button chevron rotates to point upward (▲)
- [ ] Section expands smoothly (animation)
- [ ] Shows "Base: ₹X/night"
- [ ] Shows "Service Fee: ₹X"
- [ ] Shows "Taxes & Services: ₹X" (bold, total amount)
- [ ] Text is readable and properly formatted

**Actual Results**: ___________________

**Pass**: [ ] **Fail**: [ ] **Comments**: _____________

---

### Scenario 5: Taxes & Services Collapsible (Re-collapse)

**Objective**: Verify collapsible section collapses again

**Steps**:
1. [ ] Click the "Taxes & Services" button again (while expanded)
2. [ ] Observe the collapse animation

**Expected Results**:
- [ ] Section collapses smoothly (animation)
- [ ] Chevron rotates back to point downward (▼)
- [ ] Tax details disappear
- [ ] Button appearance returns to normal

**Actual Results**: ___________________

**Pass**: [ ] **Fail**: [ ] **Comments**: _____________

---

### Scenario 6: Booking Form Price Calculation

**Objective**: Verify real-time price calculation as user fills form

**Prerequisites**: User is logged in and email verified

**Steps**:
1. [ ] Click "Proceed to Payment" from hotel detail page
2. [ ] Select a room type from dropdown
3. [ ] Observe price update in "Base:" display
4. [ ] Change check-in date
5. [ ] Change check-out date
6. [ ] Change number of rooms
7. [ ] Select a meal plan

**Expected Results**:
- [ ] Base price updates when room selected
- [ ] Base price updates when dates changed
- [ ] Base price updates when room count changed
- [ ] Taxes & Fees updates in real-time
- [ ] Total price updates correctly
- [ ] Calculations appear instantaneous
- [ ] Alert shows all required fields filled

**Actual Results**: ___________________

**Pass**: [ ] **Fail**: [ ] **Comments**: _____________

---

### Scenario 7: Booking Confirmation - Price Breakdown (Collapsed)

**Objective**: Verify confirmation page shows collapsible tax section

**Steps**:
1. [ ] Complete booking form and proceed
2. [ ] Observe confirmation page
3. [ ] Look at price breakdown section

**Expected Results**:
- [ ] "Base Amount" shows (e.g., "₹5,000")
- [ ] If discount: "Promo Discount" shows (e.g., "-₹500")
- [ ] If discount: "Subtotal" shows (e.g., "₹4,500")
- [ ] "Taxes & Services ▼" shows with chevron
- [ ] Tax details are NOT visible initially
- [ ] "Total Payable" shows (e.g., "₹5,445")
- [ ] All amounts are integers (no decimals)

**Actual Results**: ___________________

**Pass**: [ ] **Fail**: [ ] **Comments**: _____________

---

### Scenario 8: Booking Confirmation - Price Breakdown (Expanded)

**Objective**: Verify tax breakdown expands correctly

**Steps**:
1. [ ] On confirmation page, click "Taxes & Services ▼"
2. [ ] Observe expansion

**Expected Results**:
- [ ] Chevron rotates to ▲
- [ ] Tax details become visible
- [ ] Shows "Service Fee: ₹X"
- [ ] Shows "GST X%: ₹Y"
- [ ] Total matches the "Taxes & Services" amount
- [ ] Indentation shows sub-items (Service Fee, GST)

**Actual Results**: ___________________

**Pass**: [ ] **Fail**: [ ] **Comments**: _____________

---

### Scenario 9: Payment Page - Same Structure

**Objective**: Verify payment page mirrors confirmation page pricing

**Steps**:
1. [ ] Click "Proceed to Payment" from confirmation
2. [ ] Observe payment page structure
3. [ ] Look at price breakdown area

**Expected Results**:
- [ ] Layout is identical to confirmation page
- [ ] Price amounts are identical to confirmation
- [ ] "Taxes & Services" section is collapsible (same behavior)
- [ ] Chevron icon animates on click
- [ ] Tab key navigation works
- [ ] Mobile-responsive layout

**Actual Results**: ___________________

**Pass**: [ ] **Fail**: [ ] **Comments**: _____________

---

### Scenario 10: Mobile Responsiveness

**Objective**: Verify Fix-3 works properly on mobile devices

**Steps**:
1. [ ] Open search page on phone/tablet
2. [ ] View hotel cards (check price display)
3. [ ] Open hotel detail page
4. [ ] Tap "Taxes & Services" button (test touch)
5. [ ] Verify collapsible works smoothly on mobile

**Expected Results**:
- [ ] Price text readable on mobile
- [ ] Discount badge visible and not truncated
- [ ] Room cards stack properly
- [ ] Collapsible button is easily tappable (min 44px height)
- [ ] Chevron icon animates smoothly
- [ ] No horizontal scrolling needed
- [ ] Layout adapts to screen size

**Actual Results**: ___________________

**Pass**: [ ] **Fail**: [ ] **Comments**: _____________

---

## CALCULATION VERIFICATION TESTS

### Test Case 1: Standard Booking Pricing

**Scenario**: 
- Room base price: ₹2,500/night
- Discount: None
- Nights: 2
- Rooms: 1

**Expected Calculation**:
- Base Amount: ₹5,000 (2,500 × 2 × 1)
- Service Fee: ₹250 (5% of 5,000)
- GST (5%): ₹250 (for base < 7,500)
- Taxes & Services: ₹500
- **Total Payable: ₹5,500**

**Actual Calculation**: ___________________

**Pass**: [ ] **Fail**: [ ] **Comments**: _____________

---

### Test Case 2: High-Price Booking with Service Fee Cap

**Scenario**:
- Room base price: ₹10,000/night
- Discount: None
- Nights: 1
- Rooms: 1

**Expected Calculation**:
- Base Amount: ₹10,000
- Service Fee: ₹500 (5% = 500, AT CAP)
- GST (18%): ₹1,800 (for base ≥ 7,500)
- Taxes & Services: ₹2,300
- **Total Payable: ₹12,300**

**Actual Calculation**: ___________________

**Pass**: [ ] **Fail**: [ ] **Comments**: _____________

---

### Test Case 3: Discounted Booking

**Scenario**:
- Room base price: ₹5,000/night
- Discount: 20% (₹1,000 off)
- Effective price: ₹4,000/night
- Nights: 3
- Rooms: 1

**Expected Calculation**:
- Base Amount: ₹12,000 (4,000 × 3 × 1)
- Service Fee: ₹500 (5% of 12,000 = 600, CAPPED at 500)
- GST (18%): ₹2,160 (for base ≥ 7,500)
- Taxes & Services: ₹2,660
- **Total Payable: ₹14,660**

**Actual Calculation**: ___________________

**Pass**: [ ] **Fail**: [ ] **Comments**: _____________

---

## EDGE CASES & ERROR HANDLING

### Test 1: Very Cheap Room

**Scenario**: Room priced at ₹200/night

**Expected**: 
- Service fee calculation works (5% = ₹10)
- Display shows "From ₹200/night"
- Booking proceeds normally

**Result**: [ ] Pass [ ] Fail  
**Comments**: ___________________

---

### Test 2: Very Expensive Room

**Scenario**: Room priced at ₹50,000/night

**Expected**:
- Service fee CAPPED at ₹500 (not ₹2,500)
- Display shows "From ₹50,000/night"
- Collapsible shows correct amounts

**Result**: [ ] Pass [ ] Fail  
**Comments**: ___________________

---

### Test 3: Multi-Room Booking

**Scenario**: Select 5 rooms for booking

**Expected**:
- Base amount multiplies correctly
- Service fee calculated on total
- Display shows "5 Rooms"
- All prices updated

**Result**: [ ] Pass [ ] Fail  
**Comments**: ___________________

---

### Test 4: Long Stay (20+ Nights)

**Scenario**: Booking for 30 nights

**Expected**:
- Base price calculation correct (price × 30)
- Service fee reflects large amount
- GST calculated correctly
- Total updated

**Result**: [ ] Pass [ ] Fail  
**Comments**: ___________________

---

## BROWSER & DEVICE COMPATIBILITY

### Browser Testing

| Browser | Version | Desktop | Mobile | Notes |
|---------|---------|---------|--------|-------|
| Chrome | Latest | [ ] | [ ] | |
| Firefox | Latest | [ ] | [ ] | |
| Safari | Latest | [ ] | [ ] | |
| Edge | Latest | [ ] | [ ] | |

**Issues Found**: ___________________

---

### Device Testing

| Device | OS | Screen Size | Result | Notes |
|--------|----|----|--------|-------|
| Desktop | Windows | 1920×1080 | [ ] | |
| Laptop | Mac | 1440×900 | [ ] | |
| Tablet | iPad | 768×1024 | [ ] | |
| Phone | Android | 375×812 | [ ] | |
| Phone | iOS | 375×812 | [ ] | |

**Issues Found**: ___________________

---

## PERFORMANCE CHECKS

### Load Time
- Hotel search page loads in < 2 seconds: [ ] Yes [ ] No
- Hotel detail page loads in < 2 seconds: [ ] Yes [ ] No
- Confirmation page loads in < 2 seconds: [ ] Yes [ ] No

### Responsiveness
- Price calculations instantaneous: [ ] Yes [ ] No
- Collapsible animation smooth: [ ] Yes [ ] No
- No lag when clicking buttons: [ ] Yes [ ] No

**Performance Issues**: ___________________

---

## DATA INTEGRITY CHECKS

### Verify Consistent Pricing
- [ ] Search result price = minimum room price on detail page
- [ ] Detail page total = confirmation page total
- [ ] Confirmation total = payment page total
- [ ] Receipt shows same amount

### Verify Calculation Accuracy
- [ ] Service fee always ≤ ₹500
- [ ] GST percentage shown correctly
- [ ] No rounding errors visible
- [ ] Discount applied correctly

**Issues Found**: ___________________

---

## ACCESSIBILITY CHECKS

### Keyboard Navigation
- [ ] Tab through collapsible buttons works
- [ ] Enter key expands/collapses sections
- [ ] No keyboard traps
- [ ] Focus indicators visible

### Screen Reader
- [ ] Price text readable
- [ ] Button labels descriptive
- [ ] Collapsible state announced
- [ ] Error messages clear

**Accessibility Issues**: ___________________

---

## FINAL VERIFICATION

### Code Review
- [ ] All code comments present
- [ ] No hardcoded values in code
- [ ] Proper variable naming
- [ ] Code formatting consistent

### Documentation
- [ ] README updated (if needed)
- [ ] Inline code comments present
- [ ] API documentation updated
- [ ] User guide prepared

### Deployment Readiness
- [ ] No database migrations needed
- [ ] Backward compatible
- [ ] No API breaking changes
- [ ] Rollback plan available

---

## SIGN-OFF

### User Acceptance

**I have tested Fix-3 Price Disclosure and verify that:**

- [ ] Search results pricing displays correctly
- [ ] Hotel detail page shows proper pricing
- [ ] Collapsible sections work as expected
- [ ] Calculations are accurate
- [ ] Mobile experience is satisfactory
- [ ] No critical issues found
- [ ] Ready for production deployment

**Tester Name**: _______________________  
**Date**: _______________________  
**Signature**: _______________________

---

### Issues Summary

**Critical Issues**: ___________________  
**High Priority**: ___________________  
**Medium Priority**: ___________________  
**Low Priority**: ___________________

---

## RECOMMENDATIONS

### If All Tests Pass:
✅ Approve Fix-3 for production deployment

### If Issues Found:
- Log all issues in tracker
- Prioritize by severity
- Schedule fixes before deployment
- Re-test after fixes
- Document all changes

---

## NEXT STEPS

1. [ ] Complete all UAT test scenarios
2. [ ] Document any issues found
3. [ ] Get sign-off from product owner
4. [ ] Fix any critical issues
5. [ ] Schedule production deployment
6. [ ] Prepare rollback plan
7. [ ] Monitor production after deployment

---

**This checklist ensures comprehensive testing of Fix-3 Price Disclosure.**

**For questions, refer to FIX3_QUICK_REFERENCE.md or run verify_fix3.py**

---

**Date Prepared**: January 21, 2026  
**Test Coverage**: Comprehensive  
**Ready for UAT**: ✅ YES
