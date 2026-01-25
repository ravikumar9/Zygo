# FIX-4 STEP-2: Template Diff & Code Changes

## Summary
Added room-level cancellation policy disclosure to hotel detail page with:
- **Color-coded badges** (Green/Yellow/Red)
- **Collapsible policy text** (Bootstrap collapse)
- **Progressive disclosure** (collapsed by default)
- **Policy locked at booking time** (immutable snapshot)

---

## Template Changes: hotel_detail.html

### CSS Changes (Lines 26-72)

**ADDED**: Styles for policy badges and collapse button

```css
/* FIX-4: Cancellation Policy Styles */
.policy-badge {
    display: inline-block;
    padding: 0.35rem 0.75rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
    margin-right: 0.5rem;
    margin-bottom: 0.5rem;
}
.policy-badge.free {
    background-color: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
}
.policy-badge.partial {
    background-color: #fff3cd;
    color: #856404;
    border: 1px solid #ffeeba;
}
.policy-badge.non-refundable {
    background-color: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
}
.policy-collapse-btn {
    cursor: pointer;
    color: #0066cc;
    text-decoration: none;
    font-size: 0.9rem;
    padding: 0;
    border: none;
    background: none;
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
}
.policy-collapse-btn:hover {
    text-decoration: underline;
}
.policy-text {
    font-size: 0.85rem;
    color: #555;
    line-height: 1.4;
    margin-top: 0.5rem;
}
.chevron-icon {
    transition: transform 0.2s ease;
    display: inline-block;
}
.policy-collapse-btn[aria-expanded="true"] .chevron-icon {
    transform: rotate(180deg);
}
```

### HTML Changes (Lines 199-238)

**BEFORE**:
```html
<div class="col-md-5">
    <h5 class="mb-1">{{ room.name }}</h5>
    <p class="mb-1">Occupancy: {{ room.max_occupancy }}</p>
    <p class="mb-1">Beds: {{ room.number_of_beds }}</p>
    <div class="d-flex flex-wrap gap-2 small text-muted">
        {% if room.has_balcony %}<span><i class="fas fa-door-open"></i> Balcony</span>{% endif %}
        {% if room.has_tv %}<span><i class="fas fa-tv"></i> TV</span>{% endif %}
        {% if room.has_minibar %}<span><i class="fas fa-wine-bottle"></i> Minibar</span>{% endif %}
        {% if room.has_safe %}<span><i class="fas fa-lock"></i> Safe</span>{% endif %}
    </div>
</div>
```

**AFTER**:
```html
<div class="col-md-5">
    <h5 class="mb-1">{{ room.name }}</h5>
    <p class="mb-1">Occupancy: {{ room.max_occupancy }}</p>
    <p class="mb-1">Beds: {{ room.number_of_beds }}</p>
    <div class="d-flex flex-wrap gap-2 small text-muted mb-2">
        {% if room.has_balcony %}<span><i class="fas fa-door-open"></i> Balcony</span>{% endif %}
        {% if room.has_tv %}<span><i class="fas fa-tv"></i> TV</span>{% endif %}
        {% if room.has_minibar %}<span><i class="fas fa-wine-bottle"></i> Minibar</span>{% endif %}
        {% if room.has_safe %}<span><i class="fas fa-lock"></i> Safe</span>{% endif %}
    </div>
    
    <!-- FIX-4: Cancellation Policy Badge & Disclosure (Room Level) -->
    {% with active_policy=room.get_active_cancellation_policy %}
    {% if active_policy %}
    <div class="mb-2">
        {% if active_policy.policy_type == 'FREE' %}
        <span class="policy-badge free">
            <i class="fas fa-check-circle policy-icon"></i>Free Cancellation
        </span>
        {% elif active_policy.policy_type == 'PARTIAL' %}
        <span class="policy-badge partial">
            <i class="fas fa-percent policy-icon"></i>Partial Refund
        </span>
        {% elif active_policy.policy_type == 'NON_REFUNDABLE' %}
        <span class="policy-badge non-refundable">
            <i class="fas fa-ban policy-icon"></i>Non-Refundable
        </span>
        {% endif %}
        
        <button class="policy-collapse-btn" type="button" data-bs-toggle="collapse" 
                data-bs-target="#policy-detail-{{ room.id }}" aria-expanded="false">
            <i class="fas fa-chevron-down chevron-icon"></i>Policy details
        </button>
        
        <div class="collapse" id="policy-detail-{{ room.id }}">
            <div class="policy-text">
                {{ active_policy.policy_text }}
            </div>
        </div>
    </div>
    {% else %}
    <div class="mb-2">
        <span class="policy-badge non-refundable">
            <i class="fas fa-ban policy-icon"></i>Non-Refundable
        </span>
        <p class="policy-text">
            No active policy configured for this room.
        </p>
    </div>
    {% endif %}
    {% endwith %}
</div>
```

---

## Backend Changes

### hotels/models.py: New RoomCancellationPolicy (Lines 340-381)

```python
class RoomCancellationPolicy(TimeStampedModel):
    """Immutable cancellation policy stored at the room level."""

    POLICY_TYPES = [
        ('FREE', 'Free Cancellation'),
        ('PARTIAL', 'Partial Refund'),
        ('NON_REFUNDABLE', 'Non-Refundable'),
    ]

    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.CASCADE,
        related_name='cancellation_policies'
    )
    policy_type = models.CharField(
        max_length=20,
        choices=POLICY_TYPES,
        default='NON_REFUNDABLE'
    )
    free_cancel_until = models.DateTimeField(null=True, blank=True)
    refund_percentage = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percentage of paid amount to refund (0-100)"
    )
    policy_text = models.TextField(help_text="Human-readable policy snapshot")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-is_active', '-created_at']

    def __str__(self):
        return f"{self.room_type.name} - {self.get_policy_type_display()}"

    def as_snapshot(self):
        """Return a dict snapshot to freeze into a booking."""
        return {
            'policy_type': self.policy_type,
            'free_cancel_until': self.free_cancel_until,
            'refund_percentage': self.refund_percentage,
            'policy_text': self.policy_text,
        }
```

### RoomType helper (Lines 335-340)

```python
def get_active_cancellation_policy(self):
    """Return the latest active cancellation policy for this room type."""
    return (
        self.cancellation_policies.filter(is_active=True)
        .order_by('-created_at')
        .first()
    )
```

### bookings/models.py: HotelBooking policy snapshot (Lines 226-276)

```python
class HotelBooking(TimeStampedModel):
    """Hotel booking details"""
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='hotel_details')
    room_type = models.ForeignKey(RoomType, on_delete=models.PROTECT)
    meal_plan = models.ForeignKey('hotels.RoomMealPlan', on_delete=models.PROTECT, related_name='bookings')
    
    # FIX-4: Policy snapshot fields (locked at booking time)
    cancellation_policy = models.ForeignKey(
        RoomCancellationPolicy,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='bookings'
    )
    POLICY_TYPES = [
        ('FREE', 'Free Cancellation'),
        ('PARTIAL', 'Partial Refund'),
        ('NON_REFUNDABLE', 'Non-Refundable'),
    ]
    policy_type = models.CharField(max_length=20, choices=POLICY_TYPES, default='NON_REFUNDABLE')
    policy_free_cancel_until = models.DateTimeField(null=True, blank=True)
    policy_refund_percentage = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    policy_text = models.TextField(blank=True)
    policy_locked_at = models.DateTimeField(null=True, blank=True)
    
    check_in = models.DateField()
    check_out = models.DateField()
    
    number_of_rooms = models.IntegerField(default=1)
    number_of_adults = models.IntegerField(default=1)
    number_of_children = models.IntegerField(default=0)
    
    total_nights = models.IntegerField()
    
    def lock_cancellation_policy(self, policy: RoomCancellationPolicy):
        """Freeze cancellation policy snapshot on the booking if not already locked."""
        if self.policy_locked_at or not policy:
            return

        self.cancellation_policy = policy
        self.policy_type = policy.policy_type
        self.policy_free_cancel_until = policy.free_cancel_until
        self.policy_refund_percentage = policy.refund_percentage
        self.policy_text = policy.policy_text or ''
        self.policy_locked_at = timezone.now()
        self.save(
            update_fields=[
                'cancellation_policy',
                'policy_type',
                'policy_free_cancel_until',
                'policy_refund_percentage',
                'policy_text',
                'policy_locked_at',
                'updated_at',
            ]
        )
    
    def __str__(self):
        return f"Hotel Booking - {self.booking.booking_id}"
```

### hotels/views.py: Book Hotel creates policy snapshot (Lines 845-879)

```python
# At booking creation time, fetch and lock active policy
active_policy = room_type.get_active_cancellation_policy()
policy_type = active_policy.policy_type if active_policy else 'NON_REFUNDABLE'
policy_text = active_policy.policy_text if active_policy else 'Non-refundable booking. Changes and cancellations are not allowed.'
policy_refund_percentage = active_policy.refund_percentage if active_policy else 0
policy_free_cancel_until = active_policy.free_cancel_until if active_policy else None

HotelBooking.objects.create(
    booking=booking,
    room_type=room_type,
    meal_plan=meal_plan,
    cancellation_policy=active_policy,
    policy_type=policy_type,
    policy_text=policy_text,
    policy_refund_percentage=policy_refund_percentage,
    policy_free_cancel_until=policy_free_cancel_until,
    policy_locked_at=timezone.now(),
    check_in=checkin,
    check_out=checkout,
    number_of_rooms=num_rooms,
    number_of_adults=guests,
    total_nights=nights,
)
```

---

## Database Migrations

### Migration 1: hotels/migrations/0016_roomcancellationpolicy.py

Creates the new `RoomCancellationPolicy` table:
- `room_type_id` (FK to RoomType)
- `policy_type` (FREE/PARTIAL/NON_REFUNDABLE)
- `free_cancel_until` (nullable datetime)
- `refund_percentage` (nullable 0-100)
- `policy_text` (text)
- `is_active` (boolean)
- `created_at`, `updated_at` (timestamps)

### Migration 2: bookings/migrations/0014_hotelbooking_policy_snapshot.py

Adds policy snapshot fields to `HotelBooking`:
- `cancellation_policy_id` (FK to RoomCancellationPolicy, nullable)
- `policy_type` (CharField)
- `policy_free_cancel_until` (nullable datetime)
- `policy_refund_percentage` (nullable int)
- `policy_text` (text)
- `policy_locked_at` (nullable datetime)

---

## Line-by-Line Template Change

### Location in File
- **CSS Styles**: Lines 26-72 (inside `{% block extra_css %}`)
- **HTML Policy Section**: Lines 199-238 (inside `.col-md-5` after amenities)

### Key Elements

1. **Policy Badge** (lines 206-213)
   - Conditional rendering based on `active_policy.policy_type`
   - Icons: ✓ (FREE), % (PARTIAL), ⊘ (NON_REFUNDABLE)
   - Bootstrap badge colors

2. **Collapse Button** (lines 215-218)
   - Bootstrap data attributes: `data-bs-toggle="collapse"`, `data-bs-target="#policy-detail-..."`
   - Chevron icon animates on expand
   - Accessible: `aria-expanded="false"`

3. **Policy Details** (lines 220-225)
   - Wrapped in `.collapse` div
   - Displays `active_policy.policy_text`
   - Styled with `.policy-text` class

4. **Fallback** (lines 226-234)
   - If no policy configured, shows "Non-Refundable" with default message

---

## Test Output

### Seeded Policies
```
✅ 108 room types
✅ 108 policies created:
   - 36 FREE (100% refund)
   - 36 PARTIAL (50% refund) 
   - 36 NON_REFUNDABLE (0% refund)
```

### Policy Lock Test
```
✅ Booking created: 359782e5-f148-4f73-b7db-63cb2b295c18
✅ Policy locked: PARTIAL (50% refund)
✅ Policy text captured: "Free cancellation until 48 hours..."
✅ Locked at: 2026-01-21T09:47:05+00:00
✅ Refund amount: ₹5,500 × 50% = ₹2,750 ✓
```

---

## File Statistics

| File | Changes | Lines |
|------|---------|-------|
| hotels/models.py | ADD class | 42 lines |
| hotels/models.py | ADD method | 5 lines |
| bookings/models.py | ADD fields + method | 50 lines |
| hotels/views.py | MODIFY booking creation | 35 lines |
| templates/hotels/hotel_detail.html | ADD CSS | 47 lines |
| templates/hotels/hotel_detail.html | ADD HTML | 40 lines |
| Migrations | NEW x2 | ~70 lines total |

**Total**: ~290 lines of code/markup added

---

## Validation Checklist

- ✅ Policy visible on room cards
- ✅ Color-coded badges working
- ✅ Collapse/expand functional
- ✅ Policy text readable
- ✅ Booking snapshot locked
- ✅ Refund calculation correct
- ✅ No styling conflicts
- ✅ Mobile responsive
- ✅ Browser compatible
- ✅ Fix-1/2/3 untouched

---

## Ready for Step-3

This completes Step-2. Policy is now visible to users on hotel detail page BEFORE they make a selection.

Next step: Make policy visible AGAIN on confirmation & payment pages with locked snapshot.

