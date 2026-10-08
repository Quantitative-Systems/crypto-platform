"""STRATA — Account-Suitability Engine & Trading Style Selector.

Evaluates whether a given account and risk profile is suitable for specific strategy families.
The Autonomous Trading Agent may ONLY execute strategies that pass this suitability governor.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TradingStyle(str, Enum):
    SCALPING = "SCALPING"
    INTRADAY = "INTRADAY"
    SWING = "SWING"
    POSITION = "POSITION"
    INVESTMENT = "INVESTMENT"
    HEDGING = "HEDGING"
    ARBITRAGE = "ARBITRAGE"
    AUTONOMOUS = "AUTONOMOUS"


@dataclass
class SuitabilityVerdict:
    is_suitable: bool
    trading_style: TradingStyle
    eligible_strategies: List[str]
    recommended_risk_pct: float
    max_exposure_usd: float
    constraints: List[str] = field(default_factory=list)
    rejection_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_suitable": self.is_suitable,
            "trading_style": self.trading_style.value,
            "eligible_strategies": self.eligible_strategies,
            "recommended_risk_pct": round(self.recommended_risk_pct, 4),
            "max_exposure_usd": round(self.max_exposure_usd, 2),
            "constraints": self.constraints,
            "rejection_reasons": self.rejection_reasons,
        }


class AccountSuitabilityEngine:
    """
    Evaluates account characteristics against strategy execution requirements.
    """

    # Minimum equity thresholds by operating style
    MIN_EQUITY_BY_STYLE: Dict[TradingStyle, float] = {
        TradingStyle.SCALPING: 1000.0,       # Requires higher equity to overcome friction drag
        TradingStyle.INTRADAY: 500.0,
        TradingStyle.SWING: 250.0,
        TradingStyle.POSITION: 500.0,
        TradingStyle.INVESTMENT: 100.0,
        TradingStyle.HEDGING: 2000.0,        # Requires dual-margin buffers
        TradingStyle.ARBITRAGE: 5000.0,      # Requires venue balance distribution
        TradingStyle.AUTONOMOUS: 250.0,      # Multi-style orchestration
    }

    @classmethod
    def evaluate_suitability(
        cls,
        account_equity_usd: float,
        available_margin_usd: float,
        style: TradingStyle,
        venue: str = "BINANCE_FUTURES",
        user_max_risk_pct: float = 0.01,
        available_strategies: Optional[List[str]] = None,
    ) -> SuitabilityVerdict:
        """
        Computes suitability verdict, recommended risk percentage, and eligible strategies.
        Strict rule: user_max_risk_pct can never exceed 1.0% (0.01).
        """
        rejections: List[str] = []
        constraints: List[str] = []

        # 1. Enforce Frozen 1% Risk Invariant
        effective_risk = min(user_max_risk_pct, 0.01)
        if user_max_risk_pct > 0.01:
            constraints.append("Requested risk exceeded 1.0% frozen cap. Capped at 1.0%.")

        # 2. Check Minimum Capital
        min_equity = cls.MIN_EQUITY_BY_STYLE.get(style, 250.0)
        if account_equity_usd < min_equity:
            rejections.append(
                f"Account equity (${account_equity_usd:,.2f}) below minimum for {style.value} (${min_equity:,.2f})"
            )

        # 3. Check Available Margin
        margin_pct = available_margin_usd / max(account_equity_usd, 1.0)
        if margin_pct < 0.20:
            rejections.append(f"Available margin ({margin_pct*100:.1f}%) too low (<20% buffer)")

        # 4. Map Style to Compatible Strategies
        # Default strategy universe if none supplied
        candidate_pool = available_strategies or [
            "STRATA_KING_ENGINE",
            "STRATA_TREND_PULLBACK",
            "STRATA_MOMENTUM_BREAKOUT",
            "STRATA_REGIME_ADAPTIVE",
        ]

        eligible: List[str] = []
        if style in (TradingStyle.SWING, TradingStyle.AUTONOMOUS, TradingStyle.POSITION):
            eligible.append("STRATA_KING_ENGINE")
            eligible.append("STRATA_TREND_PULLBACK")
            eligible.append("STRATA_REGIME_ADAPTIVE")
        if style in (TradingStyle.INTRADAY, TradingStyle.SCALPING, TradingStyle.AUTONOMOUS):
            eligible.append("STRATA_MOMENTUM_BREAKOUT")
            if account_equity_usd >= 1000.0:
                eligible.append("STRATA_KING_ENGINE")

        # Deduplicate and intersect with available
        eligible = [s for s in list(dict.fromkeys(eligible)) if s in candidate_pool]

        max_exposure = account_equity_usd * 0.03  # Max 3% portfolio heat
        is_suitable = (len(rejections) == 0 and len(eligible) > 0)

        if not eligible and len(rejections) == 0:
            rejections.append("No compatible qualified strategies found for the selected trading style.")

        return SuitabilityVerdict(
            is_suitable=is_suitable,
            trading_style=style,
            eligible_strategies=eligible if is_suitable else [],
            recommended_risk_pct=effective_risk,
            max_exposure_usd=max_exposure,
            constraints=constraints,
            rejection_reasons=rejections,
        )
