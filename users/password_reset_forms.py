"""
Custom password reset form with error handling and logging.
Catches SMTP errors gracefully and logs them for troubleshooting.
"""
import logging
from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class SafePasswordResetForm(PasswordResetForm):
    """
    Password reset form that handles SMTP errors gracefully.
    
    If email sending fails, still shows success message to user
    (to prevent email enumeration attacks) but logs the error
    for admin investigation.
    """
    
    def save(self, domain_override=None, subject_template_name='registration/password_reset_subject.txt',
             email_template_name='registration/password_reset_email.html',
             use_https=False, token_generator=None, from_email=None,
             request=None, html_email_template_name=None, extra_email_context=None):
        """
        Generate a one-use only link for resetting password and send it to the
        user. Always return success even if email fails (prevent enumeration).
        """
        try:
            return super().save(
                domain_override=domain_override,
                subject_template_name=subject_template_name,
                email_template_name=email_template_name,
                use_https=use_https,
                token_generator=token_generator,
                from_email=from_email,
                request=request,
                html_email_template_name=html_email_template_name,
                extra_email_context=extra_email_context,
            )
        except Exception as e:
            # Log the error for admin troubleshooting
            logger.error(f"Password reset email failed for user {self.cleaned_data['email']}: {e}", exc_info=True)
            # Return success anyway (prevent email enumeration; user won't see this)
            return None
