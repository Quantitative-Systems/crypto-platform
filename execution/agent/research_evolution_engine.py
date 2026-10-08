"""STRATA — Research Evolution Engine (Controlled Self-Improvement).

Observes execution metrics, detects statistical degradation and regime drift,
generates research hypotheses, and spawns offline backtest jobs.

CRITICAL ARCHITECTURAL BOUNDARY:
The Research Evolution Engine CANNOT automatically rewrite or deploy live trading logic.
Any promotion requires:
RESEARCH → OOS → ADVERSARIAL → ROBUSTNESS → PAPER → FORWARD → QUALIFICATION → EXPLICIT AUTHORIZATION.
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DriftSeverity(str, Enum):
    NORMAL = "NORMAL"
    MILD_DRIFT = "MILD_DRIFT"
    SEVERE_DEGRADATION = "SEVERE_DEGRADATION"


@dataclass
class ResearchJob:
    job_id: str
    target_strategy: str
    hypothesis: str
    assets: List[str]
    timeframes: List[str]
    created_at_utc: str
    status: str = "PENDING_OFFLINE"  # PENDING_OFFLINE, RUNNING, COMPLETED, REJECTED
    findings: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ResearchEvolutionEngine:
    """
    Monitors running strategy performance and coordinates offline self-improvement.
    """

    def __init__(self):
        self._research_jobs: List[ResearchJob] = []

    def evaluate_performance_drift(
        self,
        strategy_id: str,
        recent_win_rate: float,
        baseline_win_rate: float,
        recent_expectancy: float,
        baseline_expectancy: float,
    ) -> Tuple[DriftSeverity, Optional[str]]:
        """
        Detects whether recent forward performance has drifted significantly below baseline.
        """
        # Statistical drift threshold
        exp_drop = baseline_expectancy - recent_expectancy
        wr_drop = baseline_win_rate - recent_win_rate

        if exp_drop > 0.40 or wr_drop > 0.20:
            msg = f"Severe performance collapse: Expectancy drop={exp_drop:.2f}R, WR drop={wr_drop*100:.1f}%"
            logger.warning(f"Strategy {strategy_id}: {msg}")
            return DriftSeverity.SEVERE_DEGRADATION, msg
        elif exp_drop > 0.20 or wr_drop > 0.10:
            msg = f"Mild drift detected: Expectancy drop={exp_drop:.2f}R"
            return DriftSeverity.MILD_DRIFT, msg

        return DriftSeverity.NORMAL, None

    def create_offline_research_job(
        self,
        strategy_id: str,
        hypothesis: str,
        assets: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
    ) -> ResearchJob:
        """
        Creates an offline research exploration job without modifying live trading.
        """
        job = ResearchJob(
            job_id=f"RES_{uuid.uuid4().hex[:10].upper()}",
            target_strategy=strategy_id,
            hypothesis=hypothesis,
            assets=assets or ["BTCUSDT", "ETHUSDT"],
            timeframes=timeframes or ["1d", "4h", "15m"],
            created_at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            status="PENDING_OFFLINE",
        )
        self._research_jobs.append(job)
        logger.info(f"Spawned offline research job {job.job_id} for strategy {strategy_id}: '{hypothesis}'")
        return job

    def list_jobs(self) -> List[ResearchJob]:
        return list(self._research_jobs)
