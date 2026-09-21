import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from market_data.data_manager import DataManager
from market_data.binance_fetcher import BinanceFetcher

ALL_ASSETS = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "LINK", "LTC"]

def fetch_all():
    print("Fetching historical funding rates for 10 assets...")
    for asset in ALL_ASSETS:
        symbol = f"{asset}/USDT"
        # Force fetch
        BinanceFetcher.fetch_historical_funding_rates(symbol)
        rates = DataManager.get_funding_rates(symbol)
        if rates:
            print(f"Loaded {len(rates)} funding rates for {symbol}.")
        else:
            print(f"Failed to load funding rates for {symbol}.")
            
if __name__ == "__main__":
    fetch_all()
