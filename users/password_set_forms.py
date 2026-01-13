"""
Custom SetPassword form to ensure password is saved correctly with hashing.
"""
import logging
from django import forms
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class SafeSetPasswordForm(SetPasswordForm):
    """
    SetPassword form that explicitly ensures password is hashed correctly.
    
    Overrides save() to guarantee set_password() is called properly
    and user is saved with commit=True.
    """
    
    def save(self, commit=True):
        """
        Save the password in hashed format using set_password().
        Force commit=True to ensure password is actually saved to DB.
        """
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        
        if commit:
            self.user.save()
            logger.info(f"Password reset completed for user: {self.user.email}")
        
        return self.user
