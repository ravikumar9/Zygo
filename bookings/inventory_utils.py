"""Inventory helpers for hotel bookings (Phase-2).

These helpers work on RoomAvailability rows to ensure inventory is reduced on
reservation and restored on cancellation. Callers should wrap operations in an
atomic transaction to avoid race conditions.
"""
from datetime import timedelta
from hotels.models import RoomAvailability, RoomType


def _date_range(check_in, check_out):
    """Return list of dates from check_in (inclusive) to check_out (exclusive)."""
    days = (check_out - check_in).days
    return [check_in + timedelta(days=i) for i in range(max(days, 0))]


def _get_available_rooms(room_type, target_date):
    """Fetch available rooms for a date, defaulting to total_rooms when missing."""
    availability = (
        RoomAvailability.objects.select_for_update()
        .filter(room_type=room_type, date=target_date)
        .first()
    )
    if availability:
        return availability.available_rooms
    return room_type.total_rooms or 0


def reserve_inventory(room_type: RoomType, check_in, check_out, num_rooms: int):
    """Reduce availability for each night in the stay.

    Raises ValueError if any date has insufficient availability.
    """
    if num_rooms <= 0:
        return

    dates = _date_range(check_in, check_out)
    # First pass: validate availability
    for current_date in dates:
        available = _get_available_rooms(room_type, current_date)
        if available < num_rooms:
            raise ValueError(f"Only {available} rooms available on {current_date}")

    # Second pass: apply reductions
    for current_date in dates:
        availability, _ = RoomAvailability.objects.select_for_update().get_or_create(
            room_type=room_type,
            date=current_date,
            defaults={
                'available_rooms': room_type.total_rooms or 0,
                'price': room_type.base_price,
            },
        )
        availability.available_rooms = max(availability.available_rooms - num_rooms, 0)
        availability.save(update_fields=['available_rooms'])


def restore_inventory(room_type: RoomType, check_in, check_out, num_rooms: int):
    """Restore availability after cancellation."""
    if num_rooms <= 0:
        return

    dates = _date_range(check_in, check_out)
    for current_date in dates:
        availability, _ = RoomAvailability.objects.select_for_update().get_or_create(
            room_type=room_type,
            date=current_date,
            defaults={
                'available_rooms': room_type.total_rooms or 0,
                'price': room_type.base_price,
            },
        )
        availability.available_rooms += num_rooms
        availability.save(update_fields=['available_rooms'])
