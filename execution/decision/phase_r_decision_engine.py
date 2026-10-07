"""Phase R — Unified Deterministic Decision Engine & Target Geometry Validator.

Orchestrates the complete causal decision pipeline for closed candles:
DATA VALIDATION
   ↓
7-TIMEFRAME FRACTAL STATE
   ↓
CROSS-SET COHERENCE & ALIGNMENT
   ↓
CONFIDENCE SCORE EVALUATION (Frozen Q.2 Weights: 0.35 + 0.25 + 0.20 + 0.15 + 0.05)
   ↓
TARGET GEOMETRY VERIFICATION (Hard Invariants & >= 4.0R Destination Floor)
   ↓
SET CAPITAL POLICY (Sets 1 & 5 at $0.00; Sets 2-4 Shadow-Paper Eligible)
   ↓
FROZEN RISK GOVERNOR (Trade Risk <= 1%, Asset Heat <= 1%, Portfolio Heat <= 3%)
   ↓
DECISION CARD & AUDIT LEDGER LOGGING
"""
from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from market_data.realtime.binance_ws_client import DataHealthStatus
from market_model.contracts import MarketState, TrendDirection
from market_model.fractal_state_engine import (
    CrossSetCoherenceTracker,
    FractalAlignment,
    FractalBias,
    FractalStateEngine,
    TIMEFRAME_SETS,
)
from research.contracts.frozen_contract_guard import FROZEN_GUARD
from research.experiments.mtf_strategy_coordinator import MTFStrategyCoordinator


class DecisionType(str, Enum):
    TRADE = "TRADE"
    NO_TRADE = "NO_TRADE"


class PhaseRNoTradeReason(str, Enum):
    DATA_UNHEALTHY = "DATA_UNHEALTHY"
    DATA_STALE = "DATA_STALE"
    SET_1_MACRO_ANCHOR = "SET_1_MACRO_ANCHOR_ZERO_CAPITAL"
    SET_5_MICRO_CONFIRMATION = "SET_5_MICRO_CONFIRMATION_ZERO_CAPITAL"
    CONFIDENCE_BELOW_THRESHOLD = "CONFIDENCE_BELOW_THRESHOLD"
    INVALID_TARGET_GEOMETRY = "INVALID_TARGET_GEOMETRY"
    TARGET_BELOW_4R = "TARGET_BELOW_4R"
    MAX_TRADE_RISK_EXCEEDED = "MAX_TRADE_RISK_EXCEEDED"
    MAX_ASSET_EXPOSURE_EXCEEDED = "MAX_ASSET_EXPOSURE_EXCEEDED"
    MAX_PORTFOLIO_HEAT_EXCEEDED = "MAX_PORTFOLIO_HEAT_EXCEEDED"
    DRAWDOWN_GOVERNOR_HALT = "DRAWDOWN_GOVERNOR_HALT"
    CORRELATION_LIMIT = "CORRELATION_LIMIT"
    UNKNOWN_STATE = "UNKNOWN_STATE"
    NO_STRUCTURAL_SETUP = "NO_STRUCTURAL_SETUP"
    CROSS_SET_EVENT_DUPLICATION = "CROSS_SET_EVENT_DUPLICATION"


@dataclass
class PhaseRDecisionRecord:
    decision_id: str
    lineage_id: str
    event_id: str
    timestamp_ms: int
    asset: str
    timeframe_set: str
    phase: str
    decision: DecisionType
    reason_codes: List[str]
    confidence_score: float
    confidence_components: Dict[str, float]
    fractal_alignment: str
    fractal_bias: str
    direction: int
    entry_price: float
    initial_stop_price: float
    target_price: float
    planned_r: float
    risk_pct: float
    portfolio_heat_pct: float
    governor_passed: bool
    execution_mode: str = "SHADOW_PAPER"
    htf_state_trend: str = "NEUTRAL"
    mtf_state_trend: str = "NEUTRAL"
    ltf_state_trend: str = "NEUTRAL"
    created_at_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["decision"] = self.decision.value
        return d


class PhaseRDecisionEngine:
    """Production decision engine enforcing frozen Q.2 research contracts."""

    def __init__(
        self,
        symbol: str,
        initial_equity_usd: float = 100_000.0,
        min_confidence: float = 0.50,
        min_target_r: float = 4.0,
    ):
        self.symbol = symbol.upper()
        self.equity_usd = initial_equity_usd
        self.min_confidence = min_confidence
        self.min_target_r = min_target_r

        self.fractal_engine = FractalStateEngine(symbol=self.symbol)
        self.coherence_tracker = CrossSetCoherenceTracker()

        # Build coordinators for Sets 1 through 5
        self.coordinators: Dict[str, Dict[str, MTFStrategyCoordinator]] = {}
        for sname, cfg in TIMEFRAME_SETS.items():
            self.coordinators[sname] = {
                "PULLBACK": MTFStrategyCoordinator(
                    timeframe_set_id=sname,
                    htf_label=cfg["htf"],
                    mtf_label=cfg["mtf"],
                    ltf_label=cfg["ltf"],
                    hypothesis_type="PULLBACK",
                    min_target_r=self.min_target_r,
                ),
                "CONTINUATION": MTFStrategyCoordinator(
                    timeframe_set_id=sname,
                    htf_label=cfg["htf"],
                    mtf_label=cfg["mtf"],
                    ltf_label=cfg["ltf"],
                    hypothesis_type="CONTINUATION",
                    min_target_r=self.min_target_r,
                ),
            }

        # Active risk state
        self.active_positions_heat: float = 0.0
        self.active_asset_heat: float = 0.0

    def evaluate_opportunity(
        self,
        set_name: str,
        hypothesis_type: str,
        all_timeframe_data: Dict[str, Dict[str, np.ndarray]],
        data_health: DataHealthStatus = DataHealthStatus.DATA_HEALTHY,
        eval_timestamp_ms: Optional[int] = None,
    ) -> PhaseRDecisionRecord:
        """Evaluates closed candle data causally and emits a deterministic decision card."""
        decision_id = f"DEC_{uuid.uuid4().hex[:10].upper()}"
        ts_now = eval_timestamp_ms or int(time.time() * 1000)
        reasons: List[str] = []

        cfg = TIMEFRAME_SETS[set_name]
        ltf_tf = cfg["ltf"]
        ltf_data = all_timeframe_data.get(ltf_tf)

        # Operational Capital Policy for Set 1 & Set 5
        if set_name == "SET_1":
            reasons.append(PhaseRNoTradeReason.SET_1_MACRO_ANCHOR.value)
        elif set_name == "SET_5":
            reasons.append(PhaseRNoTradeReason.SET_5_MICRO_CONFIRMATION.value)

        # 1. Check Data Health
        if data_health in (DataHealthStatus.DATA_INVALID, DataHealthStatus.DATA_DEGRADED):
            reasons.append(PhaseRNoTradeReason.DATA_UNHEALTHY.value)
            return self._build_no_trade(
                decision_id=decision_id,
                set_name=set_name,
                hypothesis_type=hypothesis_type,
                timestamp_ms=ts_now,
                reasons=reasons,
            )
        if data_health == DataHealthStatus.DATA_STALE:
            reasons.append(PhaseRNoTradeReason.DATA_STALE.value)
            return self._build_no_trade(
                decision_id=decision_id,
                set_name=set_name,
                hypothesis_type=hypothesis_type,
                timestamp_ms=ts_now,
                reasons=reasons,
            )

        if ltf_data is None or len(ltf_data["c"]) < 60:
            reasons.append(PhaseRNoTradeReason.NO_STRUCTURAL_SETUP.value)
            return self._build_no_trade(
                decision_id=decision_id,
                set_name=set_name,
                hypothesis_type=hypothesis_type,
                timestamp_ms=ts_now,
                reasons=reasons,
            )

        # 2. Update fractal state engine
        self.fractal_engine.load_data(all_timeframe_data)
        node = self.fractal_engine.evaluate_at(ts_now)

        # 3. Scan signals from coordinator
        coord = self.coordinators[set_name][hypothesis_type]
        candidates, _ = coord.scan_signals(
            symbol=self.symbol,
            htf_data=all_timeframe_data.get(cfg["htf"], {}),
            mtf_data=all_timeframe_data.get(cfg["mtf"], {}),
            ltf_data=ltf_data,
        )

        if not candidates:
            reasons.append(PhaseRNoTradeReason.NO_STRUCTURAL_SETUP.value)
            return self._build_no_trade(
                decision_id=decision_id,
                set_name=set_name,
                hypothesis_type=hypothesis_type,
                timestamp_ms=ts_now,
                reasons=reasons,
            )

        # Take the most recent causal candidate
        cand = candidates[-1]
        entry_px = float(cand["entry_price"])
        stop_px = float(cand["stop_price"])
        target_px = float(cand["target_price"])
        direction = int(cand["direction"])
        break_type = str(cand.get("meta", {}).get("break_type", "UNKNOWN"))
        cand_ts = int(cand.get("timestamp_ms", ts_now))

        event_id = f"{self.symbol}_{set_name}_{cand_ts}_{break_type}"
        lineage_id = f"LIN_{abs(hash(event_id)) % 100000:05d}"

        # 4. Target Geometry Hard Assertions
        is_geom_valid = False
        if direction == 1:
            is_geom_valid = target_px > entry_px > stop_px
        elif direction == -1:
            is_geom_valid = target_px < entry_px < stop_px

        if not is_geom_valid:
            reasons.append(PhaseRNoTradeReason.INVALID_TARGET_GEOMETRY.value)

        risk_dist = abs(entry_px - stop_px)
        reward_dist = abs(target_px - entry_px)
        planned_r = reward_dist / max(risk_dist, 1e-6)

        if planned_r < self.min_target_r:
            reasons.append(PhaseRNoTradeReason.TARGET_BELOW_4R.value)

        # 5. Evaluate Frozen Confidence System
        hyp = self.fractal_engine.hypothesis_engine.evaluate_hypothesis(node, set_name, hypothesis_type)
        confidence = hyp.confidence_score if hyp else 0.35

        conf_components = {
            "base": 0.35,
            "alignment": 0.25 if node.get_alignment_for_set(set_name) == FractalAlignment.FULLY_ALIGNED else 0.10,
            "location": 0.20 if (hyp and "DISCOUNT" in str(hyp.target_zone or "") or "PREMIUM" in str(hyp.target_zone or "")) else 0.0,
            "macro_htf": 0.15 if node.fractal_bias in (FractalBias.BULLISH, FractalBias.STRONG_BULLISH) and direction == 1 else 0.0,
            "cross_support": 0.05 * min(self.fractal_engine.hypothesis_engine._count_cross_set_support(node, set_name, direction), 2),
        }

        if confidence < self.min_confidence:
            reasons.append(PhaseRNoTradeReason.CONFIDENCE_BELOW_THRESHOLD.value)

        # 6. Set Operational Capital Policy
        if set_name == "SET_1":
            reasons.append(PhaseRNoTradeReason.SET_1_MACRO_ANCHOR.value)
        elif set_name == "SET_5":
            reasons.append(PhaseRNoTradeReason.SET_5_MICRO_CONFIRMATION.value)

        # 7. Deduplication & Risk Governor Evaluation
        is_unique_event = self.coherence_tracker.register_event(ltf_tf, cand_ts, break_type, set_name)
        if not is_unique_event and set_name in ["SET_2", "SET_3", "SET_4"]:
            reasons.append(PhaseRNoTradeReason.CROSS_SET_EVENT_DUPLICATION.value)

        trade_risk_pct = 1.0  # Invariant: <= 1.0%
        if trade_risk_pct > 1.0:
            reasons.append(PhaseRNoTradeReason.MAX_TRADE_RISK_EXCEEDED.value)
        if self.active_asset_heat + trade_risk_pct > 1.0:
            reasons.append(PhaseRNoTradeReason.MAX_ASSET_EXPOSURE_EXCEEDED.value)
        if self.active_positions_heat + trade_risk_pct > 3.0:
            reasons.append(PhaseRNoTradeReason.MAX_PORTFOLIO_HEAT_EXCEEDED.value)

        # Final Decision Resolution
        decision = DecisionType.TRADE if not reasons else DecisionType.NO_TRADE

        # Extract trend names for audit
        htf_st = node.states.get(cfg["htf"])
        mtf_st = node.states.get(cfg["mtf"])
        ltf_st = node.states.get(cfg["ltf"])

        return PhaseRDecisionRecord(
            decision_id=decision_id,
            lineage_id=lineage_id,
            event_id=event_id,
            timestamp_ms=cand_ts,
            asset=self.symbol,
            timeframe_set=set_name,
            phase=hypothesis_type,
            decision=decision,
            reason_codes=reasons,
            confidence_score=round(confidence, 4),
            confidence_components=conf_components,
            fractal_alignment=node.get_alignment_for_set(set_name).value,
            fractal_bias=node.fractal_bias.value,
            direction=direction,
            entry_price=entry_px,
            initial_stop_price=stop_px,
            target_price=target_px,
            planned_r=round(planned_r, 4),
            risk_pct=trade_risk_pct,
            portfolio_heat_pct=self.active_positions_heat,
            governor_passed=(decision == DecisionType.TRADE),
            execution_mode="SHADOW_PAPER",
            htf_state_trend=htf_st.trend.value if htf_st else "NEUTRAL",
            mtf_state_trend=mtf_st.trend.value if mtf_st else "NEUTRAL",
            ltf_state_trend=ltf_st.trend.value if ltf_st else "NEUTRAL",
        )

    def _build_no_trade(
        self,
        decision_id: str,
        set_name: str,
        hypothesis_type: str,
        timestamp_ms: int,
        reasons: List[str],
    ) -> PhaseRDecisionRecord:
        return PhaseRDecisionRecord(
            decision_id=decision_id,
            lineage_id=f"LIN_{abs(hash(decision_id)) % 100000:05d}",
            event_id=f"{self.symbol}_{set_name}_{timestamp_ms}_NO_TRADE",
            timestamp_ms=timestamp_ms,
            asset=self.symbol,
            timeframe_set=set_name,
            phase=hypothesis_type,
            decision=DecisionType.NO_TRADE,
            reason_codes=reasons,
            confidence_score=0.0,
            confidence_components={},
            fractal_alignment="UNKNOWN",
            fractal_bias="NEUTRAL",
            direction=0,
            entry_price=0.0,
            initial_stop_price=0.0,
            target_price=0.0,
            planned_r=0.0,
            risk_pct=0.0,
            portfolio_heat_pct=self.active_positions_heat,
            governor_passed=False,
            execution_mode="SHADOW_PAPER",
        )
