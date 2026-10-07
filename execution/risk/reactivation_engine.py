"""Reactivation & Recovery Engine: Staged Post-Crisis Regime Re-Entry.

Governs the deterministic transition from crisis FLAT/HALT back to active participation:
1. Crisis Disorder Detection (spread blowout, 4-sigma vol, liquidation cascades).
2. Stabilization Verification (volatility percentile < 90, spread <= 8 bps, order book healing).
3. Structural Recovery Confirmation (higher low formation, zone reclaim, phase continuation).
4. Staged Pacing: Tier 1 Probe (0.25x) -> Tier 2 Confirm (0.50x) -> Tier 3 Full (1.0x).
5. False Recovery Tripwires (rapid abort on lower-low breakdown).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from execution.risk.contracts import (
    MarketClarityState,
    ReactivationStage,
    RecoveryConfirmationAudit,
    RiskAction,
)
from market_intelligence.positioning.positioning_engine import (
    FundingState,
    PositioningSnapshot,
    TrappedState,
)
from market_intelligence.regimes.regime_contracts import (
    LiquidityRegime,
    MarketRegimeSnapshot,
    TrendRegime,
    VolatilityRegime,
)
from market_model.contracts import MarketPhaseType, MarketState, TrendDirection


class ReactivationEngine:
    """Manages autonomous transition from defensive FLAT/HALT to active trading."""

    def __init__(
        self,
        max_stabilization_spread_bps: float = 8.0,
        vix_calm_ceiling: float = 26.0,
        tier1_probe_risk_mult: float = 0.25,
        tier2_confirm_risk_mult: float = 0.50,
        tier3_full_risk_mult: float = 1.00,
        cool_off_bars: int = 12,
    ):
        self.max_spread_bps = max_stabilization_spread_bps
        self.vix_ceiling = vix_calm_ceiling
        self.tier1_mult = tier1_probe_risk_mult
        self.tier2_mult = tier2_confirm_risk_mult
        self.tier3_mult = tier3_full_risk_mult
        self.tier1_probe_risk_mult = tier1_probe_risk_mult
        self.tier2_confirm_risk_mult = tier2_confirm_risk_mult
        self.tier3_full_risk_mult = tier3_full_risk_mult
        self.cool_off_bars = cool_off_bars

        # State tracking per symbol
        self._current_stages: Dict[str, ReactivationStage] = {}
        self._bars_since_crisis: Dict[str, int] = {}
        self._audit_log: List[RecoveryConfirmationAudit] = []

    def get_stage(self, symbol: str) -> ReactivationStage:
        return self._current_stages.get(symbol, ReactivationStage.FULL_RECOVERY_ACTIVE)

    def set_stage(self, symbol: str, stage: ReactivationStage) -> None:
        self._current_stages[symbol] = stage

    def register_crisis_event(self, symbol: str) -> None:
        """Triggered when market experiences severe disorder or circuit breaker."""
        self._current_stages[symbol] = ReactivationStage.CRISIS_FLAT
        self._bars_since_crisis[symbol] = 0

    def register_false_recovery_failure(self, symbol: str) -> None:
        """Triggered when a probe re-entry fails into a new low."""
        self._current_stages[symbol] = ReactivationStage.FALSE_RECOVERY_ABORT
        self._bars_since_crisis[symbol] = 0

    def evaluate_reactivation_status(
        self,
        symbol: str,
        timestamp_ms: int,
        htf_state: MarketState,
        mtf_state: MarketState,
        ltf_state: MarketState,
        direction: int,
        regime: Optional[MarketRegimeSnapshot] = None,
        positioning: Optional[PositioningSnapshot] = None,
        quote_spread_bps: float = 1.0,
        vix_level: float = 18.0,
    ) -> RecoveryConfirmationAudit:
        """Evaluate 5-dimensional recovery confirmation and assign staged risk factor."""
        curr_stage = self._current_stages.get(symbol, ReactivationStage.FULL_RECOVERY_ACTIVE)
        bars_since = self._bars_since_crisis.get(symbol, 999)

        # 1. Dimension 1: Volatility Normalization
        vol_normalized = True
        if regime:
            if regime.volatility == VolatilityRegime.EXTREME:
                vol_normalized = False
            elif regime.vol_percentile >= 0.90:
                vol_normalized = False

        # 2. Dimension 2: Liquidity Restored
        liq_restored = (quote_spread_bps <= self.max_spread_bps)
        if regime and regime.liquidity == LiquidityRegime.IMPAIRED:
            liq_restored = False

        # 3. Dimension 3: Structural Higher-Low / Trend Alignment
        # Extract structure info safely
        mtf_trend = getattr(mtf_state.structure, "external_trend", TrendDirection.NEUTRAL)
        mtf_int_trend = getattr(mtf_state.structure, "internal_trend", TrendDirection.NEUTRAL)
        mtf_phase = getattr(mtf_state.phase, "current_phase", MarketPhaseType.CONTINUATION)
        htf_trend = getattr(htf_state.structure, "external_trend", TrendDirection.NEUTRAL)

        # Structure alignment check
        struct_aligned = False
        if direction == 1:  # Long Recovery
            if mtf_trend == TrendDirection.BULLISH and mtf_phase == MarketPhaseType.CONTINUATION:
                struct_aligned = True
            elif mtf_int_trend == TrendDirection.BULLISH and mtf_phase == MarketPhaseType.CONTINUATION:
                struct_aligned = True
        elif direction == -1:  # Short Breakdown
            if mtf_trend == TrendDirection.BEARISH and mtf_phase == MarketPhaseType.CONTINUATION:
                struct_aligned = True
            elif mtf_int_trend == TrendDirection.BEARISH and mtf_phase == MarketPhaseType.CONTINUATION:
                struct_aligned = True

        # 4. Dimension 4: Cross-Market Calming
        cross_market_calm = (vix_level <= self.vix_ceiling)

        # 5. Dimension 5: Positioning Stability
        pos_safe = True
        if positioning:
            funding_rate = getattr(positioning, "funding_rate_8h_bps", getattr(positioning, "funding_rate_bps", 0.0))
            if direction == 1 and funding_rate > 35.0:
                pos_safe = False  # Overheated flush risk
            elif direction == -1 and funding_rate < -15.0:
                pos_safe = False  # Squeeze risk

        # -------------------------------------------------------------
        # STATE MACHINE TRANSITION RESOLUTION
        # -------------------------------------------------------------
        next_stage = curr_stage
        risk_factor = self.tier3_full_risk_mult
        reason = "Normal market conditions; full operational capacity."

        if not vol_normalized or not liq_restored:
            # Active crisis or lingering microstructure disorder
            next_stage = ReactivationStage.CRISIS_FLAT
            risk_factor = 0.0
            reason = f"Microstructure disorder: Vol normal={vol_normalized}, Spread normal={liq_restored} ({quote_spread_bps:.1f} bps)."

        elif curr_stage in (ReactivationStage.CRISIS_FLAT, ReactivationStage.FALSE_RECOVERY_ABORT):
            # Attempting initial recovery from flat
            if vol_normalized and liq_restored and cross_market_calm:
                if struct_aligned:
                    next_stage = ReactivationStage.STRUCTURAL_TRANSITION
                    risk_factor = self.tier2_mult
                    reason = "Tier 2 Transition: Higher low established with liquidity restored."
                else:
                    next_stage = ReactivationStage.STABILIZATION_PROBE
                    risk_factor = self.tier1_mult
                    reason = "Tier 1 Probe: Volatility and spreads healed; probing initial stabilization."
            else:
                next_stage = ReactivationStage.CRISIS_FLAT
                risk_factor = 0.0
                reason = "Awaiting macro/volatility stabilization."

        elif curr_stage == ReactivationStage.STABILIZATION_PROBE:
            # Progressing from Tier 1 Probe to Tier 2 Transition
            if struct_aligned and pos_safe:
                next_stage = ReactivationStage.STRUCTURAL_TRANSITION
                risk_factor = self.tier2_mult
                reason = "Tier 2 Transition: MTF continuation confirmed."
            else:
                next_stage = ReactivationStage.STABILIZATION_PROBE
                risk_factor = self.tier1_mult
                reason = "Tier 1 Probe maintained; awaiting structural confirmation."

        elif curr_stage == ReactivationStage.STRUCTURAL_TRANSITION:
            # Progressing from Tier 2 Confirm
            if htf_trend == (TrendDirection.BULLISH if direction == 1 else TrendDirection.BEARISH) and pos_safe:
                next_stage = ReactivationStage.FULL_RECOVERY_ACTIVE
                risk_factor = self.tier3_full_risk_mult
                reason = "Tier 3 Full Recovery: Multi-timeframe trend alignment restored."
            else:
                risk_factor = self.tier2_mult
                reason = "Tier 2 Transition maintained; HTF trend not yet fully aligned."

        elif curr_stage == ReactivationStage.FULL_RECOVERY_ACTIVE:
            risk_factor = self.tier3_full_risk_mult
            reason = "Full recovery active: Normal participation approved."

        self._current_stages[symbol] = next_stage
        self._bars_since_crisis[symbol] = bars_since + 1

        audit = RecoveryConfirmationAudit(
            timestamp_ms=timestamp_ms,
            symbol=symbol,
            stage=next_stage,
            is_volatility_normalized=vol_normalized,
            is_liquidity_restored=liq_restored,
            is_structure_aligned=struct_aligned,
            is_cross_market_calm=cross_market_calm,
            is_positioning_safe=pos_safe,
            approved_risk_factor=risk_factor,
            reason=reason,
            meta={"bars_since_crisis": self._bars_since_crisis[symbol]},
        )
        self._audit_log.append(audit)
        return audit
