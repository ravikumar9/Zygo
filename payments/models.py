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
    """User invoice model - immutable snapshot at booking confirmation"""
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='invoice')
    
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField(auto_now_add=True)
    
    # Billing details
    billing_name = models.CharField(max_length=200)
    billing_email = models.EmailField()
    billing_phone = models.CharField(max_length=15)
    billing_address = models.TextField()
    
    # Immutable booking snapshot
    property_name = models.CharField(max_length=200, blank=True)
    check_in = models.DateField(null=True, blank=True)
    check_out = models.DateField(null=True, blank=True)
    num_rooms = models.IntegerField(default=1)
    meal_plan = models.CharField(max_length=100, blank=True)
    
    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    service_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    wallet_used = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Payment info
    payment_mode = models.CharField(max_length=50, blank=True)
    payment_timestamp = models.DateTimeField(null=True, blank=True)
    
    # Tax details
    cgst = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sgst = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    igst = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    pdf_file = models.FileField(upload_to='invoices/', null=True, blank=True)
    
    def __str__(self):
        return f"Invoice {self.invoice_number}"
    
    @classmethod
    def create_for_booking(cls, booking, payment=None):
        """Create invoice after successful booking payment - immutable snapshot"""
        import random
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        random_suffix = random.randint(1000, 9999)
        invoice_number = f"INV-{timestamp}-{random_suffix}"
        
        # Get booking details
        hotel_booking = getattr(booking, 'hotel_details', None)
        property_name = ''
        check_in = None
        check_out = None
        num_rooms = 1
        meal_plan = ''
        
        if hotel_booking:
            property_name = hotel_booking.room_type.hotel.name if hotel_booking.room_type else ''
            check_in = hotel_booking.check_in
            check_out = hotel_booking.check_out
            num_rooms = hotel_booking.number_of_rooms or 1
            if hotel_booking.meal_plan:
                meal_plan = hotel_booking.meal_plan.name
        
        # Get pricing snapshot
        price_snapshot = {}
        service_fee = Decimal('0')
        if hotel_booking and hasattr(hotel_booking, 'price_snapshot'):
            price_snapshot = hotel_booking.price_snapshot or {}
            service_fee = Decimal(str(price_snapshot.get('service_fee', 0)))
        
        wallet_used = booking.wallet_balance_before - booking.wallet_balance_after if (booking.wallet_balance_before and booking.wallet_balance_after) else Decimal('0')
        
        invoice = cls.objects.create(
            booking=booking,
            invoice_number=invoice_number,
            billing_name=booking.customer_name,
            billing_email=booking.customer_email,
            billing_phone=booking.customer_phone,
            billing_address='',
            property_name=property_name,
            check_in=check_in,
            check_out=check_out,
            num_rooms=num_rooms,
            meal_plan=meal_plan,
            subtotal=booking.total_amount - service_fee,
            service_fee=service_fee,
            tax_amount=Decimal('0'),
            wallet_used=wallet_used,
            total_amount=booking.total_amount,
            paid_amount=booking.paid_amount,
            payment_mode=payment.payment_method if payment else '',
            payment_timestamp=booking.confirmed_at,
        )
        return invoice


class Wallet(TimeStampedModel):
    """Closed-loop wallet for users to store balance and cashback"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payment_wallet')
    
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


class PayoutRequest(TimeStampedModel):
    """Property Owner payout requests from wallet to bank (Sprint-1)
    
    Owners can request payouts from their wallet earnings.
    Lifecycle: Requested → Processing → Completed/Failed
    Admin manually approves and processes payouts.
    """
    STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Property owner reference
    owner = models.ForeignKey(
        'property_owners.PropertyOwner',
        on_delete=models.CASCADE,
        related_name='payout_requests'
    )
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='payout_requests'
    )
    
    # Payout details
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Amount to payout (deducted from wallet)"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested')
    
    # Bank details (from PropertyOwner)
    bank_account_name = models.CharField(max_length=200)
    bank_account_number = models.CharField(max_length=20)
    bank_ifsc = models.CharField(max_length=20)
    
    # Processing
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payouts_processed'
    )
    
    # Transaction tracking
    transaction_id = models.CharField(max_length=200, blank=True)
    wallet_transaction = models.ForeignKey(
        WalletTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payout_requests'
    )
    
    # Notes
    notes = models.TextField(blank=True, help_text="Admin notes or failure reason")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', '-created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Payout #{self.id} - {self.owner.business_name} - ₹{self.amount} ({self.status})"
    
    def clean(self):
        """Validate payout request"""
        from django.core.exceptions import ValidationError
        
        # Check wallet has sufficient balance
        if self.wallet.balance < self.amount:
            raise ValidationError(
                f"Insufficient wallet balance. Available: ₹{self.wallet.balance}, Requested: ₹{self.amount}"
            )
        
        # Minimum payout amount
        if self.amount < Decimal('100'):
            raise ValidationError("Minimum payout amount is ₹100")
        
        # Check bank details
        if not all([self.bank_account_name, self.bank_account_number, self.bank_ifsc]):
            raise ValidationError("Bank details are incomplete")
    
    def request_payout(self):
        """Request payout - deduct from wallet and create transaction"""
        from django.db import transaction
        
        with transaction.atomic():
            # Validate
            self.full_clean()
            
            # Deduct from wallet
            previous_balance = self.wallet.balance
            self.wallet.balance -= self.amount
            self.wallet.save(update_fields=['balance', 'updated_at'])
            
            # Create wallet transaction
            wallet_txn = WalletTransaction.objects.create(
                wallet=self.wallet,
                transaction_type='debit',
                amount=self.amount,
                balance_before=previous_balance,
                balance_after=self.wallet.balance,
                description=f"Payout request #{self.id}",
                status='success',
                payment_gateway='internal'
            )
            
            self.wallet_transaction = wallet_txn
            self.status = 'requested'
            self.save()
    
    def approve_and_complete(self, admin_user, transaction_id=""):
        """Admin approves and marks payout as completed"""
        if self.status != 'requested':
            raise ValueError("Only requested payouts can be approved")
        
        self.status = 'completed'
        self.processed_at = timezone.now()
        self.processed_by = admin_user
        self.transaction_id = transaction_id
        self.save()
    
    def reject(self, admin_user, reason=""):
        """Admin rejects payout - refund to wallet"""
        from django.db import transaction as db_transaction
        
        if self.status != 'requested':
            raise ValueError("Only requested payouts can be rejected")
        
        with db_transaction.atomic():
            # Refund to wallet
            previous_balance = self.wallet.balance
            self.wallet.balance += self.amount
            self.wallet.save(update_fields=['balance', 'updated_at'])
            
            # Create refund transaction
            WalletTransaction.objects.create(
                wallet=self.wallet,
                transaction_type='refund',
                amount=self.amount,
                balance_before=previous_balance,
                balance_after=self.wallet.balance,
                description=f"Payout request #{self.id} rejected: {reason}",
                status='success',
                payment_gateway='internal'
            )
            
            self.status = 'failed'
            self.processed_at = timezone.now()
            self.processed_by = admin_user
            self.notes = reason
            self.save()
