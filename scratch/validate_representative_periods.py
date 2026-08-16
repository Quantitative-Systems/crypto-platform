"""
Step 2: Historical Validation across representative periods:
- 2021 bull expansion
- 2022 bear expansion
- 2023 recovery/chop
- 2024 bull expansion
"""

import sys
import os
import json
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from market_data.warehouse_loader import WarehouseLoader
from market_intelligence.coordinator import LanguageCoordinator
from market_intelligence.primitives import TrendDirection

def ts_to_date(ts):
    return datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')

def date_to_ts(d_str):
    return int(datetime.strptime(d_str, '%Y-%m-%d').timestamp())

def main():
    loader = WarehouseLoader()
    htf_candles = loader.load_history("BTCUSDT", "1D", limit=50000)
    mtf_candles = loader.load_history("BTCUSDT", "4H", limit=50000)

    periods = [
        ("2021 Bull Expansion", "2021-01-01", "2021-04-30"),
        ("2022 Bear Expansion", "2022-01-01", "2022-06-30"),
        ("2023 Recovery / Chop", "2023-01-01", "2023-06-30"),
        ("2024 Bull Expansion", "2024-01-01", "2024-04-30"),
    ]

    coordinator = LanguageCoordinator(buffer_size=300)

    print("================================================================================")
    print("                STEP 2: HISTORICAL VALIDATION OF PERIODS                        ")
    print("================================================================================")

    for name, start_d, end_d in periods:
        start_ts = date_to_ts(start_d)
        end_ts = date_to_ts(end_d)

        period_candles = [c for c in htf_candles if start_ts <= c.timestamp <= end_ts]
        print(f"\n--- Period: {name} ({start_d} to {end_d}, {len(period_candles)} 1D bars) ---")

        # Sample 5 evenly spaced dates in this period
        indices = [0, len(period_candles)//4, len(period_candles)//2, 3*len(period_candles)//4, len(period_candles)-1]
        
        for idx in indices:
            target_candle = period_candles[idx]
            # Find index in full htf_candles
            full_idx = next(i for i, c in enumerate(htf_candles) if c.timestamp == target_candle.timestamp)
            slice_c = htf_candles[max(0, full_idx - 80):full_idx + 1]

            state = coordinator.run(slice_c, symbol="BTCUSDT", timeframe="1D")
            
            # Extract structure details
            swings = state.swings
            seq_swings = state.structure_state.sequence_swings
            ext_swings = [s for s in seq_swings if str(s.scope) == "SwingScope.EXTERNAL"]
            highs = [s for s in seq_swings if "HIGH" in str(s.raw_swing.swing_type)]
            lows = [s for s in seq_swings if "LOW" in str(s.raw_swing.swing_type)]
            
            latest_high_lbl = highs[-1].label if highs else "NONE"
            latest_low_lbl = lows[-1].label if lows else "NONE"
            
            events = state.structure_state.events
            recent_events = [f"{e.event_type.value}({e.direction})" for e in events[-3:]] if events else []

            trend_dir_val = state.trend_state.value if hasattr(state.trend_state, 'value') else str(state.trend_state)
            ext_trend_val = state.structure_state.external_trend.value if hasattr(state.structure_state.external_trend, 'value') else str(state.structure_state.external_trend)
            phase_val = state.phase_state.name if hasattr(state.phase_state, 'name') else str(state.phase_state)
            print(f"Date: {ts_to_date(target_candle.timestamp)} | Price: {target_candle.close:>8.1f} | TrendState: {trend_dir_val:<8} | ExtTrend: {ext_trend_val:<8} | Phase: {phase_val:<12}")
            print(f"   Latest Swings: High[-1]={latest_high_lbl}, Low[-1]={latest_low_lbl} | Swings Total={len(seq_swings)} (Ext={len(ext_swings)})")
            print(f"   Recent Events: {recent_events}")

if __name__ == "__main__":
    main()
