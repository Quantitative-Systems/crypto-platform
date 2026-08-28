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
        giveback_r: float = 0.75
    ):
        self.maker_fee_rate = maker_fee_rate
        self.taker_fee_rate = taker_fee_rate
        self.slippage_bps = slippage_bps
        self.enable_profit_lock = enable_profit_lock
        self.lockin_r = lockin_r
        self.giveback_r = giveback_r

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

            # Track Excursions (MFE / MAE)
            if is_long:
                trade.metadata["mfe_price"] = max(trade.metadata.get("mfe_price", trade.fill_entry_price), candle.high)
                trade.metadata["mae_price"] = min(trade.metadata.get("mae_price", trade.fill_entry_price), candle.low)
            else:
                trade.metadata["mfe_price"] = min(trade.metadata.get("mfe_price", trade.fill_entry_price), candle.low)
                trade.metadata["mae_price"] = max(trade.metadata.get("mae_price", trade.fill_entry_price), candle.high)

            # Profit-Lock & Break-Even Ratchet
            if self.enable_profit_lock:
                entry_p = trade.fill_entry_price
                init_sl = trade.initial_stop_price
                risk_dist = abs(entry_p - init_sl)
                if risk_dist > 0:
                    if is_long:
                        fav_p = trade.metadata.get("mfe_price", entry_p)
                        fav_r = (fav_p - entry_p) / risk_dist
                        # Tier 1: Break-even at +1.5R excursion (+0.1R buffer)
                        if fav_r >= 1.5:
                            be_stop = entry_p + (0.1 * risk_dist)
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
                        # Tier 1: Break-even at +1.5R excursion (-0.1R buffer)
                        if fav_r >= 1.5:
                            be_stop = entry_p - (0.1 * risk_dist)
                            if be_stop < trade.current_stop_price:
                                ledger.update_trailing_stop(trade.trade_id, be_stop)
                                trade.metadata["profit_locked"] = True
                        # Tier 2: Ratchet trailing floor at lockin_r
                        if fav_r >= self.lockin_r:
                            floor_stop = fav_p + (self.giveback_r * risk_dist)
                            if floor_stop < trade.current_stop_price:
                                ledger.update_trailing_stop(trade.trade_id, floor_stop)
                                trade.metadata["profit_locked"] = True

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

            if hit_sl:
                # Stop loss triggers as a Taker market order with slippage
                exit_price = self._apply_slippage(current_stop, is_buy=(not is_long))
                notional = exit_price * trade.position_units
                exit_fee = notional * self.taker_fee_rate
                
                # Tag whether it was initial structural SL or MTF/Profit-Lock Trailed stop
                if trade.metadata.get("profit_locked", False) and abs(current_stop - trade.initial_stop_price) >= 1e-6:
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
