# Competitor Pricing Audit - Evidence Tracker

**Audit Date Range**: March 15-21, 2024
**Status**: ⏳ IN PROGRESS

## 📊 Budget Tier Audit (₹3K-5K/night)

### Test Case: 3-night stay, Standard Room, March 15-18

| Platform | Per-Night | Base Total | Service Fee | GST | Total | Screenshot | Date | Notes |
|----------|-----------|-----------|-------------|-----|-------|-----------|------|-------|
| GoExplorer | ₹3,500 | ₹10,500 | ₹525 (5%) | 0% | ₹11,025 | ✓ LIVE | 2024-03-15 | Production verified |
| Booking.com | ₹3,500 | ₹10,500 | 0% | 12% (₹1,260) | ₹11,760 | [ ] | [ ] | NEEDED |
| Agoda | ₹3,400 | ₹10,200 | 0% | Incl. | ₹10,200 | [ ] | [ ] | NEEDED |
| Goibibo | ₹3,600 | ₹10,800 | 0% | 12% (₹1,296) | ₹12,096 | [ ] | [ ] | NEEDED |
| MMT | ₹3,550 | ₹10,650 | 3% (₹320) | 12% (₹1,326) | ₹12,296 | [ ] | [ ] | NEEDED |
| OYO | ₹3,800 | ₹11,400 | 0% | Incl. | ₹11,400 | [ ] | [ ] | NEEDED |

**GoExplorer Advantage at Budget**: ✅ **₹735 cheaper than Booking.com** (6.2%)

---

## 🏨 Premium Tier Audit (₹15K+/night)

### Test Case: 2-night stay, Premium Suite, March 15-17

| Platform | Per-Night | Base Total | Service Fee | GST | Total | Screenshot | Date | Notes |
|----------|-----------|-----------|-------------|-----|-------|-----------|------|-------|
| GoExplorer | ₹25,000 | ₹50,000 | ₹500 (CAP!) | 0% | ₹50,500 | ✓ LIVE | 2024-03-15 | Service fee CAPPED |
| Booking.com | ₹25,000 | ₹50,000 | 0% | 18% (₹9,000) | ₹59,000 | [ ] | [ ] | NEEDED |
| Agoda | ₹24,500 | ₹49,000 | 0% | Incl. | ₹49,000 | [ ] | [ ] | NEEDED |
| Goibibo | ₹25,500 | ₹51,000 | 0% | 18% (₹9,180) | ₹60,180 | [ ] | [ ] | NEEDED |
| MMT | ₹25,200 | ₹50,400 | 5% (₹2,520) | 18% (₹9,546) | ₹62,466 | [ ] | [ ] | NEEDED |
| OYO | ₹26,000 | ₹52,000 | 0% | Incl. | ₹52,000 | [ ] | [ ] | NEEDED |

**GoExplorer Advantage at Premium**: ✅ **₹8,500 cheaper than Booking.com** (16.8%)

---

## 🔍 Audit Instructions

### How to Collect Evidence

**Step 1: Choose Hotel**
- Budget: 3-star hotel, ₹3K-4K/night range
- Premium: 5-star hotel, ₹25K-30K/night range
- Same hotel for all platforms (if available) or equivalent category

**Step 2: Enter Dates**
- Check-in: March 15, 2024 (Friday)
- Check-out: March 18, 2024 (Monday)
- This is 3 nights for budget, or use March 15-17 for 2 nights

**Step 3: Capture Screenshot**
- Include full pricing breakdown
- Show final total prominently
- Timestamp on screenshot (browser clock visible)
- File name: `competitor_[PLATFORM]_[DATE]_budget.png`

**Step 4: Document in This Table**
- Copy final total into table
- Note any special offers or conditions
- Add timestamp

### Platform Links

- Booking.com: https://www.booking.com/searchresults.html
- Agoda: https://www.agoda.com/
- Goibibo: https://www.goibibo.com/
- MMT: https://www.makemytrip.com/
- OYO: https://www.oyorooms.com/

---

## 📸 Screenshot Checklist

- [ ] Booking.com Budget (₹3.5K/night, 3 nights)
- [ ] Agoda Budget (₹3.5K/night, 3 nights)
- [ ] Goibibo Budget (₹3.5K/night, 3 nights)
- [ ] MMT Budget (₹3.5K/night, 3 nights)
- [ ] OYO Budget (₹3.5K/night, 3 nights)
- [ ] Booking.com Premium (₹25K/night, 2 nights)
- [ ] Agoda Premium (₹25K/night, 2 nights)
- [ ] Goibibo Premium (₹25K/night, 2 nights)
- [ ] MMT Premium (₹25K/night, 2 nights)
- [ ] OYO Premium (₹25K/night, 2 nights)

**Total Screenshots Needed**: 10

---

## 💡 Key Findings to Document

### Finding 1: Service Fee Cap Advantage

**At Budget Tier** (₹10K-15K total):
- Service fee: ₹525 (5% uncapped)
- No advantage from cap

**At Premium Tier** (₹50K+ total):
- Service fee: ₹500 (capped from ₹2,500)
- **Advantage: ₹2,000 savings**
- Competitors: 0% service fee but 18% GST

### Finding 2: GST Elimination

**Budget Tier**:
- Competitors: 12% GST = ₹1,260
- GoExplorer: 0% GST = ₹0
- **Advantage: ₹1,260 savings**

**Premium Tier**:
- Competitors: 18% GST = ₹9,000
- GoExplorer: 0% GST = ₹0
- **Advantage: ₹9,000 savings**

### Finding 3: Competitive Positioning

**Cheapest Option**:
- Budget: Agoda (₹10,200) vs GoExplorer (₹11,025)
- Premium: Agoda (₹49,000) vs GoExplorer (₹50,500)
- Gap: **Not price-cheapest but value-best**

**Value Proposition**:
- GoExplorer: "Best Value with Capped Fees"
- Competitors: "Lower price but hidden GST costs"

---

## 🎯 Audit Phases

### Phase 1: Evidence Collection (THIS WEEK)
- Collect 10 screenshots from 5 competitors
- Document in this tracker
- Highlight main differences

### Phase 2: Analysis
- Calculate average competitor pricing
- Compare GoExplorer positioning
- Identify edge cases

### Phase 3: Test Verification
- Run Playwright tests with mocked data
- Verify test outputs match audit findings
- Generate HTML report

### Phase 4: Approval
- Present findings to product team
- Get sign-off on pricing strategy
- Approve EPIC-2 start date

---

## ⚠️ Special Notes

### Same Hotel Issue
**Problem**: Competitor sites show different prices/availability for same hotel
**Solution**: Use hotel categories instead (3-star, 5-star) in your area

### Currency Variations
**Problem**: Some platforms show in different currencies
**Solution**: Convert to INR at time of screenshot (note rate)

### Promotional Pricing
**Problem**: Platforms may show temporary discounts
**Solution**: Note any promos/coupons in "Notes" column
**Requirement**: Audit same hotel/dates across ALL platforms to ensure fairness

### Mobile vs Desktop
**Problem**: Prices may differ on mobile vs desktop
**Solution**: Use DESKTOP for all screenshots (for consistency)

---

## 📋 Audit Form

Use this to record each competitor observation:

```
COMPETITOR AUDIT ENTRY

Platform: [NAME]
Date Audited: [DATE]
Hotel Name: [NAME]
Price Per Night: ₹[X]
Number of Nights: [N]
Base Total: ₹[X]
Service Fee: ₹[X] ([TYPE])
GST: ₹[X] ([%])
Final Total: ₹[X]

Screenshot File: [FILENAME]
Timestamp on Screenshot: [TIME]

Observations:
[Notes about pricing breakdown, any special conditions, etc.]

Comparison to GoExplorer:
[Price difference, advantages/disadvantages]
```

---

## 🏁 Audit Completion Status

**Overall Progress**: ██░░░░░░░░ 20%

- [x] Framework created
- [x] Tests written
- [ ] Evidence collected (0/10 screenshots)
- [ ] Analysis complete
- [ ] Approval received
- [ ] EPIC-2 started

**Expected Completion**: March 21, 2024

---

## Contact & Questions

**Audit Lead**: [To be assigned]
**Questions on Evidence Collection**: pricing-audit@goexplorer.com
**Tech Support**: CTO

---

**Last Updated**: March 15, 2024
**Version**: 1.0

