"""
Product 01: Engine 01 Telemetry & Chart Visualizer
Outputs detailed terminal tables AND exports interactive HTML charts (research/swing_chart.html).
"""

import sys
import os

# Add project root directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import List
from market_intelligence.primitives import Candle, RawSwing, SwingStatus, SwingType
from market_intelligence.engine_01_raw_swings import RawSwingEngine


def generate_html_chart(candles: List[Candle], swings: List[RawSwing], filename: str = "research/swing_chart.html"):
    """Generates an interactive HTML candlestick chart with overlaid swing markers."""
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Engine 01 - Swing Inspection Chart</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>body {{ font-family: Arial, sans-serif; background-color: #121212; color: #fff; margin: 0; padding: 20px; }}</style>
</head>
<body>
    <h2>🏛️ Engine 01 Visual Chart Inspection</h2>
    <div id="chart" style="width:100%; height:750px;"></div>
    <script>
        var dates = {[c.timestamp for c in candles]};
        var trace_candles = {{
            x: dates, open: {[c.open for c in candles]}, high: {[c.high for c in candles]},
            low: {[c.low for c in candles]}, close: {[c.close for c in candles]},
            type: 'candlestick', name: 'Price'
        }};
        var trace_highs = {{
            x: {[s.timestamp for s in swings if s.swing_type == SwingType.SWING_HIGH]},
            y: {[s.price for s in swings if s.swing_type == SwingType.SWING_HIGH]},
            mode: 'markers+text', type: 'scatter', name: 'Swing Highs',
            text: {[f"'{s.swing_id}'" for s in swings if s.swing_type == SwingType.SWING_HIGH]},
            textposition: 'top center', marker: {{ color: 'red', size: 12, symbol: 'triangle-down' }}
        }};
        var trace_lows = {{
            x: {[s.timestamp for s in swings if s.swing_type == SwingType.SWING_LOW]},
            y: {[s.price for s in swings if s.swing_type == SwingType.SWING_LOW]},
            mode: 'markers+text', type: 'scatter', name: 'Swing Lows',
            text: {[f"'{s.swing_id}'" for s in swings if s.swing_type == SwingType.SWING_LOW]},
            textposition: 'bottom center', marker: {{ color: 'green', size: 12, symbol: 'triangle-up' }}
        }};
        var layout = {{
            title: 'Engine 01 Detected Swings', plot_bgcolor: '#1e1e1e', paper_bgcolor: '#121212',
            font: {{ color: '#ffffff' }}, xaxis: {{ rangeslider: {{ visible: false }} }}
        }};
        Plotly.newPlot('chart', [trace_candles, trace_highs, trace_lows], layout);
    </script>
</body>
</html>"""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w") as f:
        f.write(html_content)
    print(f"\n📈 Interactive Visual Chart saved to: {filename}")


def run_institutional_audit(candles: List[Candle], symbol: str = "BTC/USDT", timeframe: str = "1H", lookback: int = 2):
    engine = RawSwingEngine(swing_lookback=lookback, eq_tolerance_pct=0.001)
    swings = engine.detect_raw_swings(candles, timeframe=timeframe)

    confirmed_highs = [s for s in swings if s.swing_type == SwingType.SWING_HIGH and s.status == SwingStatus.CONFIRMED]
    confirmed_lows = [s for s in swings if s.swing_type == SwingType.SWING_LOW and s.status == SwingStatus.CONFIRMED]
    candidates = [s for s in swings if s.status == SwingStatus.CANDIDATE]
    equal_clusters = [s for s in swings if s.is_equal_extreme]

    print("=" * 110)
    print(f"🏛️ ENGINE 01 INSTITUTIONAL AUDIT REPORT | SYMBOL: {symbol} | TIMEFRAME: {timeframe}")
    print("=" * 110)
    print(f"  • Total Candles Analyzed    : {len(candles)}")
    print(f"  • Confirmed Swing Highs     : {len(confirmed_highs)}")
    print(f"  • Confirmed Swing Lows      : {len(confirmed_lows)}")
    print(f"  • Pending Candidates        : {len(candidates)}")
    print(f"  • Equal High/Low Clusters   : {len(equal_clusters)}")
    print("=" * 110)
    print(f"{'SWING ID':<22} | {'IDX':<4} | {'TYPE':<10} | {'PRICE ($)':<10} | {'DISP %':<7} | {'SCORE':<6} | {'PREV SWING ID'}")
    print("-" * 110)

    for s in swings:
        prev_str = s.prev_swing_id if s.prev_swing_id else "NONE"
        print(f"{s.swing_id:<22} | {s.candle_index:<4} | {s.swing_type.value:<10} | ${s.price:<9.2f} | {s.displacement_pct:<7.2f} | {s.quality_score:<6.1f} | {prev_str}")

    print("=" * 110)

    generate_html_chart(candles, swings)


if __name__ == "__main__":
    sample_candles = [
        Candle(timestamp=1700000000 + i * 3600, open=100.0 + (i % 3), high=102.0 + (i % 3), low=98.0 + (i % 3), close=101.0 + (i % 3), volume=1000.0)
        for i in range(25)
    ]
    sample_candles[5] = Candle(timestamp=1700000000 + 5 * 3600, open=104.0, high=135.0, low=103.0, close=130.0, volume=5000.0)
    sample_candles[12] = Candle(timestamp=1700000000 + 12 * 3600, open=110.0, high=135.02, low=109.0, close=128.0, volume=4000.0)
    sample_candles[18] = Candle(timestamp=1700000000 + 18 * 3600, open=95.0, high=96.0, low=75.0, close=78.0, volume=6000.0)

    run_institutional_audit(sample_candles, symbol="BTC/USDT", timeframe="1H", lookback=2)