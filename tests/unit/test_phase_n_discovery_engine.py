"""Unit test suite for Phase N: Autonomous Market & Instrument Discovery Engine."""
import time
from pathlib import Path

from execution.decision.decision_engine import AutonomousDecisionEngine, NoTradeReason
from execution.intelligence.hierarchy_of_truth import (
    HierarchyOfTruthValidator,
    TruthLevel,
)
from execution.intelligence.two_brain_coordinator import (
    IntelligenceBrainContext,
    TwoBrainCoordinator,
)
from execution.portfolio.factor_engine import PortfolioFactorEngine
from instrument.asset_class import AssetClass
from instrument.discovery_engine import (
    AutonomousMarketDiscoveryEngine,
    DiscoveredInstrumentCandidate,
    InstrumentLifecycleStage,
    OpportunityScoreCard,
    QualificationStatus,
)
from instrument.instrument_contract import build_instrument
from instrument.instrument_health import InstrumentHealth
from research.learning.hypothesis_lifecycle import (
    AutonomousHypothesisRegistry,
    HypothesisStatus,
    SystemicHypothesis,
)


class TestPhaseNDiscoveryEngine:
    """Test suite verifying autonomous instrument discovery, truth hierarchy, and learning."""

    def test_discovery_engine_qualification_gates(self):
        engine = AutonomousMarketDiscoveryEngine()

        # 1. Eligible crypto-base instruments
        c_btc = engine.discover_instrument("BTC/USD", daily_volume_usd=100_000_000.0, observed_spread_bps=2.0)
        assert c_btc.qualification_status == QualificationStatus.QUALIFIED
        assert c_btc.is_tradable is True

        c_gold = engine.discover_instrument("BTC/XAU", daily_volume_usd=25_000_000.0, observed_spread_bps=4.5)
        assert c_gold.qualification_status == QualificationStatus.QUALIFIED
        assert c_gold.is_tradable is True

        # 2. Non-crypto base instruments strictly rejected
        c_eur = engine.discover_instrument("EUR/USD")
        assert c_eur.qualification_status == QualificationStatus.DISQUALIFIED
        assert "BASE_NOT_CRYPTO" in c_eur.disqualification_reason
        assert c_eur.is_tradable is False

        c_xau_usd = engine.discover_instrument("XAU/USD")
        assert c_xau_usd.qualification_status == QualificationStatus.DISQUALIFIED
        assert "BASE_NOT_CRYPTO" in c_xau_usd.disqualification_reason

        # 3. Insufficient history gate check (< 500 bars)
        c_nohist = engine.discover_instrument("SOL/USD", historical_depth_bars=200)
        assert c_nohist.qualification_status == QualificationStatus.DISQUALIFIED
        assert "INSUFFICIENT_HISTORY" in c_nohist.disqualification_reason

        # 4. Low liquidity volume gate check (< $1M)
        c_lowvol = engine.discover_instrument("ETH/EUR", daily_volume_usd=500_000.0)
        assert c_lowvol.qualification_status == QualificationStatus.DISQUALIFIED
        assert "LOW_VOLUME" in c_lowvol.disqualification_reason

        # 5. High spread gate check (> 15 bps)
        c_widespread = engine.discover_instrument("AVAX/USD", observed_spread_bps=25.0)
        assert c_widespread.qualification_status == QualificationStatus.DISQUALIFIED
        assert "SPREAD_TOO_HIGH" in c_widespread.disqualification_reason

    def test_discovery_engine_opportunity_ranking(self):
        engine = AutonomousMarketDiscoveryEngine()
        engine.discover_instrument("BTC/USD")
        engine.discover_instrument("ETH/USD")
        engine.discover_instrument("BTC/XAU")

        market_states = {
            "BTC/USD": {
                "structure": "BULLISH_TREND", "zone": "DEMAND", "phase": "CONTINUATION",
                "htf_bias": "BULLISH", "mtf_valid": True, "ltf_valid": True,
                "destination_r": 5.0, "spread_bps": 2.0, "entry_price": 60000.0,
                "stop_price": 59000.0, "target_price": 65000.0,
            },
            "ETH/USD": {
                "structure": "BULLISH_TREND", "zone": "DEMAND", "phase": "CONTINUATION",
                "htf_bias": "BULLISH", "mtf_valid": True, "ltf_valid": True,
                "destination_r": 4.2, "spread_bps": 4.0, "entry_price": 3000.0,
                "stop_price": 2900.0, "target_price": 3420.0,
            },
            "BTC/XAU": {
                # Ineligible setup: destination below 4R -> rejected
                "structure": "BULLISH_TREND", "zone": "DEMAND", "phase": "CONTINUATION",
                "htf_bias": "BULLISH", "mtf_valid": True, "ltf_valid": True,
                "destination_r": 3.4, "spread_bps": 5.0, "entry_price": 25.0,
                "stop_price": 24.0, "target_price": 28.4,
            },
        }

        ranked = engine.scan_and_rank_opportunities(market_states, {}, {}, [])
        # Only BTC/USD and ETH/USD qualify (BTC/XAU has 3.4R < 4.0R)
        assert len(ranked) == 2
        # BTC/USD has higher destination (5.0R vs 4.2R) and lower spread (2 bps vs 4 bps) -> Ranked #1
        assert ranked[0].symbol == "BTC/USD"
        assert ranked[1].symbol == "ETH/USD"
        assert ranked[0].composite_rank_score > ranked[1].composite_rank_score

    def test_hierarchy_of_truth_strict_progression(self):
        # 1. Full clean progression through all 12 levels
        rep_valid = HierarchyOfTruthValidator.validate_progression(
            raw_world_valid=True,
            data_quality_valid=True,
            instrument_admitted=True,
            market_model_valid=True,
            regime_favorable=True,
            causal_context_clear=True,
            strategy_hypothesis_valid=True,
            trade_opportunity_ge_4r=True,
            portfolio_capital_approved=True,
            execution_viable=True,
        )
        assert rep_valid.is_valid is True
        assert rep_valid.highest_valid_level == TruthLevel.LEVEL_11_LEARNING_DRIFT

        # 2. Level 2 Failure: Non-crypto base fails early at Level 2
        rep_lvl2_fail = HierarchyOfTruthValidator.validate_progression(
            raw_world_valid=True,
            data_quality_valid=True,
            instrument_admitted=False,  # Failed instrument admission
            market_model_valid=True,
            regime_favorable=True,
            causal_context_clear=True,
            strategy_hypothesis_valid=True,
            trade_opportunity_ge_4r=True,
            portfolio_capital_approved=True,
            execution_viable=True,
        )
        assert rep_lvl2_fail.is_valid is False
        assert rep_lvl2_fail.failure_level == TruthLevel.LEVEL_2_INSTRUMENT_STATE
        assert rep_lvl2_fail.highest_valid_level == TruthLevel.LEVEL_1_DATA_QUALITY

        # 3. Level 7 Failure: Target below 4R fails at Level 7
        rep_lvl7_fail = HierarchyOfTruthValidator.validate_progression(
            raw_world_valid=True,
            data_quality_valid=True,
            instrument_admitted=True,
            market_model_valid=True,
            regime_favorable=True,
            causal_context_clear=True,
            strategy_hypothesis_valid=True,
            trade_opportunity_ge_4r=False,  # < 4R
            portfolio_capital_approved=True,
            execution_viable=True,
        )
        assert rep_lvl7_fail.is_valid is False
        assert rep_lvl7_fail.failure_level == TruthLevel.LEVEL_7_TRADE_OPPORTUNITY

    def test_two_brain_coordinator_firewall(self):
        det_engine = AutonomousDecisionEngine()
        coordinator = TwoBrainCoordinator(det_engine)
        btc_usd = build_instrument("BTC/USD")
        health = InstrumentHealth("BTC/USD")

        market_signal = {
            "structure": "BULLISH_TREND", "zone": "DEMAND", "phase": "CONTINUATION",
            "htf_bias": "BULLISH", "mtf_valid": True, "ltf_valid": True,
            "destination_r": 4.5, "spread_bps": 2.5, "entry_price": 60000.0,
            "stop_price": 59000.0, "target_price": 64500.0,
        }
        gov = {"unknown_state_active": False, "drawdown_circuit_breaker": False, "reactivation_multiplier": 1.0}

        # Case 1: Benign intelligence context -> TRADE approved
        intel_benign = IntelligenceBrainContext(macro_narrative="EXPANSION", event_risk_active=False)
        decision1 = coordinator.process_cycle(btc_usd, health, market_signal, intel_benign, gov, [])
        assert decision1.outcome.decision == "TRADE"
        assert decision1.firewall_enforced is True

        # Case 2: Intelligence brain reports high-impact macro event freeze -> deterministic brain halts
        intel_event = IntelligenceBrainContext(event_risk_active=True, active_event_name="FOMC_RATE_DECISION")
        decision2 = coordinator.process_cycle(btc_usd, health, market_signal, intel_event, gov, [])
        assert decision2.outcome.decision == "NO_TRADE"
        assert decision2.outcome.no_trade_code == NoTradeReason.NO_TRADE_EVENT_FREEZE

    def test_hypothesis_lifecycle_transitions(self):
        registry = AutonomousHypothesisRegistry()
        active = registry.get_active_hypotheses()
        assert len(active) >= 2
        assert any(h.hypothesis_id == "H-CONT-001" for h in active)

        # Register new candidate hypothesis
        new_hyp = SystemicHypothesis(
            hypothesis_id="H-SOL-003",
            title="SOL High-Beta Breakout on Volume Surge",
            description="High volume expansion in SOL during bull regime yields elevated continuation edge.",
            market_model_phase="CONTINUATION",
            causal_conditions={"volume_surge": True},
            status=HypothesisStatus.TESTING,
            sample_size=20,
            win_rate=0.50,
            expectancy_r=0.45,
        )
        registry.register(new_hyp)

        # 1. Update testing with positive results -> promotes to ACTIVE
        status_after_tests = registry.update_lifecycle("H-SOL-003", [1.5, 2.0, -1.0, 3.0, 2.5, -0.8, 1.2, 2.0, -1.0, 1.5])
        assert status_after_tests == HypothesisStatus.ACTIVE

        # 2. Simulate subsequent persistent decay -> demotes to DEGRADED
        status_after_decay = registry.update_lifecycle("H-SOL-003", [-1.0, -1.0, -0.8, -1.2, -0.5])
        assert status_after_decay == HypothesisStatus.DEGRADED

    def test_instrument_operational_lifecycle_stages(self):
        engine = AutonomousMarketDiscoveryEngine()
        c = engine.discover_instrument("BTC/USD", daily_volume_usd=100_000_000.0, observed_spread_bps=2.0)
        assert c.lifecycle_stage == InstrumentLifecycleStage.QUALIFIED

        health = InstrumentHealth("BTC/USD")
        market_valid = {
            "structure": "BULLISH_TREND", "zone": "DEMAND", "phase": "CONTINUATION",
            "htf_bias": "BULLISH", "destination_r": 4.5, "spread_bps": 2.5,
        }
        env = {"regime": "EXPANSION_STABLE"}

        # Advance through HEALTHY -> MARKET_MODEL_COMPATIBLE -> ECONOMICALLY_TRADABLE
        stage = engine.evaluate_operational_stage(c, health, market_valid, env)
        assert stage == InstrumentLifecycleStage.ECONOMICALLY_TRADABLE

    def test_hypothesis_capital_eligibility_tiers(self):
        from research.learning.hypothesis_lifecycle import CapitalEligibilityTier
        registry = AutonomousHypothesisRegistry()
        active = registry.get_active_hypotheses()[0]
        # Active research hypotheses start at RESEARCH_ACTIVE
        assert active.capital_tier == CapitalEligibilityTier.RESEARCH_ACTIVE

        # Promote to PAPER_ELIGIBLE
        registry.promote_capital_tier(active.hypothesis_id, CapitalEligibilityTier.PAPER_ELIGIBLE, "Completed 30-day shadow soak")
        assert active.capital_tier == CapitalEligibilityTier.PAPER_ELIGIBLE

        # Promote to MICRO_LIVE_ELIGIBLE
        registry.promote_capital_tier(active.hypothesis_id, CapitalEligibilityTier.MICRO_LIVE_ELIGIBLE, "Paper live soak drag <= 0.05R")
        assert active.capital_tier == CapitalEligibilityTier.MICRO_LIVE_ELIGIBLE

    def test_continuous_observation_coordinator(self):
        from instrument.discovery_engine import ContinuousObservationCoordinator
        engine = AutonomousMarketDiscoveryEngine()
        engine.discover_instrument("BTC/USD")
        coordinator = ContinuousObservationCoordinator(engine)

        market_states = {
            "BTC/USD": {
                "structure": "BULLISH_TREND", "zone": "DEMAND", "phase": "CONTINUATION",
                "htf_bias": "BULLISH", "mtf_valid": True, "ltf_valid": True,
                "destination_r": 4.5, "spread_bps": 2.5, "entry_price": 60000.0,
                "stop_price": 59000.0, "target_price": 64500.0,
            }
        }
        ranked = coordinator.run_continuous_observation_cycle(market_states, {}, {}, [])
        assert len(ranked) == 1
        assert coordinator.cycle_count == 1
        # Opportunity stage achieved
        assert engine.discovered_candidates["BTC/USD"].lifecycle_stage == InstrumentLifecycleStage.OPPORTUNITY

