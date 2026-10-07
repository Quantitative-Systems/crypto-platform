"""
Quantitative Crypto Platform (QCP) — Dynamic Funding & Basis Carry Engine.

Economic Mechanism:
Captures structural retail long leverage demand in crypto perpetual futures. During speculative
expansion regimes, perpetual contract funding rates spike significantly above the cost of margin borrow.
Unlike passive cash-and-carry (which bleeds interest during bear/chop regimes), this active engine
deploys capital dynamically:
- Enters when annualized funding rate >= 15.0% (positive carry threshold exceeding borrow cost + amortized friction)
- Exits when funding rate compresses <= 5.0% APR or turns negative
- Trades spot-vs-perp basis on Total Deployable Capital ($10k base: 50% spot long, 25% perp 2x short, 25% buffer)
- Accounts for 32 bps round-trip friction and 6% APR hourly borrow financing during active intervals
"""

import os
import json
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DynamicFundingCarry")


@dataclass
class DynamicCarryConfig:
    entry_annual_funding_pct: float = 15.0  # Enter when funding >= 15% APR (approx +1.37 bps per 8h)
    exit_annual_funding_pct: float = 5.0    # Exit when funding <= 5% APR (below 6% borrow rate)
    borrow_apr_pct: float = 6.0             # 6.0% APR margin borrow
    roundtrip_friction_bps: float = 32.0    # 32 bps total pair roundtrip friction
    min_holding_intervals: int = 3          # Minimum 24 hours (3 x 8h) to amortize friction
    total_deployable_capital_usd: float = 10_000.0


@dataclass
class CarryTradeRecord:
    trade_id: str
    symbol: str
    entry_timestamp: int
    entry_funding_rate_bps: float
    exit_timestamp: int
    exit_funding_rate_bps: float
    intervals_held: int
    gross_funding_earned_usd: float
    borrow_cost_usd: float
    friction_usd: float
    net_pnl_usd: float
    net_return_on_capital_pct: float
    annualized_net_apy_pct: float


@dataclass
class DynamicCarryAuditReport:
    symbol: str
    sample_period_days: float
    total_funding_intervals: int
    active_intervals_count: int
    active_utilization_pct: float
    trades_count: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    total_gross_funding_usd: float
    total_borrow_cost_usd: float
    total_friction_usd: float
    total_net_pnl_usd: float
    deployable_capital_net_return_pct: float
    deployable_capital_annualized_net_apy_pct: float
    profit_factor: float
    max_drawdown_pct: float
    qualification_verdict: str
    qualification_notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        for k in ["sample_period_days", "active_utilization_pct", "win_rate_pct",
                  "total_gross_funding_usd", "total_borrow_cost_usd", "total_friction_usd",
                  "total_net_pnl_usd", "deployable_capital_net_return_pct",
                  "deployable_capital_annualized_net_apy_pct", "profit_factor", "max_drawdown_pct"]:
            if k in d and isinstance(d[k], (float, np.floating)):
                d[k] = round(d[k], 2)
        return d


class DynamicFundingCarryEngine:
    """
    Simulates dynamic regime-filtered spot-perp carry on verified Binance 8h funding records.
    """

    def __init__(self, config: Optional[DynamicCarryConfig] = None):
        self.config = config or DynamicCarryConfig()

    def evaluate_dynamic_carry(
        self,
        symbol: str,
        funding_records: List[Dict[str, Any]],
    ) -> DynamicCarryAuditReport:
        if not funding_records:
            raise ValueError("No funding records provided for carry audit.")

        # Normalize records to list of (timestamp, funding_rate)
        records: List[Tuple[int, float]] = []
        for r in funding_records:
            if hasattr(r, "timestamp"):
                ts = int(r.timestamp)
                rate = float(r.funding_rate_8h)
            elif isinstance(r, dict):
                ts = int(r.get("fundingTime", r.get("timestamp", 0)))
                rate = float(r.get("fundingRate", r.get("funding_rate_8h", 0.0)))
            else:
                continue
            records.append((ts, rate))

        records.sort(key=lambda x: x[0])

        entry_rate_threshold = (self.config.entry_annual_funding_pct / 100.0) / (365.0 * 3.0)
        exit_rate_threshold = (self.config.exit_annual_funding_pct / 100.0) / (365.0 * 3.0)
        borrow_rate_8h = (self.config.borrow_apr_pct / 100.0) / (365.0 * 3.0)

        # Capital allocations
        cap = self.config.total_deployable_capital_usd
        spot_notional = cap * 0.50          # $5,000 spot long
        perp_margin = cap * 0.25            # $2,500 perp margin for 2x short ($5,000 notional short)
        perp_notional = spot_notional       # Perfect delta-neutral balance ($5,000 short)

        # Friction cost per round-trip trade
        friction_rate = self.config.roundtrip_friction_bps / 10000.0
        trade_friction_usd = (spot_notional + perp_notional) * (friction_rate / 2.0)  # 32 bps roundtrip on $5k = $16.00

        trades: List[CarryTradeRecord] = []
        in_pos = False
        entry_idx = 0
        entry_rate = 0.0
        active_intervals = 0

        accum_funding = 0.0
        accum_borrow = 0.0

        pnl_curve = [cap]

        for i, (ts, rate) in enumerate(records):

            if not in_pos:
                # Check dynamic entry condition: funding rate exceeds entry threshold
                if rate >= entry_rate_threshold:
                    in_pos = True
                    entry_idx = i
                    entry_rate = rate
                    accum_funding = 0.0
                    accum_borrow = 0.0
            else:
                active_intervals += 1
                # Earn funding on perp short position: positive funding rate pays short!
                # Payment = perp_notional * funding_rate
                funding_payment = perp_notional * rate
                accum_funding += funding_payment

                # Borrow cost on margin collateral
                borrow_payment = perp_margin * borrow_rate_8h
                accum_borrow += borrow_payment

                intervals_held = i - entry_idx

                # Check exit condition
                should_exit = (
                    (rate <= exit_rate_threshold and intervals_held >= self.config.min_holding_intervals)
                    or (rate < 0.0)  # Inverted funding: immediate exit
                    or (i == len(records) - 1)  # End of sample
                )

                if should_exit:
                    net_trade_pnl = accum_funding - accum_borrow - trade_friction_usd
                    ret_pct = (net_trade_pnl / cap) * 100.0
                    days_held = (intervals_held * 8.0) / 24.0
                    apy = (ret_pct / max(0.01, days_held)) * 365.0

                    trades.append(
                        CarryTradeRecord(
                            trade_id=f"{symbol}_CARRY_{len(trades)+1}",
                            symbol=symbol,
                            entry_timestamp=int(records[entry_idx][0]),
                            entry_funding_rate_bps=round(entry_rate * 10000.0, 3),
                            exit_timestamp=ts,
                            exit_funding_rate_bps=round(rate * 10000.0, 3),
                            intervals_held=intervals_held,
                            gross_funding_earned_usd=round(accum_funding, 2),
                            borrow_cost_usd=round(accum_borrow, 2),
                            friction_usd=round(trade_friction_usd, 2),
                            net_pnl_usd=round(net_trade_pnl, 2),
                            net_return_on_capital_pct=round(ret_pct, 4),
                            annualized_net_apy_pct=round(apy, 2),
                        )
                    )
                    pnl_curve.append(pnl_curve[-1] + net_trade_pnl)
                    in_pos = False

        total_intervals = len(records)
        sample_days = (total_intervals * 8.0) / 24.0
        active_utilization = (active_intervals / max(1, total_intervals)) * 100.0

        total_gross_funding = sum(t.gross_funding_earned_usd for t in trades)
        total_borrow_cost = sum(t.borrow_cost_usd for t in trades)
        total_friction = sum(t.friction_usd for t in trades)
        total_net_pnl = sum(t.net_pnl_usd for t in trades)

        wins = [t for t in trades if t.net_pnl_usd > 0]
        losses = [t for t in trades if t.net_pnl_usd <= 0]
        win_rate = (len(wins) / len(trades) * 100.0) if trades else 0.0

        gross_win_usd = sum(t.net_pnl_usd for t in wins)
        gross_loss_usd = abs(sum(t.net_pnl_usd for t in losses))
        pf = gross_win_usd / gross_loss_usd if gross_loss_usd > 1e-6 else 99.0

        # Drawdown computation
        curve = np.array(pnl_curve)
        peaks = np.maximum.accumulate(curve)
        dds = (peaks - curve) / peaks * 100.0
        max_dd = float(np.max(dds)) if len(dds) > 0 else 0.0

        net_ret_pct = (total_net_pnl / cap) * 100.0
        annual_apy = (net_ret_pct / max(1.0, sample_days)) * 365.0

        # Qualification decision
        notes = []
        notes.append(f"Active Capital Utilization: {active_utilization:.1f}% (idle in low-yield/inverted periods)")
        notes.append(f"Gross Funding Earned: ${total_gross_funding:,.2f} vs Financing Cost: ${total_borrow_cost:,.2f}")
        notes.append(f"Friction Drag: ${total_friction:,.2f} across {len(trades)} active roundtrips")

        if annual_apy >= 5.0 and max_dd <= 4.0 and win_rate >= 60.0:
            verdict = "QUALIFIED_ROBUST"
            notes.append(f"Passed: Positive net deployable APY ({annual_apy:.2f}%) with low max drawdown ({max_dd:.2f}%)")
        elif annual_apy > 0.0:
            verdict = "FRAGILE"
            notes.append(f"Fragile: Marginally positive net yield ({annual_apy:.2f}%) insufficient to clear risk-free hurdle")
        else:
            verdict = "FALSIFIED"
            notes.append(f"Falsified: Net return is negative ({annual_apy:.2f}% APY) after friction and borrow financing")

        return DynamicCarryAuditReport(
            symbol=symbol,
            sample_period_days=round(sample_days, 1),
            total_funding_intervals=total_intervals,
            active_intervals_count=active_intervals,
            active_utilization_pct=round(active_utilization, 2),
            trades_count=len(trades),
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate_pct=round(win_rate, 2),
            total_gross_funding_usd=round(total_gross_funding, 2),
            total_borrow_cost_usd=round(total_borrow_cost, 2),
            total_friction_usd=round(total_friction, 2),
            total_net_pnl_usd=round(total_net_pnl, 2),
            deployable_capital_net_return_pct=round(net_ret_pct, 2),
            deployable_capital_annualized_net_apy_pct=round(annual_apy, 2),
            profit_factor=round(pf, 2),
            max_drawdown_pct=round(max_dd, 2),
            qualification_verdict=verdict,
            qualification_notes=notes,
        )
