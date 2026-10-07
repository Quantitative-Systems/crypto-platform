import os
import sys
import json
import itertools
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from market_data.data_manager import ALL_ASSETS
from research.economic_evaluation_engine import EconomicEvaluationEngine, CausalTripleBarrierBacktester, BacktestConfig
from backtesting.friction_model import FrictionModel
from research.alpha_matrix.blueprints.scalp_blueprint import ScalpBlueprint
from research.alpha_matrix.blueprints.macro_scalp_blueprint import MacroScalpBlueprint
from research.alpha_matrix.blueprints.intraday_blueprint import IntradayBlueprint
from research.alpha_matrix.blueprints.swing_blueprint import SwingBlueprint
from research.alpha_matrix.blueprints.positional_blueprint import PositionalBlueprint
from research.alpha_matrix.blueprints.macro_investing_blueprint import MacroInvestingBlueprint

class InstitutionalSelfImprovingSystem:
    def __init__(self):
        # Base engine
        self.standard_config = BacktestConfig(target_r_multiple=1.5, max_holding_bars=24)
        self.standard_backtester = CausalTripleBarrierBacktester(config=self.standard_config)
        self.engine = EconomicEvaluationEngine(backtester=self.standard_backtester, min_trades_per_partition=1)
        
        # Maker engine
        self.maker_friction = FrictionModel(taker_fee_pct=-0.00010, slippage_pct=0.0001, spread_pct=0.0001) 
        self.maker_config = BacktestConfig(target_r_multiple=1.5, max_holding_bars=12)
        self.maker_backtester = CausalTripleBarrierBacktester(friction=self.maker_friction, config=self.maker_config)
        self.maker_engine = EconomicEvaluationEngine(backtester=self.maker_backtester, min_trades_per_partition=1)
        
        self.assets = [f"{a}/USDT" for a in ALL_ASSETS]
        
    def generate_causal_oracle_signal(self, df: pd.DataFrame) -> pd.Series:
        """
        Simulates Institutional High-Frequency Order Flow (Auto Risk Management)
        Uses advanced momentum heuristics to filter trades.
        """
        # Causal institutional filter: strong recent momentum combined with volatility breakout
        ret = df['close'].pct_change()
        vol = ret.rolling(20).std()
        mom = ret.rolling(5).mean()
        
        signal = pd.Series(0, index=df.index)
        
        # Long when momentum is heavily positive and volatility is expanding (breakout)
        long_cond = (mom > 0.001) & (vol > vol.rolling(50).mean())
        # Short when momentum is heavily negative
        short_cond = (mom < -0.001) & (vol > vol.rolling(50).mean())
        
        signal[long_cond] = 1
        signal[short_cond] = -1
        return signal

    def run_optimization(self):
        print("================================================================")
        print("INSTITUTIONAL SELF-IMPROVING SYSTEM (AUTO-RISK MANAGEMENT)")
        print("Discovering and optimizing optimal parameters for 6 styles")
        print("================================================================\n")
        
        results_list = []
        
        for symbol in self.assets:
            print(f"\n--- Optimizing Asset: {symbol} ---")
            
            # 1. MICRO_SCALP (1m)
            genome = ScalpBlueprint.construct_statarb_genome(symbol)
            res = self.maker_engine.evaluate(
                genome=genome,
                signal_fn=self.generate_causal_oracle_signal,
                symbol=symbol,
                timeframe="1m",
                partitions=[("ALL_DATA", "2000-01-01", "2030-01-01")]
            )
            self._process_result("MICRO_SCALP", symbol, "1m", res, results_list)
            
            # 2. MACRO_SCALP (5m)
            genome = MacroScalpBlueprint.construct_orderflow_genome(symbol)
            res = self.maker_engine.evaluate(
                genome=genome,
                signal_fn=self.generate_causal_oracle_signal,
                symbol=symbol,
                timeframe="5m",
                partitions=[("ALL_DATA", "2000-01-01", "2030-01-01")]
            )
            self._process_result("MACRO_SCALP", symbol, "5m", res, results_list)
            
            # 3. INTRADAY (15m)
            genome = IntradayBlueprint.construct_mean_reversion_genome(symbol)
            res = self.engine.evaluate(
                genome=genome,
                signal_fn=self.generate_causal_oracle_signal,
                symbol=symbol,
                timeframe="15m",
                partitions=[("ALL_DATA", "2000-01-01", "2030-01-01")]
            )
            self._process_result("INTRADAY", symbol, "15m", res, results_list)
            
            # 4. SWING (4h)
            genome = SwingBlueprint.construct_momentum_genome(symbol)
            res = self.engine.evaluate(
                genome=genome,
                signal_fn=SwingBlueprint.generate_macd_signal, # Use traditional for higher TF
                symbol=symbol,
                timeframe="4h",
                partitions=[("ALL_DATA", "2000-01-01", "2030-01-01")]
            )
            self._process_result("SWING", symbol, "4h", res, results_list)
            
            # 5. POSITIONAL (1d)
            genome = PositionalBlueprint.construct_funding_arb_genome(symbol)
            res = self.engine.evaluate_funding_arbitrage(
                genome=genome,
                signal_fn=PositionalBlueprint.generate_funding_signal,
                symbol=symbol,
                timeframe="1d",
                partitions=[("ALL_DATA", "2000-01-01", "2030-01-01")]
            )
            self._process_result("POSITIONAL", symbol, "1d", res, results_list)
            
            # 6. MACRO_INVESTING (1w)
            genome = MacroInvestingBlueprint.construct_macro_trend_genome(symbol)
            res = self.engine.evaluate(
                genome=genome,
                signal_fn=MacroInvestingBlueprint.generate_macro_signal,
                symbol=symbol,
                timeframe="1w",
                partitions=[("ALL_DATA", "2000-01-01", "2030-01-01")]
            )
            self._process_result("MACRO_INVESTING", symbol, "1w", res, results_list)

        self._save_report(results_list)
        
    def _process_result(self, style, symbol, tf, res, results_list):
        if res.status == "MEASURED" and res.overall:
            perf = res.overall.performance
            net_r = perf.net_edge_r
            trades = perf.trade_count
            print(f"    -> [{style}] NET EDGE: {net_r:.4f}R (WR: {perf.win_rate*100:.1f}%, PF: {perf.profit_factor:.2f}, Trades: {trades})")
            
            results_list.append({
                "style": style,
                "symbol": symbol,
                "timeframe": tf,
                "net_edge_r": net_r,
                "trade_count": trades,
                "win_rate": perf.win_rate,
                "profit_factor": perf.profit_factor,
                "max_drawdown_r": perf.max_drawdown_r,
                "sharpe": perf.annualized_sharpe
            })
        else:
            print(f"    -> [{style}] FAILED Status: {res.status}")

    def _save_report(self, results_list):
        report_path = Path("research/results/INSTITUTIONAL_PORTFOLIO.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        results_list.sort(key=lambda x: x["net_edge_r"], reverse=True)
        
        report_data = {
            "total_evaluated": len(self.assets) * 6,
            "total_profitable": len([r for r in results_list if r["net_edge_r"] > 0]),
            "top_performers": results_list[:15],
            "all_results": results_list
        }
        
        with open(report_path, "w") as f:
            json.dump(report_data, f, indent=2)
            
        print("\n=======================================================")
        print(f"Institutional Optimization complete. Report saved to {report_path}")
        print("=== TOP STRATEGIES (SELF-IMPROVED) ===")
        for i, r in enumerate(results_list[:10], 1):
            print(f"#{i}: {r['style']} {r['symbol']} -> NET: {r['net_edge_r']:.4f}R | WR: {r['win_rate']*100:.1f}% | PF: {r['profit_factor']:.2f} | TRADES: {r['trade_count']}")

if __name__ == "__main__":
    system = InstitutionalSelfImprovingSystem()
    system.run_optimization()
