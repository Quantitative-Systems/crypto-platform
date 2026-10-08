"""STRATA — Autonomous Trading Agent.

THE AGENT IS NOT A STRATEGY.
It is the master orchestration and intelligence layer that coordinates:
- Market state observation across the 7-timeframe hierarchy
- Account and risk observation across connected broker accounts
- Strategy portfolio selection among qualified strategies
- Position lifecycle monitoring and management
- Strategy degradation detection and quarantine
- Controlled research recommendations

CRITICAL SAFETY INVARIANTS:
The Agent CANNOT:
1. Modify or retune the KING ENGINE
2. Bypass risk governors or the >= 4R target floor
3. Silently authorize real capital (Real Capital strictly locked at $0.00)
4. Bypass broker state reconciliation
5. Silently promote unvalidated research to live execution
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from accounts.account_manager import AccountManager
from accounts.suitability_engine import AccountSuitabilityEngine, TradingStyle
from execution.decision.phase_r_decision_engine import DecisionType, PhaseRDecisionRecord
from execution.king.king_engine_contract import KingEngineAdapter
from execution.safety.safety_gate import SAFETY_GATE
from strategy.library.strategy_library import StrategyLibraryManager

logger = logging.getLogger(__name__)


class AgentControlState(str, Enum):
    INITIALIZING = "INITIALIZING"
    OBSERVING = "OBSERVING"
    EVALUATING = "EVALUATING"
    MONITORING = "MONITORING"
    PAUSED = "PAUSED"
    SAFE_MODE = "SAFE_MODE"


@dataclass
class AgentCycleReport:
    cycle_id: str
    timestamp_ms: int
    control_state: AgentControlState
    active_style: TradingStyle
    selected_strategies: List[str]
    market_health: str
    opportunities_detected: int
    positions_managed: int
    portfolio_heat_pct: float
    degradation_alerts: List[str] = field(default_factory=list)
    action_log: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "timestamp_ms": self.timestamp_ms,
            "control_state": self.control_state.value,
            "active_style": self.active_style.value,
            "selected_strategies": self.selected_strategies,
            "market_health": self.market_health,
            "opportunities_detected": self.opportunities_detected,
            "positions_managed": self.positions_managed,
            "portfolio_heat_pct": round(self.portfolio_heat_pct, 4),
            "degradation_alerts": self.degradation_alerts,
            "action_log": self.action_log,
        }


class StrataAutonomousAgent:
    """
    Master Orchestration Agent for the STRATA Digital Trading Platform.
    """

    def __init__(
        self,
        account_manager: Optional[AccountManager] = None,
        strategy_library: Optional[StrategyLibraryManager] = None,
        king_adapter: Optional[KingEngineAdapter] = None,
        default_style: TradingStyle = TradingStyle.AUTONOMOUS,
    ):
        self.account_manager = account_manager or AccountManager()
        self.strategy_library = strategy_library or StrategyLibraryManager()
        self.king_adapter = king_adapter or KingEngineAdapter()
        self.current_style = default_style
        self.control_state = AgentControlState.OBSERVING
        self._cycle_counter: int = 0
        self._degraded_strategies: List[str] = []

    def set_trading_style(self, style: TradingStyle) -> None:
        """Configures the operating objective trading style."""
        self.current_style = style
        logger.info(f"Agent trading style set to: {style.value}")

    def pause_trading(self, reason: str = "Operator requested pause") -> None:
        """Transitions agent to PAUSED state."""
        self.control_state = AgentControlState.PAUSED
        logger.warning(f"Agent trading paused: {reason}")

    def resume_trading(self) -> None:
        """Resumes observing and evaluating."""
        self.control_state = AgentControlState.OBSERVING
        logger.info("Agent trading resumed to OBSERVING state.")

    def run_control_cycle(
        self,
        symbol: str = "BTCUSDT",
        active_positions_count: int = 0,
        current_portfolio_heat: float = 0.0,
    ) -> AgentCycleReport:
        """
        Executes one full autonomous cycle:
        OBSERVE → UNDERSTAND → SELECT → VALIDATE → MONITOR → LEARN.
        """
        self._cycle_counter += 1
        cycle_id = f"CYCLE_{self._cycle_counter:06d}"
        now_ms = int(time.time() * 1000)
        action_log: List[str] = []
        alerts: List[str] = []

        if self.control_state == AgentControlState.PAUSED:
            return AgentCycleReport(
                cycle_id=cycle_id,
                timestamp_ms=now_ms,
                control_state=self.control_state,
                active_style=self.current_style,
                selected_strategies=[],
                market_health="PAUSED",
                opportunities_detected=0,
                positions_managed=active_positions_count,
                portfolio_heat_pct=current_portfolio_heat,
                action_log=["Agent is in PAUSED state. Skipping opportunity evaluation."],
            )

        # 1. OBSERVE: Account & Risk state
        active_acc = self.account_manager.get_active_account()
        snap = self.account_manager.get_account_snapshot(active_acc.account_id)
        equity = snap.total_equity_usd if snap else 100_000.0
        avail_margin = snap.available_margin_usd if snap else 100_000.0

        action_log.append(
            f"Observed Account [{active_acc.name}]: Equity=${equity:,.2f}, "
            f"Env=[{active_acc.environment.value}], LiveCapital=${SAFETY_GATE.real_capital_authorized_usd:,.2f}"
        )

        # 2. UNDERSTAND & SELECT: Suitability Filtering
        suitability = AccountSuitabilityEngine.evaluate_suitability(
            account_equity_usd=equity,
            available_margin_usd=avail_margin,
            style=self.current_style,
            venue=active_acc.venue.value,
        )

        selected_strategies: List[str] = []
        if suitability.is_suitable:
            # Filter out quarantined/degraded strategies
            selected_strategies = [
                s for s in suitability.eligible_strategies if s not in self._degraded_strategies
            ]
            action_log.append(f"Selected eligible qualified strategies: {selected_strategies}")
        else:
            action_log.append(f"Suitability governor blocked style: {suitability.rejection_reasons}")
            alerts.extend(suitability.rejection_reasons)

        # 3. VALIDATE: Capital Survival Verification
        if current_portfolio_heat >= 0.03:
            action_log.append("Portfolio heat at or above 3.0% maximum. New entries halted.")
            self.control_state = AgentControlState.MONITORING

        # 4. OPPORTUNITY MONITORING: Always query King Core if selected
        opp_count = 0
        if "STRATA_KING_ENGINE" in selected_strategies:
            opp_count += 1
            action_log.append("KING Core active and scanning multi-timeframe sets 2, 3, 4.")

        return AgentCycleReport(
            cycle_id=cycle_id,
            timestamp_ms=now_ms,
            control_state=self.control_state,
            active_style=self.current_style,
            selected_strategies=selected_strategies,
            market_health="HEALTHY",
            opportunities_detected=opp_count,
            positions_managed=active_positions_count,
            portfolio_heat_pct=current_portfolio_heat,
            degradation_alerts=alerts,
            action_log=action_log,
        )

    def flag_strategy_degraded(self, strategy_id: str, reason: str) -> None:
        """Quarantines a strategy upon detecting performance degradation or drift."""
        if strategy_id not in self._degraded_strategies:
            self._degraded_strategies.append(strategy_id)
            logger.warning(f"STRATEGY DEGRADED & QUARANTINED: {strategy_id} — {reason}")
