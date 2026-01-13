"""
Notification services for sending emails, WhatsApp, and SMS.

Phase 1 goal: reliable email/SMS infrastructure with env-driven safety.
"""
import logging
from typing import Any, Dict

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .models import Notification, NotificationTemplate, NotificationPreference

User = get_user_model()

logger = logging.getLogger(__name__)


class NotificationService:
    """Central notification primitives for Phase 1 infra.

    send_email(to, subject, template, context)
    send_sms(phone, template_id, variables)
    """

    @staticmethod
    def _resolve_user(user: User | None, fallback_email: str | None = None) -> User:
        """Ensure a user exists for notification logging without requiring OTP/booking flows."""
        if user:
            return user

        # Prefer existing staff/superuser to avoid creating noise
        existing = (
            User.objects.filter(is_superuser=True).first()
            or User.objects.filter(is_staff=True).first()
        )
        if existing:
            return existing

        # Create a system notifier user as last resort
        email_value = fallback_email or "alerts.goexplorer+system@gmail.com"
        system_user, _ = User.objects.get_or_create(
            username="system_notifier",
            defaults={
                "email": email_value,
                "first_name": "System",
                "last_name": "Notifier",
                "is_staff": True,
            },
        )
        return system_user

    @staticmethod
    def send_email(
        to: str,
        subject: str,
        template: str,
        context: Dict[str, Any] | None = None,
        *,
        user: User | None = None,
        dry_run: bool | None = None,
        sender: str | None = None,
    ) -> Notification | None:
        context = context or {}
        html_body = render_to_string(template, context)
        text_body = strip_tags(html_body)

        dry_run = settings.NOTIFICATIONS_EMAIL_DRY_RUN if dry_run is None else dry_run
        resolved_user = NotificationService._resolve_user(user, fallback_email=to)

        notification = Notification.objects.create(
            user=resolved_user,
            notification_type="email",
            recipient=to,
            subject=subject,
            body=html_body,
            status="pending",
        )

        if dry_run:
            notification.mark_sent("dry-run")
            logger.info("[DRY-RUN] Email queued (not sent) to %s", to)
            return notification

        try:
            send_mail(
                subject=subject,
                message=text_body,
                from_email=sender or settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to],
                html_message=html_body,
                fail_silently=False,
            )
            notification.mark_sent()
            logger.info("Email sent to %s", to)
        except Exception as exc:  # noqa: BLE001
            notification.mark_failed(str(exc))
            logger.exception("Email send failed to %s", to)
        return notification

    @staticmethod
    def send_sms(
        phone: str,
        template_id: str,
        variables: Dict[str, Any] | None = None,
        *,
        user: User | None = None,
        dry_run: bool | None = None,
        sender_id: str | None = None,
    ) -> Notification | None:
        variables = variables or {}
        dry_run = settings.NOTIFICATIONS_SMS_DRY_RUN if dry_run is None else dry_run
        resolved_user = NotificationService._resolve_user(user)
        sender_value = sender_id or settings.MSG91_SENDER_ID

        notification = Notification.objects.create(
            user=resolved_user,
            notification_type="sms",
            recipient=phone,
            body=f"template={template_id} vars={variables}",
            status="pending",
        )

        if dry_run:
            notification.mark_sent("dry-run")
            logger.info("[DRY-RUN] SMS queued (not sent) to %s", phone)
            return notification

        if not settings.MSG91_AUTHKEY or not template_id:
            error_msg = "MSG91 credentials/template missing"
            notification.mark_failed(error_msg)
            logger.error("SMS send aborted for %s: %s", phone, error_msg)
            return notification

        payload = {
            "template_id": template_id,
            "sender": sender_value,
            "route": settings.MSG91_ROUTE,
            "country": settings.MSG91_COUNTRY,
            "recipients": [
                {
                    "mobiles": phone,
                    **variables,
                }
            ],
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authkey": settings.MSG91_AUTHKEY,
        }

        try:
            response = requests.post(
                settings.MSG91_BASE_URL,
                json=payload,
                headers=headers,
                timeout=10,
            )
            if response.status_code in (200, 201, 202):
                notification.mark_sent(response.text[:200])
                logger.info("SMS sent to %s via MSG91", phone)
            else:
                error_msg = f"MSG91 {response.status_code}: {response.text[:200]}"
                notification.mark_failed(error_msg)
                logger.error("Failed SMS to %s: %s", phone, error_msg)
        except Exception as exc:  # noqa: BLE001
            notification.mark_failed(str(exc))
            logger.exception("Exception while sending SMS to %s", phone)

        return notification


class EmailService:
    """Send email notifications"""
    
    @staticmethod
    def send_email(user, subject, body, html_body=None, template=None):
        """
        Send email notification
        """
        try:
            if html_body is None:
                html_body = body
            
            recipient = user.email
            if not recipient:
                logger.warning(f"User {user.id} has no email address")
                return None
            
            # Send email
            send_mail(
                subject=subject,
                message=strip_tags(body),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                html_message=html_body,
                fail_silently=False,
            )
            
            # Log notification
            notification = Notification.objects.create(
                user=user,
                notification_type='email',
                template=template,
                recipient=recipient,
                subject=subject,
                body=body,
                status='sent'
            )
            
            logger.info(f"Email sent to {recipient} for user {user.id}")
            return notification
            
        except Exception as e:
            logger.error(f"Failed to send email to {user.email}: {str(e)}")
            notification = Notification.objects.create(
                user=user,
                notification_type='email',
                template=template,
                recipient=user.email,
                subject=subject,
                body=body,
                status='failed',
                error_message=str(e)
            )
            return notification
    
    @staticmethod
    def send_booking_confirmation(user, booking_data):
        """Send booking confirmation email"""
        subject = f"Booking Confirmation - {booking_data.get('booking_id', 'N/A')}"
        body = f"""
        Dear {user.first_name or user.username},
        
        Your booking has been confirmed!
        
        Booking Details:
        - Booking ID: {booking_data.get('booking_id')}
        - Type: {booking_data.get('booking_type', 'Travel')}
        - Property: {booking_data.get('property_name')}
        - Date: {booking_data.get('booking_date')}
        - Price: ₹{booking_data.get('price', '0')}
        - Status: {booking_data.get('status', 'Confirmed')}
        
        Please keep this confirmation for your records.
        
        Thank you for booking with GoExplorer!
        
        Best regards,
        GoExplorer Team
        """
        
        return EmailService.send_email(user, subject, body)


class WhatsAppService:
    """Send WhatsApp notifications using Twilio/WhatsApp Business API"""
    
    # Using placeholder - replace with actual WhatsApp API in production
    WHATSAPP_API_URL = getattr(settings, 'WHATSAPP_API_URL', 'https://api.whatsapp.com/message')
    WHATSAPP_API_KEY = getattr(settings, 'WHATSAPP_API_KEY', '')
    WHATSAPP_BUSINESS_ID = getattr(settings, 'WHATSAPP_BUSINESS_ID', '')
    
    @staticmethod
    def send_message(user, phone_number, message_template, template_params=None):
        """
        Send WhatsApp message
        
        In production, integrate with:
        - Twilio WhatsApp API
        - Meta WhatsApp Business API
        - Nexmo/Vonage
        """
        try:
            if not phone_number:
                logger.warning(f"User {user.id} has no WhatsApp number")
                return None
            
            # Log notification (actual sending would use WhatsApp API)
            notification = Notification.objects.create(
                user=user,
                notification_type='whatsapp',
                recipient=phone_number,
                body=f"Template: {message_template}\n{template_params or ''}",
                status='pending'
            )
            
            # TODO: Integrate with actual WhatsApp API
            # For demo, mark as sent
            notification.status = 'sent'
            notification.save()
            
            logger.info(f"WhatsApp message queued for {phone_number}")
            return notification
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp to {phone_number}: {str(e)}")
            notification = Notification.objects.create(
                user=user,
                notification_type='whatsapp',
                recipient=phone_number,
                body=message_template,
                status='failed',
                error_message=str(e)
            )
            return notification
    
    @staticmethod
    def send_booking_confirmation(user, booking_data):
        """Send WhatsApp booking confirmation"""
        try:
            preference = user.notification_preference
            if not preference.whatsapp_booking_confirmation or not preference.whatsapp_number:
                return None
        except NotificationPreference.DoesNotExist:
            return None
        
        message = f"""
        🎉 Booking Confirmed!
        
        Booking ID: {booking_data.get('booking_id')}
        Property: {booking_data.get('property_name')}
        Date: {booking_data.get('booking_date')}
        Price: ₹{booking_data.get('price')}
        
        Thank you for booking with GoExplorer! 🌍
        """
        
        return WhatsAppService.send_message(
            user, 
            preference.whatsapp_number, 
            'booking_confirmation',
            message
        )


class SMSService:
    """Send SMS notifications using Twilio/AWS SNS"""
    
    # Using placeholder - replace with actual SMS API in production
    SMS_API_KEY = getattr(settings, 'SMS_API_KEY', '')
    SMS_SENDER_ID = getattr(settings, 'SMS_SENDER_ID', 'GoExplorer')
    
    @staticmethod
    def send_sms(user, phone_number, message):
        """
        Send SMS notification.

        Uses MSG91 templated flow when configured, falls back to dry-run logging otherwise.
        """
        try:
            if not phone_number:
                logger.warning(f"User {user.id} has no phone number")
                return None

            template_id = getattr(settings, "MSG91_DEFAULT_TEMPLATE_ID", "")
            variables = {"message": message} if message else {}

            # Use the central service for real delivery/dry-run handling
            return NotificationService.send_sms(
                phone=phone_number,
                template_id=template_id,
                variables=variables,
                user=user,
            )

        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to send SMS to {phone_number}: {str(e)}")
            notification = Notification.objects.create(
                user=user,
                notification_type='sms',
                recipient=phone_number,
                body=message,
                status='failed',
                error_message=str(e)
            )
            return notification
    
    @staticmethod
    def send_booking_confirmation(user, booking_data):
        """Send SMS booking confirmation"""
        try:
            preference = user.notification_preference
            if not preference.sms_booking_confirmation or not preference.phone_number:
                return None
        except NotificationPreference.DoesNotExist:
            return None
        
        message = f"GoExplorer: Your booking {booking_data.get('booking_id')} is confirmed! Property: {booking_data.get('property_name')}. Price: ₹{booking_data.get('price')}. Ref: www.goexplorer.com"
        
        return SMSService.send_sms(user, preference.phone_number, message)


class NotificationManager:
    """Unified notification manager"""
    
    @staticmethod
    def send_booking_confirmation(user, booking_data):
        """Send all enabled booking confirmation notifications"""
        results = {
            'email': None,
            'whatsapp': None,
            'sms': None
        }
        
        try:
            preference = user.notification_preference
        except NotificationPreference.DoesNotExist:
            # Create default preferences
            preference = NotificationPreference.objects.create(user=user)
        
        # Send email
        if preference.email_booking_confirmation:
            results['email'] = EmailService.send_booking_confirmation(user, booking_data)
        
        # Send WhatsApp
        if preference.whatsapp_booking_confirmation and preference.whatsapp_number:
            results['whatsapp'] = WhatsAppService.send_booking_confirmation(user, booking_data)
        
        # Send SMS
        if preference.sms_booking_confirmation and preference.phone_number:
            results['sms'] = SMSService.send_booking_confirmation(user, booking_data)
        
        return results
    
    @staticmethod
    def send_payment_confirmation(user, payment_data):
        """Send payment confirmation notifications"""
        subject = f"Payment Received - {payment_data.get('payment_id', 'N/A')}"
        body = f"""
        Dear {user.first_name or user.username},
        
        Your payment has been received successfully!
        
        Payment Details:
        - Payment ID: {payment_data.get('payment_id')}
        - Amount: ₹{payment_data.get('amount', '0')}
        - Booking: {payment_data.get('booking_id')}
        - Date: {payment_data.get('payment_date')}
        - Status: {payment_data.get('status', 'Completed')}
        
        Thank you!
        
        GoExplorer Team
        """
        
        return EmailService.send_email(user, subject, body)
    
    @staticmethod
    def send_reminder(user, reminder_data):
        """Send booking reminder notification"""
        subject = f"Booking Reminder - {reminder_data.get('booking_id')}"
        body = f"""
        Dear {user.first_name or user.username},
        
        This is a reminder for your upcoming {reminder_data.get('booking_type', 'booking')}:
        
        - Booking ID: {reminder_data.get('booking_id')}
        - Property: {reminder_data.get('property_name')}
        - Date: {reminder_data.get('booking_date')}
        - Time: {reminder_data.get('check_in_time', 'As per confirmation')}
        
        Please arrive on time!
        
        GoExplorer Team
        """
        
        return EmailService.send_email(user, subject, body)
