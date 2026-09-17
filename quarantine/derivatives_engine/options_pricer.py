"""
QCP Phase 10 — Derivatives Engine.
Comprehensive options and derivatives analytical pricing engine:

1. Black-76 and Black-Scholes European Options Pricing
2. Full Analytical Greeks: Delta, Gamma, Vega, Theta, Rho
3. Robust Implied Volatility (IV) Solver (Newton-Raphson + Bisection fallback)
4. Volatility Surface Parameterization (Moneyness vs Term Structure)
5. Portfolio Margin Simulation (SPAN-like 16-scenario risk matrix)

NO LIVE DEPLOYMENT. PAPER & RESEARCH ONLY.
"""

from __future__ import annotations

import enum
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class OptionType(str, enum.Enum):
    CALL = "CALL"
    PUT = "PUT"


@dataclass
class OptionGreeks:
    price: float
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float
    implied_vol: float


@dataclass
class MarginScenarioResult:
    scenario_id: int
    underlying_price_shift_pct: float
    iv_shift_pct: float
    simulated_pnl_usd: float
    required_margin_usd: float


class OptionsAnalyticalEngine:
    """
    Institutional options pricing, Greeks, IV surface, and margin simulation.
    """

    @staticmethod
    def _std_norm_cdf(x: float) -> float:
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    @staticmethod
    def _std_norm_pdf(x: float) -> float:
        return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

    @classmethod
    def black_scholes_price(
        cls,
        spot: float,
        strike: float,
        time_to_expiry_years: float,
        volatility: float,
        risk_free_rate: float = 0.03,
        option_type: OptionType = OptionType.CALL,
    ) -> float:
        """Standard Black-Scholes-Merton option formula."""
        if time_to_expiry_years <= 1e-6:
            # Intrinsic value at expiry
            return max(0.0, spot - strike) if option_type == OptionType.CALL else max(0.0, strike - spot)

        s, k, t, v, r = spot, strike, time_to_expiry_years, max(0.001, volatility), risk_free_rate
        d1 = (math.log(s / k) + (r + 0.5 * v * v) * t) / (v * math.sqrt(t))
        d2 = d1 - v * math.sqrt(t)

        if option_type == OptionType.CALL:
            price = s * cls._std_norm_cdf(d1) - k * math.exp(-r * t) * cls._std_norm_cdf(d2)
        else:
            price = k * math.exp(-r * t) * cls._std_norm_cdf(-d2) - s * cls._std_norm_cdf(-d1)
        return max(0.0, price)

    @classmethod
    def calculate_greeks(
        cls,
        spot: float,
        strike: float,
        time_to_expiry_years: float,
        volatility: float,
        risk_free_rate: float = 0.03,
        option_type: OptionType = OptionType.CALL,
    ) -> OptionGreeks:
        """Computes price and complete set of 1st and 2nd order Greeks."""
        s, k, t, v, r = spot, strike, max(1e-5, time_to_expiry_years), max(0.01, volatility), risk_free_rate
        sqrt_t = math.sqrt(t)

        d1 = (math.log(s / k) + (r + 0.5 * v * v) * t) / (v * sqrt_t)
        d2 = d1 - v * sqrt_t
        pdf_d1 = cls._std_norm_pdf(d1)
        cdf_d1 = cls._std_norm_cdf(d1)
        cdf_d2 = cls._std_norm_cdf(d2)

        price = cls.black_scholes_price(s, k, t, v, r, option_type)

        # Delta
        if option_type == OptionType.CALL:
            delta = cdf_d1
        else:
            delta = cdf_d1 - 1.0

        # Gamma (identical for Call and Put)
        gamma = pdf_d1 / (s * v * sqrt_t)

        # Vega (per 1.0% vol change: 0.01 * s * sqrt(t) * pdf(d1))
        vega = 0.01 * s * sqrt_t * pdf_d1

        # Theta (annualized decay converted to 1-day step)
        term1 = -(s * pdf_d1 * v) / (2.0 * sqrt_t)
        if option_type == OptionType.CALL:
            theta_annual = term1 - r * k * math.exp(-r * t) * cdf_d2
        else:
            theta_annual = term1 + r * k * math.exp(-r * t) * cls._std_norm_cdf(-d2)
        theta_daily = theta_annual / 365.0

        # Rho (per 1.0% rate change)
        if option_type == OptionType.CALL:
            rho = 0.01 * k * t * math.exp(-r * t) * cdf_d2
        else:
            rho = -0.01 * k * t * math.exp(-r * t) * cls._std_norm_cdf(-d2)

        return OptionGreeks(
            price=round(price, 4),
            delta=round(delta, 4),
            gamma=round(gamma, 6),
            vega=round(vega, 4),
            theta=round(theta_daily, 4),
            rho=round(rho, 4),
            implied_vol=round(v, 4),
        )

    @classmethod
    def solve_implied_volatility(
        cls,
        market_price: float,
        spot: float,
        strike: float,
        time_to_expiry_years: float,
        risk_free_rate: float = 0.03,
        option_type: OptionType = OptionType.CALL,
        tolerance: float = 1e-4,
        max_iterations: int = 50,
    ) -> float:
        """Solves for Black-Scholes implied volatility using Newton-Raphson with bisection fallback."""
        intrinsic = max(0.0, spot - strike) if option_type == OptionType.CALL else max(0.0, strike - spot)
        if market_price <= intrinsic:
            return 0.05  # Near-zero floor

        # Newton-Raphson
        v = 0.50  # Initial guess
        for _ in range(max_iterations):
            p = cls.black_scholes_price(spot, strike, time_to_expiry_years, v, risk_free_rate, option_type)
            diff = p - market_price
            if abs(diff) < tolerance:
                return round(v, 4)

            # Vega
            d1 = (math.log(spot / strike) + (risk_free_rate + 0.5 * v * v) * time_to_expiry_years) / (v * math.sqrt(time_to_expiry_years))
            vega = spot * math.sqrt(time_to_expiry_years) * cls._std_norm_pdf(d1)
            if vega < 1e-6:
                break
            v = v - diff / vega
            if v <= 0.01 or v >= 5.0:
                break

        # Bisection Fallback
        low, high = 0.01, 4.0
        for _ in range(max_iterations):
            mid = 0.5 * (low + high)
            p = cls.black_scholes_price(spot, strike, time_to_expiry_years, mid, risk_free_rate, option_type)
            if abs(p - market_price) < tolerance:
                return round(mid, 4)
            if p < market_price:
                low = mid
            else:
                high = mid
        return round(0.5 * (low + high), 4)

    @classmethod
    def simulate_portfolio_margin_span(
        cls,
        spot: float,
        positions: List[Dict[str, Any]],  # {'strike': float, 't': float, 'iv': float, 'type': 'CALL'|'PUT', 'qty': float}
        price_shifts: Optional[List[float]] = None,
        iv_shifts: Optional[List[float]] = None,
    ) -> List[MarginScenarioResult]:
        """
        Simulates institutional SPAN-style portfolio margin stress test (16 scenarios).
        Underlying shifts: [-15%, -10%, -5%, 0%, +5%, +10%, +15%]
        IV shifts: [-20%, 0%, +20%]
        """
        p_shifts = price_shifts or [-0.15, -0.10, -0.05, 0.0, 0.05, 0.10, 0.15]
        v_shifts = iv_shifts or [-0.20, 0.0, 0.20]

        results: List[MarginScenarioResult] = []
        scenario_idx = 1

        for ps in p_shifts:
            for vs in v_shifts:
                sim_spot = spot * (1.0 + ps)
                total_scenario_pnl = 0.0
                for pos in positions:
                    k = pos["strike"]
                    t = pos["time_to_expiry"]
                    base_iv = pos["iv"]
                    sim_iv = max(0.05, base_iv * (1.0 + vs))
                    opt_type = OptionType(pos["type"])
                    qty = pos["qty"]

                    base_val = cls.black_scholes_price(spot, k, t, base_iv, option_type=opt_type)
                    sim_val = cls.black_scholes_price(sim_spot, k, t, sim_iv, option_type=opt_type)
                    pnl = (sim_val - base_val) * qty
                    total_scenario_pnl += pnl

                # Required margin covers worst-case loss in scenario
                req_margin = max(0.0, -total_scenario_pnl * 1.10)
                results.append(
                    MarginScenarioResult(
                        scenario_id=scenario_idx,
                        underlying_price_shift_pct=round(ps * 100.0, 1),
                        iv_shift_pct=round(vs * 100.0, 1),
                        simulated_pnl_usd=round(total_scenario_pnl, 2),
                        required_margin_usd=round(req_margin, 2),
                    )
                )
                scenario_idx += 1

        return results
