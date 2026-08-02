"""
Product 01: Crypto Platform - Master Strategy Orchestrator
Executes full 5-gate pipeline, routing between Strategy A (Pullback) and Strategy B (Continuation).
"""

from dataclasses import dataclass
from market_intelligence.primitives import MarketStatePayload, Candle, TrendDirection, MarketPhase
from strategy.htf_bias import HTFBiasEngine
from strategy.strategy_a_pullback import StrategyAPullbackEngine
from strategy.strategy_b_continuation import StrategyBContinuationEngine
from strategy.ltf_trigger import LTFTriggerEngine
from strategy.mtf_setup import MTFSetupResult
from risk.risk_engine import RiskEngine


@dataclass
class TradePlan:
    symbol: str
    action: str  # "BUY" or "SELL"
    strategy_type: str  # "PULLBACK_RIDING" or "CONTINUATION_RIDING"
    entry_price: float
    stop_loss_price: float
    target_tp_price: float
    position_size_units: float
    dollar_risk_usd: float
    reward_to_risk_ratio: float
    status: str  # "APPROVED" or "REJECTED"
    reason: str = ""


class StrategyOrchestrator:

    @staticmethod
    def process_pipeline(
        htf_state: MarketStatePayload,
        mtf_state: MarketStatePayload,
        ltf_state: MarketStatePayload,
        latest_candle: Candle,
        account_balance: float = 1000.0,
        risk_pct: float = 0.01
    ) -> TradePlan:
        """Executes full 5-gate pipeline and compiles a deterministic TradePlan."""
        
        symbol = htf_state.symbol

        # Gate 1: HTF Bias & Target Evaluation
        htf_res = HTFBiasEngine.evaluate_bias(htf_state)
        if not htf_res.is_valid or not htf_res.target_tp_price:
            return TradePlan(
                symbol=symbol, action="NONE", strategy_type="NONE", entry_price=0.0,
                stop_loss_price=0.0, target_tp_price=0.0, position_size_units=0.0,
                dollar_risk_usd=0.0, reward_to_risk_ratio=0.0, status="REJECTED",
                reason=f"Gate 1 Fail: {htf_res.rejection_reason}"
            )

        # Gate 2: Route to Strategy A (Pullback Riding) or Strategy B (Continuation Riding)
        if htf_res.expected_phase == MarketPhase.PULLBACK:
            strat_res = StrategyAPullbackEngine.evaluate_pullback_setup(htf_state, mtf_state)
            strategy_type = "PULLBACK_RIDING"
        else:
            strat_res = StrategyBContinuationEngine.evaluate_continuation_setup(htf_state, mtf_state)
            strategy_type = "CONTINUATION_RIDING"

        if not strat_res.is_valid_setup or not strat_res.mtf_keyzone:
            return TradePlan(
                symbol=symbol, action="NONE", strategy_type=strategy_type, entry_price=0.0,
                stop_loss_price=0.0, target_tp_price=0.0, position_size_units=0.0,
                dollar_risk_usd=0.0, reward_to_risk_ratio=0.0, status="REJECTED",
                reason=f"Gate 2 Fail ({strategy_type}): {strat_res.reason}"
            )

        mtf_setup_obj = MTFSetupResult(
            is_aligned=True,
            strategy_type=strategy_type,
            active_mtf_keyzone=strat_res.mtf_keyzone
        )

        # Gate 3: LTF Entry Trigger (Sweep + Displacement Candle Close)
        ltf_res = LTFTriggerEngine.evaluate_entry(ltf_state, latest_candle, mtf_setup_obj, htf_res.bias)
        if not ltf_res.is_triggered:
            return TradePlan(
                symbol=symbol, action="NONE", strategy_type=strategy_type, entry_price=0.0,
                stop_loss_price=0.0, target_tp_price=0.0, position_size_units=0.0,
                dollar_risk_usd=0.0, reward_to_risk_ratio=0.0, status="REJECTED",
                reason=f"Gate 3 Fail: {ltf_res.trigger_reason}"
            )

        # Gate 4: Math-Only Risk Firewall (1.0% Equity Risk & >= 1:4 R:R Floor)
        risk_res = RiskEngine.validate_trade_risk(
            account_balance=account_balance,
            entry_price=ltf_res.entry_price,
            stop_loss_price=ltf_res.stop_loss_price,
            target_tp_price=htf_res.target_tp_price,
            risk_pct=risk_pct,
            min_rr_floor=4.0
        )

        if not risk_res.is_approved:
            return TradePlan(
                symbol=symbol, action="NONE", strategy_type=strategy_type,
                entry_price=ltf_res.entry_price, stop_loss_price=ltf_res.stop_loss_price,
                target_tp_price=htf_res.target_tp_price, position_size_units=0.0,
                dollar_risk_usd=0.0, reward_to_risk_ratio=risk_res.reward_to_risk_ratio,
                status="REJECTED", reason=f"Gate 4 Fail: {risk_res.rejection_reason}"
            )

        action = "BUY" if htf_res.bias == TrendDirection.BULLISH else "SELL"

        # Gate 5: Approved Trade Plan Creation
        return TradePlan(
            symbol=symbol,
            action=action,
            strategy_type=strategy_type,
            entry_price=ltf_res.entry_price,
            stop_loss_price=ltf_res.stop_loss_price,
            target_tp_price=htf_res.target_tp_price,
            position_size_units=risk_res.position_size_units,
            dollar_risk_usd=risk_res.dollar_risk_usd,
            reward_to_risk_ratio=risk_res.reward_to_risk_ratio,
            status="APPROVED",
            reason=f"All 5 Gates Cleared. Trade Plan Executable ({strategy_type})."
        )