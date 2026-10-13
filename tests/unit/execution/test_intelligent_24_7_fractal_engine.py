"""Unit tests for the Intelligent 24/7/365 Fractal Engine."""
import asyncio
import pytest
from execution.intelligent_24_7_fractal_engine import IntelligentFractalEngine


@pytest.mark.asyncio
async def test_intelligent_fractal_engine_initialization():
    engine = IntelligentFractalEngine(
        symbols=["BTCUSDT", "ETHUSDT"],
        account_equity_usd=50_000.0,
        risk_per_trade_pct=0.01,
        max_portfolio_heat_pct=0.03,
        broker_mode="PAPER",
    )
    status = engine.get_portfolio_status()
    assert status["mode"] == "PAPER"
    assert status["account_equity_usd"] == 50_000.0
    assert status["active_positions_count"] == 0
    assert status["current_portfolio_heat_pct"] == 0.0
    assert "BTCUSDT" in status["symbols_monitored"]


@pytest.mark.asyncio
async def test_intelligent_fractal_engine_symbol_evaluation():
    engine = IntelligentFractalEngine(
        symbols=["BTCUSDT"],
        account_equity_usd=100_000.0,
        broker_mode="PAPER",
    )
    # Evaluate a tick with realistic price
    await engine.evaluate_symbol_tick("BTCUSDT", current_price=64000.0, timestamp_ms=1700000000000)
    status = engine.get_portfolio_status()
    assert status["account_equity_usd"] == 100_000.0
