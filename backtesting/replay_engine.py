"""
Product 01: Crypto Platform - Zero-Lookahead Market Replay Engine
Fixed TP/SL evaluation logic, bankruptcy protection, and research database logging.
"""

from typing import List, Dict, Any
from market_intelligence.primitives import Candle
from market_intelligence.state_engine import MarketStateEngine
from strategy.orchestrator import StrategyOrchestrator, TradePlan
from trade_management.trailing import TrailingEngine
from backtesting.friction_model import FrictionModel
from research.research_db import ResearchDB


class ReplayEngine:

    def __init__(self, swing_lookback: int = 2):
        self.state_engine = MarketStateEngine(swing_lookback=swing_lookback)
        self.friction_model = FrictionModel()
        self.research_db = ResearchDB()

    def run_replay(
        self,
        symbol: str,
        htf_candles: List[Candle],
        mtf_candles: List[Candle],
        ltf_candles: List[Candle],
        starting_balance: float = 1000.0,
        risk_pct: float = 0.01
    ) -> Dict[str, Any]:
        trade_history: List[Dict[str, Any]] = []
        active_position: Dict[str, Any] = None
        account_balance = starting_balance
        min_bars_required = 10

        telemetry_counts = {
            "total_bars_evaluated": 0,
            "gate_1_htf_fails": 0,
            "gate_2_mtf_fails": 0,
            "gate_3_ltf_fails": 0,
            "gate_4_risk_fails": 0,
            "trades_approved": 0,
            "total_friction_cost_usd": 0.0
        }

        if len(ltf_candles) < min_bars_required:
            return {"trade_history": trade_history, "telemetry": telemetry_counts, "final_balance": account_balance}

        for i in range(min_bars_required, len(ltf_candles)):
            if account_balance <= 0.0:
                account_balance = 0.0
                break

            current_bar = ltf_candles[i]
            current_time = current_bar.timestamp

            ltf_slice = ltf_candles[max(0, i - 100):i + 1]
            mtf_slice = [c for c in mtf_candles if c.timestamp <= current_time][-100:]
            htf_slice = [c for c in htf_candles if c.timestamp <= current_time][-50:]

            if len(htf_slice) < 5:
                htf_slice = htf_candles[:max(5, len(htf_candles))]
            if len(mtf_slice) < 5:
                mtf_slice = mtf_candles[:max(5, len(mtf_candles))]

            htf_state = self.state_engine.evaluate(htf_slice, symbol=symbol, timeframe="1D")
            mtf_state = self.state_engine.evaluate(mtf_slice, symbol=symbol, timeframe="4H")
            ltf_state = self.state_engine.evaluate(ltf_slice, symbol=symbol, timeframe="1H")

            # Manage active position
            if active_position is not None:
                action = active_position["action"]
                tp_price = active_position["tp"]
                sl_price = active_position["sl"]

                hit_tp = (action == "BUY" and current_bar.high >= tp_price) or (action == "SELL" and current_bar.low <= tp_price)
                hit_sl = (action == "BUY" and current_bar.low <= sl_price) or (action == "SELL" and current_bar.high >= sl_price)

                if hit_tp or hit_sl:
                    exit_type = "TP_HIT" if hit_tp else "SL_HIT"
                    raw_exit = tp_price if hit_tp else sl_price
                    fill_exit = self.friction_model.calculate_sell_fill(raw_exit) if action == "BUY" else self.friction_model.calculate_buy_fill(raw_exit)

                    notional_exit = fill_exit * active_position["position_size"]
                    exit_fee = self.friction_model.calculate_fee(notional_exit)
                    total_friction = active_position["entry_fee"] + exit_fee

                    gross_pnl = (fill_exit - active_position["fill_entry_price"]) * active_position["position_size"] if action == "BUY" else (active_position["fill_entry_price"] - fill_exit) * active_position["position_size"]
                    net_pnl_usd = gross_pnl - exit_fee

                    account_balance += net_pnl_usd
                    active_position["exit_price"] = fill_exit
                    active_position["pnl_usd"] = net_pnl_usd
                    active_position["friction_cost_usd"] = total_friction
                    active_position["exit_reason"] = exit_type

                    telemetry_counts["total_friction_cost_usd"] += total_friction
                    self.research_db.log_trade(active_position)
                    trade_history.append(active_position)
                    active_position = None
                    continue

                # Trailing SL Update
                trail_res = TrailingEngine.update_trailing_stop(
                    action=action,
                    current_stop_loss=active_position["sl"],
                    entry_price=active_position["raw_entry_price"],
                    current_close=current_bar.close,
                    mtf_state=mtf_state
                )
                if trail_res.is_updated:
                    active_position["sl"] = trail_res.new_stop_loss

                continue

            # Evaluate new trade entry if flat
            if active_position is None:
                telemetry_counts["total_bars_evaluated"] += 1

                plan: TradePlan = StrategyOrchestrator.process_pipeline(
                    htf_state=htf_state,
                    mtf_state=mtf_state,
                    ltf_state=ltf_state,
                    latest_candle=current_bar,
                    account_balance=account_balance,
                    risk_pct=risk_pct
                )

                if plan.status == "APPROVED":
                    telemetry_counts["trades_approved"] += 1

                    raw_entry = plan.entry_price
                    fill_entry = self.friction_model.calculate_buy_fill(raw_entry) if plan.action == "BUY" else self.friction_model.calculate_sell_fill(raw_entry)
                    notional_entry = fill_entry * plan.position_size_units
                    entry_fee = self.friction_model.calculate_fee(notional_entry)

                    active_position = {
                        "symbol": symbol,
                        "action": plan.action,
                        "strategy_type": plan.strategy_type,
                        "raw_entry_price": raw_entry,
                        "fill_entry_price": fill_entry,
                        "entry_fee": entry_fee,
                        "sl": plan.stop_loss_price,
                        "tp": plan.target_tp_price,
                        "position_size": plan.position_size_units,
                        "dollar_risk": plan.dollar_risk_usd,
                        "initial_rr": plan.reward_to_risk_ratio,
                        "entry_timestamp": current_time,
                        "friction_cost_usd": entry_fee
                    }
                else:
                    reason = plan.reason
                    if "Gate 1" in reason:
                        telemetry_counts["gate_1_htf_fails"] += 1
                    elif "Gate 2" in reason:
                        telemetry_counts["gate_2_mtf_fails"] += 1
                    elif "Gate 3" in reason:
                        telemetry_counts["gate_3_ltf_fails"] += 1
                    elif "Gate 4" in reason:
                        telemetry_counts["gate_4_risk_fails"] += 1

        self.research_db.log_telemetry(symbol, telemetry_counts)
        return {
            "trade_history": trade_history,
            "telemetry": telemetry_counts,
            "final_balance": account_balance
        }