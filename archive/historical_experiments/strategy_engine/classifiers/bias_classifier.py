from market_intelligence.primitives import MarketStatePayload, TrendDirection
from strategy_engine.contracts.trade_plan import DirectionalPermission

class BiasClassifier:
    """
    Translates HTF Market State into a pure DirectionalPermission.
    """
    
    @staticmethod
    def evaluate(htf_payload: MarketStatePayload) -> DirectionalPermission:
        trend = htf_payload.trend_state
        phase = htf_payload.phase_state
        phase_str = str(phase) if phase is not None else ""
        
        is_bullish = (trend == TrendDirection.BULLISH) or ("BULLISH" in str(trend))
        is_bearish = (trend == TrendDirection.BEARISH) or ("BEARISH" in str(trend))

        if is_bullish:
            if any(p in phase_str for p in ("EXPANSION", "PULLBACK", "COMPRESSION", "CONTINUATION")):
                return DirectionalPermission.PERMIT_LONG
            elif any(p in phase_str for p in ("DISTRIBUTION", "REVERSAL")):
                return DirectionalPermission.NO_TRADE
                
        elif is_bearish:
            if any(p in phase_str for p in ("EXPANSION", "PULLBACK", "COMPRESSION", "CONTINUATION")):
                return DirectionalPermission.PERMIT_SHORT
            elif any(p in phase_str for p in ("ACCUMULATION", "REVERSAL")):
                return DirectionalPermission.NO_TRADE
                
        return DirectionalPermission.NO_TRADE
