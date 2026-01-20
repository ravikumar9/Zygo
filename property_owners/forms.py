from django import forms
from django.forms import inlineformset_factory
from .models import PropertyOwner, Property
from hotels.models import RoomType
from core.models import City


class PropertyOwnerRegistrationForm(forms.ModelForm):
    """Registration form for property owners"""
    city = forms.ModelChoiceField(queryset=City.objects.all().order_by('name'), label='City/Location')
    
    class Meta:
        model = PropertyOwner
        fields = [
            'business_name', 'property_type', 'description', 'owner_name',
            'owner_phone', 'owner_email', 'city', 'address', 'pincode',
            'gst_number', 'pan_number', 'bank_account_name',
            'bank_account_number', 'bank_ifsc'
        ]
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your property business name'}),
            'property_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe your property...'}),
            'owner_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your full name'}),
            'owner_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 XXXXXXXXXX'}),
            'owner_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'your@email.com'}),
            'city': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Full property address'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '560001'}),
            'gst_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional: XX XXXXX XXXX X XXX'}),
            'pan_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional: XXXXX XXXXX XXXXX'}),
            'bank_account_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Account holder name'}),
            'bank_account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Account number'}),
            'bank_ifsc': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'IFSC code'}),
        }


class PropertyRegistrationForm(forms.ModelForm):
    """
    Comprehensive property registration form enforcing ALL mandatory data collection.
    NO PARTIAL SUBMISSIONS - Backend validates all required fields.
    """
    
    # Declare multi-select checkboxes for amenities
    amenities_list = forms.MultipleChoiceField(
        choices=[
            ('wifi', '📶 WiFi'),
            ('parking', '🅿️ Parking'),
            ('pool', '🏊 Pool'),
            ('gym', '💪 Gym'),
            ('restaurant', '🍽️ Restaurant'),
            ('spa', '🧖 Spa'),
            ('ac', '❄️ Air Conditioning'),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True,
        label='Amenities (Select at least one)',
        help_text='Property features and facilities'
    )
    
    checkin_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        required=True,
        help_text='e.g., 14:00 (2 PM)'
    )
    
    checkout_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        required=True,
        help_text='e.g., 11:00 (11 AM)'
    )
    
    cancellation_type = forms.ChoiceField(
        choices=Property._meta.get_field('cancellation_type').choices,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        required=True,
        label='Cancellation Policy Type'
    )
    
    cancellation_days = forms.IntegerField(
        min_value=1,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Days before check-in'}),
        help_text='(Required if "X days before check-in" is selected)'
    )
    
    class Meta:
        model = Property
        fields = [
            # SECTION 1: CORE DETAILS (MANDATORY)
            'name', 'description', 'property_type',
            # SECTION 2: LOCATION (MANDATORY)
            'city', 'address', 'state', 'pincode',
            # SECTION 3: CONTACT (MANDATORY)
            'contact_phone', 'contact_email',
            # SECTION 4: RULES & POLICIES (MANDATORY)
            'property_rules',
            # SECTION 5: CAPACITY (MANDATORY)
            'max_guests', 'num_bedrooms', 'num_bathrooms',
            # SECTION 6: PRICING (MANDATORY)
            'base_price', 'gst_percentage', 'currency',
            # SECTION 7: CANCELLATION (MANDATORY)
            'cancellation_policy', 'refund_percentage',
        ]
        
        widgets = {
            # SECTION 1: CORE DETAILS
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Ocean View Villa',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Describe your property - location, style, unique features...',
                'required': True
            }),
            'property_type': forms.Select(attrs={'class': 'form-select', 'required': True}),
            
            # SECTION 2: LOCATION
            'city': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Full address with street, building number',
                'required': True
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Karnataka',
                'required': True
            }),
            'pincode': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '560001',
                'required': True,
                'maxlength': '10'
            }),
            
            # SECTION 3: CONTACT
            'contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'tel',
                'placeholder': '+91 9876543210',
                'required': True
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'contact@property.com',
                'required': True
            }),
            
            # SECTION 4: RULES & POLICIES
            'property_rules': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Check-in/out policies, pet policy, house rules, smoking policy, etc.',
                'required': True
            }),
            
            # SECTION 5: CAPACITY
            'max_guests': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'required': True
            }),
            'num_bedrooms': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'required': True
            }),
            'num_bathrooms': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'required': True
            }),
            
            # SECTION 6: PRICING
            'base_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '1',
                'placeholder': '1000.00',
                'required': True
            }),
            'gst_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'value': '18',
                'required': True
            }),
            'currency': forms.TextInput(attrs={
                'class': 'form-control',
                'value': 'INR',
                'readonly': True,
                'maxlength': '3'
            }),
            
            # SECTION 7: CANCELLATION
            'cancellation_policy': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Detailed cancellation policy and refund terms',
                'required': True
            }),
            'refund_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'value': '100',
                'required': True
            }),
        }
    
    def clean(self):
        """Backend validation - NO PARTIAL SUBMISSIONS ALLOWED"""
        cleaned_data = super().clean()
        
        # CORE DETAILS validation
        if not cleaned_data.get('name') or not cleaned_data['name'].strip():
            self.add_error('name', 'Property name is required')
        
        if not cleaned_data.get('description') or not cleaned_data['description'].strip():
            self.add_error('description', 'Description is required')
        
        if not cleaned_data.get('property_type'):
            self.add_error('property_type', 'Property type is required')
        
        # LOCATION validation
        if not cleaned_data.get('city'):
            self.add_error('city', 'City is required')
        
        if not cleaned_data.get('address') or not cleaned_data['address'].strip():
            self.add_error('address', 'Address is required')
        
        if not cleaned_data.get('state') or not cleaned_data['state'].strip():
            self.add_error('state', 'State is required')
        
        if not cleaned_data.get('pincode') or not str(cleaned_data['pincode']).strip():
            self.add_error('pincode', 'Pincode is required')
        
        # CONTACT validation
        if not cleaned_data.get('contact_phone') or not str(cleaned_data['contact_phone']).strip():
            self.add_error('contact_phone', 'Contact phone is required')
        
        if not cleaned_data.get('contact_email') or not str(cleaned_data['contact_email']).strip():
            self.add_error('contact_email', 'Contact email is required')
        
        # RULES validation
        if not cleaned_data.get('property_rules') or not cleaned_data['property_rules'].strip():
            self.add_error('property_rules', 'Property rules are required')
        
        # CAPACITY validation
        if not cleaned_data.get('max_guests') or cleaned_data['max_guests'] < 1:
            self.add_error('max_guests', 'Max guests must be at least 1')
        
        if not cleaned_data.get('num_bedrooms') or cleaned_data['num_bedrooms'] < 1:
            self.add_error('num_bedrooms', 'At least 1 bedroom is required')
        
        if not cleaned_data.get('num_bathrooms') or cleaned_data['num_bathrooms'] < 1:
            self.add_error('num_bathrooms', 'At least 1 bathroom is required')
        
        # PRICING validation
        if not cleaned_data.get('base_price') or cleaned_data['base_price'] <= 0:
            self.add_error('base_price', 'Valid price is required (> 0)')
        
        # CANCELLATION validation
        if not cleaned_data.get('cancellation_policy') or not cleaned_data['cancellation_policy'].strip():
            self.add_error('cancellation_policy', 'Cancellation policy is required')
        
        if not cleaned_data.get('cancellation_type'):
            self.add_error('cancellation_type', 'Cancellation type is required')
        
        # If cancellation type is "X days before check-in", validate cancellation_days
        if cleaned_data.get('cancellation_type') == 'x_days_before':
            if not cleaned_data.get('cancellation_days') or cleaned_data['cancellation_days'] < 1:
                self.add_error('cancellation_days', 'Number of days is required for X-day cancellation policy')
        
        # AMENITIES validation
        if not self.cleaned_data.get('amenities_list') or len(self.cleaned_data['amenities_list']) == 0:
            self.add_error('amenities_list', 'Select at least one amenity')
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save form data and set amenities based on selection"""
        instance = super().save(commit=False)
        
        # Set amenity flags based on checkbox selection
        amenities = self.cleaned_data.get('amenities_list', [])
        instance.has_wifi = 'wifi' in amenities
        instance.has_parking = 'parking' in amenities
        instance.has_pool = 'pool' in amenities
        instance.has_gym = 'gym' in amenities
        instance.has_restaurant = 'restaurant' in amenities
        instance.has_spa = 'spa' in amenities
        instance.has_ac = 'ac' in amenities
        
        # Set check-in/out times
        instance.checkin_time = self.cleaned_data.get('checkin_time')
        instance.checkout_time = self.cleaned_data.get('checkout_time')
        
        # Set cancellation days if needed
        instance.cancellation_days = self.cleaned_data.get('cancellation_days')
        
        if commit:
            instance.save()
        
        return instance

class RoomTypeForm(forms.ModelForm):
    """Form for creating room types during property registration"""
    
    class Meta:
        model = RoomType
        fields = ['name', 'room_type', 'description', 'max_occupancy', 'number_of_beds', 
                  'base_price', 'total_rooms', 'has_balcony', 'has_tv', 'has_minibar', 
                  'has_safe', 'image']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Deluxe Room',
                'required': True
            }),
            'room_type': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Room description, features, view...',
                'required': True
            }),
            'max_occupancy': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'value': '2',
                'required': True
            }),
            'number_of_beds': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'value': '1',
                'required': True
            }),
            'base_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '1',
                'placeholder': '2000.00',
                'required': True
            }),
            'total_rooms': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'value': '1',
                'required': True,
                'help_text': 'Total number of this room type available'
            }),
            'has_balcony': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_tv': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_minibar': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_safe': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }
    
    def clean(self):
        """Validate room type data"""
        cleaned_data = super().clean()
        
        if not cleaned_data.get('name') or not cleaned_data['name'].strip():
            self.add_error('name', 'Room name is required')
        
        if not cleaned_data.get('description') or not cleaned_data['description'].strip():
            self.add_error('description', 'Room description is required')
        
        if cleaned_data.get('base_price', 0) <= 0:
            self.add_error('base_price', 'Price must be greater than 0')
        
        if cleaned_data.get('total_rooms', 0) <= 0:
            self.add_error('total_rooms', 'At least 1 room must be available')
        
        if cleaned_data.get('max_occupancy', 0) <= 0:
            self.add_error('max_occupancy', 'Max occupancy must be at least 1')
        
        return cleaned_data


# Django inline formset for room types (minimum 1 room required)
RoomTypeInlineFormSet = inlineformset_factory(
    Property,
    RoomType,
    form=RoomTypeForm,
    extra=2,  # 2 empty forms for additional rooms
    min_num=1,  # MANDATORY: Minimum 1 room type required
    validate_min=True,
    can_delete=True
)