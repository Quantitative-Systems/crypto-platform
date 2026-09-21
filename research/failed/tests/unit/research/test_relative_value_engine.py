"""
Tests for Relative Value & Statistical Arbitrage Engine.
Verifies OLS estimation, Engle-Granger & Johansen cointegration,
Ornstein-Uhlenbeck half-life, causal rolling spreads, and decomposed friction.
"""

import pytest
import math
import numpy as np
from market_intelligence.primitives import Candle
from research.discovery_lab.relative_value_config import (
    RelativeValueConfig,
    DecomposedFrictionModel,
)
from research.discovery_lab.relative_value_engine import (
    RelativeValueEngine,
    CointegrationMetrics,
)


def test_ols_estimation():
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    # y = 2.0 * x + 1.5
    y = 2.0 * x + 1.5
    beta, alpha, res = RelativeValueEngine.calculate_ols(y, x)
    assert pytest.approx(beta, rel=1e-3) == 2.0
    assert pytest.approx(alpha, rel=1e-3) == 1.5
    assert np.allclose(res, 0.0, atol=1e-5)


def test_half_life_mean_reverting_vs_random_walk():
    # 1. Synthetic Mean Reverting AR(1) process: x_t = 0.8 * x_{t-1} + noise
    # gamma = 0.8 - 1 = -0.2 -> kappa = 0.2 -> half_life = ln(2)/0.2 = ~3.46 bars
    rng = np.random.default_rng(42)
    n = 500
    mr_series = np.zeros(n)
    for i in range(1, n):
        mr_series[i] = 0.8 * mr_series[i - 1] + rng.normal(0, 0.5)

    hl_mr = RelativeValueEngine.calculate_half_life(mr_series)
    assert 2.0 <= hl_mr <= 6.0

    # 2. Synthetic Random Walk: x_t = x_{t-1} + noise (gamma ~ 0 -> explosive / infinite half-life)
    rw_series = np.cumsum(rng.normal(0, 1.0, size=n))
    hl_rw = RelativeValueEngine.calculate_half_life(rw_series)
    # Random walk half-life should be either infinite or very large
    assert math.isinf(hl_rw) or hl_rw > 30.0


def test_engle_granger_cointegration():
    rng = np.random.default_rng(123)
    n = 300
    # True I(1) common factor
    common_trend = np.cumsum(rng.normal(0, 1.0, size=n)) + 50.0
    
    # Cointegrated pair: A and B share common trend with stationary residual
    log_b = np.log(common_trend)
    log_a = 1.2 * log_b + 0.5 + rng.normal(0, 0.02, size=n)

    beta, alpha, adf_stat, p_val, is_coint = RelativeValueEngine.calculate_engle_granger(log_a, log_b)
    assert pytest.approx(beta, rel=0.1) == 1.2
    assert is_coint is True
    assert p_val < 0.05
    assert adf_stat < -3.34


def test_johansen_cointegration():
    rng = np.random.default_rng(456)
    n = 300
    common_trend = np.cumsum(rng.normal(0, 1.0, size=n)) + 50.0
    log_b = np.log(common_trend)
    log_a = 1.0 * log_b + rng.normal(0, 0.02, size=n)

    eig, trace_stat, is_coint = RelativeValueEngine.calculate_johansen(log_a, log_b)
    assert trace_stat > 15.41
    assert is_coint is True


def test_decomposed_friction_model():
    f = DecomposedFrictionModel(
        taker_fee_bps_per_leg=5.0,
        slippage_bps_per_leg=3.0,
    )
    # Single leg roundtrip = (5 + 3) * 2 = 16 bps
    assert f.single_leg_roundtrip_bps == 16.0
    # Two legs (Asset A + Asset B) = 16 * 2 = 32 bps
    assert f.total_pair_roundtrip_bps == 32.0
    assert pytest.approx(f.total_pair_roundtrip_pct, rel=1e-4) == 0.0032


def test_causal_rolling_spread_no_lookahead():
    engine = RelativeValueEngine(config=RelativeValueConfig(rolling_lookback_window=30))
    n = 100
    log_b = np.linspace(2.0, 3.0, n)
    log_a = 1.5 * log_b + 0.1

    betas, alphas, spreads, z_scores = engine.compute_causal_rolling_spread(log_a, log_b)
    # Bars before lookback window must be NaN
    assert np.all(np.isnan(betas[:30]))
    assert np.all(np.isnan(z_scores[:30]))
    # Bars from index 30 onwards must be finite
    assert not np.isnan(betas[30])
    assert pytest.approx(betas[30], rel=1e-3) == 1.5
