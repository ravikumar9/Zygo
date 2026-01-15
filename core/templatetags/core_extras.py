from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Get an item from a dictionary"""
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.simple_tag
def get_corporate_status(user_email):
    """Get corporate account status for a user's email domain"""
    if not user_email or '@' not in user_email:
        return None
    
    from core.models import CorporateAccount
    domain = user_email.split('@')[-1]
    try:
        account = CorporateAccount.objects.get(email_domain=domain)
        return account.status
    except CorporateAccount.DoesNotExist:
        return None