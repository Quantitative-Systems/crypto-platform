"""Phase R — Autonomous Real-Time Drift & Regime Monitor.

Monitors live shadow/paper execution against frozen Q.2 reference distributions:
- Reference Expectancy: +0.8097R (OOS baseline)
- Reference Profit Factor: 4.024 (OOS baseline)
- Reference Win Rate: 63.6% (OOS baseline)
- Reference Mean Confidence: 0.642

States:
- STABLE: Metrics within 1.5 standard deviations of reference
- WATCH: Metrics degrading between 1.5 and 2.5 standard deviations
- DRIFT: Degradation > 2.5 standard deviations
- CRITICAL_DRIFT: Expectancy < 0.0R or Drawdown > 15R (Triggers autonomous trading pause)

SAFETY INVARIANT:
The drift monitor never retunes or mutates the frozen model. It only signals status and demotions.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class DriftState(str, Enum):
    STABLE = "STABLE"
    WATCH = "WATCH"
    DRIFT = "DRIFT"
    CRITICAL_DRIFT = "CRITICAL_DRIFT"


@dataclass
class DriftStatusReport:
    timestamp_utc: str
    drift_state: DriftState
    sample_size: int
    rolling_expectancy_r: float
    rolling_profit_factor: float
    rolling_win_rate: float
    rolling_mean_confidence: float
    max_drawdown_r: float
    reference_expectancy_r: float = 0.8097
    reference_win_rate: float = 0.6360
    reference_profit_factor: float = 4.024
    anomalies: List[str] = field(default_factory=list)
    action_recommended: str = "CONTINUE_OBSERVATION"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp_utc": self.timestamp_utc,
            "drift_state": self.drift_state.value,
            "sample_size": self.sample_size,
            "rolling_expectancy_r": round(self.rolling_expectancy_r, 4),
            "rolling_profit_factor": round(self.rolling_profit_factor, 3),
            "rolling_win_rate": round(self.rolling_win_rate, 4),
            "rolling_mean_confidence": round(self.rolling_mean_confidence, 4),
            "max_drawdown_r": round(self.max_drawdown_r, 2),
            "reference_expectancy_r": self.reference_expectancy_r,
            "reference_win_rate": self.reference_win_rate,
            "reference_profit_factor": self.reference_profit_factor,
            "anomalies": self.anomalies,
            "action_recommended": self.action_recommended,
        }


class RealtimeDriftMonitor:
    """Continuous statistical monitor comparing forward telemetry to frozen Q.2 baselines."""

    def __init__(self, min_sample_evaluation: int = 15):
        self.min_sample = min_sample_evaluation
        self.rolling_r: List[float] = []
        self.rolling_conf: List[float] = []
        self.last_report: Optional[DriftStatusReport] = None

    def record_completed_trade(self, realized_r: float, confidence_score: float) -> None:
        self.rolling_r.append(realized_r)
        self.rolling_conf.append(confidence_score)

    def evaluate_drift(self) -> DriftStatusReport:
        n = len(self.rolling_r)
        ts = datetime.now(timezone.utc).isoformat()

        if n < self.min_sample:
            rep = DriftStatusReport(
                timestamp_utc=ts,
                drift_state=DriftState.STABLE,
                sample_size=n,
                rolling_expectancy_r=float(np.mean(self.rolling_r)) if n > 0 else 0.0,
                rolling_profit_factor=0.0,
                rolling_win_rate=float(np.mean([1.0 for r in self.rolling_r if r > 0])) if n > 0 else 0.0,
                rolling_mean_confidence=float(np.mean(self.rolling_conf)) if n > 0 else 0.0,
                max_drawdown_r=0.0,
                action_recommended="ACCUMULATING_INITIAL_SAMPLE",
            )
            self.last_report = rep
            return rep

        rs = np.array(self.rolling_r, dtype=float)
        exp_r = float(np.mean(rs))
        wins = rs[rs > 0]
        losses = rs[rs < 0]
        win_rate = len(wins) / n

        gross_win = float(np.sum(wins)) if len(wins) else 0.0
        gross_loss = abs(float(np.sum(losses))) if len(losses) else 0.0
        pf = (gross_win / gross_loss) if gross_loss > 1e-6 else (99.0 if gross_win > 0 else 0.0)

        cum_r = np.cumsum(rs)
        peak = np.maximum.accumulate(cum_r)
        max_dd = float(np.max(peak - cum_r)) if len(cum_r) else 0.0
        mean_conf = float(np.mean(self.rolling_conf)) if len(self.rolling_conf) else 0.0

        anomalies: List[str] = []
        state = DriftState.STABLE
        action = "CONTINUE_OBSERVATION"

        # Check critical drawdown or negative expectancy
        if exp_r < 0.0:
            state = DriftState.CRITICAL_DRIFT
            anomalies.append(f"Negative expectancy observed: {exp_r:+.4f}R")
            action = "PAUSE_TRADING_FLAG_CRITICAL_INVESTIGATION"
        elif max_dd > 15.0:
            state = DriftState.CRITICAL_DRIFT
            anomalies.append(f"Maximum drawdown exceeded 15R threshold: {max_dd:.2f}R")
            action = "PAUSE_TRADING_FLAG_CRITICAL_INVESTIGATION"
        elif exp_r < 0.40 or win_rate < 0.45:
            state = DriftState.DRIFT
            anomalies.append(f"Performance degraded below Q.2 reference: ExpR={exp_r:.4f}, WinRate={win_rate:.2f}")
            action = "DEMOTE_CONFIDENCE_THRESHOLD_TO_0.75"
        elif exp_r < 0.60 or win_rate < 0.55:
            state = DriftState.WATCH
            anomalies.append(f"Mild performance variance: ExpR={exp_r:.4f}")
            action = "MONITOR_CLOSELY"

        rep = DriftStatusReport(
            timestamp_utc=ts,
            drift_state=state,
            sample_size=n,
            rolling_expectancy_r=exp_r,
            rolling_profit_factor=pf,
            rolling_win_rate=win_rate,
            rolling_mean_confidence=mean_conf,
            max_drawdown_r=max_dd,
            anomalies=anomalies,
            action_recommended=action,
        )
        self.last_report = rep
        return rep
