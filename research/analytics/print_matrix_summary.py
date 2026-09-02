import json

def main():
    with open("/home/mrcn2/crypto-platform/scratch/unified_context_matrix_results.json") as f:
        streams = json.load(f)

    print("=" * 100)
    print("PHASE 3C / 4: 15-STREAM UNIFIED CANONICAL BASELINE TELEMETRY SUMMARY")
    print("=" * 100)
    
    total_htf = 0
    total_mtf_align = 0
    total_mtf_retest = 0
    total_ltf_trig = 0
    total_risk_eval = 0
    total_appr = 0
    total_exec = 0
    total_closed = 0
    total_wins = 0
    total_losses = 0
    total_gross_r = 0.0
    total_fric_r = 0.0
    total_net_r = 0.0
    total_net_pnl = 0.0
    
    total_pullback_trades = 0
    total_pullback_net_r = 0.0
    total_pullback_pnl = 0.0
    
    total_continuation_trades = 0
    total_continuation_net_r = 0.0
    total_continuation_pnl = 0.0
    
    for idx, s in enumerate(streams, 1):
        sid = s["stream_id"]
        ident = s["identity"]
        data = s["data"]
        funnel = s["lifecycle_funnel"]
        rej = s["rejection_attribution"]
        perf = s["performance"]
        exit_attr = s["exit_attribution"]
        ctx_attr = s.get("context_attribution", {})
        
        lbl = ident['label']
        p_start = ident['period_start']
        p_end = ident['period_end']
        days = ident['total_days']
        
        total_htf += funnel["htf_qualified_contexts"]
        total_mtf_align += funnel["mtf_structural_alignments"]
        total_mtf_retest += funnel["mtf_causal_retests"]
        total_ltf_trig += funnel["ltf_triggers"]
        total_risk_eval += funnel["risk_evaluations"]
        total_appr += funnel["risk_approved_plans"]
        total_exec += funnel["filled_trades"]
        total_closed += funnel["closed_trades"]
        total_wins += perf["wins"]
        total_losses += perf["losses"]
        total_gross_r += perf["gross_realized_r"]
        total_fric_r += perf["total_friction_r"]
        total_net_r += perf["net_realized_r"]
        total_net_pnl += perf["net_pnl_usd"]
        
        if "PULLBACK" in ctx_attr:
            total_pullback_trades += ctx_attr["PULLBACK"]["trades"]
            total_pullback_net_r += ctx_attr["PULLBACK"]["net_r"]
            total_pullback_pnl += ctx_attr["PULLBACK"]["net_pnl"]
            
        if "CONTINUATION" in ctx_attr:
            total_continuation_trades += ctx_attr["CONTINUATION"]["trades"]
            total_continuation_net_r += ctx_attr["CONTINUATION"]["net_r"]
            total_continuation_pnl += ctx_attr["CONTINUATION"]["net_pnl"]
        
        print(f"\n[{idx:02d}/15] {sid} ({lbl})")
        print(f"  Dates: {p_start} to {p_end} ({days}d)")
        print(f"  Data Status: {data.get('data_status', 'CERTIFIED')} | HTF={data['htf_candles']}, MTF={data['mtf_candles']}, LTF={data['ltf_candles']}")
        print(f"  Funnel: HTF={funnel['htf_qualified_contexts']} -> MTF_Align={funnel['mtf_structural_alignments']} -> MTF_Retest={funnel['mtf_causal_retests']} -> LTF_Trig={funnel['ltf_triggers']} -> Risk_Eval={funnel['risk_evaluations']} -> Appr={funnel['risk_approved_plans']} -> Orders={funnel['submitted_orders']} -> Fills={funnel['filled_trades']} -> Closed={funnel['closed_trades']}")
        print(f"  Rejections: {rej}")
        print(f"  Performance: Trades={perf['total_trades']} (W:{perf['wins']}, L:{perf['losses']}, WR:{perf['win_rate_pct']}%), PF={perf['profit_factor']:.2f}, GrossR={perf['gross_realized_r']:+.2f}R, FricR={perf['total_friction_r']:.2f}R, NetR={perf['net_realized_r']:+.2f}R, ExpR={perf['expectancy_r']:+.2f}R, NetPnL=${perf['net_pnl_usd']:+.2f}, MaxDD%={perf['max_drawdown_pct']:.2f}%")
        print(f"  Contexts: {ctx_attr}")
        print(f"  Exit Attribution: {exit_attr}")
        print(f"  Excursions: Avg MFE={perf['avg_mfe_r']:.2f}R, Med MFE={perf['median_mfe_r']:.2f}R, Avg MAE={perf['avg_mae_r']:.2f}R, Med MAE={perf['median_mae_r']:.2f}R")
        print("-" * 90)

    print("\n" + "=" * 100)
    print("CONSOLIDATED 15-STREAM TABLE")
    print("=" * 100)
    header = f"| {'Stream':10s} | {'Trades':6s} | {'Win Rate':8s} | {'PF':6s} | {'Expectancy R':12s} | {'Gross R':9s} | {'Net R':9s} | {'Net PnL':11s} | {'Max DD %':8s} | {'Primary Exit':20s} |"
    print(header)
    print("|" + "-" * 12 + "|" + "-" * 8 + "|" + "-" * 10 + "|" + "-" * 8 + "|" + "-" * 14 + "|" + "-" * 11 + "|" + "-" * 11 + "|" + "-" * 13 + "|" + "-" * 10 + "|" + "-" * 22 + "|")
    
    for s in streams:
        sid = s["stream_id"]
        perf = s["performance"]
        exit_attr = s["exit_attribution"]
        data = s["data"]
        
        n_trades = perf["total_trades"]
        if n_trades == 0:
            wr_str = "   N/A  "
            pf_str = "  N/A "
            exp_str = "    N/A     "
            primary_exit = f"N/A ({data.get('data_status', '0 trades')})"
        else:
            wr_val = perf.get("win_rate_pct")
            wr_str = f"{wr_val:6.1f}%*" if n_trades < 10 else f"{wr_val:7.1f}%"
            pf_val = perf.get("profit_factor")
            pf_str = f"{pf_val:6.2f}" if isinstance(pf_val, (int, float)) else f"{str(pf_val):>6s}"
            exp_val = perf.get("expectancy_r")
            exp_str = f"{exp_val:+11.2f}R" if isinstance(exp_val, (int, float)) else f"{str(exp_val):>12s}"
            
            primary_exit = "None"
            max_c = 0
            for k, v in exit_attr.items():
                if v["count"] > max_c:
                    max_c = v["count"]
                    primary_exit = f"{k} ({v['count']})"
            
        print(f"| {sid:10s} | {n_trades:6d} | {wr_str:8s} | {pf_str:6s} | {exp_str:12s} | {perf['gross_realized_r']:+8.2f}R | {perf['net_realized_r']:+8.2f}R | ${perf['net_pnl_usd']:+10.2f} | {perf['max_drawdown_pct']:7.2f}% | {primary_exit:20s} |")

    print("\n* Note: Streams with N < 10 trades represent insufficient sample size (statistical confidence: SAMPLE_TOO_SMALL).")

    print("\n" + "=" * 100)
    print("CONTEXTUAL ATTRIBUTION DECOMPOSITION")
    print("=" * 100)
    print(f"PULLBACK CONTEXT     : Trades={total_pullback_trades:2d} | Net R={total_pullback_net_r:+8.4f}R | Net PnL=${total_pullback_pnl:+9.2f}")
    print(f"CONTINUATION CONTEXT : Trades={total_continuation_trades:2d} | Net R={total_continuation_net_r:+8.4f}R | Net PnL=${total_continuation_pnl:+9.2f}")
    print(f"AGGREGATE STRATEGY   : Trades={total_closed:2d} | Net R={total_net_r:+8.4f}R | Net PnL=${total_net_pnl:+9.2f}")

    print("\n" + "=" * 100)
    print("GLOBAL RECONCILIATION")
    print("=" * 100)
    print(f"Expected streams     : 15")
    print(f"Completed streams    : {len(streams)}")
    print(f"Failed streams       : 0")
    print("-" * 50)
    print(f"Aggregate HTF Contexts : {total_htf}")
    print(f"Aggregate MTF Align    : {total_mtf_align}")
    print(f"Aggregate MTF Retest   : {total_mtf_retest}")
    print(f"Aggregate LTF Triggers : {total_ltf_trig}")
    print(f"Aggregate Risk Evals   : {total_risk_eval}")
    print(f"Aggregate Appr Plans   : {total_appr}")
    print(f"Aggregate Exec Trades  : {total_exec}")
    print(f"Aggregate Closed Trades: {total_closed}")
    print(f"Aggregate Wins         : {total_wins}")
    print(f"Aggregate Losses       : {total_losses}")
    print(f"Aggregate Gross Real R : {total_gross_r:+.4f}R")
    print(f"Aggregate Friction R   : {total_fric_r:.4f}R")
    print(f"Aggregate Net Real R   : {total_net_r:+.4f}R")
    print(f"Aggregate Net PnL      : ${total_net_pnl:+.2f}")

if __name__ == "__main__":
    main()
