import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd
import numpy as np

from platform_core.alpha_genome import AlphaGenome
from research.economic_evaluation_engine import EconomicEvaluationEngine

from research.quant_models.funding_arbitrage_engine import generate_carry_signal


def run_experiment():
    print("================================================================")
    print("QCP EXPERIMENT EABG-004: PERPETUAL FUNDING YIELD ARBITRAGE (DYNAMIC)")
    print("================================================================\n")
    
    engine = EconomicEvaluationEngine()
    
    universe = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "LINK/USDT", "LTC/USDT"]
    
    results = []
    
    for symbol in universe:
        from platform_core.alpha_genome import AlphaFamily
        
        genome = AlphaGenome(
            alpha_id=f"FAM-10-YIELD_ARB_{symbol.replace('/','')}",
            family=AlphaFamily.CARRY,
            version="v2.0",
            asset_universe=[symbol],
            venues=["BINANCE"],
            instruments=["SPOT", "PERPETUAL"],
            timeframe="4h",
            expected_holding_period_hours=720.0,
            economic_rationale="Smart delta-neutral carry trade avoiding negative funding regimes.",
            features=["FUNDING_RATE", "MA_21"],
            entry_mechanism="FUNDING_MA_CROSS",
            exit_mechanism="FUNDING_MA_DROP"
        )
        
        print(f"Evaluating {symbol}...")
        result = engine.evaluate_funding_arbitrage(
            genome=genome,
            signal_fn=generate_carry_signal,
            symbol=symbol,
            timeframe="4h"
        )
        
        if result.status == "MEASURED":
            overall = result.overall
            net_r = overall.performance.net_edge_r
            gross_r = overall.performance.gross_edge_r
            print(f"  [PASS] {symbol} | Net Profit: {net_r:.2f}R | Gross Yield: {gross_r:.2f}R | Trades: {overall.trade_count}")
            results.append(result.to_dict())
        else:
            print(f"  [FAIL] {symbol} | Status: {result.status} | Notes: {result.notes}")
            
    # Save results
    output_dir = Path("research/results")
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "EABG004_FUNDING_ARB_RESULTS.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
        
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    run_experiment()
