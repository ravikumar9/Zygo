"""
OWNER MOBILE CONTROL SURFACE — FAST TESTS (PHASE 2.7.3.6)
"""

import pytest
from decimal import Decimal

from hotels.models import Hotel, RoomType, PricingSafetyEvent
from hotels.services import OwnerMobileControlService


@pytest.mark.django_db
class TestOwnerMobileControlSurface:
    def test_negotiation_opportunities(self):
        hotel = Hotel.objects.create(
            name="Premium Hotel",
            city_id=1,
            star_rating=5
        )
        room = RoomType.objects.create(
            hotel=hotel,
            name="Suite",
            description="Premium suite",
            base_price=Decimal('9000'),
            cost_price=Decimal('4000'),
            max_occupancy=2
        )

        PricingSafetyEvent.objects.create(
            event_type='OWNER_NEGOTIATION_OPPORTUNITY',
            hotel=hotel,
            room_type=room,
            observed_price=room.base_price,
            safe_price=room.base_price,
            floor_price=Decimal('7000'),
            reason='Opportunity detected',
            metadata_json={'demand_trend': 'SOFT'},
            source='system'
        )

        data = OwnerMobileControlService.get_active_negotiation_opportunities(hotel.id)
        assert data['count'] == 1
        assert data['events'][0]['event_type'] == 'OWNER_NEGOTIATION_OPPORTUNITY'

    def test_pending_nudges(self):
        hotel = Hotel.objects.create(
            name="Budget Hotel",
            city_id=1,
            star_rating=3
        )
        room = RoomType.objects.create(
            hotel=hotel,
            name="Standard",
            description="Budget room",
            base_price=Decimal('2000'),
            cost_price=Decimal('800'),
            max_occupancy=2
        )

        PricingSafetyEvent.objects.create(
            event_type='OWNER_NUDGE_GENERATED',
            hotel=hotel,
            room_type=room,
            observed_price=room.base_price,
            safe_price=Decimal('1800'),
            floor_price=Decimal('900'),
            reason='Smart discount nudge',
            metadata_json={'suggested_discount_percent': 10.0},
            source='system'
        )

        data = OwnerMobileControlService.get_pending_price_nudges(hotel.id)
        assert data['count'] == 1
        assert data['events'][0]['event_type'] == 'OWNER_NUDGE_GENERATED'

    def test_history(self):
        hotel = Hotel.objects.create(
            name="Premium Hotel",
            city_id=1,
            star_rating=5
        )
        room = RoomType.objects.create(
            hotel=hotel,
            name="Suite",
            description="Premium suite",
            base_price=Decimal('9000'),
            cost_price=Decimal('4000'),
            max_occupancy=2
        )

        PricingSafetyEvent.objects.create(
            event_type='OWNER_NEGOTIATION_ACCEPTED',
            hotel=hotel,
            room_type=room,
            observed_price=room.base_price,
            safe_price=room.base_price,
            floor_price=Decimal('7000'),
            reason='Accepted',
            metadata_json={},
            source='admin'
        )
        PricingSafetyEvent.objects.create(
            event_type='OWNER_NUDGE_REJECTED',
            hotel=hotel,
            room_type=room,
            observed_price=room.base_price,
            safe_price=room.base_price,
            floor_price=Decimal('7000'),
            reason='Rejected',
            metadata_json={},
            source='owner'
        )

        data = OwnerMobileControlService.get_history(hotel.id)
        event_types = {e['event_type'] for e in data['events']}
        assert 'OWNER_NEGOTIATION_ACCEPTED' in event_types
        assert 'OWNER_NUDGE_REJECTED' in event_types

    def test_incentives(self):
        hotel = Hotel.objects.create(
            name="Premium Hotel",
            city_id=1,
            star_rating=5
        )

        PricingSafetyEvent.objects.create(
            event_type='OWNER_INCENTIVE_GRANTED',
            hotel=hotel,
            room_type=None,
            observed_price=None,
            safe_price=None,
            floor_price=None,
            reason='Incentive granted',
            metadata_json={'incentive_amount': 5000},
            source='system'
        )

        data = OwnerMobileControlService.get_incentives(hotel.id)
        assert data['count'] == 1
        assert data['events'][0]['event_type'] == 'OWNER_INCENTIVE_GRANTED'
