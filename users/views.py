from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.db import transaction
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from .models import User, UserProfile
from .serializers import UserSerializer
from django import forms
import logging

logger = logging.getLogger(__name__)


class UserRegistrationForm(forms.ModelForm):
    """User registration form"""
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')
    
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone']
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Passwords do not match")
        
        if User.objects.filter(email=cleaned_data.get('email')).exists():
            raise forms.ValidationError("Email already registered")

        # Phone is mandatory: numeric and valid length
        phone = cleaned_data.get('phone')
        if not phone:
            raise forms.ValidationError("Mobile number is required")
        if not str(phone).isdigit():
            raise forms.ValidationError("Mobile number must be numeric")
        if len(str(phone)) < 10 or len(str(phone)) > 15:
            raise forms.ValidationError("Mobile number must be 10-15 digits long")
        
        return cleaned_data


class UserLoginForm(forms.Form):
    """User login form"""
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)


@csrf_protect
@require_http_methods(["GET", "POST"])
def register(request):
    """
    Phase 3.1: User registration with mandatory dual OTP verification
    
    Registration requires:
    1. Email + Phone + Password submission
    2. Email OTP verification
    3. Mobile OTP verification
    4. Only then account becomes ACTIVE
    """
    if request.user.is_authenticated:
        return redirect('core:home')
    
    # Step 1: Initial form submission (email, phone, password)
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # Create inactive user (pending verification)
            with transaction.atomic():
                user = User.objects.create_user(
                    username=form.cleaned_data['email'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    phone=form.cleaned_data.get('phone', '')
                )
                user.is_active = True  # Will verify via OTP
                user.save()
                
                # Create user profile
                UserProfile.objects.create(user=user)
            
            # Redirect to OTP verification page
            # Do NOT auto-login - user must verify first
            request.session['pending_user_id'] = user.id
            request.session['pending_email'] = user.email
            request.session['pending_phone'] = user.phone
            
            return redirect('users:verify-registration-otp')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'users/register.html', {'form': form})


@csrf_protect
@require_http_methods(["GET", "POST"])
def verify_registration_otp(request):
    """
    Phase 3.1: Verify Email + Mobile OTP for new user registration
    
    User must verify BOTH email and mobile OTP before account activation
    """
    pending_user_id = request.session.get('pending_user_id')

    # If the current user is already fully verified, avoid looping on OTP page
    if request.user.is_authenticated and request.user.email_verified_at and request.user.phone_verified_at:
        messages.info(request, 'Your account is already verified.')
        return redirect('core:home')
    
    if not pending_user_id:
        if request.method == 'POST':
            return JsonResponse({
                'success': False,
                'message': 'Session expired. Please register again.'
            }, status=400)
        messages.error(request, 'Session expired. Please register again.')
        return redirect('users:register')
    
    try:
        user = User.objects.get(id=pending_user_id)
    except User.DoesNotExist:
        if request.method == 'POST':
            return JsonResponse({
                'success': False,
                'message': 'User not found. Please register again.'
            }, status=400)
        messages.error(request, 'User not found. Please register again.')
        return redirect('users:register')

    # Prevent sending users who are already verified back into OTP flows
    if user.email_verified_at and user.phone_verified_at:
        request.session.pop('pending_user_id', None)
        request.session.pop('pending_email', None)
        request.session.pop('pending_phone', None)
        request.session.pop('email_verified', None)
        request.session.pop('mobile_verified', None)

        if request.method == 'POST':
            return JsonResponse({
                'success': True,
                'message': 'Already verified. Please log in.'
            })

        messages.info(request, 'Your account is already verified. Please log in.')
        return redirect('users:login')
    
    from .otp_service import OTPService
    
    # Get verification status
    email_verified = request.session.get('email_verified', False)
    mobile_verified = request.session.get('mobile_verified', False)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # SEND Email OTP
        if action == 'send_email_otp':
            if email_verified:
                return JsonResponse({
                    'success': False,
                    'message': 'Email already verified ✓'
                }, status=400)
            
            result = OTPService.send_email_otp(user)
            return JsonResponse(result)
        
        # SEND Mobile OTP
        elif action == 'send_mobile_otp':
            if mobile_verified:
                return JsonResponse({
                    'success': False,
                    'message': 'Mobile already verified ✓'
                }, status=400)
            
            result = OTPService.send_mobile_otp(user)
            return JsonResponse(result)
        
        # VERIFY Email OTP
        elif action == 'verify_email_otp':
            otp_code = request.POST.get('otp_code')
            
            if not otp_code:
                return JsonResponse({
                    'success': False,
                    'message': 'Enter OTP code'
                }, status=400)
            
            result = OTPService.verify_email_otp(user, otp_code)
            
            if result['success']:
                request.session['email_verified'] = True
                email_verified = True
            
            return JsonResponse(result)
        
        # VERIFY Mobile OTP
        elif action == 'verify_mobile_otp':
            otp_code = request.POST.get('otp_code')
            
            if not otp_code:
                return JsonResponse({
                    'success': False,
                    'message': 'Enter OTP code'
                }, status=400)
            
            result = OTPService.verify_mobile_otp(user, otp_code)
            
            if result['success']:
                request.session['mobile_verified'] = True
                mobile_verified = True
            
            return JsonResponse(result)
        
        # COMPLETE Registration (both verified)
        elif action == 'complete_registration':
            if not email_verified or not mobile_verified:
                return JsonResponse({
                    'success': False,
                    'message': 'Both email and mobile must be verified'
                }, status=400)
            
            # Mark account as fully verified
            user.email_verified = True
            user.phone_verified = True
            user.save(update_fields=['email_verified', 'phone_verified'])
            
            # Clear session
            del request.session['pending_user_id']
            del request.session['pending_email']
            del request.session['pending_phone']
            del request.session['email_verified']
            del request.session['mobile_verified']
            
            return JsonResponse({
                'success': True,
                'message': 'Registration complete! Your account is now active. Please log in.'
            })
    
    # GET: Show verification form
    context = {
        'email': user.email,
        'phone': user.phone,
        'email_verified': email_verified,
        'mobile_verified': mobile_verified,
        'both_verified': email_verified and mobile_verified,
    }
    
    return render(request, 'users/verify_registration_otp.html', context)


@csrf_protect
@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    User login view with mandatory dual OTP verification.
    
    CRITICAL: Users cannot login until BOTH email_verified_at AND phone_verified_at are set.
    This enforces Phase 3.1 mandatory dual OTP requirement.
    """
    if request.user.is_authenticated:
        return redirect('core:home')
    
    login_failed = False
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )
            if user is not None:
                # CRITICAL: Enforce dual OTP verification before allowing login
                if not user.email_verified_at or not user.phone_verified_at:
                    messages.error(
                        request,
                        'Please verify your email and mobile number before logging in. Check your inbox for OTP.'
                    )
                    # Store user ID in session and redirect to OTP verification
                    request.session['pending_user_id'] = user.id
                    request.session['pending_email'] = user.email
                    request.session['pending_phone'] = user.phone
                    return redirect('users:verify-registration-otp')
                
                # User is fully verified - allow login
                login(request, user)
                # Clean, professional success message (no duplicate on booking pages)
                messages.success(request, 'Login successful!')
                
                # Handle next parameter from GET or POST
                next_url = request.POST.get('next') or request.GET.get('next')
                if next_url and next_url.startswith('/'):
                    return redirect(next_url)
                return redirect('core:home')
            else:
                messages.error(request, 'Invalid email or password')
                login_failed = True
    else:
        form = UserLoginForm()
    
    return render(request, 'users/login.html', {
        'form': form,
        'login_failed': login_failed,
        'next': request.GET.get('next', '')
    })


@require_http_methods(["GET", "POST"])
def logout_view(request):
    """
    User logout view - supports both GET and POST.
    
    Clears all session data to prevent booking/auth flow contamination.
    """
    if request.user.is_authenticated:
        logout(request)
        # Clear any booking-related session flags to prevent contamination
        session_keys_to_clear = [
            'pending_user_id', 'pending_email', 'pending_phone',
            'email_verified', 'mobile_verified',
            'booking_in_progress', 'selected_seats'
        ]
        for key in session_keys_to_clear:
            if key in request.session:
                del request.session[key]
        
        messages.success(request, 'Logged out successfully!')
    return redirect('core:home')


@login_required(login_url='users:login')
def user_profile(request):
    """User profile page with bookings and wallet visibility"""
    from bookings.models import Booking
    from payments.models import Wallet, CashbackLedger
    
    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    
    # Get wallet information
    wallet = Wallet.objects.filter(user=request.user).first()
    wallet_balance = wallet.balance if wallet else 0
    wallet_currency = wallet.currency if wallet else 'INR'
    
    # Get active cashback
    active_cashback = 0
    cashback_expiry = None
    if wallet:
        from django.utils import timezone
        cashback_ledgers = CashbackLedger.objects.filter(
            wallet=wallet,
            is_used=False,
            is_expired=False,
            expires_at__gte=timezone.now()
        ).order_by('expires_at')
        
        for ledger in cashback_ledgers:
            active_cashback += ledger.amount
            if not cashback_expiry or ledger.expires_at < cashback_expiry:
                cashback_expiry = ledger.expires_at
    
    return render(request, 'users/profile.html', {
        'bookings': bookings,
        'wallet_balance': wallet_balance,
        'wallet_currency': wallet_currency,
        'active_cashback': active_cashback,
        'cashback_expiry': cashback_expiry,
    })


class UserProfileView(generics.RetrieveUpdateAPIView):
    """User profile view"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    
    def get_object(self):
        return self.request.user


@method_decorator(csrf_exempt, name='dispatch')
class RegisterAPIView(APIView):
    """API endpoint for user registration"""
    
    def post(self, request):
        """Register a new user"""
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        phone = request.data.get('phone', '')
        
        if not email or not password:
            return Response(
                {'error': 'Email and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if User.objects.filter(email=email).exists():
            return Response(
                {'error': 'Email already registered'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone
                )
                UserProfile.objects.create(user=user)
            
            return Response(
                {'message': 'User registered successfully', 'user_id': user.id},
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


@method_decorator(csrf_exempt, name='dispatch')
class LoginAPIView(APIView):
    """API endpoint for user login"""
    
    def post(self, request):
        """Login user"""
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response(
                {'error': 'Email and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return Response(
                {'message': 'Login successful', 'user': UserSerializer(user).data},
                status=status.HTTP_200_OK
            )
        
        return Response(
            {'error': 'Invalid email or password'},
            status=status.HTTP_401_UNAUTHORIZED
        )
