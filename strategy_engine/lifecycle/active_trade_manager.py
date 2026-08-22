from typing import Dict, List
from strategy_engine.contracts.trade_plan import TradePlanPayload
from strategy_engine.contracts.strategy_state import PositionState
from strategy_engine.contracts.trade_plan import DirectionalPermission
from market_intelligence.primitives import MarketStatePayload

class ActiveTradeManager:
    """
    Manages active positions, updating their MTF trailing stops, profit-lock ratchets, and detecting exit conditions.
    """
    def __init__(
        self,
        enable_mtf_trailing: bool = True,
        enable_profit_lock: bool = False,
        lockin_r: float = 1.0,
        giveback_r: float = 0.75
    ):
        self.active_trades: Dict[str, TradePlanPayload] = {}
        self.enable_mtf_trailing = enable_mtf_trailing
        self.enable_profit_lock = enable_profit_lock
        self.lockin_r = lockin_r
        self.giveback_r = giveback_r
        
    def register_trade(self, trade_id: str, plan: TradePlanPayload):
        plan.position_status = PositionState.ACTIVE_POSITION.value
        if not hasattr(plan, 'metadata') or plan.metadata is None:
            plan.metadata = {}
        plan.metadata["initial_sl"] = plan.stop_invalidation_price
        plan.metadata["max_favorable_price"] = plan.entry_price
        self.active_trades[trade_id] = plan
        
    def evaluate(self, htf_payload: MarketStatePayload, mtf_payload: MarketStatePayload, ltf_payload: MarketStatePayload) -> List[TradePlanPayload]:
        exited_trades = []
        
        for trade_id, plan in list(self.active_trades.items()):
            is_long = plan.directional_permission == DirectionalPermission.PERMIT_LONG.value
            entry_price = plan.entry_price
            initial_sl = (plan.metadata.get("initial_sl") if hasattr(plan, 'metadata') and plan.metadata else None) or plan.stop_invalidation_price
            entry_risk_dist = abs(entry_price - initial_sl) or 1.0
            
            # Update MFE tracking on current candle
            cur_high = getattr(ltf_payload.current_candle, 'high', ltf_payload.current_price) if ltf_payload.current_candle else ltf_payload.current_price
            cur_low = getattr(ltf_payload.current_candle, 'low', ltf_payload.current_price) if ltf_payload.current_candle else ltf_payload.current_price
            
            if hasattr(plan, 'metadata') and plan.metadata is not None:
                if is_long:
                    plan.metadata["max_favorable_price"] = max(plan.metadata.get("max_favorable_price", entry_price), cur_high)
                else:
                    plan.metadata["max_favorable_price"] = min(plan.metadata.get("max_favorable_price", entry_price), cur_low)
            
            # 1. Check HTF Target (Structural Target)
            if is_long and cur_high >= plan.target_price:
                plan.position_status = PositionState.TP_EXIT.value
                plan.exit_timestamp = ltf_payload.timestamp
                exited_trades.append(plan)
                del self.active_trades[trade_id]
                continue
            elif not is_long and cur_low <= plan.target_price:
                plan.position_status = PositionState.TP_EXIT.value
                plan.exit_timestamp = ltf_payload.timestamp
                exited_trades.append(plan)
                del self.active_trades[trade_id]
                continue
                
            # 2. Profit-Lock Ratchet (+1.0R Excursion Protection)
            if self.enable_profit_lock and hasattr(plan, 'metadata') and plan.metadata is not None:
                max_fav = plan.metadata.get("max_favorable_price", entry_price)
                if is_long:
                    fav_r = (max_fav - entry_price) / entry_risk_dist
                    if fav_r >= self.lockin_r:
                        floor_stop = max_fav - (self.giveback_r * entry_risk_dist)
                        if floor_stop > plan.stop_invalidation_price:
                            plan.stop_invalidation_price = floor_stop
                else:
                    fav_r = (entry_price - max_fav) / entry_risk_dist
                    if fav_r >= self.lockin_r:
                        floor_stop = max_fav + (self.giveback_r * entry_risk_dist)
                        if floor_stop < plan.stop_invalidation_price:
                            plan.stop_invalidation_price = floor_stop

            # 3. Update MTF Structural Trailing Stop (Ratcheting behind MTF Protected Swings)
            if self.enable_mtf_trailing:
                try:
                    if is_long:
                        mtf_prot_low = mtf_payload.structure_state.protected_low.raw_swing.price
                        # Stop can only ratchet upward, never widen
                        if mtf_prot_low > plan.stop_invalidation_price:
                            plan.stop_invalidation_price = mtf_prot_low
                    else:
                        mtf_prot_high = mtf_payload.structure_state.protected_high.raw_swing.price
                        # Stop can only ratchet downward, never widen
                        if mtf_prot_high < plan.stop_invalidation_price:
                            plan.stop_invalidation_price = mtf_prot_high
                except AttributeError:
                    pass  # No protected swing established yet

                # 4. Check MTF Structural Reversal (Adverse CHOCH Exit)
                mtf_events = getattr(mtf_payload.structure_state, 'events', None) or mtf_payload.events
                if mtf_events:
                    last_event = mtf_events[-1]
                    event_ts = getattr(last_event, 'timestamp', 0)
                    
                    # Causal Filter: only exit if the adverse event occurred after our setup began unfolding
                    if event_ts > getattr(plan, 'setup_timestamp', 0):
                        if "CHOCH" in str(last_event.event_type):
                            event_is_bullish = "BULLISH" in str(last_event.direction)
                            if (is_long and not event_is_bullish) or (not is_long and event_is_bullish):
                                plan.position_status = PositionState.MTF_TRAIL_EXIT.value
                                plan.exit_timestamp = mtf_payload.timestamp
                                exited_trades.append(plan)
                                del self.active_trades[trade_id]
                                continue
                        
            # 5. Check LTF / Trailed SL Trigger
            if is_long and cur_low <= plan.stop_invalidation_price:
                plan.position_status = PositionState.LTF_SL_EXIT.value
                plan.exit_timestamp = ltf_payload.timestamp
                exited_trades.append(plan)
                del self.active_trades[trade_id]
                continue
            elif not is_long and cur_high >= plan.stop_invalidation_price:
                plan.position_status = PositionState.LTF_SL_EXIT.value
                plan.exit_timestamp = ltf_payload.timestamp
                exited_trades.append(plan)
                del self.active_trades[trade_id]
                continue
                
        return exited_trades
