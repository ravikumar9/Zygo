"""
OTP verification views for Phase 2: Security
Email and mobile OTP send/verify/resend endpoints
"""
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .otp_service import OTPService


@login_required
@require_http_methods(["POST"])
def send_email_otp(request):
    """Send OTP to user's email for verification."""
    result = OTPService.send_email_otp(request.user)
    return JsonResponse(result, status=200 if result['success'] else 400)


@login_required
@require_http_methods(["POST"])
def send_mobile_otp(request):
    """Send OTP to user's mobile for verification."""
    result = OTPService.send_mobile_otp(request.user)
    return JsonResponse(result, status=200 if result['success'] else 400)


@login_required
@require_http_methods(["POST"])
def verify_email_otp(request):
    """Verify email OTP."""
    otp_code = request.POST.get('otp_code')
    
    if not otp_code:
        return JsonResponse({'success': False, 'message': 'OTP code is required'}, status=400)
    
    result = OTPService.verify_email_otp(request.user, otp_code)
    return JsonResponse(result, status=200 if result['success'] else 400)


@login_required
@require_http_methods(["POST"])
def verify_mobile_otp(request):
    """Verify mobile OTP."""
    otp_code = request.POST.get('otp_code')
    
    if not otp_code:
        return JsonResponse({'success': False, 'message': 'OTP code is required'}, status=400)
    
    result = OTPService.verify_mobile_otp(request.user, otp_code)
    return JsonResponse(result, status=200 if result['success'] else 400)


@login_required
@require_http_methods(["GET"])
def verification_status(request):
    """Get user's current verification status."""
    result = OTPService.get_verification_status(request.user)
    return JsonResponse(result)


# API Views for REST Framework

@method_decorator(csrf_exempt, name='dispatch')
class SendEmailOTPAPIView(APIView):
    """API endpoint to send email OTP."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        result = OTPService.send_email_otp(request.user)
        return Response(result, status=status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class SendMobileOTPAPIView(APIView):
    """API endpoint to send mobile OTP."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        result = OTPService.send_mobile_otp(request.user)
        return Response(result, status=status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class VerifyEmailOTPAPIView(APIView):
    """API endpoint to verify email OTP."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        otp_code = request.data.get('otp_code')
        
        if not otp_code:
            return Response(
                {'success': False, 'message': 'OTP code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = OTPService.verify_email_otp(request.user, otp_code)
        return Response(result, status=status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class VerifyMobileOTPAPIView(APIView):
    """API endpoint to verify mobile OTP."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        otp_code = request.data.get('otp_code')
        
        if not otp_code:
            return Response(
                {'success': False, 'message': 'OTP code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = OTPService.verify_mobile_otp(request.user, otp_code)
        return Response(result, status=status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class VerificationStatusAPIView(APIView):
    """API endpoint to get verification status."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        result = OTPService.get_verification_status(request.user)
        return Response(result, status=status.HTTP_200_OK)
