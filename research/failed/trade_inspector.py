"""
Product 01: Crypto Platform - Post-Mortem Trade Inspector
Queries research_vault.db to audit executed trades and print granular diagnostic breakdowns.
"""

import sys
import os
import sqlite3

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from research.research_db import DB_PATH


def inspect_recent_trades(limit: int = 20):
    print("==========================================================================================================")
    print(f"     PRODUCT 01: POST-MORTEM TRADE INSPECTOR AUDIT (LAST {limit} TRADES)")
    print("==========================================================================================================\n")

    if not os.path.exists(DB_PATH):
        print("⚠️ No research_vault.db found. Run multi_asset_runner.py first.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT trade_id, symbol, action, strategy_type, raw_entry_price, fill_entry_price,
               exit_price, stop_loss, take_profit, position_size, dollar_risk, initial_rr,
               pnl_usd, friction_cost_usd, exit_reason, entry_timestamp
        FROM research_trades
        ORDER BY trade_id DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("  • No trades recorded in research_vault.db yet.")
        return

    print(f"{'ID':<4} | {'SYMBOL':<10} | {'ACTION':<5} | {'STRATEGY':<18} | {'ENTRY ($)':<10} | {'EXIT ($)':<10} | {'SL ($)':<10} | {'R:R':<6} | {'NET PNL ($)':<12} | {'FRICTION ($)':<10} | {'REASON':<8}")
    print("-" * 115)

    for r in rows:
        trade_id, symbol, action, strat, entry_p, fill_entry, exit_p, sl, tp, pos_sz, dollar_risk, rr, pnl, friction, exit_reason, ts = r
        pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
        print(f"{trade_id:<4} | {symbol:<10} | {action:<5} | {strat:<18} | ${entry_p:<9.2f} | ${exit_p:<9.2f} | ${sl:<9.2f} | {rr:<6.1f} | {pnl_str:<12} | ${friction:<9.2f} | {exit_reason:<8}")

    print("==========================================================================================================")


if __name__ == "__main__":
    inspect_recent_trades(20)