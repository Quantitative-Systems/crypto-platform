"""
Tests for Stress & Shock Simulation Lab.
"""

from risk_engine.stress_shock_lab import (
    StressShockLab,
    StressLabReport,
)


def test_stress_shock_lab_execution():
    lab = StressShockLab()
    report = lab.run_all_stress_scenarios(
        starting_equity_usd=10_000.0,
        active_positions_count=3,
        portfolio_heat_pct=2.50
    )

    assert isinstance(report, StressLabReport)
    assert report.total_scenarios_tested == 5
    assert report.scenarios_passed >= 4
    assert report.max_portfolio_stress_drawdown_pct < 15.0
    assert report.all_survived is True
    for sc in report.scenario_results:
        assert sc.post_shock_equity_usd > 0
        assert sc.margin_buffer_ratio > 1.0
