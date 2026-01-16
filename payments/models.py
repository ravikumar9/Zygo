from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from core.models import TimeStampedModel
from bookings.models import Booking


class Payment(TimeStampedModel):
    """Payment model"""
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHOD = [
        ('razorpay', 'Razorpay'),
        ('stripe', 'Stripe'),
        ('upi', 'UPI'),
        ('card', 'Credit/Debit Card'),
        ('netbanking', 'Net Banking'),
        ('wallet', 'Wallet'),
        ('cash', 'Cash'),
    ]
    
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    # Gateway details
    gateway_payment_id = models.CharField(max_length=200, blank=True)
    gateway_order_id = models.CharField(max_length=200, blank=True)
    gateway_signature = models.CharField(max_length=500, blank=True)
    
    # Transaction details
    transaction_id = models.CharField(max_length=200, blank=True)
    transaction_date = models.DateTimeField(null=True, blank=True)
    
    # Response data
    gateway_response = models.JSONField(default=dict, blank=True)
    
    # Refund
    refund_id = models.CharField(max_length=200, blank=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refund_date = models.DateTimeField(null=True, blank=True)
    
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment for {self.booking.booking_id} - {self.status}"


class Invoice(TimeStampedModel):
    """Invoice model"""
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='invoice')
    
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField(auto_now_add=True)
    
    # Billing details
    billing_name = models.CharField(max_length=200)
    billing_email = models.EmailField()
    billing_phone = models.CharField(max_length=15)
    billing_address = models.TextField()
    
    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Tax details
    cgst = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sgst = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    igst = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    pdf_file = models.FileField(upload_to='invoices/', null=True, blank=True)
    
    def __str__(self):
        return f"Invoice {self.invoice_number}"


class Wallet(TimeStampedModel):
    """Closed-loop wallet for users to store balance and cashback"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cashback_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='INR')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - Wallet Balance: ₹{self.balance}"
    
    def add_balance(self, amount, description=""):
        """Add balance to wallet"""
        previous_balance = self.balance
        self.balance += Decimal(str(amount))
        self.save(update_fields=['balance', 'updated_at'])
        WalletTransaction.objects.create(
            wallet=self,
            transaction_type='credit',
            amount=amount,
            balance_before=previous_balance,
            balance_after=self.balance,
            description=description,
            status='success',
            payment_gateway='internal',
        )
    
    def deduct_balance(self, amount, description=""):
        """Deduct balance from wallet"""
        if self.balance < Decimal(str(amount)):
            raise ValueError("Insufficient wallet balance")
        previous_balance = self.balance
        self.balance -= Decimal(str(amount))
        self.save(update_fields=['balance', 'updated_at'])
        WalletTransaction.objects.create(
            wallet=self,
            transaction_type='debit',
            amount=amount,
            balance_before=previous_balance,
            balance_after=self.balance,
            description=description,
            status='success',
            payment_gateway='internal',
        )
    
    def get_available_balance(self):
        """Get available balance (balance + non-expired cashback)"""
        total_cashback = CashbackLedger.objects.filter(
            wallet=self,
            is_used=False,
            is_expired=False,
            expires_at__gt=timezone.now()
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
        
        return self.balance + total_cashback


class WalletTransaction(TimeStampedModel):
    """Track all wallet transactions (credits, debits, payments)."""

    TRANSACTION_TYPES = [
        ('credit', 'Credit'),      # Money added to wallet
        ('debit', 'Debit'),        # Money spent from wallet
        ('cashback', 'Cashback'),  # Reward/cashback credited
        ('refund', 'Refund'),      # Refund from cancelled booking or failed payment
        ('bonus', 'Bonus'),        # UPI top-up bonus credit
    ]

    TRANSACTION_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    PAYMENT_GATEWAYS = [
        ('cashfree', 'Cashfree'),
        ('razorpay', 'Razorpay'),
        ('upi', 'UPI'),
        ('netbanking', 'Net Banking'),
        ('internal', 'Internal'),  # For cashback, refunds, manual adjustments
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance_before = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    balance_after = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))

    payment_gateway = models.CharField(max_length=20, choices=PAYMENT_GATEWAYS, default='internal')
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS, default='pending')

    reference_id = models.CharField(max_length=200, blank=True)

    # Gateway tracking
    gateway_order_id = models.CharField(max_length=200, blank=True)
    gateway_payment_id = models.CharField(max_length=200, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)

    # Reference (if transaction relates to a booking)
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='wallet_transactions')

    description = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['gateway_order_id']),
        ]

    def __str__(self):
        return f"{self.transaction_type} - ₹{self.amount} - {self.status}"

    def create_refund(self, reason="Payment failed"):
        """Create reverse transaction for failed payment and restore balance."""
        refund_txn = WalletTransaction.objects.create(
            wallet=self.wallet,
            transaction_type='refund',
            amount=self.amount,
            balance_before=self.wallet.balance,
            balance_after=self.wallet.balance + self.amount,
            description=f"Refund: {reason}",
            gateway_order_id=self.gateway_order_id,
            gateway_payment_id=self.gateway_payment_id,
            gateway_response=self.gateway_response,
            booking=self.booking,
            status='success',
            payment_gateway=self.payment_gateway,
        )
        # Update wallet balance to reflect refund
        self.wallet.balance += self.amount
        self.wallet.save(update_fields=['balance', 'updated_at'])
        return refund_txn


class CashbackLedger(TimeStampedModel):
    """Track cashback earned, used, and expired"""
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='cashback_entries')
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='cashback_entries')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    earned_on = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    is_used = models.BooleanField(default=False)
    used_on = models.DateTimeField(null=True, blank=True)
    used_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    is_expired = models.BooleanField(default=False)
    expired_on = models.DateTimeField(null=True, blank=True)
    
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['expires_at']
    
    def __str__(self):
        return f"{self.wallet.user.username} - Cashback ₹{self.amount} - {'Used' if self.is_used else 'Active' if not self.is_expired else 'Expired'}"
    
    def mark_as_used(self, amount=None):
        """Mark cashback as used"""
        if self.is_expired:
            raise ValueError("Cannot use expired cashback")
        if self.is_used:
            raise ValueError("Cashback already used")
        
        use_amount = Decimal(str(amount)) if amount else self.amount
        if use_amount > self.amount:
            raise ValueError("Cannot use more than available cashback")
        
        self.is_used = True
        self.used_on = timezone.now()
        self.used_amount = use_amount
        self.save(update_fields=['is_used', 'used_on', 'used_amount', 'updated_at'])
    
    def check_and_expire(self):
        """Check if cashback has expired and mark accordingly"""
        if not self.is_expired and timezone.now() > self.expires_at:
            self.is_expired = True
            self.expired_on = timezone.now()
            self.save(update_fields=['is_expired', 'expired_on', 'updated_at'])
            return True
        return False
    
    @classmethod
    def expire_all_stale(cls):
        """Expire all cashback that has passed expiry date"""
        now = timezone.now()
        expired_count = cls.objects.filter(
            is_expired=False,
            is_used=False,
            expires_at__lte=now
        ).update(is_expired=True, expired_on=now)
        return expired_count
    
    @classmethod
    def create_cashback(cls, wallet, amount, booking=None, description="", validity_days=365):
        """Create new cashback entry"""
        cashback = cls.objects.create(
            wallet=wallet,
            booking=booking,
            amount=Decimal(str(amount)),
            expires_at=timezone.now() + timedelta(days=validity_days),
            description=description
        )
        return cashback

