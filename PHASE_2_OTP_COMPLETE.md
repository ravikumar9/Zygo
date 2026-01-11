# Phase 2: OTP Verification - Implementation Complete

## Overview
Email and Mobile OTP verification system implemented for user identity verification (Phase 2: Security).

---

## Implementation Summary

### 1. Models Created

**UserOTP Model** (`users/models_otp.py`):
- Tracks OTP attempts for email and mobile verification
- Fields: user, otp_type (email/mobile), otp_code, contact, created_at, expires_at, is_verified, attempts
- Built-in methods: `generate_otp()`, `create_otp()`, `verify()`, `is_expired()`, `can_attempt()`
- 5-minute expiry, 3 max attempts per OTP

**User Model Updates** (`users/models.py`):
- Added `email_verified_at` timestamp
- Added `phone_verified_at` timestamp
- Existing `email_verified` and `phone_verified` boolean flags

### 2. Service Layer

**OTPService** (`users/otp_service.py`):
- `send_email_otp(user, email=None)` - Send OTP via email
- `send_mobile_otp(user, phone=None)` - Send OTP via SMS (MSG91)
- `verify_email_otp(user, otp_code)` - Verify email OTP
- `verify_mobile_otp(user, otp_code)` - Verify mobile OTP
- `get_verification_status(user)` - Get user verification status
- `can_resend(user, otp_type)` - Check cooldown (30 seconds)
- Atomic transactions for all operations
- Automatic invalidation of previous pending OTPs on new send

### 3. Views & APIs

**Web Views** (`users/otp_views.py`):
- `send_email_otp` - POST /users/otp/send-email/
- `send_mobile_otp` - POST /users/otp/send-mobile/
- `verify_email_otp` - POST /users/otp/verify-email/
- `verify_mobile_otp` - POST /users/otp/verify-mobile/
- `verification_status` - GET /users/otp/status/

**API Views** (DRF):
- `SendEmailOTPAPIView` - POST /users/api/otp/send-email/
- `SendMobileOTPAPIView` - POST /users/api/otp/send-mobile/
- `VerifyEmailOTPAPIView` - POST /users/api/otp/verify-email/
- `VerifyMobileOTPAPIView` - POST /users/api/otp/verify-mobile/
- `VerificationStatusAPIView` - GET /users/api/otp/status/

All endpoints require authentication (`@login_required` / `IsAuthenticated`)

### 4. Admin Interface

**UserOTPAdmin**:
- Read-only view of OTP attempts
- Filter by type, verification status, date
- Search by user, contact, OTP code
- Manual creation disabled (service-only)
- Date hierarchy for easy navigation

**Updated UserAdmin**:
- Shows verification timestamps
- Readonly fields for verified_at timestamps

### 5. Email Template

**OTP Email Template** (`templates/notifications/email/otp_email.html`):
- Professional design with GoExplorer branding
- Large, clear OTP code display
- Expiry time warning
- Security notice (never share OTP)
- Responsive HTML layout

### 6. Integration with Phase 1

Uses `NotificationService` from Phase 1:
- Email delivery via SMTP (Gmail)
- SMS delivery via MSG91 templated flow
- Dry-run support for testing
- Automatic notification logging

---

## Security Features

1. **OTP Generation**: Secure 6-digit random code using `secrets.randbelow()`
2. **Expiry**: 5 minutes from generation
3. **Max Attempts**: 3 attempts per OTP, then locked
4. **Cooldown**: 30-second resend cooldown
5. **One-time Use**: OTP invalidated after successful verification
6. **Automatic Cleanup**: Previous pending OTPs invalidated on new send
7. **Atomic Operations**: All DB writes use transactions
8. **No Hardcoding**: OTPs generated fresh each time

---

## Configuration

Add to `.env` (optional overrides):

```env
# MSG91 OTP-specific template (if different from default)
MSG91_OTP_TEMPLATE_ID=your_otp_template_id
```

Existing Phase 1 settings used:
- `MSG91_AUTHKEY`
- `MSG91_SENDER_ID`
- `MSG91_DEFAULT_TEMPLATE_ID`
- `EMAIL_SMTP_ENABLED`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`

---

## Testing

### Automated Test Suite

Run: `python test_otp_verification.py`

Tests:
1. ✓ Send Email OTP
2. ✓ Verify Email OTP (wrong + correct)
3. ✓ Send Mobile OTP
4. ✓ Verify Mobile OTP (wrong + correct)
5. ✓ Resend Cooldown (30 seconds)
6. ✓ OTP Expiry (5 minutes)
7. ✓ Max Attempts (3 attempts)
8. ✓ Verification Status

Creates test user: `test_otp@goexplorer.com` / `test123`

### Manual Testing Checklist

#### Email OTP Flow
- [ ] Register/login as user
- [ ] Call `/users/otp/send-email/`
- [ ] Check email inbox for OTP
- [ ] Verify OTP displays correctly
- [ ] Try wrong OTP (should fail)
- [ ] Try correct OTP (should succeed)
- [ ] Check `email_verified` = True
- [ ] Check `email_verified_at` timestamp set

#### Mobile OTP Flow
- [ ] Call `/users/otp/send-mobile/`
- [ ] Check phone for SMS OTP
- [ ] Try wrong OTP (should fail)
- [ ] Try correct OTP (should succeed)
- [ ] Check `phone_verified` = True
- [ ] Check `phone_verified_at` timestamp set

#### Edge Cases
- [ ] Try resending within 30 seconds (should be blocked)
- [ ] Wait 30 seconds and resend (should work)
- [ ] Enter wrong OTP 3 times (should lock)
- [ ] Try 4th attempt (should reject)
- [ ] Wait 5+ minutes after OTP send (should expire)
- [ ] Verify expired OTP (should fail)

#### Admin Verification
- [ ] Login to `/admin/`
- [ ] Check `Users > User OTPs`
- [ ] View OTP attempts history
- [ ] Verify no manual creation allowed
- [ ] Check user verification flags in User admin

---

## API Usage Examples

### Send Email OTP
```bash
curl -X POST http://localhost:8000/users/api/otp/send-email/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

Response:
```json
{
  "success": true,
  "message": "OTP sent to user@example.com",
  "otp_id": 123
}
```

### Verify Email OTP
```bash
curl -X POST http://localhost:8000/users/api/otp/verify-email/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"otp_code": "123456"}'
```

Response:
```json
{
  "success": true,
  "message": "OTP verified successfully"
}
```

### Get Verification Status
```bash
curl http://localhost:8000/users/api/otp/status/ \
  -H "Authorization: Token YOUR_TOKEN"
```

Response:
```json
{
  "email_verified": true,
  "email_verified_at": "2026-01-11T10:30:00Z",
  "phone_verified": true,
  "phone_verified_at": "2026-01-11T10:35:00Z",
  "is_fully_verified": true
}
```

---

## Database Schema

### users_userotp Table
- `id` - Primary key
- `user_id` - Foreign key to users
- `otp_type` - 'email' or 'mobile'
- `otp_code` - 6-digit code
- `contact` - Email or phone where OTP sent
- `created_at` - Timestamp
- `expires_at` - Expiry timestamp (created_at + 5 min)
- `is_verified` - Boolean
- `verified_at` - Timestamp (null until verified)
- `attempts` - Integer (0-3)
- `max_attempts` - Integer (default 3)

Indexes:
- `user_id, otp_type, created_at` (composite)
- `contact, otp_type`

### users_user Updates
- `email_verified_at` - Timestamp (nullable)
- `phone_verified_at` - Timestamp (nullable)

---

## Migration

Applied:
```
users.0002_user_email_verified_at_user_phone_verified_at_and_more
```

Adds:
- `email_verified_at` field
- `phone_verified_at` field
- `UserOTP` model

---

## Known Limitations

1. **MSG91 DLT Setup Required**: SMS delivery requires PE-TM chain configuration on MSG91 dashboard
2. **No UI Pages**: Only API endpoints provided (frontend integration pending)
3. **Single Device**: OTP sent to registered email/phone only
4. **No OTP History UI**: Admin-only OTP history view

---

## Next Steps (NOT in this Phase)

❌ DO NOT implement yet (Phase 3+):
- Booking restrictions based on verification
- UI pages for OTP verification flow
- Multi-image seeding for hotels/packages
- Reviews moderation
- Booking lifecycle notifications
- Wallet/payment integration

---

## Verification Commands

```bash
# Run automated tests
python test_otp_verification.py

# Create migrations
python manage.py makemigrations users

# Apply migrations
python manage.py migrate

# Check admin
python manage.py runserver
# Visit http://localhost:8000/admin/users/userotp/

# Test email OTP manually
python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> from users.otp_service import OTPService
>>> User = get_user_model()
>>> user = User.objects.first()
>>> OTPService.send_email_otp(user)
>>> # Check email, then:
>>> OTPService.verify_email_otp(user, "123456")
```

---

## Phase 2 Status: COMPLETE ✓

All requirements met:
- ✓ Email OTP verification
- ✓ Mobile OTP verification
- ✓ 5-minute expiry
- ✓ 3 max attempts
- ✓ 30-second resend cooldown
- ✓ OTP invalidated after success
- ✓ Admin bypass (superusers can manually set verified flags)
- ✓ NotificationService integration
- ✓ No hardcoded OTPs
- ✓ Atomic transactions
- ✓ No coupling with booking/wallet/reviews
- ✓ Test suite provided
- ✓ Documentation complete

Ready for Phase 3 after user approval.
