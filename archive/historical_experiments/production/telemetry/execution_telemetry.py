"""
Quantitative Crypto Platform (QCP) — Forward Execution Telemetry Engine.

S1 REMEDIATION (EABG-001):
  - Every record now REQUIRES explicit `environment` and `session_id` fields.
  - Constructing ExecutionTelemetryLogger without both fields raises RuntimeError (fail-closed).
  - Forward execution telemetry is permanently isolated from test/research paths.
  - Contamination manifest written alongside the quarantined historical store.
  - No historical row is ever overwritten (append-only + quarantine header).

ENVIRONMENT VALUES:
  - "FORWARD_PAPER"  — live forward paper daemon (SOL Set 2 active run)
  - "RESEARCH"       — research backtests, historical simulations
  - "TEST"           — automated test suite (always in a temp dir)
  - "BURN_IN"        — controlled burn-in harness
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
import json
import os
import uuid
from typing import Dict, Any, List, Optional

# Permitted environment strings — anything else is rejected at construction time.
PERMITTED_ENVIRONMENTS = frozenset(["FORWARD_PAPER", "RESEARCH", "TEST", "BURN_IN"])

# The canonical forward paper log is the ONLY file that the forward daemon writes to.
# All other environments MUST use an isolated temp/research directory passed explicitly.
FORWARD_PAPER_LOG_NAME = "forward_execution_telemetry.jsonl"
CONTAMINATION_MANIFEST_NAME = "CONTAMINATION_MANIFEST.json"


@dataclass
class TradeTelemetryRecord:
    """Immutable execution telemetry record for a single completed trade.

    REQUIRED fields (S1 remediation):
      environment: One of FORWARD_PAPER | RESEARCH | TEST | BURN_IN
      session_id:  UUID4 string identifying the daemon/harness run that produced this record.
    """
    # ── Provenance (REQUIRED — S1) ──────────────────────────────────────────
    environment: str          # "FORWARD_PAPER" | "RESEARCH" | "TEST" | "BURN_IN"
    session_id: str           # UUID4 — one per daemon/harness invocation

    # ── Identity ─────────────────────────────────────────────────────────────
    trade_id: str
    strategy_id: str
    symbol: str
    timeframe_set: int
    direction: str            # "BUY" (Long) or "SELL" (Short)
    entry_timestamp: int
    exit_timestamp: int
    holding_bars: int
    holding_seconds: int

    # ── Price execution and friction ─────────────────────────────────────────
    expected_entry_price: float
    executed_entry_price: float
    entry_slippage_bps: float
    entry_fee_usd: float

    expected_exit_price: float
    executed_exit_price: float
    exit_slippage_bps: float
    exit_fee_usd: float

    position_units: float
    position_notional_usd: float
    initial_risk_usd: float

    # ── Realized outcomes ────────────────────────────────────────────────────
    exit_reason: str          # "SL_HIT", "TP_HIT", "BREAKEVEN_TRAIL", "TIME_STOP", etc.
    gross_pnl_usd: float
    total_friction_usd: float
    net_pnl_usd: float

    gross_r: float
    friction_r: float
    net_r: float

    # ── Context & Attribution ────────────────────────────────────────────────
    market_regime: str        # "BULL_TREND", "BEAR_TREND", "RANGE_BOUND", etc.
    peak_unrealized_r: float  # Maximum Favorable Excursion (MFE)
    max_adverse_r: float      # Maximum Adverse Excursion (MAE)
    portfolio_heat_at_entry_pct: float
    breakeven_triggered: bool

    def __post_init__(self) -> None:
        if self.environment not in PERMITTED_ENVIRONMENTS:
            raise ValueError(
                f"TradeTelemetryRecord: environment={self.environment!r} is not a "
                f"permitted value. Allowed: {sorted(PERMITTED_ENVIRONMENTS)}"
            )
        if not self.session_id or not isinstance(self.session_id, str) or not self.session_id.strip():
            raise ValueError(
                "TradeTelemetryRecord: session_id must be a non-empty, non-whitespace string (UUID4)."
            )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExecutionTelemetryLogger:
    """
    Appends execution records to an immutable JSONL log file and in-memory buffer.

    S1 REMEDIATION:
      - Both `environment` and `session_id` are REQUIRED at construction time.
      - Omitting either raises RuntimeError immediately (fail-closed).
      - `log_dir` has NO default: callers MUST supply an explicit path.
        The forward daemon supplies the canonical forward-paper directory.
        Tests supply a temporary pytest tmp_path directory.
      - Every record written carries the logger's environment + session_id as
        top-level fields, enabling contamination auditing without re-parsing.
    """

    def __init__(
        self,
        log_dir: str,
        environment: str,
        session_id: str,
    ) -> None:
        # ── S1: Fail-closed — no defaults allowed ───────────────────────────
        if not log_dir:
            raise RuntimeError(
                "ExecutionTelemetryLogger: log_dir is required and has no default. "
                "Callers must supply an explicit path to prevent cross-run contamination."
            )
        if environment not in PERMITTED_ENVIRONMENTS:
            raise RuntimeError(
                f"ExecutionTelemetryLogger: environment={environment!r} is not permitted. "
                f"Allowed: {sorted(PERMITTED_ENVIRONMENTS)}"
            )
        if not session_id or not isinstance(session_id, str):
            raise RuntimeError(
                "ExecutionTelemetryLogger: session_id must be a non-empty string (UUID4)."
            )

        os.makedirs(log_dir, exist_ok=True)
        self.log_dir = log_dir
        self.environment = environment
        self.session_id = session_id
        self.log_file = os.path.join(log_dir, FORWARD_PAPER_LOG_NAME)
        self.records: List[TradeTelemetryRecord] = []
        self.rejection_events: List[Dict[str, Any]] = []

    @classmethod
    def for_forward_paper(cls, log_dir: str, session_id: Optional[str] = None) -> "ExecutionTelemetryLogger":
        """
        Factory for the live forward paper daemon.
        Session ID auto-generated if not provided (one per daemon startup).
        """
        return cls(
            log_dir=log_dir,
            environment="FORWARD_PAPER",
            session_id=session_id or str(uuid.uuid4()),
        )

    @classmethod
    def for_research(cls, log_dir: str, session_id: Optional[str] = None) -> "ExecutionTelemetryLogger":
        """Factory for research backtests and historical simulations."""
        return cls(
            log_dir=log_dir,
            environment="RESEARCH",
            session_id=session_id or str(uuid.uuid4()),
        )

    @classmethod
    def for_test(cls, log_dir: str, session_id: Optional[str] = None) -> "ExecutionTelemetryLogger":
        """Factory for automated test suite — always uses a caller-supplied temp dir."""
        return cls(
            log_dir=log_dir,
            environment="TEST",
            session_id=session_id or str(uuid.uuid4()),
        )

    def record_trade(self, record: TradeTelemetryRecord) -> None:
        """Appends trade telemetry record. Validates provenance fields match logger."""
        if record.environment != self.environment:
            raise ValueError(
                f"Record environment {record.environment!r} does not match "
                f"logger environment {self.environment!r}. Refusing to log."
            )
        if record.session_id != self.session_id:
            raise ValueError(
                f"Record session_id {record.session_id!r} does not match "
                f"logger session_id {self.session_id!r}. Refusing to log."
            )
        self.records.append(record)
        with open(self.log_file, "a") as f:
            f.write(json.dumps(record.to_dict()) + "\n")

    def record_rejection(
        self,
        strategy_id: str,
        symbol: str,
        timestamp: int,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Logs trade rejections (e.g. risk firewall, portfolio heat, correlation limit)."""
        entry = {
            "environment": self.environment,
            "session_id": self.session_id,
            "timestamp": timestamp,
            "strategy_id": strategy_id,
            "symbol": symbol,
            "event": "TRADE_REJECTED",
            "reason": reason,
            "metadata": metadata or {},
            "logged_at": datetime.now(timezone.utc).isoformat(),
        }
        self.rejection_events.append(entry)
        rej_file = os.path.join(self.log_dir, "rejection_telemetry.jsonl")
        with open(rej_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_summary_metrics(self) -> Dict[str, Any]:
        """Calculates aggregate execution quality and performance metrics."""
        if not self.records:
            return {"total_trades": 0, "net_r": 0.0, "expectancy_r": 0.0}

        n = len(self.records)
        net_rs = [r.net_r for r in self.records]
        wins = [r for r in self.records if r.net_r > 0]
        losses = [r for r in self.records if r.net_r < 0]

        total_net_r = sum(net_rs)
        exp_r = total_net_r / n
        win_rate = len(wins) / n
        win_r_sum = sum(w.net_r for w in wins)
        loss_r_sum = abs(sum(l.net_r for l in losses))
        profit_factor = (win_r_sum / loss_r_sum) if loss_r_sum > 0 else float("inf")

        avg_friction_r = sum(r.friction_r for r in self.records) / n
        avg_entry_slip_bps = sum(r.entry_slippage_bps for r in self.records) / n
        avg_exit_slip_bps = sum(r.exit_slippage_bps for r in self.records) / n

        return {
            "environment": self.environment,
            "session_id": self.session_id,
            "total_trades": n,
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": round(win_rate, 4),
            "profit_factor": round(profit_factor, 4),
            "net_r": round(total_net_r, 4),
            "expectancy_r": round(exp_r, 4),
            "avg_friction_r": round(avg_friction_r, 4),
            "avg_entry_slippage_bps": round(avg_entry_slip_bps, 2),
            "avg_exit_slippage_bps": round(avg_exit_slip_bps, 2),
            "total_rejections": len(self.rejection_events),
        }


def write_contamination_manifest(
    log_dir: str,
    total_rows: int,
    unique_rows: int,
    max_repetition: int,
    audit_timestamp_utc: str,
    first_trade_id: str,
    verdict: str = "FAIL_CONTAMINATED_NON_EVIDENCE",
) -> str:
    """
    Write a permanent contamination manifest alongside the quarantined telemetry store.
    The historical file is NEVER modified. This manifest documents its inadmissibility.

    Returns the path to the manifest file written.
    """
    manifest = {
        "schema_version": "1.0",
        "purpose": "CONTAMINATION_QUARANTINE_RECORD",
        "directive": "EABG-001 / Finding F-02",
        "audit_timestamp_utc": audit_timestamp_utc,
        "quarantined_file": os.path.join(log_dir, FORWARD_PAPER_LOG_NAME),
        "total_rows": total_rows,
        "unique_trade_ids": unique_rows,
        "duplicate_rows": total_rows - unique_rows,
        "duplicate_pct": round(100.0 * (total_rows - unique_rows) / max(total_rows, 1), 2),
        "max_single_trade_repetition": max_repetition,
        "first_trade_id_sample": first_trade_id,
        "verdict": verdict,
        "admissibility": "NON_EVIDENCE_CONTAMINATED_SOURCE",
        "instructions": (
            "This file is NEVER to be used as evidence for strategy performance claims. "
            "All metrics derived from it are inadmissible per EABG-001 §F-02. "
            "The historical rows are preserved for audit lineage but must not be re-read "
            "by any capital, promotion, or claim pathway. "
            "New forward-paper records are written to an environment-tagged session "
            "in the same directory with full provenance."
        ),
    }
    manifest_path = os.path.join(log_dir, CONTAMINATION_MANIFEST_NAME)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest_path
