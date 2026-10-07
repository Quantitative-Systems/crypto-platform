"""Instrument Intelligence Layer.

Enforces:
1. First leg (base asset) MUST be CRYPTO.
2. Second leg (quote asset) can be any supported asset (FIAT, STABLECOIN, COMMODITY, CRYPTO).
3. Non-crypto base instruments are strictly rejected as INELIGIBLE.
4. Admission Gate: 11-step audit before trading admission.
"""
from instrument.asset_class import AssetClass, classify_asset
from instrument.instrument_contract import CryptoBaseInstrument, build_instrument
from instrument.instrument_health import HealthStatus, InstrumentHealth
from instrument.instrument_registry import (
    AdmissionChecklist,
    AdmissionDecision,
    AdmissionReport,
    InstrumentAdmissionGate,
    InstrumentRegistry,
)
from instrument.liquidity_profile import LiquidityProfile, TradingSessionType
from instrument.quote_currency import QuoteCurrencyInfo, QuoteSettlementType, get_quote_info
from instrument.symbol_normalizer import SymbolNormalizer
from instrument.trading_constraints import InstrumentMarketType, TradingConstraints
from instrument.venue_symbol_mapper import VenueSymbolMapper

__all__ = [
    "AssetClass",
    "classify_asset",
    "CryptoBaseInstrument",
    "build_instrument",
    "QuoteCurrencyInfo",
    "QuoteSettlementType",
    "get_quote_info",
    "TradingConstraints",
    "InstrumentMarketType",
    "LiquidityProfile",
    "TradingSessionType",
    "HealthStatus",
    "InstrumentHealth",
    "SymbolNormalizer",
    "VenueSymbolMapper",
    "AdmissionDecision",
    "AdmissionChecklist",
    "AdmissionReport",
    "InstrumentAdmissionGate",
    "InstrumentRegistry",
    "AutonomousMarketDiscoveryEngine",
    "DiscoveredInstrumentCandidate",
    "OpportunityScoreCard",
    "QualificationStatus",
    "InstrumentLifecycleStage",
    "ContinuousObservationCoordinator",
]
from instrument.discovery_engine import (
    AutonomousMarketDiscoveryEngine,
    ContinuousObservationCoordinator,
    DiscoveredInstrumentCandidate,
    InstrumentLifecycleStage,
    OpportunityScoreCard,
    QualificationStatus,
)
