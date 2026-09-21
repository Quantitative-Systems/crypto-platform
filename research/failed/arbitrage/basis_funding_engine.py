"""
Quantitative Crypto Platform (QCP) — Market-Neutral Basis & Funding Arbitrage Engine.

Implements institutional Spot vs Perpetual cash-and-carry basis arbitrage and
funding rate harvesting under net executable economic constraints:
- Spot purchase (Long) paired with Perpetual contract Short
- Realistic taker fees (5 bps spot + 5 bps perp on entry and exit = 20 bps round trip)
- Realistic bid-ask crossing and adverse slippage (3 bps each leg = 12 bps round trip)
- Margin borrow interest rate (e.g. 6.0% APR financing cost)
- 8-hour continuous funding payments / receipts
- Basis convergence P&L (premium decay to spot)
- Net annualized yield (APY), Sharpe ratio, and drawdown forensics.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
import math
import numpy as np


@dataclass
class FundingIntervalRecord:
    timestamp: int
    spot_price: float
    perp_price: float
    funding_rate_8h: float  # e.g., 0.0001 = 0.01% (10 bps) per 8h


@dataclass
class ArbitrageCostModel:
    spot_taker_fee_bps: float = 5.0
    perp_taker_fee_bps: float = 5.0
    spot_slippage_bps: float = 3.0
    perp_slippage_bps: float = 3.0
    borrow_apr_pct: float = 6.0          # 6.0% annual financing rate on margin
    min_entry_annualized_yield_pct: float = 8.0
    exit_basis_threshold_pct: float = 0.02 # Unwind when premium compresses to 2 bps


@dataclass
class CashAndCarryTrade:
    trade_id: str
    symbol: str
    entry_timestamp: int
    exit_timestamp: int
    spot_entry_price: float
    perp_entry_price: float
    spot_exit_price: float
    perp_exit_price: float
    notional_usd: float
    holding_hours: float
    gross_funding_usd: float
    gross_basis_pnl_usd: float
    borrow_cost_usd: float
    total_friction_usd: float
    net_pnl_usd: float
    net_roi_pct: float
    annualized_net_apy_pct: float


@dataclass
class ArbitrageSimulationReport:
    symbol: str
    starting_capital_usd: float
    ending_equity_usd: float
    net_profit_usd: float
    total_return_pct: float
    annualized_net_apy_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    total_trades: int
    gross_funding_collected_usd: float
    total_borrow_costs_usd: float
    total_friction_usd: float
    friction_drag_pct: float
    trades: List[CashAndCarryTrade]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "starting_capital_usd": self.starting_capital_usd,
            "ending_equity_usd": round(self.ending_equity_usd, 2),
            "net_profit_usd": round(self.net_profit_usd, 2),
            "total_return_pct": round(self.total_return_pct, 2),
            "annualized_net_apy_pct": round(self.annualized_net_apy_pct, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "total_trades": self.total_trades,
            "gross_funding_collected_usd": round(self.gross_funding_collected_usd, 2),
            "total_borrow_costs_usd": round(self.total_borrow_costs_usd, 2),
            "total_friction_usd": round(self.total_friction_usd, 2),
            "friction_drag_pct": round(self.friction_drag_pct, 2),
            "trades_sample": [asdict(t) for t in self.trades[:10]],
        }


class BasisFundingArbitrageEngine:
    """
    Market-Neutral Arbitrage and Funding Harvest Simulation Engine.
    """

    def __init__(self, cost_model: Optional[ArbitrageCostModel] = None):
        self.costs = cost_model or ArbitrageCostModel()

    def calculate_entry_friction(self, notional_usd: float) -> float:
        """Total entry friction = spot taker fee + perp taker fee + spot slippage + perp slippage."""
        total_bps = (
            self.costs.spot_taker_fee_bps
            + self.costs.perp_taker_fee_bps
            + self.costs.spot_slippage_bps
            + self.costs.perp_slippage_bps
        )
        return notional_usd * (total_bps / 10000.0)

    def calculate_exit_friction(self, notional_usd: float) -> float:
        """Total exit friction across spot and perp legs."""
        total_bps = (
            self.costs.spot_taker_fee_bps
            + self.costs.perp_taker_fee_bps
            + self.costs.spot_slippage_bps
            + self.costs.perp_slippage_bps
        )
        return notional_usd * (total_bps / 10000.0)

    def simulate_cash_and_carry(
        self,
        symbol: str,
        series: List[FundingIntervalRecord],
        capital_usd: float = 10000.0,
    ) -> ArbitrageSimulationReport:
        """
        Simulates systematic cash-and-carry arbitrage across historical funding intervals.
        """
        if len(series) < 2:
            return ArbitrageSimulationReport(
                symbol=symbol,
                starting_capital_usd=capital_usd,
                ending_equity_usd=capital_usd,
                net_profit_usd=0.0,
                total_return_pct=0.0,
                annualized_net_apy_pct=0.0,
                sharpe_ratio=0.0,
                max_drawdown_pct=0.0,
                total_trades=0,
                gross_funding_collected_usd=0.0,
                total_borrow_costs_usd=0.0,
                total_friction_usd=0.0,
                friction_drag_pct=0.0,
                trades=[],
            )

        equity = capital_usd
        peak_equity = capital_usd
        max_dd_pct = 0.0

        in_trade = False
        trade_id_seq = 1
        trades: List[CashAndCarryTrade] = []

        total_funding_collected = 0.0
        total_borrow_costs = 0.0
        total_friction_paid = 0.0

        # State tracking for open position
        entry_idx = 0
        spot_entry = 0.0
        perp_entry = 0.0
        pos_notional = 0.0
        cum_funding = 0.0
        cum_borrow = 0.0

        daily_borrow_rate = (self.costs.borrow_apr_pct / 100.0) / 365.0
        eight_hour_borrow_rate = daily_borrow_rate * (8.0 / 24.0)

        interval_returns: List[float] = []

        for i, interval in enumerate(series):
            spot = interval.spot_price
            perp = interval.perp_price
            funding_8h = interval.funding_rate_8h
            basis_pct = ((perp - spot) / spot) * 100.0 if spot > 0 else 0.0
            annualized_funding_pct = funding_8h * 3.0 * 365.0 * 100.0
            combined_annualized_yield_pct = annualized_funding_pct + (basis_pct * (365.0 / 30.0))

            if not in_trade:
                # Check Entry Condition:
                # Positive basis and combined net yield > hurdle
                if (
                    basis_pct > 0.10
                    and combined_annualized_yield_pct >= self.costs.min_entry_annualized_yield_pct
                ):
                    in_trade = True
                    entry_idx = i
                    spot_entry = spot * (1.0 + self.costs.spot_slippage_bps / 10000.0)
                    perp_entry = perp * (1.0 - self.costs.perp_slippage_bps / 10000.0)
                    pos_notional = equity * 0.95  # 95% capital allocation

                    # Pay entry friction
                    entry_friction = self.calculate_entry_friction(pos_notional)
                    equity -= entry_friction
                    total_friction_paid += entry_friction
                    cum_funding = 0.0
                    cum_borrow = 0.0
            else:
                # In active position:
                # 1. Accrue 8h funding payment: Short Perp collects funding if funding_rate > 0
                funding_payment = pos_notional * funding_8h
                cum_funding += funding_payment
                total_funding_collected += funding_payment

                # 2. Accrue margin borrow interest
                borrow_payment = pos_notional * eight_hour_borrow_rate
                cum_borrow += borrow_payment
                total_borrow_costs += borrow_payment

                # Net change for this 8h interval
                interval_pnl = funding_payment - borrow_payment
                equity += interval_pnl

                # Track running drawdown
                if equity > peak_equity:
                    peak_equity = equity
                else:
                    dd = ((peak_equity - equity) / peak_equity) * 100.0
                    if dd > max_dd_pct:
                        max_dd_pct = dd

                # Check Exit Condition:
                # Basis compressed to target threshold or funding inverted negative for 3 intervals
                holding_intervals = i - entry_idx
                min_hold_passed = holding_intervals >= 3  # Hold at least 24 hours (3 x 8h)
                basis_compressed = basis_pct <= self.costs.exit_basis_threshold_pct
                funding_negative = funding_8h < -0.0002

                if min_hold_passed and (basis_compressed or funding_negative or i == len(series) - 1):
                    # Unwind position
                    spot_exit = spot * (1.0 - self.costs.spot_slippage_bps / 10000.0)
                    perp_exit = perp * (1.0 + self.costs.perp_slippage_bps / 10000.0)

                    # Basis convergence P&L:
                    # Long spot: (spot_exit - spot_entry) / spot_entry
                    # Short perp: (perp_entry - perp_exit) / perp_entry
                    spot_ret = (spot_exit - spot_entry) / spot_entry
                    perp_ret = (perp_entry - perp_exit) / perp_entry
                    basis_pnl = pos_notional * 0.5 * (spot_ret + perp_ret)

                    exit_friction = self.calculate_exit_friction(pos_notional)
                    total_friction_paid += exit_friction

                    trade_net_pnl = cum_funding + basis_pnl - cum_borrow - (entry_friction + exit_friction)
                    equity += basis_pnl - exit_friction

                    holding_hours = holding_intervals * 8.0
                    holding_days = holding_hours / 24.0
                    roi_pct = (trade_net_pnl / pos_notional) * 100.0
                    apy_pct = (roi_pct * (365.0 / holding_days)) if holding_days > 0 else 0.0

                    trade = CashAndCarryTrade(
                        trade_id=f"ARB_{symbol.replace('/', '')}_{trade_id_seq:04d}",
                        symbol=symbol,
                        entry_timestamp=series[entry_idx].timestamp,
                        exit_timestamp=interval.timestamp,
                        spot_entry_price=round(spot_entry, 4),
                        perp_entry_price=round(perp_entry, 4),
                        spot_exit_price=round(spot_exit, 4),
                        perp_exit_price=round(perp_exit, 4),
                        notional_usd=round(pos_notional, 2),
                        holding_hours=holding_hours,
                        gross_funding_usd=round(cum_funding, 2),
                        gross_basis_pnl_usd=round(basis_pnl, 2),
                        borrow_cost_usd=round(cum_borrow, 2),
                        total_friction_usd=round(entry_friction + exit_friction, 2),
                        net_pnl_usd=round(trade_net_pnl, 2),
                        net_roi_pct=round(roi_pct, 4),
                        annualized_net_apy_pct=round(apy_pct, 2),
                    )
                    trades.append(trade)
                    trade_id_seq += 1
                    in_trade = False

            # Daily return approximation
            if i > 0 and i % 3 == 0:
                ret = (equity - capital_usd) / capital_usd
                interval_returns.append(ret)

        total_net_pnl = equity - capital_usd
        total_ret_pct = (total_net_pnl / capital_usd) * 100.0
        total_days = (series[-1].timestamp - series[0].timestamp) / 86400.0 if len(series) > 1 else 1.0
        annualized_apy = (total_ret_pct * (365.0 / total_days)) if total_days > 0 else 0.0

        # Sharpe ratio of daily interval returns
        ret_diffs = np.diff([capital_usd] + [capital_usd * (1.0 + r) for r in interval_returns])
        mean_ret = float(np.mean(ret_diffs)) if len(ret_diffs) > 0 else 0.0
        std_ret = float(np.std(ret_diffs)) if len(ret_diffs) > 1 else 1e-6
        sharpe = (mean_ret / std_ret * math.sqrt(365)) if std_ret > 1e-6 else 0.0

        gross_profit = total_funding_collected + max(0.0, total_net_pnl)
        friction_drag = (total_friction_paid / gross_profit * 100.0) if gross_profit > 1e-6 else 0.0

        return ArbitrageSimulationReport(
            symbol=symbol,
            starting_capital_usd=capital_usd,
            ending_equity_usd=equity,
            net_profit_usd=total_net_pnl,
            total_return_pct=total_ret_pct,
            annualized_net_apy_pct=annualized_apy,
            sharpe_ratio=sharpe,
            max_drawdown_pct=max_dd_pct,
            total_trades=len(trades),
            gross_funding_collected_usd=total_funding_collected,
            total_borrow_costs_usd=total_borrow_costs,
            total_friction_usd=total_friction_paid,
            friction_drag_pct=friction_drag,
            trades=trades,
        )
