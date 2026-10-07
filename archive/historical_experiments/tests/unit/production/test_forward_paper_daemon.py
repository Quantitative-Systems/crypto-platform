"""
Unit tests for QCP Continuous Forward Paper Daemon.
Tests clock synchronization, closed-candle confirmation, duplicate-bar rejection,
missing-bar detection, stale-data inhibit, and persistent state/position recovery.
"""

import os
import json
import pytest
import time
from market_intelligence.primitives import Candle
from production.forward_paper_daemon import ForwardPaperDaemon, DaemonConfig


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


def test_closed_candle_confirmation(tmp_path):
    state_file = str(tmp_path / "daemon_state.json")
    audit_file = str(tmp_path / "daemon_audit.json")
    config = DaemonConfig(
        symbol="SOL/USDT",
        state_file=state_file,
        audit_file=audit_file,
        max_stale_data_sec=100000.0,
    )
    daemon = ForwardPaperDaemon(config=config)

    # 15m candle at ts = 10,000. Closes at 10,900.
    start_ts = 10000
    tf_15m = make_candle_series(start_ts=start_ts, interval_sec=900, count=50)
    tf_1h = make_candle_series(start_ts=start_ts, interval_sec=3600, count=30)
    tf_4h = make_candle_series(start_ts=start_ts, interval_sec=14400, count=30)

    feed = {"15m": tf_15m, "1h": tf_1h, "4h": tf_4h}
    last_15m = tf_15m[-1]

    # Scenario A: current time is BEFORE the 15m candle closes (now = last_15m.timestamp + 500)
    now_before_close = last_15m.timestamp + 500
    res_before = daemon.run_cycle(current_time=now_before_close, candle_feed=feed)

    # The last candle was not yet closed, so its predecessor was the latest closed
    assert daemon.last_processed_ts["15m"] == tf_15m[-2].timestamp

    # Scenario B: current time is AFTER candle closes (now = last_15m.timestamp + 901)
    now_after_close = last_15m.timestamp + 901
    res_after = daemon.run_cycle(current_time=now_after_close, candle_feed=feed)
    assert daemon.last_processed_ts["15m"] == last_15m.timestamp


def test_duplicate_bar_protection(tmp_path):
    state_file = str(tmp_path / "daemon_state.json")
    audit_file = str(tmp_path / "daemon_audit.json")
    config = DaemonConfig(
        symbol="SOL/USDT",
        state_file=state_file,
        audit_file=audit_file,
        max_stale_data_sec=100000.0,
    )
    daemon = ForwardPaperDaemon(config=config)

    start_ts = 100000
    tf_15m = make_candle_series(start_ts=start_ts, interval_sec=900, count=50)
    tf_1h = make_candle_series(start_ts=start_ts, interval_sec=3600, count=30)
    tf_4h = make_candle_series(start_ts=start_ts, interval_sec=14400, count=30)
    feed = {"15m": tf_15m, "1h": tf_1h, "4h": tf_4h}

    now = tf_15m[-1].timestamp + 1000
    # Cycle 1: Processes the new bars
    res1 = daemon.run_cycle(current_time=now, candle_feed=feed)
    assert "15m" in res1["new_bars_processed"]

    # Cycle 2: Same candles feed, same time. Must be rejected as duplicate
    res2 = daemon.run_cycle(current_time=now + 10, candle_feed=feed)
    assert "15m" not in res2["new_bars_processed"]
    assert len(res2["new_orders"]) == 0


def test_missing_bar_detection(tmp_path):
    state_file = str(tmp_path / "daemon_state.json")
    audit_file = str(tmp_path / "daemon_audit.json")
    config = DaemonConfig(
        symbol="SOL/USDT",
        state_file=state_file,
        audit_file=audit_file,
        max_stale_data_sec=100000.0,
    )
    daemon = ForwardPaperDaemon(config=config)

    start_ts = 100000
    tf_15m = make_candle_series(start_ts=start_ts, interval_sec=900, count=50)
    tf_1h = make_candle_series(start_ts=start_ts, interval_sec=3600, count=30)
    tf_4h = make_candle_series(start_ts=start_ts, interval_sec=14400, count=30)
    feed = {"15m": tf_15m, "1h": tf_1h, "4h": tf_4h}

    # First cycle
    daemon.run_cycle(current_time=tf_15m[-1].timestamp + 1000, candle_feed=feed)

    # Next cycle: skip 3 bars (gap of 3600s instead of 900s)
    gap_bar = Candle(
        timestamp=tf_15m[-1].timestamp + 3600,
        open=120.0, high=121.0, low=119.0, close=120.5, volume=500.0
    )
    tf_15m_with_gap = tf_15m + [gap_bar]
    feed_gap = {"15m": tf_15m_with_gap, "1h": tf_1h, "4h": tf_4h}

    res_gap = daemon.run_cycle(current_time=gap_bar.timestamp + 1000, candle_feed=feed_gap)
    assert len(daemon.gaps_detected) == 1
    assert daemon.gaps_detected[0]["timeframe"] == "15m"
    assert daemon.gaps_detected[0]["gap_seconds"] == 3600


def test_stale_data_inhibit(tmp_path):
    state_file = str(tmp_path / "daemon_state.json")
    audit_file = str(tmp_path / "daemon_audit.json")
    config = DaemonConfig(
        symbol="SOL/USDT",
        state_file=state_file,
        audit_file=audit_file,
        max_stale_data_sec=900.0,  # 15 mins
    )
    daemon = ForwardPaperDaemon(config=config)

    start_ts = 100000
    tf_15m = make_candle_series(start_ts=start_ts, interval_sec=900, count=50)
    tf_1h = make_candle_series(start_ts=start_ts, interval_sec=3600, count=30)
    tf_4h = make_candle_series(start_ts=start_ts, interval_sec=14400, count=30)
    feed = {"15m": tf_15m, "1h": tf_1h, "4h": tf_4h}

    # Set current time to 2 hours after the latest candle (stale!)
    stale_time = tf_15m[-1].timestamp + 7200
    res = daemon.run_cycle(current_time=stale_time, candle_feed=feed)

    assert res["status"] == "STALE_DATA_INHIBITED"
    assert any("STALE_DATA_INHIBIT" in w for w in res["warnings"])


def test_state_and_position_recovery(tmp_path):
    state_file = str(tmp_path / "daemon_state.json")
    audit_file = str(tmp_path / "daemon_audit.json")
    config = DaemonConfig(
        symbol="SOL/USDT",
        state_file=state_file,
        audit_file=audit_file,
        starting_capital=1000.0,
    )
    daemon1 = ForwardPaperDaemon(config=config)

    # Manually simulate state change & open position
    daemon1.current_equity = 1450.0
    daemon1.peak_equity = 1500.0
    daemon1.max_drawdown_usd = 50.0
    daemon1.max_drawdown_pct = 3.33
    daemon1.last_processed_ts["15m"] = 1704100000

    from trade_management.lifecycle_engine import ManagedPosition, PositionLifecycleStage
    pos = ManagedPosition(
        position_id="POS_SOL_RECOVER_001",
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
    daemon1.trade_manager.active_positions[pos.position_id] = pos
    daemon1._save_state()

    assert os.path.exists(state_file)

    # Now instantiate a brand new daemon pointing to that same state file
    daemon2 = ForwardPaperDaemon(config=config)

    assert daemon2.current_equity == 1450.0
    assert daemon2.peak_equity == 1500.0
    assert daemon2.max_drawdown_usd == 50.0
    assert daemon2.max_drawdown_pct == 3.33
    assert daemon2.last_processed_ts["15m"] == 1704100000
    assert "POS_SOL_RECOVER_001" in daemon2.trade_manager.active_positions
    recovered_pos = daemon2.trade_manager.active_positions["POS_SOL_RECOVER_001"]
    assert recovered_pos.entry_price == 100.0
    assert recovered_pos.total_qty == 2.0


def test_heartbeat_emission(tmp_path):
    state_file = str(tmp_path / "daemon_state.json")
    audit_file = str(tmp_path / "daemon_audit.json")
    config = DaemonConfig(
        symbol="SOL/USDT",
        state_file=state_file,
        audit_file=audit_file,
        heartbeat_interval_sec=5.0,
        max_stale_data_sec=100000.0,
    )
    daemon = ForwardPaperDaemon(config=config)

    start_ts = 100000
    tf_15m = make_candle_series(start_ts=start_ts, interval_sec=900, count=50)
    tf_1h = make_candle_series(start_ts=start_ts, interval_sec=3600, count=30)
    tf_4h = make_candle_series(start_ts=start_ts, interval_sec=14400, count=30)
    feed = {"15m": tf_15m, "1h": tf_1h, "4h": tf_4h}

    now = tf_15m[-1].timestamp + 1000
    daemon.run_cycle(current_time=now, candle_feed=feed)

    assert os.path.exists(audit_file)
    with open(audit_file, "r") as f:
        data = json.load(f)
        assert data["platform"] == "Quantitative Crypto Platform (QCP)"
        assert data["last_heartbeat"]["status"] == "HEALTHY"
        assert data["last_heartbeat"]["current_equity_usd"] == 1000.0
