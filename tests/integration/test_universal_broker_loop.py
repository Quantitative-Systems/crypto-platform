"""
Integration Test: Universal Multi-Broker & Forex Execution Loop.
Verifies LiveTradingEngine connected to MT5ForexGateway (Exness / Vantage) on a $10 micro account.
"""

import os
import pytest
import asyncio
from market_data.warehouse_loader import WarehouseLoader
from execution_gateway.contracts.broker_config import BrokerConfig, BrokerType
from execution_gateway.gateways.mt5_forex_gateway import MT5ForexGateway
from production.live_trader import LiveTradingEngine
from production.persistence.state_store import StateStore


def test_universal_broker_exness_mt5_loop(tmp_path):
    async def _run():
        db_path = str(tmp_path / "mt5_test_state.db")
        
        # 1. Configure Exness MT5 Gateway with $10 Micro Account & Whitelist
        broker_cfg = BrokerConfig(
            broker_type=BrokerType.EXNESS_MT5,
            symbol_suffix="m",
            allowed_symbols=["BTC/USD", "ETH/USD", "EUR/USD", "XAU/USD"],
            min_lot_size=0.01,
            lot_step_size=0.01
        )
        gateway = MT5ForexGateway(config=broker_cfg, initial_balance=10.0)
        
        engine = LiveTradingEngine(
            gateway=gateway,
            initial_balance=10.0,  # $10 micro account!
            enable_regime_filter=True,
            enable_profit_lock=True,
            lockin_r=1.0,
            giveback_r=0.75,
            state_db_path=db_path
        )
        
        # 2. Start Engine
        await engine.start()
        assert engine.is_running is True
        assert engine.portfolio_coordinator.state.nav == 10.0
        
        # 3. Ingest real historical candles for BTC (Set 3: 1D / 4H / 1H)
        htf_candles = WarehouseLoader.load_history("BTC/USDT", "1D", limit=50)
        mtf_candles = WarehouseLoader.load_history("BTC/USDT", "4H", limit=100)
        ltf_candles = WarehouseLoader.load_history("BTC/USDT", "1H", limit=150)
        
        # 4. Bar Closed Evaluation
        plans = await engine.on_bar_closed(
            symbol="BTC/USD",
            htf_candles=htf_candles,
            mtf_candles=mtf_candles,
            ltf_candles=ltf_candles,
            current_atr=150.0
        )
        
        # 5. Live Market Tick Simulation
        last_close = ltf_candles[-1].close
        await engine.on_tick("BTC/USD", current_price=last_close, high=last_close + 50, low=last_close - 50)
        
        # 6. Verify State Persistence on Disk
        store = StateStore(db_path=db_path)
        persisted = store.load_state("portfolio_state")
        assert persisted is not None
        assert persisted["nav"] == 10.0
        
        # 7. Audit EOD Reconciler
        report = await engine.run_eod_reconciliation()
        assert report.is_clean is True
        
        # 8. Stop Engine
        await engine.stop()
        assert engine.is_running is False

    asyncio.run(_run())
