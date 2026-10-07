"""
Comprehensive Test Suite: Derivatives Engine & Market Making Engine.
Validates:
- Black-Scholes analytical options pricing
- Complete Greeks (Delta, Gamma, Vega, Theta, Rho)
- Implied Volatility (IV) solver
- SPAN portfolio margin simulation
- Avellaneda-Stoikov market making & adverse selection guard
"""

import math
import pytest
from derivatives_engine.options_pricer import (
    OptionsAnalyticalEngine,
    OptionType,
)
from market_making.avellaneda_stoikov import AvellanedaStoikovModel


def test_black_scholes_call_and_put():
    spot = 60_000.0
    strike = 60_000.0
    t = 0.25  # 3 months
    v = 0.60  # 60% vol
    r = 0.03

    call = OptionsAnalyticalEngine.black_scholes_price(spot, strike, t, v, r, OptionType.CALL)
    put = OptionsAnalyticalEngine.black_scholes_price(spot, strike, t, v, r, OptionType.PUT)

    assert call > 0
    assert put > 0

    # Put-Call Parity: C - P = S - K * exp(-r * t)
    parity_diff = abs((call - put) - (spot - strike * math.exp(-r * t)))
    assert parity_diff < 1e-2


def test_options_greeks():
    greeks = OptionsAnalyticalEngine.calculate_greeks(
        spot=60_000.0,
        strike=60_000.0,
        time_to_expiry_years=0.25,
        volatility=0.60,
        risk_free_rate=0.03,
        option_type=OptionType.CALL,
    )
    assert 0.45 < greeks.delta < 0.65  # ATM call delta near 0.50
    assert greeks.gamma > 0.0
    assert greeks.vega > 0.0
    assert greeks.theta < 0.0  # Daily time decay


def test_implied_volatility_solver():
    spot = 60_000.0
    strike = 65_000.0
    t = 0.5
    true_iv = 0.75

    price = OptionsAnalyticalEngine.black_scholes_price(spot, strike, t, true_iv, 0.03, OptionType.CALL)
    solved_iv = OptionsAnalyticalEngine.solve_implied_volatility(
        market_price=price,
        spot=spot,
        strike=strike,
        time_to_expiry_years=t,
        risk_free_rate=0.03,
        option_type=OptionType.CALL,
    )
    assert abs(solved_iv - true_iv) < 0.01


def test_portfolio_margin_span():
    positions = [
        {"strike": 60_000.0, "time_to_expiry": 0.25, "iv": 0.65, "type": "CALL", "qty": 1.0},
        {"strike": 55_000.0, "time_to_expiry": 0.25, "iv": 0.70, "type": "PUT", "qty": -1.0},
    ]
    scenarios = OptionsAnalyticalEngine.simulate_portfolio_margin_span(
        spot=60_000.0,
        positions=positions,
    )
    assert len(scenarios) == 21  # 7 price shifts * 3 vol shifts
    assert all(s.required_margin_usd >= 0.0 for s in scenarios)


def test_avellaneda_stoikov_market_making():
    mm = AvellanedaStoikovModel(max_inventory=5.0)

    # 1. Neutral inventory
    q1 = mm.generate_quotes("BTCUSDT", mid_price=60_000.0, volatility=0.02)
    assert q1.bid_price < q1.mid_price < q1.ask_price
    assert q1.adverse_selection_warning is False

    # 2. Long inventory skew
    mm.update_inventory("BUY", 2.0)
    q2 = mm.generate_quotes("BTCUSDT", mid_price=60_000.0, volatility=0.02)
    # Reservation price should be lower than mid to encourage selling
    assert q2.reservation_price < 60_000.0

    # 3. Adverse selection under positive OFI (toxic buyer flow)
    q3 = mm.generate_quotes("BTCUSDT", mid_price=60_000.0, order_flow_imbalance=0.8)
    assert q3.adverse_selection_warning is True
    assert q3.ask_price > q2.ask_price  # Ask lifted higher
