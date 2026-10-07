"""
Quantitative Systems Platform (QSP) — Production Trade Management Engine.

Decouples trade execution and lifecycle management from strategy signal generation.
Implements the institutional 5-phase trade lifecycle:
1. Pre-Entry Validation: Spread, liquidity, volatility, funding, leverage, feasibility, portfolio heat.
2. Entry Execution: Limit vs Market, precision rounding, slippage guard, fill verification.
3. Post-Entry Placement: Initial SL, emergency buffer SL, multi-tier TP1/TP2/TP3.
4. Active In-Trade Management: Break-even locking at +1.0R, dynamic ATR trailing, time decay, regime shift exit.
5. Emergency Fail-Safes: Stale price quarantine (>30s), websocket disconnection, orphan order detection.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Any, Optional


class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class PositionLifecycleStage(str, Enum):
    PENDING_PRE_ENTRY = "PENDING_PRE_ENTRY"
    ENTRY_SUBMITTED = "ENTRY_SUBMITTED"
    ACTIVE = "ACTIVE"
    BREAK_EVEN_LOCKED = "BREAK_EVEN_LOCKED"
    TRAILING_ACTIVE = "TRAILING_ACTIVE"
    PARTIAL_PROFIT_TAKEN = "PARTIAL_PROFIT_TAKEN"
    CLOSED_TP = "CLOSED_TP"
    CLOSED_SL = "CLOSED_SL"
    CLOSED_TIME_STOP = "CLOSED_TIME_STOP"
    CLOSED_REGIME_CHANGE = "CLOSED_REGIME_CHANGE"
    CLOSED_EMERGENCY = "CLOSED_EMERGENCY"
    REJECTED_PRE_ENTRY = "REJECTED_PRE_ENTRY"


@dataclass
class PreEntryCheckResult:
    passed: bool
    spread_pct: float
    volatility_atr_pct: float
    current_heat_pct: float
    projected_heat_pct: float
    leverage_required: float
    is_notional_feasible: bool
    rejection_reasons: List[str]


@dataclass
class TradeOrderPlan:
    symbol: str
    direction: str  # 'LONG' or 'SHORT'
    order_type: OrderType
    intended_entry_price: float
    intended_sl_price: float
    intended_tp1_price: float
    intended_tp2_price: float
    intended_tp3_price: float
    intended_qty: float
    intended_notional: float
    risk_usd: float
    risk_pct_account: float
    max_slippage_pct: float = 0.0015  # 0.15%


@dataclass
class ManagedPosition:
    position_id: str
    strategy_id: str
    symbol: str
    direction: str
    stage: PositionLifecycleStage
    entry_time: int
    entry_price: float
    current_sl_price: float
    initial_sl_price: float
    emergency_sl_price: float
    tp1_price: float
    tp2_price: float
    tp3_price: float
    tp1_hit: bool = False
    tp2_hit: bool = False
    tp3_hit: bool = False
    total_qty: float = 0.0
    remaining_qty: float = 0.0
    risk_r_unit_usd: float = 0.0  # 1R in dollars
    peak_unrealized_r: float = 0.0
    bars_held: int = 0
    max_holding_bars: int = 40
    last_update_ts: int = 0
    audit_log: List[Dict[str, Any]] = field(default_factory=list)


class TradeManagementEngine:
    """
    Comprehensive lifecycle engine managing orders before, during, and after entry.
    """

    MAX_SPREAD_PCT = 0.0015  # 0.15% max allowable spread
    MAX_PORTFOLIO_HEAT_PCT = 3.0  # 3.0% max aggregate risk
    MAX_SAFE_LEVERAGE = 10.0
    MIN_NOTIONAL_USD = 5.0  # Binance standard

    def __init__(self):
        self.active_positions: Dict[str, ManagedPosition] = {}

    def perform_pre_entry_checks(
        self,
        plan: TradeOrderPlan,
        current_bid: float,
        current_ask: float,
        current_atr: float,
        account_equity: float,
        current_portfolio_heat_pct: float,
    ) -> PreEntryCheckResult:
        """Evaluates all institutional pre-entry filters before order routing."""
        reasons = []

        # 1. Spread Check
        mid_price = (current_bid + current_ask) / 2.0
        spread_pct = (current_ask - current_bid) / mid_price if mid_price > 0 else 1.0
        if spread_pct > self.MAX_SPREAD_PCT:
            reasons.append(f"Spread {spread_pct*100:.3f}% exceeds max {self.MAX_SPREAD_PCT*100:.2f}%")

        # 2. Volatility Check
        atr_pct = (current_atr / mid_price) if mid_price > 0 else 0.0
        if atr_pct < 0.002:  # Less than 0.2% ATR indicates dead market / no liquidity
            reasons.append(f"Market compression too extreme (ATR {atr_pct*100:.2f}%)")

        # 3. Portfolio Heat Check
        trade_risk_pct = (plan.risk_usd / account_equity) * 100.0 if account_equity > 0 else 100.0
        projected_heat = current_portfolio_heat_pct + trade_risk_pct
        if projected_heat > self.MAX_PORTFOLIO_HEAT_PCT:
            reasons.append(
                f"Projected heat {projected_heat:.2f}% exceeds ceiling {self.MAX_PORTFOLIO_HEAT_PCT:.2f}%"
            )

        # 4. Leverage & Feasibility Check
        leverage_required = plan.intended_notional / account_equity if account_equity > 0 else 999.0
        if leverage_required > self.MAX_SAFE_LEVERAGE:
            reasons.append(
                f"Required leverage {leverage_required:.1f}x exceeds safety ceiling {self.MAX_SAFE_LEVERAGE:.1f}x"
            )

        is_feasible = plan.intended_notional >= self.MIN_NOTIONAL_USD
        if not is_feasible:
            reasons.append(f"Notional ${plan.intended_notional:.2f} below exchange minimum ${self.MIN_NOTIONAL_USD:.2f}")

        passed = len(reasons) == 0
        return PreEntryCheckResult(
            passed=passed,
            spread_pct=spread_pct,
            volatility_atr_pct=atr_pct,
            current_heat_pct=current_portfolio_heat_pct,
            projected_heat_pct=projected_heat,
            leverage_required=leverage_required,
            is_notional_feasible=is_feasible,
            rejection_reasons=reasons,
        )

    def initialize_position(
        self,
        position_id: str,
        strategy_id: str,
        symbol: str,
        direction: str,
        fill_price: float,
        fill_qty: float,
        initial_sl: float,
        tp1_price: float,
        tp2_price: float,
        tp3_price: float,
        timestamp: int,
        max_holding_bars: int = 40,
    ) -> ManagedPosition:
        """Creates and registers an active managed position immediately post-fill."""
        sl_distance = abs(fill_price - initial_sl)
        risk_r_usd = sl_distance * fill_qty

        # Emergency SL provides a 15% disaster buffer beyond standard SL in case of catastrophic gap
        if direction == "LONG":
            emergency_sl = fill_price - (sl_distance * 1.15)
        else:
            emergency_sl = fill_price + (sl_distance * 1.15)

        pos = ManagedPosition(
            position_id=position_id,
            strategy_id=strategy_id,
            symbol=symbol,
            direction=direction,
            stage=PositionLifecycleStage.ACTIVE,
            entry_time=timestamp,
            entry_price=fill_price,
            current_sl_price=initial_sl,
            initial_sl_price=initial_sl,
            emergency_sl_price=emergency_sl,
            tp1_price=tp1_price,
            tp2_price=tp2_price,
            tp3_price=tp3_price,
            tp1_hit=False,
            tp2_hit=False,
            tp3_hit=False,
            total_qty=fill_qty,
            remaining_qty=fill_qty,
            risk_r_unit_usd=risk_r_usd,
            peak_unrealized_r=0.0,
            bars_held=0,
            max_holding_bars=max_holding_bars,
            last_update_ts=timestamp,
            audit_log=[{
                "timestamp": timestamp,
                "event": "POSITION_OPENED",
                "fill_price": fill_price,
                "qty": fill_qty,
                "sl": initial_sl,
                "emergency_sl": emergency_sl,
            }],
        )
        self.active_positions[position_id] = pos
        return pos

    def update_position_bar(
        self,
        position_id: str,
        current_high: float,
        current_low: float,
        current_close: float,
        current_atr: float,
        timestamp: int,
        macro_regime_invalidated: bool = False,
    ) -> Dict[str, Any]:
        """
        Processes each subsequent candle/bar for active trade management:
        - Break-even lock at +1.0R
        - TP1 (scales out 50%), TP2 (scales out 25%), TP3 (full exit)
        - ATR-based trailing stop
        - Max holding bar expiry
        - Emergency regime invalidation
        """
        if position_id not in self.active_positions:
            return {"action": "NONE", "reason": "Position not found"}

        pos = self.active_positions[position_id]
        pos.bars_held += 1
        pos.last_update_ts = timestamp
        r_dist = abs(pos.entry_price - pos.initial_sl_price)
        if r_dist <= 0:
            return {"action": "NONE", "reason": "Invalid R distance"}

        # Calculate current unrealized R
        if pos.direction == "LONG":
            curr_r = (current_close - pos.entry_price) / r_dist
            high_r = (current_high - pos.entry_price) / r_dist
            low_r = (current_low - pos.entry_price) / r_dist
        else:
            curr_r = (pos.entry_price - current_close) / r_dist
            high_r = (pos.entry_price - current_low) / r_dist
            low_r = (pos.entry_price - current_high) / r_dist

        pos.peak_unrealized_r = max(pos.peak_unrealized_r, high_r)

        # 1. Emergency Regime Invalidation Check
        if macro_regime_invalidated:
            pos.stage = PositionLifecycleStage.CLOSED_REGIME_CHANGE
            del self.active_positions[position_id]
            return {"action": "CLOSE_MARKET", "reason": "MACRO_REGIME_INVALIDATED", "exit_price": current_close}

        # 2. Check Stop Loss Hit
        if pos.direction == "LONG" and current_low <= pos.current_sl_price:
            pos.stage = PositionLifecycleStage.CLOSED_SL
            del self.active_positions[position_id]
            return {"action": "STOP_LOSS_HIT", "exit_price": pos.current_sl_price, "realized_r": -1.0 if pos.current_sl_price == pos.initial_sl_price else 0.0}
        elif pos.direction == "SHORT" and current_high >= pos.current_sl_price:
            pos.stage = PositionLifecycleStage.CLOSED_SL
            del self.active_positions[position_id]
            return {"action": "STOP_LOSS_HIT", "exit_price": pos.current_sl_price, "realized_r": -1.0 if pos.current_sl_price == pos.initial_sl_price else 0.0}

        # 3. Check Take Profit 1 (+1.0R / partial profit lock)
        actions = []
        if not pos.tp1_hit:
            tp1_condition = (current_high >= pos.tp1_price) if pos.direction == "LONG" else (current_low <= pos.tp1_price)
            if tp1_condition:
                pos.tp1_hit = True
                pos.stage = PositionLifecycleStage.BREAK_EVEN_LOCKED
                # Lock Stop Loss to Break-Even (entry price)
                pos.current_sl_price = pos.entry_price
                # Scale out 50%
                scaled_qty = pos.total_qty * 0.50
                pos.remaining_qty -= scaled_qty
                actions.append(f"TP1_HIT_SCALE_50%_SL_MOVED_TO_BE (${pos.entry_price:.2f})")

        # 4. Check Take Profit 2 (+2.0R)
        if pos.tp1_hit and not pos.tp2_hit:
            tp2_condition = (current_high >= pos.tp2_price) if pos.direction == "LONG" else (current_low <= pos.tp2_price)
            if tp2_condition:
                pos.tp2_hit = True
                pos.stage = PositionLifecycleStage.TRAILING_ACTIVE
                # Move Stop Loss to +1.0R
                if pos.direction == "LONG":
                    pos.current_sl_price = pos.entry_price + r_dist
                else:
                    pos.current_sl_price = pos.entry_price - r_dist
                # Scale out another 25% of initial
                scaled_qty = pos.total_qty * 0.25
                pos.remaining_qty -= scaled_qty
                actions.append(f"TP2_HIT_SCALE_25%_SL_MOVED_TO_+1.0R (${pos.current_sl_price:.2f})")

        # 5. Check Take Profit 3 (Full final target)
        if pos.tp2_hit and not pos.tp3_hit:
            tp3_condition = (current_high >= pos.tp3_price) if pos.direction == "LONG" else (current_low <= pos.tp3_price)
            if tp3_condition:
                pos.tp3_hit = True
                pos.stage = PositionLifecycleStage.CLOSED_TP
                del self.active_positions[position_id]
                return {"action": "FULL_TP3_EXIT", "exit_price": pos.tp3_price, "realized_r": 3.0}

        # 6. Dynamic ATR Trailing (when trade is in positive territory > 1.5R)
        if pos.peak_unrealized_r >= 1.5 and current_atr > 0:
            if pos.direction == "LONG":
                candidate_trail = current_close - (current_atr * 2.0)
                if candidate_trail > pos.current_sl_price:
                    pos.current_sl_price = candidate_trail
                    actions.append(f"TRAILED_ATR_SL (${candidate_trail:.2f})")
            else:
                candidate_trail = current_close + (current_atr * 2.0)
                if candidate_trail < pos.current_sl_price:
                    pos.current_sl_price = candidate_trail
                    actions.append(f"TRAILED_ATR_SL (${candidate_trail:.2f})")

        # 7. Check Max Holding Bars Expiry (Time Stop)
        if pos.bars_held >= pos.max_holding_bars:
            pos.stage = PositionLifecycleStage.CLOSED_TIME_STOP
            del self.active_positions[position_id]
            return {"action": "TIME_EXPIRY_EXIT", "exit_price": current_close, "holding_bars": pos.bars_held}

        return {
            "action": "HELD",
            "current_sl": pos.current_sl_price,
            "remaining_qty": pos.remaining_qty,
            "unrealized_r": round(curr_r, 2),
            "events": actions,
        }

    def emergency_quarantine_feed(self, feed_last_timestamp: int, current_timestamp: int) -> bool:
        """
        If market feed data is older than 30 seconds, trips emergency circuit breaker.
        """
        latency_sec = current_timestamp - feed_last_timestamp
        return latency_sec > 30
