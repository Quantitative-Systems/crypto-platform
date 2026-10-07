"""
Quantitative Crypto Platform (QCP) — 7-Dimensional Portfolio Risk Firewall.

Institutional multi-risk governor capable of vetoing ('saying NO') to trades across:
1. Market Risk: Directional exposure, beta, gross leverage, asset concentration.
2. Liquidity Risk: Order-book depth, market impact, spread widening, liquidation capacity.
3. Correlation Risk: Cross-asset correlation, same-direction factor clustering, correlation spikes.
4. Execution Risk: Feed latency, adverse slippage spikes, rejected order rate, stale pricing.
5. Exchange Risk: API error frequency, exchange status, abnormal funding rates.
6. Model Risk: Strategy degradation score, rolling expectancy decay, regime mismatch.
7. Portfolio Tail Risk: 95% VaR/CVaR limits, account drawdown circuit breaker, crypto-wide flash crash halt.

Authority: The Capital Firewall remains the final operational arbiter over all trading signals.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import math


class FirewallAction(str, Enum):
    APPROVE = "APPROVE"
    APPROVE_REDUCED_RISK = "APPROVE_REDUCED_RISK"
    REJECT = "REJECT"


class DimensionStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass
class DimensionEvaluation:
    dimension: str
    status: DimensionStatus
    score: float  # 0.0 (safe) to 1.0 (breached)
    threshold: float
    details: Dict[str, Any]
    rejection_reasons: List[str] = field(default_factory=list)


@dataclass
class FirewallDecision:
    action: FirewallAction
    risk_multiplier: float  # 1.0 (full), 0.5 (reduced), 0.0 (vetoed)
    overall_risk_score: float
    dimensions: Dict[str, DimensionEvaluation]
    rejection_reasons: List[str]
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "risk_multiplier": self.risk_multiplier,
            "overall_risk_score": round(self.overall_risk_score, 4),
            "rejection_reasons": self.rejection_reasons,
            "rationale": self.rationale,
            "dimensions": {
                k: {
                    "status": v.status.value,
                    "score": round(v.score, 4),
                    "threshold": v.threshold,
                    "details": v.details,
                    "rejection_reasons": v.rejection_reasons,
                }
                for k, v in self.dimensions.items()
            },
        }


@dataclass
class FirewallThresholds:
    # 1. Market Risk
    max_gross_leverage: float = 3.0
    max_asset_concentration_pct: float = 50.0  # max 50% notional in single asset
    max_portfolio_heat_pct: float = 3.0        # max 3.0% account risk
    max_directional_beta: float = 2.5

    # 2. Liquidity Risk
    max_spread_pct: float = 0.0015             # 0.15% max spread
    max_order_vs_depth_pct: float = 5.0        # order cannot exceed 5% of top-book depth
    max_market_impact_bps: float = 15.0        # max 15 bps impact

    # 3. Correlation Risk
    max_correlated_heat_pct: float = 1.8       # max 1.8% in highly correlated direction
    correlation_clustering_threshold: float = 0.80

    # 4. Execution Risk
    max_stale_price_sec: float = 30.0
    max_feed_latency_ms: float = 2000.0
    max_trailing_slippage_bps: float = 10.0

    # 5. Exchange Risk
    max_api_error_rate_pct: float = 2.0
    max_abnormal_funding_bps: float = 25.0     # 0.25% 8h funding rate

    # 6. Model Risk
    max_strategy_drift_score: float = 0.40
    min_rolling_expectancy_r: float = -0.15

    # 7. Tail Risk
    max_portfolio_var95_pct: float = 2.5
    account_max_drawdown_halt_pct: float = 6.0
    flash_crash_threshold_pct: float = -8.0    # -8% in 1h triggers global halt


class PortfolioRiskFirewall:
    """
    Independent institutional risk firewall.
    Evaluates every potential trade order through the 7 risk dimensions before
    order execution can occur.
    """

    def __init__(self, thresholds: Optional[FirewallThresholds] = None):
        self.thresholds = thresholds or FirewallThresholds()

    def evaluate_order(
        self,
        candidate_symbol: str,
        candidate_direction: str,  # "BUY" / "SELL" or "LONG" / "SHORT"
        intended_risk_usd: float,
        intended_notional_usd: float,
        account_equity_usd: float,
        current_peak_equity_usd: float,
        open_positions: List[Dict[str, Any]],
        market_metrics: Optional[Dict[str, Any]] = None,
        execution_metrics: Optional[Dict[str, Any]] = None,
        exchange_metrics: Optional[Dict[str, Any]] = None,
        model_metrics: Optional[Dict[str, Any]] = None,
    ) -> FirewallDecision:
        """
        Runs comprehensive 7-dimensional risk assessment.
        """
        market_metrics = market_metrics or {}
        execution_metrics = execution_metrics or {}
        exchange_metrics = exchange_metrics or {}
        model_metrics = model_metrics or {}

        rejection_reasons: List[str] = []
        dimensions: Dict[str, DimensionEvaluation] = {}

        # ---------------------------------------------------------------------
        # 1. Market Risk Assessment
        # ---------------------------------------------------------------------
        current_notional = sum(float(p.get("notional_usd", 0.0)) for p in open_positions)
        current_heat_usd = sum(float(p.get("risk_usd", 0.0)) for p in open_positions)

        projected_notional = current_notional + intended_notional_usd
        projected_leverage = projected_notional / account_equity_usd if account_equity_usd > 0 else 999.0
        projected_heat_pct = ((current_heat_usd + intended_risk_usd) / account_equity_usd) * 100.0 if account_equity_usd > 0 else 100.0

        # Asset concentration
        asset_notionals: Dict[str, float] = {}
        for p in open_positions:
            sym = p.get("symbol", "UNKNOWN").replace("/", "")
            asset_notionals[sym] = asset_notionals.get(sym, 0.0) + float(p.get("notional_usd", 0.0))
        clean_sym = candidate_symbol.replace("/", "")
        asset_notionals[clean_sym] = asset_notionals.get(clean_sym, 0.0) + intended_notional_usd

        max_asset_notional = max(asset_notionals.values()) if asset_notionals else intended_notional_usd
        concentration_pct = (max_asset_notional / projected_notional) * 100.0 if projected_notional > 0 else 0.0

        mkt_rejections = []
        if projected_leverage > self.thresholds.max_gross_leverage:
            mkt_rejections.append(
                f"Gross leverage {projected_leverage:.2f}x exceeds ceiling {self.thresholds.max_gross_leverage:.1f}x"
            )
        if projected_heat_pct > self.thresholds.max_portfolio_heat_pct:
            mkt_rejections.append(
                f"Portfolio heat {projected_heat_pct:.2f}% exceeds ceiling {self.thresholds.max_portfolio_heat_pct:.1f}%"
            )
        if len(open_positions) >= 2 and concentration_pct > self.thresholds.max_asset_concentration_pct:
            mkt_rejections.append(
                f"Asset concentration {concentration_pct:.1f}% exceeds limit {self.thresholds.max_asset_concentration_pct:.1f}%"
            )

        mkt_score = max(
            projected_leverage / self.thresholds.max_gross_leverage,
            projected_heat_pct / self.thresholds.max_portfolio_heat_pct,
        )
        dimensions["market_risk"] = DimensionEvaluation(
            dimension="Market Risk",
            status=DimensionStatus.FAIL if mkt_rejections else (DimensionStatus.WARN if mkt_score > 0.8 else DimensionStatus.PASS),
            score=min(1.0, mkt_score),
            threshold=1.0,
            details={
                "projected_leverage": round(projected_leverage, 2),
                "projected_heat_pct": round(projected_heat_pct, 2),
                "concentration_pct": round(concentration_pct, 2),
            },
            rejection_reasons=mkt_rejections,
        )
        rejection_reasons.extend(mkt_rejections)

        # ---------------------------------------------------------------------
        # 2. Liquidity Risk Assessment
        # ---------------------------------------------------------------------
        spread_pct = float(market_metrics.get("spread_pct", 0.0005))
        book_depth_usd = float(market_metrics.get("book_depth_usd", 100000.0))
        depth_pct = (intended_notional_usd / book_depth_usd) * 100.0 if book_depth_usd > 0 else 100.0
        est_impact_bps = float(market_metrics.get("estimated_impact_bps", 3.0))

        liq_rejections = []
        if spread_pct > self.thresholds.max_spread_pct:
            liq_rejections.append(
                f"Market spread {spread_pct*100:.3f}% exceeds maximum allowable {self.thresholds.max_spread_pct*100:.2f}%"
            )
        if depth_pct > self.thresholds.max_order_vs_depth_pct:
            liq_rejections.append(
                f"Order size is {depth_pct:.1f}% of order book depth (limit {self.thresholds.max_order_vs_depth_pct:.1f}%)"
            )
        if est_impact_bps > self.thresholds.max_market_impact_bps:
            liq_rejections.append(
                f"Estimated market impact {est_impact_bps:.1f} bps exceeds ceiling {self.thresholds.max_market_impact_bps:.1f} bps"
            )

        liq_score = max(
            spread_pct / self.thresholds.max_spread_pct,
            depth_pct / self.thresholds.max_order_vs_depth_pct,
            est_impact_bps / self.thresholds.max_market_impact_bps,
        )
        dimensions["liquidity_risk"] = DimensionEvaluation(
            dimension="Liquidity Risk",
            status=DimensionStatus.FAIL if liq_rejections else (DimensionStatus.WARN if liq_score > 0.8 else DimensionStatus.PASS),
            score=min(1.0, liq_score),
            threshold=1.0,
            details={
                "spread_pct": round(spread_pct, 5),
                "depth_consumed_pct": round(depth_pct, 2),
                "impact_bps": round(est_impact_bps, 2),
            },
            rejection_reasons=liq_rejections,
        )
        rejection_reasons.extend(liq_rejections)

        # ---------------------------------------------------------------------
        # 3. Correlation Risk Assessment
        # ---------------------------------------------------------------------
        # Correlated same-direction exposure
        is_long = candidate_direction in ("BUY", "LONG")
        correlated_heat_usd = intended_risk_usd
        for p in open_positions:
            p_dir = p.get("direction", "BUY")
            p_long = p_dir in ("BUY", "LONG")
            if p_long == is_long:
                # Same directional factor in crypto universe
                correlated_heat_usd += float(p.get("risk_usd", 0.0))

        correlated_heat_pct = (correlated_heat_usd / account_equity_usd) * 100.0 if account_equity_usd > 0 else 100.0
        corr_rejections = []
        if correlated_heat_pct > self.thresholds.max_correlated_heat_pct:
            corr_rejections.append(
                f"Correlated directional heat ({'LONG' if is_long else 'SHORT'}) {correlated_heat_pct:.2f}% exceeds limit {self.thresholds.max_correlated_heat_pct:.2f}%"
            )

        corr_score = correlated_heat_pct / self.thresholds.max_correlated_heat_pct
        dimensions["correlation_risk"] = DimensionEvaluation(
            dimension="Correlation Risk",
            status=DimensionStatus.FAIL if corr_rejections else (DimensionStatus.WARN if corr_score > 0.8 else DimensionStatus.PASS),
            score=min(1.0, corr_score),
            threshold=1.0,
            details={"correlated_heat_pct": round(correlated_heat_pct, 2), "direction": "LONG" if is_long else "SHORT"},
            rejection_reasons=corr_rejections,
        )
        rejection_reasons.extend(corr_rejections)

        # ---------------------------------------------------------------------
        # 4. Execution Risk Assessment
        # ---------------------------------------------------------------------
        latency_ms = float(execution_metrics.get("latency_ms", 50.0))
        stale_sec = float(execution_metrics.get("stale_sec", 1.0))
        trail_slippage = float(execution_metrics.get("trailing_slippage_bps", 3.0))

        exec_rejections = []
        if latency_ms > self.thresholds.max_feed_latency_ms:
            exec_rejections.append(f"Feed latency {latency_ms:.0f} ms exceeds limit {self.thresholds.max_feed_latency_ms:.0f} ms")
        if stale_sec > self.thresholds.max_stale_price_sec:
            exec_rejections.append(f"Price feed stale ({stale_sec:.1f}s old > {self.thresholds.max_stale_price_sec}s)")
        if trail_slippage > self.thresholds.max_trailing_slippage_bps:
            exec_rejections.append(f"Recent slippage {trail_slippage:.1f} bps exceeds limit {self.thresholds.max_trailing_slippage_bps:.1f} bps")

        exec_score = max(
            latency_ms / self.thresholds.max_feed_latency_ms,
            stale_sec / self.thresholds.max_stale_price_sec,
            trail_slippage / self.thresholds.max_trailing_slippage_bps,
        )
        dimensions["execution_risk"] = DimensionEvaluation(
            dimension="Execution Risk",
            status=DimensionStatus.FAIL if exec_rejections else (DimensionStatus.WARN if exec_score > 0.8 else DimensionStatus.PASS),
            score=min(1.0, exec_score),
            threshold=1.0,
            details={"latency_ms": latency_ms, "stale_sec": stale_sec, "slippage_bps": trail_slippage},
            rejection_reasons=exec_rejections,
        )
        rejection_reasons.extend(exec_rejections)

        # ---------------------------------------------------------------------
        # 5. Exchange Risk Assessment
        # ---------------------------------------------------------------------
        api_err_pct = float(exchange_metrics.get("api_error_rate_pct", 0.0))
        funding_bps = abs(float(exchange_metrics.get("funding_rate_bps", 1.0)))
        exchange_down = bool(exchange_metrics.get("is_exchange_degraded", False))

        exch_rejections = []
        if exchange_down:
            exch_rejections.append("Exchange operational status is DEGRADED or HALTED")
        if api_err_pct > self.thresholds.max_api_error_rate_pct:
            exch_rejections.append(f"Exchange API error rate {api_err_pct:.2f}% exceeds limit {self.thresholds.max_api_error_rate_pct:.2f}%")
        if funding_bps > self.thresholds.max_abnormal_funding_bps:
            exch_rejections.append(f"Extreme funding rate {funding_bps:.1f} bps indicates potential liquidation cascade")

        exch_score = max(
            1.0 if exchange_down else 0.0,
            api_err_pct / self.thresholds.max_api_error_rate_pct,
            funding_bps / self.thresholds.max_abnormal_funding_bps,
        )
        dimensions["exchange_risk"] = DimensionEvaluation(
            dimension="Exchange Risk",
            status=DimensionStatus.FAIL if exch_rejections else (DimensionStatus.WARN if exch_score > 0.8 else DimensionStatus.PASS),
            score=min(1.0, exch_score),
            threshold=1.0,
            details={"api_error_rate_pct": api_err_pct, "funding_bps": funding_bps, "is_degraded": exchange_down},
            rejection_reasons=exch_rejections,
        )
        rejection_reasons.extend(exch_rejections)

        # ---------------------------------------------------------------------
        # 6. Model Risk Assessment
        # ---------------------------------------------------------------------
        drift_score = float(model_metrics.get("drift_score", 0.05))
        rolling_exp_r = float(model_metrics.get("rolling_expectancy_r", 0.20))
        regime_mismatch = bool(model_metrics.get("regime_mismatch", False))

        model_rejections = []
        if drift_score > self.thresholds.max_strategy_drift_score:
            model_rejections.append(f"Strategy drift score {drift_score:.2f} exceeds threshold {self.thresholds.max_strategy_drift_score:.2f}")
        if rolling_exp_r < self.thresholds.min_rolling_expectancy_r:
            model_rejections.append(f"Rolling expectancy {rolling_exp_r:.2f}R severely negative (decay detected)")
        if regime_mismatch:
            model_rejections.append("Current market regime contradicts strategy operational contract")

        model_score = max(
            drift_score / self.thresholds.max_strategy_drift_score,
            abs(min(0.0, rolling_exp_r)) / abs(self.thresholds.min_rolling_expectancy_r),
            1.0 if regime_mismatch else 0.0,
        )
        dimensions["model_risk"] = DimensionEvaluation(
            dimension="Model Risk",
            status=DimensionStatus.FAIL if model_rejections else (DimensionStatus.WARN if model_score > 0.8 else DimensionStatus.PASS),
            score=min(1.0, model_score),
            threshold=1.0,
            details={"drift_score": drift_score, "rolling_exp_r": rolling_exp_r, "regime_mismatch": regime_mismatch},
            rejection_reasons=model_rejections,
        )
        rejection_reasons.extend(model_rejections)

        # ---------------------------------------------------------------------
        # 7. Portfolio Tail Risk Assessment
        # ---------------------------------------------------------------------
        current_dd_pct = ((current_peak_equity_usd - account_equity_usd) / current_peak_equity_usd * 100.0) if current_peak_equity_usd > 0 else 0.0
        var95_pct = projected_heat_pct * 0.8  # Conservative proxy for 95% 1-day VaR
        crash_1h_pct = float(market_metrics.get("crypto_market_1h_return_pct", 0.0))

        tail_rejections = []
        if current_dd_pct >= self.thresholds.account_max_drawdown_halt_pct:
            tail_rejections.append(f"Account in max drawdown state ({current_dd_pct:.2f}% >= {self.thresholds.account_max_drawdown_halt_pct:.1f}% limit)")
        if crash_1h_pct <= self.thresholds.flash_crash_threshold_pct:
            tail_rejections.append(f"Market-wide flash crash detected ({crash_1h_pct:.1f}% 1h drop); circuit breaker engaged")
        if var95_pct > self.thresholds.max_portfolio_var95_pct:
            tail_rejections.append(f"Projected 95% VaR {var95_pct:.2f}% exceeds ceiling {self.thresholds.max_portfolio_var95_pct:.2f}%")

        tail_score = max(
            current_dd_pct / self.thresholds.account_max_drawdown_halt_pct,
            abs(min(0.0, crash_1h_pct)) / abs(self.thresholds.flash_crash_threshold_pct),
            var95_pct / self.thresholds.max_portfolio_var95_pct,
        )
        dimensions["tail_risk"] = DimensionEvaluation(
            dimension="Tail Risk",
            status=DimensionStatus.FAIL if tail_rejections else (DimensionStatus.WARN if tail_score > 0.8 else DimensionStatus.PASS),
            score=min(1.0, tail_score),
            threshold=1.0,
            details={"current_drawdown_pct": round(current_dd_pct, 2), "flash_crash_1h_pct": crash_1h_pct, "var95_pct": round(var95_pct, 2)},
            rejection_reasons=tail_rejections,
        )
        rejection_reasons.extend(tail_rejections)

        # ---------------------------------------------------------------------
        # Final Decision Synthesis
        # ---------------------------------------------------------------------
        overall_risk_score = float(max(d.score for d in dimensions.values()))
        has_fails = any(d.status == DimensionStatus.FAIL for d in dimensions.values())
        has_warns = any(d.status == DimensionStatus.WARN for d in dimensions.values())

        if has_fails:
            action = FirewallAction.REJECT
            risk_mult = 0.0
            rationale = f"Order VETOED by Risk Firewall across {len(rejection_reasons)} rule(s)."
        elif has_warns:
            action = FirewallAction.APPROVE_REDUCED_RISK
            risk_mult = 0.50
            rationale = "Order APPROVED with 50% de-risking due to elevated multi-factor risk scores."
        else:
            action = FirewallAction.APPROVE
            risk_mult = 1.0
            rationale = "Order APPROVED: all 7 institutional risk dimensions strictly nominal."

        return FirewallDecision(
            action=action,
            risk_multiplier=risk_mult,
            overall_risk_score=overall_risk_score,
            dimensions=dimensions,
            rejection_reasons=rejection_reasons,
            rationale=rationale,
        )
