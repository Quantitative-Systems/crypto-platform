"""Unit tests for STRATA Autonomous Trading Agent and Research Evolution Engine."""
import pytest
from accounts.suitability_engine import TradingStyle
from execution.agent.research_evolution_engine import DriftSeverity, ResearchEvolutionEngine
from execution.agent.strata_autonomous_agent import AgentControlState, StrataAutonomousAgent


def test_autonomous_agent_control_cycle_and_suitability_filtering():
    agent = StrataAutonomousAgent(default_style=TradingStyle.SWING)

    # Initial state
    assert agent.control_state == AgentControlState.OBSERVING
    assert agent.current_style == TradingStyle.SWING

    # Run cycle
    report = agent.run_control_cycle(symbol="BTCUSDT", active_positions_count=1, current_portfolio_heat=0.01)
    assert report.market_health == "HEALTHY"
    assert "STRATA_KING_ENGINE" in report.selected_strategies
    assert report.positions_managed == 1
    assert report.portfolio_heat_pct == 0.01
    assert any("KING Core active" in a for a in report.action_log)

    # Change style to Scalping
    agent.set_trading_style(TradingStyle.SCALPING)
    scalp_report = agent.run_control_cycle()
    assert scalp_report.active_style == TradingStyle.SCALPING
    assert "STRATA_MOMENTUM_BREAKOUT" in scalp_report.selected_strategies

    # Pause trading
    agent.pause_trading("Operator test pause")
    assert agent.control_state == AgentControlState.PAUSED
    paused_report = agent.run_control_cycle()
    assert paused_report.market_health == "PAUSED"
    assert len(paused_report.selected_strategies) == 0

    # Resume trading
    agent.resume_trading()
    assert agent.control_state == AgentControlState.OBSERVING


def test_autonomous_agent_degradation_quarantine():
    agent = StrataAutonomousAgent()

    # Strategy initially active
    report1 = agent.run_control_cycle()
    assert "STRATA_TREND_PULLBACK" in report1.selected_strategies

    # Flag strategy degraded
    agent.flag_strategy_degraded("STRATA_TREND_PULLBACK", "Excessive slippage drag")

    # Next cycle filters out degraded strategy
    report2 = agent.run_control_cycle()
    assert "STRATA_TREND_PULLBACK" not in report2.selected_strategies


def test_research_evolution_engine_drift_and_offline_jobs():
    engine = ResearchEvolutionEngine()

    # Normal performance
    sev, msg = engine.evaluate_performance_drift(
        strategy_id="STRAT_1",
        recent_win_rate=0.55,
        baseline_win_rate=0.56,
        recent_expectancy=0.50,
        baseline_expectancy=0.52,
    )
    assert sev == DriftSeverity.NORMAL
    assert msg is None

    # Severe degradation
    sev, msg = engine.evaluate_performance_drift(
        strategy_id="STRAT_1",
        recent_win_rate=0.30,  # 26% WR drop
        baseline_win_rate=0.56,
        recent_expectancy=0.05,  # 0.47R drop
        baseline_expectancy=0.52,
    )
    assert sev == DriftSeverity.SEVERE_DEGRADATION
    assert "Severe performance collapse" in msg

    # Create offline research job
    job = engine.create_offline_research_job(
        strategy_id="STRAT_1",
        hypothesis="Investigate whether volatility compression filter mitigates regime drawdown",
        assets=["BTCUSDT"],
        timeframes=["4h", "1h"],
    )
    assert job.status == "PENDING_OFFLINE"
    assert len(engine.list_jobs()) == 1
