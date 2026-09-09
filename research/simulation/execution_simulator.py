"""
Product 04 — Research Laboratory: Execution & Friction Simulator
Simulates realistic limit order entries, market stop losses, taker/maker fees, 
slippage penalties, and conservative adverse-first intrabar collision resolution.
"""

from typing import List, Tuple, Optional
from market_intelligence.primitives import Candle
from research.simulation.trade_ledger import TradeLedger, SimulatedTrade


class ExecutionSimulator:
    """
    Simulates order execution and friction on candle streams.
    """

    def __init__(
        self,
        maker_fee_rate: float = 0.0000,   # 0.00% maker fee
        taker_fee_rate: float = 0.0005,   # 0.05% taker fee
        slippage_bps: float = 5.0,        # 5.0 basis points slippage on stop-loss market orders
        enable_profit_lock: bool = False,
        lockin_r: float = 1.0,
        giveback_r: float = 0.75,
        profit_lock_trigger_r: float = 1.0,
        profit_lock_stop_r: float = 0.10,
        enable_breakeven_1r: bool = False,
        breakeven_trigger_r: float = 1.0,
        breakeven_stop_r: float = 0.10,
        enable_milestone_target: bool = False,
        milestone_r: float = 2.5
    ):
        self.maker_fee_rate = maker_fee_rate
        self.taker_fee_rate = taker_fee_rate
        self.slippage_bps = slippage_bps
        self.enable_profit_lock = enable_profit_lock
        self.lockin_r = lockin_r
        self.giveback_r = giveback_r
        self.profit_lock_trigger_r = profit_lock_trigger_r
        self.profit_lock_stop_r = profit_lock_stop_r
        self.enable_breakeven_1r = enable_breakeven_1r
        self.breakeven_trigger_r = breakeven_trigger_r
        self.breakeven_stop_r = breakeven_stop_r
        self.enable_milestone_target = enable_milestone_target
        self.milestone_r = milestone_r

    def _apply_slippage(self, base_price: float, is_buy: bool) -> float:
        """
        Slippage penalizes market fills:
        - Buying costs more: price * (1 + slippage)
        - Selling receives less: price * (1 - slippage)
        """
        slippage_factor = self.slippage_bps / 10000.0
        if is_buy:
            return base_price * (1.0 + slippage_factor)
        else:
            return base_price * (1.0 - slippage_factor)

    def process_candle(self, candle: Candle, ledger: TradeLedger) -> List[SimulatedTrade]:
        """
        Processes forward candle against pending limit entries and active open positions.
        Returns list of trades that were closed during this candle.
        """
        closed_this_bar: List[SimulatedTrade] = []

        # 1. Process Pending Limit Entries
        for trade in ledger.get_pending_trades():
            is_long = trade.directional_permission == "PERMIT_LONG"
            
            # Limit order triggers if price reaches the entry_price
            triggered = False
            if is_long and candle.low <= trade.entry_price:
                triggered = True
            elif not is_long and candle.high >= trade.entry_price:
                triggered = True

            if triggered:
                # Limit orders fill as Maker at exact limit price without slippage
                fill_price = trade.entry_price
                notional = fill_price * trade.position_units
                entry_fee = notional * self.maker_fee_rate
                ledger.activate_trade(
                    trade_id=trade.trade_id,
                    fill_price=fill_price,
                    timestamp=candle.timestamp,
                    entry_fee=entry_fee,
                    slippage_bps=0.0
                )

        # 2. Process Active Open Trades (Intrabar SL/TP Evaluation)
        for trade in ledger.get_active_trades():
            is_long = trade.directional_permission == "PERMIT_LONG"
            target_price = trade.target_price

            # Track Excursions (MFE / MAE) and Timing Milestones
            entry_p = trade.fill_entry_price or trade.entry_price
            init_sl = trade.initial_stop_price
            risk_dist = abs(entry_p - init_sl)

            if is_long:
                if candle.high > trade.metadata.get("mfe_price", entry_p):
                    trade.metadata["mfe_price"] = candle.high
                    trade.metadata["mfe_timestamp"] = candle.timestamp
                if candle.low < trade.metadata.get("mae_price", entry_p):
                    trade.metadata["mae_price"] = candle.low
                    trade.metadata["mae_timestamp"] = candle.timestamp
            else:
                if candle.low < trade.metadata.get("mfe_price", entry_p):
                    trade.metadata["mfe_price"] = candle.low
                    trade.metadata["mfe_timestamp"] = candle.timestamp
                if candle.high > trade.metadata.get("mae_price", entry_p):
                    trade.metadata["mae_price"] = candle.high
                    trade.metadata["mae_timestamp"] = candle.timestamp

            # Track excursion milestones (time to +0.5R, +1R, +2R, +3R, +4R)
            if risk_dist > 0 and trade.entry_timestamp:
                curr_fav_p = trade.metadata.get("mfe_price", entry_p)
                curr_fav_r = (curr_fav_p - entry_p) / risk_dist if is_long else (entry_p - curr_fav_p) / risk_dist
                dt = candle.timestamp - trade.entry_timestamp
                if curr_fav_r >= 0.5 and "time_to_0_5r" not in trade.metadata:
                    trade.metadata["time_to_0_5r"] = dt
                if curr_fav_r >= 1.0 and "time_to_1_0r" not in trade.metadata:
                    trade.metadata["time_to_1_0r"] = dt
                if curr_fav_r >= 2.0 and "time_to_2_0r" not in trade.metadata:
                    trade.metadata["time_to_2_0r"] = dt
                if curr_fav_r >= 3.0 and "time_to_3_0r" not in trade.metadata:
                    trade.metadata["time_to_3_0r"] = dt
                if curr_fav_r >= 4.0 and "time_to_4_0r" not in trade.metadata:
                    trade.metadata["time_to_4_0r"] = dt

            # Prior stop level at start of candle (for adverse-first collision arbitration)
            prior_stop = trade.current_stop_price
            hit_prior_sl = (candle.low <= prior_stop) if is_long else (candle.high >= prior_stop)

            # HYP_MGT_BREAKEVEN_1R_01: Single-variable +1.0R -> +0.10R monotonic breakeven ratchet
            if self.enable_breakeven_1r and risk_dist > 0:
                # Adverse-first collision invariant: If candle penetrated prior adverse stop,
                # adverse stop wins; cannot assume +1.0R was reached prior to stop-out.
                if not hit_prior_sl:
                    if is_long:
                        fav_p = trade.metadata.get("mfe_price", entry_p)
                        fav_r = (fav_p - entry_p) / risk_dist
                        if fav_r >= self.breakeven_trigger_r - 1e-7:
                            be_stop = entry_p + (self.breakeven_stop_r * risk_dist)
                            # Monotonicity: never weaken an already superior stop
                            if be_stop > trade.current_stop_price:
                                ledger.update_trailing_stop(trade.trade_id, be_stop)
                                trade.metadata["breakeven_triggered"] = True
                                trade.metadata["breakeven_trigger_ts"] = candle.timestamp
                                trade.metadata["breakeven_trigger_price"] = entry_p + (self.breakeven_trigger_r * risk_dist)
                                trade.metadata["breakeven_stop_ts"] = candle.timestamp
                                trade.metadata["breakeven_stop_price"] = be_stop
                    else:
                        fav_p = trade.metadata.get("mfe_price", entry_p)
                        fav_r = (entry_p - fav_p) / risk_dist
                        if fav_r >= self.breakeven_trigger_r - 1e-7:
                            be_stop = entry_p - (self.breakeven_stop_r * risk_dist)
                            # Monotonicity: never weaken an already superior stop
                            if be_stop < trade.current_stop_price:
                                ledger.update_trailing_stop(trade.trade_id, be_stop)
                                trade.metadata["breakeven_triggered"] = True
                                trade.metadata["breakeven_trigger_ts"] = candle.timestamp
                                trade.metadata["breakeven_trigger_price"] = entry_p - (self.breakeven_trigger_r * risk_dist)
                                trade.metadata["breakeven_stop_ts"] = candle.timestamp
                                trade.metadata["breakeven_stop_price"] = be_stop

            # Profit-Lock & Break-Even Ratchet
            if self.enable_profit_lock:
                if risk_dist > 0:
                    if is_long:
                        fav_p = trade.metadata.get("mfe_price", entry_p)
                        fav_r = (fav_p - entry_p) / risk_dist
                        # Tier 1: Break-even / profit lock at profit_lock_trigger_r (+profit_lock_stop_r buffer)
                        if fav_r >= self.profit_lock_trigger_r:
                            be_stop = entry_p + (self.profit_lock_stop_r * risk_dist)
                            if be_stop > trade.current_stop_price:
                                ledger.update_trailing_stop(trade.trade_id, be_stop)
                                trade.metadata["profit_locked"] = True
                        # Tier 2: Ratchet trailing floor at lockin_r
                        if fav_r >= self.lockin_r:
                            floor_stop = fav_p - (self.giveback_r * risk_dist)
                            if floor_stop > trade.current_stop_price:
                                ledger.update_trailing_stop(trade.trade_id, floor_stop)
                                trade.metadata["profit_locked"] = True
                    else:
                        fav_p = trade.metadata.get("mfe_price", entry_p)
                        fav_r = (entry_p - fav_p) / risk_dist
                        # Tier 1: Break-even / profit lock at profit_lock_trigger_r (-profit_lock_stop_r buffer)
                        if fav_r >= self.profit_lock_trigger_r:
                            be_stop = entry_p - (self.profit_lock_stop_r * risk_dist)
                            if be_stop < trade.current_stop_price:
                                ledger.update_trailing_stop(trade.trade_id, be_stop)
                                trade.metadata["profit_locked"] = True
                        # Tier 2: Ratchet trailing floor at lockin_r
                        if fav_r >= self.lockin_r:
                            floor_stop = fav_p + (self.giveback_r * risk_dist)
                            if floor_stop < trade.current_stop_price:
                                ledger.update_trailing_stop(trade.trade_id, floor_stop)
                                trade.metadata["profit_locked"] = True

            # HYP_TARGET_MILESTONE_01: Pre-registered +2.5R milestone target exit
            hit_milestone = False
            milestone_price = None
            if self.enable_milestone_target and risk_dist > 0:
                if is_long:
                    milestone_price = entry_p + (self.milestone_r * risk_dist)
                    hit_milestone = (candle.high >= milestone_price)
                else:
                    milestone_price = entry_p - (self.milestone_r * risk_dist)
                    hit_milestone = (candle.low <= milestone_price)

            current_stop = trade.current_stop_price
            hit_sl = False
            hit_tp = False

            if is_long:
                hit_sl = (candle.low <= current_stop)
                hit_tp = (candle.high >= target_price)
            else:
                hit_sl = (candle.high >= current_stop)
                hit_tp = (candle.low <= target_price)

            # 3. Collision Resolution & Execution
            if hit_sl and hit_tp:
                # ADVERSE-FIRST BASELINE AXIOM: Stop Loss takes priority in ambiguous bars
                hit_tp = False
            if hit_sl and hit_milestone:
                # ADVERSE-FIRST BASELINE AXIOM: Stop Loss takes priority over milestone target
                hit_milestone = False

            if hit_sl:
                # Stop loss triggers as a Taker market order with slippage
                exit_price = self._apply_slippage(current_stop, is_buy=(not is_long))
                notional = exit_price * trade.position_units
                exit_fee = notional * self.taker_fee_rate
                
                # Tag whether it was initial structural SL or MTF/Profit-Lock Trailed stop
                if trade.metadata.get("breakeven_triggered", False) and abs(current_stop - trade.metadata.get("breakeven_stop_price", -999.0)) < 1e-5:
                    exit_reason = "BREAKEVEN_TRAIL"
                elif trade.metadata.get("profit_locked", False) and abs(current_stop - trade.initial_stop_price) >= 1e-6:
                    exit_reason = "PROFIT_LOCK_TRAIL"
                elif abs(current_stop - trade.initial_stop_price) < 1e-6:
                    exit_reason = "INITIAL_LTF_SL"
                else:
                    exit_reason = "MTF_STRUCTURAL_TRAIL"

                closed = ledger.close_trade(
                    trade_id=trade.trade_id,
                    exit_price=exit_price,
                    exit_timestamp=candle.timestamp,
                    exit_reason=exit_reason,
                    exit_fee=exit_fee,
                    slippage_bps=self.slippage_bps
                )
                if closed:
                    closed_this_bar.append(closed)

            elif hit_milestone:
                # Milestone target fills as Limit at milestone price with maker fee (0 slippage)
                exit_price = milestone_price
                notional = exit_price * trade.position_units
                exit_fee = notional * self.maker_fee_rate

                closed = ledger.close_trade(
                    trade_id=trade.trade_id,
                    exit_price=exit_price,
                    exit_timestamp=candle.timestamp,
                    exit_reason="MILESTONE_TARGET_EXIT",
                    exit_fee=exit_fee,
                    slippage_bps=0.0
                )
                if closed:
                    closed_this_bar.append(closed)

            elif hit_tp:
                # Target Take Profit fills as Limit at target price with maker fee
                exit_price = target_price
                notional = exit_price * trade.position_units
                exit_fee = notional * self.maker_fee_rate

                closed = ledger.close_trade(
                    trade_id=trade.trade_id,
                    exit_price=exit_price,
                    exit_timestamp=candle.timestamp,
                    exit_reason="HTF_TP",
                    exit_fee=exit_fee,
                    slippage_bps=0.0
                )
                if closed:
                    closed_this_bar.append(closed)

        return closed_this_bar

    def execute_structural_exit(
        self,
        trade_id: str,
        current_market_price: float,
        timestamp: int,
        exit_reason: str,
        ledger: TradeLedger
    ) -> Optional[SimulatedTrade]:
        """
        Executes a direct market exit triggered by the strategy (e.g., MTF CHOCH structure shift).
        """
        trade = ledger.trades.get(trade_id)
        if not trade or trade.status != "ACTIVE":
            return None

        is_long = trade.directional_permission == "PERMIT_LONG"
        exit_price = self._apply_slippage(current_market_price, is_buy=(not is_long))
        notional = exit_price * trade.position_units
        exit_fee = notional * self.taker_fee_rate

        return ledger.close_trade(
            trade_id=trade_id,
            exit_price=exit_price,
            exit_timestamp=timestamp,
            exit_reason=exit_reason,
            exit_fee=exit_fee,
            slippage_bps=self.slippage_bps
        )
