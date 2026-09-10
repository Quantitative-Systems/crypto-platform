import os
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

os.makedirs("docs/evidence/figures", exist_ok=True)

# Set common style
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Ubuntu', 'Helvetica', 'Arial']
DARK_BG = '#0d1117'
PANEL_BG = '#161b22'
TEXT_COLOR = '#c9d1d9'
MUTED_TEXT = '#8b949e'
BORDER_COLOR = '#30363d'
GRID_COLOR = '#21262d'

BLUE = '#58a6ff'
GREEN = '#3fb950'
ORANGE = '#f0883e'
RED = '#f85149'
PURPLE = '#bc8cff'
CYAN = '#39c5bb'

def setup_ax(ax, title, xlabel="", ylabel=""):
    ax.set_facecolor(PANEL_BG)
    ax.set_title(title, color=TEXT_COLOR, fontsize=12, fontweight='bold', pad=12)
    if xlabel:
        ax.set_xlabel(xlabel, color=TEXT_COLOR, fontsize=10, labelpad=8)
    if ylabel:
        ax.set_ylabel(ylabel, color=TEXT_COLOR, fontsize=10, labelpad=8)
    ax.tick_params(colors=MUTED_TEXT, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(BORDER_COLOR)
    ax.grid(True, linestyle='--', alpha=0.5, color=GRID_COLOR)

# -------------------------------------------------------------
# Figure 1: Opportunity Funnel Comparison (Control vs Target Hierarchy)
# -------------------------------------------------------------
def plot_funnel():
    stages = [
        "Evaluated\nCandles",
        "Pre-filter\nCandidates",
        "LTF-Confirmed\nTriggers",
        "Target\nResolved",
        "Qualified\n(≥ 4.0R)",
        "Executed\nTrades"
    ]
    baseline_counts = [277908, 1462, 391, 387, 11, 11]
    exp_counts = [277908, 1462, 391, 387, 21, 20]

    fig, ax = plt.subplots(figsize=(10, 5.5), facecolor=DARK_BG)
    setup_ax(ax, "Opportunity Funnel Comparison: Baseline Control vs. Target Hierarchy Experiment",
             ylabel="Setup Count (Log Scale)")

    x = np.arange(len(stages))
    width = 0.35

    rects1 = ax.bar(x - width/2, baseline_counts, width, label='Control (Closest Objective)', color='#30363d', edgecolor='#8b949e')
    rects2 = ax.bar(x + width/2, exp_counts, width, label='Experiment (Structural Objective)', color='#1f6feb', edgecolor=BLUE)

    ax.set_yscale('log')
    ax.set_xticks(x)
    ax.set_xticklabels(stages, color=TEXT_COLOR, fontsize=9.5)
    ax.legend(facecolor=PANEL_BG, edgecolor=BORDER_COLOR, labelcolor=TEXT_COLOR, loc='upper right')

    # Annotate key bars
    for i, (b, e) in enumerate(zip(baseline_counts, exp_counts)):
        if i >= 2:
            ax.annotate(f"{b}", (x[i] - width/2, b), textcoords="offset points", xytext=(0, 5),
                        ha='center', color=MUTED_TEXT, fontsize=8.5, fontweight='bold')
            ax.annotate(f"{e}", (x[i] + width/2, e), textcoords="offset points", xytext=(0, 5),
                        ha='center', color=BLUE if b != e else MUTED_TEXT, fontsize=8.5, fontweight='bold')

    ax.annotate("+90.9% Qualified (11 → 21)\n+81.8% Executed (11 → 20)",
                xy=(4.2, 21), xytext=(3.5, 90),
                arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.5),
                color=GREEN, fontsize=9.5, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.4", facecolor=PANEL_BG, edgecolor=GREEN, alpha=0.9))

    fig.text(0.5, 0.02, "Data: 2021–2022 Development Partition (15 Streams: BTC/ETH/SOL SET 1–5). Zero Validation/OOS Access.",
             ha='center', color=MUTED_TEXT, fontsize=8)

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    out_path = "docs/evidence/figures/opportunity_funnel_comparison.png"
    plt.savefig(out_path, dpi=200, facecolor=DARK_BG)
    plt.close()
    print(f"Saved: {out_path}")

# -------------------------------------------------------------
# Figure 2: Planned RR Distribution Comparison
# -------------------------------------------------------------
def plot_rr_distribution():
    with open("scratch/exp_target_structural_01_dev_results.json") as f:
        exp_data = json.load(f)
    with open("scratch/composite_01_dev_results_repaired_terminal.json") as f:
        base_data = json.load(f)

    def extract_rrs(data):
        rrs = []
        for s in data.get("stream_results", []):
            for c in s.get("all_candidates", []):
                if "RISK_GATE" in c.get("stages_reached", []):
                    entry = c.get("ltf_entry_price", 0.0)
                    sl = c.get("ltf_structural_sl", 0.0)
                    tgt = c.get("htf_target_price")
                    risk = abs(entry - sl)
                    if tgt is not None and tgt > 0.0 and risk > 0:
                        rr = abs(tgt - entry) / risk
                        rrs.append(min(rr, 10.0))
        return np.array(rrs)

    base_rrs = extract_rrs(base_data)
    exp_rrs = extract_rrs(exp_data)

    fig, ax = plt.subplots(figsize=(10, 5.5), facecolor=DARK_BG)
    setup_ax(ax, "Planned Risk/Reward Distribution: Baseline vs. Structural Target Hierarchy",
             xlabel="Planned Risk/Reward Ratio (R) [Capped at 10R for Visualization]",
             ylabel="Setup Frequency")

    bins = np.linspace(0, 10, 41)
    ax.hist(base_rrs, bins=bins, alpha=0.55, color='#8b949e', label=f'Baseline Control (Median: 0.47R, P75: 0.97R, N={len(base_rrs)})', edgecolor='#30363d')
    ax.hist(exp_rrs, bins=bins, alpha=0.7, color=BLUE, label=f'Structural Target Experiment (Median: 0.66R, P75: 1.33R, N={len(exp_rrs)})', edgecolor='#1f6feb')

    # 4R firewall marker
    ax.axvline(x=4.0, color=RED, linestyle='--', linewidth=2, label='4.0R Risk Firewall Threshold')
    ax.annotate("4.0R Firewall Threshold\n(Setups below this line rejected)",
                xy=(4.0, 75), xytext=(5.2, 75),
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.5),
                color=RED, fontsize=9, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.3", facecolor=PANEL_BG, edgecolor=RED))

    ax.legend(facecolor=PANEL_BG, edgecolor=BORDER_COLOR, labelcolor=TEXT_COLOR, loc='upper right')
    fig.text(0.5, 0.02, f"Data: 2021–2022 Development Partition ({len(exp_rrs)} Target-Resolved Setups). Descriptive Distribution.",
             ha='center', color=MUTED_TEXT, fontsize=8)

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    out_path = "docs/evidence/figures/planned_rr_distribution.png"
    plt.savefig(out_path, dpi=200, facecolor=DARK_BG)
    plt.close()
    print(f"Saved: {out_path} (N_base={len(base_rrs)}, N_exp={len(exp_rrs)})")

# -------------------------------------------------------------
# Figure 3: 354 Sub-4R Geometric Failure Mode Decomposition
# -------------------------------------------------------------
def plot_decomposition():
    cats = [
        "Cat 6: Extreme Target Proximity (< 2.5% reward)",
        "Cat 4: Destination Ambiguity / Range Fallback",
        "Cat 7: Dealing Range Compression (< 12% span)",
        "Cat 1: Late Leg Entry (> 60% span consumed)",
        "Cat 2: Macro Invalidation Stop (≥ 15% SL)",
        "Cat 5: Confirmation Latency Drift (≥ 35%)",
        "Cat 3: Intermediate Swings (1.5R ≤ RR < 4.0R)"
    ]
    counts = [106, 88, 51, 29, 25, 20, 35]
    pcts = [29.94, 24.86, 14.41, 8.19, 7.06, 5.65, 9.89]

    # Colors: Cat 6,4,7,1,2,5 are low-RR (shades of orange/amber/red), Cat 3 is intermediate (cyan/blue)
    colors = ['#d29922', '#e3b341', '#db6d28', '#f85149', '#da3633', '#f0883e', '#58a6ff']

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6), facecolor=DARK_BG, gridspec_kw={'width_ratios': [1.3, 1]})

    # Bar chart on left
    setup_ax(ax1, "Breakdown of 354 Still-Rejected Setups by Geometric Cause",
             xlabel="Setup Count", ylabel="")
    y_pos = np.arange(len(cats))
    bars = ax1.barh(y_pos, counts, color=colors, edgecolor=BORDER_COLOR, height=0.65)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(cats, color=TEXT_COLOR, fontsize=8.5)
    ax1.invert_yaxis()

    for bar, count, pct in zip(bars, counts, pcts):
        ax1.text(bar.get_width() + 2, bar.get_y() + bar.get_height()/2,
                 f"{count} ({pct:.1f}%)", va='center', color=TEXT_COLOR, fontsize=8.5, fontweight='bold')
    ax1.set_xlim(0, 130)

    # Donut / Pie chart on right showing 90.11% vs 9.89%
    group_counts = [319, 35]
    group_labels = [
        "Combined Low-RR Population\n(Cats 6, 4, 7, 1, 2, 5)\n319 Setups (90.11%)",
        "Intermediate Swings\n(Cat 3: 1.5R–3.9R)\n35 Setups (9.89%)"
    ]
    group_colors = [ORANGE, BLUE]

    wedges, texts, autotexts = ax2.pie(group_counts, labels=group_labels, autopct='%1.1f%%',
                                       colors=group_colors, startangle=60,
                                       wedgeprops=dict(width=0.45, edgecolor=BORDER_COLOR, linewidth=1.5),
                                       textprops=dict(color=TEXT_COLOR, fontsize=9.5))
    for at in autotexts:
        at.set_color('#ffffff')
        at.set_fontweight('bold')
    ax2.set_title("Population Distribution", color=TEXT_COLOR, fontsize=12, fontweight='bold', pad=12)

    fig.text(0.5, 0.02, "Data: 2021–2022 Development Partition (354 Sub-4R Setups). Observational Decomposition.",
             ha='center', color=MUTED_TEXT, fontsize=8)

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    out_path = "docs/evidence/figures/rejected_setups_decomposition.png"
    plt.savefig(out_path, dpi=200, facecolor=DARK_BG)
    plt.close()
    print(f"Saved: {out_path}")

# -------------------------------------------------------------
# Figure 4: Cumulative Realized Equity Curve in R
# -------------------------------------------------------------
def plot_equity_curve():
    with open("scratch/composite_01_dev_results_repaired_terminal.json") as f:
        base_data = json.load(f)
    with open("scratch/exp_target_structural_01_dev_results.json") as f:
        exp_data = json.load(f)

    def extract_trades(data):
        trades = []
        for s in data.get("stream_results", []):
            for t in s.get("trades", []):
                trades.append({
                    "exit_time": t.get("exit_timestamp", 0),
                    "net_r": t.get("net_r", 0.0),
                    "symbol": t.get("symbol"),
                    "stream_id": s.get("stream_id")
                })
        trades.sort(key=lambda x: x["exit_time"])
        return trades

    base_trades = extract_trades(base_data)
    exp_trades = extract_trades(exp_data)

    base_cum = np.cumsum([0.0] + [t["net_r"] for t in base_trades])
    exp_cum = np.cumsum([0.0] + [t["net_r"] for t in exp_trades])

    fig, ax = plt.subplots(figsize=(10, 5.5), facecolor=DARK_BG)
    setup_ax(ax, "Cumulative Realized Return Trajectory (R): Baseline vs. Target Hierarchy Experiment",
             xlabel="Sequential Executed Trade Number",
             ylabel="Cumulative Realized Return (R)")

    ax.step(range(len(base_cum)), base_cum, where='post', color='#8b949e', linewidth=2,
            label=f'Baseline Control (11 Trades, Net: +1.4145R, Max DD: 2.13R)')
    ax.step(range(len(exp_cum)), exp_cum, where='post', color=GREEN, linewidth=2.5,
            label=f'Structural Target Experiment (20 Trades, Net: +3.8327R, Max DD: 3.35R)')

    ax.scatter(range(len(base_cum)), base_cum, color='#8b949e', s=25, zorder=4)
    ax.scatter(range(len(exp_cum)), exp_cum, color=GREEN, s=35, zorder=5)

    ax.axhline(0, color=BORDER_COLOR, linestyle=':', linewidth=1.5)
    ax.legend(facecolor=PANEL_BG, edgecolor=BORDER_COLOR, labelcolor=TEXT_COLOR, loc='upper left')

    # Annotate endpoints
    ax.annotate(f"+1.4145R\n(N=11)", xy=(len(base_cum)-1, base_cum[-1]), xytext=(len(base_cum)-0.5, base_cum[-1]-0.8),
                arrowprops=dict(arrowstyle="->", color='#8b949e', lw=1.2),
                color='#8b949e', fontsize=9, fontweight='bold')

    ax.annotate(f"+3.8327R\n(N=20)", xy=(len(exp_cum)-1, exp_cum[-1]), xytext=(len(exp_cum)-1.5, exp_cum[-1]+0.6),
                arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.5),
                color=GREEN, fontsize=9.5, fontweight='bold')

    fig.text(0.5, 0.02, "Data: 2021–2022 Development Partition. Microstructure Slippage & Fees Included. Small Sample (N=20) — Not Statistically Asymptotic.",
             ha='center', color=MUTED_TEXT, fontsize=8)

    plt.subplots_adjust(bottom=0.12, top=0.92, left=0.08, right=0.95)
    out_path = "docs/evidence/figures/cumulative_realized_r_curve.png"
    plt.savefig(out_path, dpi=200, facecolor=DARK_BG)
    plt.close()
    print(f"Saved: {out_path}")

if __name__ == "__main__":
    plot_funnel()
    plot_rr_distribution()
    plot_decomposition()
    plot_equity_curve()
    print("All research figures generated successfully.")
