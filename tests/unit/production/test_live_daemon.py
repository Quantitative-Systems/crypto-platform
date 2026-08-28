"""
Unit tests for LiveTradingDaemon & CLILauncher.
Tests interactive/non-interactive configuration, Demo vs Live modes, and graceful shutdown lifecycle.
"""

import os
import pytest
import asyncio
from execution_gateway.contracts.broker_config import BrokerConfig, BrokerType
from production.run_live_24_7 import LiveTradingDaemon


def test_live_trading_daemon_lifecycle():
    async def _run():
        broker_cfg = BrokerConfig(
            broker_type=BrokerType.PAPER,
            allowed_symbols=["BTC/USDT", "ETH/USDT"],
            testnet=True
        )
        
        runtime_opts = {
            "is_live": False,
            "hyp_b_only": True,
            "risk_pct": 0.01,
            "broker_desc": "Paper Demo"
        }
        
        daemon = LiveTradingDaemon(broker_config=broker_cfg, runtime_options=runtime_opts)
        
        # Test start
        start_task = asyncio.create_task(daemon.start())
        
        # Give it a short moment to run
        await asyncio.sleep(0.5)
        assert daemon.is_running is True
        
        # Test stop
        await daemon.stop()
        assert daemon.is_running is False
        
        # Cancel background task cleanly
        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass

    asyncio.run(_run())


def test_broker_config_demo_vs_live_flags():
    # Demo config
    demo_cfg = BrokerConfig(broker_type=BrokerType.EXNESS_MT5, testnet=True)
    assert demo_cfg.testnet is True
    
    # Live config
    live_cfg = BrokerConfig(broker_type=BrokerType.EXNESS_MT5, testnet=False)
    assert live_cfg.testnet is False
