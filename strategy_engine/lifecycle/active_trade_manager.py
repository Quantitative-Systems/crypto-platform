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
        giveback_r: float = 0.75,
        profit_lock_trigger_r: float = 1.0,
        profit_lock_stop_r: float = 0.10,
        enable_breakeven_1r: bool = False,
        breakeven_trigger_r: float = 1.0,
        breakeven_stop_r: float = 0.10
    ):
        self.active_trades: Dict[str, TradePlanPayload] = {}
        self.enable_mtf_trailing = enable_mtf_trailing
        self.enable_profit_lock = enable_profit_lock
        self.lockin_r = lockin_r
        self.giveback_r = giveback_r
        self.profit_lock_trigger_r = profit_lock_trigger_r
        self.profit_lock_stop_r = profit_lock_stop_r
        self.enable_breakeven_1r = enable_breakeven_1r
        self.breakeven_trigger_r = breakeven_trigger_r
        self.breakeven_stop_r = breakeven_stop_r
        
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
                
            # 2. Breakeven 1R Ratchet (HYP_MGT_BREAKEVEN_1R_01)
            if self.enable_breakeven_1r and hasattr(plan, 'metadata') and plan.metadata is not None:
                max_fav = plan.metadata.get("max_favorable_price", entry_price)
                if is_long:
                    fav_r = (max_fav - entry_price) / entry_risk_dist
                    if fav_r >= self.breakeven_trigger_r - 1e-7:
                        be_stop = entry_price + (self.breakeven_stop_r * entry_risk_dist)
                        if be_stop > plan.stop_invalidation_price:
                            plan.stop_invalidation_price = be_stop
                            plan.metadata["breakeven_triggered"] = True
                            plan.metadata["breakeven_stop_price"] = be_stop
                else:
                    fav_r = (entry_price - max_fav) / entry_risk_dist
                    if fav_r >= self.breakeven_trigger_r - 1e-7:
                        be_stop = entry_price - (self.breakeven_stop_r * entry_risk_dist)
                        if be_stop < plan.stop_invalidation_price:
                            plan.stop_invalidation_price = be_stop
                            plan.metadata["breakeven_triggered"] = True
                            plan.metadata["breakeven_stop_price"] = be_stop

            # 2b. Profit-Lock & Break-Even Ratchet (Preserved for historical ablation, disabled in canonical H0)
            if self.enable_profit_lock and hasattr(plan, 'metadata') and plan.metadata is not None:
                max_fav = plan.metadata.get("max_favorable_price", entry_price)
                if is_long:
                    fav_r = (max_fav - entry_price) / entry_risk_dist
                    if fav_r >= self.profit_lock_trigger_r:
                        be_stop = entry_price + (self.profit_lock_stop_r * entry_risk_dist)
                        if be_stop > plan.stop_invalidation_price:
                            plan.stop_invalidation_price = be_stop
                    if fav_r >= self.lockin_r:
                        floor_stop = max_fav - (self.giveback_r * entry_risk_dist)
                        if floor_stop > plan.stop_invalidation_price:
                            plan.stop_invalidation_price = floor_stop
                else:
                    fav_r = (entry_price - max_fav) / entry_risk_dist
                    if fav_r >= self.profit_lock_trigger_r:
                        be_stop = entry_price - (self.profit_lock_stop_r * entry_risk_dist)
                        if be_stop < plan.stop_invalidation_price:
                            plan.stop_invalidation_price = be_stop
                    if fav_r >= self.lockin_r:
                        floor_stop = max_fav + (self.giveback_r * entry_risk_dist)
                        if floor_stop < plan.stop_invalidation_price:
                            plan.stop_invalidation_price = floor_stop

            # 3. Canonical MTF Structural Trailing Stop & Adverse CHOCH Exit
            if self.enable_mtf_trailing:
                from strategy_engine.lifecycle.mtf_trailing_engine import MTFStructuralTrailingEngine
                decision = MTFStructuralTrailingEngine.evaluate(plan, mtf_payload, ltf_payload)

                if decision.should_exit_structural:
                    plan.position_status = PositionState.MTF_TRAIL_EXIT.value
                    plan.exit_timestamp = ltf_payload.timestamp
                    exited_trades.append(plan)
                    del self.active_trades[trade_id]
                    continue

                if decision.should_update_stop and decision.new_stop_price is not None:
                    if is_long and decision.new_stop_price > plan.stop_invalidation_price:
                        plan.stop_invalidation_price = decision.new_stop_price
                    elif (not is_long) and decision.new_stop_price < plan.stop_invalidation_price:
                        plan.stop_invalidation_price = decision.new_stop_price
                        
            # 5. Check LTF / Trailed SL Trigger
            is_trailed = abs(plan.stop_invalidation_price - initial_sl) >= 1e-6
            exit_status = PositionState.MTF_TRAIL_EXIT.value if is_trailed else PositionState.LTF_SL_EXIT.value

            if is_long and cur_low <= plan.stop_invalidation_price:
                plan.position_status = exit_status
                plan.exit_timestamp = ltf_payload.timestamp
                exited_trades.append(plan)
                del self.active_trades[trade_id]
                continue
            elif not is_long and cur_high >= plan.stop_invalidation_price:
                plan.position_status = exit_status
                plan.exit_timestamp = ltf_payload.timestamp
                exited_trades.append(plan)
                del self.active_trades[trade_id]
                continue
                
        return exited_trades
