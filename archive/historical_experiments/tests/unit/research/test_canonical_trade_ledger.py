"""
Unit tests for Canonical Trade Ledger schema and serialization.
"""

import os
import tempfile
import json
import pytest
from research.simulation.trade_ledger import TradeLedger, SimulatedTrade


def test_canonical_trade_ledger_schema_and_export():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        ledger_file = tf.name

    try:
        ledger = TradeLedger(initial_equity=10000.0)
        
        trade = SimulatedTrade(
            trade_id="TR_TEST_001",
            hypothesis_id="HTF_TREND_CONTINUATION_V1",
            symbol="BTC/USDT",
            timeframe_set="SET_3",
            directional_permission="PERMIT_LONG",
            setup_timestamp=1680000000,
            entry_timestamp=1680003600,
            exit_timestamp=1680018000,
            entry_price=100.0,
            fill_entry_price=100.0,
            initial_stop_price=99.0,
            current_stop_price=99.0,
            target_price=104.0,
            exit_price=104.0,
            position_units=1.0,
            dollar_risk=100.0,
            raw_rr=4.0,
            realized_rr=4.0,
            realized_pnl=400.0,
            entry_fee=0.05,
            exit_fee=0.05,
            entry_slippage_bps=1.0,
            exit_slippage_bps=1.0,
            funding_usd=0.0,
            total_friction_usd=0.12,
            status="CLOSED",
            exit_reason="HTF_TP",
            trend_regime="BULL_TREND",
            volatility_regime="HIGH_VOLATILITY",
            market_phase="CONTINUATION",
            strategy_version="v2.0-UNIFIED-CANONICAL-LOCKED",
            dataset_manifest_hash="5b8ca6a85cc772..",
            experiment_id="EXP_TEST_001",
            metadata={"mae_price": 99.8, "mfe_price": 104.5}
        )

        ledger.trades["TR_TEST_001"] = trade
        ledger.closed_trades.append(trade)

        path = ledger.export_canonical_trade_ledger(ledger_file)
        assert os.path.exists(path)

        with open(path, "r") as f:
            data = json.load(f)

        assert data["total_trades"] == 1
        t_dict = data["trades"][0]
        assert t_dict["direction"] == "LONG"
        assert t_dict["gross_r"] > 4.0
        assert t_dict["fees_r"] == 0.001
        assert t_dict["trend_regime"] == "BULL_TREND"
        assert t_dict["volatility_regime"] == "HIGH_VOLATILITY"
        assert t_dict["market_phase"] == "CONTINUATION"
        assert t_dict["strategy_version"] == "v2.0-UNIFIED-CANONICAL-LOCKED"
    finally:
        if os.path.exists(ledger_file):
            os.remove(ledger_file)
