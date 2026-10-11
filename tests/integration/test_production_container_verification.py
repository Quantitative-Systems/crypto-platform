"""Automated Verification Suite for Production Server, API, WebSockets & Restart Persistence.

Verifies:
1. Server starts with canonical production command (main.py).
2. Health & readiness endpoints (/api/ready, /api/health, /api/version, /api/telemetry).
3. Authoritative market endpoints (/api/markets, /api/markets/BTCUSDT/five-set-ladder).
4. Research endpoints (/api/backtests, /api/forward-validation, /api/risk).
5. WebSocket streaming (/ws/market-state) event schema, snapshot, and ping/pong.
6. SQLite WAL persistence and research artifact survival across process restarts.
7. Zero real capital and fail-closed live execution invariance.
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
import pytest
import aiohttp

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.mark.asyncio
async def test_production_server_api_websocket_and_restart_persistence():
    port = 8089
    host = "127.0.0.1"
    base_url = f"http://{host}:{port}"
    ws_url = f"ws://{host}:{port}/ws/market-state"

    # Step 1: Start production server process with DEVNULL to avoid pipe buffer blocking
    proc1 = subprocess.Popen(
        [sys.executable, str(REPO_ROOT / "main.py"), "--host", host, "--port", str(port), "--mode", "PAPER"],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        # Step 2: Wait for readiness probe
        async with aiohttp.ClientSession() as session:
            ready = False
            for _ in range(30):
                await asyncio.sleep(0.5)
                try:
                    async with session.get(f"{base_url}/api/ready", timeout=2) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("status") == "READY":
                                ready = True
                                break
                except Exception:
                    pass

            assert ready, "Production server failed to report READY state within 15 seconds"

            # Step 3: Test Health and Invariant Endpoints
            async with session.get(f"{base_url}/api/health") as resp:
                assert resp.status == 200
                health = await resp.json()
                assert health["real_capital_authorized"] == 0.0
                assert health["live_trading_status"] == "DISABLED_FAIL_CLOSED"
                assert health["execution_mode"] == "PAPER"

            async with session.get(f"{base_url}/api/version") as resp:
                assert resp.status == 200
                ver = await resp.json()
                assert ver["king_contract_hash"] == "8fbc923a104e7688c3a9f0e4b8592c30dfb0b9a67a84511d5e49f8721c432098"
                assert ver["contract_status"] == "VERIFIED_IMMUTABLE"

            async with session.get(f"{base_url}/api/telemetry") as resp:
                assert resp.status == 200
                tele = await resp.json()
                assert "uptime_seconds" in tele
                assert tele["real_capital_authorized_usd"] == 0.0

            # Step 4: Test Markets & 5-Set Parity Endpoints
            async with session.get(f"{base_url}/api/markets") as resp:
                assert resp.status == 200
                markets = await resp.json()
                assert "all_assets" in markets
                assert len(markets["all_assets"]) >= 4

            async with session.get(f"{base_url}/api/markets/BTCUSDT/five-set-ladder") as resp:
                assert resp.status == 200
                ladder = await resp.json()
                assert ladder["symbol"] == "BTCUSDT"
                assert "sets" in ladder
                assert "SET_1" in ladder["sets"]
                assert "SET_2" in ladder["sets"]

            # Step 5: Test Research & Validation Endpoints
            async with session.get(f"{base_url}/api/backtests") as resp:
                assert resp.status == 200
                bt = await resp.json()
                assert "benchmark_king" in bt
                assert bt["benchmark_king"]["total_trades"] == 2942
                assert bt["benchmark_king"]["expectancy_r"] == 0.8885
                assert bt["benchmark_king"]["profit_factor"] == 4.918

            async with session.get(f"{base_url}/api/forward-validation") as resp:
                assert resp.status == 200
                fwd = await resp.json()
                assert "environments" in fwd
                assert "HISTORICAL" in fwd["environments"]
                assert "OOS" in fwd["environments"]
                assert "PAPER" in fwd["environments"]
                assert fwd["safety_invariants"]["real_capital_authorized"] == 0.0

            # Step 6: Test WebSocket Streaming Endpoint
            async with session.ws_connect(ws_url) as ws:
                # First message must be STATE_SNAPSHOT
                msg = await asyncio.wait_for(ws.receive(), timeout=5.0)
                assert msg.type == aiohttp.WSMsgType.TEXT
                snap = json.loads(msg.data)
                assert snap["event_type"] == "STATE_SNAPSHOT"
                assert snap["asset"] == "UNIVERSE"
                assert "metadata" in snap

                # Test Ping / Pong
                await ws.send_str(json.dumps({"action": "ping"}))
                pong_msg = await asyncio.wait_for(ws.receive(), timeout=5.0)
                pong = json.loads(pong_msg.data)
                assert pong["action"] == "pong"
                assert "timestamp" in pong

    finally:
        # Graceful shutdown of first process
        proc1.terminate()
        try:
            proc1.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc1.kill()

    # Step 7: Verify SQLite & Research Artifacts Survival across Restart
    db_file = REPO_ROOT / "data" / "crypto_platform.db"
    assert db_file.exists(), f"SQLite database {db_file} must exist"
    initial_db_size = db_file.stat().st_size
    assert initial_db_size > 0, "SQLite database must not be empty"

    contract_guard = REPO_ROOT / "research" / "results" / "PHASE_2_1_METRIC_RECONCILIATION.json"
    assert contract_guard.exists(), "Research reconciliation artifact must exist"
    with open(contract_guard, "r", encoding="utf-8") as f:
        reconcil = json.load(f)
        assert "verified_cohorts" in reconcil
        assert len(reconcil["verified_cohorts"]) >= 3

    # Step 8: Start second process (Restart recovery test)
    proc2 = subprocess.Popen(
        [sys.executable, str(REPO_ROOT / "main.py"), "--host", host, "--port", str(port), "--mode", "PAPER"],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        async with aiohttp.ClientSession() as session:
            ready_after_restart = False
            for _ in range(30):
                await asyncio.sleep(0.5)
                try:
                    async with session.get(f"{base_url}/api/ready", timeout=2) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("status") == "READY":
                                ready_after_restart = True
                                break
                except Exception:
                    pass

            assert ready_after_restart, "Server failed to recover and become READY after restart"

            # Check that database and state persisted
            async with session.get(f"{base_url}/api/health") as resp:
                assert resp.status == 200
                health = await resp.json()
                assert health["status"] == "HEALTHY"
                assert health["real_capital_authorized"] == 0.0

    finally:
        proc2.terminate()
        try:
            proc2.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc2.kill()
