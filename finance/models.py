"""Finance models for owner payouts and platform ledger"""
from django.db import models
from django.conf import settings
from decimal import Decimal
from core.models import TimeStampedModel
from bookings.models import Booking
from hotels.models import Hotel


class OwnerPayout(TimeStampedModel):
    """Property owner payout/settlement model - Phase 4"""
    
    SETTLEMENT_STATUS = [
        ('pending', 'Pending'),
        ('kyc_pending', 'KYC Pending'),
        ('bank_pending', 'Bank Details Pending'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('retry', 'Retry'),
    ]
    
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='owner_payout')
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='payouts')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='property_payouts')
    
    # Amounts (immutable - from snapshot)
    gross_booking_value = models.DecimalField(max_digits=12, decimal_places=2)  # From price_snapshot
    platform_service_fee = models.DecimalField(max_digits=10, decimal_places=2)  # 5% capped at ₹500
    refunds_issued = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # If cancelled
    penalties = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # If applicable
    net_payable_to_owner = models.DecimalField(max_digits=12, decimal_places=2)  # gross - fees - refunds - penalties
    
    # Status & Validation
    booking_status = models.CharField(max_length=20)  # confirmed/cancelled/refunded
    settlement_status = models.CharField(max_length=20, choices=SETTLEMENT_STATUS, default='pending')
    
    # KYC & Bank Verification Flags
    kyc_verified = models.BooleanField(default=False)
    bank_verified = models.BooleanField(default=False)
    can_payout = models.BooleanField(default=False)  # Computed: kyc_verified AND bank_verified
    block_reason = models.CharField(max_length=200, blank=True)  # Why payout is blocked
    
    # Bank Account Snapshot (immutable at time of payout)
    bank_account_name = models.CharField(max_length=200, blank=True)
    bank_account_number = models.CharField(max_length=20, blank=True)
    bank_ifsc = models.CharField(max_length=20, blank=True)
    
    # Settlement tracking
    settled_at = models.DateTimeField(null=True, blank=True)
    settlement_reference = models.CharField(max_length=200, blank=True)  # Bank transfer reference
    retry_count = models.IntegerField(default=0)
    last_retry_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payout for booking {self.booking.booking_id} - {self.settlement_status}"
    
    def validate_kyc_and_bank(self):
        """Check if owner has KYC and bank verified, update flags"""
        from property_owners.models import PropertyOwner
        from django.utils import timezone
        
        try:
            owner_profile = PropertyOwner.objects.get(user=self.owner)
            
            # Check KYC
            kyc_ok = owner_profile.verification_status == 'verified'
            
            # Check Bank Details
            bank_ok = (
                owner_profile.bank_account_name and
                owner_profile.bank_account_number and
                owner_profile.bank_ifsc
            )
            
            self.kyc_verified = kyc_ok
            self.bank_verified = bank_ok
            self.can_payout = kyc_ok and bank_ok
            
            # Update block reason
            if not kyc_ok:
                self.block_reason = 'KYC not verified'
                self.settlement_status = 'kyc_pending'
            elif not bank_ok:
                self.block_reason = 'Bank details incomplete'
                self.settlement_status = 'bank_pending'
            else:
                self.block_reason = ''
                if self.settlement_status in ['kyc_pending', 'bank_pending']:
                    self.settlement_status = 'pending'
            
            # Snapshot bank details if not already set
            if not self.bank_account_name and bank_ok:
                self.bank_account_name = owner_profile.bank_account_name
                self.bank_account_number = owner_profile.bank_account_number
                self.bank_ifsc = owner_profile.bank_ifsc
            
            self.save()
            return self.can_payout
            
        except PropertyOwner.DoesNotExist:
            self.kyc_verified = False
            self.bank_verified = False
            self.can_payout = False
            self.block_reason = 'No owner profile'
            self.settlement_status = 'kyc_pending'
            self.save()
            return False
    
    def execute_payout(self, bank_transfer_id=None):
        """Execute payout - marks as paid if successful
        
        Args:
            bank_transfer_id: Reference ID from bank transfer API
            
        Returns:
            bool: True if payout successful, False otherwise
        """
        from django.utils import timezone
        
        # Validate preconditions
        if not self.can_payout:
            self.settlement_status = 'failed'
            self.failure_reason = self.block_reason or 'KYC/Bank verification failed'
            self.save()
            return False
        
        if self.settlement_status == 'paid':
            return True  # Already paid
        
        try:
            self.settlement_status = 'processing'
            self.last_retry_at = timezone.now()
            self.save()
            
            # In production, integrate with bank transfer API here
            # For now, simulate successful transfer
            transfer_successful = True  # TODO: call actual bank API
            
            if transfer_successful:
                self.settlement_status = 'paid'
                self.settled_at = timezone.now()
                self.settlement_reference = bank_transfer_id or f"TXN-{self.id}-{timezone.now().timestamp()}"
                self.failure_reason = ''
                self.save()
                return True
            else:
                self.settlement_status = 'failed'
                self.retry_count += 1
                self.failure_reason = 'Bank transfer failed'
                self.save()
                return False
                
        except Exception as e:
            self.settlement_status = 'failed'
            self.retry_count += 1
            self.failure_reason = str(e)
            self.save()
            return False
    
    def retry_payout(self):
        """Retry failed payout - max 3 retries"""
        if self.retry_count >= 3:
            self.settlement_status = 'failed'
            self.failure_reason = 'Max retries exceeded'
            self.save()
            return False
        
        return self.execute_payout()
    
    @classmethod
    def create_for_booking(cls, booking):
        """Create payout record when booking is confirmed - uses price_snapshot for immutability"""
        hotel_booking = getattr(booking, 'hotel_details', None)
        if not hotel_booking:
            return None
        
        hotel = hotel_booking.room_type.hotel
        # Get the PropertyOwner, then extract the User
        property_owner = hotel.owner_property.owner if hasattr(hotel, 'owner_property') and hotel.owner_property else None
        
        if not property_owner:
            return None
        
        # owner field expects User instance, not PropertyOwner
        owner_user = property_owner.user if hasattr(property_owner, 'user') else property_owner
        
        # Get pricing snapshot (immutable data from booking confirmation)
        price_snapshot = hotel_booking.price_snapshot or {}
        service_fee = Decimal(str(price_snapshot.get('service_fee', 0)))
        gross_amount = booking.total_amount
        
        # Calculate refunds if booking was cancelled
        refund_amount = Decimal('0')
        if booking.status == 'cancelled':
            refund_amount = booking.refund_amount
        
        # Calculate net payout
        net_payable = gross_amount - service_fee - refund_amount
        
        payout = cls.objects.create(
            booking=booking,
            hotel=hotel,
            owner=owner_user,
            gross_booking_value=gross_amount,
            platform_service_fee=service_fee,
            refunds_issued=refund_amount,
            penalties=Decimal('0'),  # TODO: implement penalty logic
            net_payable_to_owner=net_payable,
            booking_status=booking.status,
            settlement_status='pending',
        )
        
        # Validate KYC/Bank immediately
        payout.validate_kyc_and_bank()
        
        return payout


class PlatformLedger(TimeStampedModel):
    """System-wide financial ledger - aggregated daily"""
    
    date = models.DateField(unique=True)
    
    # Metrics
    total_bookings = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_service_fee_collected = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    wallet_liability = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_refunds = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Cancellations
    total_cancellations = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"Ledger {self.date} - Revenue: ₹{self.total_revenue}"
    
    @classmethod
    def compute_for_date(cls, target_date):
        """Compute or update ledger for a specific date"""
        from django.db.models import Sum, Count
        from payments.models import Wallet
        
        # Get all confirmed bookings for the date
        bookings = Booking.objects.filter(
            confirmed_at__date=target_date,
            status='confirmed'
        )
        
        total_bookings_count = bookings.count()
        total_revenue = bookings.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        
        # Sum service fees
        total_service_fee = Decimal('0')
        for booking in bookings:
            pricing_data = getattr(booking, 'pricing_data', {}) or {}
            service_fee = Decimal(str(pricing_data.get('service_fee', 0)))
            total_service_fee += service_fee
        
        # Wallet liability (all active wallets)
        wallet_liability = Wallet.objects.filter(is_active=True).aggregate(
            total=Sum('balance')
        )['total'] or Decimal('0')
        
        # Cancellations
        cancellations = Booking.objects.filter(
            cancelled_at__date=target_date,
            status='cancelled'
        ).count()
        
        # Refunds
        total_refunds = Booking.objects.filter(
            cancelled_at__date=target_date,
            status='cancelled'
        ).aggregate(total=Sum('refund_amount'))['total'] or Decimal('0')
        
        # Net revenue
        net_revenue = total_service_fee - total_refunds
        
        ledger, created = cls.objects.update_or_create(
            date=target_date,
            defaults={
                'total_bookings': total_bookings_count,
                'total_revenue': total_revenue,
                'total_service_fee_collected': total_service_fee,
                'wallet_liability': wallet_liability,
                'total_refunds': total_refunds,
                'net_revenue': net_revenue,
                'total_cancellations': cancellations,
            }
        )
        return ledger
