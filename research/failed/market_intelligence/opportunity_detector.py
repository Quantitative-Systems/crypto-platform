"""
QCP Opportunity Detector.
Scans market data and regime outputs to detect structural anomalies and emit
raw OpportunityObservations.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from market_intelligence.continuous_regime_engine import (
    RegimeState,
    FundingState,
    VolatilityState,
    TrendState,
    CorrelationState
)


class OpportunityType(str, enum.Enum):
    FUNDING_ANOMALY = "FUNDING_ANOMALY"
    VOLATILITY_SQUEEZE = "VOLATILITY_SQUEEZE"
    TREND_MOMENTUM = "TREND_MOMENTUM"
    DISPERSION_DIVERGENCE = "DISPERSION_DIVERGENCE"
    LIQUIDITY_IMBALANCE = "LIQUIDITY_IMBALANCE"
    CROSS_EXCHANGE_DISLOCATION = "CROSS_EXCHANGE_DISLOCATION"
    LIQUIDATION_CASCADE = "LIQUIDATION_CASCADE"
    MARKET_MAKING_SPREAD = "MARKET_MAKING_SPREAD"


@dataclass
class OpportunityObservation:
    """A raw, unvalidated observation of a market anomaly."""
    opportunity_id: str
    opportunity_type: OpportunityType
    symbol: str
    magnitude_score: float  # [0.0, 1.0] indicating severity/potential
    description: str
    required_data_tokens: List[str]


class OpportunityDetector:
    """
    Evaluates current regime states, order book structures, and flow indicators across assets
    to find structural crypto opportunities.
    """

    def __init__(self):
        self.observation_counter = 0

    def _generate_id(self, opp_type: str, symbol: str) -> str:
        self.observation_counter += 1
        return f"OPP-{opp_type}-{symbol.replace('/', '')}-{self.observation_counter:04d}"

    def detect_opportunities(
        self,
        regime_states: List[RegimeState],
        order_book_snapshots: Optional[Dict[str, Any]] = None,
        cross_venue_spreads_bps: Optional[Dict[str, float]] = None,
        liquidation_volumes_usd: Optional[Dict[str, float]] = None,
    ) -> List[OpportunityObservation]:
        observations = []

        for rs in regime_states:
            sym_clean = rs.symbol.split('/')[0]
            sym_flat = rs.symbol.replace('/', '')

            # 1. Funding Anomalies (Carry opportunities)
            if rs.funding in (FundingState.EXTREME_POSITIVE_FUNDING, FundingState.EXTREME_NEGATIVE_FUNDING):
                mag = min(1.0, abs(rs.annualized_funding_pct) / 100.0)
                obs = OpportunityObservation(
                    opportunity_id=self._generate_id("CARRY", rs.symbol),
                    opportunity_type=OpportunityType.FUNDING_ANOMALY,
                    symbol=rs.symbol,
                    magnitude_score=mag,
                    description=f"Extreme funding detected ({rs.annualized_funding_pct}% APR). Potential basis carry or mean reversion.",
                    required_data_tokens=[f"FUNDING_RATE_HISTORY_{sym_flat}", f"SPOT_PERP_BASIS_{sym_flat}"]
                )
                observations.append(obs)

            # 2. Volatility Squeeze (Breakout opportunities)
            if rs.volatility == VolatilityState.LOW_VOL_SQUEEZE:
                mag = max(0.0, min(1.0, 1.0 - (rs.volatility_percentile / 25.0)))
                obs = OpportunityObservation(
                    opportunity_id=self._generate_id("VOLSQZ", rs.symbol),
                    opportunity_type=OpportunityType.VOLATILITY_SQUEEZE,
                    symbol=rs.symbol,
                    magnitude_score=mag,
                    description=f"Volatility squeeze detected (Percentile: {rs.volatility_percentile}%). Potential explosive breakout.",
                    required_data_tokens=[f"OHLCV_4h_{sym_clean}", f"L2_ORDER_BOOK_DEPTH_TICK_{sym_clean}"]
                )
                observations.append(obs)

            # 3. Trend Momentum (Directional opportunities)
            if rs.trend in (TrendState.BULL_MOMENTUM, TrendState.BEAR_EXPANSION) and rs.trend_strength_score > 0.8:
                obs = OpportunityObservation(
                    opportunity_id=self._generate_id("TREND", rs.symbol),
                    opportunity_type=OpportunityType.TREND_MOMENTUM,
                    symbol=rs.symbol,
                    magnitude_score=rs.trend_strength_score,
                    description=f"Strong momentum detected ({rs.trend.value}). Potential continuation.",
                    required_data_tokens=[f"OHLCV_4h_{sym_clean}"]
                )
                observations.append(obs)

            # 4. Dispersion / Relative Value (RV opportunities)
            if rs.correlation == CorrelationState.DISPERSED_MARKET and rs.systemic_coupling_score < 0.2:
                obs = OpportunityObservation(
                    opportunity_id=self._generate_id("DISP", rs.symbol),
                    opportunity_type=OpportunityType.DISPERSION_DIVERGENCE,
                    symbol=rs.symbol,
                    magnitude_score=1.0 - rs.systemic_coupling_score,
                    description=f"Market dispersion detected. Potential relative value trades.",
                    required_data_tokens=[f"OHLCV_4h_{sym_clean}", "OHLCV_4h_BTC"]
                )
                observations.append(obs)

        # 5. Liquidity Imbalance & Microstructure (Order Flow / Imbalance)
        if order_book_snapshots:
            for symbol, snapshot in order_book_snapshots.items():
                sym_clean = symbol.split('/')[0]
                sym_flat = symbol.replace('/', '')
                imbalance = getattr(snapshot, "book_imbalance", 0.0)
                spread_bps = getattr(snapshot, "spread_bps", 0.0)
                if abs(imbalance) > 0.35:
                    obs = OpportunityObservation(
                        opportunity_id=self._generate_id("OFI", symbol),
                        opportunity_type=OpportunityType.LIQUIDITY_IMBALANCE,
                        symbol=symbol,
                        magnitude_score=min(1.0, abs(imbalance)),
                        description=f"Order book depth skew of {imbalance:.2f} detected on {symbol}. Short-term queue pressure.",
                        required_data_tokens=[f"ORDER_BOOK_L2_{sym_flat}", f"AGGRESSOR_FLOW_{sym_flat}"]
                    )
                    observations.append(obs)
                elif spread_bps > 5.0:
                    obs = OpportunityObservation(
                        opportunity_id=self._generate_id("MM", symbol),
                        opportunity_type=OpportunityType.MARKET_MAKING_SPREAD,
                        symbol=symbol,
                        magnitude_score=min(1.0, spread_bps / 20.0),
                        description=f"Wide bid-ask spread of {spread_bps:.1f} bps on {symbol}. Potential spread capture.",
                        required_data_tokens=[f"ORDER_BOOK_L2_{sym_flat}"]
                    )
                    observations.append(obs)

        # 6. Cross-Exchange Dislocation (Arbitrage)
        if cross_venue_spreads_bps:
            for symbol, spread_bps in cross_venue_spreads_bps.items():
                sym_flat = symbol.replace('/', '')
                if spread_bps > 10.0:  # >10 bps cross-venue spread
                    obs = OpportunityObservation(
                        opportunity_id=self._generate_id("ARB", symbol),
                        opportunity_type=OpportunityType.CROSS_EXCHANGE_DISLOCATION,
                        symbol=symbol,
                        magnitude_score=min(1.0, spread_bps / 50.0),
                        description=f"Cross-exchange price dislocation of {spread_bps:.1f} bps on {symbol}.",
                        required_data_tokens=[f"SPOT_PERP_BASIS_{sym_flat}", f"ORDER_BOOK_L2_{sym_flat}"]
                    )
                    observations.append(obs)

        # 7. Liquidation Cascade (Event-Driven / Forced Flow)
        if liquidation_volumes_usd:
            for symbol, liq_usd in liquidation_volumes_usd.items():
                sym_flat = symbol.replace('/', '')
                if liq_usd > 500_000.0:  # > $500k liquidation print
                    obs = OpportunityObservation(
                        opportunity_id=self._generate_id("LIQ", symbol),
                        opportunity_type=OpportunityType.LIQUIDATION_CASCADE,
                        symbol=symbol,
                        magnitude_score=min(1.0, liq_usd / 5_000_000.0),
                        description=f"Liquidation cascade volume ${liq_usd:,.0f} detected on {symbol}. Forced seller/buyer exhaustion.",
                        required_data_tokens=[f"LIQUIDATIONS_{sym_flat}", f"AGGRESSOR_FLOW_{sym_flat}"]
                    )
                    observations.append(obs)

        return observations
