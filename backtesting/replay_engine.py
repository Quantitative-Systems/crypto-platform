"""
Product 01: Crypto Platform - Zero-Lookahead Market Replay Engine
Replays historical candles sequentially and logs Gate Diagnostic Telemetry.
"""

from typing import List, Dict, Any
from market_intelligence.primitives import Candle
from market_intelligence.state_engine import MarketStateEngine
from strategy.orchestrator import StrategyOrchestrator, TradePlan
from trade_management.trailing import TrailingEngine


class ReplayEngine:

    def __init__(self, swing_lookback: int = 2):
        self.state_engine = MarketStateEngine(swing_lookback=swing_lookback)

    def run_replay(
        self,
        symbol: str,
        htf_candles: List[Candle],
        mtf_candles: List[Candle],
        ltf_candles: List[Candle],
        starting_balance: float = 1000.0,
        risk_pct: float = 0.01
    ) -> Dict[str, Any]:
        """
        Replays candles bar-by-bar across HTF, MTF, and LTF.
        Tracks Gate Rejection Diagnostic Telemetry for every bar.
        """
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
            "htf_rejection_reasons": {}
        }

        if len(ltf_candles) < min_bars_required:
            return {"trade_history": trade_history, "telemetry": telemetry_counts, "final_balance": account_balance}

        # Sequential bar-by-bar replay across LTF timeframe
        for i in range(min_bars_required, len(ltf_candles)):
            current_bar = ltf_candles[i]
            current_time = current_bar.timestamp

            # Slice history up to current_time (Zero Lookahead)
            ltf_slice = ltf_candles[max(0, i - 50):i + 1]
            mtf_slice = [c for c in mtf_candles if c.timestamp <= current_time][-50:]
            htf_slice = [c for c in htf_candles if c.timestamp <= current_time][-50:]

            # Provide minimum historical context if slices are sparse
            if len(htf_slice) < 5:
                htf_slice = htf_candles[:max(5, len(htf_candles))]
            if len(mtf_slice) < 5:
                mtf_slice = mtf_candles[:max(5, len(mtf_candles))]

            # Evaluate market states strictly on past slice data
            htf_state = self.state_engine.evaluate(htf_slice, symbol=symbol, timeframe="1D")
            mtf_state = self.state_engine.evaluate(mtf_slice, symbol=symbol, timeframe="4H")
            ltf_state = self.state_engine.evaluate(ltf_slice, symbol=symbol, timeframe="1H")

            # Manage active trade if open
            if active_position is not None:
                action = active_position["action"]

                # 1. Check Take Profit Hit
                if (action == "BUY" and current_bar.high >= active_position["tp"]) or \
                   (action == "SELL" and current_bar.low <= active_position["tp"]):
                    r_multiple = active_position["initial_rr"]
                    pnl_usd = active_position["dollar_risk"] * r_multiple
                    account_balance += pnl_usd
                    active_position["exit_price"] = active_position["tp"]
                    active_position["pnl_usd"] = pnl_usd
                    active_position["exit_reason"] = "TP_HIT"
                    active_position["r_multiple"] = r_multiple
                    trade_history.append(active_position)
                    active_position = None
                    continue

                # 2. Check Stop Loss Hit
                elif (action == "BUY" and current_bar.low <= active_position["sl"]) or \
                     (action == "SELL" and current_bar.high >= active_position["sl"]):
                    r_multiple = -1.0
                    pnl_usd = -active_position["dollar_risk"]
                    account_balance += pnl_usd
                    active_position["exit_price"] = active_position["sl"]
                    active_position["pnl_usd"] = pnl_usd
                    active_position["exit_reason"] = "SL_HIT"
                    active_position["r_multiple"] = r_multiple
                    trade_history.append(active_position)
                    active_position = None
                    continue

                # 3. Dynamic MTF Structural Trailing Stop Update
                trail_res = TrailingEngine.update_trailing_stop(
                    action=action,
                    current_stop_loss=active_position["sl"],
                    mtf_state=mtf_state
                )
                if trail_res.is_updated:
                    active_position["sl"] = trail_res.new_stop_loss

                continue

            # Evaluate strategy pipeline for new trade entry if flat
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
                    active_position = {
                        "trade_id": len(trade_history) + 1,
                        "symbol": symbol,
                        "action": plan.action,
                        "strategy_type": plan.strategy_type,
                        "entry_price": plan.entry_price,
                        "sl": plan.stop_loss_price,
                        "tp": plan.target_tp_price,
                        "position_size": plan.position_size_units,
                        "dollar_risk": plan.dollar_risk_usd,
                        "initial_rr": plan.reward_to_risk_ratio,
                        "entry_timestamp": current_time
                    }
                else:
                    reason = plan.reason
                    if "Gate 1" in reason:
                        telemetry_counts["gate_1_htf_fails"] += 1
                        sub_reason = reason.replace("Gate 1 Fail: ", "")
                        telemetry_counts["htf_rejection_reasons"][sub_reason] = \
                            telemetry_counts["htf_rejection_reasons"].get(sub_reason, 0) + 1
                    elif "Gate 2" in reason:
                        telemetry_counts["gate_2_mtf_fails"] += 1
                    elif "Gate 3" in reason:
                        telemetry_counts["gate_3_ltf_fails"] += 1
                    elif "Gate 4" in reason:
                        telemetry_counts["gate_4_risk_fails"] += 1

        return {
            "trade_history": trade_history,
            "telemetry": telemetry_counts,
            "final_balance": account_balance
        }