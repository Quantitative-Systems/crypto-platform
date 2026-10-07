"""Two-Brain Architectural Coordinator.

Enforces the absolute separation of concerns between:
1. DETERMINISTIC BRAIN:
   Controls Market State, Risk Budgets, Sizing, Trade/No-Trade Decisions,
   Stops, Targets, Portfolio Limits, and Emergency Shutdowns.
   Mathematically bounded, auditable, and immutable.

2. INTELLIGENCE BRAIN:
   Analyzes Macro Events, News, Narratives, Cross-Market Flows, Regimes,
   Anomalies, Hypothesis Generation, and Concept Drift.

FOUNDATIONAL PLATFORM INVARIANT:
The Intelligence Brain CANNOT override or weaken the Deterministic Brain.
AI/LLM or contextual intelligence can suggest caution, register hypotheses,
or provide narrative summaries, but CAN NEVER loosen risk limits, force trades,
or modify live execution parameters dynamically.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from execution.decision.decision_engine import (
    AutonomousDecisionEngine,
    AutonomousDecisionOutcome,
    NoTradeReason,
)
from instrument.instrument_contract import CryptoBaseInstrument
from instrument.instrument_health import InstrumentHealth


@dataclass
class IntelligenceBrainContext:
    """Qualitative and quantitative context synthesized by the Intelligence Brain."""
    macro_narrative: str = "BENIGN"
    event_risk_active: bool = False
    active_event_name: Optional[str] = None
    detected_market_anomalies: List[str] = field(default_factory=list)
    cross_market_flow_sentiment: str = "NEUTRAL"
    generated_hypotheses: List[str] = field(default_factory=list)
    confidence_score: float = 1.0


@dataclass
class DeterministicBrainDecision:
    """Final decision produced by the Deterministic Brain."""
    outcome: AutonomousDecisionOutcome
    deterministic_veto_applied: bool
    veto_reason: Optional[str]
    risk_headroom_remaining_pct: float
    firewall_enforced: bool = True


class TwoBrainCoordinator:
    """Orchestrates decision-making while enforcing the deterministic firewall."""

    def __init__(self, deterministic_engine: AutonomousDecisionEngine):
        self.deterministic_engine = deterministic_engine
        self.firewall_enforced: bool = True

    def process_cycle(
        self,
        instrument: CryptoBaseInstrument,
        health: InstrumentHealth,
        market_model_state: Dict[str, Any],
        intelligence_context: IntelligenceBrainContext,
        governor_state: Dict[str, Any],
        active_positions: List[Tuple[CryptoBaseInstrument, int, float]],
        account_equity_usd: float = 100_000.0,
        now: Optional[float] = None,
    ) -> DeterministicBrainDecision:
        """Run the two-brain coordination loop under strict firewall rules."""
        # 1. Map Intelligence Context into environment inputs
        environment_state = {
            "regime": "EXPANSION_STABLE" if not intelligence_context.detected_market_anomalies else "CRISIS_TURMOIL",
            "in_event_window": intelligence_context.event_risk_active,
            "event_name": intelligence_context.active_event_name or "NONE",
            "macro_state": intelligence_context.macro_narrative,
        }

        # 2. Run Deterministic Brain
        # The deterministic brain alone determines whether to trade, risk allocation, and sizing
        outcome = self.deterministic_engine.evaluate_cycle(
            instrument=instrument,
            health=health,
            market_model_state=market_model_state,
            environment_state=environment_state,
            governor_state=governor_state,
            active_positions=active_positions,
            account_equity_usd=account_equity_usd,
            current_time=now,
        )

        # 3. Verify Firewall Invariant: Intelligence Brain CANNOT force a trade or breach 4R floor
        veto_applied = False
        veto_reason = None

        if outcome.decision == "TRADE":
            # Deterministic double-check on invariants
            if outcome.destination_r < 4.0:
                outcome.decision = "NO_TRADE"
                outcome.no_trade_code = NoTradeReason.NO_TRADE_DESTINATION_LT_4R
                outcome.primary_reason = "FIREWALL_VETO: Destination below mandatory 4.0R floor"
                veto_applied = True
                veto_reason = "DESTINATION_LT_4R_VETO"
            elif outcome.risk_approved > 0.01:
                outcome.risk_approved = 0.01
                veto_applied = True
                veto_reason = "RISK_CAP_VETO (Clamped to 1.0%)"

        # Calculate remaining portfolio headroom
        factor_state = self.deterministic_engine.factor_engine.calculate_portfolio_state(active_positions)
        headroom = max(0.0, 0.03 - factor_state.total_portfolio_heat_pct)

        return DeterministicBrainDecision(
            outcome=outcome,
            deterministic_veto_applied=veto_applied,
            veto_reason=veto_reason,
            risk_headroom_remaining_pct=round(headroom, 4),
            firewall_enforced=True,
        )
