"""Unit tests for Capital Survival Governors, Unknown State Engine, and Drawdown Defense."""
from execution.risk.contracts import (
    DrawdownTier,
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
    MarketRegimeSnapshot,
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


def _make_state(symbol: str, trend: TrendDirection, phase: MarketPhaseType, close: float = 65000.0) -> MarketState:
    return MarketState(
        symbol=symbol,
        timestamp_ms=1_700_000_000_000,
        timeframe="1d",
        close_price=close,
        open_price=close * 0.99,
        high_price=close * 1.02,
        low_price=close * 0.98,
        volume=1500.0,
        structure=StructureSnapshot(external_trend=trend, internal_trend=trend),
        zones=ZonesSnapshot(premium_discount_zone="DISCOUNT"),
        phase=PhaseSnapshot(current_phase=phase),
        measurements=MeasurementsSnapshot(volume_sma_ratio=1.2, adx=26.0),
    )


def test_drawdown_governor_tier_progression_and_circuit_breaker():
    governor = DrawdownGovernor(
        elevated_threshold_pct=5.0,
        severe_threshold_pct=10.0,
        critical_halt_pct=15.0,
        initial_equity_usd=100_000.0,
    )

    # Initial state: Normal
    status = governor.evaluate_status()
    assert status.tier == DrawdownTier.NORMAL
    assert status.risk_multiplier == 1.0
    assert status.destination_r_floor == 4.0
    assert status.is_halted is False

    # Simulate 6 consecutive 1R losses -> -6R = -6% Drawdown
    for i in range(6):
        status = governor.update_equity_r(-1.0, bar_index=i)

    # Tier: ELEVATED (5% <= DD < 10%)
    assert status.tier == DrawdownTier.ELEVATED
    assert status.risk_multiplier == 0.50
    assert status.destination_r_floor == 4.0
    assert status.is_halted is False

    # Simulate another 5 losses -> -11R = -11% Drawdown
    for i in range(6, 11):
        status = governor.update_equity_r(-1.0, bar_index=i)

    # Tier: SEVERE (10% <= DD < 15%)
    assert status.tier == DrawdownTier.SEVERE
    assert status.risk_multiplier == 0.25 # 75% haircut
    assert status.destination_r_floor == 5.0 # Elevated target floor
    assert status.is_halted is False

    # Simulate another 5 losses -> -16R = -16% Drawdown
    for i in range(11, 16):
        status = governor.update_equity_r(-1.0, bar_index=i)

    # Tier: CRITICAL_HALT (DD >= 15%) -> Trading Circuit Breaker Tripped!
    assert status.tier == DrawdownTier.CRITICAL_HALT
    assert status.risk_multiplier == 0.0
    assert status.is_halted is True


def test_unknown_state_engine_anomaly_detection():
    engine = UnknownStateEngine(max_spread_bps=25.0)

    htf = _make_state("BTCUSDT", TrendDirection.BULLISH, MarketPhaseType.CONTINUATION)
    mtf = _make_state("BTCUSDT", TrendDirection.BULLISH, MarketPhaseType.CONTINUATION)
    ltf = _make_state("BTCUSDT", TrendDirection.BULLISH, MarketPhaseType.CONTINUATION)

    # 1. Normal characterized condition
    clarity_normal = engine.evaluate_clarity(htf, mtf, ltf)
    assert clarity_normal.clarity_state == MarketClarityState.KNOWN_FAVORABLE
    assert clarity_normal.is_tradable is True

    # 2. Corrupted data anomaly: Inverted OHLC
    corrupt_ltf = _make_state("BTCUSDT", TrendDirection.BULLISH, MarketPhaseType.CONTINUATION)
    corrupt_ltf.high_price = 50000.0
    corrupt_ltf.low_price = 60000.0 # High < Low!
    clarity_corrupt = engine.evaluate_clarity(htf, mtf, corrupt_ltf)
    assert clarity_corrupt.clarity_state == MarketClarityState.UNKNOWN_UNSTABLE
    assert clarity_corrupt.is_tradable is False
    assert any("DATA_RISK" in a for a in clarity_corrupt.detected_anomalies)

    # 3. Execution spread blowout
    clarity_spread = engine.evaluate_clarity(htf, mtf, ltf, quote_spread_bps=32.0)
    assert clarity_spread.clarity_state == MarketClarityState.UNKNOWN_UNSTABLE
    assert clarity_spread.is_tradable is False
    assert any("EXECUTION_RISK" in a for a in clarity_spread.detected_anomalies)


def test_systemic_risk_governor_reconciled_positioning():
    risk_gov = SystemicRiskGovernor()
    htf = _make_state("BTCUSDT", TrendDirection.BULLISH, MarketPhaseType.CONTINUATION)
    mtf = _make_state("BTCUSDT", TrendDirection.BULLISH, MarketPhaseType.CONTINUATION)
    ltf = _make_state("BTCUSDT", TrendDirection.BULLISH, MarketPhaseType.CONTINUATION)

    # Case 1: Short Squeeze Prime in strong bull trend -> Full approved risk
    pos_squeeze = PositioningSnapshot(
        timestamp_ms=1_700_000_000_000,
        funding_state=FundingState.EXTREME_NEGATIVE,
        trapped_setup=TrappedState.SHORT_SQUEEZE_PRIME,
    )
    verdict_squeeze = risk_gov.evaluate_risk_verdict(
        symbol="BTCUSDT",
        direction=1,
        candidate_destination_r=5.5,
        htf_state=htf,
        mtf_state=mtf,
        ltf_state=ltf,
        positioning=pos_squeeze,
    )
    assert verdict_squeeze.is_trade_allowed is True
    assert verdict_squeeze.approved_risk_pct == 0.01

    # Case 2: Overheated funding in strong bull trend -> Tradable with 50% haircut (0.50% risk)
    pos_overheated = PositioningSnapshot(
        timestamp_ms=1_700_000_000_000,
        funding_state=FundingState.EXTREME_POSITIVE,
        trapped_setup=TrappedState.LONG_LIQUIDATION_RISK,
    )
    verdict_overheated = risk_gov.evaluate_risk_verdict(
        symbol="BTCUSDT",
        direction=1,
        candidate_destination_r=5.5,
        htf_state=htf,
        mtf_state=mtf,
        ltf_state=ltf,
        positioning=pos_overheated,
    )
    assert verdict_overheated.is_trade_allowed is True
    assert verdict_overheated.approved_risk_pct == 0.005 # 50% haircut
    assert verdict_overheated.risk_action == RiskAction.TRADE_REDUCED

    # Case 3: Overheated funding in sideways chop -> STRICT NO TRADE FLAT
    htf_chop = _make_state("BTCUSDT", TrendDirection.RANGE, MarketPhaseType.CONSOLIDATION)
    mtf_chop = _make_state("BTCUSDT", TrendDirection.RANGE, MarketPhaseType.CONSOLIDATION)
    verdict_chop = risk_gov.evaluate_risk_verdict(
        symbol="BTCUSDT",
        direction=1,
        candidate_destination_r=5.5,
        htf_state=htf_chop,
        mtf_state=mtf_chop,
        ltf_state=ltf,
        positioning=pos_overheated,
    )
    assert verdict_chop.is_trade_allowed is False
    assert verdict_chop.risk_action == RiskAction.NO_TRADE_FLAT
