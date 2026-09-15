"""
Quantitative Crypto Platform (QCP) — Alpha Universe Extensible Research Architecture.

Establishes formal mathematical and architectural interfaces for all current and
future quantitative alpha families across:
1. Directional Alpha (Trend, Momentum, Breakout, Mean Reversion)
2. Relative Value Alpha (Statistical Arbitrage, Pairs, Cointegration)
3. Arbitrage Alpha (Cross-Exchange, Spot/Perp Basis, Funding Rate, Triangular)
4. Market Making & Liquidity Provision (Inventory-Aware, Adaptive Spread)
5. Microstructure Alpha (Order-Book Imbalance, Trade-Flow Prediction)
6. Machine Learning / Black-Box Alpha (Strict baseline comparison, meta-labeling)
7. High-Frequency Trading Simulation Contract (Tick/L2, Queue Position, Latency)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone


class AlphaFamilyType(str, Enum):
    DIRECTIONAL = "DIRECTIONAL"
    RELATIVE_VALUE = "RELATIVE_VALUE"
    ARBITRAGE = "ARBITRAGE"
    MARKET_MAKING = "MARKET_MAKING"
    MICROSTRUCTURE = "MICROSTRUCTURE"
    MACHINE_LEARNING = "MACHINE_LEARNING"
    HIGH_FREQUENCY = "HIGH_FREQUENCY"


@dataclass
class AlphaSignal:
    """Universal alpha signal payload emitted by any alpha model."""
    strategy_id: str
    family_type: AlphaFamilyType
    timestamp: int
    target_asset: str
    action: str                        # "BUY", "SELL", "QUOTE", "REBALANCE", "HOLD"
    target_weight: float               # Sizing weight or units
    expected_alpha_r: float            # Anticipated edge in R or basis points
    expected_holding_duration_s: int   # Expected alpha half-life in seconds
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAlphaModel(ABC):
    """Abstract base contract for all QCP quantitative alpha strategies."""

    def __init__(self, strategy_id: str, family_type: AlphaFamilyType):
        self.strategy_id = strategy_id
        self.family_type = family_type

    @abstractmethod
    def generate_signals(self, market_data: Dict[str, Any]) -> List[AlphaSignal]:
        """Consumes market state or book events and produces actionable signals."""
        pass

    @abstractmethod
    def get_parameter_spec(self) -> Dict[str, Any]:
        """Returns machine-readable parameter specification."""
        pass


# =============================================================================
# 1. ARBITRAGE & MARKET-NEUTRAL ECONOMICS
# =============================================================================

@dataclass
class ArbitrageEconomicModel:
    """
    Evaluates actionable net executable arbitrage after all real-world frictions:
    fees, spreads, slippage, transfer costs, funding, latency, and counterparty risk.
    """
    venue_a: str
    venue_b: str
    gross_spread_bps: float
    taker_fee_a_bps: float = 5.0
    taker_fee_b_bps: float = 5.0
    half_spread_a_bps: float = 2.0
    half_spread_b_bps: float = 2.0
    expected_slippage_bps: float = 4.0
    transfer_cost_usd: float = 1.0
    funding_drag_bps: float = 0.0
    execution_latency_ms: float = 50.0

    def calculate_net_spread_bps(self, notional_usd: float = 10000.0) -> Dict[str, float]:
        """Calculates executable net edge after all friction factors."""
        transfer_bps = (self.transfer_cost_usd / notional_usd) * 10000.0
        total_friction_bps = (
            self.taker_fee_a_bps +
            self.taker_fee_b_bps +
            self.half_spread_a_bps +
            self.half_spread_b_bps +
            self.expected_slippage_bps +
            self.funding_drag_bps +
            transfer_bps
        )
        net_spread_bps = self.gross_spread_bps - total_friction_bps
        is_actionable = net_spread_bps >= 5.0  # Minimum 5 bps net edge required

        return {
            "gross_spread_bps": round(self.gross_spread_bps, 2),
            "total_friction_bps": round(total_friction_bps, 2),
            "net_spread_bps": round(net_spread_bps, 2),
            "transfer_bps": round(transfer_bps, 2),
            "is_actionable": is_actionable,
        }


# =============================================================================
# 2. MACHINE LEARNING / BLACK-BOX MODEL CONTRACT
# =============================================================================

@dataclass
class MLBaselineComparison:
    """
    Enforces that every ML / black-box model must compete against simpler baselines:
    linear model, simple rule-based, and random control.
    """
    model_name: str
    ml_test_expectancy_r: float
    linear_baseline_expectancy_r: float
    rule_baseline_expectancy_r: float
    random_control_expectancy_r: float

    def passes_qualification(self, min_excess_edge_r: float = 0.05) -> Tuple[bool, str]:
        """Verifies ML model genuinely outperforms simple baselines after costs."""
        if self.ml_test_expectancy_r <= self.rule_baseline_expectancy_r + min_excess_edge_r:
            return False, f"ML model edge ({self.ml_test_expectancy_r:.3f}R) does not beat rule baseline ({self.rule_baseline_expectancy_r:.3f}R + {min_excess_edge_r:.3f}R margin)."
        if self.ml_test_expectancy_r <= self.linear_baseline_expectancy_r:
            return False, f"ML model does not beat linear baseline ({self.linear_baseline_expectancy_r:.3f}R)."
        return True, "ML model demonstrates statistically significant excess edge over all baselines."


# =============================================================================
# 3. HIGH-FREQUENCY SIMULATION CONTRACT
# =============================================================================

@dataclass
class HFTSimulationContract:
    """
    Interface specifying microstructural inputs required for institutional HFT research.
    Prevents coarse bar-based backtesting from masquerading as HFT.
    """
    tick_level_data_available: bool = False
    order_book_depth_levels: int = 0
    event_timestamp_resolution: str = "MICROSECOND"
    queue_position_model_enabled: bool = False
    maker_taker_fee_structure: Dict[str, float] = field(default_factory=lambda: {
        "maker_rebate_bps": -0.5,
        "taker_fee_bps": 2.0,
    })
    order_latency_roundtrip_ms: float = 15.0
    adverse_selection_alpha_decay_ms: float = 100.0

    def validate_hft_eligibility(self) -> Tuple[bool, List[str]]:
        """Validates if current research environment meets HFT simulation standards."""
        reasons = []
        if not self.tick_level_data_available:
            reasons.append("Tick-level / L2 order-book data is absent.")
        if self.order_book_depth_levels < 5:
            reasons.append("Order book depth levels < 5.")
        if not self.queue_position_model_enabled:
            reasons.append("Queue position and adverse selection simulation is disabled.")

        eligible = len(reasons) == 0
        return eligible, reasons
