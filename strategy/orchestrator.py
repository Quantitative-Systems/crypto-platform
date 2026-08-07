"""
Product 01: Crypto Platform - Master Strategy Orchestrator
Executes full 5-gate pipeline with Confluence Quality Scoring and strict TP/SL mathematical orientation.
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
    strategy_type: str
    entry_price: float
    stop_loss_price: float
    target_tp_price: float
    position_size_units: float
    dollar_risk_usd: float
    reward_to_risk_ratio: float
    confluence_score: float
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
        risk_pct: float = 0.01,
        min_confluence_score: float = 60.0
    ) -> TradePlan:
        """Executes 5-gate pipeline and evaluates 0-100 Confluence Quality Score."""
        symbol = htf_state.symbol

        # Gate 1: HTF Bias & Target Evaluation
        htf_res = HTFBiasEngine.evaluate_bias(htf_state)
        if not htf_res.is_valid or not htf_res.target_tp_price:
            return TradePlan(
                symbol=symbol, action="NONE", strategy_type="NONE", entry_price=0.0,
                stop_loss_price=0.0, target_tp_price=0.0, position_size_units=0.0,
                dollar_risk_usd=0.0, reward_to_risk_ratio=0.0, confluence_score=0.0,
                status="REJECTED", reason=f"Gate 1 Fail: {htf_res.rejection_reason}"
            )

        # Gate 2: Strategy Routing
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
                dollar_risk_usd=0.0, reward_to_risk_ratio=0.0, confluence_score=0.0,
                status="REJECTED", reason=f"Gate 2 Fail ({strategy_type}): {strat_res.reason}"
            )

        mtf_setup_obj = MTFSetupResult(
            is_aligned=True,
            strategy_type=strategy_type,
            active_mtf_keyzone=strat_res.mtf_keyzone
        )

        # Gate 3: LTF Entry Trigger
        ltf_res = LTFTriggerEngine.evaluate_entry(ltf_state, latest_candle, mtf_setup_obj, htf_res.bias)
        if not ltf_res.is_triggered:
            return TradePlan(
                symbol=symbol, action="NONE", strategy_type=strategy_type, entry_price=0.0,
                stop_loss_price=0.0, target_tp_price=0.0, position_size_units=0.0,
                dollar_risk_usd=0.0, reward_to_risk_ratio=0.0, confluence_score=0.0,
                status="REJECTED", reason=f"Gate 3 Fail: {ltf_res.trigger_reason}"
            )

        action = "BUY" if htf_res.bias == TrendDirection.BULLISH else "SELL"
        entry_price = ltf_res.entry_price
        stop_loss = ltf_res.stop_loss_price
        target_tp = htf_res.target_tp_price

        # Directional Mathematical Check
        if action == "BUY" and not (target_tp > entry_price > stop_loss):
            return TradePlan(
                symbol=symbol, action="NONE", strategy_type=strategy_type, entry_price=entry_price,
                stop_loss_price=stop_loss, target_tp_price=target_tp, position_size_units=0.0,
                dollar_risk_usd=0.0, reward_to_risk_ratio=0.0, confluence_score=0.0,
                status="REJECTED", reason=f"Direction Error: BUY requires TP ({target_tp:.2f}) > Entry ({entry_price:.2f}) > SL ({stop_loss:.2f})"
            )

        if action == "SELL" and not (target_tp < entry_price < stop_loss):
            return TradePlan(
                symbol=symbol, action="NONE", strategy_type=strategy_type, entry_price=entry_price,
                stop_loss_price=stop_loss, target_tp_price=target_tp, position_size_units=0.0,
                dollar_risk_usd=0.0, reward_to_risk_ratio=0.0, confluence_score=0.0,
                status="REJECTED", reason=f"Direction Error: SELL requires TP ({target_tp:.2f}) < Entry ({entry_price:.2f}) < SL ({stop_loss:.2f})"
            )

        # Confluence Quality Score Calculation (0 - 100)
        score = 40.0  # Baseline score for Gate 1-3 alignment
        if mtf_state.last_event:
            score += 20.0  # Recent structural BOS/CHOCH on MTF
        if strat_res.mtf_keyzone and not strat_res.mtf_keyzone.is_mitigated:
            score += 20.0  # Fresh unmitigated KeyZone score
        if ltf_state.last_event:
            score += 20.0  # LTF displacement confirmation

        if score < min_confluence_score:
            return TradePlan(
                symbol=symbol, action="NONE", strategy_type=strategy_type, entry_price=entry_price,
                stop_loss_price=stop_loss, target_tp_price=target_tp, position_size_units=0.0,
                dollar_risk_usd=0.0, reward_to_risk_ratio=0.0, confluence_score=score,
                status="REJECTED", reason=f"Confluence Score ({score:.1f}/100) below minimum {min_confluence_score:.1f} floor."
            )

        # Gate 4: Math-Only Risk Firewall
        risk_res = RiskEngine.validate_trade_risk(
            account_balance=account_balance,
            entry_price=entry_price,
            stop_loss_price=stop_loss,
            target_tp_price=target_tp,
            risk_pct=risk_pct,
            min_rr_floor=4.0
        )

        if not risk_res.is_approved:
            return TradePlan(
                symbol=symbol, action="NONE", strategy_type=strategy_type,
                entry_price=entry_price, stop_loss_price=stop_loss,
                target_tp_price=target_tp, position_size_units=0.0,
                dollar_risk_usd=0.0, reward_to_risk_ratio=risk_res.reward_to_risk_ratio,
                confluence_score=score, status="REJECTED",
                reason=f"Gate 4 Fail: {risk_res.rejection_reason}"
            )

        # Gate 5: Approved Trade Plan Creation
        return TradePlan(
            symbol=symbol,
            action=action,
            strategy_type=strategy_type,
            entry_price=entry_price,
            stop_loss_price=stop_loss,
            target_tp_price=target_tp,
            position_size_units=risk_res.position_size_units,
            dollar_risk_usd=risk_res.dollar_risk_usd,
            reward_to_risk_ratio=risk_res.reward_to_risk_ratio,
            confluence_score=score,
            status="APPROVED",
            reason=f"All Gates Cleared (Score: {score:.1f}/100 | {strategy_type})."
        )