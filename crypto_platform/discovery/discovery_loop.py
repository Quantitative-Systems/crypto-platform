"""Crypto Trading Platform — Automated Strategy Discovery & Research Loop.

Autonomously searches strategy parameter spaces, evaluates causal backtests
with realistic costs, screens for forensic defects (lookahead/leakage/collisions),
enforces G1-G7 promotion gates, archives failed candidates, and preserves evidence.

CRITICAL INVARIANT: Strategy Discovery NEVER promotes candidates to LIVE trading.
Discovery promotes strictly to FORWARD PAPER TRADING. Live deployment requires
explicit human authorization, signed deployment manifests, and production safety gates.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from crypto_platform.core.domain import OperatingMode
from qcp_platform.costs import DEFAULT
from qcp_platform.evaluate import apply_g7, evaluate_book
from qcp_platform.portfolio import run_portfolio
from qcp_platform.runner import run_all

logger = logging.getLogger("crypto_platform.discovery")


@dataclass
class DiscoveryCandidate:
    candidate_id: str
    strategy_name: str
    horizon: str
    symbol: str
    parameters: Dict[str, Any]
    verdict: str = "PENDING"
    rejection_reason: str = ""
    stats: Dict[str, Any] = field(default_factory=dict)
    target_environment: str = OperatingMode.PAPER.value


class StrategyDiscoveryEngine:
    """Autonomous quantitative strategy discovery and lifecycle orchestrator."""

    def __init__(
        self,
        results_dir: str = "research/results/crypto_platform",
        failed_archive_dir: str = "research/failed",
    ):
        self.results_dir = results_dir
        self.failed_archive_dir = failed_archive_dir
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.failed_archive_dir, exist_ok=True)
        self.history: List[DiscoveryCandidate] = []

    def run_discovery_campaign(
        self,
        horizons: Optional[List[str]] = None,
        symbols: Optional[List[str]] = None,
        verbose: bool = True,
    ) -> Dict[str, Any]:
        """Executes a full discovery campaign across specified universe."""
        start_ts = time.time()
        now_ms = int(start_ts * 1000)
        if verbose:
            print("=================================================================")
            print("AUTONOMOUS STRATEGY DISCOVERY & VALIDATION CAMPAIGN")
            print("=================================================================")

        # 1. Run causal walk-forward research sweep
        sweep = run_all(horizons=horizons, symbols=symbols, verbose=verbose)

        # 2. Apply G7 portfolio marginal contribution gates
        books_measured = {
            k: v for k, v in sweep.books.items() if v["verdict"].verdict == "MEASURED"
        }
        selected_keys = set()
        portfolio_summary = {}

        if books_measured:
            pf = run_portfolio(books_measured, use_window="oos")
            selected_keys = set(pf["selection"]["selected"])
            portfolio_summary = pf["summary"]
            for k, v in sweep.books.items():
                if v["verdict"].verdict == "MEASURED":
                    apply_g7(
                        v["verdict"],
                        passed=k in selected_keys,
                        reason="no_marginal_sharpe_contribution",
                    )

        # 3. Categorize candidates
        promoted = []
        for k, v in sweep.books.items():
            row = v["verdict"].as_row()
            if v["verdict"].verdict.startswith("PROMOTABLE"):
                # STRICT INVARIANT: Force target environment to PAPER ONLY
                cand = DiscoveryCandidate(
                    candidate_id=f"cand_{k.replace('|', '_')}_{now_ms}",
                    strategy_name=row.get("strategy", ""),
                    horizon=row.get("horizon", ""),
                    symbol=row.get("symbol", ""),
                    parameters=v.get("params", {}),
                    verdict=row.get("verdict", ""),
                    stats=row,
                    target_environment=OperatingMode.PAPER.value,
                )
                promoted.append(cand)

        rejected_rows = [
            r for r in sweep.rows if not r.get("verdict", "").startswith("PROMOTABLE")
        ]

        # 4. Archive failed candidates to research/failed/
        failed_manifest_path = os.path.join(
            self.failed_archive_dir, f"failed_candidates_{now_ms}.json"
        )
        with open(failed_manifest_path, "w") as f:
            json.dump(
                {
                    "timestamp_ms": now_ms,
                    "count": len(rejected_rows),
                    "candidates": rejected_rows,
                },
                f,
                indent=2,
            )

        # 5. Save promoted candidate evidence to research/results/crypto_platform/
        promoted_manifest_path = os.path.join(
            self.results_dir, "discovered_candidates.json"
        )
        promoted_data = [
            {
                "candidate_id": c.candidate_id,
                "strategy_name": c.strategy_name,
                "horizon": c.horizon,
                "symbol": c.symbol,
                "verdict": c.verdict,
                "target_environment": c.target_environment,
                "stats": c.stats,
            }
            for c in promoted
        ]
        with open(promoted_manifest_path, "w") as f:
            json.dump(
                {
                    "timestamp_ms": now_ms,
                    "promoted_count": len(promoted),
                    "target_environment": OperatingMode.PAPER.value,
                    "candidates": promoted_data,
                    "portfolio_contribution": portfolio_summary,
                },
                f,
                indent=2,
            )

        summary = {
            "timestamp_ms": now_ms,
            "elapsed_s": round(time.time() - start_ts, 2),
            "total_candidates_evaluated": len(sweep.rows),
            "promoted_count": len(promoted),
            "rejected_count": len(rejected_rows),
            "promoted_books": [f"{c.strategy_name}_{c.symbol}_{c.horizon}" for c in promoted],
            "target_environment": OperatingMode.PAPER.value,
            "portfolio": portfolio_summary,
            "failed_archive_path": failed_manifest_path,
            "evidence_manifest_path": promoted_manifest_path,
        }

        if verbose:
            print(f"\nDiscovery complete: {len(promoted)} promoted to PAPER / {len(sweep.rows)} tested in {summary['elapsed_s']}s")
            print(f"Failed candidates archived to: {failed_manifest_path}")
            print(f"Promoted candidates saved to: {promoted_manifest_path}")

        return summary
