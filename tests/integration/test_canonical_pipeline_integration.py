"""End-to-End Integration Test for the Canonical Crypto Platform Pipeline.

Validates the full institutional flow across decoupled components:
1. Data generation & OHLCV formatting
2. Market Model 3-dimensional state generation (Structure, Zones, Phase)
3. Causal strategy signal evaluation
4. Autonomous Decision Engine gating (No-Trade taxonomy, regime, health)
5. Shadow execution fill simulation and latency modeling
6. Immutable Decision Ledger auditing
"""
import sys
import unittest
import numpy as np
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from instrument.instrument_contract import build_instrument
from instrument.instrument_health import InstrumentHealth
from market_model.state_generator import MarketStateGenerator
from execution.shadow.shadow_trader import ShadowTrader
from execution.decision.decision_engine import AutonomousDecisionEngine, NoTradeReason


class TestCanonicalPipelineIntegration(unittest.TestCase):
    """End-to-End integration test validating the active platform lifecycle."""

    def setUp(self):
        self.state_generator = MarketStateGenerator(timeframe="1h")
        self.decision_engine = AutonomousDecisionEngine()
        self.trader = ShadowTrader(account_equity_usd=100_000.0)
        self.instrument = build_instrument("BTC/USD")
        self.trader.registry.register(self.instrument)
        self.health = InstrumentHealth(symbol="BTC/USD")

    def _generate_synthetic_ohlcv(self, n=50, base_price=50000.0):
        opens = []
        highs = []
        lows = []
        closes = []
        volumes = []
        timestamps = []
        p = base_price
        base_ts = 1700000000000
        for i in range(n):
            o = p
            h = o + 150.0
            l = o - 40.0
            c = o + 110.0
            p = c
            opens.append(o)
            highs.append(h)
            lows.append(l)
            closes.append(c)
            volumes.append(100.0)
            timestamps.append(base_ts + i * 3600000)
        return (
            np.array(opens, dtype=float),
            np.array(highs, dtype=float),
            np.array(lows, dtype=float),
            np.array(closes, dtype=float),
            np.array(volumes, dtype=float),
            np.array(timestamps, dtype=int),
        )

    def test_market_state_generation(self):
        """Test Market Model generation of Structure, Zones, and Phase."""
        opens, highs, lows, closes, volumes, timestamps = self._generate_synthetic_ohlcv(50)
        state = self.state_generator.generate(
            symbol="BTC/USD",
            opens=opens,
            highs=highs,
            lows=lows,
            closes=closes,
            volumes=volumes,
            timestamps=timestamps,
        )
        self.assertIsNotNone(state)
        self.assertEqual(state.symbol, "BTC/USD")
        self.assertEqual(state.timeframe, "1h")
        self.assertIsNotNone(state.structure)
        self.assertIsNotNone(state.zones)
        self.assertIsNotNone(state.phase)
        self.assertIsNotNone(state.measurements)

    def test_shadow_execution_and_decision_ledger(self):
        """Test full shadow execution cycle and audit logging."""
        market_signal = {
            "structure": "BULLISH_TREND",
            "zone": "DEMAND_ZONE",
            "phase": "CONTINUATION",
            "htf_bias": "BULLISH",
            "mtf_valid": True,
            "ltf_valid": True,
            "destination_r": 4.5,
            "spread_bps": 2.0,
            "entry_price": 55000.0,
            "stop_price": 54000.0,
            "target_price": 59500.0,
        }
        env = {"regime": "EXPANSION_STABLE", "in_event_window": False}
        gov = {
            "unknown_state_active": False,
            "drawdown_circuit_breaker": False,
            "reactivation_multiplier": 1.0,
        }

        # Step 1: Entry cycle evaluation
        decision = self.trader.process_cycle(
            self.instrument, self.health, 55000.0, market_signal, env, gov
        )
        self.assertEqual(decision.decision, "TRADE")
        self.assertEqual(len(self.trader.active_positions), 1)
        self.assertGreaterEqual(len(self.trader.ledger.records), 1)

        # Step 2: Exit cycle at target price
        market_at_target = dict(market_signal, ltf_valid=False)
        self.trader.process_cycle(
            self.instrument, self.health, 60000.0, market_at_target, env, gov
        )
        self.assertEqual(len(self.trader.active_positions), 0)
        self.assertEqual(len(self.trader.completed_trades), 1)

        # Step 3: Verify metrics
        metrics = self.trader.get_shadow_performance_metrics()
        self.assertEqual(metrics["total_trades"], 1)
        self.assertGreater(metrics["net_r"], 0.0)


def test_suite_integration_sanity():
    """Discoverable function runner."""
    test = TestCanonicalPipelineIntegration()
    test.setUp()
    test.test_market_state_generation()
    test.test_shadow_execution_and_decision_ledger()


if __name__ == "__main__":
    unittest.main()
