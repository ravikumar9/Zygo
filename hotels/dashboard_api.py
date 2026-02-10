"""
PHASE 2.7.3.2 — DASHBOARD API VIEWS

REST API endpoints for revenue risk intelligence dashboard.
Provides metrics, heatmaps, and enforcement simulation data.

ARCHITECTURE: Event-sourced with service layer
  - Events (ShadowRiskEvent, PricingSafetyEvent) = source of truth
  - Services (ConfidenceCalculator, etc.) = compute on-demand
  - No derived tables persisted (except EnforcementMode audit log)
  - Future-proof for realtime, streaming, ML
"""

from rest_framework import generics, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone

from hotels.models import Hotel, PricingSafetyConfig, EnforcementMode, RoomType


class DashboardPermission(IsAdminUser):
    """Dashboard access restricted to admin users only"""
    pass


@api_view(['GET'])
@permission_classes([DashboardPermission])
def dashboard_executive_summary(request):
    """Get executive risk summary for admin dashboard
    
    Query params:
    - hotel_id: Optional hotel ID to filter by
    - days: 7 or 30 (default: both)
    
    Returns:
    {
      "period_7d": {...},
      "period_30d": {...},
      "comparison": {...},
      "summary_generated_at": "..."
    }
    
    NOTE: Computed from ShadowRiskEvent on-demand. Not persisted.
    """
    hotel_id = request.query_params.get('hotel_id')
    hotel = None
    if hotel_id:
        hotel = get_object_or_404(Hotel, id=hotel_id)
    
    summary = RiskExecutiveSummaryBuilder.build(hotel=hotel)
    return Response(summary)


@api_view(['GET'])
@permission_classes([DashboardPermission])
def dashboard_confidence_score(request):
    """Get safety confidence score and enforcement readiness
    
    Query params:
    - hotel_id: Optional hotel ID
    
    Returns:
    {
      "score": 87,
      "is_enforcement_ready": true,
      "components": {...},
      "metrics": {...},
      "recommendation": "...",
      "calculated_at": "..."
    }
    
    NOTE: Computed from ShadowRiskEvent patterns on-demand. Not persisted.
    """
    hotel_id = request.query_params.get('hotel_id')
    hotel = None
    if hotel_id:
        hotel = get_object_or_404(Hotel, id=hotel_id)
    
    score_data = ConfidenceCalculator.calculate(hotel=hotel)
    return Response(score_data)


@api_view(['GET'])
@permission_classes([DashboardPermission])
def dashboard_risk_heatmap(request):
    """Get risk heatmap data for visualization
    
    Query params:
    - dimension: 'hotel', 'city', 'room_type', or 'channel' (default: hotel)
    - days: Number of days to look back (default: 7)
    
    Returns:
    {
      "dimension": "hotel",
      "period_days": 7,
      "grid": [
        {
          "label": "Taj Palace",
          "values": {"critical": 2, "high": 5, ...},
          "revenue_at_risk": 2500.00,
          "event_count": 7
        },
        ...
      ],
      "total_events": 43,
      "total_revenue_at_risk": 12500.00
    }
    
    NOTE: Computed from ShadowRiskEvent on-demand. Not persisted.
    """
    dimension = request.query_params.get('dimension', 'hotel')
    days = int(request.query_params.get('days', 7))
    
    heatmap = RiskHeatmapAggregator.build_heatmap(
        dimension=dimension,
        period_days=days
    )
    
    return Response(heatmap)


@api_view(['GET'])
@permission_classes([DashboardPermission])
def dashboard_enforcement_simulation(request):
    """Get enforcement simulation results (what-if analysis)
    
    Query params:
    - hotel_id: Optional hotel ID
    
    Returns:
    {
      "current_state": {...},
      "enforcement_enabled": {...},
      "strict_enforcement": {...},
      "recommendation": "...",
      "simulated_at": "..."
    }
    
    NOTE: Computed via scenario modeling on-demand. Not persisted.
    """
    hotel_id = request.query_params.get('hotel_id')
    
    hotel = None
    if hotel_id:
        hotel = get_object_or_404(Hotel, id=hotel_id)
    
    simulation = EnforcementSimulationEngine.simulate(hotel=hotel)
    return Response(simulation)


@api_view(['POST'])
@permission_classes([DashboardPermission])
def dashboard_enforcement_switch(request):
    """Switch pricing safety mode between SHADOW and ENFORCEMENT
    
    Body (JSON):
    {
      "action": "enable",  // or "disable"
      "confirm": true,     // MUST be explicitly true
      "reason": "7-day observation period complete"
    }
    
    Returns:
    {
      "success": true,
      "previous_mode": "SHADOW",
      "new_mode": "ENFORCEMENT",
      "timestamp": "..."
    }
    
    Hard rules:
    - Requires admin permission (is_staff=True)
    - Cannot enable ENFORCEMENT if confidence < 85 (gate enforced)
    - Must explicitly confirm=true
    - Creates audit trail in EnforcementMode table
    - Mode changes recorded with admin user and reason
    """
    data = request.data
    action = data.get('action')
    confirm = data.get('confirm', False)
    reason = data.get('reason', '')
    
    # HARD RULE: Explicit confirmation required
    if not confirm:
        return Response(
            {
                'error': 'Mode switch requires explicit confirmation',
                'details': 'Must include "confirm": true in request body'
            },
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Validate action
    if action not in ['enable', 'disable']:
        return Response(
            {'error': 'Invalid action. Must be "enable" or "disable".'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # HARD RULE: Cannot enable without sufficient confidence
    if action == 'enable':
        confidence = ConfidenceCalculator.calculate()
        if not confidence['is_enforcement_ready']:
            return Response(
                {
                    'error': 'Cannot enable enforcement',
                    'reason': f"Safety confidence {confidence['score']}/100 below minimum {ConfidenceCalculator.MIN_SCORE_FOR_ENFORCEMENT}",
                    'current_score': confidence['score'],
                    'min_required': ConfidenceCalculator.MIN_SCORE_FOR_ENFORCEMENT,
                    'recommendation': confidence['recommendation'],
                },
                status=status.HTTP_403_FORBIDDEN
            )
        new_mode = 'ENFORCEMENT'
    else:
        new_mode = 'SHADOW'
    
    # Get current mode
    current_mode_record = EnforcementMode.get_current_mode()
    previous_mode = current_mode_record.mode if current_mode_record else 'SHADOW'
    
    # ATOMIC: Create new mode record and update config
    with transaction.atomic():
        EnforcementMode.objects.create(
            mode=new_mode,
            is_active=True,
            changed_by=request.user,
            reason=reason
        )
        
        config = PricingSafetyConfig.get_config()
        config.pricing_safety_mode = new_mode
        config.save()
    
    return Response({
        'success': True,
        'previous_mode': previous_mode,
        'new_mode': new_mode,
        'timestamp': timezone.now().isoformat(),
        'reason': reason,
    })


@api_view(['GET'])
@permission_classes([DashboardPermission])
def dashboard_current_mode(request):
    """Get current pricing safety mode and enforcement status
    
    Returns:
    {
      "current_mode": "SHADOW",
      "confidence_score": 87,
      "is_enforcement_ready": true,
      "min_confidence_required": 85,
      "details": {...}
    }
    
    NOTE: Mode from EnforcementMode audit log (persisted).
          Confidence computed from events on-demand.
    """
    current_mode_record = EnforcementMode.get_current_mode()
    current_mode = current_mode_record.mode if current_mode_record else 'SHADOW'
    
    confidence = ConfidenceCalculator.calculate()
    
    return Response({
        'current_mode': current_mode,
        'confidence_score': confidence['score'],
        'is_enforcement_ready': confidence['is_enforcement_ready'],
        'min_confidence_required': ConfidenceCalculator.MIN_SCORE_FOR_ENFORCEMENT,
        'confidence_details': confidence,
        'retrieved_at': timezone.now().isoformat(),
    })


@api_view(['GET'])
@permission_classes([DashboardPermission])
def dashboard_full_status(request):
    """Get comprehensive dashboard status in single request
    
    Returns:
    {
      "current_mode": "SHADOW",
      "executive_summary": {...},
      "confidence_score": {...},
      "enforcement_simulation": {...},
      "risk_heatmap": {...},
      "retrieved_at": "..."
    }
    
    NOTE: Computed from events on-demand. Not persisted.
    """
    hotel_id = request.query_params.get('hotel_id')
    hotel = None
    if hotel_id:
        hotel = get_object_or_404(Hotel, id=hotel_id)
    
    current_mode_record = EnforcementMode.get_current_mode()
    current_mode = current_mode_record.mode if current_mode_record else 'SHADOW'
    
    summary = RiskExecutiveSummaryBuilder.build(hotel=hotel)
    confidence = ConfidenceCalculator.calculate(hotel=hotel)
    simulation = EnforcementSimulationEngine.simulate(hotel=hotel)
    heatmap = RiskHeatmapAggregator.build_heatmap(dimension='hotel', period_days=7)
    
    return Response({
        'current_mode': current_mode,
        'executive_summary': summary,
        'confidence_score': confidence,
        'enforcement_simulation': simulation,
        'risk_heatmap': heatmap,
        'retrieved_at': timezone.now().isoformat(),
    })


# ============================================================================
# REVENUE INTELLIGENCE APIs (P0 SPRINT)
# ============================================================================

@api_view(['GET'])
@permission_classes([DashboardPermission])
def margin_suggestion(request, room_type_id):
    """
    Get pricing suggestion for a room type.
    
    Fast heuristic-based pricing suggestion (NOT ML).
    
    Returns:
    {
      "optimal_price": Decimal,
      "safe_floor_price": Decimal,
      "risk_ceiling_price": Decimal,
      "confidence_score": float (0-100),
      "demand_pressure": "HIGH" | "NORMAL" | "LOW",
      "explanation": str,
      "components": {...}
    }
    
    Performance: < 200ms
    """
    suggestion = MarginSuggestionService.get_suggestion(room_type_id)
    return Response(suggestion)


@api_view(['GET'])
@permission_classes([DashboardPermission])
def competitor_trust(request, channel):
    """
    Get competitor feed trust score.
    
    Evaluates feed reliability over last 7 days.
    
    Args:
        channel: Competitor channel name (e.g., 'goibibo', 'makemytrip')
    
    Returns:
    {
      "channel": str,
      "trust_score": float (0-100),
      "trust_label": "RELIABLE" | "USABLE" | "UNSTABLE",
      "issues": [str],
      "metrics": {...},
      "recommendation": str
    }
    
    Performance: < 300ms
    """
    trust_data = CompetitorFeedTrustService.calculate_trust(channel)
    return Response(trust_data)


@api_view(['GET'])
@permission_classes([DashboardPermission])
def risk_alerts(request):
    """
    Get all active risk alerts.
    
    Detects:
    - Low confidence score
    - Competitor feed issues
    - Shadow risk spikes
    - Circuit breaker triggers
    
    Returns:
    [
      {
        "type": str,
        "severity": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
        "message": str,
        "recommended_action": str,
        "detected_at": str,
        "details": {...}
      },
      ...
    ]
    
    Performance: < 200ms
    """
    alerts = RiskAlertService.get_active_alerts()
    return Response({
        'alerts': alerts,
        'alert_count': len(alerts),
        'retrieved_at': timezone.now().isoformat(),
    })


# =============================================
# PHASE 2.7.3.4 — OWNER PRICE NUDGE APIS
# =============================================

@api_view(['GET'])
@permission_classes([DashboardPermission])
def owner_price_nudge(request, room_type_id):
    """
    Generate smart discount nudge for hotel owner.
    
    Analyzes:
    - Competitor pricing (trusted feeds only)
    - Demand pressure
    - Inventory allocation
    - Historical patterns
    
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
      "risk_level": "LOW" | "MEDIUM" | "HIGH",
      "reasoning": str,
      "competitor_context": {...},
      "demand_context": {...},
      "expires_at": datetime,
    }
    
    Performance: < 300ms
    Admin/Owner only — NO public access
    """
    nudge_data = OwnerPriceNudgeService.generate_nudge(room_type_id)
    return Response(nudge_data)


@api_view(['POST'])
@permission_classes([DashboardPermission])
def owner_price_nudge_accept(request, room_type_id):
    """
    Owner accepts a price nudge.
    
    Body:
    {
      "nudge_id": str (from previous generation),
      "duration_minutes": int (optional, override)
    }
    
    Returns:
    {
      "success": bool,
      "message": str,
      "applied_price": Decimal,
      "expires_at": datetime
    }
    
    TODO: Implement price application + event tracking
    """
    # PLACEHOLDER for fast sprint
    return Response({
        'success': False,
        'message': 'Accept/Reject implementation pending',
        'note': 'Will track acceptance via PricingSafetyEvent with type OWNER_NUDGE_ACCEPTED'
    }, status=status.HTTP_501_NOT_IMPLEMENTED)


@api_view(['POST'])
@permission_classes([DashboardPermission])
def owner_price_nudge_reject(request, room_type_id):
    """
    Owner rejects a price nudge.
    
    Body:
    {
      "nudge_id": str,
      "rejection_reason": str (optional)
    }
    
    Returns:
    {
      "success": bool,
      "message": str
    }
    
    TODO: Implement rejection tracking
    """
    # PLACEHOLDER for fast sprint
    return Response({
        'success': False,
        'message': 'Accept/Reject implementation pending',
        'note': 'Will track rejection via PricingSafetyEvent with type OWNER_NUDGE_REJECTED'
    }, status=status.HTTP_501_NOT_IMPLEMENTED)


# =============================================
# PHASE 2.7.3.5 — OWNER NEGOTIATION APIS
# =============================================

@api_view(['GET'])
@permission_classes([DashboardPermission])
def owner_negotiation_opportunity(request, hotel_id):
    """
    Generate negotiation opportunity for premium listings.
    No discounts suggested, opportunity framing only.
    """
    opportunity = OwnerNegotiationService.generate_opportunity(hotel_id)
    return Response(opportunity)


@api_view(['POST'])
@permission_classes([DashboardPermission])
def owner_negotiation_propose(request):
    """
    Owner-initiated negotiation proposal.
    Logs proposal via PricingSafetyEvent.
    """
    result, status_code = OwnerNegotiationService.propose_negotiation(request.data, user=request.user)
    return Response(result, status=status_code)


@api_view(['POST'])
@permission_classes([DashboardPermission])
def owner_negotiation_respond(request):
    """
    Platform-initiated negotiation response (accept/counter/reject).
    Logs response via PricingSafetyEvent.
    """
    result, status_code = OwnerNegotiationService.respond_to_negotiation(request.data, user=request.user)
    return Response(result, status=status_code)


@api_view(['GET'])
@permission_classes([DashboardPermission])
def admin_negotiation_active(request):
    """
    Admin view: recent negotiation activity + optional incentive evaluation.

    Query params:
    - days: lookback window (default: 30)
    - hotel_id: optional, if provided includes incentive evaluation
    """
    days = int(request.query_params.get('days', 30))
    hotel_id = request.query_params.get('hotel_id')

    data = OwnerNegotiationService.get_active_negotiations(days=days)
    if hotel_id:
        try:
            data['incentive'] = OwnerNegotiationService.evaluate_incentive(int(hotel_id))
        except Exception:
            data['incentive'] = {'eligible': False, 'message': 'Incentive evaluation failed'}

    return Response(data)


# =============================================
# PHASE 2.7.3.6 — OWNER MOBILE CONTROL SURFACE
# =============================================

@api_view(['GET'])
@permission_classes([DashboardPermission])
def owner_mobile_negotiation_opportunities(request, hotel_id):
    data = OwnerMobileControlService.get_active_negotiation_opportunities(hotel_id)
    return Response(data)


@api_view(['GET'])
@permission_classes([DashboardPermission])
def owner_mobile_pending_nudges(request, hotel_id):
    data = OwnerMobileControlService.get_pending_price_nudges(hotel_id)
    return Response(data)


@api_view(['GET'])
@permission_classes([DashboardPermission])
def owner_mobile_history(request, hotel_id):
    data = OwnerMobileControlService.get_history(hotel_id)
    return Response(data)


@api_view(['GET'])
@permission_classes([DashboardPermission])
def owner_mobile_incentives(request, hotel_id):
    data = OwnerMobileControlService.get_incentives(hotel_id)
    return Response(data)
