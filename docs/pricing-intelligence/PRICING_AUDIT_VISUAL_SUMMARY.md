# PRICING AUDIT PHASE - VISUAL SUMMARY & ROADMAP

---

## 🎯 The Big Picture

```
┌─────────────────────────────────────────────────────────────────┐
│         PRICING AUDIT PHASE (March 15-21, 2024)                 │
│                                                                 │
│  Current Reality:                                               │
│  ✓ Pricing works (we hope)                                      │
│  ✓ Tests exist (partially)                                      │
│  ? Are we competitive? (unknown)                                │
│  ? Any edge case bugs? (unmapped)                               │
│  ? Ready for EPIC-2? (NO - audit first)                         │
│                                                                 │
│  Audit Goal:                                                    │
│  ✅ Document current pricing path                               │
│  ✅ Verify no bugs exist                                        │
│  ✅ Confirm competitive advantage                               │
│  ✅ Test all edge cases                                         │
│  ✅ GET APPROVAL FOR EPIC-2                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Audit Framework (7 Days)

```
WEEK VIEW
┌──────┬──────┬──────┬──────┬──────┬──────┬──────┐
│ MON  │ TUE  │ WED  │ THU  │ FRI  │ SAT  │ SUN  │
│ 15   │ 16   │ 17   │ 18   │ 19   │ 20   │ 21   │
├──────┼──────┼──────┼──────┼──────┼──────┼──────┤
│START │WORK  │WORK  │DUE   │TESTS │APP'V │SIGN  │
│✅    │⏳    │⏳    │✅    │✅    │✅    │✅    │
│      │CODE  │CODE  │SHOTS │CODE  │TEAM  │FINAL │
│      │TESTS │FLAG  │TEST  │DONE  │MTNG  │EPIC2 │
└──────┴──────┴──────┴──────┴──────┴──────┴──────┘

PHASE VIEW
Phase 1: Planning & Setup (MON 15)           ✅ COMPLETE
    └─ All documents written
    └─ All tests created
    └─ Teams assigned

Phase 2: Code Review & Testing (TUE-WED 16-17)  ⏳ IN PROGRESS
    └─ Backend: pricing_service.py review
    └─ Backend: Run playwright tests
    └─ Flag any issues

Phase 3: Evidence Collection (WED-THU 17-18)    ⏳ IN PROGRESS
    └─ QA: Collect 10 competitor screenshots
    └─ QA: Document findings
    └─ QA: Run tests

Phase 4: Analysis & Review (THU-FRI 18-19)      ⏳ PENDING
    └─ All: Review findings
    └─ Product: Decide on 4 red flags
    └─ Engineering: Approve code

Phase 5: Final Approval (SAT-SUN 20-21)         ⏳ PENDING
    └─ Team: Approval meeting
    └─ CTO: Final sign-off
    └─ Product: Ready for EPIC-2

POST-AUDIT: EPIC-2 Starts (MON 24)              ⏳ PENDING
    └─ Inventory Locking development
    └─ Full confidence in scaling
```

---

## 👥 Team Roles & Responsibilities

```
┌─────────────────────────────────────────────────────────┐
│ AUDIT LEAD (Manager/CTO)                                │
├─────────────────────────────────────────────────────────┤
│ Responsibilities:                                        │
│ • Coordinate all teams                                  │
│ • Daily 5-min standups                                  │
│ • Escalate blockers                                     │
│ • Final sign-off on March 21                            │
│                                                         │
│ Time Commitment: 1-2 hours                              │
│ Critical Dates: Daily + March 21 sign-off              │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ BACKEND ENGINEER                                        │
├─────────────────────────────────────────────────────────┤
│ Responsibilities:                                        │
│ • Review pricing_service.py code                        │
│ • Run 3 Playwright test suites                          │
│ • Document any issues/bugs                              │
│ • Fix any regressions found                             │
│ • Report: "All tests passing" by Mar 19                │
│                                                         │
│ Time Commitment: 1-2 hours                              │
│ Critical Dates: Code review by Mar 17                   │
│               Tests passing by Mar 19                   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ QA / TEST ENGINEER                                      │
├─────────────────────────────────────────────────────────┤
│ Responsibilities:                                        │
│ • Collect 10 competitor screenshots                     │
│ • Document in COMPETITOR_AUDIT_TRACKER.md              │
│ • Run Playwright tests locally                          │
│ • Verify test results                                   │
│ • Report: "10 screenshots collected" by Mar 18         │
│                                                         │
│ Time Commitment: 3-4 hours                              │
│ Critical Dates: Screenshots by Mar 18                   │
│               Tests verified by Mar 19                  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ PRODUCT MANAGER                                         │
├─────────────────────────────────────────────────────────┤
│ Responsibilities:                                        │
│ • Review competitive analysis                           │
│ • Decide on 4 red flags                                 │
│ • Approve competitive positioning                       │
│ • Approve go-to-market messaging                        │
│ • Report: "Red flags decided" by Mar 20                │
│                                                         │
│ Time Commitment: 1-2 hours                              │
│ Critical Dates: Red flags by Mar 20                     │
│               Approval by Mar 21                        │
└─────────────────────────────────────────────────────────┘
```

---

## 📈 Pricing Analysis at a Glance

```
BUDGET TIER (₹3K-5K/night, 3 nights)

GoExplorer
│
├─ Room: ████████████████ ₹10,500 (95%)
├─ Fee:  ██ ₹525 (5%)
└─ GST:  ░░ ₹0
   Total: ₹11,025 ✅ ADVANTAGE

Booking.com
│
├─ Room: ████████████████ ₹10,500 (89%)
├─ Fee:  ░░ ₹0
└─ GST:  ██ ₹1,260 (11%)
   Total: ₹11,760 ❌ +₹735

Agoda
│
├─ Room: ████████████████ ₹10,200 (100%)
├─ Fee:  ░░ ₹0
└─ GST:  ░░ ₹0 [included]
   Total: ₹10,200 ✓ -₹825 (cheapest)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cheapest: Agoda (₹10,200)
Best Value: GoExplorer (transparent + wallet)
Most Expensive: MMT (₹12,296)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


PREMIUM TIER (₹25K/night, 2 nights)

GoExplorer
│
├─ Room: ██████████████ ₹50,000 (99%)
├─ Fee:  █ ₹500 (CAP!) (1%)
└─ GST:  ░░ ₹0
   Total: ₹50,500 ✅ HUGE ADVANTAGE

Booking.com
│
├─ Room: ██████████████ ₹50,000 (85%)
├─ Fee:  ░░ ₹0
└─ GST:  ████ ₹9,000 (15%)
   Total: ₹59,000 ❌ +₹8,500

MMT
│
├─ Room: ██████████████ ₹50,400 (80%)
├─ Fee:  ██ ₹2,520 (4%)
└─ GST:  ████ ₹9,546 (16%)
   Total: ₹62,466 ❌ +₹11,966

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cheapest: Agoda (₹49,000)
Best Value: GoExplorer (saves ₹9K vs Booking on GST)
Most Expensive: MMT (₹62,466)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🚨 Critical Red Flags (Decision Tree)

```
┌──────────────────────────────────────────────────────────┐
│ RED FLAG 1: Multi-room Fee Cap Application                │
├──────────────────────────────────────────────────────────┤
│ Question: Does ₹500 cap apply per-room or per-booking?   │
│                                                           │
│ Example: 3 rooms × ₹20K/night = ₹60K base               │
│          5% fee = ₹3,000 uncapped                        │
│                                                           │
│          Option A: Cap per room = ₹500 × 3 = ₹1,500     │
│          Option B: Cap total = ₹500 (CORRECT)            │
│                                                           │
│ Impact: Option A overcharges customer ₹1,000             │
│ Investigation: Backend code review                       │
│ Decision By: March 17                                    │
│ Owner: Backend Engineer                                  │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ RED FLAG 2: Long Stay Incentive Misalignment              │
├──────────────────────────────────────────────────────────┤
│ Problem: 30-night stay has only 0.17% effective fee      │
│                                                           │
│ Example: 30 nights × ₹5K = ₹150K                        │
│          5% fee = ₹7,500 uncapped                        │
│          But capped = ₹500 only                          │
│          Effective rate: 0.33% (too low)                 │
│                                                           │
│ Issue: Customers incentivized for ultra-long stays      │
│        (not aligned with business goals)                 │
│                                                           │
│ Options:                                                  │
│  A) Keep as-is (generous to loyal customers)            │
│  B) Tier the cap (₹500 per 7 days = 3.3% rate)          │
│  C) Different strategy for long-stays                    │
│                                                           │
│ Decision By: March 20                                    │
│ Owner: Product Manager                                   │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ RED FLAG 3: Promo Code Fee Calculation                    │
├──────────────────────────────────────────────────────────┤
│ Question: Is fee calculated on original or               │
│           discounted price?                              │
│                                                           │
│ Example: Booking ₹50K with 10% promo = ₹45K             │
│                                                           │
│          WRONG: Fee on ₹50K = ₹500 + ₹45K = ₹45,500    │
│                 (customer overpays ₹500)                 │
│                                                           │
│          RIGHT: Fee on ₹45K = ₹225 + ₹45K = ₹45,225    │
│                 (fee scales with discount)               │
│                                                           │
│ Impact: Customer overcharge of ₹275 (5% of discount)    │
│ Investigation: Code audit of promo handler               │
│ Decision By: March 18                                    │
│ Owner: Backend Engineer                                  │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ RED FLAG 4: Group Booking Wholesale Pricing               │
├──────────────────────────────────────────────────────────┤
│ Problem: Large group bookings get ₹500 fee (too low?)    │
│                                                           │
│ Example: 10 rooms × ₹10K/night × 3 nights = ₹300K      │
│          5% fee = ₹15,000 uncapped                       │
│          But capped = ₹500 only                          │
│          Effective rate: 0.17% (huge discount!)          │
│                                                           │
│ Issue: Corporate bulk bookings may exploit this          │
│        We're undercharging for high-value orders         │
│                                                           │
│ Options:                                                  │
│  A) Keep as-is (attract wholesale business)             │
│  B) Set minimum fee (e.g., ₹2,500 for ₹300K+)           │
│  C) Implement wholesale tier with custom rates           │
│                                                           │
│ Decision By: March 20                                    │
│ Owner: Product Manager                                   │
└──────────────────────────────────────────────────────────┘
```

---

## 📋 Approval Checklist (Visual)

```
APPROVAL GATES

┌─────────────────────────────────────┐
│ PHASE 1: CODE REVIEW ✅ OWNER: BACKEND
├─────────────────────────────────────┤
│ [ ] pricing_service.py reviewed      │
│ [ ] Fee cap logic verified           │
│ [ ] GST disabled verified            │
│ [ ] No bugs found                    │
│                                      │
│ DUE: March 19                        │
│ STATUS: ⏳ In Progress               │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│ PHASE 2: TESTS PASSING ✅ OWNER: QA
├─────────────────────────────────────┤
│ [ ] Budget tests passing             │
│ [ ] Premium tests passing            │
│ [ ] Edge case tests passing          │
│ [ ] No failing tests                 │
│                                      │
│ DUE: March 19                        │
│ STATUS: ⏳ In Progress               │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│ PHASE 3: EVIDENCE ✅ OWNER: QA
├─────────────────────────────────────┤
│ [ ] 10 screenshots collected         │
│ [ ] Budget tier 5 screens ✓          │
│ [ ] Premium tier 5 screens ✓         │
│ [ ] Documented in tracker            │
│                                      │
│ DUE: March 18                        │
│ STATUS: ⏳ In Progress               │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│ PHASE 4: RED FLAGS ✅ OWNER: ALL
├─────────────────────────────────────┤
│ [ ] Flag 1 investigated (multi-room) │
│ [ ] Flag 2 decided (long stay)       │
│ [ ] Flag 3 verified (promo code)     │
│ [ ] Flag 4 decided (group booking)   │
│                                      │
│ DUE: March 20                        │
│ STATUS: ⏳ Pending                   │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│ PHASE 5: APPROVALS ✅ OWNER: LEADS
├─────────────────────────────────────┤
│ [ ] Product approves positioning     │
│ [ ] Engineering approves code        │
│ [ ] QA approves tests                │
│ [ ] CTO final sign-off               │
│                                      │
│ DUE: March 21                        │
│ STATUS: ⏳ Pending                   │
└─────────────────────────────────────┘
           ↓
        ✅ EPIC-2 APPROVED!
```

---

## 🎯 Success Metrics

```
METRIC                          TARGET          STATUS
─────────────────────────────────────────────────────────
Documents Read                  All 9           ⏳ In Progress
Tests Created                   3 files         ✅ Complete
Test Scenarios                  15+             ✅ Complete
Competitor Platforms            5               ⏳ In Progress
Screenshots Collected           10              ⏳ In Progress
Red Flags Investigated          4               ⏳ Pending
Red Flags Decided               4               ⏳ Pending
Code Issues Found               TBD             ⏳ Pending
Code Issues Fixed               TBD             ⏳ Pending
All Tests Passing               100%            ⏳ Pending
Competitive Analysis            Done            ⏳ Pending
Product Approval                Yes             ⏳ Pending
Engineering Approval            Yes             ⏳ Pending
QA Approval                     Yes             ⏳ Pending
CTO Sign-off                    Yes             ⏳ Pending

SUCCESS DEFINITION: All metrics green + all approvals signed
```

---

## 🗺️ Document Navigation (Visual)

```
YOU ARE HERE → README_PRICING_AUDIT.md
               (Start reading here!)
                        ↓
          Choose Your Role Below
               ↙  ↓  ↓  ↙
               
    Audit Lead      Backend         QA            Product
        │              │             │               │
        ├→ 1            ├→ 1          ├→ 1            ├→ 1
        │   Quick Ref   │   Quick Ref │   Quick Ref    │   Quick Ref
        │               │             │                │
        ├→ 2            ├→ 2          ├→ 2             ├→ 2
        │   Summary     │   Framework │   Tracker      │   Competitive
        │               │             │                │
        ├→ 3            ├→ 3          └─→ Run Tests    ├→ 3
        │   Framework   │   Code Review               │   Analysis
        │               │
        └→ Track        └→ 4
           Progress        Run Tests
                          
All paths → PRICING_AUDIT_INDEX.md (navigation hub)
         → EPIC-2 READY! ✅
```

---

## 📊 Competitive Landscape Summary

```
PRICE POSITIONING

                        Cheap ←──────────────→ Expensive
                        ↓                        ↓
Budget Tier     Agoda ▌│ GE ▌▌│ Booking ▌▌▌│ MMT ▌▌▌▌
(₹3.5K/night)    10.2K   11.0K  11.8K     12.3K

Premium Tier    Agoda ▌│ GE ▌│ Booking ▌▌▌▌│ MMT ▌▌▌▌▌
(₹25K/night)     49K    50.5K  59K        62.5K

VALUE POSITIONING

       Transparent              Hidden Costs
       (Clear Breakdown)        (GST Hidden)
            │                        │
       GE ▓▓ Agoda              Booking ▓▓ Goibibo
       OYO ▓░ MMT              MMT ▓▓▓ (expensive)

SUMMARY:
- We're NOT the cheapest (Agoda is)
- We ARE best value (transparent + no GST)
- Premium tier: huge GST advantage (save ₹9K)
- Budget tier: modest advantage (save ₹735)
```

---

## ⏱️ Time Commitment by Role

```
Audit Lead:      [████████░] ~30 mins reading + daily sync
Backend:         [████████░] ~1-2 hours total
QA:              [███████░░] ~3-4 hours total
Product:         [████████░] ~2 hours total
Everyone:        [█████░░░░] ~5 mins daily standup

TOTAL TEAM TIME: ~12-15 person-hours for 1-week audit
EPIC-2 BENEFIT: Prevents months of debugging issues
ROI: 100:1 (1 week audit saves 100+ weeks of issues)
```

---

## 🎁 Deliverables at Each Milestone

```
MONDAY (March 15)
├─ ✅ All documents created (9 files)
├─ ✅ All tests written (3 files)
├─ ✅ Roles assigned
└─ ✅ Teams briefed

WEDNESDAY (March 17)
├─ ✅ Code review started
├─ ⏳ Red flag 1 investigation begins
└─ ⏳ Screenshots collection starts

THURSDAY (March 18)
├─ ⏳ Red flag 3 verification
├─ ✅ 10 screenshots collected (due)
└─ ⏳ Tests running

FRIDAY (March 19)
├─ ✅ All tests passing (due)
├─ ✅ Code review complete
└─ ⏳ Red flags 2 & 4 decisions

SATURDAY (March 20)
├─ ✅ Red flags all decided
├─ ✅ Competitive analysis complete
└─ ✅ Approval meeting scheduled

SUNDAY (March 21)
├─ ✅ Product approval signed
├─ ✅ Engineering approval signed
├─ ✅ QA approval signed
└─ ✅ CTO final sign-off

MONDAY (March 24)
└─ 🚀 EPIC-2 STARTS!
```

---

## ✨ The Payoff

```
WITHOUT THIS AUDIT:

User Booking                    EPIC-2 Implementation
    ↓                                    ↓
Use Current Pricing         Maybe breaking something?
    ↓                                    ↓
Unknown if:                   ❌ Pricing breaks
  • Competitive? (❌)         ❌ Edge cases fail
  • Bug-free? (❌)            ❌ Customer refunds
  • Edge-case safe? (❌)      ❌ Lost trust
                              ❌ Rollback needed


WITH THIS AUDIT:

Audit Phase (1 week)           EPIC-2 Implementation
    ↓                                    ↓
Verify Everything           Confident shipping
    ↓                                    ↓
✅ Competitive verified      ✅ Pricing safe
✅ Bugs found & fixed        ✅ Edge cases tested
✅ Edge cases tested         ✅ Customer trust
✅ Tests passing             ✅ Scale with confidence
```

---

**Document Version**: 1.0
**Created**: March 15, 2024
**Status**: ✅ Ready for Audit Phase
**Next Milestone**: March 21 Final Approval

🚀 **Let's audit pricing and ship EPIC-2 with zero regrets!**

