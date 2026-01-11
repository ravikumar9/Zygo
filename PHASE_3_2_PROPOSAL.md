# PHASE 3.2 PROPOSAL: Password Reset via OTP

**Status:** 📋 PROPOSAL (Awaiting Approval)  
**Date:** January 11, 2026  
**Estimated Effort:** 2-3 hours  
**Risk Level:** LOW (Isolated, no impact on existing flows)

---

## Executive Summary

Implement secure password reset functionality using OTP verification via email OR mobile phone. This feature allows users who forget their password to reset it securely without admin intervention.

**Key Benefits:**
- ✅ Improved user experience (self-service password reset)
- ✅ Reduced admin support burden
- ✅ Enhanced security (OTP-based verification)
- ✅ Consistent with Phase 3.1 dual OTP approach
- ✅ Zero impact on existing authentication flows

---

## Requirements

### Functional Requirements

#### 1. Password Reset Request
**User Story:** As a user who forgot my password, I want to request a password reset so I can regain access to my account.

**Flow:**
1. User clicks "Forgot Password?" link on login page
2. User enters their registered email address
3. System verifies email exists in database
4. System presents two options:
   - **Option A:** Reset via Email OTP
   - **Option B:** Reset via Mobile OTP
5. User selects preferred method

**Validation:**
- Email must be registered in system
- User account must be active
- Rate limiting: Max 3 reset requests per 30 minutes

---

#### 2. OTP Verification for Password Reset
**User Story:** As a user resetting my password, I want to verify my identity via OTP so my account remains secure.

**Flow:**
1. System sends OTP to user's chosen channel (email or mobile)
2. User receives OTP code (6-digit)
3. User enters OTP on verification page
4. System validates OTP (same rules as Phase 2: 5-min expiry, 3 max attempts)
5. If OTP valid → Proceed to password reset
6. If OTP invalid → Show error, allow retry (up to 3 attempts)
7. If max attempts exceeded → Block for 30 minutes

**Validation:**
- OTP must match generated code
- OTP must not be expired (5 minutes)
- Max 3 verification attempts
- 30-second cooldown between OTP sends

---

#### 3. New Password Entry
**User Story:** As a user who verified my identity, I want to set a new password so I can access my account again.

**Flow:**
1. After successful OTP verification, show password reset form
2. User enters new password
3. User confirms new password
4. System validates password complexity
5. System updates user password
6. System logs password change event
7. System logs user out of all sessions (security measure)
8. User redirected to login page with success message

**Validation:**
- Password must be at least 8 characters
- Password must contain uppercase, lowercase, number
- Password and confirm password must match
- New password cannot be same as old password
- Password complexity enforced by Django validators

---

### Non-Functional Requirements

#### Security
- ✅ OTP-based verification (no email-only password reset links)
- ✅ Rate limiting on reset requests
- ✅ Session invalidation after password change
- ✅ Audit logging for password changes
- ✅ CSRF protection on all forms
- ✅ No password transmitted in GET requests
- ✅ Reuse existing OTPService (no new OTP logic)

#### Performance
- ✅ Zero impact on existing login/registration flows
- ✅ Minimal database queries (same as existing OTP flows)
- ✅ Fast OTP delivery (reuses Phase 1 NotificationService)

#### Usability
- ✅ Clear error messages
- ✅ Step-by-step wizard interface
- ✅ Mobile-responsive design
- ✅ Auto-focus on input fields
- ✅ Loading spinners during operations

---

## Technical Design

### Architecture

**Principle:** Reuse existing services, zero duplication

```
Password Reset Flow
│
├─ Step 1: Request Reset (email input)
│  └─ Validate email exists → users.models.User.objects.filter(email=...)
│
├─ Step 2: Choose OTP Method (email or mobile)
│  └─ User selects: email or mobile
│
├─ Step 3: Send OTP
│  └─ Reuse: OTPService.send_email_otp() OR OTPService.send_mobile_otp()
│
├─ Step 4: Verify OTP
│  └─ Reuse: OTPService.verify_email_otp() OR OTPService.verify_mobile_otp()
│
└─ Step 5: Reset Password
   ├─ Validate password complexity
   ├─ Update user.set_password(new_password)
   ├─ Invalidate sessions (logout all devices)
   └─ Redirect to login with success message
```

---

### Views Required

#### 1. `password_reset_request()` - Step 1
**URL:** `/users/password-reset/`  
**Method:** GET, POST  
**Purpose:** User enters email to request password reset

**Logic:**
```python
def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        user = User.objects.filter(email=email).first()
        if user:
            # Store in session for next step
            request.session['reset_user_id'] = user.id
            request.session['reset_email'] = user.email
            return redirect('users:password-reset-choose-method')
        else:
            messages.error(request, 'Email not found')
    return render(request, 'users/password_reset_request.html')
```

---

#### 2. `password_reset_choose_method()` - Step 2
**URL:** `/users/password-reset/choose-method/`  
**Method:** GET, POST  
**Purpose:** User chooses OTP method (email or mobile)

**Logic:**
```python
def password_reset_choose_method(request):
    reset_user_id = request.session.get('reset_user_id')
    if not reset_user_id:
        return redirect('users:password-reset-request')
    
    user = User.objects.get(id=reset_user_id)
    
    if request.method == 'POST':
        method = request.POST.get('method')  # 'email' or 'mobile'
        request.session['reset_otp_method'] = method
        return redirect('users:password-reset-verify-otp')
    
    return render(request, 'users/password_reset_choose_method.html', {
        'user': user,
        'has_email': bool(user.email),
        'has_phone': bool(user.phone)
    })
```

---

#### 3. `password_reset_verify_otp()` - Step 3 & 4
**URL:** `/users/password-reset/verify-otp/`  
**Method:** GET, POST (AJAX)  
**Purpose:** Send and verify OTP

**Logic:**
```python
def password_reset_verify_otp(request):
    reset_user_id = request.session.get('reset_user_id')
    otp_method = request.session.get('reset_otp_method')
    
    if not reset_user_id or not otp_method:
        return redirect('users:password-reset-request')
    
    user = User.objects.get(id=reset_user_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'send_otp':
            # Reuse OTPService
            if otp_method == 'email':
                result = OTPService.send_email_otp(user)
            else:
                result = OTPService.send_mobile_otp(user)
            return JsonResponse(result)
        
        elif action == 'verify_otp':
            otp_code = request.POST.get('otp')
            
            # Reuse OTPService
            if otp_method == 'email':
                result = OTPService.verify_email_otp(user, otp_code)
            else:
                result = OTPService.verify_mobile_otp(user, otp_code)
            
            if result['success']:
                request.session['reset_otp_verified'] = True
            
            return JsonResponse(result)
    
    return render(request, 'users/password_reset_verify_otp.html', {
        'user': user,
        'otp_method': otp_method
    })
```

---

#### 4. `password_reset_confirm()` - Step 5
**URL:** `/users/password-reset/confirm/`  
**Method:** GET, POST  
**Purpose:** User enters new password

**Logic:**
```python
def password_reset_confirm(request):
    reset_user_id = request.session.get('reset_user_id')
    otp_verified = request.session.get('reset_otp_verified')
    
    if not reset_user_id or not otp_verified:
        return redirect('users:password-reset-request')
    
    user = User.objects.get(id=reset_user_id)
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match')
        elif len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters')
        else:
            # Update password
            user.set_password(new_password)
            user.save()
            
            # Log password change
            from audit_logs.models import AuditLog
            AuditLog.objects.create(
                user=user,
                action='password_reset',
                details='Password reset via OTP'
            )
            
            # Clear session
            request.session.flush()
            
            messages.success(request, 'Password reset successful. Please login.')
            return redirect('users:login')
    
    return render(request, 'users/password_reset_confirm.html')
```

---

### Templates Required

#### 1. `password_reset_request.html`
**Purpose:** Email input form

**Content:**
- Email input field
- Submit button
- Link back to login
- Professional design matching existing forms

---

#### 2. `password_reset_choose_method.html`
**Purpose:** OTP method selection

**Content:**
- Two large buttons:
  - "Reset via Email OTP" (shows user's email)
  - "Reset via Mobile OTP" (shows user's masked phone)
- Clear indication of which method will be used
- Link to go back or cancel

---

#### 3. `password_reset_verify_otp.html`
**Purpose:** OTP verification

**Content:**
- Display chosen method (email or mobile)
- OTP input field (6 digits)
- "Send OTP" button
- "Verify OTP" button
- "Resend OTP" button (with cooldown timer)
- Error/success messages
- Loading spinner
- Similar design to Phase 3.1 OTP verification

---

#### 4. `password_reset_confirm.html`
**Purpose:** New password entry

**Content:**
- New password input field
- Confirm password input field
- Password strength indicator
- Submit button
- Clear validation messages

---

### URL Routes Required

```python
# users/urls.py
urlpatterns = [
    # Existing routes...
    
    # Phase 3.2: Password Reset
    path('password-reset/', views.password_reset_request, name='password-reset-request'),
    path('password-reset/choose-method/', views.password_reset_choose_method, name='password-reset-choose-method'),
    path('password-reset/verify-otp/', views.password_reset_verify_otp, name='password-reset-verify-otp'),
    path('password-reset/confirm/', views.password_reset_confirm, name='password-reset-confirm'),
]
```

---

### Database Changes

**NONE REQUIRED**

- Reuses existing User model
- Reuses existing UserOTP model
- Reuses existing AuditLog model (if available)
- Zero migrations needed

---

## Testing Plan

### Unit Tests (4 tests)

#### Test 1: Password Reset Request
```python
def test_password_reset_request():
    # Valid email
    response = client.post('/users/password-reset/', {'email': 'user@example.com'})
    assert response.status_code == 302  # Redirect to choose method
    
    # Invalid email
    response = client.post('/users/password-reset/', {'email': 'nonexistent@example.com'})
    assert 'Email not found' in response.content.decode()
```

#### Test 2: OTP Method Selection
```python
def test_choose_otp_method():
    # Email method
    response = client.post('/users/password-reset/choose-method/', {'method': 'email'})
    assert response.status_code == 302  # Redirect to verify OTP
    
    # Mobile method
    response = client.post('/users/password-reset/choose-method/', {'method': 'mobile'})
    assert response.status_code == 302  # Redirect to verify OTP
```

#### Test 3: OTP Verification
```python
def test_otp_verification():
    # Send OTP
    result = OTPService.send_email_otp(user)
    assert result['success'] == True
    
    # Verify OTP
    otp = UserOTP.objects.filter(user=user, otp_type='email').first()
    result = OTPService.verify_email_otp(user, otp.otp_code)
    assert result['success'] == True
```

#### Test 4: Password Reset Confirmation
```python
def test_password_reset_confirm():
    # Valid password
    response = client.post('/users/password-reset/confirm/', {
        'new_password': 'NewPass123!',
        'confirm_password': 'NewPass123!'
    })
    assert response.status_code == 302  # Redirect to login
    
    # Verify password changed
    user.refresh_from_db()
    assert user.check_password('NewPass123!') == True
```

---

### Browser E2E Test

```python
def test_password_reset_e2e():
    1. Navigate to login page
    2. Click "Forgot Password?"
    3. Enter email
    4. Choose OTP method (email)
    5. Send OTP
    6. Verify OTP
    7. Enter new password
    8. Confirm password
    9. Submit
    10. Verify redirect to login
    11. Login with new password
    12. Verify successful login
```

---

## Implementation Checklist

### Phase 3.2 Tasks

- [ ] Create password_reset_request view
- [ ] Create password_reset_choose_method view
- [ ] Create password_reset_verify_otp view
- [ ] Create password_reset_confirm view
- [ ] Create password_reset_request.html template
- [ ] Create password_reset_choose_method.html template
- [ ] Create password_reset_verify_otp.html template
- [ ] Create password_reset_confirm.html template
- [ ] Add URL routes to users/urls.py
- [ ] Add "Forgot Password?" link to login.html
- [ ] Write 4 unit tests (password reset flow)
- [ ] Write 1 browser E2E test
- [ ] Test on local server
- [ ] Update documentation
- [ ] Deploy to production server
- [ ] Validate on server

---

## Risk Assessment

### Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| OTP service failure | Low | Medium | Reusing proven Phase 2 OTPService |
| Session hijacking | Low | High | CSRF tokens, secure session cookies |
| Password reset abuse | Medium | Medium | Rate limiting (3 requests/30 min) |
| User confusion | Low | Low | Clear step-by-step wizard UI |
| Regression in login | Very Low | High | Isolated code, comprehensive tests |

**Overall Risk Level:** LOW

---

## Success Criteria

### Phase 3.2 Success Metrics

- ✅ All 4 unit tests passing
- ✅ Browser E2E test passing
- ✅ Password reset flow completes successfully
- ✅ OTP verification works for both email and mobile
- ✅ Password complexity enforced
- ✅ Session invalidation after password change
- ✅ Zero impact on existing login/registration flows
- ✅ No new database migrations
- ✅ Documentation complete
- ✅ Server validation successful

---

## Estimated Timeline

### Breakdown

1. **Views Implementation:** 1 hour
2. **Templates Creation:** 1 hour
3. **URL Routes & Links:** 15 minutes
4. **Testing (Unit + E2E):** 1 hour
5. **Documentation:** 30 minutes
6. **Server Deployment & Validation:** 30 minutes

**Total:** 3-4 hours

---

## Deliverables

### Code Files

**Modified:**
- users/views.py (4 new views)
- users/urls.py (4 new routes)
- templates/users/login.html (add "Forgot Password?" link)

**Created:**
- templates/users/password_reset_request.html
- templates/users/password_reset_choose_method.html
- templates/users/password_reset_verify_otp.html
- templates/users/password_reset_confirm.html
- test_phase3_2.py (unit tests)
- test_phase3_2_browser.py (E2E test)

### Documentation

- PHASE_3_2_PASSWORD_RESET.md (comprehensive documentation)
- PHASE_3_2_QUICK_START.md (quick reference)
- PHASE_3_2_DELIVERY_REPORT.md (delivery summary)

---

## Dependencies

### Phase 3.2 Depends On

- ✅ Phase 1 (Notifications): Email/SMS sending
- ✅ Phase 2 (OTP): OTP generation and verification
- ✅ Existing User model with email and phone fields
- ✅ Django authentication system

### No New Dependencies

- Zero new Python packages
- Zero new JavaScript libraries
- Zero new database tables
- Zero new external APIs

---

## Backward Compatibility

**100% Backward Compatible**

- No changes to existing login flow
- No changes to existing registration flow
- No changes to OTPService
- No changes to NotificationService
- No database schema changes
- Optional feature (existing users unaffected)

---

## Security Considerations

### Security Measures

1. **OTP-Based Verification**
   - No insecure "email link only" reset
   - OTP expires in 5 minutes
   - Max 3 verification attempts

2. **Rate Limiting**
   - Max 3 reset requests per 30 minutes per email
   - 30-second cooldown between OTP sends

3. **Session Security**
   - All sessions invalidated after password change
   - CSRF protection on all forms
   - No password in GET parameters

4. **Audit Logging**
   - Password changes logged with timestamp
   - IP address tracking (optional)
   - Email notification on password change (optional)

5. **Password Complexity**
   - Minimum 8 characters
   - Must contain uppercase, lowercase, number
   - Django password validators enforced

---

## Alternatives Considered

### Option 1: Email Link Only (Rejected)
**Pros:** Simpler implementation  
**Cons:** Less secure, no multi-factor verification  
**Decision:** Rejected - OTP provides better security

### Option 2: Security Questions (Rejected)
**Pros:** No OTP needed  
**Cons:** Outdated, easily guessable, poor UX  
**Decision:** Rejected - OTP is modern standard

### Option 3: Admin Manual Reset (Rejected)
**Pros:** No code needed  
**Cons:** Poor UX, admin burden, slow  
**Decision:** Rejected - Self-service is better

### **Selected: OTP-Based Reset (Approved)**
**Pros:** Secure, consistent with Phase 3.1, good UX, self-service  
**Cons:** Requires OTP delivery infrastructure (already in place)  
**Decision:** Best option - leverages existing systems

---

## Post-Implementation

### After Phase 3.2 Completion

**Optional Enhancements (Future Phases):**
1. Email notification on password change
2. Password history (prevent reuse of last 5 passwords)
3. Two-factor authentication for login (optional ongoing 2FA)
4. Login history and session management
5. Account lockout after multiple failed login attempts

---

## Approval Checklist

**Before Starting Phase 3.2:**

- [ ] Phase 3.1 deployed to server
- [ ] Phase 3.1 validated on server (all tests passing)
- [ ] Screenshots shared and reviewed
- [ ] No critical issues found in Phase 3.1
- [ ] Phase 3.2 proposal reviewed
- [ ] Phase 3.2 scope approved
- [ ] Timeline approved
- [ ] Deliverables approved

---

## Sign-Off

**Proposal Status:** 📋 AWAITING APPROVAL  
**Recommended Action:** APPROVE  
**Risk Level:** LOW  
**Estimated Effort:** 3-4 hours  
**Dependencies:** All satisfied (Phase 1, 2, 3.1 complete)

**Ready to Proceed:** YES (pending approval)

---

**Phase 3.2 Proposal Version:** 1.0  
**Date:** January 11, 2026  
**Next Step:** Await approval, then begin implementation
