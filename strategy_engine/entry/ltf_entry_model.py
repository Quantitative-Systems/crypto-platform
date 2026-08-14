from market_intelligence.primitives import MarketStatePayload

class LTFEntryModel:
    """
    Evaluates whether the LTF single-candle snapshot contains a valid micro-trigger.
    Requires:
    1. A liquidity sweep in the required direction.
    2. Displacement confirmed.
    """
    
    @staticmethod
    def evaluate(ltf_payload: MarketStatePayload, req_event_dir: str) -> bool:
        # 1. Sweep check
        ltf_all_events = ltf_payload.events
        sweeps = [
            e for e in ltf_all_events 
            if "LIQUIDITY_SWEEP" in str(e.event_type) and req_event_dir in str(getattr(e, 'direction', None) or (e.metadata.get('direction', '') if hasattr(e, 'metadata') else ''))
        ]
        
        if not sweeps:
            return False
            
        # 2. Displacement check
        scorecard = ltf_payload.scorecard or {}
        reasons = scorecard.get("reason_codes", [])
        
        if "DISPLACEMENT_CONFIRMED" not in reasons:
            return False
            
        return True
