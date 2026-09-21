import sys
import os
import json
import traceback
import pandas as pd
from typing import Dict, List, Any

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import research.bias_families as bf
import research.setup_families as sf
import research.entry_families as ef
import research.sl_families as slf
import research.tp_families as tpf
import research.trailing_families as trf
from research.grammar_components import ComponentRegistry
from research.strategy_grammar import HypothesisBuilder, TimeframeSet
from research.economic_evaluation_engine import (
    EconomicEvaluationEngine, 
    DatasetProvenance, 
    BacktestConfig, 
    FrictionModel
)

from platform_core.alpha_genome import AlphaGenome

# Register all components
bf.register_all_biases(ComponentRegistry)
sf.register_all_setups(ComponentRegistry)
ef.register_all_entries(ComponentRegistry)
slf.register_all_stop_losses(ComponentRegistry)
tpf.register_all_take_profits(ComponentRegistry)
trf.register_all_trailings(ComponentRegistry)

def build_hypotheses() -> List[Dict]:
    """Define a curated matrix of hypotheses to discover edges."""
    hypotheses = []
    
    # 1. The V2.1 Canonical (Supertrend + Stoch + Structural) - 4R Firewall
    hypotheses.append({
        "alpha_id": "H_CANONICAL_V21_4R",
        "bias_id": "CANONICAL_SUPERTREND_STOCHASTIC",
        "setup_id": "CANONICAL_SUPERTREND_STOCHASTIC_SETUP",
        "entry_id": "CANONICAL_SUPERTREND_STOCHASTIC_ENTRY",
        "sl_id": "SL_LTF_SWING",
        "tp_id": "TP_HTF_STRUCTURAL",
        "trailing_id": "TRAIL_MTF_STRUCTURAL"
    })
    
    # 2. V2.1 Canonical - Relaxed 2R Firewall
    hypotheses.append({
        "alpha_id": "H_CANONICAL_V21_2R",
        "bias_id": "CANONICAL_SUPERTREND_STOCHASTIC",
        "setup_id": "CANONICAL_SUPERTREND_STOCHASTIC_SETUP",
        "entry_id": "CANONICAL_SUPERTREND_STOCHASTIC_ENTRY",
        "sl_id": "SL_LTF_SWING",
        "tp_id": "TP_HTF_STRUCTURAL",
        "trailing_id": "TRAIL_MTF_STRUCTURAL"
    })
    
    # 3. V2.1 Canonical - Strict Dynamic 2R Target
    hypotheses.append({
        "alpha_id": "H_CANONICAL_V21_DYN_2R",
        "bias_id": "CANONICAL_SUPERTREND_STOCHASTIC",
        "setup_id": "CANONICAL_SUPERTREND_STOCHASTIC_SETUP",
        "entry_id": "CANONICAL_SUPERTREND_STOCHASTIC_ENTRY",
        "sl_id": "SL_LTF_SWING",
        "tp_id": "TP_DYNAMIC_R",
        "trailing_id": "TRAIL_MTF_STRUCTURAL"
    })
    
    # 4. Trend MA Alignment + Pullback + Engulfing (4R)
    hypotheses.append({
        "alpha_id": "H_TREND_PB_ENGULF_4R",
        "bias_id": "TREND_MA_ALIGNMENT",
        "setup_id": "PULLBACK",
        "entry_id": "ENGULFING",
        "sl_id": "SL_LTF_SWING",
        "tp_id": "TP_HTF_STRUCTURAL",
        "trailing_id": "TRAIL_MTF_STRUCTURAL"
    })
    
    # 5. Trend MA Alignment + Pullback + Dynamic 2R
    hypotheses.append({
        "alpha_id": "H_TREND_PB_DYN_2R",
        "bias_id": "TREND_MA_ALIGNMENT",
        "setup_id": "PULLBACK",
        "entry_id": "ENGULFING",
        "sl_id": "SL_LTF_SWING",
        "tp_id": "TP_DYNAMIC_R",
        "trailing_id": "TRAIL_NONE"
    })
    
    # 6. Momentum RSI + Breakout + Dynamic 1.5R (High Win Rate Target)
    hypotheses.append({
        "alpha_id": "H_MOM_BREAKOUT_1_5R",
        "bias_id": "MOM_RSI_REGIME",
        "setup_id": "BREAKOUT",
        "entry_id": "MACD_CROSSOVER",
        "sl_id": "SL_ATR",
        "tp_id": "TP_DYNAMIC_R",
        "trailing_id": "TRAIL_CHANDELIER"
    })

    return hypotheses

def get_backtest_config(hyp_id: str) -> BacktestConfig:
    """Return BacktestConfig overriding the firewall based on the hypothesis ID."""
    config = BacktestConfig()
    
    if "4R" in hyp_id:
        config.min_rr_firewall = 4.0
        config.target_r_multiple = 4.0
    elif "2R" in hyp_id:
        config.min_rr_firewall = 2.0
        config.target_r_multiple = 2.0
    elif "1_5R" in hyp_id:
        config.min_rr_firewall = 1.5
        config.target_r_multiple = 1.5
    else:
        config.min_rr_firewall = 4.0
        
    return config

def run_discovery():
    print("Initializing Empirical Discovery Engine...")
    
    hypotheses = build_hypotheses()
    assets = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    timeframe_sets = {
        "SET_2": (TimeframeSet.SET_2_CORE, "4h"),
        "SET_3": (TimeframeSet.SET_3_SWING, "1h"),
        "SET_4": (TimeframeSet.SET_4_INTRADAY, "15m")
    }
    
    partitions = [("DEV", "2021-01-01", "2022-12-31")]
    
    engine = EconomicEvaluationEngine(min_trades_per_partition=1)
    
    print("\nExecuting Matrix Sweep...")
    
    matrix_results = []
    
    for spec in hypotheses:
        print(f"\n--- Testing Hypothesis: {spec['alpha_id']} (Firewall: {'4R' if '4R' in spec['alpha_id'] else 'Relaxed'}) ---")
        
        config = get_backtest_config(spec["alpha_id"])
        
        from research.economic_evaluation_engine import CausalTripleBarrierBacktester
        backtester = CausalTripleBarrierBacktester(friction=FrictionModel(taker_fee_pct=0.0004, slippage_pct=0.0002), config=config)
        engine = EconomicEvaluationEngine(min_trades_per_partition=1, backtester=backtester)
        
        hyp_trades = []
        
        for asset in assets:
            for set_id, (tf_set, tf_str) in timeframe_sets.items():
                try:
                    genome = AlphaGenome(
                        alpha_id=f"{spec['alpha_id']}_{set_id}_{asset.replace('/', '')}",
                        family="DISCOVERY",
                        version="1.0",
                        asset_universe=[asset],
                        venues=["Binance"],
                        instruments=["SPOT"],
                        timeframe=tf_str,
                        expected_holding_period_hours=24.0,
                        economic_rationale="Empirical discovery sweep",
                        features=["discovery"],
                        entry_mechanism="various",
                        exit_mechanism="various"
                    )
                    
                    signal_fn = HypothesisBuilder.build_signal(
                        hypothesis_id=spec["alpha_id"],
                        bias_id=spec["bias_id"],
                        setup_id=spec["setup_id"],
                        entry_id=spec["entry_id"],
                        sl_id=spec["sl_id"],
                        tp_id=spec["tp_id"],
                        trailing_id=spec["trailing_id"],
                        tf_set=tf_set
                    )
                    
                    res = engine.evaluate(
                        genome=genome,
                        signal_fn=signal_fn,
                        symbol=asset,
                        timeframe=tf_str,
                        partitions=partitions
                    )
                    if res.trades:
                        hyp_trades.extend(res.trades)
                        
                except Exception as e:
                    print(f"Error evaluating {spec['alpha_id']} on {asset} {tf_str}: {e}")
                    traceback.print_exc()
                    
        if not hyp_trades:
            print(f"{spec['alpha_id']:30} | Trades: 0")
            continue
            
        total_trades = len(hyp_trades)
        total_gross_r = sum(t.gross_r for t in hyp_trades)
        total_net_r = sum(t.net_r for t in hyp_trades)
        
        wins = [t for t in hyp_trades if t.gross_r > 0]
        losses = [t for t in hyp_trades if t.gross_r <= 0]
        
        win_rate = len(wins) / total_trades if total_trades > 0 else 0
        
        gross_profit = sum(t.gross_r for t in wins)
        gross_loss = abs(sum(t.gross_r for t in losses))
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999.9
        
        avg_win = gross_profit / len(wins) if len(wins) > 0 else 0
        avg_loss = gross_loss / len(losses) if len(losses) > 0 else 0
        
        matrix_results.append({
            "Hypothesis": spec["alpha_id"],
            "Trades": total_trades,
            "Win Rate": f"{win_rate*100:.1f}%",
            "PF": f"{profit_factor:.2f}",
            "Avg Win": f"{avg_win:.2f}R",
            "Avg Loss": f"{avg_loss:.2f}R",
            "Gross R": f"{total_gross_r:.2f}R",
            "Net R": f"{total_net_r:.2f}R",
            "Firewall": f"{config.min_rr_firewall}R"
        })
        
        print(f"{spec['alpha_id']:30} | Trades: {total_trades:4} | WR: {win_rate*100:4.1f}% | PF: {profit_factor:4.2f} | Net R: {total_net_r:6.2f}")

    # Output to markdown report
    if not matrix_results:
        print("No results to save.")
        return
        
    df = pd.DataFrame(matrix_results)
    
    df['PF_float'] = df['PF'].astype(float)
    df = df.sort_values(by="PF_float", ascending=False)
    df = df.drop(columns=['PF_float'])
    
    report_path = os.path.join(os.path.dirname(__file__), "../results/DISCOVERY_MATRIX_REPORT.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    with open(report_path, "w") as f:
        f.write("# QCP Empirical Discovery Matrix Report\n\n")
        f.write("## Hypothesis Leaderboard (Ranked by Profit Factor)\n\n")
        
        # Manual markdown table construction
        columns = df.columns.tolist()
        f.write("| " + " | ".join(columns) + " |\n")
        f.write("| " + " | ".join(["---"] * len(columns)) + " |\n")
        for _, row in df.iterrows():
            f.write("| " + " | ".join(str(x) for x in row.values) + " |\n")
            
        f.write("\n\n## Analysis\n")
        f.write("This run systematically swept through canonical and alternative Strategy Grammar configurations.\n")
        f.write("We varied the `min_rr_firewall` (4R vs 2R vs 1.5R) and TP methodology to discover edges mathematically capable of 60%+ win rates.\n")
        
    print(f"\nReport written to {report_path}")

if __name__ == "__main__":
    run_discovery()
