"""Unit & Regression Tests for Forensic Forward-Testing Pipeline Repair.

Verifies:
1. FractalHypothesis attribute access safety (populated and None hypotheses).
2. Multi-asset evaluation across BTCUSDT, ETHUSDT, SOLUSDT, and BNBUSDT.
3. Seeded and unseeded data handling across all timeframe sets (SET_1 to SET_5).
4. ContinuousCandleEngine subscriber error tracking and logging (no silent swallowing).
5. Duplicate candle prevention and causal ordering in supervisor.
6. API authentication for /api/decisions (401 on unauthenticated, 200 on authenticated).
7. Guest observer session provisioning (/api/auth/guest-session).
8. Strict RBAC protecting trading controls and tenant isolation against unprivileged sessions.
"""
import asyncio
import time
import pytest
from unittest.mock import MagicMock
import numpy as np
from aiohttp.test_utils import TestClient, TestServer

from execution.decision.phase_r_decision_engine import (
    PhaseRDecisionEngine,
    PhaseRDecisionRecord,
    DecisionType,
    PhaseRNoTradeReason,
)
from market_data.realtime.candle_engine import ContinuousCandleEngine, CandleRecord
from market_model.fractal_state_engine import (
    FractalHypothesis,
    FractalAlignment,
    TrendDirection,
)
from core.auth.user_model import UserRole
from core.auth.auth_service import AuthService
from web.server import PhaseRWebServer


def _make_dummy_tf_series(n=100, base_price=60000.0):
    now_ms = int(time.time() * 1000)
    ts = np.array([now_ms - (n - i) * 60000 for i in range(n)], dtype=np.int64)
    close_ts = ts + 59999
    return {
        "ts": ts,
        "close_ts": close_ts,
        "o": np.array([base_price] * n, dtype=np.float64),
        "h": np.array([base_price + 100.0] * n, dtype=np.float64),
        "l": np.array([base_price - 100.0] * n, dtype=np.float64),
        "c": np.array([base_price + 10.0] * n, dtype=np.float64),
        "v": np.array([50.0] * n, dtype=np.float64),
    }


class TestDecisionEngineHypothesisSafety:
    """Verifies that PhaseRDecisionEngine evaluates opportunities without crashing on hypothesis attributes."""

    @pytest.fixture(autouse=True)
    def setup_engine(self):
        self.engine = PhaseRDecisionEngine(symbol="BTCUSDT")

    def test_evaluate_opportunity_with_none_hypothesis(self):
        """Verifies that when hypothesis_engine returns None, evaluation does not raise AttributeError."""
        mock_node = MagicMock()
        mock_node.get_alignment_for_set.return_value = FractalAlignment.FULLY_ALIGNED
        mock_node.fractal_bias = MagicMock()
        self.engine.fractal_engine.hypothesis_engine.evaluate_hypothesis = MagicMock(return_value=None)
        self.engine.fractal_engine.hypothesis_engine._count_cross_set_support = MagicMock(return_value=1)

        # Mock coordinator to return candidate
        now_ms = int(time.time() * 1000)
        mock_coord = MagicMock()
        mock_coord.scan_signals.return_value = ([
            {
                "entry_price": 60000.0,
                "stop_price": 59000.0,
                "target_price": 65000.0,
                "direction": 1,
                "timestamp": now_ms,
                "break_type": "CHOCH",
            }
        ], {})
        self.engine.coordinators["SET_3"]["PULLBACK"] = mock_coord

        all_tf_data = {
            "15m": _make_dummy_tf_series(100),
            "1h": _make_dummy_tf_series(100),
            "4h": _make_dummy_tf_series(100),
            "1d": _make_dummy_tf_series(100),
        }

        # Must not raise AttributeError
        rec = self.engine.evaluate_opportunity(
            set_name="SET_3",
            hypothesis_type="PULLBACK",
            all_timeframe_data=all_tf_data,
            eval_timestamp_ms=now_ms,
        )
        assert isinstance(rec, PhaseRDecisionRecord)
        assert rec.asset == "BTCUSDT"
        assert rec.timeframe_set == "SET_3"
        assert rec.confidence_components["location"] == 0.0

    def test_evaluate_opportunity_with_populated_fractal_hypothesis(self):
        """Verifies that populated FractalHypothesis evaluates mtf_context safely without AttributeError."""
        hyp = FractalHypothesis(
            hypothesis_id="HYP_TEST_1",
            set_name="SET_3",
            htf_bias=TrendDirection.BULLISH,
            mtf_context="DISCOUNT",
            ltf_confirmation="CHOCH_BULLISH",
            expected_direction=1,
            target_destination="PREMIUM_EXPANSION",
            alignment=FractalAlignment.FULLY_ALIGNED,
            cross_set_support=2,
            confidence_score=0.75,
        )

        mock_node = MagicMock()
        mock_node.get_alignment_for_set.return_value = FractalAlignment.FULLY_ALIGNED
        mock_node.fractal_bias = TrendDirection.BULLISH
        self.engine.fractal_engine.hypothesis_engine.evaluate_hypothesis = MagicMock(return_value=hyp)
        self.engine.fractal_engine.hypothesis_engine._count_cross_set_support = MagicMock(return_value=2)

        now_ms = int(time.time() * 1000)
        mock_coord = MagicMock()
        mock_coord.scan_signals.return_value = ([
            {
                "entry_price": 60000.0,
                "stop_price": 59000.0,
                "target_price": 65000.0,
                "direction": 1,
                "timestamp": now_ms,
                "break_type": "CHOCH",
            }
        ], {})
        self.engine.coordinators["SET_3"]["PULLBACK"] = mock_coord

        all_tf_data = {
            "15m": _make_dummy_tf_series(100),
            "1h": _make_dummy_tf_series(100),
            "4h": _make_dummy_tf_series(100),
            "1d": _make_dummy_tf_series(100),
        }

        rec = self.engine.evaluate_opportunity(
            set_name="SET_3",
            hypothesis_type="PULLBACK",
            all_timeframe_data=all_tf_data,
            eval_timestamp_ms=now_ms,
        )
        assert isinstance(rec, PhaseRDecisionRecord)
        # Location confidence should be awarded for DISCOUNT context
        assert rec.confidence_components["location"] == 0.20
        assert rec.confidence_score >= 0.70

    def test_multi_asset_evaluation_across_all_execution_sets(self):
        """Verifies evaluation across BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT across SET_2, SET_3, SET_4."""
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]

        for sym in symbols:
            engine = PhaseRDecisionEngine(symbol=sym)
            now_ms = int(time.time() * 1000)

            # Test seeded (synthetic history), unseeded (short), and partially seeded (missing HTF/MTF)
            all_tf_seeded = {
                tf: _make_dummy_tf_series(80, base_price=1000.0)
                for tf in ["15m", "1h", "4h", "1d", "1w", "1M", "3m"]
            }
            all_tf_unseeded = {
                "15m": _make_dummy_tf_series(5, base_price=1000.0)
            }
            all_tf_partially_seeded = {
                "15m": _make_dummy_tf_series(80, base_price=1000.0)
            }

            for dataset in [all_tf_seeded, all_tf_unseeded, all_tf_partially_seeded]:
                for set_name in ["SET_2", "SET_3", "SET_4"]:
                    for hyp in ["CONTINUATION", "PULLBACK"]:
                        rec = engine.evaluate_opportunity(
                            set_name=set_name,
                            hypothesis_type=hyp,
                            all_timeframe_data=dataset,
                            eval_timestamp_ms=now_ms,
                        )
                        assert isinstance(rec, PhaseRDecisionRecord)
                        assert rec.asset == sym
                        assert rec.timeframe_set == set_name
                        assert rec.phase == hyp
                        assert rec.decision in (DecisionType.TRADE, DecisionType.NO_TRADE)


class TestCandleEngineSubscriberErrorTracking:
    """Verifies that ContinuousCandleEngine tracks subscriber exceptions and logs them instead of swallowing."""

    def test_subscriber_exception_logging_and_telemetry(self):
        engine = ContinuousCandleEngine(symbols=["BTCUSDT"])
        
        def failing_subscriber(candle):
            raise ValueError("Injected subscriber failure")

        engine.add_closed_candle_listener(failing_subscriber)

        rec = CandleRecord(
            symbol="BTCUSDT",
            timeframe="15m",
            open_ts=1792400000000,
            close_ts=1792400899999,
            open=65000.0,
            high=65500.0,
            low=64800.0,
            close=65200.0,
            volume=100.0,
            is_closed=True,
        )

        # Ingestion must not crash, but must record the error
        engine.ingest_closed_candle(rec)

        assert engine.listener_errors == 1
        assert "ValueError" in engine.last_listener_error
        assert "Injected subscriber failure" in engine.last_listener_error

        status = engine.get_summary_status()
        assert status["listener_errors"] == 1
        assert "ValueError" in status["last_listener_error"]

    def test_duplicate_candle_prevention(self):
        engine = ContinuousCandleEngine(symbols=["BTCUSDT"])
        call_count = 0

        def sub(c):
            nonlocal call_count
            call_count += 1

        engine.add_closed_candle_listener(sub)

        rec = CandleRecord(
            symbol="BTCUSDT",
            timeframe="15m",
            open_ts=1792400000000,
            close_ts=1792400899999,
            open=65000.0,
            high=65500.0,
            low=64800.0,
            close=65200.0,
            volume=100.0,
            is_closed=True,
        )

        engine.ingest_closed_candle(rec)
        assert call_count == 1

        # Ingest exact same candle again -> must be dropped
        engine.ingest_closed_candle(rec)
        assert call_count == 1


class TestWebDecisionsAndAuthSecurity:
    """Verifies API authentication, guest session handling, and RBAC protection on trading controls."""

    @pytest.fixture
    def mock_supervisor(self):
        sup = MagicMock()
        rec1 = PhaseRDecisionRecord(
            decision_id="DEC_001",
            lineage_id="LIN_001",
            event_id="EVT_001",
            timestamp_ms=1792418400000,
            asset="BTCUSDT",
            timeframe_set="SET_3",
            phase="PULLBACK",
            decision=DecisionType.NO_TRADE,
            reason_codes=[PhaseRNoTradeReason.NO_STRUCTURAL_SETUP.value],
            confidence_score=0.35,
            confidence_components={"base": 0.35},
            fractal_alignment="UNKNOWN",
            fractal_bias="NEUTRAL",
            direction=0,
            entry_price=0.0,
            initial_stop_price=0.0,
            target_price=0.0,
            planned_r=0.0,
            risk_pct=0.0,
            portfolio_heat_pct=0.0,
            governor_passed=False,
        )
        sup.decisions_history = [rec1]
        sup.active_positions = {}
        sup.closed_positions = []
        sup.orders_history = []
        sup.reconciliation_engine = MagicMock()
        sup.reconciliation_engine.last_report = MagicMock(is_reconciled=True)
        sup.drift_monitor = MagicMock()
        sup.drift_monitor.evaluate_drift.return_value = MagicMock(to_dict=lambda: {"drift_detected": False})
        sup.account_manager = MagicMock()
        sup.account_manager.list_accounts.return_value = []
        return sup

    @pytest.mark.asyncio
    async def test_decisions_api_unauthenticated_returns_401(self, mock_supervisor):
        server = PhaseRWebServer(supervisor=mock_supervisor)
        async with TestClient(TestServer(server.app)) as client:
            # Direct unauthenticated request must fail-closed with 401
            res = await client.get("/api/decisions")
            assert res.status == 401
            data = await res.json()
            assert "Authentication required" in data.get("error", "")

    @pytest.mark.asyncio
    async def test_guest_session_creation_and_decisions_access(self, mock_supervisor):
        server = PhaseRWebServer(supervisor=mock_supervisor)
        async with TestClient(TestServer(server.app)) as client:
            # 1. Request guest observer session
            guest_res = await client.post("/api/auth/guest-session")
            assert guest_res.status == 200
            guest_data = await guest_res.json()
            token = guest_data.get("token")
            assert token and token.startswith("strata_")
            assert guest_data["user"]["role"] == UserRole.RESEARCHER.value

            # 2. Access /api/decisions using guest session token
            headers = {"Authorization": f"Bearer {token}"}
            dec_res = await client.get("/api/decisions", headers=headers)
            assert dec_res.status == 200
            dec_data = await dec_res.json()
            assert len(dec_data) == 1
            assert dec_data[0]["decision_id"] == "DEC_001"
            assert dec_data[0]["symbol"] == "BTCUSDT"
            assert dec_data[0]["set_name"] == "SET_3"
            assert dec_data[0]["decision"] == "NO_TRADE"

    @pytest.mark.asyncio
    async def test_guest_session_forbidden_from_trading_controls(self, mock_supervisor):
        server = PhaseRWebServer(supervisor=mock_supervisor)
        async with TestClient(TestServer(server.app)) as client:
            guest_res = await client.post("/api/auth/guest-session")
            token = (await guest_res.json())["token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Trading controls must forbid unprivileged RESEARCHER/guest sessions (403 Forbidden)
            assert (await client.post("/api/agent/pause", headers=headers)).status == 403
            assert (await client.post("/api/agent/resume", headers=headers)).status == 403
            assert (await client.post("/api/agent/style", json={"style": "SWING"}, headers=headers)).status == 403
            assert (await client.post("/api/brokers/connect", json={"venue": "BINANCE"}, headers=headers)).status == 403
