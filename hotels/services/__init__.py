"""
HOTELS SERVICE LAYER

Production-grade services for domain business logic.

Services:
  - risk_dashboard_service: Event-sourced dashboard metrics calculation
  - margin_suggestion_service: Fast heuristic pricing suggestions
  - competitor_trust_service: Competitor feed reliability scoring
  - risk_alert_service: Critical condition detection
  - owner_price_nudge_service: Smart discount suggestions for owners
  - owner_negotiation_service: Negotiation-only pricing intelligence
  - owner_mobile_control_service: Owner mobile control surface (read-only)
  
Utilities:
  - schema_resolver: Safe query adapters for schema variations
  - safe_query: Fail-safe query execution with fallbacks
"""

from .risk_dashboard_service import (
    ConfidenceCalculator,
    RiskExecutiveSummaryBuilder,
    EnforcementSimulationEngine,
    RiskHeatmapAggregator,
)
from .margin_suggestion_service import MarginSuggestionService
from .competitor_trust_service import CompetitorFeedTrustService
from .risk_alert_service import RiskAlertService
from .owner_price_nudge_service import OwnerPriceNudgeService
from .owner_negotiation_service import OwnerNegotiationService
from .owner_mobile_control_service import OwnerMobileControlService
from .schema_resolver import BookingSchemaResolver
from .safe_query import SafeQuery, SafeConfig

__all__ = [
    'ConfidenceCalculator',
    'RiskExecutiveSummaryBuilder',
    'EnforcementSimulationEngine',
    'RiskHeatmapAggregator',
    'MarginSuggestionService',
    'CompetitorFeedTrustService',
    'RiskAlertService',
    'OwnerPriceNudgeService',
    'OwnerNegotiationService',
    'OwnerMobileControlService',
    'BookingSchemaResolver',
    'SafeQuery',
    'SafeConfig',
]
