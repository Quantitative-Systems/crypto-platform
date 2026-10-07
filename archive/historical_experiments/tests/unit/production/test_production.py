"""
Unit tests for Product 07 — Production Service & Reliability.
Tests StateStore persistence, EODReconciler ledger auditing, and AlertManager formatting.
"""

import os
import pytest
import asyncio
from production.persistence.state_store import StateStore
from production.reconciliation.eod_reconciler import EODReconciler
from production.telemetry.alert_manager import AlertManager
from portfolio_engine.contracts.portfolio_state import PortfolioState
from execution_gateway.gateways.paper_gateway import PaperGateway


def test_state_store_persistence(tmp_path):
    db_file = str(tmp_path / "test_state.db")
    store = StateStore(db_path=db_file)
    
    # 1. Save state
    data = {"nav": 10500.0, "drawdown_pct": 0.02, "active_positions": {"pos_1": {"units": 1.5}}}
    store.save_state("portfolio_state", data)
    
    # 2. Reload state
    loaded = store.load_state("portfolio_state")
    assert loaded is not None
    assert loaded["nav"] == 10500.0
    assert loaded["drawdown_pct"] == 0.02
    assert loaded["active_positions"]["pos_1"]["units"] == 1.5
    
    # 3. Overwrite & reload
    data["nav"] = 11000.0
    store.save_state("portfolio_state", data)
    loaded2 = store.load_state("portfolio_state")
    assert loaded2["nav"] == 11000.0


def test_eod_reconciler_clean_match():
    async def _run():
        gateway = PaperGateway(initial_balance=10000.0)
        await gateway.connect()
        
        state = PortfolioState(nav=10000.0, cash_balance=10000.0, peak_nav=10000.0)
        report = await EODReconciler.audit(state, gateway)
        
        assert report.is_clean is True
        assert report.discrepancy_usd == 0.0
        assert len(report.position_mismatches) == 0

    asyncio.run(_run())


def test_eod_reconciler_discrepancy_detection():
    async def _run():
        gateway = PaperGateway(initial_balance=9500.0)  # Mismatched balance
        await gateway.connect()
        
        state = PortfolioState(nav=10000.0, cash_balance=10000.0, peak_nav=10000.0)
        report = await EODReconciler.audit(state, gateway)
        
        assert report.is_clean is False
        assert report.discrepancy_usd == 500.0

    asyncio.run(_run())


def test_alert_manager_formatting(capsys):
    am = AlertManager(enable_console=True)
    am.send_alert("INFO", "TEST_ALERT", "System functioning normally", {"status": "OK"})
    
    captured = capsys.readouterr()
    assert "TEST_ALERT" in captured.out
    assert "System functioning normally" in captured.out
    assert "OK" in captured.out
