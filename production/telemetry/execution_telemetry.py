"""
Quantitative Crypto Platform (QCP) — Forward Execution Telemetry Engine.

Captures immutable, granular trade lifecycle and execution telemetry for comparison
between expected and realized execution quality, slippage drift, and attribution.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
import os
from typing import Dict, Any, List, Optional


@dataclass
class TradeTelemetryRecord:
    """Immutable execution telemetry record for a single completed trade."""
    trade_id: str
    strategy_id: str
    symbol: str
    timeframe_set: int
    direction: str                     # "BUY" (Long) or "SELL" (Short)
    entry_timestamp: int
    exit_timestamp: int
    holding_bars: int
    holding_seconds: int

    # Price execution and friction
    expected_entry_price: float
    executed_entry_price: float
    entry_slippage_bps: float
    entry_fee_usd: float

    expected_exit_price: float
    executed_exit_price: float
    exit_slippage_bps: float
    exit_fee_usd: float

    position_units: float
    position_notional_usd: float
    initial_risk_usd: float

    # Realized outcomes
    exit_reason: str                   # "SL_HIT", "TP_HIT", "BREAKEVEN_TRAIL", "TIME_STOP", etc.
    gross_pnl_usd: float
    total_friction_usd: float
    net_pnl_usd: float

    gross_r: float
    friction_r: float
    net_r: float

    # Context & Attribution
    market_regime: str                 # "BULL_TREND", "BEAR_TREND", "RANGE_BOUND", etc.
    peak_unrealized_r: float           # Maximum Favorable Excursion (MFE)
    max_adverse_r: float               # Maximum Adverse Excursion (MAE)
    portfolio_heat_at_entry_pct: float
    breakeven_triggered: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExecutionTelemetryLogger:
    """
    Appends execution records to an immutable JSONL log file and in-memory buffer.
    Guarantees no records are overwritten.
    """

    def __init__(self, log_dir: Optional[str] = None):
        if log_dir is None:
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            log_dir = os.path.join(base, "research", "results", "telemetry")
        os.makedirs(log_dir, exist_ok=True)
        self.log_dir = log_dir
        self.log_file = os.path.join(log_dir, "forward_execution_telemetry.jsonl")
        self.records: List[TradeTelemetryRecord] = []
        self.rejection_events: List[Dict[str, Any]] = []

    def record_trade(self, record: TradeTelemetryRecord) -> None:
        """Appends trade telemetry record."""
        self.records.append(record)
        with open(self.log_file, "a") as f:
            f.write(json.dumps(record.to_dict()) + "\n")

    def record_rejection(
        self,
        strategy_id: str,
        symbol: str,
        timestamp: int,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Logs trade rejections (e.g. risk firewall, portfolio heat, correlation limit)."""
        entry = {
            "timestamp": timestamp,
            "strategy_id": strategy_id,
            "symbol": symbol,
            "event": "TRADE_REJECTED",
            "reason": reason,
            "metadata": metadata or {},
            "logged_at": datetime.now(timezone.utc).isoformat(),
        }
        self.rejection_events.append(entry)
        rej_file = os.path.join(self.log_dir, "rejection_telemetry.jsonl")
        with open(rej_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_summary_metrics(self) -> Dict[str, Any]:
        """Calculates aggregate execution quality and performance metrics."""
        if not self.records:
            return {"total_trades": 0, "net_r": 0.0, "expectancy_r": 0.0}

        n = len(self.records)
        net_rs = [r.net_r for r in self.records]
        wins = [r for r in self.records if r.net_r > 0]
        losses = [r for r in self.records if r.net_r < 0]

        total_net_r = sum(net_rs)
        exp_r = total_net_r / n
        win_rate = len(wins) / n
        win_r_sum = sum(w.net_r for w in wins)
        loss_r_sum = abs(sum(l.net_r for l in losses))
        profit_factor = (win_r_sum / loss_r_sum) if loss_r_sum > 0 else float("inf")

        avg_friction_r = sum(r.friction_r for r in self.records) / n
        avg_entry_slip_bps = sum(r.entry_slippage_bps for r in self.records) / n
        avg_exit_slip_bps = sum(r.exit_slippage_bps for r in self.records) / n

        return {
            "total_trades": n,
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": round(win_rate, 4),
            "profit_factor": round(profit_factor, 4),
            "net_r": round(total_net_r, 4),
            "expectancy_r": round(exp_r, 4),
            "avg_friction_r": round(avg_friction_r, 4),
            "avg_entry_slippage_bps": round(avg_entry_slip_bps, 2),
            "avg_exit_slippage_bps": round(avg_exit_slip_bps, 2),
            "total_rejections": len(self.rejection_events),
        }
