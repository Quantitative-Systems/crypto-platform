"""Unit tests for Phase J: Regime Transition, Recovery & Re-Activation Research.

Validates the 5-dimensional recovery confirmation engine:
1. Volatility Normalization
2. Liquidity Restored / Spread Healing
3. Structural Higher-Low / Trend Alignment
4. Cross-Market Calming
5. Positioning Stability

And tests the Staged Post-Crisis Pacing:
CRISIS_FLAT (0.0x) -> STABILIZATION_PROBE (0.25x) -> STRUCTURAL_TRANSITION (0.50x) -> FULL_RECOVERY_ACTIVE (1.0x)
plus FALSE_RECOVERY_ABORT tripwire.
"""
from __future__ import annotations

from execution.risk.contracts import (
    DefenseLayerCheck,
    DrawdownTier,
    MarketClarityState,
    ReactivationStage,
    RecoveryConfirmationAudit,
    RiskAction,
)
from execution.risk.drawdown_governor import DrawdownGovernor
from execution.risk.reactivation_engine import ReactivationEngine
from execution.risk.systemic_risk_governor import SystemicRiskGovernor
from execution.risk.unknown_state_engine import UnknownStateEngine
from market_intelligence.positioning.positioning_engine import (
    FundingState,
    PositioningSnapshot,
    TrappedState,
)
from market_intelligence.regimes.regime_contracts import (
    CorrelationRegime,
    LiquidityRegime,
    MarketRegimeSnapshot,
    RiskRegime,
    TrendRegime,
    VolatilityRegime,
)
from market_model.contracts import (
    MarketPhaseType,
    MarketState,
    MeasurementsSnapshot,
    PhaseSnapshot,
    StructureSnapshot,
    TrendDirection,
    ZonesSnapshot,
)


def _make_sample_states(mtf_trend=TrendDirection.BULLISH, mtf_phase=MarketPhaseType.CONTINUATION, htf_trend=TrendDirection.BULLISH):
    htf = MarketState(
        symbol="BTCUSDT",
        timestamp_ms=1_700_000_000_000,
        timeframe="1w",
        close_price=50000.0,
        open_price=49000.0,
        high_price=51000.0,
        low_price=48500.0,
        volume=10000.0,
        structure=StructureSnapshot(external_trend=htf_trend, internal_trend=htf_trend),
        zones=ZonesSnapshot(premium_discount_zone="DISCOUNT"),
        phase=PhaseSnapshot(current_phase=MarketPhaseType.CONTINUATION),
        measurements=MeasurementsSnapshot(volume_sma_ratio=1.2, adx=28.0),
    )
    mtf = MarketState(
        symbol="BTCUSDT",
        timestamp_ms=1_700_000_000_000,
        timeframe="1d",
        close_price=50000.0,
        open_price=49200.0,
        high_price=50500.0,
        low_price=49000.0,
        volume=5000.0,
        structure=StructureSnapshot(external_trend=mtf_trend, internal_trend=mtf_trend),
        zones=ZonesSnapshot(premium_discount_zone="DISCOUNT"),
        phase=PhaseSnapshot(current_phase=mtf_phase),
        measurements=MeasurementsSnapshot(volume_sma_ratio=1.1, adx=25.0),
    )
    ltf = MarketState(
        symbol="BTCUSDT",
        timestamp_ms=1_700_000_000_000,
        timeframe="4h",
        close_price=50000.0,
        open_price=49800.0,
        high_price=50100.0,
        low_price=49700.0,
        volume=1200.0,
        structure=StructureSnapshot(external_trend=TrendDirection.BULLISH, internal_trend=TrendDirection.BULLISH),
        zones=ZonesSnapshot(premium_discount_zone="DISCOUNT"),
        phase=PhaseSnapshot(current_phase=MarketPhaseType.CONTINUATION),
        measurements=MeasurementsSnapshot(volume_sma_ratio=1.3, adx=26.0),
    )
    return htf, mtf, ltf


def test_staged_reactivation_lifecycle():
    """Verify clean stage transitions from crisis halt to full recovery."""
    engine = ReactivationEngine()
    symbol = "BTCUSDT"

    # Step 1: Market experiences severe crisis shock
    engine.register_crisis_event(symbol)
    assert engine.get_stage(symbol) == ReactivationStage.CRISIS_FLAT

    # While volatility is EXTREME, must remain CRISIS_FLAT (0.0x)
    htf, mtf, ltf = _make_sample_states()
    extreme_regime = MarketRegimeSnapshot(
        timestamp_ms=1_700_000_000_000,
        volatility=VolatilityRegime.EXTREME,
        vol_percentile=0.98,
        liquidity=LiquidityRegime.NORMAL,
        trend=TrendRegime.TRANSITIONAL,
        correlation=CorrelationRegime.IDIOSYNCRATIC,
        risk=RiskRegime.RISK_OFF,
    )
    audit = engine.evaluate_reactivation_status(
        symbol=symbol,
        timestamp_ms=1_700_000_000_000,
        htf_state=htf,
        mtf_state=mtf,
        ltf_state=ltf,
        direction=1,
        regime=extreme_regime,
        quote_spread_bps=2.0,
        vix_level=20.0,
    )
    assert audit.stage == ReactivationStage.CRISIS_FLAT
    assert audit.approved_risk_factor == 0.0

    # Step 2: Volatility normalizes, but structure not yet aligned -> STABILIZATION_PROBE (0.25x)
    normal_regime = MarketRegimeSnapshot(
        timestamp_ms=1_700_000_100_000,
        volatility=VolatilityRegime.NORMAL,
        vol_percentile=0.50,
        liquidity=LiquidityRegime.NORMAL,
        trend=TrendRegime.TRANSITIONAL,
        correlation=CorrelationRegime.BTC_LED,
        risk=RiskRegime.NEUTRAL,
    )
    # Neutral MTF structure
    htf_u, mtf_u, ltf_u = _make_sample_states(mtf_trend=TrendDirection.NEUTRAL, mtf_phase=MarketPhaseType.PULLBACK)
    audit2 = engine.evaluate_reactivation_status(
        symbol=symbol,
        timestamp_ms=1_700_000_100_000,
        htf_state=htf_u,
        mtf_state=mtf_u,
        ltf_state=ltf_u,
        direction=1,
        regime=normal_regime,
        quote_spread_bps=2.0,
        vix_level=18.0,
    )
    assert audit2.stage == ReactivationStage.STABILIZATION_PROBE
    assert audit2.approved_risk_factor == 0.25

    # Step 3: MTF continuation confirmed -> STRUCTURAL_TRANSITION (0.50x)
    htf_n, mtf_b, ltf_b = _make_sample_states(mtf_trend=TrendDirection.BULLISH, mtf_phase=MarketPhaseType.CONTINUATION, htf_trend=TrendDirection.NEUTRAL)
    audit3 = engine.evaluate_reactivation_status(
        symbol=symbol,
        timestamp_ms=1_700_000_200_000,
        htf_state=htf_n,
        mtf_state=mtf_b,
        ltf_state=ltf_b,
        direction=1,
        regime=normal_regime,
        quote_spread_bps=2.0,
        vix_level=18.0,
    )
    assert audit3.stage == ReactivationStage.STRUCTURAL_TRANSITION
    assert audit3.approved_risk_factor == 0.50

    # Step 4: HTF trend aligns -> FULL_RECOVERY_ACTIVE (1.0x)
    htf_full, mtf_full, ltf_full = _make_sample_states(mtf_trend=TrendDirection.BULLISH, mtf_phase=MarketPhaseType.CONTINUATION, htf_trend=TrendDirection.BULLISH)
    audit4 = engine.evaluate_reactivation_status(
        symbol=symbol,
        timestamp_ms=1_700_000_300_000,
        htf_state=htf_full,
        mtf_state=mtf_full,
        ltf_state=ltf_full,
        direction=1,
        regime=normal_regime,
        quote_spread_bps=1.5,
        vix_level=16.0,
    )
    assert audit4.stage == ReactivationStage.FULL_RECOVERY_ACTIVE
    assert audit4.approved_risk_factor == 1.0


def test_false_recovery_tripwire_aborts():
    """Verify engine halts immediately if a probe fails into breakdown."""
    engine = ReactivationEngine()
    symbol = "BTCUSDT"

    engine.register_crisis_event(symbol)
    assert engine.get_stage(symbol) == ReactivationStage.CRISIS_FLAT

    # Simulate registering a false recovery failure
    engine.register_false_recovery_failure(symbol)
    assert engine.get_stage(symbol) == ReactivationStage.FALSE_RECOVERY_ABORT

    htf, mtf, ltf = _make_sample_states()
    # If spread blows out or vol spikes during abort state
    audit = engine.evaluate_reactivation_status(
        symbol=symbol,
        timestamp_ms=1_700_000_000_000,
        htf_state=htf,
        mtf_state=mtf,
        ltf_state=ltf,
        direction=1,
        quote_spread_bps=15.0, # Blowout > 8.0 bps
    )
    assert audit.stage == ReactivationStage.CRISIS_FLAT
    assert audit.approved_risk_factor == 0.0


def test_5_dimensional_recovery_verifications():
    """Verify each of the 5 recovery confirmation dimensions is enforced."""
    engine = ReactivationEngine(max_stabilization_spread_bps=8.0, vix_calm_ceiling=26.0)
    symbol = "BTCUSDT"
    engine.set_stage(symbol, ReactivationStage.CRISIS_FLAT)

    htf, mtf, ltf = _make_sample_states()
    normal_regime = MarketRegimeSnapshot(
        timestamp_ms=1_700_000_000_000,
        volatility=VolatilityRegime.NORMAL,
        vol_percentile=0.50,
        liquidity=LiquidityRegime.NORMAL,
        trend=TrendRegime.TRANSITIONAL,
        correlation=CorrelationRegime.BTC_LED,
        risk=RiskRegime.NEUTRAL,
    )

    # Dimension 1: Volatility Failure
    high_vol_regime = MarketRegimeSnapshot(
        timestamp_ms=1_700_000_000_000,
        volatility=VolatilityRegime.HIGH,
        vol_percentile=0.95, # > 0.90 ceiling
        liquidity=LiquidityRegime.NORMAL,
        trend=TrendRegime.TRANSITIONAL,
        correlation=CorrelationRegime.BTC_LED,
        risk=RiskRegime.NEUTRAL,
    )
    a1 = engine.evaluate_reactivation_status(
        symbol=symbol, timestamp_ms=1_700_000_000_000,
        htf_state=htf, mtf_state=mtf, ltf_state=ltf, direction=1,
        regime=high_vol_regime, quote_spread_bps=2.0, vix_level=18.0,
    )
    assert not a1.is_volatility_normalized
    assert a1.approved_risk_factor == 0.0

    # Dimension 2: Liquidity Failure (Spread blowout)
    a2 = engine.evaluate_reactivation_status(
        symbol=symbol, timestamp_ms=1_700_000_000_000,
        htf_state=htf, mtf_state=mtf, ltf_state=ltf, direction=1,
        regime=normal_regime, quote_spread_bps=12.0, vix_level=18.0,
    )
    assert not a2.is_liquidity_restored
    assert a2.approved_risk_factor == 0.0

    # Dimension 4: Cross-Market Failure (VIX > 26.0)
    a4 = engine.evaluate_reactivation_status(
        symbol=symbol, timestamp_ms=1_700_000_000_000,
        htf_state=htf, mtf_state=mtf, ltf_state=ltf, direction=1,
        regime=normal_regime, quote_spread_bps=2.0, vix_level=32.0,
    )
    assert not a4.is_cross_market_calm
    assert a4.approved_risk_factor == 0.0

    # Dimension 5: Overheated Positioning Failure
    pos_hot = PositioningSnapshot(
        timestamp_ms=1_700_000_000_000,
        funding_rate_8h_bps=42.0,
        oi_change_pct_24h=0.15,
        funding_state=FundingState.EXTREME_POSITIVE,
        trapped_setup=TrappedState.NONE,
    )
    engine.set_stage(symbol, ReactivationStage.STABILIZATION_PROBE)
    a5 = engine.evaluate_reactivation_status(
        symbol=symbol, timestamp_ms=1_700_000_000_000,
        htf_state=htf, mtf_state=mtf, ltf_state=ltf, direction=1,
        regime=normal_regime, positioning=pos_hot, quote_spread_bps=2.0, vix_level=18.0,
    )
    assert not a5.is_positioning_safe
    assert a5.approved_risk_factor == 0.25 # Stays in probe tier, doesn't promote


def test_systemic_risk_governor_with_reactivation_engine():
    """Test full SystemicRiskGovernor integration with staged risk multipliers."""
    react_engine = ReactivationEngine()
    governor = SystemicRiskGovernor(reactivation_engine=react_engine)
    symbol = "BTCUSDT"

    htf, mtf, ltf = _make_sample_states()
    normal_regime = MarketRegimeSnapshot(
        timestamp_ms=1_700_000_000_000,
        volatility=VolatilityRegime.NORMAL,
        vol_percentile=0.40,
        liquidity=LiquidityRegime.NORMAL,
        trend=TrendRegime.TRENDING,
        correlation=CorrelationRegime.BTC_LED,
        risk=RiskRegime.RISK_ON,
    )

    # 1. When in crisis halt, governor blocks trade completely
    react_engine.register_crisis_event(symbol)
    verdict_halt = governor.evaluate_risk_verdict(
        symbol=symbol,
        direction=1,
        candidate_destination_r=5.0,
        htf_state=htf,
        mtf_state=mtf,
        ltf_state=ltf,
        regime=normal_regime,
        quote_spread_bps=12.0, # Liquidity not yet restored
        proposed_base_risk_pct=0.01,
    )
    assert not verdict_halt.is_trade_allowed
    assert verdict_halt.risk_action == RiskAction.NO_TRADE_FLAT
    assert verdict_halt.approved_risk_pct == 0.0

    # 2. When in stabilization probe, governor approves scaled-down risk (0.25% instead of 1.0%)
    react_engine.set_stage(symbol, ReactivationStage.STABILIZATION_PROBE)
    htf_pb, mtf_pb, ltf_pb = _make_sample_states(mtf_trend=TrendDirection.BULLISH, mtf_phase=MarketPhaseType.PULLBACK, htf_trend=TrendDirection.BULLISH)
    verdict_probe = governor.evaluate_risk_verdict(
        symbol=symbol,
        direction=1,
        candidate_destination_r=5.0,
        htf_state=htf_pb,
        mtf_state=mtf_pb,
        ltf_state=ltf_pb,
        regime=normal_regime,
        quote_spread_bps=2.0,
        proposed_base_risk_pct=0.01,
    )
    assert verdict_probe.is_trade_allowed
    assert verdict_probe.risk_action == RiskAction.TRADE_REDUCED
    assert verdict_probe.approved_risk_pct == 0.0025 # 0.25x of 1.0%

    # 3. When full recovery is reached, governor approves full 1.0% risk
    react_engine.set_stage(symbol, ReactivationStage.FULL_RECOVERY_ACTIVE)
    verdict_full = governor.evaluate_risk_verdict(
        symbol=symbol,
        direction=1,
        candidate_destination_r=5.0,
        htf_state=htf,
        mtf_state=mtf,
        ltf_state=ltf,
        regime=normal_regime,
        quote_spread_bps=1.5,
        proposed_base_risk_pct=0.01,
    )
    assert verdict_full.is_trade_allowed
    assert verdict_full.risk_action == RiskAction.TRADE_FULL
    assert verdict_full.approved_risk_pct == 0.01
