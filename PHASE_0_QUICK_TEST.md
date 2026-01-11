# Phase 0: Quick Start Testing Guide

## Summary of Changes Made
- ✅ **Unified Seed Command**: `seed_all` merges hotels, packages, buses, wallets in one command
- ✅ **Enhanced Admin UI**: Color badges for status, inline editors, bulk actions, image previews  
- ✅ **Wallet Visibility**: User profile now shows balance + cashback post-login (not just on payment page)
- ✅ **Booking Status Clarity**: Admin badges with tooltips explain each status (pending/confirmed/failed/expired)
- ✅ **Fixed Admin Validation**: Removed duplicate fields, fixed FK issues

---

## QUICK START: Local Testing

### 1. Reset Local DB and Reseed
```bash
# Clear database (removes all data)
python manage.py flush --no-input

# Run migrations
python manage.py migrate

# Unified seed (16 hotels + 5 packages + 3 buses + wallet)
python manage.py seed_all --env=local
```

**Expected Output**:
```
============================================================
GOEXPLORER UNIFIED SEED
Environment: local
Clear existing: False
============================================================

-> Hotels, rooms, amenities, property rules
[OK] Packages cleared
[OK] Created package: Goa Beach Paradise
...
[OK] UNIFIED SEED COMPLETE
```

### 2. Verify Admin Loads Correctly
```bash
# Start server
python manage.py runserver

# Visit admin
# http://localhost:8000/admin
# Login: admin / admin (or create superuser: python manage.py createsuperuser)
```

**Checklist**:
- [ ] Admin page loads with CSS (not unstyled)
- [ ] Left sidebar shows all model sections
- [ ] No red error banners at top

### 3. Check Hotel Admin Enhancements
```
http://localhost:8000/admin/hotels/hotel/
```

**Verify**:
- [ ] List shows: Name | Type (colored badge) | Star | Preview (image thumbnail) | Status
- [ ] Property type shows color badges (Hotel=blue, Resort=green, Villa=orange)
- [ ] Click a hotel → form opens with new "Property Rules" section
- [ ] Property Rules field shows text area for check-in times, cancellation policy
- [ ] Can create inline room type by scrolling to "Room Types" section
- [ ] Bulk action dropdown shows "Mark as active/inactive" options

### 4. Check Package Admin Enhancements
```
http://localhost:8000/admin/packages/package/
```

**Verify**:
- [ ] List shows: Name | Type | Duration (4D/3N format) | Price | Active (toggle) | Preview
- [ ] Image preview shows 100x75px thumbnail
- [ ] Click package → opens form with inline itinerary/departures/inclusions
- [ ] Can add day-wise itinerary entries

### 5. Check Wallet Admin
```
http://localhost:8000/admin/payments/wallet/
```

**Verify**:
- [ ] testuser shown with balance ₹5000
- [ ] Click testuser wallet → shows WalletTransaction history
- [ ] Can see CashbackLedger entries with expiry dates

### 6. Check Booking Admin  
```
http://localhost:8000/admin/bookings/booking/
```

**Verify**:
- [ ] Status column shows color badges with hover tooltips
- [ ] Tooltip messages explain each status (e.g., "PENDING: Payment awaited...")
- [ ] Can see customer name, phone, email

### 7. Login as testuser and View Profile
```
# http://localhost:8000/users/login
# Email: testuser@example.com
# Password: password123
# Then visit: http://localhost:8000/users/profile/
```

**Expected Profile Page**:
```
Personal Information
────────────────────
Email: testuser@example.com
First Name: Test
Last Name: User
Phone: 9876543210

💰 Wallet & Cashback               ← NEW SECTION
────────────────────────────────────
[Alert Box]
Wallet Balance: INR 5000.00
Available to spend on next booking

[Alert Box]
Active Cashback: INR 1000.00
Expires: 31 Dec 2024
```

**Checklist**:
- [ ] Wallet Balance shows ₹5000
- [ ] Active Cashback shows ₹1000
- [ ] Expiry date displays correctly
- [ ] No console errors (F12 → Console tab)

### 8. Test Hotel Listing with Filters
```
http://localhost:8000/hotels/
```

**Verify**:
- [ ] Hotel list loads (shows 16 hotels from seed)
- [ ] Filter sidebar visible on left
- [ ] Can filter by property type (Hotel/Resort/Villa/Homestay/Lodge)
- [ ] Can filter by amenities (WiFi, Pool, Gym, etc.)
- [ ] Images display without 404 errors
- [ ] No console errors

### 9. Test Package Listing
```
http://localhost:8000/packages/
```

**Verify**:
- [ ] 5 packages display
- [ ] Package cards show images
- [ ] Duration displays as "4D/3N" format
- [ ] Price shows correctly
- [ ] No 404 errors in console

### 10. Test Bus Listing  
```
http://localhost:8000/buses/
```

**Verify**:
- [ ] 3 bus routes display
- [ ] Route names (Delhi→Agra, etc.) shown
- [ ] Fares display
- [ ] Seat availability shows
- [ ] No console 404s

---

## Console Error Check

**Open DevTools in any page**:
```
F12 → Console tab
```

**Expected**: No red errors, only warnings are acceptable

---

## Automated Seed (If Unicode Issues Occur)

**If** `python manage.py seed_all` fails with unicode errors on Windows:

```bash
python run_seeds.py
```

This cross-platform script handles UTF-8 encoding properly.

---

## Next Steps After Local Testing

1. **Verify all checklist items pass** ✅
2. **Take 4 screenshots**:
   - Admin hotel list with badges
   - User profile with wallet visible
   - Hotel list with filters
   - Package/bus listings
3. **Commit and push to server**:
   ```bash
   git add -A
   git commit -m "Phase 0 tested locally - ready for server"
   git push origin main
   ```
4. **Deploy to server** (see PHASE_0_COMPLETION.md deployment section)
5. **Verify on server** (run same checklist on production)

---

## Troubleshooting

**Q: Admin loads unstyled**
```
A: CSS not collected. Run:
   python manage.py collectstatic --noinput
```

**Q: seed_all fails with unicode error**
```
A: Windows terminal encoding issue. Run:
   python run_seeds.py
```

**Q: Wallet not visible on profile**
```
A: testuser might not have wallet. Create it:
   python manage.py seed_wallet_data
```

**Q: Images show 404**
```
A: Check settings MEDIA_ROOT and MEDIA_URL are correct.
   Verify images exist in media/hotel_images/ and media/package_images/
```

**Q: No hotels appear in list**
```
A: Seed didn't run. Execute:
   python manage.py seed_all --env=local
```

---

## Success Criteria

✅ All 10 verify checklists pass  
✅ Zero console errors (Ctrl+Shift+K)  
✅ Admin loads with CSS (styled, not plain)  
✅ Hotel/package/bus lists display seeded data  
✅ Filters work and persist  
✅ User profile shows wallet balance + cashback  
✅ Wallet payment option available (on booking page)  
✅ Can navigate without 404 errors  

**Once complete**: Ready for Phase 1 (property rules editor, bus seat UI, inventory auto-release)

---

**Status**: Phase 0 code complete | Awaiting local testing verification
