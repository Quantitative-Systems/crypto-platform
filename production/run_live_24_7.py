"""
Product 07 — Production Service & Reliability
Master 24/7/365 Autonomous Trading Daemon.
Runs continuously until user stops it, managing live multi-asset feeds, risk firewall,
execution gateway, state persistence, and real-time terminal HUD.
"""

import os
import sys
import time
import signal
import asyncio
import argparse
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from execution_gateway.contracts.broker_config import BrokerConfig, BrokerType
from execution_gateway.broker_factory import BrokerFactory
from execution_gateway.symbol_normalizer import SymbolNormalizer
from portfolio_engine.contracts.portfolio_state import PortfolioRiskConfig
from production.cli_launcher import CLILauncher
from production.live_trader import LiveTradingEngine
from market_data.warehouse_loader import WarehouseLoader
from market_data.binance_fetcher import BinanceFetcher


class LiveTradingDaemon:
    """
    Continuous 24/7/365 Live Trading Daemon.
    """

    def __init__(self, broker_config: BrokerConfig, runtime_options: Optional[Dict[str, Any]] = None):
        self.broker_config = broker_config
        self.options = runtime_options or {}
        self.is_live = self.options.get("is_live", False)
        self.hyp_b_only = self.options.get("hyp_b_only", True)
        self.risk_pct = self.options.get("risk_pct", 0.01)
        
        # Setup gateway & normalizer
        self.gateway = BrokerFactory.create_gateway(self.broker_config)
        self.normalizer = SymbolNormalizer(self.broker_config)
        
        portfolio_cfg = PortfolioRiskConfig(
            max_risk_per_trade_pct=self.risk_pct,
            max_total_portfolio_risk_pct=0.03,
            max_asset_concentration_pct=0.015
        )
        
        self.engine = LiveTradingEngine(
            gateway=self.gateway,
            enable_regime_filter=True,
            enable_profit_lock=True,
            lockin_r=1.0,
            giveback_r=0.75,
            portfolio_config=portfolio_cfg,
            state_db_path="production_live_state.db"
        )
        
        self.is_running = False
        self.start_time = time.time()
        self._shutdown_event = asyncio.Event()

    def _setup_signal_handlers(self) -> None:
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))
            except (NotImplementedError, RuntimeError):
                # Fallback for platforms without add_signal_handler
                signal.signal(sig, lambda s, f: asyncio.create_task(self.stop()))

    async def start(self) -> None:
        self.is_running = True
        self._setup_signal_handlers()
        await self.engine.start()
        
        mode_str = "🔴 LIVE CAPITAL" if self.is_live else "🟢 DEMO / TESTNET"
        print("\n" + "=" * 90)
        print(f"      🚀 APEX INSTITUTIONAL 24/7/365 ENGINE ACTIVE [{mode_str}]")
        print(f"      Broker: {self.broker_config.broker_type.value} | Strategy: {'Hyp B (Continuation)' if self.hyp_b_only else 'Dual (Hyp A+B)'}")
        print(f"      Whitelist: {', '.join(self.broker_config.allowed_symbols)}")
        print("      Press Ctrl+C at any time to gracefully stop the engine and persist state.")
        print("=" * 90 + "\n")

        # Run continuous execution loop
        await self._main_event_loop()

    async def stop(self) -> None:
        if not self.is_running:
            return
        print("\n🛑 [SHUTDOWN INITIATED]: Gracefully stopping 24/7 engine and persisting state to disk...")
        self.is_running = False
        await self.engine.stop()
        self._shutdown_event.set()
        print("✅ [SHUTDOWN COMPLETE]: All state persisted atomically. Zero state drift.")

    async def _main_event_loop(self) -> None:
        """
        Main 24/7 asynchronous loop polling live market feeds and updating HUD.
        """
        cycle_count = 0
        fetcher = BinanceFetcher()

        while self.is_running and not self._shutdown_event.is_set():
            try:
                cycle_count += 1
                now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
                uptime_sec = int(time.time() - self.start_time)
                hrs, rem = divmod(uptime_sec, 3600)
                mins, secs = divmod(rem, 60)
                uptime_str = f"{hrs:02d}h {mins:02d}m {secs:02d}s"

                # 1. Process tick & candle updates for each allowed symbol
                for canon_symbol in self.broker_config.allowed_symbols:
                    if not self.is_running:
                        break
                    
                    # Convert to Binance pair for public price feed
                    binance_pair = canon_symbol.replace("/", "").upper()
                    if binance_pair.endswith("USD") and not binance_pair.endswith("USDT"):
                        binance_pair = binance_pair.replace("USD", "USDT")
                    
                    # Fetch latest live price
                    try:
                        live_price = fetcher.get_ticker(binance_pair)
                        if isinstance(live_price, (int, float)) and live_price > 0:
                            # Feed tick to engine (audits profit-locks and stops)
                            await self.engine.on_tick(
                                symbol=canon_symbol,
                                current_price=float(live_price),
                                high=float(live_price),
                                low=float(live_price)
                            )
                    except Exception:
                        pass

                # 2. Render HUD Dashboard every 10 cycles (~10 seconds)
                if cycle_count % 5 == 0:
                    nav = self.engine.portfolio_coordinator.state.nav
                    active_pos_count = len(self.engine.portfolio_coordinator.state.active_positions)
                    heat_pct = self.engine.portfolio_coordinator.state.total_risk_committed_pct * 100.0
                    mode_tag = "🔴 LIVE" if self.is_live else "🟢 DEMO"
                    
                    sys.stdout.write(
                        f"\r[{now_str}] [{mode_tag}] Uptime: {uptime_str} | NAV: ${nav:,.2f} | "
                        f"Active Positions: {active_pos_count} | Heat: {heat_pct:.1f}%/3.0% | Status: RUNNING 24/7/365 "
                    )
                    sys.stdout.flush()

                # Sleep interval between tick polls
                await asyncio.sleep(2.0)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"\n⚠️ [DAEMON LOOP]: Transient polling notice: {e}")
                await asyncio.sleep(5.0)


def main():
    parser = argparse.ArgumentParser(description="Apex Institutional 24/7/365 Trading Daemon")
    parser.add_argument("--non-interactive", action="store_true", help="Run with CLI arguments without interactive prompts")
    parser.add_argument("--broker", type=str, default="PAPER", help="Broker type: PAPER, BINANCE, EXNESS_MT5, VANTAGE_MT5, BYBIT, OKX")
    parser.add_argument("--mode", type=str, default="demo", choices=["live", "demo"], help="Execution mode: live or demo")
    parser.add_argument("--account-id", type=str, default=None, help="Account ID or MT5 login")
    parser.add_argument("--api-key", type=str, default=None, help="API key")
    parser.add_argument("--api-secret", type=str, default=None, help="API secret or MT5 password")
    parser.add_argument("--server", type=str, default=None, help="MT5 server name")
    parser.add_argument("--risk", type=float, default=1.0, help="Risk per trade in percent (default: 1.0)")
    parser.add_argument("--symbols", type=str, default=None, help="Comma-separated allowed symbols whitelist")
    
    args = parser.parse_args()

    if args.non_interactive:
        b_type = getattr(BrokerType, args.broker.upper(), BrokerType.PAPER)
        is_live = (args.mode.lower() == "live")
        allowed = [s.strip() for s in args.symbols.split(",")] if args.symbols else [
            "BTC/USDT", "ETH/USDT", "SOL/USDT", "BTC/USD", "EUR/USD", "XAU/USD"
        ]
        
        broker_cfg = BrokerConfig(
            broker_type=b_type,
            account_id=args.account_id,
            api_key=args.api_key,
            api_secret=args.api_secret,
            server_name=args.server,
            testnet=not is_live,
            allowed_symbols=allowed
        )
        runtime_opts = {
            "is_live": is_live,
            "hyp_b_only": True,
            "risk_pct": args.risk / 100.0,
            "broker_desc": f"{b_type.value} ({'LIVE' if is_live else 'DEMO'})"
        }
    else:
        broker_cfg, runtime_opts = CLILauncher.prompt_user_config()

    daemon = LiveTradingDaemon(broker_config=broker_cfg, runtime_options=runtime_opts)
    
    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        print("\n👋 24/7/365 Live Engine stopped by user.")


if __name__ == "__main__":
    main()
