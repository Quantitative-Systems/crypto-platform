"""
QCP Timeframe Sets — Canonical Definitions (v1.0.0)

Six distinct multi-timeframe execution styles covering the full
spectrum from Macro Investing to Micro Scalping.

Each set: HTF (bias) → MTF (setup) → LTF (entry/execution).
Single source of truth for all experiment runners and the research governor.
"""

from typing import Dict, List

TIMEFRAME_SETS_VERSION = "1.0.0"

TIMEFRAME_SETS: Dict[str, Dict] = {
    "SET_1": {
        "name": "Macro Investing",
        "htf": "1M", "mtf": "1W", "ltf": "1D",
        "description": "Monthly bias, weekly setup, daily entry. Institutional positioning.",
        "typical_holding": "Weeks to months",
        "news_impact": "LOW",
        "min_trade_count": 15,
        "data_depth_years": 4,
        "enabled": True,
    },
    "SET_2": {
        "name": "Swing Trading",
        "htf": "1W", "mtf": "1D", "ltf": "4h",
        "description": "Weekly bias, daily setup, 4h entry. Core QCP swing style.",
        "typical_holding": "2–14 days",
        "news_impact": "MEDIUM",
        "min_trade_count": 20,
        "data_depth_years": 3,
        "enabled": True,
    },
    "SET_3": {
        "name": "Position Trading",
        "htf": "1D", "mtf": "4h", "ltf": "1h",
        "description": "Daily bias, 4h setup, 1h entry. Phase C/D baseline set.",
        "typical_holding": "1–5 days",
        "news_impact": "MEDIUM",
        "min_trade_count": 20,
        "data_depth_years": 2,
        "enabled": True,
    },
    "SET_4": {
        "name": "Intraday Momentum",
        "htf": "4h", "mtf": "1h", "ltf": "15m",
        "description": "4h bias, 1h setup, 15m entry. High-frequency intraday.",
        "typical_holding": "2–24 hours",
        "news_impact": "HIGH",
        "min_trade_count": 30,
        "data_depth_years": 2,
        "enabled": True,
    },
    "SET_5": {
        "name": "Scalping",
        "htf": "1h", "mtf": "15m", "ltf": "5m",
        "description": "1h bias, 15m setup, 5m entry. Maker execution critical.",
        "typical_holding": "15 min–2 hours",
        "news_impact": "VERY_HIGH",
        "min_trade_count": 40,
        "data_depth_years": 1,
        "enabled": True,
    },
    "SET_6": {
        "name": "Micro Scalping",
        "htf": "15m", "mtf": "5m", "ltf": "1m",
        "description": "15m bias, 5m setup, 1m entry. Ultra-high frequency. Microstructure noise caution.",
        "typical_holding": "1–30 minutes",
        "news_impact": "VERY_HIGH",
        "min_trade_count": 60,
        "data_depth_years": 1,
        "enabled": True,
        "research_flag": "MICROSTRUCTURE_NOISE_CAUTION",
    },
}


def get_set(set_id: str) -> Dict:
    if set_id not in TIMEFRAME_SETS:
        raise ValueError(f"Unknown timeframe set: {set_id}. Valid: {list(TIMEFRAME_SETS.keys())}")
    return TIMEFRAME_SETS[set_id]


def get_enabled_sets() -> List[str]:
    return [k for k, v in TIMEFRAME_SETS.items() if v.get("enabled", True)]


def get_timeframes(set_id: str) -> Dict[str, str]:
    s = get_set(set_id)
    return {"htf": s["htf"], "mtf": s["mtf"], "ltf": s["ltf"]}


def get_min_trade_count(set_id: str) -> int:
    return get_set(set_id)["min_trade_count"]


def get_all_set_ids() -> List[str]:
    return list(TIMEFRAME_SETS.keys())


def describe_all() -> str:
    lines = ["QCP Timeframe Sets v" + TIMEFRAME_SETS_VERSION, "=" * 64]
    for sid, cfg in TIMEFRAME_SETS.items():
        lines.append(
            f"  {sid}  [{cfg['name']:20s}]  "
            f"HTF={cfg['htf']:3s} / MTF={cfg['mtf']:3s} / LTF={cfg['ltf']:3s}  "
            f"Hold: {cfg['typical_holding']}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    print(describe_all())
