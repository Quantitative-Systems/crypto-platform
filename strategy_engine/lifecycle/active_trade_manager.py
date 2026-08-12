from typing import Dict, List
from strategy_engine.contracts.trade_plan import TradePlanPayload
from strategy_engine.contracts.strategy_state import PositionState
from strategy_engine.contracts.trade_plan import DirectionalPermission
from market_intelligence.primitives import MarketStatePayload

class ActiveTradeManager:
    """
    Manages active positions, updating their MTF trailing stops and detecting exit conditions.
    """
    def __init__(self):
        self.active_trades: Dict[str, TradePlanPayload] = {}
        
    def register_trade(self, trade_id: str, plan: TradePlanPayload):
        plan.position_status = PositionState.ACTIVE_POSITION.value
        self.active_trades[trade_id] = plan
        
    def evaluate(self, htf_payload: MarketStatePayload, mtf_payload: MarketStatePayload, ltf_payload: MarketStatePayload) -> List[TradePlanPayload]:
        exited_trades = []
        
        for trade_id, plan in list(self.active_trades.items()):
            is_long = plan.directional_permission == DirectionalPermission.PERMIT_LONG.value
            
            # 1. Check HTF Target (Structural Target)
            if is_long and htf_payload.current_price >= plan.target_price:
                plan.position_status = PositionState.TP_EXIT.value
                plan.exit_timestamp = htf_payload.timestamp
                exited_trades.append(plan)
                del self.active_trades[trade_id]
                continue
            elif not is_long and htf_payload.current_price <= plan.target_price:
                plan.position_status = PositionState.TP_EXIT.value
                plan.exit_timestamp = htf_payload.timestamp
                exited_trades.append(plan)
                del self.active_trades[trade_id]
                continue
                
            # 2. Check MTF Structural Trailing
            # If MTF structure prints a CHOCH against the trade bias, exit.
            mtf_events = mtf_payload.structure_state.events
            if mtf_events:
                last_event = mtf_events[-1]
                if "CHOCH" in str(last_event.event_type):
                    event_is_bullish = "BULLISH" in str(last_event.direction)
                    if (is_long and not event_is_bullish) or (not is_long and event_is_bullish):
                        plan.position_status = PositionState.MTF_TRAIL_EXIT.value
                        plan.exit_timestamp = mtf_payload.timestamp
                        exited_trades.append(plan)
                        del self.active_trades[trade_id]
                        continue
                        
            # 3. Check LTF Initial SL
            if is_long and ltf_payload.current_price <= plan.stop_invalidation_price:
                plan.position_status = PositionState.LTF_SL_EXIT.value
                plan.exit_timestamp = ltf_payload.timestamp
                exited_trades.append(plan)
                del self.active_trades[trade_id]
                continue
            elif not is_long and ltf_payload.current_price >= plan.stop_invalidation_price:
                plan.position_status = PositionState.LTF_SL_EXIT.value
                plan.exit_timestamp = ltf_payload.timestamp
                exited_trades.append(plan)
                del self.active_trades[trade_id]
                continue
                
        return exited_trades
