"""
Integration Test: End-to-End 24/7/365 Autonomous Trading Loop.
Verifies the complete production pipeline:
P01 Market Intelligence -> Alpha Regime Filter -> P02 Strategy -> P03 Risk -> P05 Portfolio -> P06 Paper Gateway -> P07 Persistence & EOD Audit.
"""

import os
import pytest
import asyncio
from market_data.warehouse_loader import WarehouseLoader
from execution_gateway.gateways.paper_gateway import PaperGateway
from production.live_trader import LiveTradingEngine
from production.persistence.state_store import StateStore


def test_24_7_live_trading_loop_end_to_end(tmp_path):
    async def _run():
        db_path = str(tmp_path / "live_trading_test.db")
        gateway = PaperGateway(initial_balance=10000.0)
        
        engine = LiveTradingEngine(
            gateway=gateway,
            initial_balance=10000.0,
            enable_regime_filter=True,
            enable_profit_lock=True,
            lockin_r=1.0,
            giveback_r=0.75,
            state_db_path=db_path
        )
        
        # 1. Start Engine
        await engine.start()
        assert engine.is_running is True
        assert engine.portfolio_coordinator.state.nav == 10000.0
        
        # 2. Ingest real historical candles for BTC (Set 3: 1D / 4H / 1H)
        htf_candles = WarehouseLoader.load_history("BTC/USDT", "1D", limit=50)
        mtf_candles = WarehouseLoader.load_history("BTC/USDT", "4H", limit=100)
        ltf_candles = WarehouseLoader.load_history("BTC/USDT", "1H", limit=150)
        
        assert len(htf_candles) > 0
        assert len(mtf_candles) > 0
        assert len(ltf_candles) > 0
        
        # 3. Simulate Bar-Close event
        plans = await engine.on_bar_closed(
            symbol="BTCUSDT",
            htf_candles=htf_candles,
            mtf_candles=mtf_candles,
            ltf_candles=ltf_candles,
            current_atr=150.0
        )
        
        # 4. Simulate Live Market Ticks
        last_close = ltf_candles[-1].close
        await engine.on_tick("BTCUSDT", current_price=last_close, high=last_close + 50, low=last_close - 50)
        
        # 5. Verify State Persistence on Disk
        store = StateStore(db_path=db_path)
        persisted = store.load_state("portfolio_state")
        assert persisted is not None
        assert "nav" in persisted
        assert persisted["nav"] == 10000.0
        
        # 6. Run EOD Reconciliation Audit
        recon_report = await engine.run_eod_reconciliation()
        assert recon_report.is_clean is True
        assert recon_report.discrepancy_usd == 0.0
        
        # 7. Stop Engine Cleanly
        await engine.stop()
        assert engine.is_running is False

    asyncio.run(_run())
