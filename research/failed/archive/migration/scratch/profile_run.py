import cProfile
import pstats
from market_data.warehouse_loader import WarehouseLoader
from research.replayer.causal_replayer import CausalReplayer
from risk_engine.contracts.risk_config import RiskConfig

def run_short():
    htf_candles = WarehouseLoader.load_history("BTC/USDT", "1d", 50000)
    mtf_candles = WarehouseLoader.load_history("BTC/USDT", "4h", 50000)
    ltf_candles = WarehouseLoader.load_history("BTC/USDT", "1h", 50000)
    
    # Only use 500 LTF candles
    ltf_candles = ltf_candles[:500]

    risk_config = RiskConfig(
        max_risk_fraction=0.01,
        min_rr_floor=4.0,
        enable_circuit_breakers=False,
        enable_exposure_limits=False,
        enable_news_filter=False
    )

    replayer_a = CausalReplayer(
        timeframe_set_id="SET_3",
        initial_balance=10000.0,
        maker_fee_rate=0.0000,
        taker_fee_rate=0.0005,
        slippage_bps=5.0,
        enable_mtf_trailing=False,
        cache_htf_mtf=True,
        risk_config=risk_config
    )
    result_a = replayer_a.run(
        symbol="BTCUSDT",
        htf_candles=htf_candles,
        mtf_candles=mtf_candles,
        ltf_candles=ltf_candles
    )

if __name__ == '__main__':
    cProfile.run("run_short()", "scratch/baseline.prof")
    p = pstats.Stats("scratch/baseline.prof")
    p.sort_stats("tottime").print_stats(30)
