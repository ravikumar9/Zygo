"""
Bus Operator Registration Form - Session 3
Mandatory data collection with strict validation
"""
from django import forms
from django.core.exceptions import ValidationError
from .models import BusOperator, BusRoute, SeatLayout


class OperatorRegistrationForm(forms.ModelForm):
    """
    Complete operator registration with 6 mandatory sections:
    1. Operator Identity
    2. Bus Details
    3. Route Configuration
    4. Pricing Configuration
    5. Policies
    6. Amenities
    """
    
    class Meta:
        model = BusOperator
        fields = [
            # Section 1: Operator Identity
            'company_legal_name', 'name', 'contact_phone', 'contact_email', 
            'operator_office_address', 'gst_number',
            
            # Section 2: Bus Details
            'bus_type', 'total_seats_per_bus', 'fleet_size',
            
            # Section 3: Route Configuration
            'primary_source_city', 'primary_destination_city', 'routes_description',
            
            # Section 4: Pricing Configuration
            'base_fare_per_seat', 'gst_percentage', 'refund_percentage',
            
            # Section 5: Policies
            'cancellation_policy', 'cancellation_cutoff_hours',
            
            # Section 6: Amenities
            'has_ac', 'has_wifi', 'has_charging_point', 'has_blanket', 'has_water_bottle',
        ]
        widgets = {
            # Section 1: Operator Identity
            'company_legal_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., ABC Tours Pvt Ltd',
                'required': True,
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Operating brand name',
                'required': True,
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+91-XXXXXXXXXX',
                'type': 'tel',
                'required': True,
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'company@example.com',
                'required': True,
            }),
            'operator_office_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Full office address with city, state, pincode',
                'required': True,
            }),
            'gst_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '27AABCT1234A1Z5',
                'required': True,
            }),
            
            # Section 2: Bus Details
            'bus_type': forms.Select(attrs={
                'class': 'form-control',
                'required': True,
            }),
            'total_seats_per_bus': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '10',
                'max': '60',
                'placeholder': 'e.g., 45',
                'required': True,
            }),
            'fleet_size': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'Number of buses',
                'required': True,
            }),
            
            # Section 3: Route Configuration
            'primary_source_city': forms.Select(attrs={
                'class': 'form-control',
                'required': True,
            }),
            'primary_destination_city': forms.Select(attrs={
                'class': 'form-control',
                'required': True,
            }),
            'routes_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe your routes, intermediate stops, and departure/arrival times',
                'required': True,
            }),
            
            # Section 4: Pricing Configuration
            'base_fare_per_seat': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'e.g., 500.00',
                'required': True,
            }),
            'gst_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'value': '5',
                'required': True,
            }),
            'refund_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'value': '100',
                'required': True,
            }),
            
            # Section 5: Policies
            'cancellation_policy': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Specify refund conditions, timing, and any charges',
                'required': True,
            }),
            'cancellation_cutoff_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'e.g., 24',
                'required': True,
            }),
            
            # Section 6: Amenities
            'has_ac': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_wifi': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_charging_point': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_blanket': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_water_bottle': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        """Backend validation - NO PARTIAL SUBMISSIONS"""
        cleaned_data = super().clean()
        
        # Check all mandatory fields
        mandatory = {
            'company_legal_name': 'Company legal name',
            'name': 'Operating name',
            'contact_phone': 'Contact phone',
            'contact_email': 'Contact email',
            'operator_office_address': 'Office address',
            'gst_number': 'GST number',
            'bus_type': 'Bus type',
            'total_seats_per_bus': 'Total seats',
            'fleet_size': 'Fleet size',
            'primary_source_city': 'Source city',
            'primary_destination_city': 'Destination city',
            'routes_description': 'Routes description',
            'base_fare_per_seat': 'Base fare',
            'cancellation_policy': 'Cancellation policy',
            'cancellation_cutoff_hours': 'Cancellation cutoff',
        }
        
        missing_fields = []
        for field, label in mandatory.items():
            value = cleaned_data.get(field)
            if not value or (isinstance(value, str) and not value.strip()):
                missing_fields.append(label)
        
        if missing_fields:
            raise ValidationError(
                f"Cannot submit incomplete registration. Missing: {', '.join(missing_fields)}"
            )
        
        # Validate phone format
        phone = cleaned_data.get('contact_phone', '').strip()
        if phone and not (phone.startswith('+91-') or len(phone) >= 10):
            raise ValidationError("Phone must be 10+ digits or +91-XXXXXXXXXX format")
        
        # Validate GST format
        gst = cleaned_data.get('gst_number', '').strip()
        if gst and len(gst) != 15:
            raise ValidationError("GST number must be 15 characters (e.g., 27AABCT1234A1Z5)")
        
        # Validate fares
        base_fare = cleaned_data.get('base_fare_per_seat')
        if base_fare and base_fare <= 0:
            raise ValidationError("Base fare must be greater than 0")
        
        # Validate seats
        seats = cleaned_data.get('total_seats_per_bus')
        if seats and (seats < 10 or seats > 60):
            raise ValidationError("Seats must be between 10 and 60")
        
        fleet = cleaned_data.get('fleet_size')
        if fleet and fleet < 1:
            raise ValidationError("Fleet size must be at least 1")
        
        # Validate source != destination
        src = cleaned_data.get('primary_source_city')
        dst = cleaned_data.get('primary_destination_city')
        if src and dst and src == dst:
            raise ValidationError("Source and destination cities must be different")
        
        return cleaned_data
    
    def clean_company_legal_name(self):
        value = self.cleaned_data.get('company_legal_name')
        if value and not value.strip():
            raise ValidationError("Company legal name cannot be empty")
        if value and len(value.strip()) < 5:
            raise ValidationError("Company legal name must be at least 5 characters")
        return value.strip() if value else value
    
    def clean_operator_office_address(self):
        value = self.cleaned_data.get('operator_office_address')
        if value and not value.strip():
            raise ValidationError("Office address cannot be empty")
        if value and len(value.strip()) < 10:
            raise ValidationError("Office address must be at least 10 characters")
        return value.strip() if value else value
    
    def clean_routes_description(self):
        value = self.cleaned_data.get('routes_description')
        if value and not value.strip():
            raise ValidationError("Routes description cannot be empty")
        if value and len(value.strip()) < 20:
            raise ValidationError("Routes description must be at least 20 characters")
        return value.strip() if value else value
    
    def clean_cancellation_policy(self):
        value = self.cleaned_data.get('cancellation_policy')
        if value and not value.strip():
            raise ValidationError("Cancellation policy cannot be empty")
        if value and len(value.strip()) < 20:
            raise ValidationError("Cancellation policy must be at least 20 characters")
        return value.strip() if value else value
