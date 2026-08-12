from market_intelligence.primitives import MarketStatePayload, TrendDirection
from market_intelligence.phase_engine import MarketPhase
from strategy_engine.contracts.trade_plan import DirectionalPermission

class BiasClassifier:
    """
    Translates HTF Market State into a pure DirectionalPermission.
    """
    
    @staticmethod
    def evaluate(htf_payload: MarketStatePayload) -> DirectionalPermission:
        trend = htf_payload.trend_state
        phase = htf_payload.phase_state
        
        if trend == TrendDirection.BULLISH:
            if phase in (MarketPhase.EXPANSION, MarketPhase.PULLBACK, MarketPhase.COMPRESSION):
                return DirectionalPermission.PERMIT_LONG
            elif phase in (MarketPhase.DISTRIBUTION, MarketPhase.REVERSAL):
                return DirectionalPermission.NO_TRADE
                
        elif trend == TrendDirection.BEARISH:
            if phase in (MarketPhase.EXPANSION, MarketPhase.PULLBACK, MarketPhase.COMPRESSION):
                return DirectionalPermission.PERMIT_SHORT
            elif phase in (MarketPhase.ACCUMULATION, MarketPhase.REVERSAL):
                return DirectionalPermission.NO_TRADE
                
        return DirectionalPermission.NO_TRADE
