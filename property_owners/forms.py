from django import forms
from django.forms import inlineformset_factory
from .models import PropertyOwner, Property, PropertyRoomType
from core.models import City
class PropertyRegistrationForm(forms.ModelForm):
    """Minimal property registration form used in Phase-2 owner draft flow"""
    class Meta:
        model = Property
        fields = [
            'name','description','property_type','city','address','state','pincode',
            'contact_phone','contact_email','property_rules','cancellation_policy',
            'cancellation_type','cancellation_days','refund_percentage',
            'has_wifi','has_parking','has_pool','has_gym','has_restaurant','has_spa','has_ac',
            'amenities','base_price','currency','gst_percentage','max_guests','num_bedrooms','num_bathrooms',
        ]


class PropertyOwnerRegistrationForm(forms.ModelForm):
    """Registration form for property owners"""
    city = forms.ModelChoiceField(queryset=City.objects.all().order_by('name'), label='City/Location')
    
    class Meta:
        # NOTE: This Meta was malformed; fix to minimal valid structure
        from .models import Property
        model = Property
        fields = '__all__'
    
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


class PropertyRoomTypeForm(forms.ModelForm):
    """Form for creating room types for properties (Phase-2)"""
    
    class Meta:
        model = PropertyRoomType
        fields = [
            'name', 'room_type', 'description', 'max_occupancy', 'number_of_beds',
            'room_size', 'base_price', 'discounted_price', 'total_rooms', 'image'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Deluxe Ocean View Room',
                'required': True
            }),
            'room_type': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Room description, features, amenities...',
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
            'room_size': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'Square feet (optional)'
            }),
            'base_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '1',
                'placeholder': '2000.00',
                'required': True
            }),
            'discounted_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '1',
                'placeholder': 'Optional discount price'
            }),
            'total_rooms': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'value': '1',
                'required': True,
                'help_text': 'Total inventory for this room type'
            }),
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
        
        base_price = cleaned_data.get('base_price', 0)
        if base_price <= 0:
            self.add_error('base_price', 'Base price must be greater than 0')
        
        discounted_price = cleaned_data.get('discounted_price')
        if discounted_price and discounted_price >= base_price:
            self.add_error('discounted_price', 'Discounted price must be less than base price')
        
        total_rooms = cleaned_data.get('total_rooms', 0)
        if total_rooms <= 0:
            self.add_error('total_rooms', 'At least 1 room must be available')
        
        max_occupancy = cleaned_data.get('max_occupancy', 0)
        if max_occupancy <= 0:
            self.add_error('max_occupancy', 'Max occupancy must be at least 1')
        
        return cleaned_data


# PropertyRoomType inline formset (Phase-2: correct FK architecture)
PropertyRoomTypeInlineFormSet = inlineformset_factory(
    Property,
    PropertyRoomType,
    form=PropertyRoomTypeForm,
    extra=2,  # 2 empty forms for additional rooms
    min_num=1,  # MANDATORY: Minimum 1 room type required
    validate_min=True,
    can_delete=True
)
