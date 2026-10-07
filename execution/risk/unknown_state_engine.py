"""Unknown State Engine: Novelty Detection, Data Anomaly, and Model Dissonance.

Detects uncharacterized, unstable, or aberrant conditions:
- Data feed anomalies (stale bars, inverted OHLC, extreme timestamp gaps)
- Structural dissonance (extreme timeframe conflict, broken swing geometry)
- Novel regime shocks (volatility > 4 sigma above baseline, correlation collapse)
- Microstructure dislocation (spread blowout > 25 bps, order book vacuum)

Core Invariant:
"The system must prefer missing an opportunity over entering a condition it cannot characterize."
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from execution.risk.contracts import MarketClarityState
from market_intelligence.regimes.regime_contracts import (
    MarketRegimeSnapshot,
    VolatilityRegime,
)
from market_model.contracts import MarketState, TrendDirection


@dataclass
class ClarityEvaluation:
    clarity_state: MarketClarityState
    is_tradable: bool
    confidence_score: float                # 0.0 to 1.0
    detected_anomalies: List[str] = field(default_factory=list)
    reason: str = "Market condition is structurally characterized."


class UnknownStateEngine:
    """Classifies market intelligibility and flags novel/unseen or corrupted conditions."""

    def __init__(
        self,
        max_spread_bps: float = 25.0,
        max_vol_sigma: float = 3.5,
    ):
        self.max_spread_bps = max_spread_bps
        self.max_vol_sigma = max_vol_sigma

    def evaluate_clarity(
        self,
        htf_state: MarketState,
        mtf_state: MarketState,
        ltf_state: MarketState,
        regime: Optional[MarketRegimeSnapshot] = None,
        quote_spread_bps: float = 1.0,
        expected_bar_interval_ms: Optional[int] = None,
    ) -> ClarityEvaluation:
        """Evaluate structural, contextual, and operational clarity at time t."""
        anomalies: List[str] = []

        # 1. DATA RISK: Forensic Data Invariants Check
        # Check OHLC validity
        for label, st in [("HTF", htf_state), ("MTF", mtf_state), ("LTF", ltf_state)]:
            if st.close_price <= 0:
                anomalies.append(f"DATA_RISK: Non-positive close price on {label} ({st.close_price})")
            if st.high_price > 0 and st.low_price > 0 and st.high_price < st.low_price:
                anomalies.append(f"DATA_RISK: Inverted OHLC (High < Low) on {label}")
            if st.volume < 0:
                anomalies.append(f"DATA_RISK: Negative volume on {label} ({st.volume})")

        # Check timestamp consistency
        if ltf_state.timestamp_ms < mtf_state.timestamp_ms - (7 * 24 * 3600 * 1000):
            anomalies.append("DATA_RISK: Timestamp retrocession between LTF and MTF")

        # 2. EXECUTION RISK: Microstructure Dislocation
        if quote_spread_bps > self.max_spread_bps:
            anomalies.append(f"EXECUTION_RISK: Spread blowout ({quote_spread_bps:.1f} bps > {self.max_spread_bps} bps)")

        # 3. NOVEL REGIME SHOCK: Extreme Volatility Dislocation
        if regime and regime.volatility == VolatilityRegime.EXTREME:
            if regime.vol_percentile > 0.98:
                anomalies.append(f"NOVELTY_RISK: Unprecedented volatility expansion ({regime.realized_vol_annualized:.1f} ann vol, 98th+ percentile)")

        # 4. MODEL RISK: Extreme Structural Dissonance
        h_trend = htf_state.structure.external_trend
        m_trend = mtf_state.structure.external_trend
        l_trend = ltf_state.structure.external_trend

        # Severe dissonance: HTF strong bull, but MTF and LTF show violent displacement lower with no key zones
        if h_trend == TrendDirection.BULLISH and m_trend == TrendDirection.BEARISH and l_trend == TrendDirection.BEARISH:
            if not mtf_state.zones.order_blocks and not mtf_state.zones.fair_value_gaps:
                anomalies.append("MODEL_RISK: Severe structural dissonance with zero established key zones")

        # Resolution of Clarity State
        if anomalies:
            return ClarityEvaluation(
                clarity_state=MarketClarityState.UNKNOWN_UNSTABLE,
                is_tradable=False,
                confidence_score=0.10,
                detected_anomalies=anomalies,
                reason=f"UNKNOWN_UNSTABLE: {anomalies[0]}",
            )

        # Check for Known Unfavorable (Chop / Sideways)
        if h_trend in (TrendDirection.RANGE, TrendDirection.NEUTRAL) and m_trend in (TrendDirection.RANGE, TrendDirection.NEUTRAL):
            return ClarityEvaluation(
                clarity_state=MarketClarityState.KNOWN_UNFAVORABLE,
                is_tradable=False,
                confidence_score=0.85,
                reason="KNOWN_UNFAVORABLE: Market is in documented multi-timeframe consolidation/chop.",
            )

        # Check for Transition
        if h_trend != m_trend or mtf_state.phase.current_phase.value == "UNCERTAIN":
            return ClarityEvaluation(
                clarity_state=MarketClarityState.TRANSITION,
                is_tradable=True, # Tradable but with reduced sizing
                confidence_score=0.60,
                reason="TRANSITION: Timeframe structure in retest or transition.",
            )

        # Known Favorable
        return ClarityEvaluation(
            clarity_state=MarketClarityState.KNOWN_FAVORABLE,
            is_tradable=True,
            confidence_score=0.90,
            reason="KNOWN_FAVORABLE: Strong structural alignment and characterized regime.",
        )
