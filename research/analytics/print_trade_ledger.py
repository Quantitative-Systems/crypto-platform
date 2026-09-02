import json
from datetime import datetime, timezone

def main():
    with open("/home/mrcn2/crypto-platform/scratch/unified_matrix_trade_ledger.json") as f:
        trades = json.load(f)

    print("=" * 165)
    print("PHASE 3C / 4: MACHINE-READABLE TRADE LEDGER (ALL TRADES ACROSS 15 STREAMS)")
    print("=" * 165)
    print(f"{'#':2s} | {'Stream':10s} | {'Context':12s} | {'Trade ID':32s} | {'Dir':12s} | {'Entry (UTC)':16s} | {'Entry P':9s} | {'Stop P':9s} | {'Target P':9s} | {'Planned RR':10s} | {'Exit P':9s} | {'Exit Reason':18s} | {'Gross R':7s} | {'Fric USD':8s} | {'Net R':7s} | {'Net PnL':9s}")
    print("-" * 185)
    
    for idx, t in enumerate(trades, 1):
        dt_str = datetime.fromtimestamp(t['entry_timestamp'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M') if t.get('entry_timestamp') else 'None'
        ctx_str = t.get('htf_context', 'UNKNOWN')
        print(f"{idx:2d} | {t['stream']:10s} | {ctx_str:12s} | {t['trade_id']:32s} | {t['direction']:12s} | {dt_str:16s} | {t['entry_price']:9.2f} | {t['stop']:9.2f} | {t['target']:9.2f} | {t['planned_rr']:10.2f} | {t['exit_price']:9.2f} | {str(t['exit_reason']):18s} | {t['gross_r']:+7.2f} | ${t['friction']:7.2f} | {t['net_r']:+7.2f} | ${t['net_pnl']:+9.2f}")

if __name__ == "__main__":
    main()
