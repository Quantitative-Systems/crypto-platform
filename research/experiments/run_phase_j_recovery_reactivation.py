"""Phase J: Regime Transition, Recovery & Re-Activation Research Engine.

Empirically investigates:
1. Crisis Disorder Detection: How quickly does the system recognize disorder?
2. Stabilization Verification: Does the system recognize when volatility, spreads, and order book depth heal?
3. False Recovery Traps: How often does premature re-entry hit dead-cat bounces vs. staged protection?
4. Recovery Confirmation: Which 5-dimensional combination (Structure, Phase, Volatility, Liquidity, Cross-Market, Positioning) provides sufficient evidence?
5. Post-Crisis Opportunity Recovery: How much of the recovery trend is captured?
6. Re-Entry Risk Frontier: Quantifies early re-entry losses vs. late re-entry opportunity cost.

Evaluates 3 distinct reactivation architectures across 5 major historical crisis-to-recovery cycles (2021-2025):
- Policy A: NAIVE_PREMATURE (Immediate re-entry on first LTF signal at 1.0x)
- Policy B: RIGID_ULTRA_CONSERVATIVE (Excessive defensiveness; wait for full HTF serenity at 1.0x)
- Policy C: AUTONOMOUS_STAGED_PACING (Staged pacing: 0.25x Probe -> 0.50x Confirm -> 1.0x Full, with false-recovery tripwire)

Strict adherence:
The Market Model (Structure / Key Zones / Phase) and Execution Spine remain 100% frozen.
Calibrated Governor from Phase I remains frozen.
"""
from __future__ import annotations

import json
import math
import shutil
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from execution.backtest.engine import CausalBacktestEngine, TradeRecord
from execution.portfolio.risk_governor import PortfolioRiskGovernor
from execution.risk.contracts import (
    DefenseLayerCheck,
    DrawdownTier,
    MarketClarityState,
    ReactivationPolicyComparison,
    ReactivationStage,
    RecoveryConfirmationAudit,
    RiskAction,
    SystemRiskVerdict,
)
from execution.risk.drawdown_governor import DrawdownGovernor
from execution.risk.reactivation_engine import ReactivationEngine
from execution.risk.systemic_risk_governor import SystemicRiskGovernor
from execution.risk.unknown_state_engine import UnknownStateEngine
from market_intelligence.positioning.positioning_engine import (
    FundingState,
    PositioningIntelligenceEngine,
    PositioningSnapshot,
    TrappedState,
)
from market_intelligence.regimes.regime_contracts import (
    CorrelationRegime,
    LiquidityRegime,
    MarketRegimeSnapshot,
    RiskRegime,
    TrendRegime,
    VolatilityRegime,
)
from market_intelligence.regimes.regime_engine import MarketRegimeEngine
from market_model.contracts import MarketPhaseType, MarketState, TrendDirection
from market_model.state_generator import MarketStateGenerator
from research.datasets.causal_history_warehouse import CausalHistoryWarehouse
from research.experiments.discovery_runner import DiscoveryResearchRunner, TIMEFRAME_SETS
from strategy.adaptive.adaptive_engine_v1 import AdaptiveEngineV1

RESULTS_DIR = REPO_ROOT / "research" / "results"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
BRAIN_DIR = Path(r"C:\Users\nares\.gemini\antigravity-ide\brain\ec7e6b79-e0f8-412d-aa20-d7a400d73b1d")

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

ASSETS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
ANCHOR_SET = "SET_2"  # 1W -> 1D -> 4H


@dataclass
class PostCrisisRecoveryEpisode:
    """Historical post-crisis stabilization and recovery window specification."""
    episode_id: str
    name: str
    crisis_shock_start_ts: int
    crisis_shock_end_ts: int
    recovery_window_start_ts: int
    recovery_window_end_ts: int
    macro_catalyst: str
    crisis_trough_price: float
    recovery_peak_price: float
    description: str


# 5 Major Post-Crisis Recovery Cycles (2021-2025)
POST_CRISIS_EPISODES: List[PostCrisisRecoveryEpisode] = [
    PostCrisisRecoveryEpisode(
        episode_id="PCE_01_POST_MAY_2021",
        name="Post-May 2021 Flash Crash Recovery Cycle",
        crisis_shock_start_ts=1620604800000,    # 2021-05-10
        crisis_shock_end_ts=1623715200000,      # 2021-06-15 (Crash $58k -> $30k)
        recovery_window_start_ts=1623715200000, # 2021-06-15
        recovery_window_end_ts=1636934400000,   # 2021-11-15 (Impulse to $69k ATH)
        macro_catalyst="China mining ban flush absorption & Taproot upgrade anticipation",
        crisis_trough_price=28800.0,
        recovery_peak_price=69000.0,
        description="Bitcoin tests $30k base multiple times before launching explosive 139% recovery to cycle ATH.",
    ),
    PostCrisisRecoveryEpisode(
        episode_id="PCE_02_POST_FTX_COLLAPSE",
        name="Post-FTX Insolvency & Cycle Bottom Recovery Cycle",
        crisis_shock_start_ts=1667606400000,    # 2022-11-05
        crisis_shock_end_ts=1672444800000,      # 2022-12-31 (Crash $21k -> $15.5k)
        recovery_window_start_ts=1672531200000, # 2023-01-01
        recovery_window_end_ts=1681516800000,   # 2023-04-15 (Relief breakout to $31k)
        macro_catalyst="Exhaustion of forced liquidator selling & global liquidity pivot",
        crisis_trough_price=15476.0,
        recovery_peak_price=31000.0,
        description="Historical pessimism and liquidity vacuum transition into secular accumulation, doubling price to $31k.",
    ),
    PostCrisisRecoveryEpisode(
        episode_id="PCE_03_POST_SVB_PANIC",
        name="Post-SVB / USDC Depeg Relief Rally Cycle",
        crisis_shock_start_ts=1678233600000,    # 2023-03-08
        crisis_shock_end_ts=1678665600000,      # 2023-03-13 (USDC depeg, BTC drops to $19.8k)
        recovery_window_start_ts=1678665600000, # 2023-03-13
        recovery_window_end_ts=1689379200000,   # 2023-07-15 (Breakout to $31.8k)
        macro_catalyst="Federal Reserve BTFP emergency facility & systemic banking bailouts",
        crisis_trough_price=19549.0,
        recovery_peak_price=31818.0,
        description="Emergency liquidity injection triggers violent short squeeze and 62% recovery rally.",
    ),
    PostCrisisRecoveryEpisode(
        episode_id="PCE_04_POST_AUG_2023_FLASH_CRASH",
        name="Post-August 2023 Flush & Spot ETF Expansion Cycle",
        crisis_shock_start_ts=1692144000000,    # 2023-08-16
        crisis_shock_end_ts=1694736000000,      # 2023-09-15 (Flush from $29k -> $25k)
        recovery_window_start_ts=1694736000000, # 2023-09-15
        recovery_window_end_ts=1711929600000,   # 2024-04-01 (Expansion to $73.7k ATH)
        macro_catalyst="Grayscale court victory & SEC approval of US Spot Bitcoin ETFs",
        crisis_trough_price=24900.0,
        recovery_peak_price=73750.0,
        description="Prolonged low-vol base at $25k transitions into the most powerful institutional expansion wave in crypto history.",
    ),
    PostCrisisRecoveryEpisode(
        episode_id="PCE_05_POST_YEN_UNWIND",
        name="Post-August 2024 Yen Carry Unwind Recovery Cycle",
        crisis_shock_start_ts=1722470400000,    # 2024-08-01
        crisis_shock_end_ts=1723248000000,      # 2024-08-10 (VIX 65, BTC $49.2k wick)
        recovery_window_start_ts=1723248000000, # 2024-08-10
        recovery_window_end_ts=1731628800000,   # 2024-11-15 (Recovery past $75k)
        macro_catalyst="Bank of Japan rate hike pause & US election clarity expansion",
        crisis_trough_price=49120.0,
        recovery_peak_price=76000.0,
        description="Extreme macro correlation shock rapidly normalizes into sustained continuation to fresh record highs.",
    ),
]


def _calc_stats(trades: List[TradeRecord], initial_capital: float = 100_000.0) -> Dict[str, Any]:
    if not trades:
        return {
            "total_trades": 0, "net_r": 0.0, "expectancy_r": 0.0,
            "win_rate": 0.0, "profit_factor": 0.0, "max_drawdown_pct": 0.0,
            "max_consecutive_losses": 0, "var_95_r": 0.0, "cvar_95_tail_loss_r": 0.0,
            "risk_of_ruin_pct": 0.0, "final_equity_usd": initial_capital,
        }
    r_list = [t.realized_r for t in trades]
    equity_curve = [initial_capital]
    for r in r_list:
        equity_curve.append(equity_curve[-1] + r * (initial_capital * 0.01))

    peak = equity_curve[0]
    mdd_pct = 0.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak * 100.0 if peak > 0 else 0.0
        if dd > mdd_pct:
            mdd_pct = dd

    wins = [r for r in r_list if r > 0]
    losses = [r for r in r_list if r < 0]
    win_rate = len(wins) / len(r_list) if r_list else 0.0

    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 1e-6
    pf = gross_profit / gross_loss
    exp_r = np.mean(r_list) if r_list else 0.0

    var_95_r = float(np.percentile(r_list, 5)) if len(r_list) >= 5 else (min(r_list) if r_list else 0.0)
    cvar_tail = [r for r in r_list if r <= var_95_r]
    cvar_95_r = float(np.mean(cvar_tail)) if cvar_tail else var_95_r

    return {
        "total_trades": len(trades),
        "net_r": round(float(np.sum(r_list)), 2),
        "expectancy_r": round(exp_r, 3),
        "win_rate": round(win_rate * 100, 1),
        "profit_factor": round(pf, 2),
        "max_drawdown_pct": round(mdd_pct, 2),
        "var_95_r": round(var_95_r, 2),
        "cvar_95_tail_loss_r": round(cvar_95_r, 2),
        "final_equity_usd": round(equity_curve[-1], 2),
    }


def run_phase_j_research():
    print("=" * 80)
    print("PHASE J -- REGIME TRANSITION, RECOVERY & RE-ACTIVATION RESEARCH")
    print("=" * 80)
    start_time = time.time()

    runner = DiscoveryResearchRunner()
    history_wh = CausalHistoryWarehouse()
    regime_engine = MarketRegimeEngine()
    pos_engine = PositioningIntelligenceEngine()
    tfs = TIMEFRAME_SETS[ANCHOR_SET]

    # Step 1: Load Market Data
    print("\n[Step 1] Loading multi-year bar series across BTC, ETH, SOL...", flush=True)
    asset_data: Dict[str, Any] = {}
    for sym in ASSETS:
        h_data = runner.load_series_arrays(sym, tfs["htf"])
        m_data = runner.load_series_arrays(sym, tfs["mtf"])
        l_data = runner.load_series_arrays(sym, tfs["ltf"])
        if not h_data or not m_data or not l_data:
            continue
        overlap_start = max(h_data["timestamps"][0], m_data["timestamps"][0], l_data["timestamps"][0])
        overlap_end = min(h_data["timestamps"][-1], m_data["timestamps"][-1], l_data["timestamps"][-1])
        ltf_mask = (l_data["timestamps"] >= overlap_start) & (l_data["timestamps"] <= overlap_end)
        ltf_idx = np.where(ltf_mask)[0]
        if len(ltf_idx) < 30:
            continue
        asset_data[sym] = {
            "h_data": h_data, "m_data": m_data, "l_data": l_data,
            "sub_ts": l_data["timestamps"][ltf_idx],
            "sub_o": l_data["opens"][ltf_idx],
            "sub_h": l_data["highs"][ltf_idx],
            "sub_l": l_data["lows"][ltf_idx],
            "sub_c": l_data["closes"][ltf_idx],
            "sub_v": l_data["volumes"][ltf_idx],
            "ltf_idx": ltf_idx,
        }
        print(f"  {sym}: {len(ltf_idx)} bars aligned.", flush=True)

    backtest_engine = CausalBacktestEngine(taker_fee_bps=5.0, slippage_bps=2.0)

    # Step 2: Signal Generation from Frozen Market Model
    print("\n[Step 2] Scanning technical signals and contextual states...", flush=True)
    candidate_setups: List[Dict[str, Any]] = []

    for sym, ds in asset_data.items():
        htf_gen = MarketStateGenerator(timeframe=tfs["htf"])
        mtf_gen = MarketStateGenerator(timeframe=tfs["mtf"])
        ltf_gen = MarketStateGenerator(timeframe=tfs["ltf"])
        base_engine = AdaptiveEngineV1(
            timeframe_set_id=ANCHOR_SET,
            htf_label=tfs["htf"],
            mtf_label=tfs["mtf"],
            ltf_label=tfs["ltf"],
            min_target_r=4.0,
        )

        n_bars = len(ds["sub_ts"])
        cached_htf_idx = -1
        cached_htf_state = None
        cached_mtf_idx = -1
        cached_mtf_state = None

        for i in range(100, n_bars, 4):
            curr_t = int(ds["sub_ts"][i])

            # HTF State
            h_mask = ds["h_data"]["timestamps"] <= curr_t
            if not np.any(h_mask):
                continue
            h_idx_end = np.where(h_mask)[0][-1]
            if h_idx_end != cached_htf_idx:
                h_start = max(0, h_idx_end - 150)
                cached_htf_state = htf_gen.generate_state(
                    symbol=sym,
                    opens=ds["h_data"]["opens"][h_start : h_idx_end + 1],
                    highs=ds["h_data"]["highs"][h_start : h_idx_end + 1],
                    lows=ds["h_data"]["lows"][h_start : h_idx_end + 1],
                    closes=ds["h_data"]["closes"][h_start : h_idx_end + 1],
                    volumes=ds["h_data"]["volumes"][h_start : h_idx_end + 1],
                    timestamps=ds["h_data"]["timestamps"][h_start : h_idx_end + 1],
                )
                cached_htf_idx = h_idx_end
            h_state = cached_htf_state

            # MTF State
            m_mask = ds["m_data"]["timestamps"] <= curr_t
            if not np.any(m_mask):
                continue
            m_idx_end = np.where(m_mask)[0][-1]
            if m_idx_end != cached_mtf_idx:
                m_start = max(0, m_idx_end - 150)
                cached_mtf_state = mtf_gen.generate_state(
                    symbol=sym,
                    opens=ds["m_data"]["opens"][m_start : m_idx_end + 1],
                    highs=ds["m_data"]["highs"][m_start : m_idx_end + 1],
                    lows=ds["m_data"]["lows"][m_start : m_idx_end + 1],
                    closes=ds["m_data"]["closes"][m_start : m_idx_end + 1],
                    volumes=ds["m_data"]["volumes"][m_start : m_idx_end + 1],
                    timestamps=ds["m_data"]["timestamps"][m_start : m_idx_end + 1],
                )
                cached_mtf_idx = m_idx_end
            m_state = cached_mtf_state

            # LTF State
            l_start = max(0, i - 150)
            ltf_state = ltf_gen.generate_state(
                symbol=sym,
                opens=ds["sub_o"][l_start : i + 1],
                highs=ds["sub_h"][l_start : i + 1],
                lows=ds["sub_l"][l_start : i + 1],
                closes=ds["sub_c"][l_start : i + 1],
                volumes=ds["sub_v"][l_start : i + 1],
                timestamps=ds["sub_ts"][l_start : i + 1],
            )

            # Causal context extraction
            cross_snap = history_wh.get_cross_market_quote(curr_t)
            pos_snap = history_wh.get_crypto_positioning(sym, curr_t)
            regime = regime_engine.evaluate_regime(
                current_state=m_state,
                cross_market_data={"vix_level": cross_snap.vix, "dxy_trend": "BULLISH" if cross_snap.dxy_change_24h_pct > 0 else "BEARISH"},
            )

            # Microstructure quote spread estimation
            quote_spread_bps = 1.0
            if regime.volatility == VolatilityRegime.EXTREME:
                quote_spread_bps = 12.0
            elif regime.liquidity == LiquidityRegime.IMPAIRED:
                quote_spread_bps = 10.0
            elif regime.volatility == VolatilityRegime.HIGH:
                quote_spread_bps = 3.5

            # VIX level estimation
            vix_level = cross_snap.vix

            # Technical signal
            base_sig, base_audit = base_engine.evaluate_adaptive_decision(
                bar_index=i,
                timestamp_ms=curr_t,
                htf_state=h_state,
                mtf_state=m_state,
                ltf_state=ltf_state,
            )

            if not base_sig or base_sig.target_r < 4.0:
                continue

            candidate_setups.append({
                "bar_index": i,
                "timestamp_ms": curr_t,
                "direction": base_sig.direction,
                "entry_price": base_sig.entry_price,
                "stop_price": base_sig.stop_price,
                "target_price": base_sig.target_price,
                "target_r": base_sig.target_r,
                "has_4r_target": True,
                "symbol": sym,
                "h_state": h_state,
                "m_state": m_state,
                "ltf_state": ltf_state,
                "regime": regime,
                "pos_snap": pos_snap,
                "quote_spread_bps": quote_spread_bps,
                "vix_level": vix_level,
            })

    print(f"  Discovered {len(candidate_setups)} structurally valid candidate setups across {ASSETS}.", flush=True)

    # Step 3: Run Baseline (Ungoverned) Execution to establish Ground Truth Outcomes
    print("\n[Step 3] Running Ungoverned Baseline to determine ground truth outcomes...", flush=True)
    ungov_signals = [{k: v for k, v in c.items() if k not in ("h_state", "m_state", "ltf_state", "regime", "pos_snap", "quote_spread_bps", "vix_level")} for c in candidate_setups]
    
    baseline_trades: List[TradeRecord] = []
    for sym in ASSETS:
        ds = asset_data[sym]
        sym_sigs = [s for s in ungov_signals if s["symbol"] == sym]
        if sym_sigs:
            res = backtest_engine.execute_stream(
                stream_id=f"BASE_{sym}",
                symbol=sym,
                timeframe_set=ANCHOR_SET,
                hypothesis="UNGOVERNED_BASELINE",
                ltf_opens=ds["sub_o"],
                ltf_highs=ds["sub_h"],
                ltf_lows=ds["sub_l"],
                ltf_closes=ds["sub_c"],
                ltf_timestamps=ds["sub_ts"],
                signal_candidates=sym_sigs,
            )
            baseline_trades.extend(res.trades)

    baseline_trades.sort(key=lambda t: t.entry_ts)
    baseline_stats = _calc_stats(baseline_trades)
    print(f"  Ungoverned Baseline: {baseline_stats['total_trades']} trades | Net {baseline_stats['net_r']:+.2f}R | MDD: {baseline_stats['max_drawdown_pct']:.2f}%", flush=True)

    trade_outcome_map: Dict[Tuple[str, int], TradeRecord] = {(t.symbol, t.entry_ts): t for t in baseline_trades}

    # Helper function: Check if a trade is in a post-crisis episode
    def get_episode_for_ts(ts: int) -> Optional[PostCrisisRecoveryEpisode]:
        for ep in POST_CRISIS_EPISODES:
            if ep.crisis_shock_start_ts <= ts <= ep.recovery_window_end_ts:
                return ep
        return None

    # Step 4: Execute & Compare the 3 Reactivation Policies
    print("\n[Step 4] Executing Comparative Audit of 3 Reactivation Policies...", flush=True)

    # Policy Definitions:
    # Policy A: NAIVE_PREMATURE
    # As soon as crisis shock starts to ease (or on any signal after shock starts), re-enter at full 1.0x.
    # No waiting for volatility or liquidity restoration.
    #
    # Policy B: RIGID_ULTRA_CONSERVATIVE
    # Stays FLAT until Volatility is LOW/NORMAL, Spread <= 1.5 bps, VIX <= 18, and HTF external trend is BULLISH.
    # 
    # Policy C: AUTONOMOUS_STAGED_PACING (Phase J Engine)
    # Staged pacing: 0.25x Probe -> 0.50x Transition -> 1.0x Full, plus False Recovery Abort tripwire.

    policy_records: Dict[str, List[TradeRecord]] = {
        "POLICY_A_NAIVE_PREMATURE": [],
        "POLICY_B_RIGID_ULTRA_CONSERVATIVE": [],
        "POLICY_C_STAGED_PACING": [],
    }

    # Tracking false recovery stats
    false_traps: Dict[str, int] = {"POLICY_A_NAIVE_PREMATURE": 0, "POLICY_B_RIGID_ULTRA_CONSERVATIVE": 0, "POLICY_C_STAGED_PACING": 0}
    false_loss_r: Dict[str, float] = {"POLICY_A_NAIVE_PREMATURE": 0.0, "POLICY_B_RIGID_ULTRA_CONSERVATIVE": 0.0, "POLICY_C_STAGED_PACING": 0.0}

    # Recovery confirmation audit logs
    confirmation_audits: List[RecoveryConfirmationAudit] = []

    # Initialize Governors
    # 1. Calibrated Governor from Phase I (Frozen baseline governor)
    calibrated_base_gov = SystemicRiskGovernor(calibration_mode="CALIBRATED")

    # 2. Reactivation Engine for Policy C
    react_engine_c = ReactivationEngine(
        max_stabilization_spread_bps=8.0,
        vix_calm_ceiling=26.0,
        tier1_probe_risk_mult=0.25,
        tier2_confirm_risk_mult=0.50,
        tier3_full_risk_mult=1.00,
    )
    governor_c = SystemicRiskGovernor(
        calibration_mode="CALIBRATED",
        reactivation_engine=react_engine_c,
    )

    # Track crisis status per symbol
    active_crisis_symbols: Dict[str, bool] = {s: False for s in ASSETS}

    # Filter setups to only those occurring in or around the 5 post-crisis recovery windows
    recovery_setups = [c for c in candidate_setups if get_episode_for_ts(c["timestamp_ms"]) is not None]
    recovery_setups.sort(key=lambda c: c["timestamp_ms"])
    print(f"  Identified {len(recovery_setups)} setups situated across the 5 Post-Crisis Cycles.", flush=True)

    policy_signals: Dict[str, List[Dict[str, Any]]] = {
        "POLICY_A_NAIVE_PREMATURE": [],
        "POLICY_B_RIGID_ULTRA_CONSERVATIVE": [],
        "POLICY_C_STAGED_PACING": [],
    }
    policy_risk_factors: Dict[str, Dict[Tuple[str, int], float]] = {
        "POLICY_A_NAIVE_PREMATURE": {},
        "POLICY_B_RIGID_ULTRA_CONSERVATIVE": {},
        "POLICY_C_STAGED_PACING": {},
    }

    for c in recovery_setups:
        sym = c["symbol"]
        ts = c["timestamp_ms"]
        direction = c["direction"]
        tgt_r = c["target_r"]
        h_st = c["h_state"]
        m_st = c["m_state"]
        l_st = c["ltf_state"]
        reg = c["regime"]
        pos = c["pos_snap"]
        spread_bps = c["quote_spread_bps"]
        vix = c["vix_level"]
        ep = get_episode_for_ts(ts)
        entry_bar = c["bar_index"] + 1

        is_in_shock = (ep.crisis_shock_start_ts <= ts <= ep.crisis_shock_end_ts)
        is_in_recovery = (ep.recovery_window_start_ts < ts <= ep.recovery_window_end_ts)

        # Update crisis state tracking
        if is_in_shock:
            react_engine_c.register_crisis_event(sym)
            active_crisis_symbols[sym] = True

        cand_exec = {k: v for k, v in c.items() if k not in ("h_state", "m_state", "ltf_state", "regime", "pos_snap", "quote_spread_bps", "vix_level")}

        # -------------------------------------------------------------
        # 1. EVALUATE POLICY A: NAIVE_PREMATURE
        # -------------------------------------------------------------
        # Re-enters immediately upon any signal in shock or recovery at 1.0x
        if is_in_shock or is_in_recovery:
            sig_a = dict(cand_exec)
            sig_a["risk_pct"] = 0.01
            policy_signals["POLICY_A_NAIVE_PREMATURE"].append(sig_a)
            policy_risk_factors["POLICY_A_NAIVE_PREMATURE"][(sym, entry_bar)] = 1.0

        # -------------------------------------------------------------
        # 2. EVALUATE POLICY B: RIGID_ULTRA_CONSERVATIVE
        # -------------------------------------------------------------
        # Only trades if 100% serene in recovery window
        if not is_in_shock and is_in_recovery:
            htf_trend = getattr(h_st.structure, "external_trend", TrendDirection.NEUTRAL)
            is_htf_aligned = (direction == 1 and htf_trend == TrendDirection.BULLISH) or (direction == -1 and htf_trend == TrendDirection.BEARISH)
            if (reg.volatility in (VolatilityRegime.LOW, VolatilityRegime.NORMAL)
                and reg.vol_percentile < 0.60
                and spread_bps <= 2.0
                and vix <= 20.0
                and is_htf_aligned):
                sig_b = dict(cand_exec)
                sig_b["risk_pct"] = 0.01
                policy_signals["POLICY_B_RIGID_ULTRA_CONSERVATIVE"].append(sig_b)
                policy_risk_factors["POLICY_B_RIGID_ULTRA_CONSERVATIVE"][(sym, entry_bar)] = 1.0

        # -------------------------------------------------------------
        # 3. EVALUATE POLICY C: AUTONOMOUS_STAGED_PACING (Phase J Engine)
        # -------------------------------------------------------------
        audit_entry = react_engine_c.evaluate_reactivation_status(
            symbol=sym,
            timestamp_ms=ts,
            htf_state=h_st,
            mtf_state=m_st,
            ltf_state=l_st,
            direction=direction,
            regime=reg,
            positioning=pos,
            quote_spread_bps=spread_bps,
            vix_level=vix,
        )
        confirmation_audits.append(audit_entry)

        verdict_c = governor_c.evaluate_risk_verdict(
            symbol=sym,
            direction=direction,
            candidate_destination_r=tgt_r,
            htf_state=h_st,
            mtf_state=m_st,
            ltf_state=l_st,
            regime=reg,
            positioning=pos,
            quote_spread_bps=spread_bps,
            vix_level=vix,
            timestamp_ms=ts,
            proposed_base_risk_pct=0.01,
        )

        if verdict_c.is_trade_allowed and verdict_c.approved_risk_pct > 0:
            sig_c = dict(cand_exec)
            sig_c["risk_pct"] = verdict_c.approved_risk_pct
            rf = verdict_c.approved_risk_pct / 0.01
            policy_signals["POLICY_C_STAGED_PACING"].append(sig_c)
            policy_risk_factors["POLICY_C_STAGED_PACING"][(sym, entry_bar)] = rf

    # Execute stream backtest for each policy
    for pol_id in ["POLICY_A_NAIVE_PREMATURE", "POLICY_B_RIGID_ULTRA_CONSERVATIVE", "POLICY_C_STAGED_PACING"]:
        for sym in ASSETS:
            ds = asset_data[sym]
            sym_sigs = [s for s in policy_signals[pol_id] if s["symbol"] == sym]
            if sym_sigs:
                res = backtest_engine.execute_stream(
                    stream_id=f"{pol_id}_{sym}",
                    symbol=sym,
                    timeframe_set=ANCHOR_SET,
                    hypothesis=pol_id,
                    ltf_opens=ds["sub_o"],
                    ltf_highs=ds["sub_h"],
                    ltf_lows=ds["sub_l"],
                    ltf_closes=ds["sub_c"],
                    ltf_timestamps=ds["sub_ts"],
                    signal_candidates=sym_sigs,
                )
                for t in res.trades:
                    matches = np.where(ds["sub_ts"] == t.entry_ts)[0]
                    rf = 1.0
                    if len(matches) > 0:
                        rf = policy_risk_factors[pol_id].get((sym, int(matches[0])), 1.0)

                    realized_r = round(t.realized_r * rf, 2)
                    scaled_trade = TradeRecord(
                        stream_id=t.stream_id,
                        symbol=t.symbol,
                        direction=t.direction,
                        entry_ts=t.entry_ts,
                        exit_ts=t.exit_ts,
                        entry_px=t.entry_px,
                        exit_px=t.exit_px,
                        initial_sl=t.initial_sl,
                        target_px=t.target_px,
                        initial_risk_dist=t.initial_risk_dist,
                        target_r=t.target_r,
                        realized_r=realized_r,
                        exit_reason=t.exit_reason,
                        bars_held=t.bars_held,
                        fee_bps=t.fee_bps,
                        slippage_bps=t.slippage_bps,
                        mae_r=t.mae_r,
                        mfe_r=t.mfe_r,
                    )
                    policy_records[pol_id].append(scaled_trade)

                    ep = get_episode_for_ts(t.entry_ts)
                    if ep:
                        is_shock = (ep.crisis_shock_start_ts <= t.entry_ts <= ep.crisis_shock_end_ts)
                        if realized_r < 0 and (is_shock or rf <= 0.30):
                            false_traps[pol_id] += 1
                            false_loss_r[pol_id] += abs(realized_r)
                            if pol_id == "POLICY_C_STAGED_PACING":
                                react_engine_c.register_false_recovery_failure(sym)

        policy_records[pol_id].sort(key=lambda t: t.entry_ts)

    # Step 5: Compute Comparative Policy Metrics
    print("\n[Step 5] Compiling Comparative Performance Metrics...", flush=True)

    # Theoretical maximum recovery trend R (sum of all winning trades in recovery windows)
    total_theoretical_recovery_r = sum(t.realized_r for t in baseline_trades if t.realized_r > 0 and get_episode_for_ts(t.entry_ts) is not None)
    if total_theoretical_recovery_r <= 0:
        total_theoretical_recovery_r = 1.0

    comparison_results: List[ReactivationPolicyComparison] = []

    for pol_id, t_list in policy_records.items():
        stats = _calc_stats(t_list)
        f_traps = false_traps[pol_id]
        f_loss = round(false_loss_r[pol_id], 2)
        winning_r = sum(t.realized_r for t in t_list if t.realized_r > 0)
        captured_pct = round(winning_r / total_theoretical_recovery_r * 100.0, 1)

        # Reactivation Efficiency Ratio: Net R / (1.0 + False Recovery Loss R)
        # Measures return earned per unit of false recovery drawdown sustained
        rer = round(stats["net_r"] / (1.0 + f_loss), 3) if stats["net_r"] > 0 else 0.0

        pol_names = {
            "POLICY_A_NAIVE_PREMATURE": "Policy A: Naive Premature (Immediate Re-entry 1.0x)",
            "POLICY_B_RIGID_ULTRA_CONSERVATIVE": "Policy B: Rigid Ultra-Conservative (Full HTF Serenity 1.0x)",
            "POLICY_C_STAGED_PACING": "Policy C: Autonomous Staged Pacing (0.25x -> 0.50x -> 1.0x)",
        }

        comp = ReactivationPolicyComparison(
            policy_id=pol_id,
            name=pol_names[pol_id],
            total_recovery_trades=stats["total_trades"],
            net_r=stats["net_r"],
            expectancy_r=stats["expectancy_r"],
            win_rate=stats["win_rate"],
            profit_factor=stats["profit_factor"],
            false_recovery_traps_hit=f_traps,
            false_recovery_loss_r=f_loss,
            post_crisis_trend_captured_pct=captured_pct,
            max_drawdown_pct=stats["max_drawdown_pct"],
            reactivation_efficiency_ratio=rer,
            meta={"stats": stats},
        )
        comparison_results.append(comp)
        print(f"  {comp.name}:")
        print(f"    Trades: {comp.total_recovery_trades} | Net R: {comp.net_r:+.2f}R | WR: {comp.win_rate:.1f}% | PF: {comp.profit_factor:.2f}")
        print(f"    False Traps Hit: {comp.false_recovery_traps_hit} | False Loss: -{comp.false_recovery_loss_r:.2f}R | Trend Captured: {comp.post_crisis_trend_captured_pct:.1f}%")
        print(f"    MDD: {comp.max_drawdown_pct:.2f}% | Reactivation Efficiency Ratio (RER): {comp.reactivation_efficiency_ratio:.3f}\n")

    # Step 6: Detailed Breakdown per Post-Crisis Episode
    print("\n[Step 6] Auditing Breakdown Across 5 Historical Post-Crisis Cycles...", flush=True)
    episode_audits: List[Dict[str, Any]] = []

    for ep in POST_CRISIS_EPISODES:
        ep_dict: Dict[str, Any] = {
            "episode_id": ep.episode_id,
            "name": ep.name,
            "macro_catalyst": ep.macro_catalyst,
            "trough_price": ep.crisis_trough_price,
            "peak_price": ep.recovery_peak_price,
            "recovery_expansion_pct": round((ep.recovery_peak_price - ep.crisis_trough_price) / ep.crisis_trough_price * 100.0, 1),
            "policies": {},
        }

        for pol_id, t_list in policy_records.items():
            ep_trades = [t for t in t_list if ep.crisis_shock_start_ts <= t.entry_ts <= ep.recovery_window_end_ts]
            ep_stats = _calc_stats(ep_trades)
            ep_dict["policies"][pol_id] = {
                "trades": ep_stats["total_trades"],
                "net_r": ep_stats["net_r"],
                "win_rate": ep_stats["win_rate"],
                "profit_factor": ep_stats["profit_factor"],
                "max_drawdown_pct": ep_stats["max_drawdown_pct"],
            }
        episode_audits.append(ep_dict)
        print(f"  {ep.name} (+{ep_dict['recovery_expansion_pct']}% Expansion):")
        for p_id, p_st in ep_dict["policies"].items():
            print(f"    {p_id}: {p_st['trades']} trades, {p_st['net_r']:+.2f}R, {p_st['win_rate']:.1f}% WR, {p_st['max_drawdown_pct']:.2f}% MDD")

    # Step 7: 5-Dimensional Recovery Confirmation Dimension Statistics
    print("\n[Step 7] Auditing 5-Dimensional Recovery Confirmation Efficacy...", flush=True)
    n_audits = len(confirmation_audits)
    dim_stats = {
        "total_evaluations": n_audits,
        "volatility_normalized_pct": round(sum(1 for a in confirmation_audits if a.is_volatility_normalized) / max(1, n_audits) * 100.0, 1),
        "liquidity_restored_pct": round(sum(1 for a in confirmation_audits if a.is_liquidity_restored) / max(1, n_audits) * 100.0, 1),
        "structure_aligned_pct": round(sum(1 for a in confirmation_audits if a.is_structure_aligned) / max(1, n_audits) * 100.0, 1),
        "cross_market_calm_pct": round(sum(1 for a in confirmation_audits if a.is_cross_market_calm) / max(1, n_audits) * 100.0, 1),
        "positioning_safe_pct": round(sum(1 for a in confirmation_audits if a.is_positioning_safe) / max(1, n_audits) * 100.0, 1),
        "stage_distribution": {
            s.value: sum(1 for a in confirmation_audits if a.stage == s)
            for s in ReactivationStage
        },
    }
    print(f"  Dimension Normalization Rates: Vol: {dim_stats['volatility_normalized_pct']}%, Liq: {dim_stats['liquidity_restored_pct']}%, Struct: {dim_stats['structure_aligned_pct']}%, Cross: {dim_stats['cross_market_calm_pct']}%, Pos: {dim_stats['positioning_safe_pct']}%")
    print(f"  Stage Distribution: {dim_stats['stage_distribution']}")

    # Step 8: Persist Artifacts
    print("\n[Step 8] Persisting Phase J JSON Artifacts...", flush=True)

    reactivation_audit_json = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "PHASE_J_REGIME_TRANSITION_RECOVERY_REACTIVATION",
        "dimension_statistics": dim_stats,
        "audit_samples": [a.to_dict() for a in confirmation_audits[:50]],
    }
    staged_comparison_json = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "PHASE_J",
        "policies": [c.to_dict() for c in comparison_results],
    }
    false_recovery_json = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "PHASE_J",
        "false_recovery_metrics": {
            pol_id: {
                "traps_hit": false_traps[pol_id],
                "loss_r": round(false_loss_r[pol_id], 2),
                "loss_mitigation_vs_naive_pct": round((false_loss_r["POLICY_A_NAIVE_PREMATURE"] - false_loss_r[pol_id]) / max(0.01, false_loss_r["POLICY_A_NAIVE_PREMATURE"]) * 100.0, 1) if pol_id != "POLICY_A_NAIVE_PREMATURE" else 0.0,
            }
            for pol_id in policy_records
        },
    }
    post_crisis_episodes_json = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "PHASE_J",
        "total_episodes": len(POST_CRISIS_EPISODES),
        "episodes": episode_audits,
    }
    registry_json = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "PHASE_J",
        "total_recovery_setups_evaluated": len(recovery_setups),
        "total_post_crisis_episodes": len(POST_CRISIS_EPISODES),
        "best_policy_id": max(comparison_results, key=lambda c: c.reactivation_efficiency_ratio).policy_id,
        "best_reactivation_efficiency_ratio": max(comparison_results, key=lambda c: c.reactivation_efficiency_ratio).reactivation_efficiency_ratio,
        "artifacts_generated": [
            "PHASE_J_REACTIVATION_AUDIT.json",
            "PHASE_J_STAGED_PACING_COMPARISON.json",
            "PHASE_J_FALSE_RECOVERY_METRICS.json",
            "PHASE_J_POST_CRISIS_EPISODES.json",
            "PHASE_J_EXPERIMENT_REGISTRY.json",
        ],
    }

    files_to_save = {
        "PHASE_J_REACTIVATION_AUDIT.json": reactivation_audit_json,
        "PHASE_J_STAGED_PACING_COMPARISON.json": staged_comparison_json,
        "PHASE_J_FALSE_RECOVERY_METRICS.json": false_recovery_json,
        "PHASE_J_POST_CRISIS_EPISODES.json": post_crisis_episodes_json,
        "PHASE_J_EXPERIMENT_REGISTRY.json": registry_json,
    }

    for fname, data in files_to_save.items():
        p_res = RESULTS_DIR / fname
        p_root = REPO_ROOT / fname
        with open(p_res, "w") as f:
            json.dump(data, f, indent=2)
        with open(p_root, "w") as f:
            json.dump(data, f, indent=2)
        print(f"  Saved {fname} -> research/results/ and root.", flush=True)

    elapsed = time.time() - start_time
    print(f"\n================================================================================")
    print(f"PHASE J RESEARCH EXECUTION COMPLETED IN {elapsed:.1f}s")
    print(f"================================================================================")


if __name__ == "__main__":
    run_phase_j_research()
