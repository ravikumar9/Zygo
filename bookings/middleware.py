"""
Middleware to clear authentication messages on booking/payment pages.
Prevents "Login successful" from appearing on booking confirmation.
"""
from django.contrib import messages


class ClearAuthMessagesMiddleware:
    """
    Clear authentication messages on booking/payment pages to prevent
    "Login successful" from appearing on booking confirmation.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Paths where we should clear auth messages
        booking_payment_paths = [
            '/bookings/',
            '/payments/',
            '/api/bookings/',
            '/api/payments/',
        ]
        
        # Check if current path is booking/payment related
        if any(request.path.startswith(path) for path in booking_payment_paths):
            # Get current messages storage
            storage = messages.get_messages(request)
            
            # Filter out authentication messages
            filtered_messages = []
            for message in storage:
                msg_lower = str(message).lower()
                # Skip login/auth success messages
                if not any(auth_word in msg_lower for auth_word in ['login successful', 'logged in', 'welcome back', 'authentication successful']):
                    filtered_messages.append(message)
            
            # Clear all messages
            storage.used = True
            
            # Re-add non-auth messages
            for msg in filtered_messages:
                messages.add_message(request, msg.level, msg.message, msg.extra_tags)
        
        response = self.get_response(request)
        return response
