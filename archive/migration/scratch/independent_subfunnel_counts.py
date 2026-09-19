"""
Script to measure independent primitive activity across all 3 timeframes
over the 50,000 candle history to provide full diagnostic transparency.
"""

import sys
import os
import json
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from market_data.warehouse_loader import WarehouseLoader
from market_intelligence.coordinator import LanguageCoordinator
from research.replayer.timeframe_aligner import TimeframeAligner

def main():
    loader = WarehouseLoader()
    htf_candles = loader.load_history("BTCUSDT", "1D", limit=50000)
    mtf_candles = loader.load_history("BTCUSDT", "4H", limit=50000)
    ltf_candles = loader.load_history("BTCUSDT", "1H", limit=50000)

    timeframe_set = TimeframeAligner.get_set("SET_3")
    language_coordinator = LanguageCoordinator(buffer_size=300)

    stats = {
        "htf_bos_events": 0,
        "htf_choch_events": 0,
        "htf_keyzones_total": 0,
        "mtf_bos_events": 0,
        "mtf_choch_events": 0,
        "mtf_keyzones_total": 0,
        "mtf_bullish_trends": 0,
        "mtf_bearish_trends": 0,
        "mtf_ranging_trends": 0,
        "ltf_liquidity_sweeps": 0,
        "ltf_displacement_confirmed": 0,
        "ltf_bos_events": 0,
        "ltf_choch_events": 0,
    }

    _htf_cache = {"key": None, "state": None}
    _mtf_cache = {"key": None, "state": None}

    for i in range(15, len(ltf_candles)):
        current_bar = ltf_candles[i]
        ts = current_bar.timestamp

        ltf_slice = ltf_candles[max(0, i - 150):i + 1]
        mtf_slice = TimeframeAligner.filter_visible_candles(mtf_candles, ts, timeframe_set.mtf, buffer_size=100)
        htf_slice = TimeframeAligner.filter_visible_candles(htf_candles, ts, timeframe_set.htf, buffer_size=80)

        if len(htf_slice) < 5 or len(mtf_slice) < 5 or len(ltf_slice) < 5:
            continue

        htf_key = htf_slice[-1].timestamp if htf_slice else None
        if _htf_cache["key"] != htf_key:
            htf_state = language_coordinator.run(htf_slice, symbol="BTCUSDT", timeframe="1D")
            _htf_cache = {"key": htf_key, "state": htf_state}
            
            # HTF stats
            events = getattr(htf_state.structure_state, 'events', []) or htf_state.events or []
            for e in events:
                if "BOS" in str(e.event_type): stats["htf_bos_events"] += 1
                if "CHOCH" in str(e.event_type): stats["htf_choch_events"] += 1
            stats["htf_keyzones_total"] += len(htf_state.keyzones)
        else:
            htf_state = _htf_cache["state"]

        mtf_key = mtf_slice[-1].timestamp if mtf_slice else None
        if _mtf_cache["key"] != mtf_key:
            mtf_state = language_coordinator.run(mtf_slice, symbol="BTCUSDT", timeframe="4H")
            _mtf_cache = {"key": mtf_key, "state": mtf_state}
            
            # MTF stats
            events = getattr(mtf_state.structure_state, 'events', []) or mtf_state.events or []
            for e in events:
                if "BOS" in str(e.event_type): stats["mtf_bos_events"] += 1
                if "CHOCH" in str(e.event_type): stats["mtf_choch_events"] += 1
            stats["mtf_keyzones_total"] += len(mtf_state.keyzones)
            
            trend = str(mtf_state.trend_state)
            if "BULLISH" in trend: stats["mtf_bullish_trends"] += 1
            elif "BEARISH" in trend: stats["mtf_bearish_trends"] += 1
            else: stats["mtf_ranging_trends"] += 1
        else:
            mtf_state = _mtf_cache["state"]

        ltf_state = language_coordinator.run(ltf_slice, symbol="BTCUSDT", timeframe="1H")
        
        # LTF stats
        for e in ltf_state.events or []:
            if "LIQUIDITY_SWEEP" in str(e.event_type): stats["ltf_liquidity_sweeps"] += 1
            if "BOS" in str(e.event_type): stats["ltf_bos_events"] += 1
            if "CHOCH" in str(e.event_type): stats["ltf_choch_events"] += 1
            
        scorecard = ltf_state.scorecard or {}
        if "DISPLACEMENT_CONFIRMED" in scorecard.get("reason_codes", []):
            stats["ltf_displacement_confirmed"] += 1

    print("INDEPENDENT PRIMITIVE STATS:")
    print(json.dumps(stats, indent=2))

if __name__ == "__main__":
    main()
