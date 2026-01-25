
from django import forms
from django.forms import inlineformset_factory
from .models import PropertyOwner, Property, PropertyRoomType
from core.models import City
from hotels.models import RoomType

class MultiFileInput(forms.ClearableFileInput):
    # Allow multi-upload for room gallery
    allow_multiple_selected = True


class PropertyRegistrationForm(forms.ModelForm):
    """Property draft/submission form with hard validation for go-live readiness."""

    AMENITY_CHOICES = [
        ('wifi', 'WiFi'),
        ('parking', 'Parking'),
        ('pool', 'Swimming Pool'),
        ('gym', 'Gym'),
        ('restaurant', 'Restaurant'),
        ('spa', 'Spa'),
        ('ac', 'Air Conditioning'),
    ]

    amenities_list = forms.MultipleChoiceField(
        choices=AMENITY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label='Amenities'
    )

    class Meta:
        model = Property
        fields = [
            'name','description','property_type','city','address','state','pincode',
            'contact_phone','contact_email','property_rules','cancellation_policy',
            'cancellation_type','cancellation_days','refund_percentage',
            'has_wifi','has_parking','has_pool','has_gym','has_restaurant','has_spa','has_ac',
            'amenities','base_price','currency','gst_percentage','max_guests','num_bedrooms','num_bathrooms',
            'checkin_time','checkout_time','image'
        ]
        widgets = {
            'checkin_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'checkout_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-select amenity checkboxes based on stored flags when editing
        initial_amenities = []
        if getattr(self.instance, 'id', None):
            if self.instance.has_wifi:
                initial_amenities.append('wifi')
            if self.instance.has_parking:
                initial_amenities.append('parking')
            if self.instance.has_pool:
                initial_amenities.append('pool')
            if self.instance.has_gym:
                initial_amenities.append('gym')
            if self.instance.has_restaurant:
                initial_amenities.append('restaurant')
            if self.instance.has_spa:
                initial_amenities.append('spa')
            if self.instance.has_ac:
                initial_amenities.append('ac')
        if initial_amenities:
            self.initial.setdefault('amenities_list', initial_amenities)

    def clean(self):
        cleaned_data = super().clean()

        # CORE DETAILS validation
        if not cleaned_data.get('name') or not str(cleaned_data.get('name', '')).strip():
            self.add_error('name', 'Property name is required')

        if not cleaned_data.get('description') or not str(cleaned_data.get('description', '')).strip():
            self.add_error('description', 'Description is required')

        if not cleaned_data.get('property_type'):
            self.add_error('property_type', 'Property type is required')

        # LOCATION validation
        if not cleaned_data.get('city'):
            self.add_error('city', 'City is required')

        if not cleaned_data.get('address') or not str(cleaned_data.get('address', '')).strip():
            self.add_error('address', 'Address is required')

        if not cleaned_data.get('state') or not str(cleaned_data.get('state', '')).strip():
            self.add_error('state', 'State is required')

        if not cleaned_data.get('pincode') or not str(cleaned_data.get('pincode', '')).strip():
            self.add_error('pincode', 'Pincode is required')

        # CONTACT validation
        if not cleaned_data.get('contact_phone') or not str(cleaned_data.get('contact_phone', '')).strip():
            self.add_error('contact_phone', 'Contact phone is required')

        if not cleaned_data.get('contact_email') or not str(cleaned_data.get('contact_email', '')).strip():
            self.add_error('contact_email', 'Contact email is required')

        # RULES validation
        if not cleaned_data.get('property_rules') or not str(cleaned_data.get('property_rules', '')).strip():
            self.add_error('property_rules', 'Property rules are required')

        if not cleaned_data.get('checkin_time'):
            self.add_error('checkin_time', 'Check-in time is required')

        if not cleaned_data.get('checkout_time'):
            self.add_error('checkout_time', 'Check-out time is required')

        # CAPACITY validation
        if not cleaned_data.get('max_guests') or cleaned_data.get('max_guests', 0) < 1:
            self.add_error('max_guests', 'Max guests must be at least 1')

        if not cleaned_data.get('num_bedrooms') or cleaned_data.get('num_bedrooms', 0) < 1:
            self.add_error('num_bedrooms', 'At least 1 bedroom is required')

        if not cleaned_data.get('num_bathrooms') or cleaned_data.get('num_bathrooms', 0) < 1:
            self.add_error('num_bathrooms', 'At least 1 bathroom is required')

        # PRICING validation
        base_price = cleaned_data.get('base_price')
        if not base_price or base_price <= 0:
            self.add_error('base_price', 'Valid price is required (> 0)')

        # CANCELLATION validation
        if not cleaned_data.get('cancellation_policy') or not str(cleaned_data.get('cancellation_policy', '')).strip():
            self.add_error('cancellation_policy', 'Cancellation policy is required')

        if not cleaned_data.get('cancellation_type'):
            self.add_error('cancellation_type', 'Cancellation type is required')

        if cleaned_data.get('cancellation_type') == 'x_days_before':
            if not cleaned_data.get('cancellation_days') or cleaned_data.get('cancellation_days', 0) < 1:
                self.add_error('cancellation_days', 'Number of days is required for X-day cancellation policy')

        # AMENITIES validation
        amenities_selected = cleaned_data.get('amenities_list') or []
        if len(amenities_selected) == 0:
            self.add_error('amenities_list', 'Select at least one amenity')

        # IMAGE validation (allow existing image on edits)
        if not cleaned_data.get('image') and not getattr(self.instance, 'image', None):
            self.add_error('image', 'Cover image is required')

        return cleaned_data

    def save(self, commit=True):
        """Save form data and set amenity flags based on selection."""
        instance = super().save(commit=False)

        amenities = self.cleaned_data.get('amenities_list', [])
        instance.has_wifi = 'wifi' in amenities
        instance.has_parking = 'parking' in amenities
        instance.has_pool = 'pool' in amenities
        instance.has_gym = 'gym' in amenities
        instance.has_restaurant = 'restaurant' in amenities
        instance.has_spa = 'spa' in amenities
        instance.has_ac = 'ac' in amenities
        instance.amenities = ', '.join(amenities)

        instance.checkin_time = self.cleaned_data.get('checkin_time')
        instance.checkout_time = self.cleaned_data.get('checkout_time')
        instance.cancellation_days = self.cleaned_data.get('cancellation_days')

        if commit:
            instance.save()

        return instance


class PropertyOwnerRegistrationForm(forms.ModelForm):
    """Registration form for property owners"""
    city = forms.ModelChoiceField(queryset=City.objects.all().order_by('name'), label='City/Location')

    class Meta:
        model = PropertyOwner
        fields = [
            'business_name','property_type','description',
            'owner_name','owner_phone','owner_email',
            'city','address','pincode','latitude','longitude',
            'gst_number','pan_number','business_license',
            'bank_account_name','bank_account_number','bank_ifsc'
        ]

    def clean(self):
        cleaned_data = super().clean()

        required_fields = {
            'business_name': 'Property name is required',
            'property_type': 'Property type is required',
            'description': 'Description is required',
            'owner_name': 'Full name is required',
            'owner_phone': 'Phone number is required',
            'owner_email': 'Email is required',
            'city': 'City is required',
            'address': 'Address is required',
            'pincode': 'Pincode is required',
        }

        for field, msg in required_fields.items():
            value = cleaned_data.get(field)
            if not value or not str(value).strip():
                self.add_error(field, msg)

        return cleaned_data


class PropertyRoomTypeForm(forms.ModelForm):
    """Form for creating room types for properties (Phase-2)"""

    ROOM_AMENITIES = [
        ('balcony', 'Balcony'),
        ('tv', 'TV'),
        ('minibar', 'Minibar'),
        ('safe', 'Safe'),
        ('ac', 'Air Conditioning'),
        ('wifi', 'WiFi'),
    ]

    amenities_list = forms.MultipleChoiceField(
        choices=ROOM_AMENITIES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Room Amenities'
    )

    extra_images = forms.FileField(
        required=False,
        widget=MultiFileInput(attrs={'multiple': True, 'class': 'form-control', 'accept': 'image/*'}),
        help_text="Upload multiple images for this room (first becomes primary if none set)"
    )
    
    # Meal Plan fields (absolute per-night pricing)
    plan_room_only = forms.BooleanField(required=False, label='Room Only')
    price_room_only = forms.DecimalField(required=False, min_value=0, label='Price (Room Only)', widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'e.g., 2000'}))
    
    plan_room_breakfast = forms.BooleanField(required=False, label='Room + Breakfast')
    price_room_breakfast = forms.DecimalField(required=False, min_value=0, label='Price (Room + Breakfast)', widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'e.g., 2400'}))
    
    plan_room_half_board = forms.BooleanField(required=False, label='Room + Breakfast + Lunch/Dinner')
    price_room_half_board = forms.DecimalField(required=False, min_value=0, label='Price (Half Board)', widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'e.g., 3000'}))
    
    plan_room_full_board = forms.BooleanField(required=False, label='Room + All Meals')
    price_room_full_board = forms.DecimalField(required=False, min_value=0, label='Price (Full Board)', widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'e.g., 3600'}))

    class Meta:
        model = PropertyRoomType
        fields = [
            'name', 'room_type', 'description', 'max_occupancy', 'number_of_beds',
            'room_size', 'base_price', 'discount_type', 'discount_value', 'discount_valid_from',
            'discount_valid_to', 'discount_is_active', 'total_rooms', 'image'
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
            'discount_type': forms.Select(attrs={'class': 'form-select'}),
            'discount_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'e.g., 10 (for %) or 500 (for ₹)'
            }),
            'discount_valid_from': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'discount_valid_to': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'discount_is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if getattr(self.instance, 'id', None) and self.instance.amenities:
            self.initial['amenities_list'] = self.instance.amenities
    
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
        
        discount_type = cleaned_data.get('discount_type') or 'none'
        discount_value = cleaned_data.get('discount_value') or 0
        valid_from = cleaned_data.get('discount_valid_from')
        valid_to = cleaned_data.get('discount_valid_to')

        # Mutually exclusive discount type/value
        if discount_type in ['percentage', 'fixed']:
            if discount_value is None or discount_value <= 0:
                self.add_error('discount_value', 'Discount value must be greater than 0')
        else:
            cleaned_data['discount_value'] = 0
            cleaned_data['discount_valid_from'] = None
            cleaned_data['discount_valid_to'] = None
            cleaned_data['discount_is_active'] = False

        if valid_from and valid_to and valid_from > valid_to:
            self.add_error('discount_valid_to', 'Valid to date must be after valid from date')
        
        total_rooms = cleaned_data.get('total_rooms', 0)
        if total_rooms <= 0:
            self.add_error('total_rooms', 'At least 1 room must be available')
        
        max_occupancy = cleaned_data.get('max_occupancy', 0)
        if max_occupancy <= 0:
            self.add_error('max_occupancy', 'Max occupancy must be at least 1')
        
        # Validate meal plan pricing (if selected, price must be provided)
        meal_plan_errors = []
        def _check(plan_field, price_field, plan_name):
            plan_selected = self.cleaned_data.get(plan_field)
            price_value = self.cleaned_data.get(price_field)
            if plan_selected and (price_value is None or price_value <= 0):
                meal_plan_errors.append(f"{plan_name} selected but price missing")
        _check('plan_room_only', 'price_room_only', 'Room Only')
        _check('plan_room_breakfast', 'price_room_breakfast', 'Room + Breakfast')
        _check('plan_room_half_board', 'price_room_half_board', 'Half Board')
        _check('plan_room_full_board', 'price_room_full_board', 'Full Board')
        if meal_plan_errors:
            self.add_error(None, '; '.join(meal_plan_errors))
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Persist amenity selections to JSON list
        amenities_selected = self.cleaned_data.get('amenities_list') or []
        instance.amenities = amenities_selected

        # Normalize discount defaults
        if instance.discount_type == 'none':
            instance.discount_value = 0
            instance.discount_valid_from = None
            instance.discount_valid_to = None
            instance.discount_is_active = False

        if commit:
            instance.save()
            self.save_m2m()
            
            # Persist meal plans to JSON
            meal_plans = []
            if self.cleaned_data.get('plan_room_only') and self.cleaned_data.get('price_room_only'):
                meal_plans.append({'type': 'room_only', 'price': float(self.cleaned_data['price_room_only'])})
            if self.cleaned_data.get('plan_room_breakfast') and self.cleaned_data.get('price_room_breakfast'):
                meal_plans.append({'type': 'room_breakfast', 'price': float(self.cleaned_data['price_room_breakfast'])})
            if self.cleaned_data.get('plan_room_half_board') and self.cleaned_data.get('price_room_half_board'):
                meal_plans.append({'type': 'room_half_board', 'price': float(self.cleaned_data['price_room_half_board'])})
            if self.cleaned_data.get('plan_room_full_board') and self.cleaned_data.get('price_room_full_board'):
                meal_plans.append({'type': 'room_full_board', 'price': float(self.cleaned_data['price_room_full_board'])})
            instance.meal_plans = meal_plans
            instance.save(update_fields=['meal_plans'])

        return instance


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


# ===== PROPERTY REGISTRATION STEP 2: ROOM TYPES COLLECTION =====

class RoomTypeForm(forms.ModelForm):
    """Form for creating/editing room types (Step 2)"""
    
    meal_plans = forms.MultipleChoiceField(
        choices=[],  # Will be populated in __init__
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Available Meal Plans for this Room'
    )
    
    class Meta:
        model = RoomType
        fields = [
            'name', 'room_type', 'description', 
            'max_occupancy', 'number_of_beds', 'room_size',
            'base_price'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Deluxe Ocean View',
                'required': True
            }),
            'room_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe this room type, features, amenities...',
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
                'placeholder': 'Optional - size in sq ft'
            }),
            'base_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '1',
                'placeholder': '₹2000.00',
                'required': True
            }),
        }
    
    def __init__(self, *args, hotel=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.hotel = hotel
        
        # Populate meal plan choices from the hotel
        if hotel:
            from hotels.models import RoomMealPlan
            meal_plans = RoomMealPlan.objects.filter(is_active=True).values_list('id', 'name')
            self.fields['meal_plans'].choices = meal_plans
            
            # If editing, pre-select existing meal plans
            if self.instance.pk:
                selected_ids = self.instance.meal_plans.values_list('id', flat=True)
                self.initial['meal_plans'] = list(selected_ids)
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate required fields
        if not cleaned_data.get('name') or not cleaned_data['name'].strip():
            self.add_error('name', 'Room name is required')
        
        if not cleaned_data.get('description') or not cleaned_data['description'].strip():
            self.add_error('description', 'Room description is required')
        
        base_price = cleaned_data.get('base_price')
        if not base_price or base_price <= 0:
            self.add_error('base_price', 'Price must be greater than ₹0')
        
        max_occ = cleaned_data.get('max_occupancy', 0)
        if max_occ < 1:
            self.add_error('max_occupancy', 'Must accommodate at least 1 guest')
        
        beds = cleaned_data.get('number_of_beds', 0)
        if beds < 1:
            self.add_error('number_of_beds', 'Must have at least 1 bed')
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.hotel:
            instance.hotel = self.hotel
            instance.status = 'DRAFT'  # Always start as DRAFT
        
        if commit:
            instance.save()
            
            # Handle meal plan M2M relationship
            meal_plan_ids = self.cleaned_data.get('meal_plans', [])
            if meal_plan_ids:
                from hotels.models import RoomMealPlan
                plans = RoomMealPlan.objects.filter(id__in=meal_plan_ids)
                instance.meal_plans.set(plans)
        
        return instance

