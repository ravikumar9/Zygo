"""
OWNER MOBILE CONTROL SURFACE — READ-ONLY INTELLIGENCE (PHASE 2.7.3.6)

Provides owner-facing, read-only views:
- Active negotiation opportunities
- Pending price nudges
- Accepted/rejected history
- Incentives earned

Event-sourced only (PricingSafetyEvent). No auto pricing.
"""

from datetime import timedelta
from typing import Dict, List

from django.utils import timezone

from hotels.models import PricingSafetyEvent
from hotels.services.safe_query import SafeQuery


class OwnerMobileControlService:
    """
    Read-only aggregation for owner mobile control surface.
    """

    @staticmethod
    def get_active_negotiation_opportunities(hotel_id: int, days: int = 30) -> Dict:
        cutoff = timezone.now() - timedelta(days=days)
        events = OwnerMobileControlService._fetch_events(
            hotel_id=hotel_id,
            event_types=['OWNER_NEGOTIATION_OPPORTUNITY'],
            cutoff=cutoff,
            limit=50,
            operation_name='MobileNegotiationOpportunities'
        )
        return OwnerMobileControlService._serialize_events(events, label='negotiation_opportunities')

    @staticmethod
    def get_pending_price_nudges(hotel_id: int, days: int = 7) -> Dict:
        cutoff = timezone.now() - timedelta(days=days)
        events = OwnerMobileControlService._fetch_events(
            hotel_id=hotel_id,
            event_types=['OWNER_NUDGE_GENERATED'],
            cutoff=cutoff,
            limit=50,
            operation_name='MobilePendingNudges'
        )
        return OwnerMobileControlService._serialize_events(events, label='pending_nudges')

    @staticmethod
    def get_history(hotel_id: int, days: int = 60) -> Dict:
        cutoff = timezone.now() - timedelta(days=days)
        events = OwnerMobileControlService._fetch_events(
            hotel_id=hotel_id,
            event_types=[
                'OWNER_NUDGE_ACCEPTED',
                'OWNER_NUDGE_REJECTED',
                'OWNER_NEGOTIATION_ACCEPTED',
                'OWNER_NEGOTIATION_REJECTED',
                'OWNER_NEGOTIATION_COUNTERED',
            ],
            cutoff=cutoff,
            limit=100,
            operation_name='MobileHistory'
        )
        return OwnerMobileControlService._serialize_events(events, label='history')

    @staticmethod
    def get_incentives(hotel_id: int, days: int = 365) -> Dict:
        cutoff = timezone.now() - timedelta(days=days)
        events = OwnerMobileControlService._fetch_events(
            hotel_id=hotel_id,
            event_types=['OWNER_INCENTIVE_GRANTED'],
            cutoff=cutoff,
            limit=50,
            operation_name='MobileIncentives'
        )
        return OwnerMobileControlService._serialize_events(events, label='incentives')

    @staticmethod
    def _fetch_events(
        hotel_id: int,
        event_types: List[str],
        cutoff,
        limit: int,
        operation_name: str
    ):
        return SafeQuery.safe_queryset(
            lambda: PricingSafetyEvent.objects.filter(
                hotel_id=hotel_id,
                event_type__in=event_types,
                created_at__gte=cutoff
            ).select_related('hotel', 'room_type').order_by('-created_at')[:limit],
            model_class=PricingSafetyEvent,
            operation_name=operation_name
        )

    @staticmethod
    def _serialize_events(events, label: str) -> Dict:
        serialized = [
            {
                'event_type': e.event_type,
                'hotel_id': e.hotel_id,
                'room_type_id': e.room_type_id,
                'observed_price': float(e.observed_price) if e.observed_price is not None else None,
                'safe_price': float(e.safe_price) if e.safe_price is not None else None,
                'floor_price': float(e.floor_price) if e.floor_price is not None else None,
                'reason': e.reason,
                'metadata': e.metadata_json,
                'created_at': e.created_at.isoformat(),
            }
            for e in events
        ]

        return {
            'label': label,
            'events': serialized,
            'count': len(serialized),
            'retrieved_at': timezone.now().isoformat(),
        }
