from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
from strategy_engine.contracts.trade_plan import TradePlanPayload, DirectionalPermission
from strategy_engine.contracts.strategy_state import CandidateState


@dataclass
class HTFTimeline:
    structure: str = ""
    bias: str = ""
    strong_swing: Dict[str, Any] = field(default_factory=dict)
    weak_swing: Dict[str, Any] = field(default_factory=dict)
    keyzone: Dict[str, Any] = field(default_factory=dict)
    phase: str = ""
    interaction_timestamp: int = 0


@dataclass
class MTFTimeline:
    initial_structure: str = ""
    countertrend_duration_bars: int = 0
    alignment_event: str = ""
    alignment_timestamp: int = 0
    new_structure: str = ""
    new_keyzone: Dict[str, Any] = field(default_factory=dict)
    pullback_detected: bool = False
    retest_timestamp: int = 0
    retest_depth_pct: float = 0.0


@dataclass
class LTFTimeline:
    structure: str = ""
    liquidity_event: str = ""
    sweep_timestamp: int = 0
    displacement_magnitude_pct: float = 0.0
    displacement_candle_close: float = 0.0
    structural_invalidation_pivot: float = 0.0


@dataclass
class TradeTimeline:
    entry_timestamp: int = 0
    entry_price: float = 0.0
    initial_structural_sl: float = 0.0
    htf_target: float = 0.0
    initial_risk_distance: float = 0.0
    target_distance: float = 0.0
    planned_rr: float = 0.0
    risk_pct: float = 0.01
    position_units: float = 0.0
    mfe_price: float = 0.0
    mfe_r: float = 0.0
    mae_price: float = 0.0
    mae_r: float = 0.0
    mtf_trail_events: List[Dict[str, Any]] = field(default_factory=list)
    exit_timestamp: int = 0
    exit_price: float = 0.0
    exit_reason: str = ""
    realized_r: float = 0.0


@dataclass
class TradeTimelineTelemetry:
    candidate_id: str
    symbol: str
    timeframe_set: str = ""
    htf_timeline: HTFTimeline = field(default_factory=HTFTimeline)
    mtf_timeline: MTFTimeline = field(default_factory=MTFTimeline)
    ltf_timeline: LTFTimeline = field(default_factory=LTFTimeline)
    trade_timeline: TradeTimeline = field(default_factory=TradeTimeline)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TelemetryHelper:
    """
    Helps safely construct TradePlanPayload objects to ensure full telemetry preservation.
    """
    
    @staticmethod
    def reject(
        trade_plan_id: str,
        hypothesis_id: str,
        symbol: str,
        directional_permission: DirectionalPermission,
        setup_timestamp: int,
        rejection_reason: str,
        entry_price: float = 0.0,
        stop_invalidation_price: float = 0.0,
        target_price: float = 0.0,
        raw_rr: float = 0.0,
        structural_provenance: Optional[Dict[str, Any]] = None,
        source_timeframes: Optional[Dict[str, str]] = None
    ) -> TradePlanPayload:
        return TradePlanPayload(
            trade_plan_id=trade_plan_id,
            hypothesis_id=hypothesis_id,
            symbol=symbol,
            directional_permission=directional_permission.value,
            setup_timestamp=setup_timestamp,
            entry_price=entry_price,
            stop_invalidation_price=stop_invalidation_price,
            target_price=target_price,
            raw_rr=raw_rr,
            status=CandidateState.REJECTED.value,
            rejection_reason=rejection_reason,
            structural_provenance=structural_provenance or {},
            source_timeframes=source_timeframes or {}
        )
