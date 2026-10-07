"""
Product 04 — Research Laboratory: Counterfactual Opportunity-Funnel Diagnostic Engine
Performs forward counterfactual simulations on rejected candidate opportunities to classify
filtering gates as either 'PROTECTIVE_RISK_FILTER' (saving capital) or 'ALPHA_DESTROYER' (discarding edge).
"""

import os
import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
from enum import Enum


class GateEfficacyVerdict(str, Enum):
    PROTECTIVE_RISK_FILTER = "PROTECTIVE_RISK_FILTER"
    ALPHA_DESTROYER = "ALPHA_DESTROYER"
    NEUTRAL_NOISE_REJECTION = "NEUTRAL_NOISE_REJECTION"


@dataclass
class CounterfactualGateResult:
    gate_name: str
    total_rejections_audited: int
    counterfactual_wins: int
    counterfactual_losses: int
    counterfactual_win_rate_pct: float
    capital_saved_r: float          # Positive R: Losses prevented by rejecting bad setups
    alpha_forfeited_r: float        # Positive R: Profits missed by discarding valid setups
    net_economic_value_r: float     # capital_saved_r - alpha_forfeited_r
    verdict: GateEfficacyVerdict
    recommendation: str


class CounterfactualFunnelEngine:
    """
    Simulates counterfactual execution paths for filtered candidates to determine
    the economic attribution of each Risk Firewall and Strategy rejection gate.
    """

    @staticmethod
    def simulate_counterfactual_trade(
        entry_price: float,
        is_long: bool,
        subsequent_highs: List[float],
        subsequent_lows: List[float],
        target_rr: float = 4.0,
        stop_dist_pct: float = 0.01
    ) -> Dict[str, Any]:
        """
        Simulates forward price action against a counterfactual stop and target.
        Adverse-first intrabar collision assumed.
        """
        if is_long:
            stop_price = entry_price * (1.0 - stop_dist_pct)
            target_price = entry_price * (1.0 + (stop_dist_pct * target_rr))
        else:
            stop_price = entry_price * (1.0 + stop_dist_pct)
            target_price = entry_price * (1.0 - (stop_dist_pct * target_rr))

        bars_tracked = min(len(subsequent_highs), len(subsequent_lows))
        for i in range(bars_tracked):
            high = subsequent_highs[i]
            low = subsequent_lows[i]

            if is_long:
                # Adverse first: Check stop hit
                if low <= stop_price:
                    return {"outcome": "LOSS", "realized_r": -1.0, "exit_bar": i}
                if high >= target_price:
                    return {"outcome": "WIN", "realized_r": target_rr, "exit_bar": i}
            else:
                # Short: Check stop hit (high >= stop_price)
                if high >= stop_price:
                    return {"outcome": "LOSS", "realized_r": -1.0, "exit_bar": i}
                if low <= target_price:
                    return {"outcome": "WIN", "realized_r": target_rr, "exit_bar": i}

        # Expired / Time-decay exit
        return {"outcome": "TIMEOUT", "realized_r": 0.0, "exit_bar": bars_tracked}

    @staticmethod
    def evaluate_gate_counterfactually(
        gate_name: str,
        rejected_setups: List[Dict[str, Any]],
        target_rr: float = 4.0
    ) -> CounterfactualGateResult:
        """
        Evaluates a population of rejected setups at a specific gate.
        """
        if not rejected_setups:
            return CounterfactualGateResult(
                gate_name=gate_name,
                total_rejections_audited=0,
                counterfactual_wins=0,
                counterfactual_losses=0,
                counterfactual_win_rate_pct=0.0,
                capital_saved_r=0.0,
                alpha_forfeited_r=0.0,
                net_economic_value_r=0.0,
                verdict=GateEfficacyVerdict.NEUTRAL_NOISE_REJECTION,
                recommendation="No candidates observed at this gate."
            )

        wins = 0
        losses = 0
        timeouts = 0

        for s in rejected_setups:
            entry = s.get("entry_price", 100.0)
            is_long = "LONG" in str(s.get("direction", "LONG"))
            highs = s.get("future_highs", [])
            lows = s.get("future_lows", [])
            stop_dist = s.get("stop_dist_pct", 0.01)

            res = CounterfactualFunnelEngine.simulate_counterfactual_trade(
                entry_price=entry,
                is_long=is_long,
                subsequent_highs=highs,
                subsequent_lows=lows,
                target_rr=target_rr,
                stop_dist_pct=stop_dist
            )

            if res["outcome"] == "WIN":
                wins += 1
            elif res["outcome"] == "LOSS":
                losses += 1
            else:
                timeouts += 1

        total = wins + losses + timeouts
        win_rate = (wins / total * 100.0) if total > 0 else 0.0

        # Capital saved: Each avoided loss prevented -1.0R loss (+1.0R economic value)
        capital_saved = float(losses * 1.0)
        # Alpha forfeited: Each rejected win missed +target_rr R profit
        alpha_forfeited = float(wins * target_rr)
        net_value = capital_saved - alpha_forfeited

        if net_value > 5.0:
            verdict = GateEfficacyVerdict.PROTECTIVE_RISK_FILTER
            recommendation = "PRESERVE GATE: Effectively filters out unprofitable noise and protects capital."
        elif net_value < -5.0:
            verdict = GateEfficacyVerdict.ALPHA_DESTROYER
            recommendation = "INVESTIGATE & REFINE: Filter is overly restrictive and discards positive expectancy opportunities."
        else:
            verdict = GateEfficacyVerdict.NEUTRAL_NOISE_REJECTION
            recommendation = "MONITOR: Economic impact of gate is neutral within sample variance."

        return CounterfactualGateResult(
            gate_name=gate_name,
            total_rejections_audited=total,
            counterfactual_wins=wins,
            counterfactual_losses=losses,
            counterfactual_win_rate_pct=round(win_rate, 2),
            capital_saved_r=round(capital_saved, 2),
            alpha_forfeited_r=round(alpha_forfeited, 2),
            net_economic_value_r=round(net_value, 2),
            verdict=verdict,
            recommendation=recommendation
        )

    @staticmethod
    def print_counterfactual_audit_report(results: List[CounterfactualGateResult]):
        """Prints a comprehensive diagnostic report of filter gate economic efficacy."""
        print("=" * 120)
        print("RESEARCH LABORATORY: COUNTERFACTUAL OPPORTUNITY-FUNNEL ECONOMIC EFFICACY REPORT")
        print("=" * 120)
        header = f"| {'Gating Rejection Gate':35s} | {'Audited':8s} | {'Wins':6s} | {'Losses':6s} | {'Win %':7s} | {'Saved R':9s} | {'Forfeited':9s} | {'Net Value':10s} | {'Gate Verdict':24s} |"
        print(header)
        print("|" + "-" * 37 + "|" + "-" * 10 + "|" + "-" * 8 + "|" + "-" * 8 + "|" + "-" * 9 + "|" + "-" * 11 + "|" + "-" * 11 + "|" + "-" * 12 + "|" + "-" * 26 + "|")
        for r in results:
            print(f"| {r.gate_name:35s} | {r.total_rejections_audited:8d} | {r.counterfactual_wins:6d} | {r.counterfactual_losses:6d} | {r.counterfactual_win_rate_pct:6.1f}% | {r.capital_saved_r:8.1f}R | {r.alpha_forfeited_r:8.1f}R | {r.net_economic_value_r:9.1f}R | {r.verdict.value:24s} |")
        print("=" * 120)


def main():
    # Diagnostic execution with representative funnel samples
    gates = [
        "REJECT_MISSING_STRUCTURAL_ANCHORS",
        "REJECT_INVALID_ANCHOR_GEOMETRY",
        "REJECT_OPPOSING_MTF_STRUCTURE",
        "REJECT_SUPERSEDED_HTF_CONTEXT",
        "REJECT_RR_BELOW_4R"
    ]
    
    # Example diagnostic run
    diagnostics = []
    for g in gates:
        # Generate representative counterfactual distribution
        sample_setups = []
        for i in range(50):
            # Simulated forward price path: 70% chance of chop/loss, 30% chance of breakout
            if i % 3 == 0:
                highs = [101.0, 102.5, 104.5, 105.0]
                lows = [99.5, 100.0, 101.0, 102.0]
            else:
                highs = [100.5, 100.2, 99.8, 99.0]
                lows = [98.5, 97.0, 96.0, 95.0]
            sample_setups.append({
                "entry_price": 100.0,
                "direction": "LONG",
                "future_highs": highs,
                "future_lows": lows,
                "stop_dist_pct": 0.01
            })
        diag = CounterfactualFunnelEngine.evaluate_gate_counterfactually(g, sample_setups)
        diagnostics.append(diag)

    CounterfactualFunnelEngine.print_counterfactual_audit_report(diagnostics)


if __name__ == "__main__":
    main()
