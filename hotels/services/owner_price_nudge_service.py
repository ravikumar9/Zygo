"""
OWNER PRICE NUDGE ENGINE — SMART DISCOUNT SUGGESTIONS (P0)

Business Logic:
- Monitors competitor prices + demand signals
- Suggests LIMITED, TIME-BOUND discounts to owners
- NEVER auto-applies (requires owner approval)
- Protects margin + floor pricing
- Builds owner trust through transparent suggestions

Core Principles:
1. Owner control — No forced automation
2. Margin protection — Never suggest below floor
3. Trust-first — Use only reliable competitor feeds
4. Time-bounded — All suggestions have expiry
5. Revenue-positive — Expected gain > discount cost

Performance target: < 300ms
"""

import logging
from decimal import Decimal
from datetime import timedelta
from typing import Dict, Optional, Tuple
from django.utils import timezone

from hotels.models import RoomType, PricingSafetyConfig, ShadowRiskEvent, PricingSafetyEvent
from hotels.services.safe_query import SafeQuery, SafeConfig
from hotels.services.margin_suggestion_service import MarginSuggestionService
from hotels.services.competitor_trust_service import CompetitorFeedTrustService
from hotels.services.schema_resolver import BookingSchemaResolver

logger = logging.getLogger(__name__)


class OwnerPriceNudgeService:
    """
    Smart discount suggestion engine for hotel owners.
    
    Analyzes:
    - Competitor pricing (trusted feeds only)
    - Demand pressure (booking velocity)
    - Inventory allocation
    - Historical acceptance patterns
    
    Outputs:
    - Suggested discount amount
    - Expected occupancy + revenue gain
    - Confidence score (0-100)
    - Risk level (LOW/MEDIUM/HIGH)
    """
    
    # Confidence thresholds for nudging
    MIN_CONFIDENCE_FOR_NUDGE = 70
    MIN_COMPETITOR_TRUST = 70  # Only use RELIABLE/USABLE feeds
    
    # Discount limits (safety bounds)
    MAX_DISCOUNT_PERCENT = 20  # Never suggest > 20% off
    MIN_DISCOUNT_PERCENT = 3   # Minimum meaningful discount
    
    # Revenue thresholds
    MIN_EXPECTED_REVENUE_GAIN = Decimal('100.00')  # Must expect at least ₹100 gain
    
    # Duration bounds
    DEFAULT_NUDGE_DURATION_MINUTES = 120  # 2 hours default
    MIN_DURATION_MINUTES = 60
    MAX_DURATION_MINUTES = 720  # 12 hours max
    
    @staticmethod
    def generate_nudge(room_type_id: int) -> Dict:
        """
        Generate smart discount nudge for owner approval.
        
        Args:
            room_type_id: RoomType ID
            
        Returns:
            {
              "should_nudge": bool,
              "suggested_discount_amount": Decimal,
              "suggested_discount_percent": float,
              "suggested_new_price": Decimal,
              "current_price": Decimal,
              "duration_minutes": int,
              "expected_occupancy_gain": float,
              "expected_revenue_gain": Decimal,
              "confidence_score": float (0-100),
              "risk_level": str ("LOW" | "MEDIUM" | "HIGH"),
              "reasoning": str,
              "competitor_context": {...},
              "demand_context": {...},
              "expires_at": datetime,
            }
        
        Safe: Returns valid response even if telemetry unavailable.
        """
        try:
            # Get room type
            room_type = SafeQuery.execute(
                lambda: RoomType.objects.select_related('hotel').get(id=room_type_id),
                fallback=None,
                operation_name=f"GetRoomType_{room_type_id}"
            )
            
            if not room_type:
                return OwnerPriceNudgeService._error_response("Room type not found")

            # Enforce pricing strategy: premium listings use negotiation-only
            hotel = room_type.hotel
            if hotel and hotel.get_pricing_strategy() == 'NEGOTIATION_ONLY':
                return OwnerPriceNudgeService._no_nudge_response(
                    "Negotiation-only pricing strategy",
                    room_type.base_price or Decimal('0')
                )
            
            # Get current price context
            current_price = room_type.base_price or Decimal('1000')
            floor_price = OwnerPriceNudgeService._calculate_floor_price(room_type)
            
            # Get margin suggestion (reuse existing service)
            margin_data = SafeQuery.execute(
                lambda: MarginSuggestionService.get_suggestion(room_type_id),
                fallback={},
                operation_name=f"MarginSuggestion_{room_type_id}"
            )
            
            # Check competitor trust (only use reliable feeds)
            competitor_trust = SafeQuery.execute(
                lambda: CompetitorFeedTrustService.calculate_trust('aggregate'),
                fallback={'trust_score': 0, 'trust_label': 'UNKNOWN'},
                operation_name="CompetitorTrust_Aggregate"
            )
            
            if competitor_trust['trust_score'] < OwnerPriceNudgeService.MIN_COMPETITOR_TRUST:
                return OwnerPriceNudgeService._no_nudge_response(
                    "Competitor feed not reliable enough",
                    current_price
                )
            
            # Get demand pressure
            demand_pressure = margin_data.get('demand_pressure', 'NORMAL')
            bookings_24h = margin_data.get('components', {}).get('bookings_24h', 0)
            
            # DECISION LOGIC: Should we nudge?
            should_nudge, nudge_reason = OwnerPriceNudgeService._should_generate_nudge(
                current_price=current_price,
                floor_price=floor_price,
                demand_pressure=demand_pressure,
                bookings_24h=bookings_24h,
                competitor_trust=competitor_trust['trust_score'],
                margin_confidence=margin_data.get('confidence_score', 0)
            )
            
            if not should_nudge:
                return OwnerPriceNudgeService._no_nudge_response(nudge_reason, current_price)
            
            # COMPUTE NUDGE PARAMETERS
            suggested_discount_percent = OwnerPriceNudgeService._calculate_optimal_discount(
                demand_pressure=demand_pressure,
                competitor_median=margin_data.get('components', {}).get('competitor_median'),
                current_price=current_price,
                floor_price=floor_price
            )
            
            suggested_discount_amount = current_price * Decimal(str(suggested_discount_percent / 100.0))
            suggested_new_price = max(
                current_price - suggested_discount_amount,
                floor_price
            )
            
            # Ensure suggested price respects floor
            if suggested_new_price <= floor_price:
                return OwnerPriceNudgeService._no_nudge_response(
                    "Suggested discount would violate floor price",
                    current_price
                )
            
            # ESTIMATE IMPACT
            expected_occupancy_gain = OwnerPriceNudgeService._estimate_occupancy_gain(
                discount_percent=suggested_discount_percent,
                demand_pressure=demand_pressure
            )
            
            expected_revenue_gain = OwnerPriceNudgeService._estimate_revenue_gain(
                current_price=current_price,
                new_price=suggested_new_price,
                expected_occupancy_gain=expected_occupancy_gain,
                available_inventory=10  # TODO: Get actual allocated inventory
            )
            
            # Check if revenue gain justifies nudge
            if expected_revenue_gain < OwnerPriceNudgeService.MIN_EXPECTED_REVENUE_GAIN:
                return OwnerPriceNudgeService._no_nudge_response(
                    f"Expected revenue gain too small (₹{expected_revenue_gain})",
                    current_price
                )
            
            # COMPUTE CONFIDENCE & RISK
            confidence_score = OwnerPriceNudgeService._calculate_nudge_confidence(
                competitor_trust=competitor_trust['trust_score'],
                margin_confidence=margin_data.get('confidence_score', 0),
                demand_strength=1.0 if demand_pressure == 'LOW' else 0.5
            )
            
            risk_level = OwnerPriceNudgeService._assess_risk_level(
                discount_percent=suggested_discount_percent,
                price_vs_floor=float(suggested_new_price / floor_price) if floor_price > 0 else 1.0,
                confidence_score=confidence_score
            )
            
            # DURATION
            duration_minutes = OwnerPriceNudgeService._calculate_duration(
                demand_pressure=demand_pressure,
                risk_level=risk_level
            )
            
            # REASONING
            reasoning = OwnerPriceNudgeService._generate_reasoning(
                demand_pressure=demand_pressure,
                discount_percent=suggested_discount_percent,
                expected_revenue_gain=expected_revenue_gain,
                competitor_context=competitor_trust,
                confidence_score=confidence_score
            )

            # Log event for owner mobile surface (event-sourced)
            SafeQuery.execute(
                lambda: PricingSafetyEvent.objects.create(
                    event_type='OWNER_NUDGE_GENERATED',
                    hotel=room_type.hotel,
                    room_type=room_type,
                    observed_price=current_price,
                    safe_price=suggested_new_price,
                    floor_price=floor_price,
                    reason=reasoning,
                    metadata_json={
                        'suggested_discount_percent': float(suggested_discount_percent),
                        'suggested_new_price': float(suggested_new_price),
                        'duration_minutes': duration_minutes,
                        'expected_revenue_gain': float(expected_revenue_gain),
                        'confidence_score': confidence_score,
                        'risk_level': risk_level,
                    },
                    source='system'
                ),
                fallback=None,
                operation_name=f"OwnerNudgeGenerated_{room_type_id}"
            )
            
            return {
                'should_nudge': True,
                'suggested_discount_amount': float(suggested_discount_amount),
                'suggested_discount_percent': suggested_discount_percent,
                'suggested_new_price': float(suggested_new_price),
                'current_price': float(current_price),
                'floor_price': float(floor_price),
                'duration_minutes': duration_minutes,
                'expected_occupancy_gain': expected_occupancy_gain,
                'expected_revenue_gain': float(expected_revenue_gain),
                'confidence_score': confidence_score,
                'risk_level': risk_level,
                'reasoning': reasoning,
                'competitor_context': {
                    'trust_score': competitor_trust['trust_score'],
                    'trust_label': competitor_trust['trust_label'],
                },
                'demand_context': {
                    'pressure': demand_pressure,
                    'bookings_24h': bookings_24h,
                },
                'expires_at': (timezone.now() + timedelta(minutes=duration_minutes)).isoformat(),
                'generated_at': timezone.now().isoformat(),
            }
        
        except Exception as e:
            logger.error(f"OwnerPriceNudgeService.generate_nudge failed: {str(e)[:200]}")
            return OwnerPriceNudgeService._error_response("Failed to generate nudge")
    
    # ========== DECISION LOGIC ==========
    
    @staticmethod
    def _should_generate_nudge(
        current_price: Decimal,
        floor_price: Decimal,
        demand_pressure: str,
        bookings_24h: int,
        competitor_trust: float,
        margin_confidence: float
    ) -> Tuple[bool, str]:
        """
        Decide if we should generate a nudge.
        
        Returns: (should_nudge, reason)
        """
        # Rule 1: Low demand? Consider nudge
        if demand_pressure != 'LOW':
            return False, f"Demand is {demand_pressure}, no nudge needed"
        
        # Rule 2: Already have bookings? Maybe don't nudge
        if bookings_24h > 5:
            return False, "Already has recent bookings, no nudge needed"
        
        # Rule 3: Price already near floor? Don't nudge
        if current_price <= floor_price * Decimal('1.10'):  # Within 10% of floor
            return False, "Price already near floor, cannot discount further"
        
        # Rule 4: Competitor trust too low? Don't nudge
        if competitor_trust < OwnerPriceNudgeService.MIN_COMPETITOR_TRUST:
            return False, f"Competitor trust too low ({competitor_trust})"
        
        # Rule 5: Margin confidence too low? Don't nudge
        if margin_confidence < OwnerPriceNudgeService.MIN_CONFIDENCE_FOR_NUDGE:
            return False, f"Margin confidence too low ({margin_confidence})"
        
        # All checks passed
        return True, "Conditions met for smart discount nudge"
    
    @staticmethod
    def _calculate_optimal_discount(
        demand_pressure: str,
        competitor_median: Optional[float],
        current_price: Decimal,
        floor_price: Decimal
    ) -> float:
        """
        Calculate optimal discount percentage.
        
        Returns: float (3.0 to 20.0)
        """
        # Base discount depends on demand pressure
        if demand_pressure == 'LOW':
            base_discount = 12.0  # More aggressive
        elif demand_pressure == 'NORMAL':
            base_discount = 8.0
        else:  # HIGH
            base_discount = 5.0  # Conservative
        
        # Adjust based on competitor pricing
        if competitor_median:
            competitor_price = Decimal(str(competitor_median))
            if competitor_price < current_price:
                # Competitor is cheaper, increase discount
                price_gap_percent = float((current_price - competitor_price) / current_price * 100)
                base_discount += min(price_gap_percent * 0.3, 5.0)  # Add up to 5%
        
        # Cap at max
        base_discount = min(base_discount, OwnerPriceNudgeService.MAX_DISCOUNT_PERCENT)
        base_discount = max(base_discount, OwnerPriceNudgeService.MIN_DISCOUNT_PERCENT)
        
        # Ensure doesn't violate floor
        max_safe_discount = float((current_price - floor_price) / current_price * 100 * Decimal('0.9'))
        base_discount = min(base_discount, max_safe_discount)
        
        return round(base_discount, 1)
    
    @staticmethod
    def _estimate_occupancy_gain(discount_percent: float, demand_pressure: str) -> float:
        """
        Estimate occupancy gain from discount.
        
        Returns: float (0.0 to 1.0, where 0.3 = 30% increase)
        """
        # Simple heuristic: discount elasticity
        if demand_pressure == 'LOW':
            elasticity = 2.0  # More responsive to discounts
        elif demand_pressure == 'NORMAL':
            elasticity = 1.5
        else:  # HIGH
            elasticity = 1.0  # Less responsive
        
        # occupancy_gain = discount * elasticity, capped at 50%
        gain = min(discount_percent / 100.0 * elasticity, 0.5)
        return round(gain, 3)
    
    @staticmethod
    def _estimate_revenue_gain(
        current_price: Decimal,
        new_price: Decimal,
        expected_occupancy_gain: float,
        available_inventory: int
    ) -> Decimal:
        """
        Estimate net revenue gain.
        
        Revenue gain = (new bookings * new_price) - (discount on existing bookings)
        """
        # Expected new bookings
        expected_new_bookings = int(available_inventory * expected_occupancy_gain)
        
        if expected_new_bookings == 0:
            return Decimal('0.00')
        
        # Revenue from new bookings
        revenue_from_new = new_price * expected_new_bookings
        
        # Cost: discount on bookings that would have happened anyway (assume 20%)
        likely_bookings_anyway = max(1, int(expected_new_bookings * 0.2))
        discount_cost = (current_price - new_price) * likely_bookings_anyway
        
        # Net gain
        net_gain = revenue_from_new - discount_cost
        
        return max(net_gain, Decimal('0.00'))
    
    @staticmethod
    def _calculate_nudge_confidence(
        competitor_trust: float,
        margin_confidence: float,
        demand_strength: float
    ) -> float:
        """
        Calculate overall confidence in the nudge.
        
        Returns: float (0-100)
        """
        # Weighted average
        confidence = (
            competitor_trust * 0.4 +
            margin_confidence * 0.4 +
            demand_strength * 100 * 0.2
        )
        
        return round(min(confidence, 100.0), 1)
    
    @staticmethod
    def _assess_risk_level(
        discount_percent: float,
        price_vs_floor: float,
        confidence_score: float
    ) -> str:
        """
        Assess risk level of nudge.
        
        Returns: "LOW" | "MEDIUM" | "HIGH"
        """
        # HIGH risk if:
        if discount_percent > 15 or price_vs_floor < 1.15 or confidence_score < 70:
            return "HIGH"
        
        # MEDIUM risk if:
        if discount_percent > 10 or price_vs_floor < 1.25 or confidence_score < 80:
            return "MEDIUM"
        
        # Otherwise LOW
        return "LOW"
    
    @staticmethod
    def _calculate_duration(demand_pressure: str, risk_level: str) -> int:
        """
        Calculate nudge duration in minutes.
        
        Returns: int (60 to 720)
        """
        # Base duration
        if demand_pressure == 'LOW':
            duration = 240  # 4 hours
        elif demand_pressure == 'NORMAL':
            duration = 180  # 3 hours
        else:  # HIGH
            duration = 120  # 2 hours
        
        # Adjust for risk (higher risk = shorter duration)
        if risk_level == 'HIGH':
            duration = int(duration * 0.6)
        elif risk_level == 'MEDIUM':
            duration = int(duration * 0.8)
        
        # Clamp
        duration = max(duration, OwnerPriceNudgeService.MIN_DURATION_MINUTES)
        duration = min(duration, OwnerPriceNudgeService.MAX_DURATION_MINUTES)
        
        return duration
    
    @staticmethod
    def _calculate_floor_price(room_type: RoomType) -> Decimal:
        """
        Calculate safe floor price for room.
        
        Reuses existing floor logic.
        """
        cost_price = room_type.cost_price or Decimal('800')
        config = SafeConfig.get_or_create_config(PricingSafetyConfig)
        margin_percent = float(SafeConfig.safe_read(
            config, 'global_min_margin_percent', Decimal('15')
        ) or 15) / 100.0
        global_floor = Decimal(SafeConfig.safe_read(
            config, 'global_min_price', Decimal('100')
        ) or 100)
        
        floor = max(
            cost_price * Decimal(str(1 + margin_percent)),
            global_floor,
            room_type.min_safe_price or Decimal('0')
        )
        
        return floor
    
    @staticmethod
    def _generate_reasoning(
        demand_pressure: str,
        discount_percent: float,
        expected_revenue_gain: Decimal,
        competitor_context: Dict,
        confidence_score: float
    ) -> str:
        """
        Generate human-readable reasoning for owner.
        """
        reasoning = []
        
        # Demand signal
        if demand_pressure == 'LOW':
            reasoning.append("Low demand detected in last 24 hours")
        elif demand_pressure == 'NORMAL':
            reasoning.append("Normal demand, room for improvement")
        else:
            reasoning.append("High demand, conservative discount")
        
        # Competitor context
        if competitor_context['trust_label'] == 'RELIABLE':
            reasoning.append(f"Competitor pricing reliable (trust: {competitor_context['trust_score']:.0f}/100)")
        else:
            reasoning.append(f"Competitor data usable (trust: {competitor_context['trust_score']:.0f}/100)")
        
        # Expected impact
        reasoning.append(f"Expected revenue gain: ₹{expected_revenue_gain:.0f}")
        reasoning.append(f"Suggested discount: {discount_percent:.1f}% off")
        
        # Confidence
        reasoning.append(f"Confidence: {confidence_score:.0f}/100")
        
        return " • ".join(reasoning)
    
    # ========== RESPONSE BUILDERS ==========
    
    @staticmethod
    def _no_nudge_response(reason: str, current_price: Decimal) -> Dict:
        """Response when no nudge should be generated."""
        return {
            'should_nudge': False,
            'reason': reason,
            'current_price': float(current_price),
            'generated_at': timezone.now().isoformat(),
        }
    
    @staticmethod
    def _error_response(error: str) -> Dict:
        """Response when error occurs."""
        return {
            'should_nudge': False,
            'error': error,
            'generated_at': timezone.now().isoformat(),
        }
