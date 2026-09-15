"""
Quantitative Systems Platform (QSP) — Portfolio Intelligence Engine.

Sits above individual strategy logic to dynamically answer:
    "Should the platform accept this trade even though Strategy X generated a signal?"
Evaluates:
1. Cross-Asset Correlation & Concentration Risk
2. Aggregate Net Crypto Beta
3. Dynamic Drawdown Scaling (Tiered risk reduction during equity pullbacks)
4. Portfolio Heat Ceiling (<= 3.00% aggregate active risk)
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from enum import Enum


class PortfolioAllocationDecision(str, Enum):
    APPROVED_FULL_SIZE = "APPROVED_FULL_SIZE"
    APPROVED_SCALED_SIZE = "APPROVED_SCALED_SIZE"
    REJECTED_HEAT_EXCEEDED = "REJECTED_HEAT_EXCEEDED"
    REJECTED_CORRELATION_CONCENTRATION = "REJECTED_CORRELATION_CONCENTRATION"
    REJECTED_DRAWDOWN_HALT = "REJECTED_DRAWDOWN_HALT"

    # Compatibility aliases
    ACCEPT_FULL = "APPROVED_FULL_SIZE"
    ACCEPT_REDUCED = "APPROVED_SCALED_SIZE"


@dataclass
class TradeAllocationEvaluation:
    decision: PortfolioAllocationDecision
    base_risk_pct: float
    recommended_risk_pct: float
    allocation_multiplier: float
    current_drawdown_pct: float
    current_portfolio_heat_pct: float
    projected_portfolio_heat_pct: float
    net_beta: float
    rationale: str


class PortfolioIntelligenceEngine:
    """
    Multi-asset portfolio risk coordinator and capital allocator.
    """

    MAX_PORTFOLIO_HEAT_PCT = 3.00  # 3.00% max simultaneous portfolio risk
    BASE_TARGET_RISK_PCT = 0.60    # 0.60% base risk per trade

    # Correlation matrix between major crypto assets
    PAIRWISE_CORRELATIONS = {
        ("BTCUSDT", "ETHUSDT"): 0.78,
        ("ETHUSDT", "BTCUSDT"): 0.78,
        ("BTCUSDT", "SOLUSDT"): 0.68,
        ("SOLUSDT", "BTCUSDT"): 0.68,
        ("ETHUSDT", "SOLUSDT"): 0.74,
        ("SOLUSDT", "ETHUSDT"): 0.74,
    }

    @classmethod
    def get_drawdown_risk_multiplier(cls, current_drawdown_pct: float) -> float:
        """
        Calculates dynamic risk scaling multiplier based on current account drawdown:
        - Drawdown <= 5%: 100% allocation (1.0x)
        - Drawdown 5% - 15%: 50% allocation (0.5x)
        - Drawdown 15% - 25%: 25% allocation (0.25x)
        - Drawdown > 25%: Circuit Breaker Halt (0.0x)
        """
        if current_drawdown_pct <= 5.0:
            return 1.00
        elif current_drawdown_pct <= 15.0:
            return 0.50
        elif current_drawdown_pct <= 25.0:
            return 0.25
        else:
            return 0.00

    @classmethod
    def evaluate_new_trade(
        cls,
        candidate_symbol: str,
        candidate_direction: str,  # 'LONG' or 'SHORT'
        current_open_positions: List[Dict[str, Any]],
        account_equity: float,
        current_drawdown_pct: float,
    ) -> TradeAllocationEvaluation:
        """
        Evaluates whether a new candidate trade signal should be accepted, scaled, or rejected.
        """
        reasons = []

        # 1. Check Drawdown Circuit Breaker
        dd_multiplier = cls.get_drawdown_risk_multiplier(current_drawdown_pct)
        if dd_multiplier == 0.0:
            return TradeAllocationEvaluation(
                decision=PortfolioAllocationDecision.REJECTED_DRAWDOWN_HALT,
                base_risk_pct=cls.BASE_TARGET_RISK_PCT,
                recommended_risk_pct=0.0,
                allocation_multiplier=0.0,
                current_drawdown_pct=current_drawdown_pct,
                current_portfolio_heat_pct=0.0,
                projected_portfolio_heat_pct=0.0,
                net_beta=0.0,
                rationale=f"Hard trading halt: current drawdown ({current_drawdown_pct:.1f}%) exceeds 25.0% threshold",
            )

        # 2. Calculate Current Portfolio Heat
        current_risk_usd = sum(p.get("risk_usd", 0.0) for p in current_open_positions)
        current_heat_pct = (current_risk_usd / account_equity) * 100.0 if account_equity > 0 else 0.0

        # 3. Check Correlation Concentration
        # Count how many positions are currently open in the same direction with high correlation
        correlated_positions_count = 0
        for p in current_open_positions:
            open_sym = p.get("symbol", "")
            open_dir = p.get("direction", "")
            if open_dir == candidate_direction:
                pair_corr = cls.PAIRWISE_CORRELATIONS.get((candidate_symbol, open_sym), 0.0)
                if pair_corr >= 0.65 or open_sym == candidate_symbol:
                    correlated_positions_count += 1

        correlation_multiplier = 1.00
        if correlated_positions_count >= 2:
            # Already holding 2 correlated positions in the same direction
            correlation_multiplier = 0.50
            reasons.append(f"Holding {correlated_positions_count} correlated {candidate_direction} positions; discount sizing 50%")
        elif correlated_positions_count >= 3:
            # Over-concentrated
            return TradeAllocationEvaluation(
                decision=PortfolioAllocationDecision.REJECTED_CORRELATION_CONCENTRATION,
                base_risk_pct=cls.BASE_TARGET_RISK_PCT,
                recommended_risk_pct=0.0,
                allocation_multiplier=0.0,
                current_drawdown_pct=current_drawdown_pct,
                current_portfolio_heat_pct=current_heat_pct,
                projected_portfolio_heat_pct=current_heat_pct,
                net_beta=0.0,
                rationale=f"Rejected: {correlated_positions_count} concurrent correlated {candidate_direction} positions already active",
            )

        # Combined multiplier
        final_multiplier = dd_multiplier * correlation_multiplier
        recommended_risk_pct = cls.BASE_TARGET_RISK_PCT * final_multiplier

        # 4. Check Heat Ceiling
        projected_heat_pct = current_heat_pct + recommended_risk_pct
        if projected_heat_pct > cls.MAX_PORTFOLIO_HEAT_PCT:
            # Try to scale down to fit remaining heat budget
            remaining_heat_pct = max(0.0, cls.MAX_PORTFOLIO_HEAT_PCT - current_heat_pct)
            if remaining_heat_pct >= 0.20:  # Minimum viable risk 0.20%
                recommended_risk_pct = remaining_heat_pct
                final_multiplier = recommended_risk_pct / cls.BASE_TARGET_RISK_PCT
                decision = PortfolioAllocationDecision.APPROVED_SCALED_SIZE
                reasons.append(f"Risk scaled down to fit remaining heat capacity ({remaining_heat_pct:.2f}%)")
            else:
                return TradeAllocationEvaluation(
                    decision=PortfolioAllocationDecision.REJECTED_HEAT_EXCEEDED,
                    base_risk_pct=cls.BASE_TARGET_RISK_PCT,
                    recommended_risk_pct=0.0,
                    allocation_multiplier=0.0,
                    current_drawdown_pct=current_drawdown_pct,
                    current_portfolio_heat_pct=current_heat_pct,
                    projected_portfolio_heat_pct=projected_heat_pct,
                    net_beta=0.0,
                    rationale=f"Rejected: Projected heat ({projected_heat_pct:.2f}%) exceeds {cls.MAX_PORTFOLIO_HEAT_PCT:.2f}% limit",
                )
        else:
            if final_multiplier < 1.0:
                decision = PortfolioAllocationDecision.APPROVED_SCALED_SIZE
                if dd_multiplier < 1.0:
                    reasons.append(f"Drawdown scaling active ({dd_multiplier*100:.0f}% risk allocated)")
            else:
                decision = PortfolioAllocationDecision.APPROVED_FULL_SIZE
                reasons.append("Full risk approved under healthy portfolio conditions")

        return TradeAllocationEvaluation(
            decision=decision,
            base_risk_pct=cls.BASE_TARGET_RISK_PCT,
            recommended_risk_pct=round(recommended_risk_pct, 4),
            allocation_multiplier=round(final_multiplier, 4),
            current_drawdown_pct=round(current_drawdown_pct, 2),
            current_portfolio_heat_pct=round(current_heat_pct, 2),
            projected_portfolio_heat_pct=round(current_heat_pct + recommended_risk_pct, 2),
            net_beta=1.0,
            rationale="; ".join(reasons) if reasons else "Approved",
        )
