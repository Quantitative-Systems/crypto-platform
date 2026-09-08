"""
Product 02 — Strategy Engine: Strategy Coordinator
Stateful orchestrator coordinating candidates across multiple candles and managing active trades.
Integrates HTF Context Engine, Candidate Tracker, Active Trade Manager, and News Filter.
"""

import uuid
from typing import List, Optional
from market_intelligence.primitives import MarketStatePayload, MarketPhase, TrendDirection
from strategy_engine.contracts.trade_plan import TradePlanPayload, DirectionalPermission
from strategy_engine.contracts.strategy_state import CandidateState
from strategy_engine.classifiers.bias_classifier import BiasClassifier
from strategy_engine.classifiers.regime_filter import RegimeFilter
from strategy_engine.context.htf_context_engine import HTFContextEngine, HTFContext
from strategy_engine.hypotheses.base_hypothesis import BaseHypothesis
from strategy_engine.hypotheses.unified_strategy import UnifiedStrategy
from strategy_engine.lifecycle.candidate_tracker import CandidateTracker, CandidateSetup
from strategy_engine.lifecycle.active_trade_manager import ActiveTradeManager
from strategy_engine.news.news_provider import NewsProvider, NullNewsProvider


def get_max_lifespan_seconds(mtf_timeframe: str) -> int:
    """
    Returns max lifespan in seconds for a candidate based on MTF timeframe.
    Strictly disambiguates 1m (minute) vs 1M (month) without substring collisions.
    """
    tf_str = str(mtf_timeframe).strip()
    
    # Exact case-sensitive mappings for ambiguous single-letter suffixes
    exact_map = {
        "1m": 3600,             # 1 hour (60 bars of 1m)
        "1min": 3600,
        "1MIN": 3600,
        "5m": 4 * 3600,         # 4 hours (48 bars of 5m)
        "5min": 4 * 3600,
        "5MIN": 4 * 3600,
        "15m": 12 * 3600,       # 12 hours (48 bars of 15m)
        "15min": 12 * 3600,
        "15MIN": 12 * 3600,
        "1h": 48 * 3600,        # 48 hours (48 bars of 1h)
        "1H": 48 * 3600,
        "60m": 48 * 3600,
        "60min": 48 * 3600,
        "4h": 7 * 86400,        # 7 days (42 bars of 4h)
        "4H": 7 * 86400,
        "240m": 7 * 86400,
        "1d": 21 * 86400,       # 21 days (21 bars of 1d)
        "1D": 21 * 86400,
        "D": 21 * 86400,
        "1day": 21 * 86400,
        "1DAY": 21 * 86400,
        "1w": 60 * 86400,       # 60 days (~8.5 bars of 1w)
        "1W": 60 * 86400,
        "W": 60 * 86400,
        "1week": 60 * 86400,
        "1WEEK": 60 * 86400,
        "1M": 180 * 86400,      # 180 days (6 bars of 1M month)
        "1MO": 180 * 86400,
        "1mo": 180 * 86400,
        "1MONTH": 180 * 86400,
        "1month": 180 * 86400,
        "MO": 180 * 86400,
    }
    
    if tf_str in exact_map:
        return exact_map[tf_str]
        
    tf_upper = tf_str.upper()
    if tf_upper in exact_map:
        return exact_map[tf_upper]
        
    return 7 * 86400


class StrategyCoordinator:
    """
    Stateful orchestrator coordinating candidates across multiple candles and managing active trades.
    """
    
    def __init__(
        self,
        news_provider: Optional[NewsProvider] = None,
        enable_mtf_trailing: bool = True,
        enable_profit_lock: bool = False,
        lockin_r: float = 1.0,
        giveback_r: float = 0.75,
        profit_lock_trigger_r: float = 1.0,
        profit_lock_stop_r: float = 0.10,
        regime_filter: Optional[RegimeFilter] = None,
        htf_context_filter: Optional[str] = None,
        hypothesis: Optional[BaseHypothesis] = None,
        enable_kz_freshness: bool = False,
        max_htf_kz_age_seconds: Optional[int] = None
    ):
        """
        htf_context_filter: when set to "PULLBACK" or "CONTINUATION", candidates
        are only spawned when the HTF phase context matches that expected phase.
        This isolates the two canonical hypotheses:
          HYP_A_PULLBACK_RIDING      -> filter="PULLBACK"
          HYP_B_CONTINUATION_RIDING  -> filter="CONTINUATION"
        """
        self.enable_kz_freshness = enable_kz_freshness
        self.max_htf_kz_age_seconds = max_htf_kz_age_seconds
        if hypothesis is not None:
            self.hypotheses = {hypothesis.hypothesis_id: hypothesis}
        else:
            self.hypotheses = {
                "UNIFIED_STRATEGY": UnifiedStrategy(
                    enable_kz_freshness=enable_kz_freshness,
                    max_htf_kz_age_seconds=max_htf_kz_age_seconds
                )
            }
        self.candidate_tracker = CandidateTracker()
        self.active_manager = ActiveTradeManager(
            enable_mtf_trailing=enable_mtf_trailing,
            enable_profit_lock=enable_profit_lock,
            lockin_r=lockin_r,
            giveback_r=giveback_r,
            profit_lock_trigger_r=profit_lock_trigger_r,
            profit_lock_stop_r=profit_lock_stop_r
        )
        self.news_provider = news_provider or NullNewsProvider()
        self.regime_filter = regime_filter
        self.htf_context_filter = htf_context_filter
        
    def evaluate(
        self,
        htf_payload: MarketStatePayload,
        mtf_payload: MarketStatePayload,
        ltf_payload: MarketStatePayload
    ) -> List[TradePlanPayload]:
        
        trade_plans = []
        symbol = htf_payload.symbol
        
        # 0. Expired Candidates are handled inside the Hypothesis to generate telemetry
        
        # 1. Evaluate Active Trades (MTF Trailing, Profit-Lock, TP, SL)
        exited_trades = self.active_manager.evaluate(htf_payload, mtf_payload, ltf_payload)
        trade_plans.extend(exited_trades)
        
        # 2. Extract HTF Context and Expected Move
        bias = BiasClassifier.evaluate(htf_payload)
        htf_context: HTFContext = HTFContextEngine.evaluate(htf_payload)
        phase_str = str(htf_payload.phase_state) if htf_payload.phase_state is not None else ""
        max_lifespan = get_max_lifespan_seconds(mtf_payload.timeframe)
        
        # Check Alpha Regime Filter
        if self.regime_filter and bias != DirectionalPermission.NO_TRADE:
            regime_dec = self.regime_filter.evaluate(htf_payload)
            if not regime_dec.is_permitted:
                bias = DirectionalPermission.NO_TRADE

        active_hyp_id = next(iter(self.hypotheses.keys())) if self.hypotheses else "UNIFIED_STRATEGY"

        if bias != DirectionalPermission.NO_TRADE:
            is_bullish = htf_payload.trend_state == TrendDirection.BULLISH
            
            # --- Dynamic Hypothesis Candidate Tracking ---
            active = self.candidate_tracker.get_active_candidates(symbol, active_hyp_id)
            if not active:
                # Phase 3: Mandatory Active HTF KeyZone Interaction
                # Price must actively interact with a relevant causal HTF keyzone in the HTF trend direction.
                # Historical mitigation alone must never qualify current price as interacting with a zone.
                htf_interacting_kz = None
                for kz in (htf_payload.keyzones or []):
                    kz_type_str = str(getattr(kz, 'zone_type', ''))
                    status_str = str(getattr(kz, 'status', ''))
                    if "INVALIDATED" in status_str:
                        continue

                    # Direction matching: Bullish keyzone for Long, Bearish keyzone for Short
                    if is_bullish and ("BULLISH" not in kz_type_str):
                        continue
                    if (not is_bullish) and ("BEARISH" not in kz_type_str):
                        continue

                    high_bound = getattr(kz, 'high_boundary', None)
                    if high_bound is None:
                        high_bound = getattr(kz, 'high', None)
                    low_bound = getattr(kz, 'low_boundary', None)
                    if low_bound is None:
                        low_bound = getattr(kz, 'low', None)

                    if high_bound is None or low_bound is None:
                        continue
                    if low_bound > high_bound:
                        low_bound, high_bound = high_bound, low_bound

                    # Active price interaction check: current price or current candle penetrating zone
                    price_in_zone = False
                    if ltf_payload.current_candle:
                        price_in_zone = (ltf_payload.current_candle.low <= high_bound and ltf_payload.current_candle.high >= low_bound)
                    elif htf_payload.current_candle:
                        price_in_zone = (htf_payload.current_candle.low <= high_bound and htf_payload.current_candle.high >= low_bound)
                    else:
                        price_in_zone = (low_bound <= htf_payload.current_price <= high_bound)

                    if price_in_zone:
                        htf_interacting_kz = kz
                        break

                # MANDATORY GATE: If price has not reached a relevant HTF keyzone, NO candidate setup can qualify
                if htf_interacting_kz is not None:
                    htf_ctx_label = "PULLBACK" if ("PULLBACK" in phase_str or (htf_interacting_kz is not None and "PULLBACK" in phase_str)) else "CONTINUATION"
                    context_matches = (self.htf_context_filter is None) or (htf_ctx_label == self.htf_context_filter)

                    if context_matches:
                        # Discover forward structural destination
                        from strategy_engine.context.htf_destination_engine import HTFDestinationEngine
                        dest = HTFDestinationEngine.evaluate(htf_payload, reference_price=ltf_payload.current_price, is_long=is_bullish)
                        target_price = dest.target_price if dest.is_valid else htf_context.target_anchor_price

                        kz_create_ts = getattr(htf_interacting_kz, 'creation_timestamp', None)
                        if (kz_create_ts is None or kz_create_ts == 0) and getattr(htf_interacting_kz, 'zone_id', None):
                            for part in str(htf_interacting_kz.zone_id).split('_'):
                                if part.isdigit() and len(part) >= 9:
                                    kz_create_ts = int(part)
                                    break

                        new_candidate = CandidateSetup(
                            candidate_id=f"cand_{symbol}_{active_hyp_id}_{ltf_payload.timestamp}",
                            hypothesis_id=active_hyp_id,
                            symbol=symbol,
                            htf=htf_payload.timeframe,
                            mtf=mtf_payload.timeframe,
                            ltf=ltf_payload.timeframe,
                            state=CandidateState.WAIT_MTF_ALIGNMENT,
                            directional_permission=DirectionalPermission.PERMIT_LONG if is_bullish else DirectionalPermission.PERMIT_SHORT,
                            htf_context=htf_ctx_label,
                            htf_context_id=htf_context.context_id,
                            htf_context_timestamp=htf_context.timestamp,
                            htf_macro_direction=htf_payload.trend_state.value if hasattr(htf_payload.trend_state, 'value') else str(htf_payload.trend_state),
                            htf_phase=str(htf_payload.phase_state),
                            htf_target_price=target_price,
                            htf_keyzone_id=getattr(htf_interacting_kz, 'zone_id', None),
                            htf_kz_creation_timestamp=kz_create_ts,
                            htf_interaction_timestamp=ltf_payload.timestamp,
                            creation_timestamp=ltf_payload.timestamp,
                            max_lifespan_seconds=max_lifespan
                        )
                        self.candidate_tracker.add_candidate(new_candidate)
                    
        # 3. Progress Active Candidate Setups
        for hyp_id, hypothesis in self.hypotheses.items():
            candidates = self.candidate_tracker.get_active_candidates(symbol, hyp_id)
            for candidate in candidates:
                try:
                    plan = hypothesis.evaluate(candidate, htf_payload, mtf_payload, ltf_payload)
                    
                    if plan:
                        # Check news blackout before finalizing trade plan entry
                        if plan.status == CandidateState.ENTERED.value:
                            is_blackout, news_ev = self.news_provider.is_news_blackout(
                                symbol=symbol,
                                timestamp=ltf_payload.timestamp
                            )
                            if is_blackout:
                                plan.status = CandidateState.REJECTED.value
                                plan.rejection_reason = "REJECT_NEWS_BLACKOUT"
                        
                        trade_plans.append(plan)
                        self.candidate_tracker.remove_candidate(candidate.candidate_id)
                        
                        if plan.status == CandidateState.ENTERED.value:
                            self.active_manager.register_trade(candidate.candidate_id, plan)
                            
                except Exception as e:
                    self.candidate_tracker.remove_candidate(candidate.candidate_id)
                    raise RuntimeError(f"Hypothesis {hyp_id} failed during state evaluation: {str(e)}") from e

        return trade_plans
