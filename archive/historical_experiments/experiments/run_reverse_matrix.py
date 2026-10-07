import pandas as pd
import json
import os
import sys

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from market_data.binance_fetcher import BinanceFetcher
from research.economic_evaluation_engine import EconomicEvaluationEngine, BacktestConfig
from research.alpha_matrix.blueprints.reverse_indicator_blueprint import ReverseIndicatorBlueprint

# -------------------------------------------------------------------------------------
# REVERSE TIMEFRAME CONFIGURATION
# -------------------------------------------------------------------------------------
# The user wants to apply typical "Fast Scalping" logic to Macro timeframes (1M, 1w, 1d)
# and "Macro Investing" logic to Micro timeframes (15m, 5m, 1m).
REVERSE_STYLES = {
    # 1. Scalping logic applied to Macro
    'SCALPING': {'htf': '1M', 'mtf': '1w', 'ltf': '1d'},
    # 2. Intraday logic applied to Positional/Macro
    'INTRADAY': {'htf': '1w', 'mtf': '1d', 'ltf': '4h'},
    # 3. Swing logic applied to Positional
    'SWING': {'htf': '1d', 'mtf': '4h', 'ltf': '1h'},
    # 4. Positional logic applied to Swing/Intraday
    'POSITIONAL': {'htf': '4h', 'mtf': '1h', 'ltf': '15m'},
    # 5. Investing logic applied to Intraday/Scalping
    'INVESTING': {'htf': '1h', 'mtf': '15m', 'ltf': '5m'},
    # 6. Macro Investing logic applied to Micro Scalping
    'MACRO': {'htf': '15m', 'mtf': '5m', 'ltf': '1m'}
}

# The 10 core assets
ASSETS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT',
    'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'LTC/USDT'
]

# Shared evaluation engine
engine = EconomicEvaluationEngine()
# Target 1:2.5 RR to ensure 50-80% win rate with MTF trailing, max 2000 bars
cfg = BacktestConfig(
    target_r_multiple=2.5,
    max_holding_bars=2000,
    use_trailing_stop=True,
    apply_borrow_financing=True
)
engine.backtester.config = cfg

fetcher = BinanceFetcher()

def run_reverse_matrix():
    print("================================================================")
    print("🔄 REVERSE TIMEFRAME MATRIX DISCOVERY")
    print(f"Evaluating {len(REVERSE_STYLES)} Inverse Styles Across {len(ASSETS)} Assets")
    print("================================================================\n")
    
    results = {}
    best_overall = {}

    for style_name, tfs in REVERSE_STYLES.items():
        htf = tfs['htf']
        mtf = tfs['mtf']
        ltf = tfs['ltf']
        
        print(f"--- Testing Reverse Style: {style_name} ({htf} -> {mtf} -> {ltf}) ---")
        style_results = []

        # Make sure data exists
        try:
            for asset in ASSETS:
                fetcher.fetch_real_candles(symbol=asset, timeframe=htf, limit=1000)
                fetcher.fetch_real_candles(symbol=asset, timeframe=mtf, limit=5000)
                fetcher.fetch_real_candles(symbol=asset, timeframe=ltf, limit=20000)
        except Exception as e:
            print(f"  [ERROR] Data fetch failed for {style_name}: {e}")
            continue

        for asset in ASSETS:
            genome = ReverseIndicatorBlueprint.construct_genome(asset, ltf=ltf, mtf=mtf, htf=htf)
            
            try:
                # Engine will automatically load data for ltf, mtf, htf from cache
                res = engine.evaluate(
                    genome=genome,
                    signal_fn=lambda df, a=asset: ReverseIndicatorBlueprint.generate_signal(
                        df, a, mtf=mtf, htf=htf
                    ),
                    symbol=asset,
                    timeframe=ltf,
                    partitions=[('ALL_DATA', '2000-01-01', '2030-01-01')]
                )
                
                if res.status == "MEASURED" and res.overall:
                    net_edge = res.overall.performance.net_edge_r
                    wr = res.overall.performance.win_rate
                    pf = res.overall.performance.profit_factor
                    tc = res.overall.performance.trade_count
                    
                    if tc < 30:
                        print(f"  {asset:<10} -> [FAILED] INSUFFICIENT_TRADES ({tc})")
                        continue
                        
                    print(f"  {asset:<10} -> NET: {net_edge:7.4f}R | WR: {wr:5.2f}% | PF: {pf:.2f} | Trades: {tc}")
                    
                    style_results.append({
                        'asset': asset,
                        'net_edge': net_edge,
                        'win_rate': wr,
                        'profit_factor': pf,
                        'trades': tc
                    })
                else:
                    print(f"  {asset:<10} -> [FAILED] {res.status}")
                    continue
                
            except Exception as e:
                import traceback
                print(f"  {asset:<10} -> [ERROR] {e}")
                print(traceback.format_exc())

        # Find best for this style
        if style_results:
            style_results.sort(key=lambda x: x['net_edge'], reverse=True)
            winner = style_results[0]
            print(f"  => WINNER for {style_name}: {winner['asset']} (+{winner['net_edge']:.4f}R)\n")
            best_overall[style_name] = winner
            results[style_name] = style_results
        else:
            print(f"  => NO VALID STRATEGIES FOR {style_name}\n")
            results[style_name] = []
            best_overall[style_name] = None

    # Write results
    os.makedirs('research/results', exist_ok=True)
    with open('research/results/REVERSE_MATRIX_RESULTS.json', 'w') as f:
        json.dump({'best_overall': best_overall, 'all_results': results}, f, indent=4)
        
    print("=======================================================")
    print("REVERSE MATRIX DISCOVERY COMPLETE")
    print("=== BEST STRATEGY PER INVERSE STYLE ===")
    for style_name, winner in best_overall.items():
        if winner:
            print(f"{style_name:<15}: {winner['asset']:<10} | NET: +{winner['net_edge']:.4f}R | WR: {winner['win_rate']:.2f}%")
        else:
            print(f"{style_name:<15}: NONE")

if __name__ == '__main__':
    run_reverse_matrix()
