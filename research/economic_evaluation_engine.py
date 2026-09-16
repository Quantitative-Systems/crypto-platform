"""
QCP Economic Evaluation Engine.
The only sanctioned source of NET economic edge evidence in the platform.

Design laws enforced here:
  1. Every metric is COMPUTED from a checksummed dataset. Nothing is typed in.
  2. Execution is causally ordered: a signal observed on a closed bar can only
     be filled at the NEXT bar's open. Same-bar fills are impossible.
  3. Costs are deducted before any claim of edge (fees, spread, slippage,
     borrow financing).
  4. Every emitted metric carries an EvidenceRecord naming the dataset, its
     SHA-256, the partition, the method and the reproducing command.
  5. When data required by an alpha does not exist, the engine reports
     DATA_UNAVAILABLE rather than substituting a simulation.

A strategy that cannot be measured here is not an economic candidate; it is a
hypothesis.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import sys
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from backtesting.friction_model import FrictionModel
from platform_core.alpha_genome import AlphaGenome, EconomicPerformance
from platform_core.evidence_provenance import EvidenceLedger, ProvenanceClass

KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume", "close_time",
    "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore",
]

METHOD_LABEL = "CAUSAL_NEXT_BAR_OPEN_TRIPLE_BARRIER_V1"

#: Canonical chronological research partitions (README governance contract).
PARTITIONS: List[Tuple[str, str, str]] = [
    ("DEV", "2021-01-01", "2022-12-31"),
    ("VAL", "2023-01-01", "2023-12-31"),
    ("OOS", "2024-01-01", "2026-12-31"),
]

TIMEFRAME_HOURS: Dict[str, float] = {
    "1m": 1.0 / 60.0, "5m": 5.0 / 60.0, "15m": 0.25, "1h": 1.0,
    "4h": 4.0, "1d": 24.0, "1w": 168.0, "1M": 720.0,
}


@dataclass
class DatasetProvenance:
    """Immutable provenance descriptor for one loaded market series."""

    dataset_id: str
    symbol: str
    timeframe: str
    venue: str
    row_count: int
    start_utc: str
    end_utc: str
    file_path: str
    sha256: str
    ohlc_invariants_ok: bool
    monotonic_timestamps: bool
    certification_status: str
    research_eligible: bool
    provenance: ProvenanceClass
    generated_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["provenance"] = self.provenance.value
        return d


class CertifiedSeriesLoader:
    """
    Loads real Binance kline archives from the local warehouse and asserts their
    integrity before any research use.

    Certification status is resolved from the repository's dataset manifest
    registry (scratch/dataset_manifests.json) when available. A missing series
    raises instead of silently substituting generated data.
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        manifest_path: Optional[Path] = None,
    ):
        repo_root = Path(__file__).resolve().parent.parent
        self.cache_dir = Path(cache_dir) if cache_dir else repo_root / "market_data" / "cache"
        self.manifest_path = (
            Path(manifest_path) if manifest_path
            else repo_root / "scratch" / "dataset_manifests.json"
        )
        self._manifest_cache: Optional[Dict[str, Any]] = None

    @staticmethod
    def _sha256_file(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    def available_series(self) -> List[Tuple[str, str]]:
        """Returns the (symbol, timeframe) pairs actually present in the warehouse."""
        found: List[Tuple[str, str]] = []
        for path in sorted(self.cache_dir.glob("binance_*_*.json")):
            parts = path.stem.split("_")
            if len(parts) != 3:
                continue
            _, raw_symbol, timeframe = parts
            if not raw_symbol.upper().endswith("USDT") or len(raw_symbol) <= 4:
                continue
            found.append((f"{raw_symbol[:-4]}/USDT", timeframe))
        return found

    def _load_manifests(self) -> Dict[str, Any]:
        if self._manifest_cache is not None:
            return self._manifest_cache
        self._manifest_cache = {}
        if self.manifest_path.exists():
            with open(self.manifest_path, "r") as f:
                payload = json.load(f)
            for m in payload.get("manifests", []):
                key = f"{m.get('symbol')}::{m.get('timeframe')}"
                self._manifest_cache[key] = m
        return self._manifest_cache

    def _resolve_certification(
        self, symbol: str, timeframe: str, sha256: str
    ) -> Tuple[str, bool]:
        manifest = self._load_manifests().get(f"{symbol}::{timeframe}")
        if not manifest:
            return ("UNCERTIFIED", False)
        checksum_matches = manifest.get("sha256_checksum") == sha256
        status = manifest.get("certification_status", "UNCERTIFIED")
        eligible = bool(manifest.get("research_eligibility", False)) and checksum_matches
        if not checksum_matches:
            status = f"{status}_CHECKSUM_MISMATCH"
        return (status, eligible)

    def load(self, symbol: str, timeframe: str = "4h") -> Tuple[pd.DataFrame, DatasetProvenance]:
        """
        Loads a real series. Raises FileNotFoundError when the series is absent
        so callers cannot silently substitute fabricated data.
        """
        clean = symbol.replace("/", "").replace("-", "").upper()
        path = self.cache_dir / f"binance_{clean}_{timeframe}.json"
        if not path.exists():
            raise FileNotFoundError(
                f"NO_CERTIFIED_SERIES_FOR:{symbol}:{timeframe} at {path}. "
                "QCP does not fabricate market data; ingest the dataset first."
            )

        with open(path, "r") as f:
            raw = json.load(f)

        sha256 = self._sha256_file(path)
        df = pd.DataFrame(raw, columns=KLINE_COLUMNS)
        df = df.drop(columns=["ignore"]).astype(float)
        df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        df = df[["timestamp", "open", "high", "low", "close", "volume", "quote_volume", "trades"]]
        df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)

        ohlc_ok = bool(
            (
                (df["high"] >= df[["open", "close", "low"]].max(axis=1))
                & (df["low"] <= df[["open", "close", "high"]].min(axis=1))
                & (df[["open", "high", "low", "close"]] > 0).all(axis=1)
            ).all()
        )
        monotonic = bool(df["timestamp"].is_monotonic_increasing)

        status, eligible = self._resolve_certification(symbol, timeframe, sha256)
        provenance = (
            ProvenanceClass.MEASURED_CERTIFIED_DATA
            if eligible else ProvenanceClass.MEASURED_UNCERTIFIED_DATA
        )

        descriptor = DatasetProvenance(
            dataset_id=f"binance_{clean}_{timeframe}_{sha256[:12]}",
            symbol=symbol,
            timeframe=timeframe,
            venue="Binance",
            row_count=int(len(df)),
            start_utc=df["timestamp"].iloc[0].isoformat(),
            end_utc=df["timestamp"].iloc[-1].isoformat(),
            file_path=str(path),
            sha256=sha256,
            ohlc_invariants_ok=ohlc_ok,
            monotonic_timestamps=monotonic,
            certification_status=status,
            research_eligible=eligible,
            provenance=provenance,
        )
        return df, descriptor


@dataclass
class BacktestConfig:
    """Execution and risk geometry for the causal triple-barrier simulation."""

    atr_period: int = 14
    stop_atr_multiple: float = 2.0
    target_r_multiple: float = 2.0
    max_holding_bars: int = 20
    apply_borrow_financing: bool = True


@dataclass
class SimulatedTrade:
    entry_time: str
    exit_time: str
    direction: int
    entry_price: float
    exit_price: float
    stop_price: float
    target_price: float
    bars_held: int
    exit_reason: str
    gross_r: float
    net_r: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PartitionMetrics:
    partition: str
    start_utc: str
    end_utc: str
    performance: EconomicPerformance
    metrics_available: bool
    trade_count: int = 0
    note: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["performance"] = asdict(self.performance)
        return d


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Wilder ATR computed causally: ATR[i] uses only bars <= i."""
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


class CausalTripleBarrierBacktester:
    """
    Event-driven, strictly causal backtester.

    A signal computed on the close of bar i can only be filled at the open of
    bar i+1. Stops are resolved before targets on any bar containing both
    (ADVERSE_FIRST collision invariant, matching the platform's canonical
    execution contract).
    """

    def __init__(
        self,
        friction: Optional[FrictionModel] = None,
        config: Optional[BacktestConfig] = None,
    ):
        self.friction = friction or FrictionModel()
        self.config = config or BacktestConfig()
        self.last_fee_r: List[float] = []
        self.last_borrow_r: List[float] = []

    def _fee_r(self, entry_fill: float, risk_per_unit: float) -> float:
        roundtrip_fee_pct = 2.0 * self.friction.taker_fee_pct
        return (entry_fill * roundtrip_fee_pct) / risk_per_unit

    def _borrow_r(self, entry_fill: float, risk_per_unit: float, holding_hours: float) -> float:
        if not self.config.apply_borrow_financing:
            return 0.0
        borrow_apr = 0.06  # canonical margin borrow financing
        return (entry_fill * borrow_apr * (holding_hours / 8760.0)) / risk_per_unit

    def simulate(
        self, df: pd.DataFrame, signal: np.ndarray, bar_hours: float
    ) -> List[SimulatedTrade]:
        cfg = self.config
        atr = compute_atr(df, cfg.atr_period)
        opens = df["open"].to_numpy()
        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()
        closes = df["close"].to_numpy()
        ts = df["timestamp"]
        atr_arr = atr.to_numpy()

        trades: List[SimulatedTrade] = []
        n = len(df)
        i = cfg.atr_period

        while i < n - 1:
            direction = int(signal[i]) if signal is not None else 0
            if direction == 0 or not np.isfinite(atr_arr[i]) or atr_arr[i] <= 0:
                i += 1
                continue

            entry_bar = i + 1  # next-bar open execution (no same-bar fills)
            raw_entry = opens[entry_bar]
            risk_per_unit = cfg.stop_atr_multiple * atr_arr[i]
            if risk_per_unit <= 0 or raw_entry <= 0:
                i += 1
                continue

            if direction > 0:
                entry_fill = self.friction.calculate_buy_fill(raw_entry)
                stop = entry_fill - risk_per_unit
                target = entry_fill + cfg.target_r_multiple * risk_per_unit
            else:
                entry_fill = self.friction.calculate_sell_fill(raw_entry)
                stop = entry_fill + risk_per_unit
                target = entry_fill - cfg.target_r_multiple * risk_per_unit

            exit_price = None
            exit_bar = None
            exit_reason = None

            for j in range(entry_bar, min(entry_bar + cfg.max_holding_bars, n)):
                if direction > 0:
                    hit_stop, hit_target = lows[j] <= stop, highs[j] >= target
                else:
                    hit_stop, hit_target = highs[j] >= stop, lows[j] <= target

                if hit_stop:  # adverse-first collision invariant
                    exit_price, exit_bar, exit_reason = stop, j, "STOP_LOSS"
                    break
                if hit_target:
                    exit_price, exit_bar, exit_reason = target, j, "TAKE_PROFIT"
                    break

            if exit_price is None:
                exit_bar = min(entry_bar + cfg.max_holding_bars, n) - 1
                exit_price = closes[exit_bar]
                exit_reason = "TIME_STOP"

            if direction > 0:
                exit_fill = self.friction.calculate_sell_fill(exit_price)
                gross_r = (exit_fill - entry_fill) / risk_per_unit
            else:
                exit_fill = self.friction.calculate_buy_fill(exit_price)
                gross_r = (entry_fill - exit_fill) / risk_per_unit

            bars_held = exit_bar - entry_bar + 1
            fee_r = self._fee_r(entry_fill, risk_per_unit)
            borrow_r = self._borrow_r(entry_fill, risk_per_unit, bars_held * bar_hours)
            net_r = gross_r - fee_r - borrow_r

            trades.append(SimulatedTrade(
                entry_time=ts.iloc[entry_bar].isoformat(),
                exit_time=ts.iloc[exit_bar].isoformat(),
                direction=direction,
                entry_price=float(entry_fill),
                exit_price=float(exit_fill),
                stop_price=float(stop),
                target_price=float(target),
                bars_held=int(bars_held),
                exit_reason=exit_reason,
                gross_r=float(gross_r),
                net_r=float(net_r),
            ))

            # No overlapping positions: resume scanning after the trade closes.
            i = exit_bar + 1

        return trades


def _metrics_from_returns(
    net: np.ndarray, gross: np.ndarray, years: float, hurdle_rate_r: float = 0.20
) -> EconomicPerformance:
    """Computes measured economic statistics from realised trade returns."""
    n = int(len(net))
    if n == 0:
        return EconomicPerformance()

    mean_net = float(np.mean(net))
    mean_gross = float(np.mean(gross))
    se = float(np.std(net, ddof=1) / math.sqrt(n)) if n > 1 else 0.0

    wins, losses = net[net > 0], net[net < 0]
    win_rate = float(len(wins) / n * 100.0)
    gross_profit, gross_loss = float(wins.sum()), float(abs(losses.sum()))
    if gross_loss > 0:
        profit_factor = min(999.0, gross_profit / gross_loss)
    else:
        profit_factor = 999.0 if gross_profit > 0 else 0.0

    cum = np.cumsum(net)
    peak = np.maximum.accumulate(cum)
    max_drawdown_r = float(abs((cum - peak).min())) if n > 0 else 0.0

    sd = float(np.std(net, ddof=1)) if n > 1 else 0.0
    trades_per_year = n / years if years > 0 else 0.0
    if sd > 0 and trades_per_year > 0:
        annualized_sharpe = float((mean_net / sd) * math.sqrt(trades_per_year))
    else:
        annualized_sharpe = 0.0

    total_r = float(cum[-1])
    calmar_ratio = float(total_r / max_drawdown_r) if max_drawdown_r > 0 else 0.0

    return EconomicPerformance(
        gross_edge_r=round(mean_gross, 6),
        net_edge_r=round(mean_net, 6),
        uncertainty_se=round(se, 6),
        trade_count=n,
        win_rate=round(win_rate, 4),
        profit_factor=round(profit_factor, 4),
        max_drawdown_r=round(max_drawdown_r, 6),
        annualized_sharpe=round(annualized_sharpe, 4),
        calmar_ratio=round(calmar_ratio, 4),
        hurdle_rate_r=hurdle_rate_r,
    )


@dataclass
class EvaluationResult:
    alpha_id: str
    status: str  # MEASURED | DATA_UNAVAILABLE | DATA_INTEGRITY_FAILURE | INSUFFICIENT_TRADES
    symbol: str
    timeframe: str
    dataset: Optional[DatasetProvenance]
    overall: Optional[PartitionMetrics]
    partitions: Dict[str, PartitionMetrics]
    ledger: EvidenceLedger
    trades: List[SimulatedTrade]
    notes: List[str]
    reproducible_command: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alpha_id": self.alpha_id,
            "status": self.status,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "dataset": self.dataset.to_dict() if self.dataset else None,
            "overall": self.overall.to_dict() if self.overall else None,
            "partitions": {k: v.to_dict() for k, v in self.partitions.items()},
            "evidence_ledger": self.ledger.to_dict(),
            "trade_count": len(self.trades),
            "notes": self.notes,
            "reproducible_command": self.reproducible_command,
        }


class EconomicEvaluationEngine:
    """
    Turns an alpha specification into measured economic evidence — or an honest
    refusal to produce a number.

    The engine NEVER fills in a metric it did not compute.
    """

    def __init__(
        self,
        loader: Optional[CertifiedSeriesLoader] = None,
        backtester: Optional[CausalTripleBarrierBacktester] = None,
        min_trades_per_partition: int = 30,
    ):
        self.loader = loader or CertifiedSeriesLoader()
        self.backtester = backtester or CausalTripleBarrierBacktester()
        self.min_trades_per_partition = min_trades_per_partition

    def evaluate(
        self,
        genome: AlphaGenome,
        signal_fn: Callable[[pd.DataFrame], np.ndarray],
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        partitions: Optional[List[Tuple[str, str, str]]] = None,
    ) -> EvaluationResult:
        symbol = symbol or (genome.asset_universe[0] if genome.asset_universe else "BTC/USDT")
        timeframe = timeframe or genome.timeframe
        windows = partitions or PARTITIONS
        ledger = EvidenceLedger(alpha_id=genome.alpha_id)
        notes: List[str] = []
        command = (
            f"PYTHONPATH=. python3 -m research.economic_evaluation_engine "
            f"--alpha {genome.alpha_id} --symbol {symbol} --timeframe {timeframe}"
        )

        def _fail(status: str, reason: str) -> EvaluationResult:
            ledger.record(
                "evaluation_status", 0.0, ProvenanceClass.UNAVAILABLE,
                method="EVIDENCE_ADMISSION_CONTROL", note=reason,
            )
            notes.append(reason)
            return EvaluationResult(
                alpha_id=genome.alpha_id, status=status, symbol=symbol, timeframe=timeframe,
                dataset=None, overall=None, partitions={}, ledger=ledger, trades=[],
                notes=notes, reproducible_command=command,
            )

        try:
            df, dataset = self.loader.load(symbol, timeframe)
        except FileNotFoundError as exc:
            return _fail("DATA_UNAVAILABLE", str(exc))

        if not dataset.ohlc_invariants_ok or not dataset.monotonic_timestamps:
            return _fail(
                "DATA_INTEGRITY_FAILURE",
                f"Dataset failed integrity invariants (ohlc_ok={dataset.ohlc_invariants_ok}, "
                f"monotonic={dataset.monotonic_timestamps}).",
            )

        signal = signal_fn(df)
        if signal is None or len(signal) != len(df):
            return _fail("DATA_UNAVAILABLE", "Signal function returned no usable causal signal.")

        bar_hours = TIMEFRAME_HOURS.get(timeframe, 4.0)
        trades = self.backtester.simulate(df, np.asarray(signal), bar_hours)

        if len(trades) < self.min_trades_per_partition:
            ledger.record(
                "trade_count", float(len(trades)), ProvenanceClass.UNAVAILABLE,
                method=METHOD_LABEL, note="Below minimum trade count for inference.",
            )
            ledger.record(
                "net_edge_r", 0.0, ProvenanceClass.UNAVAILABLE,
                method=METHOD_LABEL, note="Not computed: insufficient trades.",
            )
            notes.append(f"INSUFFICIENT_TRADES:{len(trades)}")
            return EvaluationResult(
                alpha_id=genome.alpha_id, status="INSUFFICIENT_TRADES", symbol=symbol,
                timeframe=timeframe, dataset=dataset, overall=None, partitions={},
                ledger=ledger, trades=trades, notes=notes, reproducible_command=command,
            )

        return self._measure_partitions(
            genome, dataset, trades, windows, ledger, notes, command, symbol, timeframe
        )

    def _measure_partitions(
        self, genome, dataset, trades, windows, ledger, notes, command, symbol, timeframe
    ) -> EvaluationResult:
        partition_metrics: Dict[str, PartitionMetrics] = {}

        for name, start, end in windows:
            subset = [t for t in trades if start <= t.entry_time[:10] <= end]
            if len(subset) < self.min_trades_per_partition:
                partition_metrics[name] = PartitionMetrics(
                    partition=name, start_utc=start, end_utc=end,
                    performance=EconomicPerformance(), metrics_available=False,
                    trade_count=len(subset),
                    note=f"INSUFFICIENT_TRADES:{len(subset)}",
                )
                continue

            net = np.array([t.net_r for t in subset])
            gross = np.array([t.gross_r for t in subset])
            first = datetime.fromisoformat(subset[0].entry_time)
            last = datetime.fromisoformat(subset[-1].exit_time)
            years = max(1e-6, (last - first).days / 365.25)
            perf = _metrics_from_returns(net, gross, years, genome.performance.hurdle_rate_r)

            partition_metrics[name] = PartitionMetrics(
                partition=name, start_utc=start, end_utc=end,
                performance=perf, metrics_available=True, trade_count=len(subset),
            )

            for metric in (
                "gross_edge_r", "net_edge_r", "trade_count", "win_rate",
                "profit_factor", "max_drawdown_r", "uncertainty_se",
                "annualized_sharpe", "calmar_ratio",
            ):
                ledger.record(
                    metric=metric,
                    value=float(getattr(perf, metric)),
                    provenance=dataset.provenance,
                    method=METHOD_LABEL,
                    source_dataset_id=dataset.dataset_id,
                    source_dataset_sha256=dataset.sha256,
                    partition=name,
                    reproducible_command=command,
                )

        available = {k: v for k, v in partition_metrics.items() if v.metrics_available}
        overall = None
        if available:
            overall = available.get("OOS") or available.get("VAL") or list(available.values())[-1]
            if overall.partition != "OOS":
                notes.append(f"NO_OOS_MEASURED:primary_partition={overall.partition}")

        if dataset.provenance is ProvenanceClass.MEASURED_UNCERTIFIED_DATA:
            notes.append("DATASET_UNCERTIFIED:metrics_measured_but_uncertified")

        status = "MEASURED" if overall is not None else "INSUFFICIENT_TRADES"
        return EvaluationResult(
            alpha_id=genome.alpha_id, status=status, symbol=symbol, timeframe=timeframe,
            dataset=dataset, overall=overall, partitions=partition_metrics,
            ledger=ledger, trades=trades, notes=notes, reproducible_command=command,
        )
