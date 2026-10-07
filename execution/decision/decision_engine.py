"""Autonomous Decision Engine & Deterministic NO-TRADE Reason Taxonomy.

Implements the deterministic state machine for 24/7 autonomous decisions:
OBSERVE
   ↓
CHECK INSTRUMENT ELIGIBILITY (Invariant: Base must be CRYPTO)
   ↓
CHECK DATA HEALTH (Feeds, Latency, Clocks, Spreads)
   ↓
CHECK SYSTEMIC RISK & DRAWDOWN GOVERNOR
   ↓
CHECK UNKNOWN STATE & REACTIVATION
   ↓
CHECK MACRO EVENT WINDOW (Freeze Pre/Post High Impact Prints)
   ↓
CHECK REGIME (Unfavorable Regimes Blocked)
   ↓
CHECK HTF BIAS (Bias & Key Zones)
   ↓
CHECK MARKET MODEL PHASE (Pullback vs Continuation)
   ↓
CHECK MTF SETUP (Setup Validation & Structural Trail Target)
   ↓
CHECK LTF ENTRY (Entry Trigger & Initial Structural Stop)
   ↓
CHECK HTF DESTINATION (Must be >= 4.0R)
   ↓
CHECK PORTFOLIO FACTOR ENGINE (Crypto Beta, USD, Gold, Heat <= 3%)
   ↓
CALCULATE POSITION SIZE
   ↓
DECISION: TRADE / NO_TRADE
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from instrument.asset_class import AssetClass
from instrument.instrument_contract import CryptoBaseInstrument
from instrument.instrument_health import InstrumentHealth
from execution.portfolio.factor_engine import PortfolioFactorEngine


class NoTradeReason(str, Enum):
    """Exhaustive institutional taxonomy for rejected opportunities."""
    NO_TRADE_INELIGIBLE_INSTRUMENT = "NO_TRADE_INELIGIBLE_INSTRUMENT"
    NO_TRADE_DATA_UNHEALTHY = "NO_TRADE_DATA_UNHEALTHY"
    NO_TRADE_INSTRUMENT_HEALTH = "NO_TRADE_INSTRUMENT_HEALTH"
    NO_TRADE_UNKNOWN_STATE = "NO_TRADE_UNKNOWN_STATE"
    NO_TRADE_DRAWDOWN_GOVERNOR = "NO_TRADE_DRAWDOWN_GOVERNOR"
    NO_TRADE_REACTIVATION = "NO_TRADE_REACTIVATION"
    NO_TRADE_EVENT_FREEZE = "NO_TRADE_EVENT_FREEZE"
    NO_TRADE_SPREAD_TOO_HIGH = "NO_TRADE_SPREAD_TOO_HIGH"
    NO_TRADE_LIQUIDITY_TOO_LOW = "NO_TRADE_LIQUIDITY_TOO_LOW"
    NO_TRADE_REGIME_UNFAVORABLE = "NO_TRADE_REGIME_UNFAVORABLE"
    NO_TRADE_HTF_UNCLEAR = "NO_TRADE_HTF_UNCLEAR"
    NO_TRADE_PHASE_INVALID = "NO_TRADE_PHASE_INVALID"
    NO_TRADE_MTF_NOT_CONFIRMED = "NO_TRADE_MTF_NOT_CONFIRMED"
    NO_TRADE_LTF_NOT_CONFIRMED = "NO_TRADE_LTF_NOT_CONFIRMED"
    NO_TRADE_DESTINATION_LT_4R = "NO_TRADE_DESTINATION_LT_4R"
    NO_TRADE_PORTFOLIO_HEAT = "NO_TRADE_PORTFOLIO_HEAT"
    NO_TRADE_CORRELATION = "NO_TRADE_CORRELATION"


@dataclass
class AutonomousDecisionOutcome:
    """Full decision audit card produced every decision cycle."""
    decision_id: str
    timestamp: float
    instrument: str
    decision: str                         # "TRADE" or "NO_TRADE"
    primary_reason: str
    no_trade_code: Optional[NoTradeReason] = None
    direction: Optional[str] = None       # "LONG", "SHORT", or None
    market_model: Dict[str, Any] = field(default_factory=dict)
    htf: str = ""
    mtf: str = ""
    ltf: str = ""
    regime: str = ""
    causal_context: str = ""
    strategy: str = ""
    destination_r: float = 0.0
    risk_approved: float = 0.0            # e.g. 0.01 = 1.0%
    position_size: float = 0.0            # Base asset units
    entry_price: Optional[float] = None
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    system_version: str = "CandidateV1"
    data_snapshot: Dict[str, Any] = field(default_factory=dict)
    feature_version: str = "v1.2.0"
    execution_version: str = "v1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to institutional structured JSON schema."""
        d: Dict[str, Any] = {
            "decision_id": self.decision_id,
            "timestamp": self.timestamp,
            "instrument": self.instrument,
            "decision": self.decision,
            "reason": self.primary_reason,
            "system_version": self.system_version,
            "feature_version": self.feature_version,
            "execution_version": self.execution_version,
        }
        if self.no_trade_code:
            d["no_trade_code"] = self.no_trade_code.value
            d["primary_reason"] = self.no_trade_code.value

        if self.decision == "TRADE":
            d.update({
                "direction": self.direction,
                "market_model": self.market_model,
                "htf": self.htf,
                "mtf": self.mtf,
                "ltf": self.ltf,
                "regime": self.regime,
                "causal_context": self.causal_context,
                "strategy": self.strategy,
                "destination_r": self.destination_r,
                "risk_approved": self.risk_approved,
                "position_size": self.position_size,
                "entry_price": self.entry_price,
                "stop_price": self.stop_price,
                "target_price": self.target_price,
                "data_snapshot": self.data_snapshot,
            })
        return d


class AutonomousDecisionEngine:
    """Deterministic, auditable decision engine implementing candidate V1 gates."""

    def __init__(self, factor_engine: Optional[PortfolioFactorEngine] = None):
        self.factor_engine = factor_engine or PortfolioFactorEngine()

    def evaluate_cycle(
        self,
        instrument: CryptoBaseInstrument,
        health: InstrumentHealth,
        market_model_state: Dict[str, Any],
        environment_state: Dict[str, Any],
        governor_state: Dict[str, Any],
        active_positions: List[Tuple[CryptoBaseInstrument, int, float]],
        account_equity_usd: float = 100_000.0,
        current_time: Optional[float] = None,
    ) -> AutonomousDecisionOutcome:
        """Run all deterministic gates in strict sequence."""
        now = current_time if current_time is not None else time.time()
        dec_id = f"DEC-{uuid.uuid4().hex[:10].upper()}"

        # Helper to construct rejection card
        def reject(code: NoTradeReason, explanation: str) -> AutonomousDecisionOutcome:
            return AutonomousDecisionOutcome(
                decision_id=dec_id,
                timestamp=now,
                instrument=instrument.symbol,
                decision="NO_TRADE",
                primary_reason=explanation,
                no_trade_code=code,
                market_model={
                    "structure": market_model_state.get("structure", "UNKNOWN"),
                    "zone": market_model_state.get("zone", "UNKNOWN"),
                    "phase": market_model_state.get("phase", "UNKNOWN"),
                },
                htf=market_model_state.get("htf_bias", "UNKNOWN"),
                mtf=market_model_state.get("mtf_setup", "UNKNOWN"),
                ltf=market_model_state.get("ltf_entry", "UNKNOWN"),
                regime=environment_state.get("regime", "UNKNOWN"),
                causal_context=environment_state.get("macro_state", "UNKNOWN"),
                strategy=market_model_state.get("strategy", "ADAPTIVE_ENGINE_V1"),
                destination_r=float(market_model_state.get("destination_r", 0.0)),
            )

        # 1. Gate: Instrument Eligibility Invariant
        if not instrument.engine_eligible or instrument.base_class != AssetClass.CRYPTO:
            return reject(
                NoTradeReason.NO_TRADE_INELIGIBLE_INSTRUMENT,
                f"Instrument {instrument.symbol} base leg is {instrument.base_class.value}, not CRYPTO"
            )

        # 2. Gate: Data Health
        health_status = health.evaluate(now)
        if not health.is_operational():
            return reject(
                NoTradeReason.NO_TRADE_DATA_UNHEALTHY,
                f"Data health failed: {health_status.value} ({', '.join(health.active_issues)})"
            )

        # 3. Gate: Unknown State Engine
        if governor_state.get("unknown_state_active", False):
            return reject(
                NoTradeReason.NO_TRADE_UNKNOWN_STATE,
                f"Unknown State Governor active: {governor_state.get('unknown_state_reason', 'DATA_CORRUPTION_OR_ANOMALY')}"
            )

        # 4. Gate: Drawdown Governor
        if governor_state.get("drawdown_circuit_breaker", False):
            return reject(
                NoTradeReason.NO_TRADE_DRAWDOWN_GOVERNOR,
                f"Drawdown Circuit Breaker active (Current DD {governor_state.get('current_drawdown_pct', 0.0):.2f}%)"
            )

        # 5. Gate: Staged Reactivation Pacing
        reactivation_mult = float(governor_state.get("reactivation_multiplier", 1.0))
        if reactivation_mult <= 0.0:
            return reject(
                NoTradeReason.NO_TRADE_REACTIVATION,
                "Staged Reactivation pacing set allocation to 0.0x during crisis cooloff"
            )

        # 6. Gate: Event Risk Freeze Window
        if environment_state.get("in_event_window", False):
            return reject(
                NoTradeReason.NO_TRADE_EVENT_FREEZE,
                f"Macro event window active: {environment_state.get('event_name', 'HIGH_IMPACT_EVENT')}"
            )

        # 7. Gate: Microstructure Spread & Liquidity
        observed_spread_bps = float(market_model_state.get("spread_bps", 3.0))
        is_liq, liq_msg = instrument.liquidity_profile.is_currently_liquid(observed_spread_bps)
        if not is_liq:
            if observed_spread_bps > instrument.liquidity_profile.max_tolerated_spread_bps:
                return reject(NoTradeReason.NO_TRADE_SPREAD_TOO_HIGH, liq_msg)
            return reject(NoTradeReason.NO_TRADE_LIQUIDITY_TOO_LOW, liq_msg)

        # 8. Gate: Macro / Volatility Regime
        regime = str(environment_state.get("regime", "EXPANSION_STABLE")).upper()
        if regime in ("CRISIS_TURMOIL", "VOLATILITY_EXPLOSION", "HIGH_VOLATILITY_CHOP"):
            return reject(
                NoTradeReason.NO_TRADE_REGIME_UNFAVORABLE,
                f"Regime {regime} unfavorable for directional trend-continuation"
            )

        # 9. Gate: HTF Directional Bias
        htf_bias = str(market_model_state.get("htf_bias", "NEUTRAL")).upper()
        if htf_bias not in ("BULLISH", "BEARISH"):
            return reject(
                NoTradeReason.NO_TRADE_HTF_UNCLEAR,
                f"HTF directional bias is {htf_bias}; requires distinct BULLISH or BEARISH bias"
            )

        direction = 1 if htf_bias == "BULLISH" else -1
        direction_str = "LONG" if direction == 1 else "SHORT"

        # 10. Gate: Market Model Phase (Must be Pullback or Continuation)
        phase = str(market_model_state.get("phase", "UNKNOWN")).upper()
        if phase not in ("PULLBACK", "CONTINUATION"):
            return reject(
                NoTradeReason.NO_TRADE_PHASE_INVALID,
                f"Market Model phase is {phase}; only PULLBACK and CONTINUATION are tradable"
            )

        # 11. Gate: MTF Setup Confirmation
        mtf_valid = bool(market_model_state.get("mtf_valid", False))
        if not mtf_valid:
            return reject(
                NoTradeReason.NO_TRADE_MTF_NOT_CONFIRMED,
                f"MTF structural setup not validated: {market_model_state.get('mtf_reason', 'SETUP_CRITERIA_UNMET')}"
            )

        # 12. Gate: LTF Entry Confirmation
        ltf_valid = bool(market_model_state.get("ltf_valid", False))
        if not ltf_valid:
            return reject(
                NoTradeReason.NO_TRADE_LTF_NOT_CONFIRMED,
                f"LTF entry trigger not confirmed: {market_model_state.get('ltf_reason', 'NO_TRIGGER')}"
            )

        # 13. Gate: HTF Destination Target >= 4.0R
        dest_r = float(market_model_state.get("destination_r", 0.0))
        if dest_r < 4.0:
            return reject(
                NoTradeReason.NO_TRADE_DESTINATION_LT_4R,
                f"HTF destination {dest_r:.2f}R is below the mandatory 4.0R floor"
            )

        # 14. Gate: Portfolio Factor Risk & Capital Approval
        base_requested_risk = 0.01 * reactivation_mult  # 1.0% scaled by reactivation pacing
        approved, final_risk, factor_reason = self.factor_engine.evaluate_capital_approval(
            instrument=instrument,
            direction=direction,
            requested_risk_pct=base_requested_risk,
            active_positions=active_positions,
        )

        if not approved:
            if "PORTFOLIO_HEAT" in factor_reason:
                return reject(NoTradeReason.NO_TRADE_PORTFOLIO_HEAT, factor_reason)
            return reject(NoTradeReason.NO_TRADE_CORRELATION, factor_reason)

        # 15. Sizing Calculation
        entry_price = float(market_model_state.get("entry_price", 0.0))
        stop_price = float(market_model_state.get("stop_price", 0.0))
        target_price = float(market_model_state.get("target_price", 0.0))

        risk_distance = abs(entry_price - stop_price)
        if risk_distance <= 0:
            return reject(NoTradeReason.NO_TRADE_LTF_NOT_CONFIRMED, "Stop distance is zero")

        dollar_risk = account_equity_usd * final_risk
        raw_units = dollar_risk / risk_distance
        pos_size = instrument.trading_constraints.round_qty(raw_units)

        # Final TRADE Decision
        return AutonomousDecisionOutcome(
            decision_id=dec_id,
            timestamp=now,
            instrument=instrument.symbol,
            decision="TRADE",
            primary_reason=f"HTF {htf_bias} {phase}, MTF setup valid, LTF confirmed, Destination {dest_r:.1f}R >= 4.0R, Capital approved",
            no_trade_code=None,
            direction=direction_str,
            market_model={
                "structure": market_model_state.get("structure", "BULLISH_TREND"),
                "zone": market_model_state.get("zone", "HTF_SUPPORT_DEMAND"),
                "phase": phase,
            },
            htf=htf_bias,
            mtf="CONFIRMED_STRUCTURAL_SETUP",
            ltf="CONFIRMED_BREAKOUT_AND_RETEST",
            regime=regime,
            causal_context=environment_state.get("macro_state", "EXPANSION"),
            strategy=market_model_state.get("strategy", "ADAPTIVE_ENGINE_V1"),
            destination_r=round(dest_r, 2),
            risk_approved=round(final_risk, 4),
            position_size=pos_size,
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            data_snapshot={
                "spread_bps": observed_spread_bps,
                "latency_ms": health.feed_latency_ms,
            },
        )
