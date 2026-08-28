"""
Product 07 — Production Service & Reliability
Interactive CLI Launcher for Live & Demo/Testnet Trading.
Prompts user to select broker, account mode (Live vs Demo), credentials, and asset whitelists.
"""

import os
import sys
from typing import Tuple, Dict, Any, List
from execution_gateway.contracts.broker_config import BrokerConfig, BrokerType
from execution_gateway.broker_factory import BrokerFactory
from execution_gateway.interfaces.base_gateway import BaseGateway


class CLILauncher:
    """
    Handles interactive user prompts for Live vs Demo account selection and broker configuration.
    """

    BROKER_CHOICES = {
        "1": (BrokerType.PAPER, "Institutional Paper Simulator (Internal Zero-Risk Sandbox)"),
        "2": (BrokerType.BINANCE, "Binance USDT-M Futures (Testnet / Live)"),
        "3": (BrokerType.EXNESS_MT5, "Exness MetaTrader 5 (Demo / Real)"),
        "4": (BrokerType.VANTAGE_MT5, "Vantage MetaTrader 5 (Demo / Live)"),
        "5": (BrokerType.BYBIT, "Bybit Unified Derivatives (Testnet / Live)"),
        "6": (BrokerType.OKX, "OKX Futures / Swap (Demo / Live)"),
        "7": (BrokerType.PEPPERSTONE_MT5, "Pepperstone MetaTrader 5 (Demo / Live)"),
        "8": (BrokerType.IC_MARKETS_MT5, "IC Markets MetaTrader 5 (Demo / Live)")
    }

    @staticmethod
    def prompt_user_config() -> Tuple[BrokerConfig, Dict[str, Any]]:
        print("\n" + "=" * 80)
        print("     APEX INSTITUTIONAL 24/7/365 AUTONOMOUS TRADING PLATFORM LAUNCHER")
        print("=" * 80 + "\n")

        # 1. Select Broker
        print("📌 [1] SELECT YOUR BROKER / EXCHANGE:")
        for k, (b_type, desc) in CLILauncher.BROKER_CHOICES.items():
            print(f"   [{k}] {desc}")
        
        choice = input("\nEnter choice [1-8] (default: 1): ").strip() or "1"
        selected_broker, desc = CLILauncher.BROKER_CHOICES.get(choice, (BrokerType.PAPER, "Paper"))

        # 2. Select Account Mode (DEMO vs LIVE)
        print("\n" + "-" * 80)
        print("📌 [2] SELECT ACCOUNT EXECUTION MODE:")
        print("   [1] 🟢 DEMO / TESTNET / PAPER ACCOUNT (Practice & Zero Risk)")
        print("   [2] 🔴 LIVE REAL CAPITAL ACCOUNT (Real Money Trading)")
        mode_choice = input("\nEnter choice [1 or 2] (default: 1): ").strip() or "1"
        is_live = (mode_choice == "2")

        account_id = None
        api_key = None
        api_secret = None
        server_name = None
        symbol_suffix = ""

        if selected_broker == BrokerType.PAPER:
            print("\n✅ Initializing Paper Simulation Engine.")
        
        elif selected_broker in [BrokerType.EXNESS_MT5, BrokerType.VANTAGE_MT5, BrokerType.PEPPERSTONE_MT5, BrokerType.IC_MARKETS_MT5]:
            mode_label = "REAL" if is_live else "DEMO"
            print(f"\n🔑 Configuring {selected_broker.value} ({mode_label}):")
            account_id = input(f"Enter MT5 Account Number ({mode_label}): ").strip()
            api_secret = input(f"Enter MT5 Password ({mode_label}): ").strip()
            default_server = f"{selected_broker.value.split('_')[0].capitalize()}-{'Real' if is_live else 'Trial'}"
            server_name = input(f"Enter Server Name (e.g. '{default_server}'): ").strip() or default_server
            suffix_prompt = input("Enter symbol suffix if required (e.g. 'm' for Exness mini, '+' for Vantage, or leave empty): ").strip()
            symbol_suffix = suffix_prompt

        elif selected_broker in [BrokerType.BINANCE, BrokerType.BYBIT, BrokerType.OKX]:
            mode_label = "LIVE" if is_live else "TESTNET"
            print(f"\n🔑 Configuring {selected_broker.value} ({mode_label}):")
            api_key = input(f"Enter API Key ({mode_label}): ").strip()
            api_secret = input(f"Enter API Secret ({mode_label}): ").strip()

        # 3. Strategy Configuration
        print("\n" + "-" * 80)
        print("📌 [3] SELECT STRATEGY ALPHA ENGINE:")
        print("   [1] ⭐ HYPOTHESIS B ONLY (Continuation Riding - 2.97 PF, +1.74R Expectancy) [RECOMMENDED]")
        print("   [2] 🔄 FULL DUAL STRATEGY (Hypothesis A Pullback + Hypothesis B Continuation)")
        strat_choice = input("\nEnter choice [1 or 2] (default: 1): ").strip() or "1"
        hyp_b_only = (strat_choice == "1")

        # 4. Risk per trade
        risk_input = input("\n📌 [4] Enter Risk Per Trade in % (default: 1.0%): ").strip() or "1.0"
        try:
            risk_pct = float(risk_input) / 100.0
        except ValueError:
            risk_pct = 0.01

        # 5. Asset Whitelist
        print("\n📌 [5] ASSET WHITELIST (Only these symbols will be traded):")
        print("   Default Whitelist: ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BTC/USD', 'ETH/USD', 'EUR/USD', 'XAU/USD']")
        custom_assets = input("Press ENTER to use defaults or enter comma-separated symbols: ").strip()
        allowed_symbols = [s.strip() for s in custom_assets.split(",")] if custom_assets else [
            "BTC/USDT", "ETH/USDT", "SOL/USDT", "BTC/USD", "ETH/USD", "EUR/USD", "XAU/USD"
        ]

        broker_config = BrokerConfig(
            broker_type=selected_broker,
            account_id=account_id,
            api_key=api_key,
            api_secret=api_secret,
            server_name=server_name,
            testnet=not is_live,
            symbol_suffix=symbol_suffix,
            allowed_symbols=allowed_symbols
        )

        runtime_options = {
            "is_live": is_live,
            "hyp_b_only": hyp_b_only,
            "risk_pct": risk_pct,
            "broker_desc": desc
        }

        print("\n" + "=" * 80)
        print("                    LAUNCH CONFIGURATION SUMMARY")
        print("=" * 80)
        print(f"  • Broker:         {selected_broker.value} ({'🔴 LIVE REAL MONEY' if is_live else '🟢 DEMO / TESTNET'})")
        print(f"  • Strategy Mode:  {'Hypothesis B (Continuation Only)' if hyp_b_only else 'Dual Strategy (Hyp A + B)'}")
        print(f"  • Risk / Trade:   {risk_pct*100:.1f}%")
        print(f"  • Whitelist:      {', '.join(allowed_symbols)}")
        print(f"  • Profit-Lock:    ACTIVE (+1.0R -> +0.25R Ratchet)")
        print(f"  • Execution:      CONTINUOUS 24/7/365 UNTIL STOPPED")
        print("=" * 80 + "\n")

        confirm = input("Type 'START' to launch the autonomous 24/7 engine: ").strip().upper()
        if confirm != "START":
            print("❌ Launch cancelled by user.")
            sys.exit(0)

        return broker_config, runtime_options
