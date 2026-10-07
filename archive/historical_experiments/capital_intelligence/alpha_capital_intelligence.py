"""
Quantitative Systems Platform (QSP) — Alpha & Capital Intelligence Layer.

Implements the economic intelligence above strategy signals:
1. NetEdgeEngine: Computes Gross Expected R minus fees, spread, slippage, market impact,
   funding, and latency. Enforces the Trade Economics Gate (No-Trade default when Net Edge <= 0.05R).
2. AlphaConfidenceEngine: Computes Bayesian standard errors and confidence intervals based on sample size.
3. AlphaSelectionEngine: Dynamic Opportunity Auction ranking competing trades by marginal risk-adjusted return.
4. AlphaCapacityEngine: Square-root market impact modeling across capital tiers ($10 to $10,000,000).
5. FactorAttributionEngine: Decomposes returns into independent risk drivers (Trend, Momentum, Volatility, Carry, Microstructure).
6. AlphaHealthEngine: Statistical health index and Edge Decay Clock for active strategies.
"""

import math
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple


class ConfidenceBand(str, Enum):
    HIGH = "HIGH"        # N >= 300, lower bound > 0.08R
    MEDIUM = "MEDIUM"    # 100 <= N < 300, lower bound > 0.00R
    LOW = "LOW"          # N < 100 or lower bound <= 0.00R
    UNRELIABLE = "UNRELIABLE"


class AlphaHealthStatus(str, Enum):
    NORMAL = "NORMAL"            # Score 85 - 100
    WATCH = "WATCH"              # Score 70 - 85
    REDUCE = "REDUCE"            # Score 50 - 70 (cut allocation 50%)
    QUARANTINE = "QUARANTINE"    # Score 30 - 50 (halt trading, generate research ticket)
    RETIRE = "RETIRE"            # Score < 30 (move to graveyard)


@dataclass
class NetEdgeBreakdown:
    symbol: str
    direction: str
    gross_alpha_r: float
    fee_drag_r: float
    spread_drag_r: float
    slippage_drag_r: float
    funding_drag_r: float
    market_impact_drag_r: float
    latency_cost_r: float
    expected_net_edge_r: float
    is_economically_viable: bool
    verdict: str  # 'TRADE' or 'NO_TRADE'
    rationale: str


@dataclass
class AlphaConfidenceMetrics:
    strategy_id: str
    sample_size_n: int
    mean_expectancy_r: float
    std_dev_r: float
    standard_error_r: float
    confidence_interval_95: Tuple[float, float]
    confidence_band: ConfidenceBand
    confidence_score: float  # 0.0 to 1.0


@dataclass
class CapacityCurvePoint:
    capital_usd: float
    estimated_impact_bps: float
    estimated_impact_r: float
    net_expectancy_r: float
    is_capacity_exceeded: bool


@dataclass
class FactorAttribution:
    trend_beta_pnl_r: float
    momentum_pnl_r: float
    volatility_expansion_pnl_r: float
    carry_funding_pnl_r: float
    microstructure_execution_pnl_r: float
    unexplained_residual_r: float
    primary_alpha_driver: str


# =====================================================================
# 1. Net Edge Estimation Engine & Trade Economics Gate
# =====================================================================

class NetEdgeEngine:
    """
    Deducts all microstructure frictions to calculate realized Expected Net Edge in R-multiples.
    Enforces the Trade Economics Gate: If Expected Net Edge <= 0.05R -> NO_TRADE.
    """

    MIN_NET_EDGE_THRESHOLD_R = 0.05  # Minimum viable net edge

    @classmethod
    def calculate_net_edge(
        cls,
        symbol: str,
        direction: str,
        gross_alpha_r: float,
        stop_distance_pct: float,
        order_notional_usd: float,
        venue: str = "USDM_FUTURES",
        taker_fee_pct: float = 0.0005,  # 0.05%
        spread_pct: float = 0.0002,     # 0.02% typical top of book
        slippage_pct: float = 0.0003,   # 0.03% modeled slippage
        funding_8h_pct: float = 0.0001, # 0.01% standard funding
        average_daily_volume_usd: float = 1_000_000_000.0,
    ) -> NetEdgeBreakdown:
        if stop_distance_pct <= 0:
            return NetEdgeBreakdown(
                symbol=symbol, direction=direction, gross_alpha_r=gross_alpha_r,
                fee_drag_r=0, spread_drag_r=0, slippage_drag_r=0, funding_drag_r=0,
                market_impact_drag_r=0, latency_cost_r=0, expected_net_edge_r=0,
                is_economically_viable=False, verdict="NO_TRADE", rationale="Zero stop distance",
            )

        # Convert percentage costs to R-multiples: Drag (R) = Cost (%) / StopDistance (%)
        # Round trip taker fee = 2 * taker_fee_pct
        fee_drag_r = (taker_fee_pct * 2.0) / (stop_distance_pct / 100.0)
        spread_drag_r = spread_pct / (stop_distance_pct / 100.0)
        slippage_drag_r = (slippage_pct * 2.0) / (stop_distance_pct / 100.0)
        funding_drag_r = funding_8h_pct / (stop_distance_pct / 100.0)

        # Market impact square root law: impact = 0.5 * sigma * sqrt(Size / ADV)
        daily_volatility = 0.04  # 4% daily sigma
        impact_pct = 0.5 * daily_volatility * math.sqrt(max(0.0, order_notional_usd / average_daily_volume_usd))
        market_impact_drag_r = impact_pct / (stop_distance_pct / 100.0)

        # Latency cost (modeled as 0.01R for sub-second execution, higher if delayed)
        latency_cost_r = 0.01

        total_friction_r = (
            fee_drag_r + spread_drag_r + slippage_drag_r +
            funding_drag_r + market_impact_drag_r + latency_cost_r
        )
        expected_net_edge_r = gross_alpha_r - total_friction_r

        is_viable = expected_net_edge_r > cls.MIN_NET_EDGE_THRESHOLD_R
        verdict = "TRADE" if is_viable else "NO_TRADE"
        rationale = (
            f"Gross Alpha: +{gross_alpha_r:.3f}R | Total Frictions: -{total_friction_r:.3f}R "
            f"(Fees: -{fee_drag_r:.3f}R, Spread: -{spread_drag_r:.3f}R, Slip: -{slippage_drag_r:.3f}R, "
            f"Impact: -{market_impact_drag_r:.3f}R) | Net Edge: {expected_net_edge_r:.3f}R"
        )
        if not is_viable:
            rationale += f" -> BELOW ECONOMIC VIABILITY THRESHOLD (+{cls.MIN_NET_EDGE_THRESHOLD_R:.2f}R)"

        return NetEdgeBreakdown(
            symbol=symbol,
            direction=direction,
            gross_alpha_r=round(gross_alpha_r, 4),
            fee_drag_r=round(fee_drag_r, 4),
            spread_drag_r=round(spread_drag_r, 4),
            slippage_drag_r=round(slippage_drag_r, 4),
            funding_drag_r=round(funding_drag_r, 4),
            market_impact_drag_r=round(market_impact_drag_r, 4),
            latency_cost_r=round(latency_cost_r, 4),
            expected_net_edge_r=round(expected_net_edge_r, 4),
            is_economically_viable=is_viable,
            verdict=verdict,
            rationale=rationale,
        )


# =====================================================================
# 2. Alpha Confidence Engine
# =====================================================================

class AlphaConfidenceEngine:
    """
    Quantifies statistical uncertainty around strategy expectancy estimates.
    Prevents small-sample winners from receiving unwarranted risk capital.
    """

    @classmethod
    def evaluate_confidence(
        cls,
        strategy_id: str,
        trade_r_multiples: List[float],
    ) -> AlphaConfidenceMetrics:
        n = len(trade_r_multiples)
        if n < 10:
            return AlphaConfidenceMetrics(
                strategy_id=strategy_id,
                sample_size_n=n,
                mean_expectancy_r=0.0,
                std_dev_r=0.0,
                standard_error_r=0.0,
                confidence_interval_95=(0.0, 0.0),
                confidence_band=ConfidenceBand.UNRELIABLE,
                confidence_score=0.0,
            )

        arr = np.array(trade_r_multiples, dtype=np.float64)
        mean_r = float(np.mean(arr))
        std_r = float(np.std(arr, ddof=1))
        se_r = std_r / math.sqrt(n)

        # 95% Confidence Interval
        ci_lower = mean_r - 1.96 * se_r
        ci_upper = mean_r + 1.96 * se_r

        # Score (0.0 to 1.0)
        # Driven by sample size (saturates at N=1000) and lower bound
        n_factor = min(1.0, math.log10(max(10, n)) / 3.0)  # log10(1000) / 3 = 1.0
        edge_factor = max(0.0, min(1.0, ci_lower / 0.15)) if ci_lower > 0 else 0.0
        sample_penalty = min(1.0, n / 100.0)
        conf_score = (0.5 * n_factor + 0.5 * edge_factor) * sample_penalty

        if n >= 300 and ci_lower >= 0.08:
            band = ConfidenceBand.HIGH
        elif n >= 100 and ci_lower > 0.00:
            band = ConfidenceBand.MEDIUM
        elif n >= 30:
            band = ConfidenceBand.LOW
        else:
            band = ConfidenceBand.UNRELIABLE

        return AlphaConfidenceMetrics(
            strategy_id=strategy_id,
            sample_size_n=n,
            mean_expectancy_r=round(mean_r, 4),
            std_dev_r=round(std_r, 4),
            standard_error_r=round(se_r, 4),
            confidence_interval_95=(round(ci_lower, 4), round(ci_upper, 4)),
            confidence_band=band,
            confidence_score=round(conf_score, 3),
        )


# =====================================================================
# 3. Alpha Capacity & Capital Elasticity Engine
# =====================================================================

class AlphaCapacityEngine:
    """
    Evaluates how expected net alpha decays as deployed capital scales from $10 to $10,000,000.
    """

    CAPITAL_TIERS = [10.0, 100.0, 1_000.0, 10_000.0, 100_000.0, 1_000_000.0, 10_000_000.0]

    @classmethod
    def evaluate_capacity_curve(
        cls,
        strategy_id: str,
        symbol: str,
        baseline_net_expectancy_r: float,
        stop_distance_pct: float,
        average_daily_volume_usd: float = 1_000_000_000.0,
    ) -> List[CapacityCurvePoint]:
        curve = []
        daily_volatility = 0.04

        for cap in cls.CAPITAL_TIERS:
            # Assume 1.0x to 2.0x notional position per trade
            order_notional = cap
            # Market impact model in bps: impact_bps = 5000 * sigma * sqrt(Size / ADV)
            pct_adv = max(0.0, order_notional / average_daily_volume_usd)
            impact_bps = 5000.0 * daily_volatility * math.sqrt(pct_adv)
            impact_pct = impact_bps / 10000.0
            impact_r = impact_pct / (stop_distance_pct / 100.0)

            net_exp = baseline_net_expectancy_r - impact_r
            is_exceeded = net_exp <= 0.05 or impact_r >= (baseline_net_expectancy_r * 0.50)

            curve.append(
                CapacityCurvePoint(
                    capital_usd=cap,
                    estimated_impact_bps=round(impact_bps, 2),
                    estimated_impact_r=round(impact_r, 4),
                    net_expectancy_r=round(net_exp, 4),
                    is_capacity_exceeded=is_exceeded,
                )
            )
        return curve


# =====================================================================
# 4. Alpha Selection & Opportunity Auction Engine
# =====================================================================

class AlphaSelectionEngine:
    """
    Internal Capital Auction: Dynamically ranks competing trade opportunities
    by marginal risk-adjusted net return per unit of portfolio capacity.
    """

    @classmethod
    def rank_opportunities(
        cls,
        candidates: List[Dict[str, Any]],
        current_portfolio_heat: float,
        max_heat_limit: float = 3.0,
    ) -> List[Dict[str, Any]]:
        """
        Ranks opportunities using the Institutional Auction Score:
        Score = (NetEdge * ConfidenceScore * RegimeFit) / (DrawdownPenalty * CorrelationPenalty * CostDrag)
        """
        ranked = []
        remaining_heat = max(0.0, max_heat_limit - current_portfolio_heat)

        for c in candidates:
            net_edge = c.get("expected_net_edge_r", 0.15)
            conf_score = c.get("confidence_score", 0.5)
            regime_fit = c.get("regime_compatibility", 0.8)
            dd_penalty = 1.0 + max(0.0, c.get("current_drawdown_pct", 0.0) / 20.0)
            corr_penalty = 1.0 + (0.5 if c.get("is_correlated", False) else 0.0)
            cost_drag = 1.0 + c.get("friction_drag_r", 0.05)

            if net_edge <= 0.05:
                auction_score = 0.0
            else:
                auction_score = (net_edge * conf_score * regime_fit) / (dd_penalty * corr_penalty * cost_drag)

            rec = dict(c)
            rec["auction_score"] = round(auction_score, 4)
            rec["auction_verdict"] = "WINNER" if auction_score > 0.05 and remaining_heat >= 0.3 else "REJECTED"
            ranked.append(rec)

        ranked.sort(key=lambda x: x["auction_score"], reverse=True)
        return ranked


# =====================================================================
# 5. Factor Attribution Engine
# =====================================================================

class FactorAttributionEngine:
    """
    Decomposes realized strategy returns into underlying systematic risk factors.
    Allows the platform to determine whether profits stem from Trend, Momentum, Volatility, or Execution.
    """

    @classmethod
    def attribute_returns(
        cls,
        total_realized_r: float,
        strategy_family: str,
        market_regime_trend_score: float,  # +1.0 strong trend, 0.0 neutral
        market_volatility_expansion_score: float,  # +1.0 expansion, 0.0 normal
    ) -> FactorAttribution:
        fam = strategy_family.upper()

        if "FAM-07" in fam or "FAM-01" in fam or "FAM-02" in fam:
            trend_weight = 0.60
            momentum_weight = 0.20
            vol_weight = 0.15
            carry_weight = -0.02
            exec_weight = 0.07
        elif "FAM-04" in fam:
            trend_weight = 0.30
            momentum_weight = 0.55
            vol_weight = 0.15
            carry_weight = -0.02
            exec_weight = 0.02
        elif "FAM-09" in fam:
            trend_weight = 0.05
            momentum_weight = 0.10
            vol_weight = 0.10
            carry_weight = 0.00
            exec_weight = 0.75  # Relative value is execution & spread-driven
        else:
            trend_weight = 0.40
            momentum_weight = 0.30
            vol_weight = 0.20
            carry_weight = -0.02
            exec_weight = 0.12

        trend_pnl = total_realized_r * trend_weight * (0.8 + 0.2 * market_regime_trend_score)
        mom_pnl = total_realized_r * momentum_weight
        vol_pnl = total_realized_r * vol_weight * (0.8 + 0.2 * market_volatility_expansion_score)
        carry_pnl = total_realized_r * carry_weight
        exec_pnl = total_realized_r * exec_weight
        residual = total_realized_r - (trend_pnl + mom_pnl + vol_pnl + carry_pnl + exec_pnl)

        factors = {
            "Trend Beta": trend_pnl,
            "Momentum": mom_pnl,
            "Volatility Expansion": vol_pnl,
            "Microstructure / Execution": exec_pnl,
        }
        primary_driver = max(factors.items(), key=lambda x: x[1])[0]

        return FactorAttribution(
            trend_beta_pnl_r=round(trend_pnl, 2),
            momentum_pnl_r=round(mom_pnl, 2),
            volatility_expansion_pnl_r=round(vol_pnl, 2),
            carry_funding_pnl_r=round(carry_pnl, 2),
            microstructure_execution_pnl_r=round(exec_pnl, 2),
            unexplained_residual_r=round(residual, 2),
            primary_alpha_driver=primary_driver,
        )


# =====================================================================
# 6. Alpha Health & Edge Decay Clock
# =====================================================================

class AlphaHealthEngine:
    """
    Maintains a continuous statistical health score (0 to 100) for every active strategy.
    Drives proactive capital deallocation before catastrophic drawdown occurs.
    """

    @classmethod
    def compute_health_index(
        cls,
        strategy_id: str,
        historical_expectancy_r: float,
        recent_expectancy_r: float,
        current_drawdown_r: float,
        historical_max_dd_r: float,
        recent_win_rate: float,
        historical_win_rate: float,
        sample_size_recent: int = 30,
    ) -> Tuple[float, AlphaHealthStatus, str]:
        if sample_size_recent < 5:
            return 100.0, AlphaHealthStatus.NORMAL, "Insufficient recent trades to evaluate health decay"

        # 1. Expectancy Decay (40% weight)
        exp_ratio = recent_expectancy_r / historical_expectancy_r if historical_expectancy_r > 0 else 1.0
        exp_score = max(0.0, min(100.0, exp_ratio * 100.0))

        # 2. Drawdown Stress (35% weight)
        dd_ratio = current_drawdown_r / historical_max_dd_r if historical_max_dd_r > 0 else 0.0
        dd_score = max(0.0, 100.0 - (dd_ratio * 70.0))

        # 3. Win Rate Stability (25% weight)
        wr_diff = historical_win_rate - recent_win_rate
        wr_score = max(0.0, 100.0 - max(0.0, wr_diff * 4.0))

        total_health = 0.40 * exp_score + 0.35 * dd_score + 0.25 * wr_score
        total_health = round(max(0.0, min(100.0, total_health)), 1)

        notes = []
        if total_health >= 85.0:
            status = AlphaHealthStatus.NORMAL
            notes.append("Nominal operational variance; full capital allocation approved")
        elif total_health >= 70.0:
            status = AlphaHealthStatus.WATCH
            notes.append("Moderate underperformance; flagged for enhanced telemetry monitoring")
        elif total_health >= 50.0:
            status = AlphaHealthStatus.REDUCE
            notes.append(f"Statistically meaningful edge decay (Exp ratio: {exp_ratio:.2f}); reducing risk allocation by 50%")
        elif total_health >= 30.0:
            status = AlphaHealthStatus.QUARANTINE
            notes.append(f"Severe degradation (DD ratio: {dd_ratio:.2f}x); trading quarantined and research ticket triggered")
        else:
            status = AlphaHealthStatus.RETIRE
            notes.append("Terminal edge exhaustion; candidate recommended for permanent retirement to Graveyard")

        return total_health, status, "; ".join(notes)
