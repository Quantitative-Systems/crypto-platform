"""Unit tests for King Engine Contract, invariants, and adapter execution."""
import pytest
from execution.king.king_engine_contract import (
    EXPECTED_KING_CONTRACT_HASH,
    KingEngineAdapter,
    KingEngineProtectionGuard,
)
from market_data.realtime.binance_ws_client import DataHealthStatus
from market_model.contracts import MarketState, TrendDirection


def test_king_engine_guard_contract_verification():
    guard = KingEngineProtectionGuard()
    status = guard.get_status()
    assert status.is_valid is True
    assert status.contract_hash == EXPECTED_KING_CONTRACT_HASH
    assert status.target_floor_r == 4.0
    assert status.max_trade_risk_pct == 0.01
    assert status.max_portfolio_heat_pct == 0.03
    assert status.real_capital_authorized_usd == 0.0
    assert status.is_live_locked is True


def test_king_engine_guard_invariant_checks():
    guard = KingEngineProtectionGuard()

    # Valid scenario
    ok, err = guard.verify_invariants(target_r=4.5, trade_risk=0.01, portfolio_heat=0.02, real_capital=0.0)
    assert ok is True
    assert err is None

    # Sub-4R target rejected
    ok, err = guard.verify_invariants(target_r=3.8, trade_risk=0.01, portfolio_heat=0.02, real_capital=0.0)
    assert ok is False
    assert "violates King floor" in err

    # Excessive trade risk rejected
    ok, err = guard.verify_invariants(target_r=4.5, trade_risk=0.015, portfolio_heat=0.02, real_capital=0.0)
    assert ok is False
    assert "exceeds King limit" in err

    # Excessive portfolio heat rejected
    ok, err = guard.verify_invariants(target_r=4.5, trade_risk=0.01, portfolio_heat=0.035, real_capital=0.0)
    assert ok is False
    assert "exceeds King limit" in err

    # Real capital unauthorized rejected
    ok, err = guard.verify_invariants(target_r=4.5, trade_risk=0.01, portfolio_heat=0.02, real_capital=100.0)
    assert ok is False
    assert "violates zero-capital gate" in err


from market_model.contracts import MarketState, TrendDirection, StructureSnapshot, PhaseSnapshot, MarketPhaseType


def test_king_engine_adapter_initialization_and_overview():
    adapter = KingEngineAdapter()
    assert adapter.name == "STRATA_KING_ENGINE"
    assert adapter.domain == "DOMAIN_A_KING"
    assert adapter.priority == 1

    states = {
        tf: MarketState(
            symbol="BTCUSDT",
            timestamp_ms=1000000,
            timeframe=tf,
            close_price=50000.0,
            structure=StructureSnapshot(external_trend=TrendDirection.BULLISH),
            phase=PhaseSnapshot(current_phase=MarketPhaseType.CONTINUATION),
        )
        for tf in ["1M", "1w", "1d", "4h", "1h", "15m", "3m"]
    }

    overview = adapter.get_market_structure_overview(states)
    assert overview["engine"] == "STRATA_KING_ENGINE"
    assert overview["status"] == "PROTECTED_CORE"
    assert "SET_1" in overview["timeframe_sets"]
    assert "SET_2" in overview["timeframe_sets"]
