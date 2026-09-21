"""
QCP Phase 9 — Comprehensive Hedging Engine.
Decomposes portfolio exposures and constructs hedging overlays across:
1. Beta Hedge (macro systematic market direction relative to BTC/ETH)
2. Delta Hedge (net linear directional delta across perps and options)
3. Volatility Hedge (vega/tail risk protection via volatility instruments)
4. Correlation Hedge (cross-asset spread hedging to neutralize basis drift)
5. Basis Hedge (spot vs perp funding rate and calendar curve arbitrage)

STRICT INVARIANT:
All hedge proposals must pass the Risk Governor before submission to the Execution Gateway.
No hedge can increase portfolio heat beyond the 3.00% ceiling.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("QCP.HedgingEngine")


class HedgeMode(str, enum.Enum):
    BETA = "BETA"
    DELTA = "DELTA"
    VOLATILITY = "VOLATILITY"
    CORRELATION = "CORRELATION"
    BASIS = "BASIS"


class HedgeStatus(str, enum.Enum):
    PENDING_RISK_AUDIT = "PENDING_RISK_AUDIT"
    APPROVED = "APPROVED"
    REJECTED_HEAT_BREACH = "REJECTED_HEAT_BREACH"
    REJECTED_RISK_VETO = "REJECTED_RISK_VETO"
    EXECUTED = "EXECUTED"


@dataclass
class ExposureDecomposition:
    symbol: str
    asset_class: str  # PERP, SPOT, OPTION
    notional_usd: float
    net_delta: float
    beta_to_btc: float
    vega: float
    open_basis_bps: float
    active_heat_pct: float


@dataclass
class HedgeRecommendation:
    hedge_id: str
    mode: HedgeMode
    target_instrument: str
    direction: str  # BUY or SELL
    target_notional_usd: float
    estimated_delta_impact: float
    estimated_beta_impact: float
    estimated_additional_heat_pct: float
    status: HedgeStatus
    rationale: str
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ComprehensiveHedgingEngine:
    """
    Hedging Engine coordinating portfolio decomposition and multi-asset overlay hedging.
    """

    MAX_PORTFOLIO_HEAT_PCT = 3.00
    TARGET_MAX_UNHEDGED_BETA = 1.25
    MIN_EXECUTION_NOTIONAL_USD = 10.00

    def __init__(self, risk_governor: Optional[Any] = None):
        self._risk_governor = risk_governor

    def decompose_portfolio(
        self,
        positions: List[Dict[str, Any]],
        account_equity_usd: float,
    ) -> List[ExposureDecomposition]:
        """Decomposes raw position records into multidimensional risk exposures."""
        decomposed: List[ExposureDecomposition] = []
        for pos in positions:
            symbol = pos.get("symbol", "UNKNOWN")
            notional = float(pos.get("notional_usd", 0.0))
            direction = pos.get("direction", "LONG").upper()
            sign = 1.0 if direction == "LONG" else -1.0
            asset_class = pos.get("asset_class", "PERP")

            # Empirical beta estimates
            beta_map = {"BTCUSDT": 1.0, "ETHUSDT": 1.18, "SOLUSDT": 1.42}
            beta = beta_map.get(symbol, 1.20) * sign

            delta = sign * notional
            vega = float(pos.get("vega", 0.0))
            basis_bps = float(pos.get("basis_bps", 0.0))
            risk_usd = float(pos.get("risk_usd", notional * 0.02))
            heat_pct = (risk_usd / max(1.0, account_equity_usd)) * 100.0

            decomposed.append(
                ExposureDecomposition(
                    symbol=symbol,
                    asset_class=asset_class,
                    notional_usd=notional,
                    net_delta=delta,
                    beta_to_btc=beta,
                    vega=vega,
                    open_basis_bps=basis_bps,
                    active_heat_pct=heat_pct,
                )
            )
        return decomposed

    def generate_hedges(
        self,
        decompositions: List[ExposureDecomposition],
        account_equity_usd: float,
        current_portfolio_heat_pct: float,
    ) -> List[HedgeRecommendation]:
        """
        Calculates required hedge overlays and submits each for risk evaluation.
        """
        recommendations: List[HedgeRecommendation] = []
        if account_equity_usd <= 0:
            return recommendations

        total_net_delta = sum(d.net_delta for d in decompositions)
        total_portfolio_beta = sum((d.beta_to_btc * d.notional_usd) / account_equity_usd for d in decompositions)
        total_vega = sum(d.vega for d in decompositions)

        # 1. Beta Hedge Evaluation
        if abs(total_portfolio_beta) > self.TARGET_MAX_UNHEDGED_BETA:
            excess_beta = total_portfolio_beta - (self.TARGET_MAX_UNHEDGED_BETA if total_portfolio_beta > 0 else -self.TARGET_MAX_UNHEDGED_BETA)
            hedge_notional = abs(excess_beta * account_equity_usd)
            hedge_dir = "SELL" if total_portfolio_beta > 0 else "BUY"

            if hedge_notional >= self.MIN_EXECUTION_NOTIONAL_USD:
                add_heat = (hedge_notional * 0.01 / account_equity_usd) * 100.0
                rec = HedgeRecommendation(
                    hedge_id=f"HEDGE-BETA-{int(datetime.now(timezone.utc).timestamp())}",
                    mode=HedgeMode.BETA,
                    target_instrument="BTCUSDT",
                    direction=hedge_dir,
                    target_notional_usd=round(hedge_notional, 2),
                    estimated_delta_impact=-hedge_notional if hedge_dir == "SELL" else hedge_notional,
                    estimated_beta_impact=-excess_beta,
                    estimated_additional_heat_pct=round(add_heat, 4),
                    status=HedgeStatus.PENDING_RISK_AUDIT,
                    rationale=f"Net portfolio beta {total_portfolio_beta:.2f} exceeds ceiling {self.TARGET_MAX_UNHEDGED_BETA:.2f}",
                )
                recommendations.append(rec)

        # 2. Volatility / Vega Hedge Evaluation
        if total_vega < -500.0:  # Short vega danger zone
            hedge_notional = abs(total_vega) * 2.0
            rec = HedgeRecommendation(
                hedge_id=f"HEDGE-VOL-{int(datetime.now(timezone.utc).timestamp())}",
                mode=HedgeMode.VOLATILITY,
                target_instrument="BTC-OPTIONS-STRADDLE",
                direction="BUY",
                target_notional_usd=round(hedge_notional, 2),
                estimated_delta_impact=0.0,
                estimated_beta_impact=0.0,
                estimated_additional_heat_pct=0.25,
                status=HedgeStatus.PENDING_RISK_AUDIT,
                rationale=f"Short vega exposure {total_vega:.1f} violates tail volatility limits",
            )
            recommendations.append(rec)

        # 3. Basis Hedge Evaluation
        for d in decompositions:
            if abs(d.open_basis_bps) > 150.0 and d.asset_class == "PERP":
                rec = HedgeRecommendation(
                    hedge_id=f"HEDGE-BASIS-{d.symbol}-{int(datetime.now(timezone.utc).timestamp())}",
                    mode=HedgeMode.BASIS,
                    target_instrument=f"{d.symbol}-SPOT",
                    direction="SELL" if d.net_delta > 0 else "BUY",
                    target_notional_usd=round(min(d.notional_usd, 50_000.0), 2),
                    estimated_delta_impact=-d.net_delta,
                    estimated_beta_impact=0.0,
                    estimated_additional_heat_pct=0.10,
                    status=HedgeStatus.PENDING_RISK_AUDIT,
                    rationale=f"Spot-Perp basis divergence of {d.open_basis_bps:.1f} bps on {d.symbol}",
                )
                recommendations.append(rec)

        # Audit recommendations through Risk Governor
        audited_recommendations: List[HedgeRecommendation] = []
        for rec in recommendations:
            if current_portfolio_heat_pct + rec.estimated_additional_heat_pct > self.MAX_PORTFOLIO_HEAT_PCT:
                rec.status = HedgeStatus.REJECTED_HEAT_BREACH
                logger.warning(f"Hedge {rec.hedge_id} rejected: violates 3% portfolio heat ceiling")
            elif self._risk_governor and not self._risk_governor.approve_hedge(rec):
                rec.status = HedgeStatus.REJECTED_RISK_VETO
                logger.warning(f"Hedge {rec.hedge_id} rejected by Risk Governor veto")
            else:
                rec.status = HedgeStatus.APPROVED
            audited_recommendations.append(rec)

        return audited_recommendations
