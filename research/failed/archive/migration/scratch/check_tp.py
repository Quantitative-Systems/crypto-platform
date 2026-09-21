import sys
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

print(f"{'Symbol':<10} | {'TP (1:10)':<10} | {'TS (Step)':<10} | {'SL (Stop)':<10} | {'TIME (Max)':<10}")
print("-" * 60)

for asset in ["LTC/USDT", "DOGE/USDT", "XRP/USDT", "BNB/USDT"]:
    genome_mtf = MTFBlueprint.construct_mtf_genome(asset, ltf="5m", mtf="15m", htf="4h")
    res_mtf = engine.evaluate(
        genome=genome_mtf,
        signal_fn=lambda df: MTFBlueprint.generate_mtf_signal(df, asset, mtf="15m", htf="4h"),
        symbol=asset,
        timeframe="5m",
        partitions=[("ALL_DATA", "2000-01-01", "2030-01-01")]
    )

    trades = res_mtf.trades
    tp = sum(1 for t in trades if t.exit_reason == "TAKE_PROFIT")
    ts = sum(1 for t in trades if t.exit_reason == "TRAILING_STOP")
    sl = sum(1 for t in trades if t.exit_reason == "STOP_LOSS")
    time_stop = sum(1 for t in trades if t.exit_reason == "TIME_STOP")
    print(f"{asset:<10} | {tp:<10} | {ts:<10} | {sl:<10} | {time_stop:<10}")

