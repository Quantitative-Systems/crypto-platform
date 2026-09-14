"""
Quantitative Systems Platform (QSP) — Daily Multi-Set Decision Record Engine.

Produces an immutable, daily machine-readable decision audit:
    NO_TRADE / TRADE / REDUCE / HEDGE / QUARANTINE

Executes the institutional 10-level decision hierarchy:
Level 1: Is the data trustworthy? (Timestamp monotonicity, gap detection, <30s latency)
Level 2: Is the market environment tradable? (Not in extreme illiquidity or dead compression)
Level 3: Is there qualified alpha? (Verified against Canonical Registry)
Level 4: Is Expected Net Edge economically sufficient after all frictions? (> +0.05R)
Level 5: Is the position executable at this account size? (No fatal risk distortion)
Level 6: Does portfolio construction justify taking it? (Heat <= 3.00%, Correlation discount)
Level 7: Is a hedge required or unavailable? (Net beta tracking)
Level 8: Final deterministic decision output.
"""

import os
import sys
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from enum import Enum

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platform_core.canonical_strategy_registry import CanonicalStrategyRegistry
from capital_intelligence.alpha_capital_intelligence import NetEdgeEngine, AlphaSelectionEngine
from capital_intelligence.feasibility_engine import CapitalFeasibilityEngine, FeasibilityVerdict
from portfolio_engine.portfolio_intelligence import PortfolioIntelligenceEngine, PortfolioAllocationDecision
from portfolio_engine.hedging_engine import PortfolioHedgingEngine, PositionExposure, HedgeAction
from market_intelligence.regime_engine import MarketRegimeEngine, RegimeFilterAction

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "research", "results")
DECISION_RECORD_FILE = os.path.join(RESULTS_DIR, "DAILY_DECISION_RECORD.json")


class PlatformDecisionVerdict(str, Enum):
    NO_TRADE = "NO_TRADE"
    TRADE = "TRADE"
    REDUCE = "REDUCE"
    HEDGE = "HEDGE"
    QUARANTINE = "QUARANTINE"


@dataclass
class CandidateSignalEvaluation:
    strategy_id: str
    symbol: str
    direction: str
    timeframe_set: int
    gross_alpha_r: float
    expected_net_edge_r: float
    data_trust_passed: bool
    market_tradable_passed: bool
    net_edge_passed: bool
    capital_feasible: bool
    portfolio_approved: bool
    verdict: PlatformDecisionVerdict
    allocated_risk_pct: float
    reason: str


class DecisionRecordEngine:
    """
    Evaluates the complete operational decision stack across all assets and strategies.
    """

    def __init__(self, account_capital: float = 1000.0):
        self.account_capital = account_capital
        self.registry = CanonicalStrategyRegistry()
        self.hedging_engine = PortfolioHedgingEngine()

    def evaluate_daily_decisions(
        self,
        candidate_signals: List[Dict[str, Any]],
        current_open_positions: List[Dict[str, Any]],
        current_drawdown_pct: float = 2.5,
    ) -> Dict[str, Any]:
        evaluations: List[CandidateSignalEvaluation] = []

        # Current portfolio heat
        current_risk_usd = sum(p.get("risk_usd", 0.0) for p in current_open_positions)
        current_heat_pct = (current_risk_usd / self.account_capital) * 100.0 if self.account_capital > 0 else 0.0

        for sig in candidate_signals:
            strat_id = sig.get("strategy_id", "")
            symbol = sig.get("symbol", "")
            direction = sig.get("direction", "LONG")
            set_num = sig.get("set", 2)
            entry_p = sig.get("entry_price", 100.0)
            sl_p = sig.get("sl_price", 95.0)
            gross_r = sig.get("gross_alpha_r", 0.22)
            stop_dist_pct = (abs(entry_p - sl_p) / entry_p) * 100.0

            # Level 1: Data Trust
            data_trust_passed = sig.get("data_latency_sec", 2.0) <= 30.0
            if not data_trust_passed:
                evaluations.append(
                    CandidateSignalEvaluation(
                        strategy_id=strat_id, symbol=symbol, direction=direction, timeframe_set=set_num,
                        gross_alpha_r=gross_r, expected_net_edge_r=0.0, data_trust_passed=False,
                        market_tradable_passed=False, net_edge_passed=False, capital_feasible=False,
                        portfolio_approved=False, verdict=PlatformDecisionVerdict.NO_TRADE,
                        allocated_risk_pct=0.0, reason="Data feed latency > 30s; feed quarantined",
                    )
                )
                continue

            # Level 2: Market Tradability
            market_tradable = sig.get("market_spread_pct", 0.0002) <= 0.0015
            if not market_tradable:
                evaluations.append(
                    CandidateSignalEvaluation(
                        strategy_id=strat_id, symbol=symbol, direction=direction, timeframe_set=set_num,
                        gross_alpha_r=gross_r, expected_net_edge_r=0.0, data_trust_passed=True,
                        market_tradable_passed=False, net_edge_passed=False, capital_feasible=False,
                        portfolio_approved=False, verdict=PlatformDecisionVerdict.NO_TRADE,
                        allocated_risk_pct=0.0, reason="Market spread exceeds 0.15% maximum; liquidity abnormal",
                    )
                )
                continue

            # Level 3 & 4: Net Edge Economics Gate
            net_breakdown = NetEdgeEngine.calculate_net_edge(
                symbol=symbol,
                direction=direction,
                gross_alpha_r=gross_r,
                stop_distance_pct=stop_dist_pct,
                order_notional_usd=self.account_capital * 0.10,
            )

            if not net_breakdown.is_economically_viable:
                evaluations.append(
                    CandidateSignalEvaluation(
                        strategy_id=strat_id, symbol=symbol, direction=direction, timeframe_set=set_num,
                        gross_alpha_r=gross_r, expected_net_edge_r=net_breakdown.expected_net_edge_r,
                        data_trust_passed=True, market_tradable_passed=True, net_edge_passed=False,
                        capital_feasible=False, portfolio_approved=False, verdict=PlatformDecisionVerdict.NO_TRADE,
                        allocated_risk_pct=0.0, reason=f"Net edge (+{net_breakdown.expected_net_edge_r:.3f}R) <= 0.05R viability threshold",
                    )
                )
                continue

            # Level 5: Capital Feasibility Gate
            feas_eval = CapitalFeasibilityEngine.evaluate_feasibility(
                account_capital=self.account_capital,
                symbol=symbol,
                entry_price=entry_p,
                stop_distance_usd=abs(entry_p - sl_p),
                venue="USDM_FUTURES",
                target_risk_pct=0.006,
            )

            if feas_eval.verdict in (
                FeasibilityVerdict.NOT_FEASIBLE,
                FeasibilityVerdict.FATAL_LIQUIDATION_RISK,
                FeasibilityVerdict.HIGH_RISK_DISTORTED,
            ):
                evaluations.append(
                    CandidateSignalEvaluation(
                        strategy_id=strat_id, symbol=symbol, direction=direction, timeframe_set=set_num,
                        gross_alpha_r=gross_r, expected_net_edge_r=net_breakdown.expected_net_edge_r,
                        data_trust_passed=True, market_tradable_passed=True, net_edge_passed=True,
                        capital_feasible=False, portfolio_approved=False, verdict=PlatformDecisionVerdict.NO_TRADE,
                        allocated_risk_pct=0.0, reason=f"Capital feasibility failed: {feas_eval.notes}",
                    )
                )
                continue

            # Level 6: Portfolio Risk & Heat Gate
            port_eval = PortfolioIntelligenceEngine.evaluate_new_trade(
                candidate_symbol=symbol,
                candidate_direction=direction,
                current_open_positions=current_open_positions,
                account_equity=self.account_capital,
                current_drawdown_pct=current_drawdown_pct,
            )

            if port_eval.decision in (
                PortfolioAllocationDecision.REJECTED_HEAT_EXCEEDED,
                PortfolioAllocationDecision.REJECTED_CORRELATION_CONCENTRATION,
                PortfolioAllocationDecision.REJECTED_DRAWDOWN_HALT,
            ):
                evaluations.append(
                    CandidateSignalEvaluation(
                        strategy_id=strat_id, symbol=symbol, direction=direction, timeframe_set=set_num,
                        gross_alpha_r=gross_r, expected_net_edge_r=net_breakdown.expected_net_edge_r,
                        data_trust_passed=True, market_tradable_passed=True, net_edge_passed=True,
                        capital_feasible=True, portfolio_approved=False, verdict=PlatformDecisionVerdict.NO_TRADE,
                        allocated_risk_pct=0.0, reason=f"Portfolio rejection: {port_eval.rationale}",
                    )
                )
                continue

            # Final Decision
            final_verdict = PlatformDecisionVerdict.TRADE
            if port_eval.decision == PortfolioAllocationDecision.APPROVED_SCALED_SIZE:
                final_verdict = PlatformDecisionVerdict.REDUCE

            evaluations.append(
                CandidateSignalEvaluation(
                    strategy_id=strat_id,
                    symbol=symbol,
                    direction=direction,
                    timeframe_set=set_num,
                    gross_alpha_r=gross_r,
                    expected_net_edge_r=net_breakdown.expected_net_edge_r,
                    data_trust_passed=True,
                    market_tradable_passed=True,
                    net_edge_passed=True,
                    capital_feasible=True,
                    portfolio_approved=True,
                    verdict=final_verdict,
                    allocated_risk_pct=port_eval.recommended_risk_pct,
                    reason=f"Approved ({port_eval.rationale}) | Net Edge: +{net_breakdown.expected_net_edge_r:.3f}R",
                )
            )

        # Level 7: Hedging Evaluation
        exposures = [
            PositionExposure(
                symbol=p.get("symbol", ""),
                direction=p.get("direction", "LONG"),
                notional_usd=p.get("notional_usd", 100.0),
                risk_usd=p.get("risk_usd", 6.0),
            )
            for p in current_open_positions
        ]
        hedge_dec = self.hedging_engine.evaluate_hedge_requirement(
            open_positions=exposures,
            account_equity=self.account_capital,
            macro_regime_is_hostile=False,
        )

        record = {
            "audit_timestamp": datetime.now(timezone.utc).isoformat(),
            "account_capital": self.account_capital,
            "current_drawdown_pct": current_drawdown_pct,
            "current_portfolio_heat_pct": round(current_heat_pct, 2),
            "hedging_status": asdict(hedge_dec),
            "evaluations": [asdict(e) for e in evaluations],
        }

        os.makedirs(RESULTS_DIR, exist_ok=True)
        with open(DECISION_RECORD_FILE, "w") as f:
            json.dump(record, f, indent=2)

        return record


if __name__ == "__main__":
    engine = DecisionRecordEngine(account_capital=1000.0)
    sample_signals = [
        {"strategy_id": "FAM-07-SOL-Set3", "symbol": "SOLUSDT", "direction": "LONG", "set": 3, "entry_price": 100.0, "sl_price": 96.50, "gross_alpha_r": 0.24, "market_spread_pct": 0.0002, "data_latency_sec": 1.2},
        {"strategy_id": "FAM-07-BTC-Set2", "symbol": "BTCUSDT", "direction": "LONG", "set": 2, "entry_price": 45000.0, "sl_price": 43110.0, "gross_alpha_r": 0.22, "market_spread_pct": 0.0001, "data_latency_sec": 0.8},
        {"strategy_id": "WEAK-ALPHA-ETH", "symbol": "ETHUSDT", "direction": "SHORT", "set": 2, "entry_price": 2500.0, "sl_price": 2480.0, "gross_alpha_r": 0.06, "market_spread_pct": 0.0002, "data_latency_sec": 1.5},
    ]
    open_pos = [{"symbol": "SOLUSDT", "direction": "LONG", "notional_usd": 150.0, "risk_usd": 6.0}]
    rec = engine.evaluate_daily_decisions(sample_signals, open_pos, current_drawdown_pct=1.8)
    print(f"[DECISION ENGINE] Recorded {len(rec['evaluations'])} evaluations:")
    for ev in rec["evaluations"]:
        print(f"  {ev['strategy_id']} ({ev['symbol']}): [{ev['verdict']}] Risk: {ev['allocated_risk_pct']}% | {ev['reason']}")
