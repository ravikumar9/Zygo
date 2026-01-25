from rest_framework import serializers
from decimal import Decimal

from payments.models import Invoice
from .models import OwnerPayout, PlatformLedger
from bookings.models import Booking


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for Invoice model"""
    booking_id = serializers.CharField(source='booking.booking_id', read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'booking_id', 'invoice_number', 'invoice_date',
            'billing_name', 'billing_email', 'billing_phone',
            'property_name', 'check_in', 'check_out', 'num_rooms', 'meal_plan',
            'subtotal', 'service_fee', 'tax_amount', 'discount_amount',
            'wallet_used', 'total_amount', 'paid_amount',
            'payment_mode', 'payment_timestamp',
        ]


class OwnerPayoutSerializer(serializers.ModelSerializer):
    """Serializer for OwnerPayout model"""
    property_name = serializers.CharField(source='property.name', read_only=True)
    booking_id = serializers.CharField(source='booking.booking_id', read_only=True)
    
    class Meta:
        model = OwnerPayout
        fields = [
            'id', 'property_name', 'booking_id',
            'gross_booking_value', 'platform_service_fee',
            'net_payable_to_owner', 'settlement_status',
            'settlement_date', 'payment_reference',
            'created_at'
        ]


class PlatformLedgerSerializer(serializers.ModelSerializer):
    """Serializer for PlatformLedger model"""
    
    class Meta:
        model = PlatformLedger
        fields = [
            'id', 'date',
            'total_bookings', 'total_revenue', 'total_service_fee',
            'total_wallet_liability', 'total_refunds',
            'net_revenue', 'cancellations_count',
            'created_at'
        ]


class DashboardMetricsSerializer(serializers.Serializer):
    """Serializer for dashboard summary metrics"""
    total_bookings = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_service_fee = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_wallet_used = serializers.DecimalField(max_digits=12, decimal_places=2)
    cancellations_count = serializers.IntegerField()
    active_properties = serializers.IntegerField()
    pending_approvals = serializers.IntegerField()


class BookingListSerializer(serializers.ModelSerializer):
    """Serializer for booking list in admin"""
    customer_email = serializers.EmailField()
    wallet_used = serializers.SerializerMethodField()
    
    class Meta:
        model = Booking
        fields = [
            'id', 'booking_id', 'customer_name', 'customer_email',
            'status', 'total_amount', 'wallet_used',
            'created_at'
        ]
    
    def get_wallet_used(self, obj):
        if obj.wallet_balance_before and obj.wallet_balance_after:
            return obj.wallet_balance_before - obj.wallet_balance_after
        return Decimal('0')
