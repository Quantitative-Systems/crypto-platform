import sys
import json
sys.path.append('.')
from research.alpha_matrix.blueprints.mtf_blueprint import MTFBlueprint
from research.economic_evaluation_engine import EconomicEvaluationEngine, BacktestConfig

engine = EconomicEvaluationEngine()
cfg = BacktestConfig(
    target_r_multiple=10.0, 
    max_holding_bars=100, 
    use_trailing_stop=True,
    apply_borrow_financing=True
)
engine.backtester.config = cfg

STYLES = {
    "MICRO_SCALPING": {"ltf": "1m", "mtf": "5m", "htf": "15m"},
    "SCALPING": {"ltf": "5m", "mtf": "15m", "htf": "1h"},
    "INTRADAY": {"ltf": "15m", "mtf": "1h", "htf": "4h"},
    "SWING": {"ltf": "1h", "mtf": "4h", "htf": "1d"},
    "POSITIONAL": {"ltf": "4h", "mtf": "1d", "htf": "1w"},
    "INVESTING": {"ltf": "1d", "mtf": "1w", "htf": "1M"}
}

ASSETS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT",
    "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "LINK/USDT", "LTC/USDT"
]

print("================================================================")
print("QCP MATRIX DISCOVERY ENGINE")
print(f"Evaluating 6 Styles Across {len(ASSETS)} Assets (60 Total Models)")
print("================================================================")

best_performers = {}
all_results = []

for style_name, tf_config in STYLES.items():
    print(f"\n--- Testing Style: {style_name} ({tf_config['ltf']} -> {tf_config['htf']}) ---")
    
    top_net_edge = -999.0
    top_asset = None
    top_stats = None

    for asset in ASSETS:
        try:
            genome = MTFBlueprint.construct_mtf_genome(asset, ltf=tf_config['ltf'], mtf=tf_config['mtf'], htf=tf_config['htf'])
            res = engine.evaluate(
                genome=genome,
                signal_fn=lambda df, a=asset, config=tf_config: MTFBlueprint.generate_mtf_signal(
                    df, a, mtf=config['mtf'], htf=config['htf']
                ),
                symbol=asset,
                timeframe=tf_config['ltf'],
                partitions=[("ALL_DATA", "2000-01-01", "2030-01-01")]
            )

            if res.status == "MEASURED" and res.overall:
                net = res.overall.performance.net_edge_r
                wr = res.overall.performance.win_rate
                pf = res.overall.performance.profit_factor
                tc = res.overall.performance.trade_count
                
                print(f"  {asset:<10} -> NET: {net:>7.4f}R | WR: {wr:>5.2f}% | PF: {pf:>4.2f} | Trades: {tc}")
                
                if tc >= 10 and net > top_net_edge:
                    top_net_edge = net
                    top_asset = asset
                    top_stats = {"net": net, "wr": wr, "pf": pf, "trades": tc}
                
                all_results.append({
                    "style": style_name,
                    "asset": asset,
                    "net_edge": net,
                    "win_rate": wr,
                    "pf": pf,
                    "trades": tc
                })
            else:
                print(f"  {asset:<10} -> [FAILED] {res.status}")
                
        except Exception as e:
            print(f"  {asset:<10} -> [ERROR] {str(e)}")
            
    if top_asset and top_net_edge > 0:
        best_performers[style_name] = {"asset": top_asset, "stats": top_stats}
        print(f"  => WINNER for {style_name}: {top_asset} (+{top_net_edge:.4f}R)")

print("\n=======================================================")
print("MATRIX DISCOVERY COMPLETE")
print("=== BEST STRATEGY PER STYLE ===")
for style, winner in best_performers.items():
    print(f"{style:<15}: {winner['asset']:<10} | NET: +{winner['stats']['net']:.4f}R | WR: {winner['stats']['wr']:.2f}%")

with open('research/results/STYLE_MATRIX_RESULTS.json', 'w') as f:
    json.dump({
        "best_performers": best_performers,
        "all_results": all_results
    }, f, indent=4)
