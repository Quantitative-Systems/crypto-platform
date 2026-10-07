"""
Regression Tests for Canonical Baseline Remediations
Validates:
1. Trade Ledger Accounting: Realized PnL includes BOTH entry and exit fees,
   Realized RR is net of all fees, and Account Equity delta strictly matches
   sum(realized_pnl) with zero double-counting.
2. Canonical Trailing Default: StrategyCoordinator, ActiveTradeManager, CausalReplayer,
   ExecutionSimulator, and LiveTradingEngine all default enable_profit_lock=False.
3. Timeframe Lifespan Disambiguation: Strict resolution of "1m" != "1M" and aliases.
4. WarehouseLoader Fail-Closed: Missing data raises RuntimeError and never produces synthetic candles.
"""

import pytest
from unittest.mock import patch
from research.simulation.trade_ledger import TradeLedger, SimulatedTrade
from strategy_engine.coordinator.strategy_coordinator import StrategyCoordinator, get_max_lifespan_seconds
from strategy_engine.lifecycle.active_trade_manager import ActiveTradeManager
from research.replayer.causal_replayer import CausalReplayer
from research.simulation.execution_simulator import ExecutionSimulator
from production.live_trader import LiveTradingEngine
from execution_gateway.interfaces.base_gateway import BaseGateway
from market_data.warehouse_loader import WarehouseLoader


# =====================================================================
# 1. TRADE LEDGER ACCOUNTING REGRESSION TEST
# =====================================================================
def test_trade_ledger_fee_accounting_and_equity_consistency():
    initial_equity = 10000.0
    ledger = TradeLedger(initial_equity=initial_equity)
    
    # Trade 1: Winning Long Trade
    t1 = SimulatedTrade(
        trade_id="TR_01",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTC/USDT",
        timeframe_set="SET_3",
        directional_permission="PERMIT_LONG",
        setup_timestamp=1700000000,
        entry_price=100.0,
        initial_stop_price=95.0,
        current_stop_price=95.0,
        target_price=120.0,
        position_units=20.0,
        dollar_risk=100.0,
        raw_rr=4.0
    )
    ledger.record_pending_trade(t1)
    
    # Activation: entry fee = $2.00, fill = 100.0
    entry_fee_1 = 2.00
    ledger.activate_trade(
        trade_id="TR_01",
        fill_price=100.0,
        timestamp=1700000060,
        entry_fee=entry_fee_1,
        slippage_bps=5.0
    )
    assert ledger.current_equity == initial_equity - entry_fee_1  # 9998.0
    
    # Close: exit price = 120.0, exit fee = 2.40
    exit_fee_1 = 2.40
    closed_t1 = ledger.close_trade(
        trade_id="TR_01",
        exit_price=120.0,
        exit_timestamp=1700003600,
        exit_reason="HTF_TP",
        exit_fee=exit_fee_1,
        slippage_bps=5.0
    )
    
    # Gross PnL = (120 - 100) * 20 = 400.0
    # Net PnL = 400.0 - 2.00 - 2.40 = 395.60
    assert closed_t1 is not None
    assert closed_t1.realized_pnl == pytest.approx(395.60, abs=1e-4)
    assert closed_t1.realized_rr == pytest.approx(395.60 / 100.0, abs=1e-4)
    
    # Trade 2: Losing Short Trade
    t2 = SimulatedTrade(
        trade_id="TR_02",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="ETH/USDT",
        timeframe_set="SET_3",
        directional_permission="PERMIT_SHORT",
        setup_timestamp=1700005000,
        entry_price=2000.0,
        initial_stop_price=2050.0,
        current_stop_price=2050.0,
        target_price=1800.0,
        position_units=2.0,
        dollar_risk=100.0,
        raw_rr=4.0
    )
    ledger.record_pending_trade(t2)
    
    entry_fee_2 = 1.00
    ledger.activate_trade(
        trade_id="TR_02",
        fill_price=2000.0,
        timestamp=1700005060,
        entry_fee=entry_fee_2,
        slippage_bps=5.0
    )
    
    # Stop loss hit at 2050.0
    exit_fee_2 = 1.025
    closed_t2 = ledger.close_trade(
        trade_id="TR_02",
        exit_price=2050.0,
        exit_timestamp=1700007200,
        exit_reason="INITIAL_LTF_SL",
        exit_fee=exit_fee_2,
        slippage_bps=5.0
    )
    
    # Gross PnL = (2000 - 2050) * 2.0 = -100.0
    # Net PnL = -100.0 - 1.00 - 1.025 = -102.025
    assert closed_t2 is not None
    assert closed_t2.realized_pnl == pytest.approx(-102.025, abs=1e-4)
    assert closed_t2.realized_rr == pytest.approx(-102.025 / 100.0, abs=1e-4)
    
    # Master Consistency Invariant:
    # Final Equity - Initial Equity == sum(realized_pnl of all closed trades)
    total_realized_pnl = sum(t.realized_pnl for t in ledger.closed_trades)
    expected_final_equity = initial_equity + total_realized_pnl
    assert ledger.current_equity == pytest.approx(expected_final_equity, abs=1e-4)


# =====================================================================
# 2. CANONICAL TRAILING DEFAULT REGRESSION TEST
# =====================================================================
def test_canonical_trailing_defaults(tmp_path):
    # StrategyCoordinator default
    coord = StrategyCoordinator()
    assert coord.active_manager.enable_profit_lock is False, "StrategyCoordinator must default enable_profit_lock=False"
    
    # ActiveTradeManager default
    atm = ActiveTradeManager()
    assert atm.enable_profit_lock is False, "ActiveTradeManager must default enable_profit_lock=False"
    
    # CausalReplayer default
    replayer = CausalReplayer()
    assert replayer.enable_profit_lock is False, "CausalReplayer must default enable_profit_lock=False"
    
    # ExecutionSimulator default
    sim = ExecutionSimulator()
    assert sim.enable_profit_lock is False, "ExecutionSimulator must default enable_profit_lock=False"
    
    # LiveTradingEngine default
    from execution_gateway.gateways.paper_gateway import PaperGateway
    gw = PaperGateway(initial_balance=10000.0)
    db_file = str(tmp_path / "test_live_state.db")
    live_engine = LiveTradingEngine(gateway=gw, state_db_path=db_file)
    assert live_engine.strategy_coordinator.active_manager.enable_profit_lock is False, "LiveTradingEngine must default enable_profit_lock=False"


# =====================================================================
# 3. TIMEFRAME LIFESPAN DISAMBIGUATION REGRESSION TEST
# =====================================================================
def test_timeframe_lifespan_disambiguation():
    # Strict inequality check
    assert get_max_lifespan_seconds("1m") != get_max_lifespan_seconds("1M"), "1m and 1M must NOT have the same lifespan!"
    
    # Minute aliases: 3600 seconds
    assert get_max_lifespan_seconds("1m") == 3600
    assert get_max_lifespan_seconds("1min") == 3600
    assert get_max_lifespan_seconds("1MIN") == 3600
    
    # 5m aliases: 14400 seconds
    assert get_max_lifespan_seconds("5m") == 14400
    assert get_max_lifespan_seconds("5min") == 14400
    assert get_max_lifespan_seconds("5MIN") == 14400
    
    # 15m aliases: 43200 seconds
    assert get_max_lifespan_seconds("15m") == 43200
    assert get_max_lifespan_seconds("15min") == 43200
    assert get_max_lifespan_seconds("15MIN") == 43200
    
    # 1h aliases: 172800 seconds (48 hours)
    assert get_max_lifespan_seconds("1h") == 172800
    assert get_max_lifespan_seconds("1H") == 172800
    assert get_max_lifespan_seconds("60m") == 172800
    assert get_max_lifespan_seconds("60min") == 172800
    
    # 4h aliases: 604800 seconds (7 days)
    assert get_max_lifespan_seconds("4h") == 604800
    assert get_max_lifespan_seconds("4H") == 604800
    assert get_max_lifespan_seconds("240m") == 604800
    
    # 1d aliases: 1814400 seconds (21 days)
    assert get_max_lifespan_seconds("1d") == 1814400
    assert get_max_lifespan_seconds("1D") == 1814400
    assert get_max_lifespan_seconds("1day") == 1814400
    assert get_max_lifespan_seconds("1DAY") == 1814400
    
    # 1w aliases: 5184000 seconds (60 days)
    assert get_max_lifespan_seconds("1w") == 5184000
    assert get_max_lifespan_seconds("1W") == 5184000
    assert get_max_lifespan_seconds("1week") == 5184000
    assert get_max_lifespan_seconds("1WEEK") == 5184000
    
    # Month aliases: 15552000 seconds (180 days)
    assert get_max_lifespan_seconds("1M") == 180 * 86400
    assert get_max_lifespan_seconds("1MO") == 180 * 86400
    assert get_max_lifespan_seconds("1mo") == 180 * 86400
    assert get_max_lifespan_seconds("1month") == 180 * 86400
    assert get_max_lifespan_seconds("1MONTH") == 180 * 86400
    assert get_max_lifespan_seconds("MO") == 180 * 86400


# =====================================================================
# 4. WAREHOUSE LOADER FAIL CLOSED REGRESSION TEST
# =====================================================================
def test_warehouse_loader_fails_closed_without_synthetic_data():
    with patch("market_data.binance_fetcher.BinanceFetcher.fetch_real_candles", return_value=[]):
        with pytest.raises(RuntimeError, match="Dataset unavailable"):
            WarehouseLoader.load_history(symbol="BTC/USDT", timeframe="1H")
            
    with patch("market_data.binance_fetcher.BinanceFetcher.fetch_real_candles", return_value=None):
        with pytest.raises(RuntimeError, match="Dataset unavailable"):
            WarehouseLoader.load_history(symbol="ETH/USDT", timeframe="4H")
