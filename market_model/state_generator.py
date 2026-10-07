"""MarketState Generator.

Synthesizes Market Structure, Key Zones, Market Phase, and Technical Measurements
into a single canonical, deterministic MarketState snapshot for any timeframe.
"""
from __future__ import annotations

import numpy as np

from market_model.contracts import MarketState, MeasurementsSnapshot
from market_model.key_zones_levels.order_blocks.key_zones_engine import KeyZonesEngine
from market_model.market_structure_trend.trend.structure_engine import StructureEngine
from market_model.phases.pullback.detection.phase_engine import PhaseEngine
from market_tools.indicators.technical_indicators import atr, ema, rsi


class MarketStateGenerator:
    """Generates canonical MarketState snapshots from OHLCV arrays."""

    def __init__(
        self,
        timeframe: str = "1D",
        structure_engine: StructureEngine = None,
        key_zones_engine: KeyZonesEngine = None,
        phase_engine: PhaseEngine = None,
    ):
        self.timeframe = timeframe
        self.structure_engine = structure_engine or StructureEngine(timeframe=timeframe)
        self.key_zones_engine = key_zones_engine or KeyZonesEngine()
        self.phase_engine = phase_engine or PhaseEngine()

    def generate(
        self,
        symbol: str,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray,
        timestamps: np.ndarray,
    ) -> MarketState:
        """Generate a complete MarketState snapshot as of the current bar (index -1)."""
        n = len(closes)
        if n == 0:
            return MarketState(symbol=symbol, timestamp_ms=0, timeframe=self.timeframe, close_price=0.0)

        curr_close = float(closes[-1])
        curr_open = float(opens[-1])
        curr_high = float(highs[-1])
        curr_low = float(lows[-1])
        curr_vol = float(volumes[-1])
        curr_ts = int(timestamps[-1])

        # 1. Compute Structure
        struct = self.structure_engine.compute_structure(opens, highs, lows, closes, timestamps)

        # 2. Compute Key Zones
        zones = self.key_zones_engine.compute_zones(opens, highs, lows, closes, timestamps, struct)

        # 3. Compute Phase
        phase = self.phase_engine.compute_phase(closes, highs, lows, struct)

        # 4. Compute Measurements
        atr_arr = atr(highs, lows, closes, 14)
        curr_atr = float(atr_arr[-1]) if len(atr_arr) else 0.0
        atr_bps = (curr_atr / curr_close * 1e4) if curr_close > 0 else 0.0

        rsi_arr = rsi(closes, 14)
        curr_rsi = float(rsi_arr[-1]) if len(rsi_arr) else 50.0

        vol_sma = float(np.mean(volumes[-20:])) if n >= 20 else curr_vol
        vol_ratio = (curr_vol / vol_sma) if vol_sma > 0 else 1.0

        ema_arr = ema(closes, 50)
        curr_ema_50 = float(ema_arr[-1]) if len(ema_arr) else curr_close

        measurements = MeasurementsSnapshot(
            atr=round(curr_atr, 4),
            atr_bps=round(atr_bps, 1),
            realized_vol=0.0,
            volume_sma_ratio=round(vol_ratio, 2),
            rsi=round(curr_rsi, 2),
            adx=0.0,
            meta={"ema_50": round(curr_ema_50, 4)},
        )

        return MarketState(
            symbol=symbol,
            timestamp_ms=curr_ts,
            timeframe=self.timeframe,
            close_price=curr_close,
            open_price=curr_open,
            high_price=curr_high,
            low_price=curr_low,
            volume=curr_vol,
            structure=struct,
            zones=zones,
            phase=phase,
            measurements=measurements,
        )

    generate_state = generate
