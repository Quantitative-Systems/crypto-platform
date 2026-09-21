"""
QCP — Certified 10-Asset Universe Registry.
Directive: EABG-001

Implements an objective, rule-governed asset universe registry capable of:
1. Asset identity and metadata tracking
2. Market-cap and liquidity ranking
3. Trading volume and order-book depth hurdles
4. Historical data depth and timestamp continuity
5. Multi-venue and derivatives availability
6. Survivorship bias controls and listing/delisting audit
7. Asset-specific trading constraints (lot size, tick size, min notional)
8. Research vs. Production eligibility separation:
   - Research Universe: Assets certified for empirical research and hypothesis testing.
   - Trading Universe: Assets approved for forward paper and production qualification.
   - INVARIANT: Asset Universe ≠ Trading Universe. New assets are research candidates first.
"""

from __future__ import annotations

import enum
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from platform_core.foundation.audit_logger import AuditLogger
from platform_core.foundation.clock import SystemClock
from platform_core.foundation.error_taxonomy import PlatformError, ErrorCategory, ErrorSeverity

logger = logging.getLogger("QCP.AssetUniverseRegistry")


class AssetCategory(str, enum.Enum):
    STORE_OF_VALUE = "STORE_OF_VALUE"
    SMART_CONTRACT_L1 = "SMART_CONTRACT_L1"
    HIGH_BETA_L1 = "HIGH_BETA_L1"
    EXCHANGE_ECOSYSTEM = "EXCHANGE_ECOSYSTEM"
    PAYMENTS = "PAYMENTS"
    MEME_SPECULATION = "MEME_SPECULATION"
    ORACLE_INFRASTRUCTURE = "ORACLE_INFRASTRUCTURE"
    POW_PAYMENT = "POW_PAYMENT"


class SurvivorshipStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    HALTED = "HALTED"
    DELISTED = "DELISTED"
    MIGRATED = "MIGRATED"


class AssetGovernanceStatus(str, enum.Enum):
    CERTIFIED_BENCHMARK = "CERTIFIED_BENCHMARK"  # Verified baseline (BTC, ETH, SOL)
    RESEARCH_CANDIDATE = "RESEARCH_CANDIDATE"    # Approved for research backtesting
    PRODUCTION_BLOCKED = "PRODUCTION_BLOCKED"    # Blocked from execution/paper trading
    REJECTED = "REJECTED"                        # Fails liquidity/data quality hurdles
    RETIRED = "RETIRED"                          # Deprecated or delisted


@dataclass
class AssetMetadata:
    """Canonical asset metadata record conforming to Directive EABG-001."""
    symbol: str  # e.g. "BTC/USDT"
    base_asset: str  # e.g. "BTC"
    quote_asset: str  # e.g. "USDT"
    category: AssetCategory
    economic_role: str
    market_cap_rank: int
    median_daily_volume_usd: float
    historical_depth_days: int
    primary_venues: List[str]
    spot_available: bool
    perp_available: bool
    options_available: bool
    min_order_qty: float
    min_notional_usd: float
    tick_size: float
    step_size: float
    typical_spread_bps: float
    listing_date_utc: str
    delisting_date_utc: Optional[str] = None
    survivorship_status: SurvivorshipStatus = SurvivorshipStatus.ACTIVE
    data_quality_certified: bool = False
    research_eligibility: bool = False
    production_eligibility: bool = False
    governance_status: AssetGovernanceStatus = AssetGovernanceStatus.RESEARCH_CANDIDATE
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        d["survivorship_status"] = self.survivorship_status.value
        d["governance_status"] = self.governance_status.value
        return d


@dataclass
class UniverseEligibilityHurdles:
    """Objective, rule-governed hurdles for asset universe selection."""
    max_market_cap_rank: int = 20
    min_daily_volume_usd: float = 50_000_000.0  # $50M daily volume
    min_history_days: int = 730                   # 2 years continuous history
    min_primary_venues: int = 2                  # At least 2 Tier-1 venues
    require_perp_futures: bool = True
    max_typical_spread_bps: float = 12.0


class AssetUniverseRegistry:
    """
    Authoritative Asset Universe Registry for QCP.
    Maintains the certified research universe and enforces the separation
    between Research Candidates and Production-Eligible Trading Assets.
    """

    def __init__(
        self,
        hurdles: Optional[UniverseEligibilityHurdles] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        self._hurdles = hurdles or UniverseEligibilityHurdles()
        self._audit_logger = audit_logger or AuditLogger()
        self._assets: Dict[str, AssetMetadata] = {}
        self._initialize_canonical_10_universe()

    def _initialize_canonical_10_universe(self) -> None:
        """
        Initializes the canonical 10-asset universe per Directive EABG-001.
        Existing M2 baseline assets (BTC, ETH, SOL) retain CERTIFIED_BENCHMARK status.
        New expansion assets are initialized strictly as RESEARCH_CANDIDATE.
        """
        canonical_assets = [
            AssetMetadata(
                symbol="BTC/USDT",
                base_asset="BTC",
                quote_asset="USDT",
                category=AssetCategory.STORE_OF_VALUE,
                economic_role="Benchmark / Store-of-Value / Deepest global liquidity",
                market_cap_rank=1,
                median_daily_volume_usd=25_000_000_000.0,
                historical_depth_days=3300,
                primary_venues=["Binance", "OKX", "Bybit", "Coinbase"],
                spot_available=True,
                perp_available=True,
                options_available=True,
                min_order_qty=0.001,
                min_notional_usd=5.0,
                tick_size=0.10,
                step_size=0.001,
                typical_spread_bps=1.0,
                listing_date_utc="2017-08-17T00:00:00Z",
                data_quality_certified=True,
                research_eligibility=True,
                production_eligibility=False,  # Live capital fail-closed
                governance_status=AssetGovernanceStatus.CERTIFIED_BENCHMARK,
                notes="Primary macro benchmark; foundation of all beta decomposition.",
            ),
            AssetMetadata(
                symbol="ETH/USDT",
                base_asset="ETH",
                quote_asset="USDT",
                category=AssetCategory.SMART_CONTRACT_L1,
                economic_role="Smart-contract platform leader / Large-cap ecosystem asset",
                market_cap_rank=2,
                median_daily_volume_usd=12_000_000_000.0,
                historical_depth_days=3300,
                primary_venues=["Binance", "OKX", "Bybit", "Coinbase"],
                spot_available=True,
                perp_available=True,
                options_available=True,
                min_order_qty=0.01,
                min_notional_usd=5.0,
                tick_size=0.01,
                step_size=0.01,
                typical_spread_bps=1.5,
                listing_date_utc="2017-08-17T00:00:00Z",
                data_quality_certified=True,
                research_eligibility=True,
                production_eligibility=False,
                governance_status=AssetGovernanceStatus.CERTIFIED_BENCHMARK,
                notes="Secondary macro benchmark; primary decentralized finance reference.",
            ),
            AssetMetadata(
                symbol="SOL/USDT",
                base_asset="SOL",
                quote_asset="USDT",
                category=AssetCategory.HIGH_BETA_L1,
                economic_role="High-throughput alternative L1 / High-beta momentum vehicle",
                market_cap_rank=5,
                median_daily_volume_usd=3_500_000_000.0,
                historical_depth_days=1800,
                primary_venues=["Binance", "OKX", "Bybit", "Coinbase"],
                spot_available=True,
                perp_available=True,
                options_available=True,
                min_order_qty=0.1,
                min_notional_usd=5.0,
                tick_size=0.01,
                step_size=0.1,
                typical_spread_bps=2.5,
                listing_date_utc="2020-08-11T00:00:00Z",
                data_quality_certified=True,
                research_eligibility=True,
                production_eligibility=False,
                governance_status=AssetGovernanceStatus.CERTIFIED_BENCHMARK,
                notes="Primary asset for forward paper burn-in daemon (Set 2).",
            ),
            AssetMetadata(
                symbol="BNB/USDT",
                base_asset="BNB",
                quote_asset="USDT",
                category=AssetCategory.EXCHANGE_ECOSYSTEM,
                economic_role="Exchange token & L1 utility asset / Distinct fee-burn economics",
                market_cap_rank=4,
                median_daily_volume_usd=1_000_000_000.0,
                historical_depth_days=2500,
                primary_venues=["Binance", "Bybit", "OKX"],
                spot_available=True,
                perp_available=True,
                options_available=False,
                min_order_qty=0.01,
                min_notional_usd=5.0,
                tick_size=0.10,
                step_size=0.01,
                typical_spread_bps=3.0,
                listing_date_utc="2017-11-06T00:00:00Z",
                data_quality_certified=False,
                research_eligibility=True,
                production_eligibility=False,
                governance_status=AssetGovernanceStatus.RESEARCH_CANDIDATE,
                notes="Research candidate: Test if exchange-token utility provides orthogonal factor edge.",
            ),
            AssetMetadata(
                symbol="XRP/USDT",
                base_asset="XRP",
                quote_asset="USDT",
                category=AssetCategory.PAYMENTS,
                economic_role="Payments-oriented legacy large-cap / Regulatory shock behavior",
                market_cap_rank=7,
                median_daily_volume_usd=1_500_000_000.0,
                historical_depth_days=2600,
                primary_venues=["Binance", "OKX", "Bybit", "Coinbase"],
                spot_available=True,
                perp_available=True,
                options_available=False,
                min_order_qty=1.0,
                min_notional_usd=5.0,
                tick_size=0.0001,
                step_size=1.0,
                typical_spread_bps=2.0,
                listing_date_utc="2018-05-04T00:00:00Z",
                data_quality_certified=False,
                research_eligibility=True,
                production_eligibility=False,
                governance_status=AssetGovernanceStatus.RESEARCH_CANDIDATE,
                notes="Research candidate: Explores cross-border payments order flow dynamics.",
            ),
            AssetMetadata(
                symbol="ADA/USDT",
                base_asset="ADA",
                quote_asset="USDT",
                category=AssetCategory.SMART_CONTRACT_L1,
                economic_role="Alternative PoS L1 / High retail dispersion / Sluggish momentum",
                market_cap_rank=10,
                median_daily_volume_usd=400_000_000.0,
                historical_depth_days=2400,
                primary_venues=["Binance", "OKX", "Bybit", "Coinbase"],
                spot_available=True,
                perp_available=True,
                options_available=False,
                min_order_qty=1.0,
                min_notional_usd=5.0,
                tick_size=0.0001,
                step_size=1.0,
                typical_spread_bps=3.5,
                listing_date_utc="2018-04-17T00:00:00Z",
                data_quality_certified=False,
                research_eligibility=True,
                production_eligibility=False,
                governance_status=AssetGovernanceStatus.RESEARCH_CANDIDATE,
                notes="Research candidate: Tests whether low-velocity assets produce falsifiable trend signals.",
            ),
            AssetMetadata(
                symbol="DOGE/USDT",
                base_asset="DOGE",
                quote_asset="USDT",
                category=AssetCategory.MEME_SPECULATION,
                economic_role="Pure speculative attention proxy / High retail sentiment reflexivity",
                market_cap_rank=8,
                median_daily_volume_usd=1_200_000_000.0,
                historical_depth_days=2200,
                primary_venues=["Binance", "OKX", "Bybit", "Coinbase"],
                spot_available=True,
                perp_available=True,
                options_available=False,
                min_order_qty=10.0,
                min_notional_usd=5.0,
                tick_size=0.00001,
                step_size=10.0,
                typical_spread_bps=3.0,
                listing_date_utc="2019-07-05T00:00:00Z",
                data_quality_certified=False,
                research_eligibility=True,
                production_eligibility=False,
                governance_status=AssetGovernanceStatus.RESEARCH_CANDIDATE,
                notes="Research candidate: Tests extreme tail events and social sentiment volume shocks.",
            ),
            AssetMetadata(
                symbol="AVAX/USDT",
                base_asset="AVAX",
                quote_asset="USDT",
                category=AssetCategory.HIGH_BETA_L1,
                economic_role="Subnet-based L1 / High correlation to SOL and ETH risk appetite",
                market_cap_rank=11,
                median_daily_volume_usd=500_000_000.0,
                historical_depth_days=1500,
                primary_venues=["Binance", "OKX", "Bybit", "Coinbase"],
                spot_available=True,
                perp_available=True,
                options_available=False,
                min_order_qty=0.1,
                min_notional_usd=5.0,
                tick_size=0.01,
                step_size=0.1,
                typical_spread_bps=4.0,
                listing_date_utc="2020-09-22T00:00:00Z",
                data_quality_certified=False,
                research_eligibility=True,
                production_eligibility=False,
                governance_status=AssetGovernanceStatus.RESEARCH_CANDIDATE,
                notes="Research candidate: Evaluates cross-L1 relative momentum and beta hedging.",
            ),
            AssetMetadata(
                symbol="LINK/USDT",
                base_asset="LINK",
                quote_asset="USDT",
                category=AssetCategory.ORACLE_INFRASTRUCTURE,
                economic_role="Decentralized oracle infrastructure / Institutional adoption proxy",
                market_cap_rank=14,
                median_daily_volume_usd=350_000_000.0,
                historical_depth_days=2200,
                primary_venues=["Binance", "OKX", "Bybit", "Coinbase"],
                spot_available=True,
                perp_available=True,
                options_available=False,
                min_order_qty=0.1,
                min_notional_usd=5.0,
                tick_size=0.001,
                step_size=0.1,
                typical_spread_bps=3.5,
                listing_date_utc="2019-01-16T00:00:00Z",
                data_quality_certified=False,
                research_eligibility=True,
                production_eligibility=False,
                governance_status=AssetGovernanceStatus.RESEARCH_CANDIDATE,
                notes="Research candidate: Tests infrastructure token lead-lag relationships with DeFi.",
            ),
            AssetMetadata(
                symbol="LTC/USDT",
                base_asset="LTC",
                quote_asset="USDT",
                category=AssetCategory.POW_PAYMENT,
                economic_role="Legacy PoW silver-to-gold proxy / Halving cycle market dynamics",
                market_cap_rank=19,
                median_daily_volume_usd=300_000_000.0,
                historical_depth_days=3100,
                primary_venues=["Binance", "OKX", "Bybit", "Coinbase"],
                spot_available=True,
                perp_available=True,
                options_available=False,
                min_order_qty=0.01,
                min_notional_usd=5.0,
                tick_size=0.01,
                step_size=0.01,
                typical_spread_bps=3.0,
                listing_date_utc="2017-12-13T00:00:00Z",
                data_quality_certified=False,
                research_eligibility=True,
                production_eligibility=False,
                governance_status=AssetGovernanceStatus.RESEARCH_CANDIDATE,
                notes="Research candidate: Deep historical data; evaluates cyclical halving lead/lag.",
            ),
        ]

        for asset in canonical_assets:
            self._assets[asset.symbol] = asset

    def evaluate_eligibility(self, asset: AssetMetadata) -> Tuple[bool, List[str]]:
        """
        Evaluates an asset against objective quantitative hurdles.
        Returns whether it qualifies as a Research Candidate and any violation reasons.
        """
        reasons: List[str] = []

        if asset.market_cap_rank > self._hurdles.max_market_cap_rank:
            reasons.append(f"Market cap rank {asset.market_cap_rank} > max {self._hurdles.max_market_cap_rank}")

        if asset.median_daily_volume_usd < self._hurdles.min_daily_volume_usd:
            reasons.append(
                f"Daily volume ${asset.median_daily_volume_usd:,.0f} < min ${self._hurdles.min_daily_volume_usd:,.0f}"
            )

        if asset.historical_depth_days < self._hurdles.min_history_days:
            reasons.append(
                f"History {asset.historical_depth_days} days < min {self._hurdles.min_history_days} days"
            )

        if len(asset.primary_venues) < self._hurdles.min_primary_venues:
            reasons.append(
                f"Venue count {len(asset.primary_venues)} < min {self._hurdles.min_primary_venues}"
            )

        if self._hurdles.require_perp_futures and not asset.perp_available:
            reasons.append("Perpetual futures derivatives not available")

        if asset.typical_spread_bps > self._hurdles.max_typical_spread_bps:
            reasons.append(
                f"Typical spread {asset.typical_spread_bps} bps > max {self._hurdles.max_typical_spread_bps} bps"
            )

        if asset.survivorship_status != SurvivorshipStatus.ACTIVE:
            reasons.append(f"Asset is not active: {asset.survivorship_status.value}")

        is_eligible = len(reasons) == 0
        return is_eligible, reasons

    def get_asset(self, symbol: str) -> Optional[AssetMetadata]:
        return self._assets.get(symbol)

    def list_all_assets(self) -> List[AssetMetadata]:
        return list(self._assets.values())

    def list_research_universe(self) -> List[AssetMetadata]:
        """Returns all assets eligible for quantitative research."""
        return [a for a in self._assets.values() if a.research_eligibility]

    def list_trading_universe(self) -> List[AssetMetadata]:
        """
        Returns all assets approved for live/forward trading.
        INVARIANT: Asset Universe ≠ Trading Universe.
        Only assets with empirical evidence and zero live capital allocation qualify.
        """
        return [a for a in self._assets.values() if a.production_eligibility]

    def export_registry_json(self) -> Dict[str, Any]:
        """Generates canonical registry JSON conforming to Directive EABG-001."""
        return {
            "registry_version": "1.0.0",
            "directive": "EABG-001",
            "last_audit_utc": SystemClock.utc_now().isoformat(),
            "total_assets_registered": len(self._assets),
            "research_universe_count": len(self.list_research_universe()),
            "trading_universe_count": len(self.list_trading_universe()),
            "capital_allocation_rule": "$0.00_FAIL_CLOSED",
            "hurdles": asdict(self._hurdles),
            "assets": {sym: a.to_dict() for sym, a in self._assets.items()},
        }
