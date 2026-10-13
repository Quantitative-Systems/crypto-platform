"""Unit tests for the Self-Evolving Autonomous Quantitative Fund Daemon."""
import asyncio
import pytest
from execution.autonomous_self_evolving_daemon import SelfEvolvingFundDaemon


@pytest.mark.asyncio
async def test_self_evolving_fund_daemon_initialization():
    daemon = SelfEvolvingFundDaemon(
        active_symbols=["BTCUSDT", "ETHUSDT"],
        account_equity_usd=100_000.0,
        broker_mode="PAPER",
        research_interval_seconds=3600,
    )
    status = daemon.trading_engine.get_portfolio_status()
    assert status["mode"] == "PAPER"
    assert status["account_equity_usd"] == 100_000.0
    assert "BTCUSDT" in daemon.active_symbols


@pytest.mark.asyncio
async def test_self_evolving_fund_daemon_research_cycle():
    daemon = SelfEvolvingFundDaemon(
        active_symbols=["BTCUSDT"],
        account_equity_usd=100_000.0,
        broker_mode="PAPER",
    )
    # Run 1 single research discovery cycle with 1 symbol
    await daemon.run_autonomous_research_cycle(max_scan_symbols=1)
    registry = daemon.load_active_registry()
    assert isinstance(registry, dict)
