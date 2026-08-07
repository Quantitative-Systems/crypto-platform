"""
Layer 1 Unit Test: Engine 02 Sequence Labeling
Strict enforcement of the 14-Mandate Contract.
"""

import unittest
from market_intelligence.primitives import RawSwing, SwingType, SwingStatus, SequenceLabel
from market_intelligence.engine_02_sequence import SequenceEngine

class TestEngine02Sequence(unittest.TestCase):

    def setUp(self):
        self.engine = SequenceEngine()

    def _mock_swing(self, price: float, s_type: SwingType, idx: int, uuid_str: str = None) -> RawSwing:
        return RawSwing(
            swing_id=uuid_str or f"MOCK_{idx}", timestamp=1000+idx, price=price,
            swing_type=s_type, candle_index=idx, timeframe="1H",
            status=SwingStatus.CONFIRMED, quality_score=99.5
        )

    def test_01_empty_input(self):
        self.assertEqual(self.engine.assign_sequences([]), [])

    def test_02_one_swing(self):
        seq = self.engine.assign_sequences([self._mock_swing(100.0, SwingType.SWING_HIGH, 1)])
        self.assertEqual(seq[0].label, SequenceLabel.UNKNOWN)

    def test_03_two_highs(self):
        swings = [self._mock_swing(100, SwingType.SWING_HIGH, 1), self._mock_swing(120, SwingType.SWING_HIGH, 2)]
        seq = self.engine.assign_sequences(swings)
        self.assertEqual(seq[0].label, SequenceLabel.UNKNOWN)
        self.assertEqual(seq[1].label, SequenceLabel.HH)

    def test_04_two_lows(self):
        swings = [self._mock_swing(100, SwingType.SWING_LOW, 1), self._mock_swing(90, SwingType.SWING_LOW, 2)]
        seq = self.engine.assign_sequences(swings)
        self.assertEqual(seq[0].label, SequenceLabel.UNKNOWN)
        self.assertEqual(seq[1].label, SequenceLabel.LL)

    def test_05_equal_high(self):
        swings = [self._mock_swing(100, SwingType.SWING_HIGH, 1), self._mock_swing(100, SwingType.SWING_HIGH, 2)]
        seq = self.engine.assign_sequences(swings)
        self.assertEqual(seq[1].label, SequenceLabel.EQH)

    def test_06_equal_low(self):
        swings = [self._mock_swing(90, SwingType.SWING_LOW, 1), self._mock_swing(90, SwingType.SWING_LOW, 2)]
        seq = self.engine.assign_sequences(swings)
        self.assertEqual(seq[1].label, SequenceLabel.EQL)

    def test_07_mixed_sequence(self):
        swings = [
            self._mock_swing(90, SwingType.SWING_LOW, 1),
            self._mock_swing(120, SwingType.SWING_HIGH, 2),
            self._mock_swing(80, SwingType.SWING_LOW, 3), # LL relative to 90
            self._mock_swing(130, SwingType.SWING_HIGH, 4) # HH relative to 120
        ]
        seq = self.engine.assign_sequences(swings)
        self.assertEqual(seq[0].label, SequenceLabel.UNKNOWN)
        self.assertEqual(seq[1].label, SequenceLabel.UNKNOWN)
        self.assertEqual(seq[2].label, SequenceLabel.LL)
        self.assertEqual(seq[3].label, SequenceLabel.HH)

    def test_08_alternating_extremes(self):
        # Highs: 100 -> 90 (LH)
        # Lows: 50 -> 60 (HL)
        swings = [
            self._mock_swing(100, SwingType.SWING_HIGH, 1),
            self._mock_swing(50, SwingType.SWING_LOW, 2),
            self._mock_swing(90, SwingType.SWING_HIGH, 3), # LH
            self._mock_swing(60, SwingType.SWING_LOW, 4)   # HL
        ]
        seq = self.engine.assign_sequences(swings)
        self.assertEqual(seq[2].label, SequenceLabel.LH)
        self.assertEqual(seq[3].label, SequenceLabel.HL)

    def test_09_chronology_preservation(self):
        swings = [self._mock_swing(100, SwingType.SWING_LOW, 3), self._mock_swing(150, SwingType.SWING_HIGH, 7)]
        seq = self.engine.assign_sequences(swings)
        self.assertEqual(seq[0].raw_swing.candle_index, 3)
        self.assertEqual(seq[1].raw_swing.candle_index, 7)

    def test_10_and_13_uuid_integrity(self):
        target_uuid = "SW_HIGH_ALPHA_123"
        raw = self._mock_swing(120, SwingType.SWING_HIGH, 1, target_uuid)
        seq = self.engine.assign_sequences([raw])
        self.assertEqual(seq[0].raw_swing.swing_id, target_uuid)

    def test_11_and_14_metadata_immutability(self):
        raw = self._mock_swing(120, SwingType.SWING_HIGH, 1)
        original_id = id(raw) # Memory address
        seq = self.engine.assign_sequences([raw])
        
        # Verify object reference remains identical (no mutation, just decoration)
        self.assertEqual(id(seq[0].raw_swing), original_id)
        self.assertEqual(seq[0].raw_swing.quality_score, 99.5)

    def test_12_large_dataset_performance(self):
        import time
        swings = [
            self._mock_swing(100 + (i % 10), SwingType.SWING_HIGH if i % 2 == 0 else SwingType.SWING_LOW, i)
            for i in range(100000)
        ]
        start = time.time()
        seq = self.engine.assign_sequences(swings)
        elapsed_ms = (time.time() - start) * 1000
        
        self.assertEqual(len(seq), 100000)
        self.assertTrue(elapsed_ms < 500, f"O(n) failure: took {elapsed_ms:.2f}ms")
        print(f"\n⚡ Engine 02 benchmark: 100k swings in {elapsed_ms:.2f}ms")

if __name__ == "__main__":
    unittest.main()