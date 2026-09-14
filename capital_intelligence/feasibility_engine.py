"""
Quantitative Systems Platform (QSP) — Capital Feasibility & Survivability Engine.

Empirically evaluates the execution viability, risk distortion, fee drag, leverage,
and probability of ruin across an account capital ladder ($10 to $100,000) under
real exchange microstructure constraints (Binance Spot & USD-M Futures).
"""

import math
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
from enum import Enum


class FeasibilityVerdict(str, Enum):
    EXECUTABLE = "EXECUTABLE"
    EXECUTION_DISTORTED = "EXECUTION_DISTORTED"
    HIGH_RISK_DISTORTED = "HIGH_RISK_DISTORTED"
    NOT_FEASIBLE = "NOT_FEASIBLE"
    FATAL_LIQUIDATION_RISK = "FATAL_LIQUIDATION_RISK"


@dataclass
class InstrumentConstraints:
    symbol: str
    venue: str  # 'SPOT' or 'USDM_FUTURES'
    min_notional: float  # e.g. 5.00 USD
    min_qty: float  # minimum lot step
    qty_step: float  # lot step size
    price_tick: float  # price tick size
    maker_fee_pct: float  # e.g. 0.02%
    taker_fee_pct: float  # e.g. 0.05%
    max_safe_leverage: float  # e.g. 10.0x


BINANCE_CONSTRAINTS: Dict[str, Dict[str, InstrumentConstraints]] = {
    "BTCUSDT": {
        "SPOT": InstrumentConstraints(
            symbol="BTCUSDT",
            venue="SPOT",
            min_notional=5.00,
            min_qty=0.00001,
            qty_step=0.00001,
            price_tick=0.01,
            maker_fee_pct=0.0010,  # 0.10%
            taker_fee_pct=0.0010,
            max_safe_leverage=1.0,
        ),
        "USDM_FUTURES": InstrumentConstraints(
            symbol="BTCUSDT",
            venue="USDM_FUTURES",
            min_notional=5.00,
            min_qty=0.001,
            qty_step=0.001,
            price_tick=0.10,
            maker_fee_pct=0.0002,  # 0.02%
            taker_fee_pct=0.0005,  # 0.05%
            max_safe_leverage=10.0,
        ),
    },
    "ETHUSDT": {
        "SPOT": InstrumentConstraints(
            symbol="ETHUSDT",
            venue="SPOT",
            min_notional=5.00,
            min_qty=0.0001,
            qty_step=0.0001,
            price_tick=0.01,
            maker_fee_pct=0.0010,
            taker_fee_pct=0.0010,
            max_safe_leverage=1.0,
        ),
        "USDM_FUTURES": InstrumentConstraints(
            symbol="ETHUSDT",
            venue="USDM_FUTURES",
            min_notional=5.00,
            min_qty=0.001,
            qty_step=0.001,
            price_tick=0.01,
            maker_fee_pct=0.0002,
            taker_fee_pct=0.0005,
            max_safe_leverage=10.0,
        ),
    },
    "SOLUSDT": {
        "SPOT": InstrumentConstraints(
            symbol="SOLUSDT",
            venue="SPOT",
            min_notional=5.00,
            min_qty=0.001,
            qty_step=0.001,
            price_tick=0.01,
            maker_fee_pct=0.0010,
            taker_fee_pct=0.0010,
            max_safe_leverage=1.0,
        ),
        "USDM_FUTURES": InstrumentConstraints(
            symbol="SOLUSDT",
            venue="USDM_FUTURES",
            min_notional=5.00,
            min_qty=0.01,
            qty_step=0.01,
            price_tick=0.01,
            maker_fee_pct=0.0002,
            taker_fee_pct=0.0005,
            max_safe_leverage=10.0,
        ),
    },
}


@dataclass
class FeasibilityEvaluation:
    account_capital: float
    target_risk_pct: float
    target_risk_usd: float
    entry_price: float
    stop_distance_usd: float
    stop_distance_pct: float
    theoretical_qty: float
    executable_qty: float
    executable_notional: float
    actual_risk_usd: float
    actual_risk_pct: float
    risk_distortion_ratio: float
    required_leverage: float
    round_trip_fee_usd: float
    fee_drag_pct_of_risk: float
    liquidation_distance_pct: float
    liquidation_safe: bool
    ruin_probability_50pct_dd: float
    verdict: FeasibilityVerdict
    notes: str


class CapitalFeasibilityEngine:
    """
    Evaluates execution feasibility of any trade or strategy across account capital sizes.
    """

    CAPITAL_LADDER = [10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 10000.0, 100000.0]

    @staticmethod
    def calculate_gamblers_ruin_prob(win_rate: float, payoff_ratio: float, risk_pct_per_trade: float) -> float:
        """
        Calculates theoretical probability of hitting a 50% drawdown within 200 trades.
        Uses classical Gambler's Ruin approximation with drift and volatility.
        """
        if risk_pct_per_trade <= 0:
            return 0.0
        # Expected return per trade in %
        mu = win_rate * payoff_ratio * risk_pct_per_trade - (1.0 - win_rate) * risk_pct_per_trade
        # Variance of trade outcome in %^2
        var = (win_rate * ((payoff_ratio * risk_pct_per_trade) ** 2) +
               (1.0 - win_rate) * (risk_pct_per_trade ** 2)) - (mu ** 2)
        if var <= 0:
            return 0.0
        sigma = math.sqrt(var)

        # 50% drawdown corresponds to a loss barrier of ~50%
        # Ruin probability = exp(-2 * mu * barrier / sigma^2) if mu > 0, else 1.0
        barrier = 50.0
        if mu <= 0:
            return 1.0
        val = -2.0 * mu * barrier / (sigma ** 2)
        try:
            prob = math.exp(val)
        except OverflowError:
            prob = 1.0
        return min(max(prob, 0.0), 1.0)

    @classmethod
    def evaluate_feasibility(
        cls,
        account_capital: float,
        symbol: str,
        entry_price: float,
        stop_distance_usd: float,
        venue: str = "USDM_FUTURES",
        target_risk_pct: float = 0.006,  # 0.60%
        win_rate: float = 0.40,
        payoff_ratio: float = 2.0,
    ) -> FeasibilityEvaluation:
        """
        Evaluates feasibility for a specific account capital and trade geometry.
        """
        constraints = BINANCE_CONSTRAINTS.get(symbol, {}).get(venue)
        if not constraints:
            # Fallback conservative constraints
            constraints = InstrumentConstraints(
                symbol=symbol,
                venue=venue,
                min_notional=5.0,
                min_qty=0.001,
                qty_step=0.001,
                price_tick=0.01,
                maker_fee_pct=0.0002,
                taker_fee_pct=0.0005,
                max_safe_leverage=10.0,
            )

        target_risk_usd = account_capital * target_risk_pct
        stop_distance_pct = (stop_distance_usd / entry_price) * 100.0

        if stop_distance_usd <= 0:
            return FeasibilityEvaluation(
                account_capital=account_capital,
                target_risk_pct=target_risk_pct * 100.0,
                target_risk_usd=target_risk_usd,
                entry_price=entry_price,
                stop_distance_usd=0.0,
                stop_distance_pct=0.0,
                theoretical_qty=0.0,
                executable_qty=0.0,
                executable_notional=0.0,
                actual_risk_usd=0.0,
                actual_risk_pct=0.0,
                risk_distortion_ratio=0.0,
                required_leverage=0.0,
                round_trip_fee_usd=0.0,
                fee_drag_pct_of_risk=0.0,
                liquidation_distance_pct=0.0,
                liquidation_safe=False,
                ruin_probability_50pct_dd=1.0,
                verdict=FeasibilityVerdict.NOT_FEASIBLE,
                notes="Zero stop distance",
            )

        # 1. Theoretical sizing
        theoretical_qty = target_risk_usd / stop_distance_usd

        # 2. Enforce minimum notional
        min_notional_qty = constraints.min_notional / entry_price

        # Minimum required to satisfy both lot step and min notional
        raw_qty = max(theoretical_qty, min_notional_qty)

        # Round to step size
        steps = math.ceil(raw_qty / constraints.qty_step)
        executable_qty = steps * constraints.qty_step
        executable_notional = executable_qty * entry_price

        # 3. Calculate actual realized risk
        actual_risk_usd = executable_qty * stop_distance_usd
        actual_risk_pct = (actual_risk_usd / account_capital) * 100.0
        risk_distortion_ratio = actual_risk_usd / target_risk_usd if target_risk_usd > 0 else 1.0

        # 4. Required leverage
        required_leverage = executable_notional / account_capital

        # 5. Fee drag (taker entry + taker exit)
        round_trip_fee_usd = executable_notional * (constraints.taker_fee_pct * 2.0)
        fee_drag_pct_of_risk = (round_trip_fee_usd / actual_risk_usd) * 100.0 if actual_risk_usd > 0 else 0.0

        # 6. Liquidation distance
        # On isolated margin, approx liquidation distance % = (1 / leverage) * (1 - maintenance_margin)
        maintenance_margin_pct = 0.005  # 0.5% for tier 1
        liquidation_distance_pct = (1.0 / required_leverage - maintenance_margin_pct) * 100.0 if required_leverage > 0 else 999.0
        liquidation_safe = liquidation_distance_pct > (stop_distance_pct * 1.15)  # 15% buffer beyond stop

        # 7. Gambler's ruin probability
        ruin_prob = cls.calculate_gamblers_ruin_prob(win_rate, payoff_ratio, actual_risk_pct)

        # 8. Determine verdict
        notes = []
        if required_leverage > constraints.max_safe_leverage:
            verdict = FeasibilityVerdict.NOT_FEASIBLE
            notes.append(f"Required leverage {required_leverage:.1f}x exceeds safe ceiling {constraints.max_safe_leverage:.1f}x")
        elif not liquidation_safe:
            verdict = FeasibilityVerdict.FATAL_LIQUIDATION_RISK
            notes.append(f"Liquidation distance ({liquidation_distance_pct:.2f}%) inside stop distance ({stop_distance_pct:.2f}%)")
        elif risk_distortion_ratio > 5.0:
            verdict = FeasibilityVerdict.HIGH_RISK_DISTORTED
            notes.append(f"Severe risk distortion: target {target_risk_pct*100:.2f}%, actual {actual_risk_pct:.2f}% ({risk_distortion_ratio:.1f}x)")
        elif risk_distortion_ratio > 1.5:
            verdict = FeasibilityVerdict.EXECUTION_DISTORTED
            notes.append(f"Moderate risk distortion: target {target_risk_pct*100:.2f}%, actual {actual_risk_pct:.2f}% ({risk_distortion_ratio:.1f}x)")
        else:
            verdict = FeasibilityVerdict.EXECUTABLE
            notes.append(f"Clean execution: actual risk {actual_risk_pct:.2f}% conforms to target {target_risk_pct*100:.2f}%")

        return FeasibilityEvaluation(
            account_capital=account_capital,
            target_risk_pct=target_risk_pct * 100.0,
            target_risk_usd=round(target_risk_usd, 4),
            entry_price=entry_price,
            stop_distance_usd=round(stop_distance_usd, 2),
            stop_distance_pct=round(stop_distance_pct, 2),
            theoretical_qty=round(theoretical_qty, 6),
            executable_qty=round(executable_qty, 6),
            executable_notional=round(executable_notional, 2),
            actual_risk_usd=round(actual_risk_usd, 4),
            actual_risk_pct=round(actual_risk_pct, 2),
            risk_distortion_ratio=round(risk_distortion_ratio, 2),
            required_leverage=round(required_leverage, 2),
            round_trip_fee_usd=round(round_trip_fee_usd, 4),
            fee_drag_pct_of_risk=round(fee_drag_pct_of_risk, 2),
            liquidation_distance_pct=round(liquidation_distance_pct, 2),
            liquidation_safe=liquidation_safe,
            ruin_probability_50pct_dd=round(ruin_prob, 4),
            verdict=verdict,
            notes="; ".join(notes),
        )

    @classmethod
    def evaluate_strategy_across_ladder(
        cls,
        strategy_id: str,
        symbol: str,
        entry_price: float,
        stop_distance_usd: float,
        venue: str = "USDM_FUTURES",
        target_risk_pct: float = 0.006,
        win_rate: float = 0.40,
        payoff_ratio: float = 2.0,
    ) -> List[FeasibilityEvaluation]:
        """Runs the feasibility evaluation across all tiers in the CAPITAL_LADDER."""
        evals = []
        for cap in cls.CAPITAL_LADDER:
            ev = cls.evaluate_feasibility(
                account_capital=cap,
                symbol=symbol,
                entry_price=entry_price,
                stop_distance_usd=stop_distance_usd,
                venue=venue,
                target_risk_pct=target_risk_pct,
                win_rate=win_rate,
                payoff_ratio=payoff_ratio,
            )
            evals.append(ev)
        return evals
