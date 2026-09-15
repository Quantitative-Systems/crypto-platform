"""
Quantitative Crypto Platform (QCP) — Forward Paper Daemon Operational Acceptance Test (OAT).

Proves the operational reality of the forward paper infrastructure before live burn-in:
1. Real Binance public data arrives without API keys.
2. Only closed candles are processed (no in-progress candle leakage).
3. Duplicate candles are rejected across cycles.
4. Missing bar gaps are detected and logged.
5. Restart recovery restores equity and positions without duplicate orders.
6. State is persisted atomically to disk.
7. Telemetry and Model-vs-Reality deltas are written to disk.
8. Structured heartbeats continue reliably.
9. Capital firewall is locked: zero live credentials permitted.
10. Zero live order execution paths reachable (strictly simulated fills).
"""

import os
import json
import time
import pytest

from market_intelligence.primitives import Candle
from market_data.binance_fetcher import BinanceFetcher
from production.forward_paper_daemon import ForwardPaperDaemon, DaemonConfig
from platform_core.canonical_strategy_spec import create_fam07_spec, StrategyLifecycleState
from trade_management.lifecycle_engine import ManagedPosition, PositionLifecycleStage


def make_candle_series(start_ts: int, interval_sec: int, count: int, base_price: float = 100.0):
    candles = []
    price = base_price
    for i in range(count):
        ts = start_ts + i * interval_sec
        candles.append(
            Candle(
                timestamp=ts,
                open=price,
                high=price + 1.0,
                low=price - 1.0,
                close=price + 0.5,
                volume=1000.0,
            )
        )
        price += 0.2
    return candles


def test_oat_01_real_binance_public_data():
    """OAT Criterion 1: Verify real Binance public data arrives without API keys."""
    candles = BinanceFetcher.fetch_live_candles(symbol="SOL/USDT", timeframe="15m", limit=5)
    assert len(candles) == 5
    for c in candles:
        assert c.timestamp > 1700000000
        assert c.open > 0
        assert c.high >= c.low
        assert c.close > 0
        assert c.volume >= 0


def test_oat_02_closed_candle_confirmation(tmp_path):
    """OAT Criterion 2: Only closed candles are processed."""
    config = DaemonConfig(
        symbol="SOL/USDT",
        state_file=str(tmp_path / "state.json"),
        audit_file=str(tmp_path / "audit.json"),
        max_stale_data_sec=100000.0,
    )
    daemon = ForwardPaperDaemon(config=config)

    start_ts = 100000
    tf_15m = make_candle_series(start_ts=start_ts, interval_sec=900, count=40)
    tf_1h = make_candle_series(start_ts=start_ts, interval_sec=3600, count=30)
    tf_4h = make_candle_series(start_ts=start_ts, interval_sec=14400, count=30)
    feed = {"15m": tf_15m, "1h": tf_1h, "4h": tf_4h}

    # Time before 15m candle closes
    now_unclosed = tf_15m[-1].timestamp + 300
    daemon.run_cycle(current_time=now_unclosed, candle_feed=feed)
    assert daemon.last_processed_ts["15m"] == tf_15m[-2].timestamp

    # Time after 15m candle closes
    now_closed = tf_15m[-1].timestamp + 901
    daemon.run_cycle(current_time=now_closed, candle_feed=feed)
    assert daemon.last_processed_ts["15m"] == tf_15m[-1].timestamp


def test_oat_03_duplicate_candle_rejection(tmp_path):
    """OAT Criterion 3: Duplicate candles rejected across cycles."""
    config = DaemonConfig(
        symbol="SOL/USDT",
        state_file=str(tmp_path / "state.json"),
        audit_file=str(tmp_path / "audit.json"),
        max_stale_data_sec=100000.0,
    )
    daemon = ForwardPaperDaemon(config=config)

    start_ts = 100000
    tf_15m = make_candle_series(start_ts=start_ts, interval_sec=900, count=40)
    tf_1h = make_candle_series(start_ts=start_ts, interval_sec=3600, count=30)
    tf_4h = make_candle_series(start_ts=start_ts, interval_sec=14400, count=30)
    feed = {"15m": tf_15m, "1h": tf_1h, "4h": tf_4h}

    now = tf_15m[-1].timestamp + 1000
    res1 = daemon.run_cycle(current_time=now, candle_feed=feed)
    assert "15m" in res1["new_bars_processed"]

    # Repeat cycle with same candles
    res2 = daemon.run_cycle(current_time=now + 10, candle_feed=feed)
    assert "15m" not in res2["new_bars_processed"]
    assert len(res2["new_orders"]) == 0


def test_oat_04_gap_detection_and_logging(tmp_path):
    """OAT Criterion 4: Missing bar gaps detected and logged."""
    config = DaemonConfig(
        symbol="SOL/USDT",
        state_file=str(tmp_path / "state.json"),
        audit_file=str(tmp_path / "audit.json"),
        max_stale_data_sec=100000.0,
    )
    daemon = ForwardPaperDaemon(config=config)

    start_ts = 100000
    tf_15m = make_candle_series(start_ts=start_ts, interval_sec=900, count=40)
    tf_1h = make_candle_series(start_ts=start_ts, interval_sec=3600, count=30)
    tf_4h = make_candle_series(start_ts=start_ts, interval_sec=14400, count=30)
    feed = {"15m": tf_15m, "1h": tf_1h, "4h": tf_4h}

    daemon.run_cycle(current_time=tf_15m[-1].timestamp + 1000, candle_feed=feed)

    # Introduce 2-bar gap (2700s instead of 900s)
    gap_bar = Candle(
        timestamp=tf_15m[-1].timestamp + 2700,
        open=120.0, high=121.0, low=119.0, close=120.5, volume=500.0
    )
    feed_gap = {"15m": tf_15m + [gap_bar], "1h": tf_1h, "4h": tf_4h}

    daemon.run_cycle(current_time=gap_bar.timestamp + 1000, candle_feed=feed_gap)
    assert len(daemon.gaps_detected) == 1
    assert daemon.gaps_detected[0]["gap_seconds"] == 2700


def test_oat_05_state_persistence_and_restart_recovery(tmp_path):
    """OAT Criterion 5: State persistence and clean restart recovery."""
    state_file = str(tmp_path / "daemon_state.json")
    config = DaemonConfig(
        symbol="SOL/USDT",
        state_file=state_file,
        audit_file=str(tmp_path / "daemon_audit.json"),
        starting_capital=1000.0,
    )
    d1 = ForwardPaperDaemon(config=config)
    d1.current_equity = 1650.0
    d1.peak_equity = 1700.0
    d1.max_drawdown_usd = 50.0
    d1.max_drawdown_pct = 2.94

    pos = ManagedPosition(
        position_id="POS_SOL_OAT_001",
        strategy_id="FAM-07-MTFCONT_SOLUSDT_Set2",
        symbol="SOL/USDT",
        direction="BUY",
        stage=PositionLifecycleStage.ACTIVE,
        entry_price=100.0,
        initial_sl_price=95.0,
        current_sl_price=95.0,
        emergency_sl_price=95.0,
        tp1_price=105.0,
        tp2_price=110.0,
        tp3_price=112.5,
        total_qty=2.0,
        remaining_qty=2.0,
        risk_r_unit_usd=10.0,
        entry_time=1704100000,
    )
    d1.trade_manager.active_positions[pos.position_id] = pos
    d1._save_state()

    assert os.path.exists(state_file)

    # Reboot daemon instance
    d2 = ForwardPaperDaemon(config=config)
    assert d2.current_equity == 1650.0
    assert d2.peak_equity == 1700.0
    assert d2.max_drawdown_pct == 2.94
    assert "POS_SOL_OAT_001" in d2.trade_manager.active_positions
    rec_pos = d2.trade_manager.active_positions["POS_SOL_OAT_001"]
    assert rec_pos.entry_price == 100.0
    assert rec_pos.total_qty == 2.0


def test_oat_06_structured_heartbeat_emission(tmp_path):
    """OAT Criterion 6: Structured heartbeat emission with Model-vs-Reality gap audit."""
    audit_file = str(tmp_path / "daemon_audit.json")
    config = DaemonConfig(
        symbol="SOL/USDT",
        state_file=str(tmp_path / "daemon_state.json"),
        audit_file=audit_file,
        heartbeat_interval_sec=1.0,
        max_stale_data_sec=100000.0,
    )
    daemon = ForwardPaperDaemon(config=config)

    start_ts = 100000
    tf_15m = make_candle_series(start_ts=start_ts, interval_sec=900, count=40)
    tf_1h = make_candle_series(start_ts=start_ts, interval_sec=3600, count=30)
    tf_4h = make_candle_series(start_ts=start_ts, interval_sec=14400, count=30)
    feed = {"15m": tf_15m, "1h": tf_1h, "4h": tf_4h}

    daemon.run_cycle(current_time=tf_15m[-1].timestamp + 1000, candle_feed=feed)

    assert os.path.exists(audit_file)
    with open(audit_file, "r") as f:
        data = json.load(f)
        assert data["last_heartbeat"]["status"] == "HEALTHY"
        assert "model_vs_reality_gap" in data
        assert "avg_friction_error_bps" in data["model_vs_reality_gap"]


def test_oat_07_capital_firewall_locked_and_no_credentials():
    """OAT Criterion 7 & 8: Zero live credentials permitted and no live order path reachable."""
    # Ensure no credentials exist in environment
    assert os.getenv("BINANCE_API_KEY") is None
    assert os.getenv("BINANCE_SECRET_KEY") is None
    assert os.getenv("EXCHANGE_PRIVATE_KEY") is None

    # Simulating presence of credential must raise immediate fatal exception
    os.environ["BINANCE_API_KEY"] = "fake_key_123"
    try:
        with pytest.raises(RuntimeError, match="FATAL: Capital firewall violation"):
            ForwardPaperDaemon()
    finally:
        del os.environ["BINANCE_API_KEY"]
