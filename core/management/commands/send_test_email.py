"""
Send test email command - for email configuration verification.

Usage:
    python manage.py send_test_email
    python manage.py send_test_email --to user@example.com
"""
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send a test email to verify email configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            type=str,
            default=None,
            help='Email recipient (defaults to DEFAULT_FROM_EMAIL)'
        )

    def handle(self, *args, **options):
        recipient = options.get('to') or settings.DEFAULT_FROM_EMAIL

        self.stdout.write(self.style.NOTICE('Email Configuration Check'))
        self.stdout.write('-' * 60)
        self.stdout.write(f'Backend: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'From: {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write(f'To: {recipient}')
        
        if hasattr(settings, 'EMAIL_HOST'):
            self.stdout.write(f'SMTP Host: {settings.EMAIL_HOST}')
            self.stdout.write(f'SMTP Port: {settings.EMAIL_PORT}')
            self.stdout.write(f'SMTP User: {settings.EMAIL_HOST_USER}')
            self.stdout.write(f'SMTP TLS: {settings.EMAIL_USE_TLS}')
        
        self.stdout.write('-' * 60)
        self.stdout.write('\nSending test email...\n')

        try:
            subject = 'GoExplorer Test Email - Configuration Check'
            message = '''
Hello,

This is a test email from GoExplorer to verify email configuration.

✓ SMTP connection successful
✓ Email backend working correctly
✓ Password reset emails should work

If you received this email, your email configuration is correct.

---
GoExplorer Platform
            '''.strip()

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )

            self.stdout.write(
                self.style.SUCCESS(f'\n✓ Test email sent successfully to {recipient}')
            )
            self.stdout.write(
                self.style.SUCCESS('Check your inbox (and spam folder)')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n✗ Failed to send email: {str(e)}')
            )
            logger.error(f'Test email failed: {str(e)}', exc_info=True)
            
            # Provide troubleshooting help
            self.stdout.write('\n' + self.style.WARNING('Troubleshooting:'))
            self.stdout.write('1. Check EMAIL_SMTP_ENABLED=True in .env')
            self.stdout.write('2. Verify EMAIL_HOST, EMAIL_PORT in .env')
            self.stdout.write('3. Ensure EMAIL_HOST_USER and EMAIL_HOST_PASSWORD are correct')
            self.stdout.write('4. Check firewall/network allows SMTP connections')
            self.stdout.write('5. For Gmail: use App Password, not account password')
