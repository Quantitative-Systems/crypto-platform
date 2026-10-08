"""STRATA — Market Data & Asset State Service.

Provides consolidated market monitoring, watchlist management, and 7-timeframe
causal market model diagnostics across admitted crypto assets:
- BTCUSDT (Benchmark / Priority 1)
- ETHUSDT (Priority 2)
- SOLUSDT (Priority 3)
- BNBUSDT (Priority 4)
"""
from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set

from market_data.universe.crypto_universe import CryptoUniverseManager

logger = logging.getLogger(__name__)


@dataclass
class TimeframeStateDetail:
    timeframe: str
    structure: str  # BULLISH / BEARISH / RANGING
    phase: str  # ACCUMULATION / MARKUP / DISTRIBUTION / MARKDOWN
    key_level_support: float
    key_level_resistance: float
    premium_discount: str  # DISCOUNT / PREMIUM / EQUILIBRIUM
    closed_candles_count: int
    provenance: str = "HISTORICAL_AND_PAPER"


@dataclass
class AssetMarketCard:
    symbol: str
    base_asset: str
    quote_asset: str
    current_price: float
    change_24h_pct: float
    high_24h: float
    low_24h: float
    volume_24h_usd: float
    volatility_atr_pct: float
    liquidity_health: str  # TIER_1_HIGH / TIER_2_MODERATE
    strategy_eligibility: bool  # True for all admitted assets
    execution_eligibility: str  # PAPER_AND_DEMO_ELIGIBLE (Live FAIL_CLOSED)
    is_priority: bool
    market_structure_summary: str
    phase_summary: str
    timeframes: Dict[str, TimeframeStateDetail] = field(default_factory=dict)
    last_updated_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "base_asset": self.base_asset,
            "quote_asset": self.quote_asset,
            "current_price": self.current_price,
            "change_24h_pct": self.change_24h_pct,
            "high_24h": self.high_24h,
            "low_24h": self.low_24h,
            "volume_24h_usd": self.volume_24h_usd,
            "volatility_atr_pct": self.volatility_atr_pct,
            "liquidity_health": self.liquidity_health,
            "strategy_eligibility": self.strategy_eligibility,
            "execution_eligibility": self.execution_eligibility,
            "is_priority": self.is_priority,
            "market_structure_summary": self.market_structure_summary,
            "phase_summary": self.phase_summary,
            "timeframes": {k: asdict(v) for k, v in self.timeframes.items()},
            "last_updated_utc": self.last_updated_utc,
        }


class MarketService:
    """Consolidated market observation, watchlist, and asset diagnostics service."""

    def __init__(self):
        self._watchlists_by_tenant: Dict[str, Set[str]] = {}
        # Default market profiles based on live/recent market model states
        self._asset_profiles = self._initialize_market_cards()

    def _initialize_market_cards(self) -> Dict[str, AssetMarketCard]:
        cards = {}

        # 1. BTCUSDT
        btc_tf = {
            "1M": TimeframeStateDetail("1M", "BULLISH", "MARKUP", 52000.0, 74000.0, "PREMIUM", 84),
            "1W": TimeframeStateDetail("1W", "BULLISH", "MARKUP", 59500.0, 69500.0, "EQUILIBRIUM", 364),
            "1D": TimeframeStateDetail("1D", "BULLISH", "MARKUP", 61800.0, 66500.0, "DISCOUNT", 2550),
            "4H": TimeframeStateDetail("4H", "BULLISH", "ACCUMULATION", 62400.0, 65200.0, "DISCOUNT", 15300),
            "1H": TimeframeStateDetail("1H", "RANGING", "ACCUMULATION", 63100.0, 64400.0, "EQUILIBRIUM", 61200),
            "15M": TimeframeStateDetail("15M", "BULLISH", "MARKUP", 63350.0, 64250.0, "DISCOUNT", 244800),
            "3M": TimeframeStateDetail("3M", "BULLISH", "MARKUP", 63600.0, 64100.0, "EQUILIBRIUM", 1224000),
        }
        cards["BTCUSDT"] = AssetMarketCard(
            symbol="BTCUSDT",
            base_asset="BTC",
            quote_asset="USDT",
            current_price=64120.50,
            change_24h_pct=2.45,
            high_24h=64850.00,
            low_24h=62580.00,
            volume_24h_usd=28_450_000_000.0,
            volatility_atr_pct=2.85,
            liquidity_health="TIER_1_HIGH",
            strategy_eligibility=True,
            execution_eligibility="PAPER_AND_DEMO_ELIGIBLE",
            is_priority=True,
            market_structure_summary="HTF Bullish / MTF Consolidation / LTF Markup",
            phase_summary="Phase C Markup Expansion",
            timeframes=btc_tf,
        )

        # 2. ETHUSDT
        eth_tf = {
            "1M": TimeframeStateDetail("1M", "BULLISH", "ACCUMULATION", 2400.0, 3900.0, "DISCOUNT", 84),
            "1W": TimeframeStateDetail("1W", "RANGING", "ACCUMULATION", 2850.0, 3600.0, "EQUILIBRIUM", 364),
            "1D": TimeframeStateDetail("1D", "BULLISH", "MARKUP", 3150.0, 3550.0, "DISCOUNT", 2550),
            "4H": TimeframeStateDetail("4H", "BULLISH", "MARKUP", 3280.0, 3510.0, "EQUILIBRIUM", 15300),
            "1H": TimeframeStateDetail("1H", "BULLISH", "MARKUP", 3340.0, 3480.0, "DISCOUNT", 61200),
            "15M": TimeframeStateDetail("15M", "BULLISH", "MARKUP", 3390.0, 3465.0, "DISCOUNT", 244800),
            "3M": TimeframeStateDetail("3M", "RANGING", "ACCUMULATION", 3410.0, 3450.0, "EQUILIBRIUM", 1224000),
        }
        cards["ETHUSDT"] = AssetMarketCard(
            symbol="ETHUSDT",
            base_asset="ETH",
            quote_asset="USDT",
            current_price=3442.20,
            change_24h_pct=3.12,
            high_24h=3495.00,
            low_24h=3310.00,
            volume_24h_usd=16_200_000_000.0,
            volatility_atr_pct=3.40,
            liquidity_health="TIER_1_HIGH",
            strategy_eligibility=True,
            execution_eligibility="PAPER_AND_DEMO_ELIGIBLE",
            is_priority=True,
            market_structure_summary="HTF Accumulation / MTF Bullish / LTF Markup",
            phase_summary="Phase C Markup Confirmation",
            timeframes=eth_tf,
        )

        # 3. SOLUSDT
        sol_tf = {
            "1M": TimeframeStateDetail("1M", "BULLISH", "MARKUP", 110.0, 210.0, "EQUILIBRIUM", 84),
            "1W": TimeframeStateDetail("1W", "BULLISH", "MARKUP", 130.0, 195.0, "DISCOUNT", 364),
            "1D": TimeframeStateDetail("1D", "BULLISH", "MARKUP", 142.0, 178.0, "DISCOUNT", 2550),
            "4H": TimeframeStateDetail("4H", "BULLISH", "ACCUMULATION", 148.0, 168.0, "EQUILIBRIUM", 15300),
            "1H": TimeframeStateDetail("1H", "BULLISH", "MARKUP", 152.0, 164.0, "DISCOUNT", 61200),
            "15M": TimeframeStateDetail("15M", "BULLISH", "MARKUP", 155.0, 162.5, "DISCOUNT", 244800),
            "3M": TimeframeStateDetail("3M", "RANGING", "EQUILIBRIUM", 156.5, 161.0, "EQUILIBRIUM", 1224000),
        }
        cards["SOLUSDT"] = AssetMarketCard(
            symbol="SOLUSDT",
            base_asset="SOL",
            quote_asset="USDT",
            current_price=158.85,
            change_24h_pct=4.80,
            high_24h=162.90,
            low_24h=150.20,
            volume_24h_usd=4_850_000_000.0,
            volatility_atr_pct=5.10,
            liquidity_health="TIER_1_HIGH",
            strategy_eligibility=True,
            execution_eligibility="PAPER_AND_DEMO_ELIGIBLE",
            is_priority=False,
            market_structure_summary="Bullish Trend across HTF/MTF / Expanding Volatility",
            phase_summary="Phase C Strong Markup",
            timeframes=sol_tf,
        )

        # 4. BNBUSDT
        bnb_tf = {
            "1M": TimeframeStateDetail("1M", "BULLISH", "MARKUP", 480.0, 680.0, "EQUILIBRIUM", 84),
            "1W": TimeframeStateDetail("1W", "RANGING", "ACCUMULATION", 520.0, 610.0, "DISCOUNT", 364),
            "1D": TimeframeStateDetail("1D", "BULLISH", "MARKUP", 545.0, 598.0, "DISCOUNT", 2550),
            "4H": TimeframeStateDetail("4H", "BULLISH", "ACCUMULATION", 560.0, 590.0, "EQUILIBRIUM", 15300),
            "1H": TimeframeStateDetail("1H", "RANGING", "ACCUMULATION", 570.0, 588.0, "EQUILIBRIUM", 61200),
            "15M": TimeframeStateDetail("15M", "BULLISH", "MARKUP", 575.0, 586.0, "DISCOUNT", 244800),
            "3M": TimeframeStateDetail("3M", "BULLISH", "MARKUP", 578.0, 584.0, "EQUILIBRIUM", 1224000),
        }
        cards["BNBUSDT"] = AssetMarketCard(
            symbol="BNBUSDT",
            base_asset="BNB",
            quote_asset="USDT",
            current_price=581.40,
            change_24h_pct=1.15,
            high_24h=588.20,
            low_24h=572.50,
            volume_24h_usd=1_950_000_000.0,
            volatility_atr_pct=2.15,
            liquidity_health="TIER_1_HIGH",
            strategy_eligibility=True,
            execution_eligibility="PAPER_AND_DEMO_ELIGIBLE",
            is_priority=False,
            market_structure_summary="HTF Range High / MTF Bullish Transition",
            phase_summary="Phase B Accumulation Near Key Support",
            timeframes=bnb_tf,
        )

        return cards

    def list_market_assets(self, tenant_id: str = "default") -> Dict[str, Any]:
        """Lists priority assets, all supported assets, and the tenant's watchlist."""
        user_wl = self.get_watchlist(tenant_id)
        all_cards = list(self._asset_profiles.values())
        return {
            "watchlist": [c.to_dict() for c in all_cards if c.symbol in user_wl],
            "priority_assets": [c.to_dict() for c in all_cards if c.is_priority],
            "all_assets": [c.to_dict() for c in all_cards],
            "universe_type": "ADMITTED_CRYPTO_PERPETUAL",
            "execution_mode": "PAPER_AND_DEMO",
            "live_status": "LOCKED_FAIL_CLOSED",
        }

    def get_asset_detail(self, symbol: str) -> Optional[Dict[str, Any]]:
        card = self._asset_profiles.get(symbol.upper())
        if not card:
            return None
        return card.to_dict()

    def get_watchlist(self, tenant_id: str) -> List[str]:
        if tenant_id not in self._watchlists_by_tenant:
            # Default watchlist for new tenants
            self._watchlists_by_tenant[tenant_id] = {"BTCUSDT", "ETHUSDT"}
        return sorted(list(self._watchlists_by_tenant[tenant_id]))

    def toggle_watchlist(self, tenant_id: str, symbol: str) -> List[str]:
        sym = symbol.upper()
        CryptoUniverseManager.validate_asset(sym)
        wl = self._watchlists_by_tenant.setdefault(tenant_id, {"BTCUSDT", "ETHUSDT"})
        if sym in wl:
            wl.remove(sym)
        else:
            wl.add(sym)
        return sorted(list(wl))
