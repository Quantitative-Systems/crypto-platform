"""STRATA Digital Trading Platform — Degradation to Research Candidate Pipeline.

When the real-time drift monitor or execution auditor detects statistical degradation,
slippage expansion, or structural regime changes:
1. It creates a structured, immutable ResearchCandidate file in research/candidates/.
2. It logs forensic divergence data for offline laboratory investigation.
3. CRITICAL INVARIANT: It NEVER alters or retunes live/paper strategy logic autonomously.
   Strategy parameters remain strictly frozen. Live code modification requires the complete
   offline scientific research lifecycle.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from notifications.alert_router import ALERTS, AlertCategory, AlertSeverity
from validation.realtime_drift_monitor import DriftState, DriftStatusReport

logger = logging.getLogger(__name__)

DEFAULT_CANDIDATES_DIR = Path(__file__).resolve().parent.parent / "research" / "candidates"


@dataclass
class ResearchCandidateProposal:
    candidate_id: str
    created_at_utc: str
    trigger_reason: str
    drift_state: str
    sample_size: int
    observed_metrics: Dict[str, Any]
    reference_metrics: Dict[str, Any]
    statistical_divergence: Dict[str, Any]
    proposed_offline_hypotheses: List[str]
    status: str = "QUEUED_FOR_OFFLINE_STUDY"
    governance_rule: str = "LIVE_STRATEGY_PARAMETERS_REMAIN_STRICTLY_FROZEN"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ResearchCandidatePipeline:
    """Manages the creation of offline research study proposals from forward observation."""

    def __init__(self, candidates_dir: Optional[Path] = None):
        self.candidates_dir = candidates_dir or DEFAULT_CANDIDATES_DIR
        self.candidates_dir.mkdir(parents=True, exist_ok=True)
        self._processed_triggers: set = set()

    def inspect_and_emit(
        self,
        drift_report: DriftStatusReport,
        execution_drag_bps: float = 0.0,
    ) -> Optional[ResearchCandidateProposal]:
        """Inspect drift report; generate research proposal if degradation is certified."""
        if drift_report.drift_state not in (DriftState.DRIFT, DriftState.CRITICAL_DRIFT):
            return None

        # Prevent duplicate candidate spam within same sample size
        trigger_key = f"{drift_report.drift_state.value}_{drift_report.sample_size}"
        if trigger_key in self._processed_triggers:
            return None

        self._processed_triggers.add(trigger_key)

        cand_id = f"CAND_DRIFT_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4].upper()}"
        observed = {
            "rolling_expectancy_r": drift_report.rolling_expectancy_r,
            "rolling_profit_factor": drift_report.rolling_profit_factor,
            "rolling_win_rate": drift_report.rolling_win_rate,
            "rolling_mean_confidence": drift_report.rolling_mean_confidence,
            "max_drawdown_r": drift_report.max_drawdown_r,
            "execution_drag_bps": execution_drag_bps,
        }
        reference = {
            "expectancy_r": drift_report.reference_expectancy_r,
            "win_rate": drift_report.reference_win_rate,
            "profit_factor": drift_report.reference_profit_factor,
        }
        divergence = {
            "delta_expectancy_r": round(drift_report.rolling_expectancy_r - drift_report.reference_expectancy_r, 4),
            "delta_win_rate": round(drift_report.rolling_win_rate - drift_report.reference_win_rate, 4),
            "delta_pf": round(drift_report.rolling_profit_factor - drift_report.reference_profit_factor, 3),
        }

        hypotheses = [
            f"Investigate HTF-MTF structural alignment shift under anomalous volatility regime.",
            f"Audit whether 15m adverse intrabar friction expanded beyond reference assumptions ({execution_drag_bps:.1f} bps drag).",
            f"Evaluate whether candidate demotion to Set 2/3 macro-only windows restores baseline expectancy.",
        ]

        proposal = ResearchCandidateProposal(
            candidate_id=cand_id,
            created_at_utc=datetime.now(timezone.utc).isoformat(),
            trigger_reason=f"Observed {drift_report.drift_state.value} degradation across {drift_report.sample_size} forward trades.",
            drift_state=drift_report.drift_state.value,
            sample_size=drift_report.sample_size,
            observed_metrics=observed,
            reference_metrics=reference,
            statistical_divergence=divergence,
            proposed_offline_hypotheses=hypotheses,
        )

        # Write to research/candidates/
        out_file = self.candidates_dir / f"{cand_id}.json"
        try:
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(proposal.to_dict(), f, indent=2)
            logger.warning(
                f"[RESEARCH PIPELINE] Research candidate queued: {cand_id}. "
                f"File: {out_file.name}. LIVE LOGIC REMAINS FROZEN."
            )
        except Exception as e:
            logger.error(f"Failed to persist research candidate: {e}")

        # Emit alert
        ALERTS.emit(
            severity=AlertSeverity.WARNING if drift_report.drift_state == DriftState.DRIFT else AlertSeverity.CRITICAL,
            category=AlertCategory.DRIFT,
            title=f"Research Candidate Generated: {cand_id}",
            message=f"Forward drift detected ({drift_report.drift_state.value}). Proposal logged for offline research.",
            metadata={"candidate_id": cand_id, "divergence": divergence},
        )

        return proposal


# Global singleton
RESEARCH_PIPELINE = ResearchCandidatePipeline()
