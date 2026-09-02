"""
Product 04 — Research Laboratory: Immutable Trade Ledger & Account State
Records every state transition, simulated fill, friction cost, excursion metric,
regime classification, and equity curve point.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import json
import os


@dataclass
class SimulatedTrade:
    trade_id: str
    hypothesis_id: str
    symbol: str
    timeframe_set: str
    directional_permission: str  # PERMIT_LONG / PERMIT_SHORT
    setup_timestamp: int
    entry_timestamp: Optional[int] = None
    exit_timestamp: Optional[int] = None
    
    # Prices
    entry_price: float = 0.0
    fill_entry_price: float = 0.0
    initial_stop_price: float = 0.0
    current_stop_price: float = 0.0
    target_price: float = 0.0
    exit_price: Optional[float] = None
    
    # Sizing & Risk
    position_units: float = 0.0
    dollar_risk: float = 0.0
    raw_rr: float = 0.0
    realized_rr: Optional[float] = None
    realized_pnl: Optional[float] = None
    
    # Friction Breakdown
    entry_fee: float = 0.0
    exit_fee: float = 0.0
    entry_slippage_bps: float = 0.0
    exit_slippage_bps: float = 0.0
    funding_usd: float = 0.0
    total_friction_usd: float = 0.0
    
    # Lifecycle
    status: str = "PENDING_ENTRY"  # PENDING_ENTRY, ACTIVE, CLOSED, CANCELLED
    exit_reason: Optional[str] = None  # HTF_TP, MTF_STRUCTURAL_TRAIL, INITIAL_LTF_SL, TIMEOUT
    
    # Provenance, Metadata & Regimes
    trend_regime: str = "RANGE_CHOP"
    volatility_regime: str = "NORMAL_VOLATILITY"
    market_phase: str = "CONTINUATION"
    strategy_version: str = "v2.0-UNIFIED-CANONICAL-LOCKED"
    dataset_manifest_hash: str = ""
    experiment_id: str = "CANONICAL_MATRIX_EXP_001"
    rejection_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["direction"] = "LONG" if self.directional_permission == "PERMIT_LONG" else "SHORT"
        d["net_r"] = self.realized_rr if self.realized_rr is not None else 0.0
        d["net_pnl"] = self.realized_pnl if self.realized_pnl is not None else 0.0
        
        # Friction decomposition in R-multiples
        risk = self.dollar_risk if self.dollar_risk > 0 else 100.0
        d["fees_r"] = round((self.entry_fee + self.exit_fee) / risk, 4)
        d["slippage_r"] = round(((self.entry_slippage_bps + self.exit_slippage_bps) / 10000.0) * (self.fill_entry_price or self.entry_price) * self.position_units / risk, 4)
        d["funding_r"] = round(self.funding_usd / risk, 4)
        d["gross_r"] = round(d["net_r"] + d["fees_r"] + d["slippage_r"] + d["funding_r"], 4)
        
        # Duration attribution
        if self.exit_timestamp and self.entry_timestamp:
            d["duration_sec"] = max(0, self.exit_timestamp - self.entry_timestamp)
        else:
            d["duration_sec"] = 0
            
        # Excursion attribution (MFE / MAE in R-multiples)
        entry_p = self.fill_entry_price or self.entry_price
        risk_dist = abs(entry_p - self.initial_stop_price)
        if risk_dist > 0 and self.metadata:
            is_long = self.directional_permission == "PERMIT_LONG"
            mfe_p = self.metadata.get("mfe_price", entry_p)
            mae_p = self.metadata.get("mae_price", entry_p)
            if is_long:
                d["mfe_r"] = round((mfe_p - entry_p) / risk_dist, 4)
                d["mae_r"] = round((entry_p - mae_p) / risk_dist, 4)
            else:
                d["mfe_r"] = round((entry_p - mfe_p) / risk_dist, 4)
                d["mae_r"] = round((mae_p - entry_p) / risk_dist, 4)
        else:
            d["mfe_r"] = 0.0
            d["mae_r"] = 0.0
            
        prov = self.metadata.get("structural_provenance", {}) if self.metadata else {}
        d["htf_context"] = prov.get("htf_context") or ("PULLBACK" if "PULLBACK" in str(prov.get("htf_phase", "")) else "CONTINUATION")
            
        return d


class TradeLedger:
    """
    Stateful immutable ledger recording all trades and running account equity.
    """

    def __init__(self, initial_equity: float = 10000.0):
        self.initial_equity: float = initial_equity
        self.current_equity: float = initial_equity
        self.peak_equity: float = initial_equity
        self.max_drawdown_pct: float = 0.0
        
        self.trades: Dict[str, SimulatedTrade] = {}
        self.closed_trades: List[SimulatedTrade] = []
        self.equity_curve: List[Dict[str, Any]] = [
            {"timestamp": 0, "equity": initial_equity, "drawdown_pct": 0.0}
        ]

    def record_pending_trade(self, trade: SimulatedTrade):
        self.trades[trade.trade_id] = trade

    def activate_trade(self, trade_id: str, fill_price: float, timestamp: int, entry_fee: float, slippage_bps: float):
        trade = self.trades.get(trade_id)
        if not trade:
            return
        trade.status = "ACTIVE"
        trade.entry_timestamp = timestamp
        trade.fill_entry_price = fill_price
        trade.entry_fee = entry_fee
        trade.entry_slippage_bps = slippage_bps
        trade.total_friction_usd += entry_fee
        
        # Deduct entry fee from current equity
        self.current_equity -= entry_fee
        self._update_drawdown(timestamp)

    def update_trailing_stop(self, trade_id: str, new_stop: float):
        trade = self.trades.get(trade_id)
        if not trade:
            return
        is_long = trade.directional_permission == "PERMIT_LONG"
        # Stop can only tighten/protect profits, never widen
        if is_long and new_stop > trade.current_stop_price:
            trade.current_stop_price = new_stop
        elif not is_long and new_stop < trade.current_stop_price:
            trade.current_stop_price = new_stop

    def close_trade(
        self,
        trade_id: str,
        exit_price: float,
        exit_timestamp: int,
        exit_reason: str,
        exit_fee: float,
        slippage_bps: float
    ) -> Optional[SimulatedTrade]:
        trade = self.trades.get(trade_id)
        if not trade or trade.status != "ACTIVE":
            return None
            
        trade.status = "CLOSED"
        trade.exit_price = exit_price
        trade.exit_timestamp = exit_timestamp
        trade.exit_reason = exit_reason
        trade.exit_fee = exit_fee
        trade.exit_slippage_bps = slippage_bps
        trade.total_friction_usd += exit_fee
        
        # Calculate Realized PnL
        is_long = trade.directional_permission == "PERMIT_LONG"
        if is_long:
            gross_pnl = (exit_price - trade.fill_entry_price) * trade.position_units
        else:
            gross_pnl = (trade.fill_entry_price - exit_price) * trade.position_units
            
        net_pnl = gross_pnl - exit_fee
        trade.realized_pnl = net_pnl
        
        # Realized R-Multiple
        if trade.dollar_risk > 0:
            trade.realized_rr = net_pnl / trade.dollar_risk
        else:
            trade.realized_rr = 0.0
            
        self.current_equity += net_pnl
        self._update_drawdown(exit_timestamp)
        
        self.closed_trades.append(trade)
        return trade

    def _update_drawdown(self, timestamp: int):
        if self.current_equity > self.peak_equity:
            self.peak_equity = self.current_equity
            
        current_dd = 0.0
        if self.peak_equity > 0:
            current_dd = max(0.0, (self.peak_equity - self.current_equity) / self.peak_equity)
            
        if current_dd > self.max_drawdown_pct:
            self.max_drawdown_pct = current_dd
            
        self.equity_curve.append({
            "timestamp": timestamp,
            "equity": self.current_equity,
            "drawdown_pct": current_dd
        })

    def get_active_trades(self) -> List[SimulatedTrade]:
        return [t for t in self.trades.values() if t.status == "ACTIVE"]

    def get_pending_trades(self) -> List[SimulatedTrade]:
        return [t for t in self.trades.values() if t.status == "PENDING_ENTRY"]

    def export_canonical_trade_ledger(self, filepath: Optional[str] = None) -> str:
        """
        Exports the complete closed trade ledger to an immutable JSON artifact.
        """
        if filepath is None:
            filepath = os.path.join(os.path.dirname(__file__), "..", "..", "scratch", "canonical_trade_ledger.json")
            
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        data = {
            "total_trades": len(self.closed_trades),
            "initial_equity": self.initial_equity,
            "final_equity": round(self.current_equity, 2),
            "net_profit_usd": round(self.current_equity - self.initial_equity, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct * 100.0, 2),
            "trades": [t.to_dict() for t in self.closed_trades]
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        return filepath
