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
from strategy_engine.hypotheses.unified_strategy import UnifiedStrategy
from strategy_engine.lifecycle.candidate_tracker import CandidateTracker, CandidateSetup
from strategy_engine.lifecycle.active_trade_manager import ActiveTradeManager
from strategy_engine.news.news_provider import NewsProvider, NullNewsProvider


def get_max_lifespan_seconds(mtf_timeframe: str) -> int:
    mtf_upper = str(mtf_timeframe).upper()
    if "15M" in mtf_upper or "15MIN" in mtf_upper:
        return 12 * 3600 # 12 hours
    elif "1H" in mtf_upper:
        return 48 * 3600 # 48 hours
    elif "4H" in mtf_upper:
        return 7 * 86400 # 7 days
    elif "1D" in mtf_upper or "D" in mtf_upper:
        return 21 * 86400 # 21 days
    elif "1W" in mtf_upper or "W" in mtf_upper:
        return 60 * 86400 # 60 days
    elif "1M" in mtf_upper or "MO" in mtf_upper:
        return 180 * 86400 # 180 days
    else:
        return 7 * 86400


class StrategyCoordinator:
    """
    Stateful orchestrator coordinating candidates across multiple candles and managing active trades.
    """
    
    def __init__(
        self,
        news_provider: Optional[NewsProvider] = None,
        enable_mtf_trailing: bool = True,
        enable_profit_lock: bool = True,
        lockin_r: float = 1.0,
        giveback_r: float = 0.75,
        regime_filter: Optional[RegimeFilter] = None
    ):
        self.hypotheses = {
            "UNIFIED_STRATEGY": UnifiedStrategy()
        }
        self.candidate_tracker = CandidateTracker()
        self.active_manager = ActiveTradeManager(
            enable_mtf_trailing=enable_mtf_trailing,
            enable_profit_lock=enable_profit_lock,
            lockin_r=lockin_r,
            giveback_r=giveback_r
        )
        self.news_provider = news_provider or NullNewsProvider()
        self.regime_filter = regime_filter
        
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

        if bias != DirectionalPermission.NO_TRADE:
            is_bullish = htf_payload.trend_state == TrendDirection.BULLISH
            
            # --- UNIFIED STRATEGY (HTF KeyZone Interaction) ---
            active = self.candidate_tracker.get_active_candidates(symbol, "UNIFIED_STRATEGY")
            if not active:
                # Check for HTF KeyZone Interaction (Optional for Context)
                htf_interacting_kz = None
                for kz in (htf_payload.keyzones or []):
                    kz_type_str = str(getattr(kz, 'zone_type', ''))
                    if is_bullish and ("BULLISH" not in kz_type_str): continue
                    if (not is_bullish) and ("BEARISH" not in kz_type_str): continue
                    is_mitigated = "MITIGATED" in str(getattr(kz, 'status', ''))
                    high_bound = getattr(kz, 'high_boundary', getattr(kz, 'high', None))
                    low_bound = getattr(kz, 'low_boundary', getattr(kz, 'low', None))
                    price_in_zone = False
                    if high_bound is not None and low_bound is not None:
                        if htf_payload.current_candle:
                            price_in_zone = (htf_payload.current_candle.low <= high_bound and htf_payload.current_candle.high >= low_bound)
                        else:
                            price_in_zone = (low_bound <= htf_payload.current_price <= high_bound)
                    if is_mitigated or price_in_zone:
                        htf_interacting_kz = kz
                        break
                
                # Unconditionally spawn a candidate if bias allows
                new_candidate = CandidateSetup(
                    candidate_id=f"cand_{symbol}_UNIFIED_{ltf_payload.timestamp}",
                    hypothesis_id="UNIFIED_STRATEGY",
                    symbol=symbol,
                    htf=htf_payload.timeframe,
                    mtf=mtf_payload.timeframe,
                    ltf=ltf_payload.timeframe,
                    state=CandidateState.WAIT_MTF_ALIGNMENT,
                    directional_permission=DirectionalPermission.PERMIT_LONG if is_bullish else DirectionalPermission.PERMIT_SHORT,
                    htf_context_id=htf_context.context_id,
                    htf_context_timestamp=htf_context.timestamp,
                    htf_macro_direction=htf_payload.trend_state.value if hasattr(htf_payload.trend_state, 'value') else str(htf_payload.trend_state),
                    htf_phase=str(htf_payload.phase_state),
                    htf_target_price=htf_context.target_anchor_price,
                    htf_keyzone_id=getattr(htf_interacting_kz, 'zone_id', None) if htf_interacting_kz else None,
                    htf_interaction_timestamp=htf_payload.timestamp if htf_interacting_kz else None,
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
