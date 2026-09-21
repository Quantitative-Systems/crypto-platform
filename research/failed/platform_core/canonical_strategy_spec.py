"""
Quantitative Crypto Platform (QCP) — Canonical Strategy Specification.

Machine-readable, strategy-agnostic specification contract. Eliminates hardcoded
defaults and connects Research discovery to Production qualification, Paper execution,
and Telemetry attribution.
"""

from dataclasses import dataclass, field, asdict
import json
from typing import Dict, Any, Optional
from platform_core.canonical_strategy_registry import StrategyLifecycleState


@dataclass
class CanonicalStrategySpec:
    """
    Authoritative machine-readable strategy contract for QCP.
    All strategies across all alpha families (Directional, Relative Value,
    Arbitrage, Market Making, Microstructure, ML) must serialize to this contract.
    """
    strategy_id: str
    family_id: str
    family_name: str
    symbol: str
    timeframe_set: int
    timeframes: Dict[str, str]  # e.g. {"HTF": "1W", "MTF": "1D", "LTF": "4H"}
    parameters: Dict[str, Any]  # e.g. {"tp_r": 2.5, "atr_mult": 1.5, "ema_len": 21, "donchian_len": 10}
    rules: Dict[str, Any]       # Explicit rule definitions (entry, exit, trailing, filters)
    risk_policy: Dict[str, Any] = field(default_factory=lambda: {
        "risk_pct": 0.006,
        "max_risk_pct": 0.01,
        "friction_adjusted": True,
        "collision_policy": "ADVERSE_FIRST",
    })
    lifecycle_state: StrategyLifecycleState = StrategyLifecycleState.RESEARCH
    notes: Optional[str] = None
    provenance: Dict[str, Any] = field(default_factory=lambda: {
        "platform": "QCP",
        "version": "1.0.0",
        "source": "discovery_lab",
    })

    def to_dict(self) -> Dict[str, Any]:
        """Convert spec to JSON-serializable dictionary."""
        d = asdict(self)
        d["lifecycle_state"] = self.lifecycle_state.value if isinstance(self.lifecycle_state, StrategyLifecycleState) else str(self.lifecycle_state)
        return d

    def to_json(self, indent: int = 2) -> str:
        """Serialize spec to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CanonicalStrategySpec":
        """Reconstruct spec from dictionary."""
        state_str = data.get("lifecycle_state", StrategyLifecycleState.RESEARCH.value)
        try:
            state = StrategyLifecycleState(state_str)
        except ValueError:
            state = StrategyLifecycleState.RESEARCH

        return cls(
            strategy_id=data["strategy_id"],
            family_id=data["family_id"],
            family_name=data["family_name"],
            symbol=data["symbol"],
            timeframe_set=int(data["timeframe_set"]),
            timeframes=dict(data.get("timeframes", {})),
            parameters=dict(data.get("parameters", {})),
            rules=dict(data.get("rules", {})),
            risk_policy=dict(data.get("risk_policy", {})),
            lifecycle_state=state,
            notes=data.get("notes"),
            provenance=dict(data.get("provenance", {})),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "CanonicalStrategySpec":
        """Reconstruct spec from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def validate(self) -> bool:
        """Validates that all required fields and invariants are present."""
        if not self.strategy_id or not self.family_id:
            raise ValueError("strategy_id and family_id are required")
        if not self.symbol:
            raise ValueError("symbol is required")
        if not self.timeframes or "LTF" not in self.timeframes:
            raise ValueError("timeframes dict must at least define 'LTF'")
        if not self.parameters:
            raise ValueError("parameters dict cannot be empty")
        return True


def create_fam07_spec(
    symbol: str = "SOLUSDT",
    timeframe_set: int = 2,
    lifecycle_state: StrategyLifecycleState = StrategyLifecycleState.RESEARCH,
    notes: Optional[str] = None,
) -> CanonicalStrategySpec:
    """
    Factory creating canonical specification for Family 7: Multi-Timeframe Continuation.
    Default Set 2: HTF=1W, MTF=1D, LTF=4H.

    IMPORTANT (F-04 fix): lifecycle_state defaults to RESEARCH (not QUALIFIED_ROBUST).
    Any caller promoting this spec to a higher lifecycle state must pass the state
    explicitly with a documented rationale.
    """
    tf_mapping = {
        1: {"HTF": "1M", "MTF": "1W", "LTF": "1D"},
        2: {"HTF": "1W", "MTF": "1D", "LTF": "4H"},
        3: {"HTF": "1D", "MTF": "4H", "LTF": "1H"},
        4: {"HTF": "4H", "MTF": "1H", "LTF": "15m"},
    }
    timeframes = tf_mapping.get(timeframe_set, {"HTF": "1W", "MTF": "1D", "LTF": "4H"})
    clean_sym = symbol.replace("/", "").replace("_", "")

    strategy_id = f"FAM-07-MTFCONT_{clean_sym}_Set{timeframe_set}"

    params = {
        "tp_r": 2.5,
        "atr_mult": 1.5,
        "atr_period": 14,
        "ema_len": 21,
        "donchian_len": 10,
        "direction": "BOTH",
    }

    rules = {
        "entry_long": "HTF_close > HTF_EMA(21) AND MTF_close > MTF_EMA(21) AND LTF_close > LTF_Donchian_Upper(10)",
        "entry_short": "HTF_close < HTF_EMA(21) AND MTF_close < MTF_EMA(21) AND LTF_close < LTF_Donchian_Lower(10)",
        "stop_loss": "LTF_ATR(14) * 1.5",
        "take_profit": "Entry +/- (Risk * 2.5)",
        "collision_policy": "ADVERSE_FIRST",
        "same_bar_confirmation": "CLOSED_CANDLES_ONLY",
    }

    return CanonicalStrategySpec(
        strategy_id=strategy_id,
        family_id="FAM-07-MTFCONT",
        family_name="Multi-Timeframe Continuation",
        symbol=symbol,
        timeframe_set=timeframe_set,
        timeframes=timeframes,
        parameters=params,
        rules=rules,
        lifecycle_state=lifecycle_state,
        notes=notes,
    )
