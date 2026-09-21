import sys
from pathlib import Path
import time

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from market_data.data_manager import ALL_ASSETS
from market_data.binance_fetcher import BinanceFetcher
from market_data.dataset_manifest import DatasetManifestManager

def main():
    timeframes = ["1d", "4h", "1h", "15m"]
    fetcher = BinanceFetcher()
    
    print("=== Phase 1: Fetching Market Data ===")
    for asset in ALL_ASSETS:
        symbol = f"{asset}/USDT"
        for tf in timeframes:
            print(f"Fetching {symbol} {tf}...")
            try:
                # 50,000 limit for robust historical discovery
                candles = fetcher.fetch_real_candles(symbol=symbol, timeframe=tf, limit=50000)
                print(f"  -> Fetched {len(candles)} candles.")
                # Give a small pause to respect rate limits
                time.sleep(0.5)
            except Exception as e:
                print(f"  -> ERROR fetching {symbol} {tf}: {e}")

    print("\n=== Phase 2: Auditing and Certifying Datasets ===")
    manifests = DatasetManifestManager.audit_and_save_manifests()
    DatasetManifestManager.print_manifest_summary(manifests)
    print("\nFetch and certification complete.")

if __name__ == "__main__":
    main()
