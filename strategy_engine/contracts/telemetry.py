from typing import Dict, Any, Optional
from strategy_engine.contracts.trade_plan import TradePlanPayload, DirectionalPermission
from strategy_engine.contracts.strategy_state import CandidateState

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
        structural_provenance: Optional[Dict[str, str]] = None,
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
