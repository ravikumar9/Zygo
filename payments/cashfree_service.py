"""
Cashfree UPI Payment Integration
Handles: UPI intent, QR codes, webhooks
"""
import hmac
import json
import hashlib
import requests
from decimal import Decimal
from django.conf import settings
from django.http import JsonResponse


class CashfreeService:
    """Cashfree payment gateway wrapper"""
    
    BASE_URL = "https://api.cashfree.com"
    
    def __init__(self):
        self.app_id = settings.CASHFREE_APP_ID
        self.secret_key = settings.CASHFREE_SECRET_KEY
        self.api_version = settings.CASHFREE_API_VERSION
    
    def create_order(self, booking_id, amount, customer_email, customer_phone):
        """Create Cashfree order for UPI/Cards"""
        try:
            if not self.app_id or not self.secret_key:
                return None
            
            headers = {
                "Content-Type": "application/json",
                "x-api-version": self.api_version,
                "x-client-id": self.app_id,
                "x-client-secret": self.secret_key,
            }
            
            payload = {
                "order_id": f"order_{booking_id}",
                "order_amount": float(amount),
                "order_currency": "INR",
                "customer_details": {
                    "customer_id": f"cust_{booking_id}",
                    "customer_email": customer_email,
                    "customer_phone": customer_phone,
                },
                "order_meta": {
                    "return_url": f"http://127.0.0.1:8000/bookings/{booking_id}/payment-callback/",
                    "notify_url": f"http://127.0.0.1:8000/payments/cashfree-webhook/",
                },
                "order_tags": {
                    "booking_id": str(booking_id)
                }
            }
            
            # Create order
            response = requests.post(
                f"{self.BASE_URL}/orders",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'order_id': data.get('order_id'),
                    'payment_session_id': data.get('payment_session_id'),
                    'payment_link': data.get('payment_link'),
                    'status': data.get('order_status'),
                }
            else:
                return None
        except Exception as e:
            print(f"Cashfree order creation error: {e}")
            return None
    
    def verify_signature(self, order_id, order_amount, order_status, signature):
        """Verify Cashfree webhook signature"""
        try:
            message = f"{order_id}{order_amount}{order_status}"
            hash_object = hmac.new(
                self.secret_key.encode(),
                message.encode(),
                hashlib.sha256
            )
            computed_signature = hash_object.hexdigest()
            return computed_signature == signature
        except Exception as e:
            print(f"Signature verification error: {e}")
            return False
    
    def get_order_status(self, order_id):
        """Get order status from Cashfree"""
        try:
            if not self.app_id or not self.secret_key:
                return None
            
            headers = {
                "x-api-version": self.api_version,
                "x-client-id": self.app_id,
                "x-client-secret": self.secret_key,
            }
            
            response = requests.get(
                f"{self.BASE_URL}/orders/{order_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'order_id': data.get('order_id'),
                    'status': data.get('order_status'),
                    'payment_method': data.get('payment_method'),
                    'amount': data.get('order_amount'),
                }
            return None
        except Exception as e:
            print(f"Get order status error: {e}")
            return None
