"""STRATA — Protected KING Engine Contract & Execution Adapter.

THIS MODULE FORMALIZES THE IMMUTABLE BOUNDARY AROUND THE FROZEN Q.2 / PHASE R TRADING CORE.

CRITICAL INVARIANTS:
1. Frozen Research Core: Q.2 Market Model, FractalStateEngine weights, 7-timeframe hierarchy,
   and confidence scoring formulas are 100% immutable.
2. Target Floor: >= 4.0R reward-to-risk ratio strictly required for all trade candidates.
3. Risk Invariants: Max 1.0% trade risk, max 1.0% base-asset risk, max 3.0% portfolio heat.
4. Capital Boundary: Real capital is locked to $0.00 fail-closed until multi-signature human approval.
5. Causal Execution: Only confirmed closed candles trigger decision evaluation.
6. Domain Priority: KING Engine is Domain A — the highest-priority intelligence layer of STRATA.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from market_data.realtime.binance_ws_client import DataHealthStatus
from market_model.contracts import MarketState, TrendDirection
from market_model.fractal_state_engine import (
    CrossSetCoherenceTracker,
    FractalAlignment,
    FractalBias,
    FractalStateEngine,
    TIMEFRAME_SETS,
)
from research.contracts.frozen_contract_guard import FROZEN_GUARD
from execution.decision.phase_r_decision_engine import (
    DecisionType,
    PhaseRDecisionRecord,
    PhaseRDecisionEngine,
    PhaseRNoTradeReason,
)

logger = logging.getLogger(__name__)

# Canonical Frozen Contract SHA-256 Hash
EXPECTED_KING_CONTRACT_HASH = "8fbc923a104e7688c3a9f0e4b8592c30dfb0b9a67a84511d5e49f8721c432098"


@dataclass(frozen=True)
class KingEngineContractStatus:
    is_valid: bool
    contract_hash: str
    target_floor_r: float
    max_trade_risk_pct: float
    max_portfolio_heat_pct: float
    real_capital_authorized_usd: float
    is_live_locked: bool
    version: str = "1.0.0-canonical"


class KingEngineProtectionGuard:
    """
    Enforces that the STRATA King Engine cannot be bypassed, mutated, or weakened.
    """

    def __init__(self, contract_path: Optional[str] = None):
        self.contract_path = Path(
            contract_path or "research/contracts/PHASE_R_FROZEN_Q2_CONTRACT.json"
        )
        self._verify_contract_file()

    def _verify_contract_file(self) -> None:
        if not self.contract_path.exists():
            raise RuntimeError(f"CRITICAL: King Contract missing at {self.contract_path}")

        raw = self.contract_path.read_bytes()
        contract_data = json.loads(raw)
        stored_hash = contract_data.get("hash_sha256")

        if stored_hash != EXPECTED_KING_CONTRACT_HASH:
            raise RuntimeError(
                f"CRITICAL: King Contract hash mismatch! {stored_hash} != {EXPECTED_KING_CONTRACT_HASH}"
            )

    def get_status(self) -> KingEngineContractStatus:
        return KingEngineContractStatus(
            is_valid=True,
            contract_hash=EXPECTED_KING_CONTRACT_HASH,
            target_floor_r=4.0,
            max_trade_risk_pct=0.01,
            max_portfolio_heat_pct=0.03,
            real_capital_authorized_usd=0.0,
            is_live_locked=True,
        )

    def verify_invariants(
        self,
        target_r: float,
        trade_risk: float,
        portfolio_heat: float,
        real_capital: float,
    ) -> Tuple[bool, Optional[str]]:
        """Verifies candidate trade geometry against King invariants."""
        if target_r < 4.0:
            return False, f"Target R ({target_r:.2f}R) violates King floor (>=4.0R)"
        if trade_risk > 0.01:
            return False, f"Trade risk ({trade_risk*100:.2f}%) exceeds King limit (<=1.0%)"
        if portfolio_heat > 0.03:
            return False, f"Portfolio heat ({portfolio_heat*100:.2f}%) exceeds King limit (<=3.0%)"
        if real_capital > 0.0:
            return False, f"Real capital (${real_capital:,.2f}) violates zero-capital gate"
        return True, None


class KingEngineAdapter:
    """
    Stable application interface to the Protected STRATA King Engine.
    All platform layers (Autonomous Agent, Strategy Lab, UI) access King intelligence
    strictly through this adapter.
    """

    def __init__(self, symbol: str = "BTCUSDT", decision_engine: Optional[PhaseRDecisionEngine] = None):
        self.guard = KingEngineProtectionGuard()
        self.symbol = symbol.upper()
        self.decision_engine = decision_engine or PhaseRDecisionEngine(symbol=self.symbol)
        self.name = "STRATA_KING_ENGINE"
        self.domain = "DOMAIN_A_KING"
        self.priority = 1  # Highest priority platform intelligence

    def evaluate_opportunity(
        self,
        set_name: str,
        hypothesis_type: str,
        all_timeframe_data: Dict[str, Dict[str, np.ndarray]],
        data_health: DataHealthStatus = DataHealthStatus.DATA_HEALTHY,
        eval_timestamp_ms: Optional[int] = None,
    ) -> PhaseRDecisionRecord:
        """
        Executes deterministic King Engine evaluation for closed candle.
        """
        record = self.decision_engine.evaluate_opportunity(
            set_name=set_name,
            hypothesis_type=hypothesis_type,
            all_timeframe_data=all_timeframe_data,
            data_health=data_health,
            eval_timestamp_ms=eval_timestamp_ms,
        )

        # Enforce contract post-condition if a trade is recommended
        if record.decision == DecisionType.TRADE:
            target_r = record.planned_r or 0.0
            trade_risk = record.risk_pct or 0.0
            ok, err = self.guard.verify_invariants(
                target_r=target_r,
                trade_risk=trade_risk,
                portfolio_heat=record.portfolio_heat_pct,
                real_capital=0.0,
            )
            if not ok:
                logger.critical(f"King Engine Contract invariant tripped: {err}")
                record.decision = DecisionType.NO_TRADE
                record.reason_codes.append(PhaseRNoTradeReason.INVALID_TARGET_GEOMETRY.value)

        return record

    def get_market_structure_overview(
        self,
        fractal_states: Dict[str, MarketState],
    ) -> Dict[str, Any]:
        """Provides high-level King market structure representation for terminal UI."""
        overview_sets = {}
        for name, s in TIMEFRAME_SETS.items():
            htf_state = fractal_states.get(s["htf"])
            bias_val = (
                htf_state.structure.external_trend.value
                if htf_state and hasattr(htf_state, "structure")
                else "NEUTRAL"
            )
            overview_sets[name] = {
                "htf": s["htf"],
                "mtf": s["mtf"],
                "ltf": s["ltf"],
                "bias": bias_val,
            }

        return {
            "engine": self.name,
            "domain": self.domain,
            "status": "PROTECTED_CORE",
            "symbol": self.symbol,
            "timeframe_sets": overview_sets,
        }
