"""Standardized Institutional Benchmark Lab.

Implements rigorous comparison of all discovery candidates against 9 standardized benchmarks:
BENCHMARK 0: Buy and hold
BENCHMARK 1: Market Model only (single-timeframe structure without MTF confirmation)
BENCHMARK 2: HTF -> MTF -> LTF canonical baseline
BENCHMARK 3: Current frozen candidate (F08 Trendline / Adaptive Candidate)
BENCHMARK 4: Simple trend following (Donchian / Breakout)
BENCHMARK 5: Simple momentum (RSI / Candle expansion ignition)
BENCHMARK 6: Simple mean reversion (Bollinger Band mean reversion)
BENCHMARK 7: External quantitative benchmark (ICT/SMC Sweep + Displacement)
BENCHMARK 8: Randomized / Null control distribution
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
from execution.backtest.engine import CausalBacktestEngine, TradeRecord
from market_model.contracts import MarketState, StructuralBreakType, TrendDirection
from market_model.state_generator import MarketStateGenerator


@dataclass
class BenchmarkResult:
    benchmark_id: str
    name: str
    symbol: str
    timeframe: str
    total_trades: int
    win_rate: float
    total_r: float
    expectancy_r: float
    profit_factor: float
    max_drawdown_r: float
    sharpe_proxy: float
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "name": self.name,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "total_trades": self.total_trades,
            "win_rate": round(self.win_rate, 4),
            "total_r": round(self.total_r, 2),
            "expectancy_r": round(self.expectancy_r, 4),
            "profit_factor": round(self.profit_factor, 3),
            "max_drawdown_r": round(self.max_drawdown_r, 2),
            "sharpe_proxy": round(self.sharpe_proxy, 3),
            "description": self.description,
        }


class BenchmarkLab:
    """Executes and scores strategies against standardized industry benchmarks."""

    def __init__(
        self,
        taker_fee_bps: float = 5.0,
        slippage_bps: float = 2.0,
    ):
        self.taker_fee_bps = taker_fee_bps
        self.slippage_bps = slippage_bps
        self.engine = CausalBacktestEngine(
            taker_fee_bps=taker_fee_bps,
            slippage_bps=slippage_bps,
            min_target_r=4.0,
        )

    def run_benchmark_0_buy_and_hold(
        self, symbol: str, timeframe: str, closes: np.ndarray, timestamps: np.ndarray
    ) -> BenchmarkResult:
        """BENCHMARK 0: Buy and Hold."""
        if len(closes) < 2:
            return BenchmarkResult("BM_0", "Buy and Hold", symbol, timeframe, 0, 0, 0, 0, 0, 0, 0, "Insufficient bars")

        p0 = float(closes[0])
        p1 = float(closes[-1])
        pct_return = (p1 - p0) / p0 * 100.0

        # Max drawdown of price
        peak = np.maximum.accumulate(closes)
        dd = (peak - closes) / peak * 100.0
        max_dd_pct = float(np.max(dd))

        # Risk units proxy: assuming 1R = 2% initial risk
        r_equiv = (p1 - p0) / (p0 * 0.02)
        mdd_r = max_dd_pct / 2.0

        return BenchmarkResult(
            benchmark_id="BM_0",
            name="Buy and Hold",
            symbol=symbol,
            timeframe=timeframe,
            total_trades=1,
            win_rate=1.0 if p1 > p0 else 0.0,
            total_r=r_equiv,
            expectancy_r=r_equiv,
            profit_factor=99.0 if p1 > p0 else 0.0,
            max_drawdown_r=mdd_r,
            sharpe_proxy=r_equiv / (mdd_r + 1e-4),
            description=f"Passive long exposure: Net {pct_return:.1f}% (Max DD {max_dd_pct:.1f}%)",
        )

    def run_benchmark_4_trend_breakout(
        self, symbol: str, timeframe: str, ltf_data: Dict[str, np.ndarray], window: int = 20
    ) -> BenchmarkResult:
        """BENCHMARK 4: Simple Donchian Trend Following Breakout."""
        c = ltf_data["c"]
        h = ltf_data["h"]
        l = ltf_data["l"]
        o = ltf_data["o"]
        ts = ltf_data["ts"]
        n = len(c)

        trades: List[TradeRecord] = []
        in_pos = 0  # +1 long, -1 short
        entry_idx = 0
        entry_px = 0.0
        sl_px = 0.0
        tp_px = 0.0
        slip_frac = self.slippage_bps / 1e4
        rt_fee = self.taker_fee_bps * 2.0

        for i in range(window + 1, n):
            if in_pos == 0:
                highest_h = np.max(h[i - window : i])
                lowest_l = np.min(l[i - window : i])
                # Long breakout
                if c[i - 1] > highest_h and i < n - 1:
                    in_pos = 1
                    entry_idx = i
                    entry_px = float(o[i]) * (1.0 + slip_frac)
                    risk = abs(entry_px - lowest_l)
                    sl_px = float(lowest_l)
                    tp_px = entry_px + 4.0 * risk
                elif c[i - 1] < lowest_l and i < n - 1:
                    in_pos = -1
                    entry_idx = i
                    entry_px = float(o[i]) * (1.0 - slip_frac)
                    risk = abs(highest_h - entry_px)
                    sl_px = float(highest_h)
                    tp_px = entry_px - 4.0 * risk
            else:
                risk_dist = abs(entry_px - sl_px)
                if risk_dist <= 0:
                    in_pos = 0
                    continue
                hi_bar = float(h[i])
                lo_bar = float(l[i])

                exit_px = None
                exit_reason = None
                if in_pos == 1:
                    if lo_bar <= sl_px:
                        exit_px = sl_px * (1.0 - slip_frac)
                        exit_reason = "SL"
                    elif hi_bar >= tp_px:
                        exit_px = tp_px * (1.0 - slip_frac)
                        exit_reason = "TP"
                elif in_pos == -1:
                    if hi_bar >= sl_px:
                        exit_px = sl_px * (1.0 + slip_frac)
                        exit_reason = "SL"
                    elif lo_bar <= tp_px:
                        exit_px = tp_px * (1.0 + slip_frac)
                        exit_reason = "TP"

                # Time stop after 100 bars
                if exit_px is None and (i - entry_idx) >= 100:
                    exit_px = float(c[i]) * (1.0 - in_pos * slip_frac)
                    exit_reason = "TIME"

                if exit_px is not None:
                    pnl_bps = (exit_px - entry_px) / entry_px * 1e4 * in_pos - rt_fee
                    realized_r = (pnl_bps / 1e4 * entry_px) / risk_dist
                    trades.append(
                        TradeRecord(
                            symbol=symbol,
                            stream_id="BM_4",
                            direction=in_pos,
                            entry_ts=int(ts[entry_idx]),
                            exit_ts=int(ts[i]),
                            entry_px=round(entry_px, 4),
                            exit_px=round(exit_px, 4),
                            initial_sl=round(sl_px, 4),
                            target_px=round(tp_px, 4),
                            initial_risk_dist=round(risk_dist, 4),
                            target_r=4.0,
                            realized_r=round(realized_r, 4),
                            exit_reason=exit_reason,
                            bars_held=i - entry_idx,
                            fee_bps=rt_fee,
                            slippage_bps=self.slippage_bps * 2.0,
                        )
                    )
                    in_pos = 0

        rs = np.array([t.realized_r for t in trades], dtype=float) if trades else np.array([])
        n_t = len(rs)
        if n_t == 0:
            return BenchmarkResult("BM_4", "Simple Trend Following", symbol, timeframe, 0, 0, 0, 0, 0, 0, 0, "No trades generated")

        wins = rs[rs > 0]
        losses = rs[rs < 0]
        tot_r = float(np.sum(rs))
        exp_r = float(np.mean(rs))
        pf = float(np.sum(wins) / abs(np.sum(losses))) if len(losses) > 0 and np.sum(losses) != 0 else 99.0
        cum = np.cumsum(rs)
        pk = np.maximum.accumulate(cum)
        mdd = float(np.max(pk - cum)) if len(cum) else 0.0

        return BenchmarkResult(
            benchmark_id="BM_4",
            name="Simple Trend Following",
            symbol=symbol,
            timeframe=timeframe,
            total_trades=n_t,
            win_rate=float(len(wins) / n_t),
            total_r=tot_r,
            expectancy_r=exp_r,
            profit_factor=min(pf, 99.0),
            max_drawdown_r=mdd,
            sharpe_proxy=exp_r / (np.std(rs) + 1e-4),
            description="Donchian 20-period breakout with 4R target and adverse-first collision",
        )

    def run_benchmark_6_mean_reversion(
        self, symbol: str, timeframe: str, ltf_data: Dict[str, np.ndarray], window: int = 20, num_std: float = 2.0
    ) -> BenchmarkResult:
        """BENCHMARK 6: Simple Bollinger Mean Reversion."""
        c = ltf_data["c"]
        h = ltf_data["h"]
        l = ltf_data["l"]
        o = ltf_data["o"]
        ts = ltf_data["ts"]
        n = len(c)

        trades: List[TradeRecord] = []
        slip_frac = self.slippage_bps / 1e4
        rt_fee = self.taker_fee_bps * 2.0
        in_pos = 0
        entry_idx = 0
        entry_px = 0.0
        sl_px = 0.0
        tp_px = 0.0

        for i in range(window + 1, n):
            window_slice = c[i - window : i]
            mean = np.mean(window_slice)
            std = np.std(window_slice)
            upper = mean + num_std * std
            lower = mean - num_std * std

            if in_pos == 0 and std > 0:
                # Oversold: Buy
                if c[i - 1] < lower and i < n - 1:
                    in_pos = 1
                    entry_idx = i
                    entry_px = float(o[i]) * (1.0 + slip_frac)
                    risk = std * 1.5
                    sl_px = entry_px - risk
                    tp_px = float(mean)
                elif c[i - 1] > upper and i < n - 1:
                    in_pos = -1
                    entry_idx = i
                    entry_px = float(o[i]) * (1.0 - slip_frac)
                    risk = std * 1.5
                    sl_px = entry_px + risk
                    tp_px = float(mean)
            elif in_pos != 0:
                risk_dist = abs(entry_px - sl_px)
                if risk_dist <= 0:
                    in_pos = 0
                    continue
                hi_bar = float(h[i])
                lo_bar = float(l[i])
                exit_px = None
                exit_reason = None

                if in_pos == 1:
                    if lo_bar <= sl_px:
                        exit_px = sl_px * (1.0 - slip_frac)
                        exit_reason = "SL"
                    elif hi_bar >= tp_px:
                        exit_px = tp_px * (1.0 - slip_frac)
                        exit_reason = "TP"
                elif in_pos == -1:
                    if hi_bar >= sl_px:
                        exit_px = sl_px * (1.0 + slip_frac)
                        exit_reason = "SL"
                    elif lo_bar <= tp_px:
                        exit_px = tp_px * (1.0 + slip_frac)
                        exit_reason = "TP"

                if exit_px is None and (i - entry_idx) >= 50:
                    exit_px = float(c[i]) * (1.0 - in_pos * slip_frac)
                    exit_reason = "TIME"

                if exit_px is not None:
                    pnl_bps = (exit_px - entry_px) / entry_px * 1e4 * in_pos - rt_fee
                    realized_r = (pnl_bps / 1e4 * entry_px) / risk_dist
                    trades.append(
                        TradeRecord(
                            symbol=symbol,
                            stream_id="BM_6",
                            direction=in_pos,
                            entry_ts=int(ts[entry_idx]),
                            exit_ts=int(ts[i]),
                            entry_px=round(entry_px, 4),
                            exit_px=round(exit_px, 4),
                            initial_sl=round(sl_px, 4),
                            target_px=round(tp_px, 4),
                            initial_risk_dist=round(risk_dist, 4),
                            target_r=abs(tp_px - entry_px) / risk_dist,
                            realized_r=round(realized_r, 4),
                            exit_reason=exit_reason,
                            bars_held=i - entry_idx,
                            fee_bps=rt_fee,
                            slippage_bps=self.slippage_bps * 2.0,
                        )
                    )
                    in_pos = 0

        rs = np.array([t.realized_r for t in trades], dtype=float) if trades else np.array([])
        n_t = len(rs)
        if n_t == 0:
            return BenchmarkResult("BM_6", "Simple Mean Reversion", symbol, timeframe, 0, 0, 0, 0, 0, 0, 0, "No trades generated")

        wins = rs[rs > 0]
        losses = rs[rs < 0]
        tot_r = float(np.sum(rs))
        exp_r = float(np.mean(rs))
        pf = float(np.sum(wins) / abs(np.sum(losses))) if len(losses) > 0 and np.sum(losses) != 0 else 99.0
        cum = np.cumsum(rs)
        pk = np.maximum.accumulate(cum)
        mdd = float(np.max(pk - cum)) if len(cum) else 0.0

        return BenchmarkResult(
            benchmark_id="BM_6",
            name="Simple Mean Reversion",
            symbol=symbol,
            timeframe=timeframe,
            total_trades=n_t,
            win_rate=float(len(wins) / n_t),
            total_r=tot_r,
            expectancy_r=exp_r,
            profit_factor=min(pf, 99.0),
            max_drawdown_r=mdd,
            sharpe_proxy=exp_r / (np.std(rs) + 1e-4),
            description="Bollinger Bands (20, 2.0) reversion to the 20-SMA mean",
        )
