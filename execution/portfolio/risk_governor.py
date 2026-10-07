"""Portfolio Risk Governor: Multi-Asset Opportunity Ranking & Correlation Governor.

Allocates capital across concurrent asset opportunities, preventing excessive common-factor
exposure and correlation clustering (e.g. holding 100% BTC and 100% ETH simultaneously).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PortfolioOpportunity:
    """A qualified candidate setup competing for portfolio risk allocation."""
    symbol: str
    direction: int                         # +1 LONG, -1 SHORT
    expected_edge_r: float
    destination_r: float
    confidence_score: float = 1.0          # 0.5 to 1.5
    btc_correlation: float = 0.85          # Pairwise correlation to BTC
    pairwise_correlations: Dict[str, float] = field(default_factory=dict)
    base_risk_pct: float = 0.01            # Requested risk (default 1.0% max)
    approved_risk_pct: float = 0.0         # Final allocated risk
    allocation_action: str = "PENDING"     # "ALLOCATED", "HAIRCUT", "SUPPRESSED"
    allocation_reason: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def composite_rank_score(self) -> float:
        """Risk-adjusted attractiveness score."""
        return self.expected_edge_r * self.confidence_score * (self.destination_r / 4.0)


class PortfolioRiskGovernor:
    """Enforces institutional portfolio risk limits and correlation haircutting."""

    def __init__(
        self,
        max_total_portfolio_risk_pct: float = 0.03, # 3.0% maximum aggregate concurrent portfolio risk
        max_single_trade_risk_pct: float = 0.01,    # 1.0% strict ceiling per trade
        high_correlation_threshold: float = 0.75,   # Haircut triggers above 0.75 correlation
        correlation_haircut_factor: float = 0.50,   # Reduce risk by 50% for secondary correlated asset
    ):
        self.max_total_portfolio_risk_pct = max_total_portfolio_risk_pct
        self.max_single_trade_risk_pct = max_single_trade_risk_pct
        self.high_correlation_threshold = high_correlation_threshold
        self.correlation_haircut_factor = correlation_haircut_factor

    def is_correlated_with_active(self, sym_a: str, sym_b: str, threshold: float = 0.75) -> bool:
        """Helper to determine if two symbols share high structural correlation."""
        if sym_a == sym_b:
            return True
        canonical_correlations = {
            ("BTCUSDT", "ETHUSDT"): 0.84,
            ("ETHUSDT", "BTCUSDT"): 0.84,
            ("BTCUSDT", "SOLUSDT"): 0.78,
            ("SOLUSDT", "BTCUSDT"): 0.78,
            ("ETHUSDT", "SOLUSDT"): 0.80,
            ("SOLUSDT", "ETHUSDT"): 0.80,
        }
        corr = canonical_correlations.get((sym_a, sym_b), 0.50)
        return corr >= threshold

    def allocate_portfolio_risk(
        self,
        opportunities: List[PortfolioOpportunity],
        current_active_risk_pct: float = 0.0,
    ) -> List[PortfolioOpportunity]:
        """Rank candidates and allocate risk budget with correlation haircutting."""
        if not opportunities:
            return []

        # Sort opportunities descending by composite rank score
        ranked = sorted(opportunities, key=lambda o: o.composite_rank_score, reverse=True)
        remaining_budget = max(0.0, self.max_total_portfolio_risk_pct - current_active_risk_pct)
        allocated_assets: List[PortfolioOpportunity] = []

        for opp in ranked:
            # Floor check: Destination must be >= 4.0R
            if opp.destination_r < 4.0:
                opp.approved_risk_pct = 0.0
                opp.allocation_action = "SUPPRESSED"
                opp.allocation_reason = f"Destination {opp.destination_r:.2f}R below mandatory 4.0R floor."
                continue

            # Hard stop if portfolio budget exhausted
            if remaining_budget <= 0.001:
                opp.approved_risk_pct = 0.0
                opp.allocation_action = "SUPPRESSED"
                opp.allocation_reason = "Total portfolio risk capacity (3.0%) exhausted."
                continue

            target_risk = min(opp.base_risk_pct, self.max_single_trade_risk_pct)

            # Check pairwise correlation against already allocated positions
            has_high_corr_peer = False
            for prev in allocated_assets:
                if prev.direction == opp.direction:
                    # Resolve pairwise correlation
                    corr = opp.pairwise_correlations.get(
                        prev.symbol,
                        prev.pairwise_correlations.get(
                            opp.symbol,
                            opp.btc_correlation if prev.symbol == "BTCUSDT"
                            else (prev.btc_correlation if opp.symbol == "BTCUSDT"
                            else 0.50)
                        )
                    )
                    if corr >= self.high_correlation_threshold:
                        has_high_corr_peer = True
                        break

            if has_high_corr_peer:
                target_risk *= self.correlation_haircut_factor
                reason = (
                    f"Correlation haircut ({self.correlation_haircut_factor * 100:.0f}%): "
                    f"highly correlated with existing position."
                )
                action = "HAIRCUT"
            else:
                reason = "Primary allocation approved based on top risk-adjusted rank."
                action = "ALLOCATED"

            # Clip against remaining portfolio budget
            final_risk = min(target_risk, remaining_budget)
            if final_risk < 0.002: # Less than 0.20% risk is not worth capital friction
                opp.approved_risk_pct = 0.0
                opp.allocation_action = "SUPPRESSED"
                opp.allocation_reason = "Residual risk budget below minimum economic trade threshold (0.20%)."
                continue

            opp.approved_risk_pct = round(final_risk, 4)
            opp.allocation_action = action
            opp.allocation_reason = reason
            remaining_budget -= final_risk
            allocated_assets.append(opp)

        return ranked
