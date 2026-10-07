"""Unit tests for STRATA Degradation to Research Candidate Pipeline."""
import tempfile
from pathlib import Path
import pytest
from validation.realtime_drift_monitor import DriftState, DriftStatusReport
from validation.research_candidate_pipeline import ResearchCandidatePipeline


def test_research_candidate_pipeline_emits_on_drift():
    with tempfile.TemporaryDirectory() as tmpdir:
        pipe = ResearchCandidatePipeline(candidates_dir=Path(tmpdir))

        # Stable report -> no candidate emitted
        stable_report = DriftStatusReport(
            timestamp_utc="2026-10-07T00:00:00Z",
            drift_state=DriftState.STABLE,
            sample_size=20,
            rolling_expectancy_r=0.75,
            rolling_profit_factor=3.8,
            rolling_win_rate=0.62,
            rolling_mean_confidence=0.63,
            max_drawdown_r=2.5,
        )
        res = pipe.inspect_and_emit(stable_report)
        assert res is None

        # Drift report -> candidate emitted & saved to disk
        drift_report = DriftStatusReport(
            timestamp_utc="2026-10-07T00:00:00Z",
            drift_state=DriftState.DRIFT,
            sample_size=25,
            rolling_expectancy_r=0.15,  # Substantial degradation
            rolling_profit_factor=1.4,
            rolling_win_rate=0.45,
            rolling_mean_confidence=0.61,
            max_drawdown_r=8.5,
        )
        proposal = pipe.inspect_and_emit(drift_report, execution_drag_bps=12.5)
        assert proposal is not None
        assert proposal.candidate_id.startswith("CAND_DRIFT_")
        assert proposal.drift_state == "DRIFT"
        assert proposal.governance_rule == "LIVE_STRATEGY_PARAMETERS_REMAIN_STRICTLY_FROZEN"

        # Check file was written to disk
        cand_files = list(Path(tmpdir).glob("*.json"))
        assert len(cand_files) == 1
