"""Unit tests for Phase I: Defensive Efficiency & Regime Coverage.

Validates layer-by-layer toggles, calibration mode behaviors,
and DefenseEfficiencyMetrics contracts.
"""
from __future__ import annotations

from execution.risk.contracts import (
    DefenseEfficiencyMetrics,
    DrawdownTier,
    HistoricalCrisisEpisode,
    MarketClarityState,
    RiskAction,
)
from execution.risk.drawdown_governor import DrawdownGovernor
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


def _make_bull_states():
    htf = MarketState(
        symbol="BTCUSDT",
        timestamp_ms=1_700_000_000_000,
        timeframe="1w",
        close_price=50000.0,
        open_price=49000.0,
        high_price=51000.0,
        low_price=48500.0,
        volume=10000.0,
        structure=StructureSnapshot(external_trend=TrendDirection.BULLISH, internal_trend=TrendDirection.BULLISH),
        zones=ZonesSnapshot(premium_discount_zone="DISCOUNT"),
        phase=PhaseSnapshot(current_phase=MarketPhaseType.CONTINUATION),
        measurements=MeasurementsSnapshot(volume_sma_ratio=1.2, adx=28.0),
    )
    mtf = MarketState(
        symbol="BTCUSDT",
        timestamp_ms=1_700_000_000_000,
        timeframe="1d",
        close_price=50000.0,
        open_price=49500.0,
        high_price=50500.0,
        low_price=49000.0,
        volume=3000.0,
        structure=StructureSnapshot(external_trend=TrendDirection.BULLISH, internal_trend=TrendDirection.BULLISH),
        zones=ZonesSnapshot(premium_discount_zone="DISCOUNT"),
        phase=PhaseSnapshot(current_phase=MarketPhaseType.CONTINUATION),
        measurements=MeasurementsSnapshot(volume_sma_ratio=1.2, adx=26.0),
    )
    ltf = MarketState(
        symbol="BTCUSDT",
        timestamp_ms=1_700_000_000_000,
        timeframe="4h",
        close_price=50000.0,
        open_price=49800.0,
        high_price=50200.0,
        low_price=49700.0,
        volume=500.0,
        structure=StructureSnapshot(external_trend=TrendDirection.BULLISH, internal_trend=TrendDirection.BULLISH),
        zones=ZonesSnapshot(premium_discount_zone="DISCOUNT"),
        phase=PhaseSnapshot(current_phase=MarketPhaseType.CONTINUATION),
        measurements=MeasurementsSnapshot(volume_sma_ratio=1.1, adx=24.0),
    )
    regime = MarketRegimeSnapshot(
        risk=RiskRegime.RISK_ON,
        volatility=VolatilityRegime.NORMAL,
        trend=TrendRegime.TRENDING,
        liquidity=LiquidityRegime.ABUNDANT,
        correlation=CorrelationRegime.IDIOSYNCRATIC,
        timestamp_ms=1700000000000,
    )
    return htf, mtf, ltf, regime


def test_layer_toggles():
    htf, mtf, ltf, regime = _make_bull_states()

    # Extreme volatility regime that would normally block
    vol_regime = MarketRegimeSnapshot(
        risk=RiskRegime.RISK_OFF,
        volatility=VolatilityRegime.EXTREME,
        trend=TrendRegime.RANGING,
        liquidity=LiquidityRegime.TIGHT,
        correlation=CorrelationRegime.MACRO_LED,
        timestamp_ms=1700000000000,
    )

    # 1. With Layer 4 enabled -> Blocked
    gov_strict = SystemicRiskGovernor(enable_layer_4=True)
    v1 = gov_strict.evaluate_risk_verdict(
        symbol="BTCUSDT",
        direction=1,
        candidate_destination_r=4.5,
        htf_state=htf,
        mtf_state=mtf,
        ltf_state=ltf,
        regime=vol_regime,
    )
    assert not v1.is_trade_allowed
    assert "LAYER_4_REGIME" in v1.primary_reason

    # 2. With Layer 4 disabled -> Allowed
    gov_no_l4 = SystemicRiskGovernor(enable_layer_4=False)
    v2 = gov_no_l4.evaluate_risk_verdict(
        symbol="BTCUSDT",
        direction=1,
        candidate_destination_r=4.5,
        htf_state=htf,
        mtf_state=mtf,
        ltf_state=ltf,
        regime=vol_regime,
    )
    assert v2.is_trade_allowed
    assert v2.approved_risk_pct > 0.0


def test_calibration_mode_sizing():
    htf, mtf, ltf, regime = _make_bull_states()

    # Overheated funding in a strong bull continuation
    pos_hot = PositioningSnapshot(
        timestamp_ms=1700000000000,
        funding_rate_8h_bps=32.0,
        funding_state=FundingState.EXTREME_POSITIVE,
        trapped_setup=TrappedState.NONE,
    )

    # STRICT mode -> 0.50x haircut (0.0050 risk)
    gov_strict = SystemicRiskGovernor(calibration_mode="STRICT")
    v_strict = gov_strict.evaluate_risk_verdict(
        symbol="BTCUSDT",
        direction=1,
        candidate_destination_r=5.5,
        htf_state=htf,
        mtf_state=mtf,
        ltf_state=ltf,
        regime=regime,
        positioning=pos_hot,
    )
    assert v_strict.is_trade_allowed
    assert v_strict.approved_risk_pct == 0.0050

    # CALIBRATED mode -> 0.85x sizing for high asymmetry >= 4.5R target (0.0085 risk)
    gov_cal = SystemicRiskGovernor(calibration_mode="CALIBRATED")
    v_cal = gov_cal.evaluate_risk_verdict(
        symbol="BTCUSDT",
        direction=1,
        candidate_destination_r=5.5,
        htf_state=htf,
        mtf_state=mtf,
        ltf_state=ltf,
        regime=regime,
        positioning=pos_hot,
    )
    assert v_cal.is_trade_allowed
    assert v_cal.approved_risk_pct == 0.0085

    # But CALIBRATED mode STILL strictly blocks overheated funding during CHOP!
    chop_regime = MarketRegimeSnapshot(
        risk=RiskRegime.NEUTRAL,
        volatility=VolatilityRegime.NORMAL,
        trend=TrendRegime.RANGING,
        liquidity=LiquidityRegime.TIGHT,
        correlation=CorrelationRegime.IDIOSYNCRATIC,
        is_favorable_for_trend_following=False,
        timestamp_ms=1700000000000,
    )
    v_chop = gov_cal.evaluate_risk_verdict(
        symbol="BTCUSDT",
        direction=1,
        candidate_destination_r=5.5,
        htf_state=htf,
        mtf_state=mtf,
        ltf_state=ltf,
        regime=chop_regime,
        positioning=pos_hot,
    )
    assert not v_chop.is_trade_allowed


def test_defense_efficiency_metrics():
    m = DefenseEfficiencyMetrics(
        layer_id="LAYER_4_REGIME",
        total_signals_evaluated=100,
        approved_trades=80,
        rejected_signals=20,
        rejection_ratio_pct=20.0,
        true_positive_blocks=14,
        false_positive_blocks=6,
        true_positive_approvals=45,
        false_negative_approvals=35,
        block_precision_pct=70.0,
        net_r_realized=42.5,
        net_r_sacrificed=5.0,
        loss_r_prevented=14.0,
        max_drawdown_pct=5.5,
        mdd_reduction_pct=1.5,
        var_95_r=-1.0,
        cvar_95_tail_loss_r=-1.05,
        defense_efficiency_ratio=0.30,
    )
    d = m.to_dict()
    assert d["layer_id"] == "LAYER_4_REGIME"
    assert d["block_precision_pct"] == 70.0
    assert d["defense_efficiency_ratio"] == 0.30


def test_crisis_episode_dataclass():
    ep = HistoricalCrisisEpisode(
        episode_id="EP_05_FTX_COLLAPSE_2022",
        name="FTX Insolvency Shock & Liquidity Vacuum",
        start_ts=1667692800000,
        end_ts=1672531199000,
        regime_climate="CRITICAL_CRYPTO_CRISIS",
        primary_stress="Exchange insolvency and systemic counterparty contagion",
        description="FTX bank run leading to Chapter 11 filing and market-wide liquidation flush",
    )
    assert ep.episode_id == "EP_05_FTX_COLLAPSE_2022"
    assert ep.start_ts < ep.end_ts
