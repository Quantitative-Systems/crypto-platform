import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy_candidate_v2.run_backtest import StateMachine, update_state, SwingCache
from market_intelligence.primitives import Candle

def test_state_machine():
    print("--- MANUAL FIXTURE: STATE MACHINE TEST ---")
    sm = StateMachine()
    
    # Fake a SwingCache that returns a target
    class DummySwingCache:
        def get_target(self, idx, direction):
            return 100.0
    sc = DummySwingCache()

    # Step 1: IDLE, Stoch goes to 80 (>= 75)
    # def update_state(sm: StateMachine, st_dir: int, k: float, d: float,
    #                  prev_k: float, prev_d: float, direction: int,
    #                  is_ltf: bool, swing_cache: SwingCache, candle_idx: int):
    update_state(sm, st_dir=1, k=80.0, d=70.0, prev_k=50.0, prev_d=50.0, direction=1, is_ltf=False, swing_cache=sc, candle_idx=1)
    print(f"Step 1: Stoch K=80 -> State: {sm.state}")

    # Step 2: WAITING_PEAK, Stoch goes to 20 (<= 25)
    update_state(sm, st_dir=1, k=20.0, d=30.0, prev_k=80.0, prev_d=70.0, direction=1, is_ltf=False, swing_cache=sc, candle_idx=2)
    print(f"Step 2: Stoch K=20 -> State: {sm.state}")

    # Step 3: WAITING_PULLBACK (HTF/MTF instantly goes to READY if ST is bullish)
    # The previous call already transitioned from WAITING_PEAK to WAITING_PULLBACK.
    # The next update with Stoch staying low
    update_state(sm, st_dir=1, k=22.0, d=25.0, prev_k=20.0, prev_d=30.0, direction=1, is_ltf=False, swing_cache=sc, candle_idx=3)
    print(f"Step 3: Stoch K=22 (HTF/MTF) -> State: {sm.state} (Target: {sm.target_price})")

    # Now test LTF
    print("\n--- LTF State Machine ---")
    sm_ltf = StateMachine()
    update_state(sm_ltf, st_dir=1, k=80.0, d=70.0, prev_k=50.0, prev_d=50.0, direction=1, is_ltf=True, swing_cache=sc, candle_idx=1)
    print(f"LTF Step 1: Stoch K=80 -> State: {sm_ltf.state}")
    
    update_state(sm_ltf, st_dir=1, k=20.0, d=30.0, prev_k=80.0, prev_d=70.0, direction=1, is_ltf=True, swing_cache=sc, candle_idx=2)
    print(f"LTF Step 2: Stoch K=20 -> State: {sm_ltf.state}")
    
    update_state(sm_ltf, st_dir=1, k=22.0, d=25.0, prev_k=20.0, prev_d=30.0, direction=1, is_ltf=True, swing_cache=sc, candle_idx=3)
    print(f"LTF Step 3: Stoch K=22 (LTF) -> State: {sm_ltf.state}")

    # Crossover: K > D and prev_K <= prev_D
    update_state(sm_ltf, st_dir=1, k=30.0, d=25.0, prev_k=22.0, prev_d=25.0, direction=1, is_ltf=True, swing_cache=sc, candle_idx=4)
    print(f"LTF Step 4: Stoch K=30, D=25 -> State: {sm_ltf.state} (Target: {sm_ltf.target_price})")

    # Step 5: Stoch goes back to peak while READY
    update_state(sm_ltf, st_dir=1, k=85.0, d=80.0, prev_k=30.0, prev_d=25.0, direction=1, is_ltf=True, swing_cache=sc, candle_idx=5)
    print(f"LTF Step 5: Stoch K=85 -> State: {sm_ltf.state}")


if __name__ == '__main__':
    test_state_machine()
