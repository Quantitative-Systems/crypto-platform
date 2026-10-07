"""Master Strategy Discovery & Edge Research Runner.

Executes systematic hypothesis testing across:
- 5 Canonical Timeframe Sets (SET 1 to SET 5)
- 4 Core Liquid Crypto Assets (BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT)
- 10 Phase A Strategy Families (F01 to F10)
- 2 Phase Modes (PULLBACK, CONTINUATION)

Enforces:
1. Frozen Market Model (Structure, Key Zones, Phase).
2. Strict zero lookahead causality (signals on LTF close, execution on next-bar open).
3. Adverse-first intrabar collision resolution (SL before TP).
4. Realistic taker fees (7.5 bps) and adverse slippage (2.0 bps).
5. Strict >= 4.0R minimum target floor.
6. 1% max account risk position sizing constraint.
7. Chronological Walk-Forward validation (DEV 60% / VAL 20% / OOS 20%).
8. Comprehensive Section 20 performance metrics recording.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from execution.backtest.engine import CausalBacktestEngine, TradeRecord
from execution.costs.cost_model import CostModel
from market_data.certified_loader import CertifiedSeriesLoader
from market_model.contracts import MarketState
from market_model.state_generator import MarketStateGenerator
from strategy.base import CandidateSignal
from strategy.families import FAMILY_REGISTRY, BaseStrategyFamily

RESULTS_DIR = REPO_ROOT / "research" / "results" / "discovery"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

TIMEFRAME_SETS = {
    "SET_1": {"htf": "1M", "mtf": "1w", "ltf": "1d"},
    "SET_2": {"htf": "1w", "mtf": "1d", "ltf": "4h"},
    "SET_3": {"htf": "1d", "mtf": "4h", "ltf": "1h"},
    "SET_4": {"htf": "4h", "mtf": "1h", "ltf": "15m"},
    "SET_5": {"htf": "1h", "mtf": "15m", "ltf": "3m"},
}


class DiscoveryResearchRunner:
    """Orchestrates systematic hypothesis testing and walk-forward edge validation."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or (REPO_ROOT / "market_data" / "cache")
        self.loader = CertifiedSeriesLoader(cache_dir=self.cache_dir)
        self.backtest_engine = CausalBacktestEngine(
            taker_fee_bps=7.5,
            slippage_bps=2.0,
            min_target_r=4.0,
        )
        self.cost_model = CostModel()

    def load_series_arrays(self, symbol: str, timeframe: str) -> Optional[Dict[str, np.ndarray]]:
        """Load certified series as numpy arrays."""
        try:
            df, _ = self.loader.load(symbol, timeframe)
            if df.empty:
                return None
            ts = df["timestamp"].astype(np.int64) // 10**6  # Ensure ms
            return {
                "timestamps": ts.to_numpy(),
                "opens": df["open"].to_numpy(dtype=float),
                "highs": df["high"].to_numpy(dtype=float),
                "lows": df["low"].to_numpy(dtype=float),
                "closes": df["close"].to_numpy(dtype=float),
                "volumes": df["volume"].to_numpy(dtype=float),
            }
        except Exception as e:
            return None

    def run_experiment(
        self,
        symbol: str,
        set_id: str,
        family_id: str,
        phase_mode: str,
        force_rerun: bool = False,
    ) -> Dict[str, Any]:
        """Execute a single immutable experiment."""
        exp_id = f"EXP_{symbol}_{set_id}_{family_id}_{phase_mode}_V1"
        out_file = RESULTS_DIR / f"{exp_id}.json"

        # Check if already completed and valid with full trade records
        if not force_rerun and out_file.exists():
            with open(out_file, "r") as f:
                existing = json.load(f)
            if "trade_records" in existing:
                return existing

        tfs = TIMEFRAME_SETS[set_id]
        htf_label, mtf_label, ltf_label = tfs["htf"], tfs["mtf"], tfs["ltf"]

        # Load series
        htf_data = self.load_series_arrays(symbol, htf_label)
        mtf_data = self.load_series_arrays(symbol, mtf_label)
        ltf_data = self.load_series_arrays(symbol, ltf_label)

        if not htf_data or not mtf_data or not ltf_data:
            record = {
                "experiment_id": exp_id,
                "status": "REJECTED_MISSING_DATA",
                "symbol": symbol,
                "set_id": set_id,
                "family_id": family_id,
                "phase_mode": phase_mode,
                "error": "One or more series missing from cache",
            }
            with open(out_file, "w") as f:
                json.dump(record, f, indent=2)
            return record

        # Calculate true overlapping causal window
        overlap_start = max(htf_data["timestamps"][0], mtf_data["timestamps"][0], ltf_data["timestamps"][0])
        overlap_end = min(htf_data["timestamps"][-1], mtf_data["timestamps"][-1], ltf_data["timestamps"][-1])

        if overlap_start >= overlap_end:
            record = {
                "experiment_id": exp_id,
                "status": "REJECTED_NO_OVERLAP",
                "symbol": symbol,
                "set_id": set_id,
                "family_id": family_id,
                "phase_mode": phase_mode,
            }
            with open(out_file, "w") as f:
                json.dump(record, f, indent=2)
            return record

        # Filter LTF to overlapping range
        ltf_mask = (ltf_data["timestamps"] >= overlap_start) & (ltf_data["timestamps"] <= overlap_end)
        ltf_idx = np.where(ltf_mask)[0]
        if len(ltf_idx) < 30:
            record = {
                "experiment_id": exp_id,
                "status": "REJECTED_INSUFFICIENT_BARS",
                "symbol": symbol,
                "set_id": set_id,
                "family_id": family_id,
                "phase_mode": phase_mode,
            }
            with open(out_file, "w") as f:
                json.dump(record, f, indent=2)
            return record

        # Initialize Strategy Family
        family_cls = FAMILY_REGISTRY[family_id]
        strategy: BaseStrategyFamily = family_cls(
            timeframe_set_id=set_id,
            htf_label=htf_label,
            mtf_label=mtf_label,
            ltf_label=ltf_label,
            phase_mode=phase_mode,
            min_target_r=4.0,
        )

        # Build causal generator helpers
        htf_gen = MarketStateGenerator(timeframe=htf_label)
        mtf_gen = MarketStateGenerator(timeframe=mtf_label)
        ltf_gen = MarketStateGenerator(timeframe=ltf_label)

        # Slice LTF active arrays
        sub_ltf_ts = ltf_data["timestamps"][ltf_idx]
        sub_ltf_o = ltf_data["opens"][ltf_idx]
        sub_ltf_h = ltf_data["highs"][ltf_idx]
        sub_ltf_l = ltf_data["lows"][ltf_idx]
        sub_ltf_c = ltf_data["closes"][ltf_idx]
        sub_ltf_v = ltf_data["volumes"][ltf_idx]

        n_ltf = len(sub_ltf_c)

        # Chronological Walk-Forward partition boundaries: DEV (60%), VAL (20%), OOS (20%)
        dev_end_idx = int(n_ltf * 0.60)
        val_end_idx = int(n_ltf * 0.80)

        # Signal scanning over LTF bars causally with HTF/MTF memoization
        signals: List[CandidateSignal] = []
        lookback_warmup = 30
        step = 1 if n_ltf <= 1500 else (2 if n_ltf <= 4000 else 4)

        cached_htf_ts = -1
        cached_htf_state = None
        cached_mtf_ts = -1
        cached_mtf_state = None

        for i in range(lookback_warmup, n_ltf, step):
            curr_ltf_ts = sub_ltf_ts[i]

            # 1. Causal HTF State (memoized by latest closed HTF timestamp)
            h_mask = htf_data["timestamps"] <= curr_ltf_ts
            if np.sum(h_mask) < 10:
                continue
            h_idx_end = np.where(h_mask)[0][-1]
            latest_htf_ts = int(htf_data["timestamps"][h_idx_end])

            if latest_htf_ts != cached_htf_ts:
                h_start = max(0, h_idx_end - 150)
                cached_htf_state = htf_gen.generate_state(
                    symbol=symbol,
                    opens=htf_data["opens"][h_start : h_idx_end + 1],
                    highs=htf_data["highs"][h_start : h_idx_end + 1],
                    lows=htf_data["lows"][h_start : h_idx_end + 1],
                    closes=htf_data["closes"][h_start : h_idx_end + 1],
                    timestamps=htf_data["timestamps"][h_start : h_idx_end + 1],
                    volumes=htf_data["volumes"][h_start : h_idx_end + 1],
                )
                cached_htf_ts = latest_htf_ts

            htf_state = cached_htf_state

            # 2. HTF Directional Hypothesis
            direction = strategy.evaluate_htf(htf_state)
            if direction is None:
                continue

            # 3. Causal MTF State (memoized by latest closed MTF timestamp)
            m_mask = mtf_data["timestamps"] <= curr_ltf_ts
            if np.sum(m_mask) < 10:
                continue
            m_idx_end = np.where(m_mask)[0][-1]
            latest_mtf_ts = int(mtf_data["timestamps"][m_idx_end])

            if latest_mtf_ts != cached_mtf_ts:
                m_start = max(0, m_idx_end - 150)
                cached_mtf_state = mtf_gen.generate_state(
                    symbol=symbol,
                    opens=mtf_data["opens"][m_start : m_idx_end + 1],
                    highs=mtf_data["highs"][m_start : m_idx_end + 1],
                    lows=mtf_data["lows"][m_start : m_idx_end + 1],
                    closes=mtf_data["closes"][m_start : m_idx_end + 1],
                    timestamps=mtf_data["timestamps"][m_start : m_idx_end + 1],
                    volumes=mtf_data["volumes"][m_start : m_idx_end + 1],
                )
                cached_mtf_ts = latest_mtf_ts

            mtf_state = cached_mtf_state

            # 4. MTF Setup Validation
            if not strategy.validate_mtf(mtf_state, direction):
                continue

            # 5. Causal LTF State (windowed for high performance)
            l_start = max(0, i - 120)
            ltf_state = ltf_gen.generate_state(
                symbol=symbol,
                opens=sub_ltf_o[l_start : i + 1],
                highs=sub_ltf_h[l_start : i + 1],
                lows=sub_ltf_l[l_start : i + 1],
                closes=sub_ltf_c[l_start : i + 1],
                timestamps=sub_ltf_ts[l_start : i + 1],
                volumes=sub_ltf_v[l_start : i + 1],
            )

            # 6. LTF Entry Confirmation & SL/TP
            confirmed, sl, target = strategy.confirm_ltf_entry(ltf_state, direction)
            if confirmed and sl is not None and target is not None:
                risk_dist = abs(sub_ltf_c[i] - sl)
                if risk_dist <= 0:
                    continue
                target_r = abs(target - sub_ltf_c[i]) / risk_dist
                if target_r >= 4.0:
                    signals.append(
                        CandidateSignal(
                            bar_index=i,
                            direction=direction,
                            entry_price=float(sub_ltf_c[i]),
                            stop_price=float(sl),
                            target_price=float(target),
                            target_r=float(target_r),
                            hypothesis_id=strategy.hypothesis_id,
                            meta={
                                "timestamp_ms": int(curr_ltf_ts),
                                "partition": "DEV" if i < dev_end_idx else ("VAL" if i < val_end_idx else "OOS"),
                            },
                        )
                    )

        # Execute Causal Backtest
        stream_metrics = self.backtest_engine.execute_stream(
            stream_id=exp_id,
            symbol=symbol,
            timeframe_set=set_id,
            hypothesis=f"{family_id}_{phase_mode}",
            ltf_opens=sub_ltf_o,
            ltf_highs=sub_ltf_h,
            ltf_lows=sub_ltf_l,
            ltf_closes=sub_ltf_c,
            ltf_timestamps=sub_ltf_ts,
            signal_candidates=signals,
        )

        # Compute Partitioned Walk-Forward Metrics (DEV, VAL, OOS)
        trades = stream_metrics.trades

        def _calc_partition_metrics(sub_trades: List[TradeRecord]) -> Dict[str, Any]:
            if not sub_trades:
                return {
                    "trade_count": 0, "win_rate": 0.0, "total_r": 0.0,
                    "expectancy_r": 0.0, "profit_factor": 0.0, "max_drawdown_r": 0.0,
                }
            r_vals = [t.realized_r for t in sub_trades]
            wins = [r for r in r_vals if r > 0]
            losses = [r for r in r_vals if r <= 0]
            win_count = len(wins)
            loss_count = len(losses)
            total_r = sum(r_vals)
            gross_win = sum(wins)
            gross_loss = abs(sum(losses))
            pf = gross_win / gross_loss if gross_loss > 0 else (99.0 if gross_win > 0 else 0.0)

            # Drawdown
            equity = np.cumsum(r_vals)
            peak = np.maximum.accumulate(equity)
            dd = peak - equity
            max_dd = float(np.max(dd)) if len(dd) > 0 else 0.0

            return {
                "trade_count": len(sub_trades),
                "win_count": win_count,
                "loss_count": loss_count,
                "win_rate": round(win_count / len(sub_trades), 4),
                "loss_rate": round(loss_count / len(sub_trades), 4),
                "total_r": round(total_r, 2),
                "expectancy_r": round(total_r / len(sub_trades), 4),
                "profit_factor": round(pf, 3),
                "max_drawdown_r": round(max_dd, 2),
                "average_win_r": round(float(np.mean(wins)), 2) if wins else 0.0,
                "average_loss_r": round(float(np.mean(losses)), 2) if losses else 0.0,
            }

        dev_ts_limit = sub_ltf_ts[dev_end_idx]
        val_ts_limit = sub_ltf_ts[val_end_idx]

        dev_trades = [t for t in trades if t.entry_ts < dev_ts_limit]
        val_trades = [t for t in trades if dev_ts_limit <= t.entry_ts < val_ts_limit]
        oos_trades = [t for t in trades if t.entry_ts >= val_ts_limit]

        dev_metrics = _calc_partition_metrics(dev_trades)
        val_metrics = _calc_partition_metrics(val_trades)
        oos_metrics = _calc_partition_metrics(oos_trades)

        long_trades = [t for t in trades if t.direction == 1]
        short_trades = [t for t in trades if t.direction == -1]

        experiment_record = {
            "experiment_id": exp_id,
            "status": "COMPLETED",
            "symbol": symbol,
            "set_id": set_id,
            "family_id": family_id,
            "phase_mode": phase_mode,
            "timeframe_hierarchy": {"htf": htf_label, "mtf": mtf_label, "ltf": ltf_label},
            "testable_period": {
                "start_iso": datetime.fromtimestamp(overlap_start / 1000.0, tz=timezone.utc).isoformat(),
                "end_iso": datetime.fromtimestamp(overlap_end / 1000.0, tz=timezone.utc).isoformat(),
                "total_ltf_bars": n_ltf,
            },
            "overall_metrics": {
                "trade_count": stream_metrics.total_trades,
                "win_count": stream_metrics.win_count,
                "loss_count": stream_metrics.loss_count,
                "win_rate": stream_metrics.win_rate,
                "loss_rate": stream_metrics.loss_rate,
                "total_r": stream_metrics.total_r,
                "expectancy_r": stream_metrics.expectancy_r,
                "profit_factor": stream_metrics.profit_factor,
                "max_drawdown_r": stream_metrics.max_drawdown_r,
                "target_4r_hit_rate": stream_metrics.target_4r_hit_rate,
                "avg_bars_held": stream_metrics.avg_bars_held,
                "fees_bps_roundtrip": 15.0,
                "slippage_bps_roundtrip": 4.0,
            },
            "partitioned_walk_forward": {
                "dev": dev_metrics,
                "val": val_metrics,
                "oos": oos_metrics,
            },
            "direction_performance": {
                "long_trades": len(long_trades),
                "long_total_r": round(sum(t.realized_r for t in long_trades), 2),
                "short_trades": len(short_trades),
                "short_total_r": round(sum(t.realized_r for t in short_trades), 2),
            },
            "edge_qualification": {
                "has_positive_expectancy": stream_metrics.expectancy_r > 0.05,
                "has_positive_oos": oos_metrics["expectancy_r"] > 0.0,
                "has_sufficient_trades": stream_metrics.total_trades >= 15,
                "survives_costs": stream_metrics.expectancy_r > 0.15,
            },
            "trade_records": [
                {
                    "direction": t.direction,
                    "entry_price": round(float(t.entry_px), 2),
                    "exit_price": round(float(t.exit_px), 2),
                    "stop_price": round(float(t.initial_sl), 2),
                    "target_price": round(float(t.target_px), 2),
                    "realized_r": round(float(t.realized_r), 4),
                    "entry_ts": int(t.entry_ts),
                    "exit_ts": int(t.exit_ts),
                    "exit_reason": str(t.exit_reason),
                    "bars_held": int(t.bars_held),
                    "mfe_r": round(float(t.mfe_r), 4),
                    "mae_r": round(float(t.mae_r), 4),
                }
                for t in trades
            ],
        }

        # Save to results/discovery/<EXP_ID>.json
        with open(out_file, "w") as f:
            json.dump(experiment_record, f, indent=2)

        return experiment_record
