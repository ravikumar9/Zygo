from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import views as auth_views
from django.conf import settings
from .password_reset_forms import SafePasswordResetForm
from . import views
from . import otp_views

app_name = 'users'

urlpatterns = [
    # Web UI authentication
    path('register/', views.register, name='register'),
    path('verify-registration-otp/', views.verify_registration_otp, name='verify-registration-otp'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.user_profile, name='profile'),
    
    # Password reset
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='users/password_reset.html',
        email_template_name='users/password_reset_email.html',
        subject_template_name='users/password_reset_subject.txt',
        success_url='/users/password-reset/done/',
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        form_class=SafePasswordResetForm,  # Use safe form with error handling
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='users/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='users/password_reset_confirm.html',
        success_url='/users/reset/done/'
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='users/password_reset_complete.html'
    ), name='password_reset_complete'),

    # API endpoints
    path('api/profile/', views.UserProfileView.as_view(), name='api-profile'),
    
    # OTP verification endpoints
    path('otp/send-email/', otp_views.send_email_otp, name='otp-send-email'),
    path('otp/send-mobile/', otp_views.send_mobile_otp, name='otp-send-mobile'),
    path('otp/verify-email/', otp_views.verify_email_otp, name='otp-verify-email'),
    path('otp/verify-mobile/', otp_views.verify_mobile_otp, name='otp-verify-mobile'),
    path('otp/status/', otp_views.verification_status, name='otp-status'),
    
    # OTP API endpoints
    path('api/otp/send-email/', otp_views.SendEmailOTPAPIView.as_view(), name='api-otp-send-email'),
    path('api/otp/send-mobile/', otp_views.SendMobileOTPAPIView.as_view(), name='api-otp-send-mobile'),
    path('api/otp/verify-email/', otp_views.VerifyEmailOTPAPIView.as_view(), name='api-otp-verify-email'),
    path('api/otp/verify-mobile/', otp_views.VerifyMobileOTPAPIView.as_view(), name='api-otp-verify-mobile'),
    path('api/otp/status/', otp_views.VerificationStatusAPIView.as_view(), name='api-otp-status'),
]
