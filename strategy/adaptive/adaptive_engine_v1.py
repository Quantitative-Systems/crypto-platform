"""ADAPTIVE_ENGINE_V1: Causal Adaptive Market-State Engine.

Frozen, immutable decision rules derived from DEV data.
Decoupled from future performance; operates strictly causally at time t.

Core Architecture:
1. Multi-Timeframe State Classification (HTF, MTF, LTF).
2. Frozen State-to-Hypothesis Mapping.
3. Strict Causal Trade / No-Trade Invariants.
4. Scale-Aware Risk & Target Floor Enforcement (>= 4.0R, <= 1.0% equity risk).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from market_model.contracts import (
    MarketPhaseType,
    MarketState,
    StructuralBreakType,
    TrendDirection,
)
from strategy.base import CandidateSignal
from strategy.families.base_family import BaseStrategyFamily
from strategy.families.f01_structure_phase import StructurePhaseFamily
from strategy.families.f05_structure_ob_phase import StructureOBPhaseFamily
from strategy.families.f08_structure_trendline_phase import StructureTrendlinePhaseFamily
from strategy.families.f10_structure_momentum_phase import StructureMomentumPhaseFamily


class AdaptiveMarketState(str, Enum):
    BULL_TRENDING_CONTINUATION = "BULL_TRENDING_CONTINUATION"
    BEAR_TRENDING_CONTINUATION = "BEAR_TRENDING_CONTINUATION"
    BULL_PULLBACK = "BULL_PULLBACK"
    BEAR_PULLBACK = "BEAR_PULLBACK"
    RANGING_CHOP = "RANGING_CHOP"


@dataclass
class AdaptiveDecisionAudit:
    bar_index: int
    timestamp_ms: int
    detected_state: AdaptiveMarketState
    action: str  # "TRADE" or "NO_TRADE"
    selected_family: Optional[str] = None
    reason: str = ""
    htf_trend: str = ""
    mtf_phase: str = ""
    target_r: float = 0.0


class AdaptiveEngineV1(BaseStrategyFamily):
    """Immutable Adaptive Market-State Engine (Version 1)."""

    def __init__(
        self,
        timeframe_set_id: str,
        htf_label: str,
        mtf_label: str,
        ltf_label: str,
        phase_mode: str = "CONTINUATION",
        min_target_r: float = 4.0,
        risk_pct_per_trade: float = 0.01,
    ):
        super().__init__(
            family_id="ADAPTIVE_ENGINE_V1",
            timeframe_set_id=timeframe_set_id,
            htf_label=htf_label,
            mtf_label=mtf_label,
            ltf_label=ltf_label,
            phase_mode=phase_mode,
            min_target_r=min_target_r,
            risk_pct_per_trade=risk_pct_per_trade,
        )

        # Frozen Sub-Components
        self.sub_f08 = StructureTrendlinePhaseFamily(
            timeframe_set_id=timeframe_set_id,
            htf_label=htf_label,
            mtf_label=mtf_label,
            ltf_label=ltf_label,
            phase_mode="CONTINUATION",
            min_target_r=min_target_r,
        )
        self.sub_f05 = StructureOBPhaseFamily(
            timeframe_set_id=timeframe_set_id,
            htf_label=htf_label,
            mtf_label=mtf_label,
            ltf_label=ltf_label,
            phase_mode="CONTINUATION",
            min_target_r=min_target_r,
        )
        self.sub_f10 = StructureMomentumPhaseFamily(
            timeframe_set_id=timeframe_set_id,
            htf_label=htf_label,
            mtf_label=mtf_label,
            ltf_label=ltf_label,
            phase_mode="CONTINUATION",
            min_target_r=min_target_r,
        )
        self.sub_f01 = StructurePhaseFamily(
            timeframe_set_id=timeframe_set_id,
            htf_label=htf_label,
            mtf_label=mtf_label,
            ltf_label=ltf_label,
            phase_mode="CONTINUATION",
            min_target_r=min_target_r,
        )

        self.audit_log: List[AdaptiveDecisionAudit] = []
        self._active_sub: Optional[BaseStrategyFamily] = None
        self._active_sub_name: Optional[str] = None

    def classify_market_state(
        self, htf_state: MarketState, mtf_state: MarketState
    ) -> AdaptiveMarketState:
        """Classify multi-timeframe state into one of the 5 canonical categories."""
        h_trend = htf_state.structure.external_trend
        m_phase = mtf_state.phase.current_phase
        m_trend = mtf_state.structure.external_trend

        # 1. Ranging Chop Filter
        # Conflicting trends, sideways consolidation, or uncertain phase
        if (
            h_trend in (TrendDirection.RANGE, TrendDirection.NEUTRAL, TrendDirection.TRANSITIONAL)
            or m_trend in (TrendDirection.RANGE, TrendDirection.NEUTRAL, TrendDirection.TRANSITIONAL)
            or (h_trend == TrendDirection.BULLISH and m_trend == TrendDirection.BEARISH)
            or (h_trend == TrendDirection.BEARISH and m_trend == TrendDirection.BULLISH)
            or mtf_state.phase.is_compressed
        ):
            return AdaptiveMarketState.RANGING_CHOP

        # 2. Bullish Continuation
        if h_trend == TrendDirection.BULLISH and m_phase in (
            MarketPhaseType.CONTINUATION,
            MarketPhaseType.CONSOLIDATION,
        ):
            return AdaptiveMarketState.BULL_TRENDING_CONTINUATION

        # 3. Bearish Continuation
        if h_trend == TrendDirection.BEARISH and m_phase in (
            MarketPhaseType.CONTINUATION,
            MarketPhaseType.CONSOLIDATION,
        ):
            return AdaptiveMarketState.BEAR_TRENDING_CONTINUATION

        # 4. Bullish Pullback
        if h_trend == TrendDirection.BULLISH and m_phase == MarketPhaseType.PULLBACK:
            return AdaptiveMarketState.BULL_PULLBACK

        # 5. Bearish Pullback
        if h_trend == TrendDirection.BEARISH and m_phase == MarketPhaseType.PULLBACK:
            return AdaptiveMarketState.BEAR_PULLBACK

        return AdaptiveMarketState.RANGING_CHOP

    def evaluate_htf(self, htf_state: MarketState) -> Optional[int]:
        """Base HTF direction evaluation."""
        trend = htf_state.structure.external_trend
        if trend == TrendDirection.BULLISH:
            return 1
        elif trend == TrendDirection.BEARISH:
            return -1
        return None

    def validate_mtf_family_specifics(self, mtf_state: MarketState, direction: int) -> bool:
        """Adaptive specific validation: requires at least one validated sub-family to align."""
        if self.sub_f08.validate_mtf_family_specifics(mtf_state, direction):
            self._active_sub = self.sub_f08
            self._active_sub_name = "F08_STRUCTURE_TRENDLINE_PHASE"
            return True
        elif self.sub_f05.validate_mtf_family_specifics(mtf_state, direction):
            self._active_sub = self.sub_f05
            self._active_sub_name = "F05_STRUCTURE_OB_PHASE"
            return True
        elif self.sub_f10.validate_mtf_family_specifics(mtf_state, direction):
            self._active_sub = self.sub_f10
            self._active_sub_name = "F10_STRUCTURE_MOMENTUM_PHASE"
            return True
        self._active_sub = None
        self._active_sub_name = None
        return False

    def confirm_ltf_entry(
        self, ltf_state: MarketState, direction: int
    ) -> Tuple[bool, Optional[float], Optional[float]]:
        """Delegate entry confirmation to currently active sub-strategy."""
        if self._active_sub is not None:
            return self._active_sub.confirm_ltf_entry(ltf_state, direction)
        return False, None, None

    def evaluate_adaptive_decision(
        self,
        bar_index: int,
        timestamp_ms: int,
        htf_state: MarketState,
        mtf_state: MarketState,
        ltf_state: MarketState,
    ) -> Tuple[Optional[CandidateSignal], AdaptiveDecisionAudit]:
        """Master Causal Adaptive Decision Pipeline at bar i (time t)."""
        state = self.classify_market_state(htf_state, mtf_state)
        curr_px = ltf_state.close_price

        # Rule 1: NO TRADE in Ranging Chop
        if state == AdaptiveMarketState.RANGING_CHOP:
            audit = AdaptiveDecisionAudit(
                bar_index=bar_index,
                timestamp_ms=timestamp_ms,
                detected_state=state,
                action="NO_TRADE",
                reason="REASON_CHOP_FILTER: Market is sideways or HTF/MTF structure conflicts",
                htf_trend=str(htf_state.structure.external_trend.value),
                mtf_phase=str(mtf_state.phase.current_phase.value),
            )
            self.audit_log.append(audit)
            return None, audit

        # Rule 2: NO TRADE in Bearish Pullback
        if state == AdaptiveMarketState.BEAR_PULLBACK:
            audit = AdaptiveDecisionAudit(
                bar_index=bar_index,
                timestamp_ms=timestamp_ms,
                detected_state=state,
                action="NO_TRADE",
                reason="REASON_BEAR_PULLBACK_FILTER: Counter-trend rally into macro bear trend",
                htf_trend=str(htf_state.structure.external_trend.value),
                mtf_phase=str(mtf_state.phase.current_phase.value),
            )
            self.audit_log.append(audit)
            return None, audit

        # Rule 3: Selective Bullish Pullback (Requires deep OTE or discount key zone)
        if state == AdaptiveMarketState.BULL_PULLBACK:
            pd_zone = mtf_state.zones.premium_discount_zone
            if pd_zone != "DISCOUNT":
                audit = AdaptiveDecisionAudit(
                    bar_index=bar_index,
                    timestamp_ms=timestamp_ms,
                    detected_state=state,
                    action="NO_TRADE",
                    reason="REASON_PULLBACK_NOT_IN_DISCOUNT: Retracement has not reached discount dealing range",
                    htf_trend=str(htf_state.structure.external_trend.value),
                    mtf_phase=str(mtf_state.phase.current_phase.value),
                )
                self.audit_log.append(audit)
                return None, audit

        # Directional mapping
        direction = 1 if "BULL" in state.value else -1

        # Causal Strategy Selector based on current state & primitive interactions
        selected_sub: Optional[BaseStrategyFamily] = None
        selected_name = "NONE"

        # Check Trendline first (Expansion mode)
        if self.sub_f08.validate_mtf_family_specifics(mtf_state, direction):
            selected_sub = self.sub_f08
            selected_name = "F08_STRUCTURE_TRENDLINE_PHASE"
        # Check Order Block next (Key Zone retest mode)
        elif self.sub_f05.validate_mtf_family_specifics(mtf_state, direction):
            selected_sub = self.sub_f05
            selected_name = "F05_STRUCTURE_OB_PHASE"
        # Check Momentum expansion
        elif self.sub_f10.validate_mtf_family_specifics(mtf_state, direction):
            selected_sub = self.sub_f10
            selected_name = "F10_STRUCTURE_MOMENTUM_PHASE"
        else:
            audit = AdaptiveDecisionAudit(
                bar_index=bar_index,
                timestamp_ms=timestamp_ms,
                detected_state=state,
                action="NO_TRADE",
                reason="REASON_NO_FAMILY_CONFLUENCE: State active but no specific primitive alignment (F08/F05/F10)",
                htf_trend=str(htf_state.structure.external_trend.value),
                mtf_phase=str(mtf_state.phase.current_phase.value),
            )
            self.audit_log.append(audit)
            return None, audit

        # LTF Entry Confirmation via selected family
        confirmed, sl, target = selected_sub.confirm_ltf_entry(ltf_state, direction)
        if not confirmed or sl is None or target is None:
            audit = AdaptiveDecisionAudit(
                bar_index=bar_index,
                timestamp_ms=timestamp_ms,
                detected_state=state,
                action="NO_TRADE",
                selected_family=selected_name,
                reason="REASON_LTF_UNCONFIRMED: LTF structural break or entry trigger missing",
                htf_trend=str(htf_state.structure.external_trend.value),
                mtf_phase=str(mtf_state.phase.current_phase.value),
            )
            self.audit_log.append(audit)
            return None, audit

        risk_dist = abs(curr_px - sl)
        if risk_dist <= 0:
            return None, audit

        target_r = abs(target - curr_px) / risk_dist

        # Rule 5: Strict Target Floor >= 4.0R
        if target_r < 4.0:
            audit = AdaptiveDecisionAudit(
                bar_index=bar_index,
                timestamp_ms=timestamp_ms,
                detected_state=state,
                action="NO_TRADE",
                selected_family=selected_name,
                reason=f"REASON_TARGET_BELOW_4R: Structural destination ({round(target_r, 2)}R) < 4.0R floor",
                htf_trend=str(htf_state.structure.external_trend.value),
                mtf_phase=str(mtf_state.phase.current_phase.value),
                target_r=round(target_r, 2),
            )
            self.audit_log.append(audit)
            return None, audit

        # Candidate Signal Accepted
        sig = CandidateSignal(
            bar_index=bar_index,
            direction=direction,
            entry_price=float(curr_px),
            stop_price=float(sl),
            target_price=float(target),
            timestamp_ms=timestamp_ms,
            hypothesis_id=f"ADAPTIVE_{selected_name}_{self.timeframe_set_id}",
            risk_pct=self.risk_pct_per_trade,
            meta={
                "adaptive_state": state.value,
                "selected_family": selected_name,
                "target_r": round(target_r, 2),
            },
        )

        audit = AdaptiveDecisionAudit(
            bar_index=bar_index,
            timestamp_ms=timestamp_ms,
            detected_state=state,
            action="TRADE",
            selected_family=selected_name,
            reason=f"SELECTED: State {state.value} satisfied; {selected_name} confluence with {round(target_r, 2)}R destination",
            htf_trend=str(htf_state.structure.external_trend.value),
            mtf_phase=str(mtf_state.phase.current_phase.value),
            target_r=round(target_r, 2),
        )
        self.audit_log.append(audit)
        return sig, audit


# Register with Strategy Family Registry
from strategy.families import FAMILY_REGISTRY
FAMILY_REGISTRY["ADAPTIVE_ENGINE_V1"] = AdaptiveEngineV1
