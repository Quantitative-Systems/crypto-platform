"""Market Regime Contracts & Domain Definitions.

Explicitly decouples Regime (macro/environment climate) from Phase (micro/swing progression).
Phase answers: Is price in Pullback or Continuation?
Regime answers: What kind of macro/volatility/liquidity/correlation climate is the market operating in?
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class VolatilityRegime(str, Enum):
    LOW = "LOW"            # Compression, sub-normal ATR, low realized volatility
    NORMAL = "NORMAL"      # Standard distribution, healthy directional follow-through
    HIGH = "HIGH"          # Elevated ATR, expansion, wider stops required
    EXTREME = "EXTREME"    # Tail risk, spread blowouts, liquidation cascades


class LiquidityRegime(str, Enum):
    ABUNDANT = "ABUNDANT"  # Deep order books, tight spreads, stable funding, positive flows
    NORMAL = "NORMAL"      # Average market depth, normal slippage
    TIGHT = "TIGHT"        # Thin books, widening spreads, erratic slippage
    IMPAIRED = "IMPAIRED"  # Discontinuous liquidity, gap risk, withdrawal freezes


class CorrelationRegime(str, Enum):
    BTC_LED = "BTC_LED"                # High crypto beta to BTC; BTC dominance driving altcoins
    MACRO_LED = "MACRO_LED"            # High correlation to DXY, US yields, SPX, global liquidity
    SECTOR_LED = "SECTOR_LED"          # Layer 1s, DeFi, or AI coins moving independently
    IDIOSYNCRATIC = "IDIOSYNCRATIC"    # Asset-specific decoupling; low pairwise correlation


class TrendRegime(str, Enum):
    TRENDING = "TRENDING"              # Persistent directional impulse across multiple timeframes
    TRANSITIONAL = "TRANSITIONAL"      # Structural inflection, range breakout testing, or momentum fade
    RANGING = "RANGING"                # Mean-reverting, bounding between high and low extremes


class RiskRegime(str, Enum):
    RISK_ON = "RISK_ON"                # Capital flowing into speculative assets, equities up, dollar soft
    NEUTRAL = "NEUTRAL"                # Mixed signals, balanced flows
    RISK_OFF = "RISK_OFF"              # Capital fleeing to USD/cash, bonds bid, risk assets sold


@dataclass
class MarketRegimeSnapshot:
    """Comprehensive environment snapshot at timestamp t."""
    timestamp_ms: int
    volatility: VolatilityRegime = VolatilityRegime.NORMAL
    liquidity: LiquidityRegime = LiquidityRegime.NORMAL
    correlation: CorrelationRegime = CorrelationRegime.BTC_LED
    trend: TrendRegime = TrendRegime.TRANSITIONAL
    risk: RiskRegime = RiskRegime.NEUTRAL
    realized_vol_annualized: float = 0.50
    vol_percentile: float = 0.50
    liquidity_score: float = 1.0
    average_crypto_macro_corr: float = 0.0
    is_favorable_for_trend_following: bool = True
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp_ms": self.timestamp_ms,
            "volatility": self.volatility.value,
            "liquidity": self.liquidity.value,
            "correlation": self.correlation.value,
            "trend": self.trend.value,
            "risk": self.risk.value,
            "realized_vol_annualized": self.realized_vol_annualized,
            "vol_percentile": self.vol_percentile,
            "liquidity_score": self.liquidity_score,
            "average_crypto_macro_corr": self.average_crypto_macro_corr,
            "is_favorable_for_trend_following": self.is_favorable_for_trend_following,
            "meta": self.meta,
        }
