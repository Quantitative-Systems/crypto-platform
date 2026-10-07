"""
Product 02 — Strategy Engine: Alpha Regime Filter
Detects market compression, volatility squeeze, and structural chop to prevent
false liquidity sweep executions during unfavorable low-expansion market environments.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
from market_intelligence.primitives import MarketStatePayload, Candle, MarketPhase


@dataclass(frozen=True)
class RegimeDecision:
    is_permitted: bool
    regime_label: str
    atr: float
    volatility_ratio: float
    reason: Optional[str] = None


class RegimeFilter:
    """
    Evaluates market regime characteristics to filter out dead chop and volatility compression.
    """

    def __init__(
        self,
        min_volatility_ratio: float = 0.65,
        atr_period_short: int = 14,
        atr_period_long: int = 50,
        enable_filter: bool = True
    ):
        self.min_volatility_ratio = min_volatility_ratio
        self.atr_period_short = atr_period_short
        self.atr_period_long = atr_period_long
        self.enable_filter = enable_filter

    @staticmethod
    def compute_atr(candles: List[Candle], period: int = 14) -> float:
        """
        Computes the Average True Range (ATR) causally across closed historical candles.
        """
        if len(candles) < 2:
            return 0.0

        n = min(len(candles) - 1, period)
        if n <= 0:
            return 0.0

        true_ranges: List[float] = []
        for i in range(len(candles) - n, len(candles)):
            curr = candles[i]
            prev = candles[i - 1]
            tr = max(
                curr.high - curr.low,
                abs(curr.high - prev.close),
                abs(curr.low - prev.close)
            )
            true_ranges.append(tr)

        return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0

    def evaluate(
        self,
        htf_payload: MarketStatePayload,
        recent_candles: Optional[List[Candle]] = None
    ) -> RegimeDecision:
        """
        Evaluates whether current HTF market state permits strategy candidate formation.
        """
        if not self.enable_filter:
            return RegimeDecision(
                is_permitted=True,
                regime_label="FILTER_DISABLED",
                atr=0.0,
                volatility_ratio=1.0,
                reason=None
            )

        # 1. Structural Phase Check
        if htf_payload.phase_state == MarketPhase.COMPRESSION:
            # Check if payload explicitly reports compression phase
            return RegimeDecision(
                is_permitted=False,
                regime_label="COMPRESSION_PHASE",
                atr=0.0,
                volatility_ratio=0.0,
                reason="REJECT_REGIME_STRUCTURAL_COMPRESSION"
            )

        # 2. Volatility Compression Check (if historical candles are provided)
        if recent_candles and len(recent_candles) >= self.atr_period_long:
            short_atr = self.compute_atr(recent_candles, self.atr_period_short)
            long_atr = self.compute_atr(recent_candles, self.atr_period_long)

            if long_atr > 0:
                vol_ratio = short_atr / long_atr
                if vol_ratio < self.min_volatility_ratio:
                    return RegimeDecision(
                        is_permitted=False,
                        regime_label="VOLATILITY_SQUEEZE",
                        atr=short_atr,
                        volatility_ratio=vol_ratio,
                        reason=f"REJECT_REGIME_VOLATILITY_SQUEEZE_{vol_ratio:.2f}"
                    )
                return RegimeDecision(
                    is_permitted=True,
                    regime_label="HEALTHY_VOLATILITY",
                    atr=short_atr,
                    volatility_ratio=vol_ratio,
                    reason=None
                )

        # Default permit if insufficient candle history for ATR calculation
        return RegimeDecision(
            is_permitted=True,
            regime_label="NORMAL",
            atr=0.0,
            volatility_ratio=1.0,
            reason=None
        )
