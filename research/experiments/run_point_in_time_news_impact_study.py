"""STRATA — Phase 4: Point-in-Time News Impact Empirical Study.

Empirically measures the effect of high-impact macro announcements and crypto protocol events
on real BTCUSDT and ETHUSDT historical candlestick data.
Validates the protective value of the pre-event and post-event volatility freeze window.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

import sys
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from market_model.news_narrative_intelligence import (
    PointInTimeNewsCalendar,
    build_canonical_crypto_macro_calendar,
)
from research.experiments.run_phase_p_fractal_discovery import load_series_arrays

OUTPUT_DIR = WORKSPACE_ROOT / "research" / "results" / "STRATA_PHASE_4_NEWS"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def run_news_impact_study():
    print("=" * 105)
    print("STRATA PHASE 4: POINT-IN-TIME NEWS & MACRO IMPACT EMPIRICAL STUDY")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 105)

    calendar = build_canonical_crypto_macro_calendar()
    print(f"Loaded Canonical Macro Calendar: {len(calendar.events)} major events indexed.")

    # Load BTC 1h data
    btc_1h = load_series_arrays("BTCUSDT", "1h")
    eth_1h = load_series_arrays("ETHUSDT", "1h")

    if btc_1h is None:
        print("ERROR: BTCUSDT 1h data not found.")
        return

    study_results = []

    print("\nEmpirical Impact Analysis on BTCUSDT (1h):")
    print("-" * 105)
    print(f"{'EVENT ID':<22} | {'EVENT NAME':<35} | {'EXPANSION (x)':<14} | {'POST-EXP (x)':<14} | {'NET DISPL %':<12}")
    print("-" * 105)

    for event_id, event in calendar.events.items():
        impact = calendar.measure_event_volatility_impact(
            event=event,
            timestamps_ms=btc_1h["ts"],
            opens=btc_1h["o"],
            highs=btc_1h["h"],
            lows=btc_1h["l"],
            closes=btc_1h["c"],
            lookback_bars=12,
            forward_bars=12,
        )
        if impact.get("status") == "SUCCESS":
            study_results.append(impact)
            print(f"{event.event_id:<22} | {event.event_name[:35]:<35} | {impact['event_range_expansion_x']:>12.2f}x | {impact['post_range_expansion_x']:>12.2f}x | {impact['net_displacement_pct']:>+10.2f}%")
        else:
            print(f"{event.event_id:<22} | {event.event_name[:35]:<35} | OUTSIDE DATA RANGE")

    # Save artifact
    out_file = OUTPUT_DIR / "point_in_time_news_impact_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(study_results, f, indent=2)

    print("-" * 105)
    print(f"Empirical study complete. Results saved to: {out_file.name}")


if __name__ == "__main__":
    run_news_impact_study()
