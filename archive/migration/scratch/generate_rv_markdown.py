import json

def generate_md():
    with open("research/results/RELATIVE_VALUE_BASELINE_AUDIT.json", "r") as f:
        data = json.load(f)
        
    md = "# Relative Value Baseline Econometrics Evidence\n\n"
    md += f"**Platform:** {data['platform']}\n"
    md += f"**Experiment:** {data['experiment']}\n"
    md += f"**Generated UTC:** {data['generated_utc']}\n\n"
    
    md += "## Summary\n"
    md += f"- **Total Candidates:** {data['summary']['total_candidates']}\n"
    md += f"- **Qualified Candidates:** {data['summary']['qualified_candidates']}\n"
    md += f"- **Falsified Candidates:** {data['summary']['falsified_candidates']}\n"
    md += f"- **Fragile Candidates:** {data['summary']['fragile_candidates']}\n\n"
    
    for pair_id, details in data["pairs_evaluated"].items():
        md += f"### {pair_id} ({details['symbol_a']} / {details['symbol_b']})\n"
        md += f"- **Verdict:** `{details['research_verdict']}`\n"
        for reason in details['verdict_reasons']:
            md += f"  - {reason}\n"
        md += "\n#### Cointegration Metrics\n"
        md += f"- Hedge Ratio (Beta): {details['cointegration']['hedge_ratio_beta']:.4f}\n"
        md += f"- Engle-Granger p-value: {details['cointegration']['engle_granger_p_value']:.4f}\n"
        md += f"- Is Engle-Granger Cointegrated: {details['cointegration']['is_engle_granger_cointegrated']}\n"
        md += f"- Johansen Trace Statistic: {details['cointegration']['johansen_trace_statistic']:.4f}\n"
        md += f"- Is Johansen Cointegrated: {details['cointegration']['is_johansen_cointegrated']}\n"
        md += f"- Half-Life: {details['cointegration']['half_life_bars']:.2f} bars\n\n"
        
        oos = details["oos_sample"]
        md += "#### OOS Sample Performance\n"
        md += f"- Total Trades: {oos['total_trades']}\n"
        md += f"- Win Rate: {oos['win_rate_pct']:.2f}%\n"
        md += f"- Total Net R: {oos['total_net_r']:.2f}\n"
        md += f"- Profit Factor: {oos['profit_factor_r']:.2f}\n"
        md += f"- Max Drawdown R: {oos['max_drawdown_r']:.2f}\n"
        md += f"- Total Friction Drag R: {oos['total_friction_drag_r']:.2f}\n\n"
        
    with open("research/results/RV_ECONOMETRICS_EVIDENCE.md", "w") as f:
        f.write(md)

if __name__ == "__main__":
    generate_md()
