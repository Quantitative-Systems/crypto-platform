"""Observation Registry for Canonical Market Model.

Provides a unified, strategy-agnostic registry that extracts structured,
causal observations from MarketState snapshots across:
- Structure (External/Internal Trend, Swings, Breaks, Protected/Weak levels)
- Zones (Order Blocks, FVGs, Imbalance, Supply/Demand, Premium/Discount, Fibonacci)
- Phase (Pullback, Continuation, Depth, Exhaustion)
- Technical (EMA, ATR, ADX, Momentum, Volume, Volatility)
- Regime (Trend Strength, Volatility Regime, Market Phase)
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from market_model.contracts import MarketState, MarketPhaseType, TrendDirection
from market_model.observations.contracts import (
    ObservationCategory,
    ObservationDefinition,
    ObservationValue,
)


class ObservationRegistry:
    """Registry managing extraction and query of MarketState observations."""

    def __init__(self) -> None:
        self._registry: Dict[str, ObservationDefinition] = {}
        self._register_default_extractors()

    def register(self, definition: ObservationDefinition) -> None:
        """Register a new observation definition."""
        self._registry[definition.observation_id] = definition

    def get_definition(self, observation_id: str) -> Optional[ObservationDefinition]:
        return self._registry.get(observation_id)

    def list_observations(self, category: Optional[ObservationCategory] = None) -> List[str]:
        if category is None:
            return list(self._registry.keys())
        return [k for k, v in self._registry.items() if v.category == category]

    def extract(self, observation_id: str, state: MarketState) -> Optional[ObservationValue]:
        definition = self._registry.get(observation_id)
        if not definition:
            return None
        return definition.extractor(state)

    def extract_all(self, state: MarketState) -> Dict[str, ObservationValue]:
        """Extract all registered observations for a given MarketState."""
        results: Dict[str, ObservationValue] = {}
        for obs_id, definition in self._registry.items():
            try:
                results[obs_id] = definition.extractor(state)
            except Exception:
                continue
        return results

    def _register_default_extractors(self) -> None:
        # ----------------------------------------------------
        # 1. STRUCTURE OBSERVATIONS
        # ----------------------------------------------------
        self.register(
            ObservationDefinition(
                observation_id="structure.external_trend",
                category=ObservationCategory.STRUCTURE,
                name="External Trend Direction",
                description="Macro external trend direction (BULLISH, BEARISH, RANGE, NEUTRAL)",
                extractor=lambda s: ObservationValue(
                    observation_id="structure.external_trend",
                    category=ObservationCategory.STRUCTURE,
                    timestamp_ms=s.timestamp_ms,
                    timeframe=s.timeframe,
                    symbol=s.symbol,
                    value=s.structure.external_trend.value if hasattr(s.structure.external_trend, "value") else str(s.structure.external_trend),
                    confidence=1.0,
                ),
            )
        )
        self.register(
            ObservationDefinition(
                observation_id="structure.internal_trend",
                category=ObservationCategory.STRUCTURE,
                name="Internal Trend Direction",
                description="Minor internal structure trend direction",
                extractor=lambda s: ObservationValue(
                    observation_id="structure.internal_trend",
                    category=ObservationCategory.STRUCTURE,
                    timestamp_ms=s.timestamp_ms,
                    timeframe=s.timeframe,
                    symbol=s.symbol,
                    value=s.structure.internal_trend.value if hasattr(s.structure.internal_trend, "value") else str(s.structure.internal_trend),
                    confidence=1.0,
                ),
            )
        )
        self.register(
            ObservationDefinition(
                observation_id="structure.trend_strength",
                category=ObservationCategory.STRUCTURE,
                name="Trend Strength",
                description="Quantitative structural trend strength (0.0 to 1.0)",
                extractor=lambda s: ObservationValue(
                    observation_id="structure.trend_strength",
                    category=ObservationCategory.STRUCTURE,
                    timestamp_ms=s.timestamp_ms,
                    timeframe=s.timeframe,
                    symbol=s.symbol,
                    value=float(s.structure.trend_strength),
                    confidence=1.0,
                ),
            )
        )
        self.register(
            ObservationDefinition(
                observation_id="structure.recent_break",
                category=ObservationCategory.STRUCTURE,
                name="Most Recent Structural Break",
                description="Details of the latest validated BOS / CHoCH / MSS",
                extractor=lambda s: ObservationValue(
                    observation_id="structure.recent_break",
                    category=ObservationCategory.STRUCTURE,
                    timestamp_ms=s.timestamp_ms,
                    timeframe=s.timeframe,
                    symbol=s.symbol,
                    value=(
                        s.structure.recent_breaks[-1].break_type.value
                        if s.structure.recent_breaks
                        else "NONE"
                    ),
                    meta={
                        "break_count": len(s.structure.recent_breaks),
                        "trigger_price": s.structure.recent_breaks[-1].trigger_price if s.structure.recent_breaks else None,
                    },
                ),
            )
        )
        self.register(
            ObservationDefinition(
                observation_id="structure.swing_hierarchy",
                category=ObservationCategory.STRUCTURE,
                name="Swing Hierarchy Snapshot",
                description="Active major/minor high and low coordinates",
                extractor=lambda s: ObservationValue(
                    observation_id="structure.swing_hierarchy",
                    category=ObservationCategory.STRUCTURE,
                    timestamp_ms=s.timestamp_ms,
                    timeframe=s.timeframe,
                    symbol=s.symbol,
                    value={
                        "major_high": s.structure.last_major_high.price if s.structure.last_major_high else None,
                        "major_low": s.structure.last_major_low.price if s.structure.last_major_low else None,
                        "minor_high": s.structure.last_minor_high.price if s.structure.last_minor_high else None,
                        "minor_low": s.structure.last_minor_low.price if s.structure.last_minor_low else None,
                    },
                ),
            )
        )

        # ----------------------------------------------------
        # 2. KEY ZONE OBSERVATIONS
        # ----------------------------------------------------
        self.register(
            ObservationDefinition(
                observation_id="zones.active_order_blocks",
                category=ObservationCategory.ZONES,
                name="Active Unmitigated Order Blocks",
                description="Count and coordinates of active unmitigated Order Blocks",
                extractor=lambda s: ObservationValue(
                    observation_id="zones.active_order_blocks",
                    category=ObservationCategory.ZONES,
                    timestamp_ms=s.timestamp_ms,
                    timeframe=s.timeframe,
                    symbol=s.symbol,
                    value=[z.zone_id for z in self._get_all_zones(s) if z.zone_type == "ORDER_BLOCK" and not z.is_mitigated],
                    meta={
                        "count": len([z for z in self._get_all_zones(s) if z.zone_type == "ORDER_BLOCK" and not z.is_mitigated]),
                        "bullish_count": len([z for z in self._get_all_zones(s) if z.zone_type == "ORDER_BLOCK" and not z.is_mitigated and z.is_bullish]),
                        "bearish_count": len([z for z in self._get_all_zones(s) if z.zone_type == "ORDER_BLOCK" and not z.is_mitigated and not z.is_bullish]),
                    },
                ),
            )
        )
        self.register(
            ObservationDefinition(
                observation_id="zones.active_fvgs",
                category=ObservationCategory.ZONES,
                name="Active Fair Value Gaps",
                description="Count and coordinates of active Fair Value Gaps / Imbalances",
                extractor=lambda s: ObservationValue(
                    observation_id="zones.active_fvgs",
                    category=ObservationCategory.ZONES,
                    timestamp_ms=s.timestamp_ms,
                    timeframe=s.timeframe,
                    symbol=s.symbol,
                    value=[z.zone_id for z in self._get_all_zones(s) if z.zone_type in ("FVG", "IMBALANCE") and not z.is_mitigated],
                    meta={"count": len([z for z in self._get_all_zones(s) if z.zone_type in ("FVG", "IMBALANCE") and not z.is_mitigated])},
                ),
            )
        )
        self.register(
            ObservationDefinition(
                observation_id="zones.premium_discount_equilibrium",
                category=ObservationCategory.ZONES,
                name="Premium / Discount Equilibrium State",
                description="Position of current price relative to dealing range (PREMIUM, DISCOUNT, EQUILIBRIUM)",
                extractor=lambda s: ObservationValue(
                    observation_id="zones.premium_discount_equilibrium",
                    category=ObservationCategory.ZONES,
                    timestamp_ms=s.timestamp_ms,
                    timeframe=s.timeframe,
                    symbol=s.symbol,
                    value=self._compute_pd_state(s),
                ),
            )
        )

        # ----------------------------------------------------
        # 3. PHASE OBSERVATIONS
        # ----------------------------------------------------
        self.register(
            ObservationDefinition(
                observation_id="phase.current_phase",
                category=ObservationCategory.PHASE,
                name="Current Market Phase",
                description="Active market phase (PULLBACK, CONTINUATION, CONSOLIDATION, UNCERTAIN)",
                extractor=lambda s: ObservationValue(
                    observation_id="phase.current_phase",
                    category=ObservationCategory.PHASE,
                    timestamp_ms=s.timestamp_ms,
                    timeframe=s.timeframe,
                    symbol=s.symbol,
                    value=s.phase.current_phase.value if hasattr(s.phase.current_phase, "value") else str(s.phase.current_phase),
                    meta={
                        "depth_pct": float(s.phase.depth_pct),
                        "duration_bars": int(s.phase.duration_bars),
                        "is_displaced": bool(s.phase.is_displaced),
                    },
                ),
            )
        )

        # ----------------------------------------------------
        # 4. TECHNICAL & VOLATILITY OBSERVATIONS
        # ----------------------------------------------------
        self.register(
            ObservationDefinition(
                observation_id="technical.ema_alignment",
                category=ObservationCategory.TECHNICAL,
                name="EMA Alignment",
                description="Price alignment relative to EMA_50 / EMA_200",
                extractor=lambda s: ObservationValue(
                    observation_id="technical.ema_alignment",
                    category=ObservationCategory.TECHNICAL,
                    timestamp_ms=s.timestamp_ms,
                    timeframe=s.timeframe,
                    symbol=s.symbol,
                    value={
                        "ema_50": self._get_measurements_dict(s).get("ema_50"),
                        "ema_200": self._get_measurements_dict(s).get("ema_200"),
                        "atr_14": self._get_measurements_dict(s).get("atr_14", getattr(s.measurements, "atr", 0.0)),
                        "adx_14": self._get_measurements_dict(s).get("adx_14", getattr(s.measurements, "adx", 0.0)),
                    },
                ),
            )
        )

        # ----------------------------------------------------
        # 5. REGIME OBSERVATIONS
        # ----------------------------------------------------
        self.register(
            ObservationDefinition(
                observation_id="regime.market_regime",
                category=ObservationCategory.REGIME,
                name="Market Macro Regime",
                description="Synthetic market regime classification",
                extractor=lambda s: ObservationValue(
                    observation_id="regime.market_regime",
                    category=ObservationCategory.REGIME,
                    timestamp_ms=s.timestamp_ms,
                    timeframe=s.timeframe,
                    symbol=s.symbol,
                    value=self._classify_regime(s),
                ),
            )
        )

    def _get_all_zones(self, s: MarketState) -> List[Any]:
        if hasattr(s, "zones") and s.zones is not None:
            return (
                getattr(s.zones, "order_blocks", []) +
                getattr(s.zones, "fair_value_gaps", []) +
                getattr(s.zones, "supply_demand", []) +
                getattr(s.zones, "support_resistance", [])
            )
        if hasattr(s, "key_zones") and s.key_zones is not None:
            return s.key_zones
        return []

    def _get_measurements_dict(self, s: MarketState) -> Dict[str, Any]:
        if hasattr(s, "measurements") and s.measurements is not None:
            if hasattr(s.measurements, "__dict__"):
                return s.measurements.__dict__
            if isinstance(s.measurements, dict):
                return s.measurements
        return {}

    def _compute_pd_state(self, s: MarketState) -> str:
        h = s.structure.last_major_high.price if s.structure.last_major_high else None
        l = s.structure.last_major_low.price if s.structure.last_major_low else None
        if h is None or l is None or h <= l:
            return "EQUILIBRIUM"
        eq = (h + l) / 2.0
        all_zones = self._get_all_zones(s)
        if all_zones:
            ref = all_zones[0].high_price
            return "DISCOUNT" if ref < eq else "PREMIUM"
        return "EQUILIBRIUM"

    def _classify_regime(self, s: MarketState) -> str:
        trend = s.structure.external_trend
        phase = s.phase.current_phase
        if trend == TrendDirection.BULLISH:
            return "BULL_TRENDING" if phase == MarketPhaseType.CONTINUATION else "BULL_PULLBACK"
        elif trend == TrendDirection.BEARISH:
            return "BEAR_TRENDING" if phase == MarketPhaseType.CONTINUATION else "BEAR_PULLBACK"
        return "RANGING_CHOP"


# Global singleton instance
OBSERVATION_REGISTRY = ObservationRegistry()
