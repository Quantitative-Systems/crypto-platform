import sys
import os
import json
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from market_data.warehouse_loader import WarehouseLoader
from research.replayer.timeframe_aligner import TimeframeAligner
from strategy_engine.contracts.trade_plan import DirectionalPermission
from strategy_engine.coordinator.strategy_coordinator import StrategyCoordinator
from strategy_engine.lifecycle.candidate_tracker import CandidateState

def main():
    print("Loading data...")
    loader = WarehouseLoader()
    htf_candles = loader.load_history("BTCUSDT", "1D", limit=50000)
    mtf_candles = loader.load_history("BTCUSDT", "4H", limit=50000)
    ltf_candles = loader.load_history("BTCUSDT", "1H", limit=50000)

    print("Aligning...")
    aligner = TimeframeAligner()
    aligner.initialize(htf_candles, mtf_candles, ltf_candles)
    coordinator = StrategyCoordinator()

    funnel = {
        "htf_observations": 0,
        "valid_bias": 0,
        "valid_pullback": 0,
        "mtf_alignment": 0,
        "causal_mtf_kz": 0,
        "valid_mtf_retest": 0,
        "ltf_sweep": 0,
        "displacement": 0,
        "structural_confirmation": 0,
        "rr_approved": 0,
        "completed": 0
    }

    import strategy_engine.hypotheses.pullback_riding as pr
    
    # We will hook into the tracker and hypothesis to count
    for t_idx, ltf_c in enumerate(ltf_candles):
        if t_idx % 10000 == 0:
            print(f"Processed {t_idx} candles")
        
        state = aligner.get_aligned_state(ltf_c.timestamp)
        if not state:
            continue
            
        htf, mtf, ltf = state
        
        funnel["htf_observations"] += 1
        
        bias = htf.directional_permission
        if bias != DirectionalPermission.NO_TRADE:
            funnel["valid_bias"] += 1
            
            is_long = bias == DirectionalPermission.PERMIT_LONG
            htf_interacting_kz = None
            for kz in htf.keyzones:
                kz_type_str = str(getattr(kz, 'zone_type', ''))
                if is_long and ("BULLISH" not in kz_type_str): continue
                if (not is_long) and ("BEARISH" not in kz_type_str): continue
                is_mitigated = "MITIGATED" in str(getattr(kz, 'status', ''))
                high_bound = getattr(kz, 'high_boundary', getattr(kz, 'high', None))
                low_bound = getattr(kz, 'low_boundary', getattr(kz, 'low', None))
                price_in_zone = False
                if high_bound is not None and low_bound is not None:
                    if htf.current_candle:
                        price_in_zone = (htf.current_candle.low <= high_bound and htf.current_candle.high >= low_bound)
                    else:
                        price_in_zone = (low_bound <= htf.current_price <= high_bound)
                if is_mitigated or price_in_zone:
                    htf_interacting_kz = kz
                    break
            
            is_pullback_phase = htf.phase_state is not None and "PULLBACK" in str(htf.phase_state)
            if htf_interacting_kz is not None or is_pullback_phase:
                funnel["valid_pullback"] += 1
                
        # Now check existing candidates
        for c in coordinator.candidate_tracker.get_active_candidates("BTCUSDT", "HYP_A_PULLBACK_RIDING"):
            # State transitions
            pass
            
        plans = coordinator.evaluate_market_state(htf, mtf, ltf)

    print("FUNNEL COUNTS:", json.dumps(funnel, indent=2))

if __name__ == "__main__":
    main()
