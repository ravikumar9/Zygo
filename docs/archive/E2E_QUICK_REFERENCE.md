# E2E Test Suite - Quick Reference

## Files Created

```
qa_e2e/
├── conftest.py                    # pytest configuration
├── test_1_survivability.py        # 4 tests (SECTION A)
├── test_2_booking_flow.py         # 3 tests (SECTION B)
├── test_3_pricing_trust.py        # 3 tests (SECTION C)
├── test_4_cancellation.py         # 4 tests (SECTION D)
├── test_5_accessibility.py        # 8 tests (SECTION E)
├── test-results/                  # Screenshots (auto-generated)
└── __pycache__/                   # Python cache (auto-generated)
```

## Run Commands

### All Tests
```bash
pytest qa_e2e/ -v
```

### Specific Section
```bash
pytest qa_e2e/test_1_survivability.py -v      # SECTION A
pytest qa_e2e/test_2_booking_flow.py -v       # SECTION B
pytest qa_e2e/test_3_pricing_trust.py -v      # SECTION C
pytest qa_e2e/test_4_cancellation.py -v       # SECTION D
pytest qa_e2e/test_5_accessibility.py -v      # SECTION E
```

### With Browser Visible
```bash
pytest qa_e2e/ -v --headed
```

### With Full Output
```bash
pytest qa_e2e/ -v -s --tb=short
```

## Test Coverage

| Section | Tests | Focus |
|---------|-------|-------|
| A: Survivability | 4 | Edge cases (no rooms, no images, no meals) |
| B: Booking Flow | 3 | Critical path (validation, identity, flow) |
| C: Pricing Trust | 3 | Transparency (math, taxes, not misleading) |
| D: Cancellation | 4 | Visibility (policies clear everywhere) |
| E: Accessibility | 8 | WCAG 2.1 AA (heading, alt, keyboard, focus) |
| **TOTAL** | **22** | |

## Test Data

Each test run creates:
- 4 unique test hotels (with different properties)
- 2 bookings (1 hotel, 1 bus)
- All with timestamped unique identifiers

**No manual data creation needed.**

## Expected Output - Success

```
======================== 22 passed in 45.23s ========================
```

## Expected Output - Failure

```
FAILED qa_e2e/test_1_survivability.py::TestSurvivability::test_hotel_with_zero_rooms

qa_e2e/test_1_survivability.py:25: in test_hotel_with_zero_rooms
    expect(page.locator('text=/No rooms available/i')).to_be_visible()
AssertionError: Expected locator('text=/No rooms available/i') to be visible

Screenshot saved: qa_e2e/test-results/01_zero_rooms_hotel.png
```

## Environment Requirements

- Python 3.10+
- Django 4.2+
- pytest 9.0+
- pytest-playwright 0.7+
- Browser: Chromium (auto-installed by Playwright)

## Pre-Flight Checklist

- [ ] `python manage.py migrate --noinput` ✓
- [ ] `.env` file configured ✓
- [ ] Port 8000 free (or modify in conftest.py) ✓
- [ ] `requirements.txt` dependencies installed ✓

## Troubleshooting Quick Links

**Port 8000 in use:** Kill with `Get-NetTCPConnection -LocalPort 8000 | Stop-Process -Force`

**Import errors:** Verify PYTHONPATH includes project root

**Database errors:** Run `python manage.py migrate --noinput`

**Timeout errors:** Increase default timeout in conftest.py

## Output Artifacts

**Location:** `qa_e2e/test-results/`

Files generated on failure:
- `01_zero_rooms_hotel.png` - Screenshot of failed test
- `02_no_meal_plans.png` - Screenshot context
- `03_hotel_booking_form.png` - Visual debugging

## Integration Points

### CI/CD
- GitHub Actions example in `E2E_TEST_SUMMARY.md`
- Can run in Docker
- Artifact collection available

### Reporting
- pytest-html for HTML reports
- JUnit XML for CI integration
- Screenshots for visual debugging

---

**Created:** January 23, 2026  
**Framework:** Playwright + pytest  
**Ready to use:** ✓
