from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from market_intelligence.primitives import Candle, RawSwing
from market_intelligence.raw_swing_engine import RawSwingEngine, RawSwingConfig
from strategy_candidate.indicators import SupertrendEngine, StochasticEngine
from strategy_candidate.strategy_logic import StrategyCandidateLogic, TimeframeContext, SetupState
from strategy_candidate.trailing_manager import TrailingManager, TrailingPhase
from backtesting.friction_model import FrictionModel
from strategy_engine.news.news_provider import NullNewsProvider
import datetime

@dataclass
class ReplayResult:
    trades: List[Dict[str, Any]]
    final_balance: float

class CandidateReplayer:
    def __init__(self):
        self.friction_model = FrictionModel()
        self.news_provider = NullNewsProvider()
        
    def _compute_swings(self, candles: List[Candle], tf: str) -> List[RawSwing]:
        engine = RawSwingEngine(RawSwingConfig(left_bars=2, right_bars=2, timeframe=tf))
        return engine.detect(candles)
        
    def run(
        self,
        symbol: str,
        set_name: str,
        htf_candles: List[Candle],
        mtf_candles: List[Candle],
        ltf_candles: List[Candle],
        starting_balance: float = 1000.0,
        risk_pct: float = 0.01,
        direction: int = 1 # 1 for Long, -1 for Short
    ) -> ReplayResult:
        if len(htf_candles) < 50 or len(mtf_candles) < 50 or len(ltf_candles) < 50:
            return ReplayResult([], starting_balance)
            
        # 1. Compute Intervals
        htf_interval = htf_candles[1].timestamp - htf_candles[0].timestamp
        mtf_interval = mtf_candles[1].timestamp - mtf_candles[0].timestamp
        ltf_interval = ltf_candles[1].timestamp - ltf_candles[0].timestamp
        
        # 2. Bulk Compute Indicators
        htf_st = SupertrendEngine.calculate(htf_candles, 6, 5.0)
        htf_stoch = StochasticEngine.calculate(htf_candles, 25, 5, 3)
        htf_swings = self._compute_swings(htf_candles, "HTF")
        
        mtf_st = SupertrendEngine.calculate(mtf_candles, 6, 5.0)
        mtf_stoch = StochasticEngine.calculate(mtf_candles, 25, 5, 3)
        mtf_swings = self._compute_swings(mtf_candles, "MTF")
        
        ltf_st = SupertrendEngine.calculate(ltf_candles, 6, 5.0)
        ltf_stoch = StochasticEngine.calculate(ltf_candles, 25, 5, 3)
        ltf_swings = self._compute_swings(ltf_candles, "LTF")
        
        # 3. Setup State
        htf_ctx = TimeframeContext("HTF")
        mtf_ctx = TimeframeContext("MTF")
        ltf_ctx = TimeframeContext("LTF")
        
        balance = starting_balance
        trades = []
        active_position = None
        trailing_mgr = None
        
        htf_idx = 0
        mtf_idx = 0
        
        for i in range(10, len(ltf_candles)):
            if balance <= 0:
                break
                
            ltf_bar = ltf_candles[i]
            ltf_close_time = ltf_bar.timestamp + ltf_interval
            
            # Advance HTF index
            while htf_idx + 1 < len(htf_candles) and htf_candles[htf_idx + 1].timestamp + htf_interval <= ltf_close_time:
                htf_idx += 1
                
            # Advance MTF index
            while mtf_idx + 1 < len(mtf_candles) and mtf_candles[mtf_idx + 1].timestamp + mtf_interval <= ltf_close_time:
                mtf_idx += 1
                
            # Check if we have enough bars
            if htf_idx < 10 or mtf_idx < 10:
                continue
                
            current_htf_st = htf_st[htf_idx]
            current_htf_stoch = htf_stoch[htf_idx]
            
            current_mtf_st = mtf_st[mtf_idx]
            current_mtf_stoch = mtf_stoch[mtf_idx]
            
            current_ltf_st = ltf_st[i]
            current_ltf_stoch = ltf_stoch[i]
            prev_ltf_stoch = ltf_stoch[i-1]
            
            if active_position is not None:
                # Update Trailing
                current_sl = trailing_mgr.update(
                    current_ltf_st["supertrend"],
                    current_mtf_st["supertrend"],
                    current_htf_st["supertrend"]
                )
                
                # Check Exits
                hit_sl = False
                hit_tp = False
                
                if direction == 1:
                    if ltf_bar.low <= current_sl:
                        hit_sl = True
                    if ltf_bar.high >= active_position["tp3"]:
                        hit_tp = True
                else:
                    if ltf_bar.high >= current_sl:
                        hit_sl = True
                    if ltf_bar.low <= active_position["tp3"]:
                        hit_tp = True
                        
                if hit_sl or hit_tp:
                    # Adverse-first collision invariant: SL takes precedence on same-bar collision
                    if hit_sl and hit_tp:
                        hit_tp = False
                    exit_price = current_sl if hit_sl else active_position["tp3"]
                    # If gap past stop/target, use fill model
                    fill_exit = self.friction_model.calculate_sell_fill(exit_price) if direction == 1 else self.friction_model.calculate_buy_fill(exit_price)
                    
                    gross_pnl = (fill_exit - active_position["fill_entry"]) * active_position["size"] * direction
                    notional_exit = fill_exit * active_position["size"]
                    exit_fee = self.friction_model.calculate_fee(notional_exit)
                    
                    net_pnl = gross_pnl - exit_fee
                    balance += net_pnl
                    
                    active_position["exit_price"] = fill_exit
                    active_position["exit_time"] = ltf_close_time
                    active_position["pnl"] = net_pnl
                    active_position["reason"] = "TP3" if hit_tp else ("SL" if trailing_mgr.phase == TrailingPhase.PHASE_1_LTF else "TRAIL")
                    
                    trades.append(active_position)
                    active_position = None
                    trailing_mgr = None
                    
                    # Reset states after trade
                    htf_ctx.state = SetupState.WAITING_25 if direction == 1 else SetupState.WAITING_75
                    mtf_ctx.state = SetupState.WAITING_75
                    ltf_ctx.state = SetupState.WAITING_75
                
                continue
            
            # Not in trade, evaluate logic
            # Only evaluate HTF/MTF when a new bar closes
            is_new_htf = (htf_candles[htf_idx].timestamp + htf_interval == ltf_close_time)
            is_new_mtf = (mtf_candles[mtf_idx].timestamp + mtf_interval == ltf_close_time)
            
            if is_new_htf:
                StrategyCandidateLogic.evaluate_htf(
                    htf_ctx,
                    current_htf_st["direction"],
                    current_htf_stoch["k"],
                    htf_swings,
                    ltf_close_time,
                    direction
                )
                
            if is_new_mtf:
                StrategyCandidateLogic.evaluate_mtf(
                    mtf_ctx,
                    current_mtf_st["direction"],
                    current_mtf_stoch["k"],
                    mtf_swings,
                    ltf_close_time,
                    direction
                )
                
            # LTF always evaluated
            StrategyCandidateLogic.evaluate_ltf(
                ltf_ctx,
                current_ltf_st["direction"],
                current_ltf_stoch["k"],
                current_ltf_stoch["d"],
                prev_ltf_stoch["k"],
                prev_ltf_stoch["d"],
                ltf_swings,
                ltf_close_time,
                direction
            )
            
            # Check Entry
            if htf_ctx.state == SetupState.READY and mtf_ctx.state == SetupState.READY and ltf_ctx.state == SetupState.READY:
                # 6R Target Check
                entry_price = ltf_bar.close
                sl_price = current_ltf_st["supertrend"]
                tp3_price = htf_ctx.target_price
                
                if tp3_price is not None:
                    risk = abs(entry_price - sl_price)
                    if risk > 0:
                        reward = abs(tp3_price - entry_price)
                        rr = reward / risk
                        
                        if rr >= 6.0:
                            # News Filter Check
                            is_blackout, _ = self.news_provider.is_news_blackout(symbol, ltf_close_time // 1000)
                            if not is_blackout:
                                # ENTER TRADE
                                fill_entry = self.friction_model.calculate_buy_fill(entry_price) if direction == 1 else self.friction_model.calculate_sell_fill(entry_price)
                                dollar_risk = balance * risk_pct
                                position_size = dollar_risk / risk
                                notional_entry = fill_entry * position_size
                                entry_fee = self.friction_model.calculate_fee(notional_entry)
                                
                                # Use MTF target as TP2 and TP1
                                tp2_price = mtf_ctx.target_price
                                tp1_price = ltf_ctx.target_price
                                
                                if tp1_price is None:
                                    tp1_price = entry_price + (risk * direction * 2) # fallback
                                if tp2_price is None:
                                    tp2_price = entry_price + (risk * direction * 4) # fallback
                                
                                active_position = {
                                    "symbol": symbol,
                                    "set": set_name,
                                    "direction": "LONG" if direction == 1 else "SHORT",
                                    "entry_time": ltf_close_time,
                                    "entry_price": entry_price,
                                    "fill_entry": fill_entry,
                                    "size": position_size,
                                    "entry_fee": entry_fee,
                                    "initial_sl": sl_price,
                                    "tp1": tp1_price,
                                    "tp2": tp2_price,
                                    "tp3": tp3_price,
                                    "initial_rr": rr
                                }
                                
                                trailing_mgr = TrailingManager(
                                    direction=direction,
                                    tp1=tp1_price,
                                    tp2=tp2_price,
                                    tp3=tp3_price,
                                    current_sl=sl_price
                                )
                                
                                # Reset ready states to prevent multiple entries on same signal
                                htf_ctx.state = SetupState.WAITING_25 if direction == 1 else SetupState.WAITING_75
                                mtf_ctx.state = SetupState.WAITING_75
                                ltf_ctx.state = SetupState.WAITING_75
                                
        return ReplayResult(trades, balance)
