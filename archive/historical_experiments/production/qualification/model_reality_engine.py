"""
Quantitative Crypto Platform (QCP) — Model-vs-Reality (Execution Reality Delta) Engine.

Measures discrepancies between theoretical strategy assumptions and live market reality:
1. Entry Reality: Expected entry vs observed market vs simulated executable entry.
2. Slippage Reality: Expected slippage vs observed slippage (Slippage Model Error).
3. Friction Reality: Predicted friction bps vs observed friction bps (Friction Model Error).
4. R-Realization Delta: Expected theoretical gross R vs realized net R.
5. Rolling Expectancy Decay: Forward rolling expectancy compared to historical backtest baseline (+0.611R).
6. Reality Gap Alerts: Triggered when friction or slippage models underestimate real-world market costs.
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any, Tuple
import numpy as np


@dataclass
class TradeRealityDelta:
    trade_id: str
    symbol: str
    direction: str
    expected_entry_price: float
    observed_market_price: float
    simulated_executable_entry: float
    expected_slippage_bps: float
    observed_slippage_bps: float
    slippage_model_error_bps: float
    expected_friction_bps: float
    observed_friction_bps: float
    friction_model_error_bps: float
    expected_gross_r: float
    realized_net_r: float
    r_realization_delta: float
    holding_seconds: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ModelRealitySummary:
    total_trades_analyzed: int
    avg_slippage_error_bps: float
    avg_friction_error_bps: float
    avg_r_realization_delta: float
    backtest_baseline_expectancy_r: float
    forward_observed_expectancy_r: float
    expectancy_decay_pct: float
    backtest_win_rate_pct: float
    forward_win_rate_pct: float
    win_rate_decay_pct: float
    total_observed_friction_usd: float
    alerts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_trades_analyzed": self.total_trades_analyzed,
            "avg_slippage_error_bps": round(self.avg_slippage_error_bps, 2),
            "avg_friction_error_bps": round(self.avg_friction_error_bps, 2),
            "avg_r_realization_delta": round(self.avg_r_realization_delta, 4),
            "backtest_baseline_expectancy_r": round(self.backtest_baseline_expectancy_r, 4),
            "forward_observed_expectancy_r": round(self.forward_observed_expectancy_r, 4),
            "expectancy_decay_pct": round(self.expectancy_decay_pct, 2),
            "backtest_win_rate_pct": round(self.backtest_win_rate_pct, 2),
            "forward_win_rate_pct": round(self.forward_win_rate_pct, 2),
            "win_rate_decay_pct": round(self.win_rate_decay_pct, 2),
            "total_observed_friction_usd": round(self.total_observed_friction_usd, 2),
            "alerts": self.alerts,
        }


class ModelVsRealityEngine:
    """
    Analyzes telemetry streams to continuously calculate the Execution Reality Delta.
    """

    # Institutional Alert Thresholds
    MAX_FRICTION_MODEL_ERROR_BPS = 3.0   # Alert if observed friction exceeds model by > 3 bps
    MAX_SLIPPAGE_MODEL_ERROR_BPS = 5.0   # Alert if observed slippage exceeds model by > 5 bps
    MAX_EXPECTANCY_DECAY_PCT = -30.0     # Alert if forward expectancy falls > 30% below backtest

    @classmethod
    def evaluate_trade(
        cls,
        trade: Dict[str, Any],
        expected_entry_slippage_bps: float = 2.0,
        expected_exit_slippage_bps: float = 5.0,
        expected_entry_fee_bps: float = 2.0,
        expected_exit_fee_bps: float = 5.0,
    ) -> TradeRealityDelta:
        """
        Calculates execution delta for a single completed trade telemetry record.
        """
        trade_id = str(trade.get("trade_id", "UNKNOWN"))
        symbol = str(trade.get("symbol", "UNKNOWN"))
        direction = str(trade.get("direction", "BUY"))

        exp_entry = float(trade.get("expected_entry_price", 0.0))
        exec_entry = float(trade.get("executed_entry_price", exp_entry))
        obs_market = float(trade.get("observed_market_price", exp_entry))

        entry_slip_bps = float(trade.get("entry_slippage_bps", 0.0))
        exit_slip_bps = float(trade.get("exit_slippage_bps", 0.0))
        obs_slip_bps = entry_slip_bps + exit_slip_bps
        exp_slip_bps = expected_entry_slippage_bps + expected_exit_slippage_bps
        slip_error_bps = obs_slip_bps - exp_slip_bps

        notional = float(trade.get("position_notional_usd", 100.0))
        fric_usd = float(trade.get("total_friction_usd", 0.0))
        obs_fric_bps = (fric_usd / notional * 10000.0) if notional > 0 else 0.0
        exp_fric_bps = exp_slip_bps + expected_entry_fee_bps + expected_exit_fee_bps
        fric_error_bps = obs_fric_bps - exp_fric_bps

        gross_r = float(trade.get("gross_r", 0.0))
        net_r = float(trade.get("net_r", gross_r))
        r_delta = net_r - gross_r

        holding_sec = int(trade.get("holding_seconds", 0))

        return TradeRealityDelta(
            trade_id=trade_id,
            symbol=symbol,
            direction=direction,
            expected_entry_price=exp_entry,
            observed_market_price=obs_market,
            simulated_executable_entry=exec_entry,
            expected_slippage_bps=exp_slip_bps,
            observed_slippage_bps=obs_slip_bps,
            slippage_model_error_bps=slip_error_bps,
            expected_friction_bps=exp_fric_bps,
            observed_friction_bps=obs_fric_bps,
            friction_model_error_bps=fric_error_bps,
            expected_gross_r=gross_r,
            realized_net_r=net_r,
            r_realization_delta=r_delta,
            holding_seconds=holding_sec,
        )

    @classmethod
    def audit_reality_gap(
        cls,
        trades: List[Dict[str, Any]],
        backtest_expectancy_r: float = 0.6107,
        backtest_win_rate: float = 0.7014,
    ) -> ModelRealitySummary:
        """
        Performs aggregate reality gap analysis across a sequence of trades.
        """
        n = len(trades)
        if n == 0:
            return ModelRealitySummary(
                total_trades_analyzed=0,
                avg_slippage_error_bps=0.0,
                avg_friction_error_bps=0.0,
                avg_r_realization_delta=0.0,
                backtest_baseline_expectancy_r=backtest_expectancy_r,
                forward_observed_expectancy_r=0.0,
                expectancy_decay_pct=0.0,
                backtest_win_rate_pct=backtest_win_rate * 100.0,
                forward_win_rate_pct=0.0,
                win_rate_decay_pct=0.0,
                total_observed_friction_usd=0.0,
                alerts=["NO_FORWARD_TRADES_AVAILABLE"],
            )

        deltas = [cls.evaluate_trade(t) for t in trades]

        avg_slip_error = float(np.mean([d.slippage_model_error_bps for d in deltas]))
        avg_fric_error = float(np.mean([d.friction_model_error_bps for d in deltas]))
        avg_r_delta = float(np.mean([d.r_realization_delta for d in deltas]))
        total_friction_usd = sum(float(t.get("total_friction_usd", 0.0)) for t in trades)

        net_rs = [d.realized_net_r for d in deltas]
        forward_exp_r = float(np.mean(net_rs))
        wins = [r for r in net_rs if r > 0]
        forward_wr = len(wins) / n

        exp_decay_pct = (
            ((forward_exp_r - backtest_expectancy_r) / backtest_expectancy_r) * 100.0
            if abs(backtest_expectancy_r) > 1e-6
            else 0.0
        )
        wr_decay_pct = (
            ((forward_wr - backtest_win_rate) / backtest_win_rate) * 100.0
            if backtest_win_rate > 1e-6
            else 0.0
        )

        alerts = []
        if avg_fric_error > cls.MAX_FRICTION_MODEL_ERROR_BPS:
            alerts.append(
                f"FRICTION_MODEL_UNDERESTIMATING_COST: Observed friction exceeds model by +{avg_fric_error:.2f} bps"
            )
        if avg_slip_error > cls.MAX_SLIPPAGE_MODEL_ERROR_BPS:
            alerts.append(
                f"SLIPPAGE_SPIKE_DETECTED: Observed slippage exceeds expected model by +{avg_slip_error:.2f} bps"
            )
        if exp_decay_pct < cls.MAX_EXPECTANCY_DECAY_PCT:
            alerts.append(
                f"SUBSTANTIAL_ALPHA_DECAY: Forward expectancy decay is {exp_decay_pct:.1f}% (threshold {cls.MAX_EXPECTANCY_DECAY_PCT:.1f}%)"
            )

        return ModelRealitySummary(
            total_trades_analyzed=n,
            avg_slippage_error_bps=avg_slip_error,
            avg_friction_error_bps=avg_fric_error,
            avg_r_realization_delta=avg_r_delta,
            backtest_baseline_expectancy_r=backtest_expectancy_r,
            forward_observed_expectancy_r=forward_exp_r,
            expectancy_decay_pct=exp_decay_pct,
            backtest_win_rate_pct=backtest_win_rate * 100.0,
            forward_win_rate_pct=forward_wr * 100.0,
            win_rate_decay_pct=wr_decay_pct,
            total_observed_friction_usd=total_friction_usd,
            alerts=alerts,
        )
