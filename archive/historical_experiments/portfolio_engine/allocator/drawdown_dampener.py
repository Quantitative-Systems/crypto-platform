"""
Product 05 — Portfolio & Dynamic Risk Engine
Drawdown Dampener Module.
Throttles position sizing during portfolio drawdowns to protect high-water mark capital.
"""

from typing import Tuple, Optional
from portfolio_engine.contracts.portfolio_state import PortfolioRiskConfig, PortfolioState


class DrawdownDampener:
    """
    Applies non-linear risk throttling based on high-water mark drawdown depth.
    """

    @staticmethod
    def get_dampener_factor(
        portfolio_state: PortfolioState,
        config: PortfolioRiskConfig
    ) -> Tuple[float, Optional[str]]:
        """
        Evaluates drawdown dampening factor.
        Returns: (dampener_factor, optional_rejection_reason)
        """
        portfolio_state.update_drawdown()
        dd = portfolio_state.current_drawdown_pct

        if dd >= config.drawdown_tier_2_pct:
            return 0.0, f"REJECT_PORTFOLIO_CIRCUIT_PAUSE_DD_{dd*100:.1f}%"
        elif dd >= config.drawdown_tier_1_pct:
            return 0.50, None
        else:
            return 1.0, None
