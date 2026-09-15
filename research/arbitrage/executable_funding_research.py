"""
Quantitative Crypto Platform (QCP) — Executable Reality Funding Arbitrage Research.

Evaluates institutional Spot vs Perpetual cash-and-carry basis arbitrage under
executable market reality and DEPLOYABLE CAPITAL constraints:
- Total deployable capital denominator (accounts for spot purchase, perp margin collateral,
  and unencumbered liquidation buffer reserves)
- Real Binance historical funding rates (exact 8h timestamps, negative funding intervals)
- Realistic execution friction (taker fees, bid-ask spread crossing, adverse slippage)
- Margin borrow financing APR (6.0%)
- Liquidation headroom and margin stress forensics
- Research -> Qualification Pipeline classification (remains strictly R&D, not production)
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
import math
import numpy as np
import urllib.request
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class DeployableCapitalConfig:
    total_deployable_capital_usd: float = 10000.0
    spot_allocation_pct: float = 50.0       # 50% used to purchase spot asset
    perp_margin_pct: float = 25.0           # 25% posted as collateral for 2x perp short
    liquidation_buffer_pct: float = 25.0    # 25% held in unencumbered reserve against adverse mark moves
    perp_leverage: float = 2.0              # 2x leverage on perp leg
    maintenance_margin_pct: float = 0.5     # Binance tier 1 maintenance margin (0.5%)

    @property
    def spot_notional_usd(self) -> float:
        return self.total_deployable_capital_usd * (self.spot_allocation_pct / 100.0)

    @property
    def perp_notional_usd(self) -> float:
        # Market-neutral hedge: short perp notional exactly equals long spot notional
        return self.spot_notional_usd

    @property
    def capital_utilization_pct(self) -> float:
        return (self.spot_allocation_pct + self.perp_margin_pct)


@dataclass
class ExecutableCostConfig:
    spot_taker_fee_bps: float = 5.0
    perp_taker_fee_bps: float = 5.0
    spot_slippage_bps: float = 3.0
    perp_slippage_bps: float = 3.0
    borrow_apr_pct: float = 6.0             # Annual financing cost on perp margin collateral
    min_entry_funding_annualized_pct: float = 8.0  # Minimum annual funding to initiate position
    rebalance_threshold_pct: float = 15.0   # Trigger rebalance if spot moves > 15%

    @property
    def total_entry_friction_bps(self) -> float:
        return (self.spot_taker_fee_bps + self.perp_taker_fee_bps + 
                self.spot_slippage_bps + self.perp_slippage_bps)

    @property
    def total_roundtrip_friction_bps(self) -> float:
        return self.total_entry_friction_bps * 2.0


@dataclass
class FundingPaymentRecord:
    timestamp: int
    funding_rate_8h: float
    mark_price: float
    is_positive: bool
    annualized_rate_pct: float


@dataclass
class ExecutableArbitrageAuditReport:
    symbol: str
    sample_period_days: float
    total_funding_intervals: int
    positive_funding_intervals: int
    negative_funding_intervals: int
    negative_funding_ratio_pct: float
    avg_funding_rate_8h_bps: float
    annualized_raw_funding_rate_pct: float
    
    # Capital and Economic Results
    total_deployable_capital_usd: float
    spot_notional_usd: float
    perp_margin_usd: float
    liquidation_buffer_usd: float
    
    # P&L Breakdown
    gross_funding_earned_usd: float
    margin_borrow_cost_usd: float
    roundtrip_friction_usd: float
    net_profit_usd: float
    
    # Yield Forensics (The Critical Comparison)
    theoretical_position_net_apy_pct: float   # Yield calculated on notional only
    deployable_capital_net_apy_pct: float     # REALISTIC yield on total deployable capital
    capital_haircut_drag_pct: float           # APY lost due to margin + buffer capital allocation
    
    # Liquidation and Stress Forensics
    max_underlying_price_spike_pct: float
    margin_stress_liquidation_cushion_pct: float
    liquidation_risk_verdict: str
    
    # Qualification Status
    research_qualification_verdict: str
    qualification_notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "sample_period_days": round(self.sample_period_days, 1),
            "total_funding_intervals": self.total_funding_intervals,
            "positive_funding_intervals": self.positive_funding_intervals,
            "negative_funding_intervals": self.negative_funding_intervals,
            "negative_funding_ratio_pct": round(self.negative_funding_ratio_pct, 2),
            "avg_funding_rate_8h_bps": round(self.avg_funding_rate_8h_bps, 3),
            "annualized_raw_funding_rate_pct": round(self.annualized_raw_funding_rate_pct, 2),
            "capital_architecture": {
                "total_deployable_capital_usd": self.total_deployable_capital_usd,
                "spot_notional_usd": self.spot_notional_usd,
                "perp_margin_usd": self.perp_margin_usd,
                "liquidation_buffer_usd": self.liquidation_buffer_usd,
            },
            "pnl_forensics": {
                "gross_funding_earned_usd": round(self.gross_funding_earned_usd, 2),
                "margin_borrow_cost_usd": round(self.margin_borrow_cost_usd, 2),
                "roundtrip_friction_usd": round(self.roundtrip_friction_usd, 2),
                "net_profit_usd": round(self.net_profit_usd, 2),
            },
            "yield_forensics": {
                "theoretical_position_net_apy_pct": round(self.theoretical_position_net_apy_pct, 2),
                "deployable_capital_net_apy_pct": round(self.deployable_capital_net_apy_pct, 2),
                "capital_haircut_drag_pct": round(self.capital_haircut_drag_pct, 2),
            },
            "liquidation_forensics": {
                "max_underlying_price_spike_pct": round(self.max_underlying_price_spike_pct, 2),
                "margin_stress_liquidation_cushion_pct": round(self.margin_stress_liquidation_cushion_pct, 2),
                "liquidation_risk_verdict": self.liquidation_risk_verdict,
            },
            "research_qualification_verdict": self.research_qualification_verdict,
            "qualification_notes": self.qualification_notes,
        }


class ExecutableFundingResearchEngine:
    """
    Evaluates cash-and-carry arbitrage on real deployable capital constraints.
    """

    def __init__(
        self,
        capital_config: Optional[DeployableCapitalConfig] = None,
        cost_config: Optional[ExecutableCostConfig] = None,
    ):
        self.capital_config = capital_config or DeployableCapitalConfig()
        self.cost_config = cost_config or ExecutableCostConfig()

    def fetch_binance_funding_history(
        self,
        symbol: str = "SOLUSDT",
        limit: int = 1000,
    ) -> List[FundingPaymentRecord]:
        """
        Fetches official historical 8-hour funding rates from Binance public futures REST API.
        No API keys required.
        """
        url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit={limit}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "QuantitativeCryptoPlatform/2.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            logger.error(f"Failed to fetch funding history for {symbol}: {exc}")
            return []

        records = []
        for item in data:
            rate = float(item["fundingRate"])
            mark = float(item.get("markPrice", 0.0))
            ts = int(item["fundingTime"])
            # Annualized rate = 8h rate * 3 * 365
            ann_rate = rate * 3.0 * 365.0 * 100.0
            records.append(
                FundingPaymentRecord(
                    timestamp=ts,
                    funding_rate_8h=rate,
                    mark_price=mark,
                    is_positive=(rate > 0),
                    annualized_rate_pct=ann_rate,
                )
            )
        return records

    def audit_executable_arbitrage(
        self,
        symbol: str,
        funding_records: List[FundingPaymentRecord],
    ) -> ExecutableArbitrageAuditReport:
        """
        Conducts rigorous audit of funding arbitrage economics on DEPLOYABLE capital.
        """
        if not funding_records:
            return ExecutableArbitrageAuditReport(
                symbol=symbol,
                sample_period_days=0.0,
                total_funding_intervals=0,
                positive_funding_intervals=0,
                negative_funding_intervals=0,
                negative_funding_ratio_pct=0.0,
                avg_funding_rate_8h_bps=0.0,
                annualized_raw_funding_rate_pct=0.0,
                total_deployable_capital_usd=self.capital_config.total_deployable_capital_usd,
                spot_notional_usd=self.capital_config.spot_notional_usd,
                perp_margin_usd=self.capital_config.total_deployable_capital_usd * (self.capital_config.perp_margin_pct / 100.0),
                liquidation_buffer_usd=self.capital_config.total_deployable_capital_usd * (self.capital_config.liquidation_buffer_pct / 100.0),
                gross_funding_earned_usd=0.0,
                margin_borrow_cost_usd=0.0,
                roundtrip_friction_usd=0.0,
                net_profit_usd=0.0,
                theoretical_position_net_apy_pct=0.0,
                deployable_capital_net_apy_pct=0.0,
                capital_haircut_drag_pct=0.0,
                max_underlying_price_spike_pct=0.0,
                margin_stress_liquidation_cushion_pct=0.0,
                liquidation_risk_verdict="NO_DATA",
                research_qualification_verdict="INSUFFICIENT_DATA",
                qualification_notes=["No funding intervals available."],
            )

        n_intervals = len(funding_records)
        sample_hours = n_intervals * 8.0
        sample_days = sample_hours / 24.0
        years = sample_days / 365.0 if sample_days > 0 else 1e-6

        positive_intervals = sum(1 for r in funding_records if r.funding_rate_8h > 0)
        negative_intervals = sum(1 for r in funding_records if r.funding_rate_8h < 0)
        neg_ratio = (negative_intervals / n_intervals) * 100.0

        rates = [r.funding_rate_8h for r in funding_records]
        avg_rate = float(np.mean(rates))
        avg_rate_bps = avg_rate * 10000.0
        ann_raw_funding_pct = avg_rate * 3.0 * 365.0 * 100.0

        # Capital allocations
        deployable_capital = self.capital_config.total_deployable_capital_usd
        spot_notional = self.capital_config.spot_notional_usd
        perp_margin = deployable_capital * (self.capital_config.perp_margin_pct / 100.0)
        buffer_reserve = deployable_capital * (self.capital_config.liquidation_buffer_pct / 100.0)

        # 1. Gross funding earned on hedged position
        # Gross funding = sum(rate * spot_notional)
        gross_funding_usd = sum(r * spot_notional for r in rates)

        # 2. Borrow financing cost on margin collateral (e.g. 6.0% APR on margin)
        borrow_cost_usd = perp_margin * (self.cost_config.borrow_apr_pct / 100.0) * years

        # 3. Execution Friction (Spot taker + Perp taker + Bid-ask crossing on entry and exit)
        roundtrip_friction_bps = self.cost_config.total_roundtrip_friction_bps
        roundtrip_friction_usd = spot_notional * (roundtrip_friction_bps / 10000.0)

        # 4. Net PnL
        net_profit_usd = gross_funding_usd - borrow_cost_usd - roundtrip_friction_usd

        # 5. Yield Forensics
        # Theoretical yield: profit relative to spot notional ($5k)
        theo_roi = (net_profit_usd / spot_notional) if spot_notional > 0 else 0.0
        theoretical_net_apy = (theo_roi / years) * 100.0

        # REALISTIC yield: profit relative to total DEPLOYABLE capital ($10k)
        real_roi = (net_profit_usd / deployable_capital) if deployable_capital > 0 else 0.0
        deployable_net_apy = (real_roi / years) * 100.0

        capital_haircut_drag = theoretical_net_apy - deployable_net_apy

        # 6. Liquidation & Margin Stress Forensics
        # Mark price trajectory analysis
        mark_prices = [r.mark_price for r in funding_records if r.mark_price > 0]
        max_spike_pct = 0.0
        if len(mark_prices) >= 2:
            min_p = min(mark_prices)
            max_p = max(mark_prices)
            max_spike_pct = ((max_p - min_p) / min_p) * 100.0

        # Perp position is short. Liquidation occurs when mark price rises such that margin balance <= maintenance margin.
        # At 2x leverage, initial margin is 50% of perp notional.
        # Liquidation price ~ entry_price * (1 + initial_margin_rate - maintenance_margin_rate)
        # = entry_price * (1 + 0.50 - 0.005) = entry_price * 1.495 (+49.5% cushion).
        # Plus unencumbered buffer allows absorption of an additional +50% move before capital depletion.
        total_collateral = perp_margin + buffer_reserve
        margin_cushion_pct = ((total_collateral / spot_notional) - (self.capital_config.maintenance_margin_pct / 100.0)) * 100.0

        if margin_cushion_pct > 60.0:
            liq_verdict = "SAFE_EXCESS_COLLATERALIZED"
        elif margin_cushion_pct > 30.0:
            liq_verdict = "MODERATE_REBALANCE_REQUIRED_ON_RALLIES"
        else:
            liq_verdict = "HIGH_LIQUIDATION_RISK"

        # 7. Research Qualification Verdict
        qualification_notes = []
        qualification_notes.append(f"Deployable Capital Haircut Drag: -{capital_haircut_drag:.2f}% APY lost to idle margin/buffer reserves.")
        qualification_notes.append(f"Negative Funding Drag: {neg_ratio:.1f}% of 8h intervals were negative (paying funding).")
        qualification_notes.append(f"Friction and Borrow Drag: ${roundtrip_friction_usd + borrow_cost_usd:.2f} total cost vs ${gross_funding_usd:.2f} gross revenue.")

        if deployable_net_apy <= 0.0:
            verdict = "RESEARCH_FAIL_NET_NEGATIVE"
            qualification_notes.append("Deployable capital net yield is negative after real friction and borrow financing.")
        elif deployable_net_apy < 5.0:
            verdict = "RESEARCH_MARGINAL_BELOW_TREASURY_RATE"
            qualification_notes.append("Deployable capital net yield is positive but below baseline risk-free cash return (~5.0%).")
        elif deployable_net_apy >= 5.0 and liq_verdict in ("SAFE_EXCESS_COLLATERALIZED", "MODERATE_REBALANCE_REQUIRED_ON_RALLIES"):
            verdict = "QUALIFIED_RESEARCH_CANDIDATE"
            qualification_notes.append("Meets R&D qualification hurdle. Remains strictly locked in Research -> Qualification pipeline.")
        else:
            verdict = "RESEARCH_HIGH_RISK"
            qualification_notes.append("High liquidation or volatility risk prevents advancement.")

        return ExecutableArbitrageAuditReport(
            symbol=symbol,
            sample_period_days=sample_days,
            total_funding_intervals=n_intervals,
            positive_funding_intervals=positive_intervals,
            negative_funding_intervals=negative_intervals,
            negative_funding_ratio_pct=neg_ratio,
            avg_funding_rate_8h_bps=avg_rate_bps,
            annualized_raw_funding_rate_pct=ann_raw_funding_pct,
            total_deployable_capital_usd=deployable_capital,
            spot_notional_usd=spot_notional,
            perp_margin_usd=perp_margin,
            liquidation_buffer_usd=buffer_reserve,
            gross_funding_earned_usd=gross_funding_usd,
            margin_borrow_cost_usd=borrow_cost_usd,
            roundtrip_friction_usd=roundtrip_friction_usd,
            net_profit_usd=net_profit_usd,
            theoretical_position_net_apy_pct=theoretical_net_apy,
            deployable_capital_net_apy_pct=deployable_net_apy,
            capital_haircut_drag_pct=capital_haircut_drag,
            max_underlying_price_spike_pct=max_spike_pct,
            margin_stress_liquidation_cushion_pct=margin_cushion_pct,
            liquidation_risk_verdict=liq_verdict,
            research_qualification_verdict=verdict,
            qualification_notes=qualification_notes,
        )
