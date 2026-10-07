"""Systemic Risk Governor: 7-Layer Capital Defense & Absolute Trade Gate.

Implements the non-negotiable architectural law:
"Survive first, profit second."
The Market Model finds opportunity; the Causal Intelligence explains context;
and the Systemic Risk Governor has absolute authority to say NO TRADE.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from execution.portfolio.risk_governor import PortfolioRiskGovernor
from execution.risk.contracts import (
    DefenseLayerCheck,
    DrawdownTier,
    MarketClarityState,
    RiskAction,
    SystemRiskVerdict,
)
from execution.risk.drawdown_governor import DrawdownGovernor
from execution.risk.reactivation_engine import ReactivationEngine
from execution.risk.unknown_state_engine import UnknownStateEngine
from market_intelligence.events.contracts import EventTimeContext
from market_intelligence.positioning.positioning_engine import (
    FundingState,
    PositioningSnapshot,
    TrappedState,
)
from market_intelligence.regimes.regime_contracts import (
    MarketRegimeSnapshot,
    VolatilityRegime,
)
from market_model.contracts import MarketState


class SystemicRiskGovernor:
    """Master institutional risk arbiter governing all 7 layers of defense."""

    def __init__(
        self,
        max_trade_risk_pct: float = 0.01,         # Layer 1: 1.0% hard ceiling per trade
        max_portfolio_heat_pct: float = 0.03,     # Layer 2: 3.0% hard ceiling total portfolio
        drawdown_governor: Optional[DrawdownGovernor] = None,
        unknown_state_engine: Optional[UnknownStateEngine] = None,
        portfolio_governor: Optional[PortfolioRiskGovernor] = None,
        reactivation_engine: Optional[ReactivationEngine] = None,
        enable_layer_1: bool = True,
        enable_layer_2: bool = True,
        enable_layer_3: bool = True,
        enable_layer_4: bool = True,
        enable_layer_5: bool = True,
        enable_layer_6: bool = True,
        enable_layer_7: bool = True,
        enable_positioning: bool = True,
        calibration_mode: str = "STRICT",         # "STRICT" or "CALIBRATED"
    ):
        self.max_trade_risk_pct = max_trade_risk_pct
        self.max_portfolio_heat_pct = max_portfolio_heat_pct
        self.dd_governor = drawdown_governor or DrawdownGovernor()
        self.unknown_engine = unknown_state_engine or UnknownStateEngine()
        self.portfolio_governor = portfolio_governor or PortfolioRiskGovernor()
        self.reactivation_engine = reactivation_engine
        self.enable_layer_1 = enable_layer_1
        self.enable_layer_2 = enable_layer_2
        self.enable_layer_3 = enable_layer_3
        self.enable_layer_4 = enable_layer_4
        self.enable_layer_5 = enable_layer_5
        self.enable_layer_6 = enable_layer_6
        self.enable_layer_7 = enable_layer_7
        self.enable_positioning = enable_positioning
        self.calibration_mode = calibration_mode

    def evaluate_risk_verdict(
        self,
        symbol: str,
        direction: int,                           # +1 LONG, -1 SHORT
        candidate_destination_r: float,
        htf_state: MarketState,
        mtf_state: MarketState,
        ltf_state: MarketState,
        regime: Optional[MarketRegimeSnapshot] = None,
        positioning: Optional[PositioningSnapshot] = None,
        event_context: Optional[EventTimeContext] = None,
        quote_spread_bps: float = 1.0,
        current_active_portfolio_risk_pct: float = 0.0,
        proposed_base_risk_pct: float = 0.01,
        timestamp_ms: int = 0,
        vix_level: float = 18.0,
    ) -> SystemRiskVerdict:
        """Execute exhaustive 7-layer defense evaluation."""
        checks: List[DefenseLayerCheck] = []
        blockers: List[str] = []
        risk_multiplier = 1.0
        target_r_floor = 4.0

        # -------------------------------------------------------------
        # LAYER 6: DRAWDOWN GOVERNOR (Circuit Breaker & Tiered Haircut)
        # -------------------------------------------------------------
        dd_status = self.dd_governor.evaluate_status()
        if self.enable_layer_6:
            if dd_status.is_halted:
                blockers.append(f"LAYER_6_DRAWDOWN: {dd_status.message}")
                checks.append(DefenseLayerCheck("LAYER_6_DRAWDOWN", False, 0.0, dd_status.destination_r_floor, dd_status.message))
            else:
                m = dd_status.risk_multiplier
                if self.calibration_mode == "CALIBRATED" and dd_status.tier == DrawdownTier.ELEVATED and candidate_destination_r >= 5.0:
                    m = 0.75  # Calibrated: grant 0.75x to high-asymmetry >= 5R trades in elevated DD
                risk_multiplier *= m
                target_r_floor = max(target_r_floor, dd_status.destination_r_floor)
                checks.append(DefenseLayerCheck("LAYER_6_DRAWDOWN", True, m, target_r_floor, dd_status.message))
        else:
            checks.append(DefenseLayerCheck("LAYER_6_DRAWDOWN", True, 1.0, 4.0, "Layer 6 disabled."))

        # -------------------------------------------------------------
        # LAYER 7: SYSTEMIC ANOMALY & UNKNOWN STATE ENGINE
        # -------------------------------------------------------------
        clarity = self.unknown_engine.evaluate_clarity(
            htf_state=htf_state,
            mtf_state=mtf_state,
            ltf_state=ltf_state,
            regime=regime,
            quote_spread_bps=quote_spread_bps,
        )
        if self.enable_layer_7:
            if clarity.clarity_state == MarketClarityState.UNKNOWN_UNSTABLE:
                blockers.append(f"LAYER_7_UNKNOWN_STATE: {clarity.reason}")
                checks.append(DefenseLayerCheck("LAYER_7_UNKNOWN_STATE", False, 0.0, target_r_floor, clarity.reason))
            elif clarity.clarity_state == MarketClarityState.KNOWN_UNFAVORABLE:
                blockers.append(f"LAYER_7_UNFAVORABLE: {clarity.reason}")
                checks.append(DefenseLayerCheck("LAYER_7_UNFAVORABLE", False, 0.0, target_r_floor, clarity.reason))
            elif clarity.clarity_state == MarketClarityState.TRANSITION:
                risk_multiplier *= 0.50  # 50% haircut during structural transition
                checks.append(DefenseLayerCheck("LAYER_7_TRANSITION", True, 0.50, target_r_floor, clarity.reason))
            else:
                checks.append(DefenseLayerCheck("LAYER_7_CLARITY", True, 1.0, target_r_floor, "Market characterized and favorable."))
        else:
            checks.append(DefenseLayerCheck("LAYER_7_CLARITY", True, 1.0, target_r_floor, "Layer 7 disabled."))

        # -------------------------------------------------------------
        # LAYER 5: EVENT RISK (Event Clock Proximity Gating)
        # -------------------------------------------------------------
        if self.enable_layer_5:
            if event_context and event_context.is_trading_prohibited:
                blockers.append(f"LAYER_5_EVENT_RISK: {event_context.reason}")
                checks.append(DefenseLayerCheck("LAYER_5_EVENT_RISK", False, 0.0, target_r_floor, event_context.reason))
            else:
                checks.append(DefenseLayerCheck("LAYER_5_EVENT_RISK", True, 1.0, target_r_floor, "Outside catalyst freeze window."))
        else:
            checks.append(DefenseLayerCheck("LAYER_5_EVENT_RISK", True, 1.0, target_r_floor, "Layer 5 disabled."))

        # -------------------------------------------------------------
        # LAYER 4: REGIME RISK
        # -------------------------------------------------------------
        if self.enable_layer_4 and regime:
            if regime.volatility == VolatilityRegime.EXTREME:
                blockers.append("LAYER_4_REGIME: Extreme volatility regime prohibits entries.")
                checks.append(DefenseLayerCheck("LAYER_4_REGIME", False, 0.0, target_r_floor, "Extreme volatility."))
            elif not regime.is_favorable_for_trend_following:
                blockers.append("LAYER_4_REGIME: Unfavorable regime climate (Tight Liquidity / Chop).")
                checks.append(DefenseLayerCheck("LAYER_4_REGIME", False, 0.0, target_r_floor, "Unfavorable regime."))
            elif regime.volatility == VolatilityRegime.HIGH:
                m_factor = 0.50
                if self.calibration_mode == "CALIBRATED":
                    phase_str = getattr(mtf_state.phase, "value", str(mtf_state.phase))
                    if phase_str == "CONTINUATION" and candidate_destination_r >= 4.5:
                        m_factor = 0.75  # Calibrated: 0.75x for strong continuation with >= 4.5R target
                risk_multiplier *= m_factor
                checks.append(DefenseLayerCheck("LAYER_4_REGIME", True, m_factor, target_r_floor, "High volatility haircut applied."))
            else:
                checks.append(DefenseLayerCheck("LAYER_4_REGIME", True, 1.0, target_r_floor, "Regime favorable."))
        else:
            checks.append(DefenseLayerCheck("LAYER_4_REGIME", True, 1.0, target_r_floor, "Layer 4 disabled."))

        # -------------------------------------------------------------
        # RECONCILED POSITIONING DYNAMICS (Reconciling Model 3 Inconsistency)
        # -------------------------------------------------------------
        if self.enable_positioning and positioning:
            trapped_val = getattr(positioning, "trapped_setup", TrappedState.NONE)
            funding_state_val = getattr(positioning, "funding_state", None)
            funding_bps = getattr(positioning, "funding_rate_8h_bps", getattr(positioning, "funding_rate_bps", 0.0))

            if funding_state_val is None:
                if funding_bps > 25.0:
                    funding_state_val = FundingState.EXTREME_POSITIVE
                elif funding_bps < -12.0:
                    funding_state_val = FundingState.EXTREME_NEGATIVE
                elif funding_bps > 10.0:
                    funding_state_val = FundingState.ELEVATED
                elif funding_bps < -2.0:
                    funding_state_val = FundingState.DISCOUNT
                else:
                    funding_state_val = FundingState.NEUTRAL

            if direction == 1:  # Looking for Long
                if trapped_val == TrappedState.SHORT_SQUEEZE_PRIME:
                    risk_multiplier *= 1.25  # Short squeeze bonus
                    checks.append(DefenseLayerCheck("POSITIONING_DYNAMICS", True, 1.25, target_r_floor, "Short squeeze asymmetric edge."))
                elif funding_state_val == FundingState.EXTREME_POSITIVE:
                    # In secular bull, allow trade with haircut; in transition or chop, block it!
                    if clarity.clarity_state == MarketClarityState.KNOWN_FAVORABLE:
                        f_mult = 0.85 if (self.calibration_mode == "CALIBRATED" and candidate_destination_r >= 4.5) else 0.50
                        risk_multiplier *= f_mult
                        checks.append(DefenseLayerCheck("POSITIONING_DYNAMICS", True, f_mult, target_r_floor, f"Overheated funding: {f_mult:.2f}x sizing in strong trend."))
                    else:
                        blockers.append("POSITIONING_DYNAMICS: Overheated funding in transitional/ranging market.")
                        checks.append(DefenseLayerCheck("POSITIONING_DYNAMICS", False, 0.0, target_r_floor, "Overheated funding flush hazard."))
                else:
                    checks.append(DefenseLayerCheck("POSITIONING_DYNAMICS", True, 1.0, target_r_floor, "Positioning normal for long."))
            elif direction == -1:  # Looking for Short
                if funding_state_val == FundingState.EXTREME_NEGATIVE:
                    blockers.append("POSITIONING_DYNAMICS: Crowded shorts face violent squeeze hazard.")
                    checks.append(DefenseLayerCheck("POSITIONING_DYNAMICS", False, 0.0, target_r_floor, "Crowded short squeeze hazard."))
                else:
                    checks.append(DefenseLayerCheck("POSITIONING_DYNAMICS", True, 1.0, target_r_floor, "Positioning normal for short."))
        else:
            checks.append(DefenseLayerCheck("POSITIONING_DYNAMICS", True, 1.0, target_r_floor, "Positioning disabled."))

        # -------------------------------------------------------------
        # MINIMUM DESTINATION FLOOR CHECK
        # -------------------------------------------------------------
        if candidate_destination_r < target_r_floor:
            blockers.append(f"DESTINATION_FLOOR: Target {candidate_destination_r:.2f}R below mandatory {target_r_floor:.1f}R floor.")

        # -------------------------------------------------------------
        # REACTIVATION & RECOVERY STAGE ENGINE (POST-CRISIS PACING)
        # -------------------------------------------------------------
        if self.reactivation_engine is not None:
            ts = timestamp_ms or getattr(mtf_state, "timestamp_ms", 0)
            react_audit = self.reactivation_engine.evaluate_reactivation_status(
                symbol=symbol,
                timestamp_ms=ts,
                htf_state=htf_state,
                mtf_state=mtf_state,
                ltf_state=ltf_state,
                direction=direction,
                regime=regime,
                positioning=positioning,
                quote_spread_bps=quote_spread_bps,
                vix_level=vix_level,
            )
            if react_audit.approved_risk_factor <= 0.0:
                blockers.append(f"REACTIVATION_RECOVERY: {react_audit.reason}")
                checks.append(DefenseLayerCheck("REACTIVATION_RECOVERY", False, 0.0, target_r_floor, react_audit.reason))
            else:
                risk_multiplier *= react_audit.approved_risk_factor
                checks.append(DefenseLayerCheck("REACTIVATION_RECOVERY", True, react_audit.approved_risk_factor, target_r_floor, react_audit.reason))

        # -------------------------------------------------------------
        # LAYER 3: CORRELATION GOVERNOR
        # -------------------------------------------------------------
        if self.enable_layer_3:
            if symbol != "BTCUSDT" and self.portfolio_governor.is_correlated_with_active("BTCUSDT", symbol, threshold=0.75):
                risk_multiplier *= 0.50
                checks.append(DefenseLayerCheck("LAYER_3_CORRELATION", True, 0.50, target_r_floor, "50% Haircut: Highly correlated with active BTC exposure."))
            else:
                checks.append(DefenseLayerCheck("LAYER_3_CORRELATION", True, 1.0, target_r_floor, "Correlation within safe thresholds."))
        else:
            checks.append(DefenseLayerCheck("LAYER_3_CORRELATION", True, 1.0, target_r_floor, "Layer 3 disabled."))

        # -------------------------------------------------------------
        # LAYER 2 & LAYER 1: PORTFOLIO HEAT & TRADE RISK CEILING
        # -------------------------------------------------------------
        if self.enable_layer_2:
            remaining_portfolio_heat = max(0.0, self.max_portfolio_heat_pct - current_active_portfolio_risk_pct)
            if remaining_portfolio_heat <= 0.001:
                blockers.append(f"LAYER_2_PORTFOLIO_HEAT: Capacity exhausted ({current_active_portfolio_risk_pct*100:.1f}% >= {self.max_portfolio_heat_pct*100:.1f}%).")
        else:
            remaining_portfolio_heat = 1.0

        # Determine Final Risk Allocation
        if blockers:
            action = RiskAction.CIRCUIT_BREAKER_HALT if dd_status.is_halted else RiskAction.NO_TRADE_FLAT
            return SystemRiskVerdict(
                is_trade_allowed=False,
                risk_action=action,
                approved_risk_pct=0.0,
                destination_r_floor=target_r_floor,
                clarity_state=clarity.clarity_state,
                drawdown_tier=dd_status.tier,
                current_drawdown_pct=dd_status.current_drawdown_pct,
                active_blockers=blockers,
                layer_audits=checks,
                primary_reason=blockers[0],
            )

        # Calculate approved trade risk (Layer 1 enforcement)
        max_trade_cap = self.max_trade_risk_pct if self.enable_layer_1 else 1.0
        calculated_risk = min(proposed_base_risk_pct * risk_multiplier, max_trade_cap)
        approved_risk = min(calculated_risk, remaining_portfolio_heat)
        approved_risk = round(approved_risk, 4)

        if approved_risk < 0.0020: # < 20 bps is not worth transaction friction
            return SystemRiskVerdict(
                is_trade_allowed=False,
                risk_action=RiskAction.NO_TRADE_FLAT,
                approved_risk_pct=0.0,
                destination_r_floor=target_r_floor,
                clarity_state=clarity.clarity_state,
                drawdown_tier=dd_status.tier,
                current_drawdown_pct=dd_status.current_drawdown_pct,
                active_blockers=["Allocated risk below economic friction threshold (0.20%)"],
                layer_audits=checks,
                primary_reason="Risk allocation below economic viability threshold.",
            )

        action = RiskAction.TRADE_FULL if approved_risk >= proposed_base_risk_pct else RiskAction.TRADE_REDUCED

        return SystemRiskVerdict(
            is_trade_allowed=True,
            risk_action=action,
            approved_risk_pct=approved_risk,
            destination_r_floor=target_r_floor,
            clarity_state=clarity.clarity_state,
            drawdown_tier=dd_status.tier,
            current_drawdown_pct=dd_status.current_drawdown_pct,
            active_blockers=[],
            layer_audits=checks,
            primary_reason="Full 7-Layer Risk Defense clearance approved.",
        )
