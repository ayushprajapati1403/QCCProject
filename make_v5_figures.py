"""
make_v5_figures.py - figures for the V5 results, drawn only from committed result files (results/h5_test, h6_dynamic,
h7_test, h8_migration and, if present, h10_elite_migration, h11_event_elite, h12_incremental_elite and h13_event_gamma). Writes new files results/fig_v5_*.png (write-once).

Design: light surface; categorical hues from the reference palette in fixed order, colour follows the entity across
panels (validated with the dataviz validator: adjacent CVD dE >= 9.1, normal-vision >= 22.9); 2 px lines, ringed
end-markers, solid hairline grid, text in ink tokens (never the series colour), legend + direct labels; one y-axis per
panel; the markdown analysis files are the table view.
"""
import os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, SymLogNorm
from matplotlib.ticker import FuncFormatter

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
COLOR = {"QI-MRFO+CXM": "#2a78d6", "QI-MRFO": "#eb6834", "GA+CXM": "#1baf7a", "GA": "#eda100",
         "(1+1)-EA+CXM": "#e87ba4", "QI-MRFO+CXM+seed": "#008300", "(1+1)-EA+CXM+seed": "#4a3aa7"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "figure.facecolor": SURF, "axes.facecolor": SURF,
                     "savefig.facecolor": SURF, "text.color": INK})


def plain_log_ticks(ax):
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))


def style(ax, title, xlabel, ylabel):
    ax.set_title(title, loc="left", fontsize=10, color=INK)
    ax.set_xlabel(xlabel, color=INK2); ax.set_ylabel(ylabel, color=INK2)
    ax.grid(True, color=GRID, linewidth=0.8, linestyle="-"); ax.set_axisbelow(True)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)


def save(fig, name):
    path = os.path.join(os.environ.get("QI_FIG_DIR", RES), name)
    if os.path.exists(path) and "--force" not in sys.argv:
        print("exists, skipped:", path); plt.close(fig); return
    fig.savefig(path, dpi=150, bbox_inches="tight"); plt.close(fig); print("wrote", path)


def convergence_panel(ax, df, algos, title):
    cps = [c for c in df.columns if c.startswith("bsf_")]
    x = np.array([int(c[4:]) for c in cps])
    ends = []
    for a in algos:
        sub = df[df.algo == a]
        y = ((sub[cps].values - sub.lb2.values[:, None]) / sub.lb2.values[:, None] * 100).mean(0)
        ax.plot(x, y, color=COLOR[a], linewidth=2, solid_capstyle="round", label=a)
        ax.plot(x[-1], y[-1], "o", color=COLOR[a], markersize=6, markeredgecolor=SURF, markeredgewidth=2, zorder=3)
        ends.append((y[-1], a))
    ax.set_yscale("log")
    # direct end labels in ink; spread in log space only if two labels would overlap, with a leader line
    ends.sort(); placed = []
    for yv, a in ends:
        ly = yv
        while placed and np.log10(ly) - np.log10(placed[-1]) < 0.09: ly *= 10 ** 0.09
        placed.append(ly)
        ax.annotate(f"{a}  {yv:.2f} %", xy=(100, yv), xytext=(104, ly), fontsize=8, color=INK2, va="center",
                    arrowprops=dict(arrowstyle="-", color=AXIS, linewidth=0.8) if abs(np.log10(ly / yv)) > 0.02 else None)
    ax.set_xlim(0, 100); ax.set_xticks([5, 25, 50, 75, 100]); plain_log_ticks(ax)
    style(ax, title, "evaluation budget used (%)", "mean gap to the preemptive lower bound (%, log)")


def fig_convergence():
    h5, h7 = pd.read_csv(os.path.join(RES, "h5_test", "records.csv")), pd.read_csv(os.path.join(RES, "h7_test", "records.csv"))
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.6))
    convergence_panel(axes[0], h5, ["QI-MRFO", "GA", "GA+CXM", "QI-MRFO+CXM"], "H5 (held-out, seeds 101–110): CXM on the swarm and on the GA")
    convergence_panel(axes[1], h7, ["QI-MRFO+CXM", "(1+1)-EA+CXM", "QI-MRFO+CXM+seed", "(1+1)-EA+CXM+seed"],
                      "H7 (fresh, seeds 201–210): swarm vs (1+1)-EA with the same moves; Max-Min seed")
    for ax in axes: ax.legend(frameon=False, fontsize=8, loc="upper right", labelcolor=INK2)
    fig.subplots_adjust(wspace=0.55, right=0.86)
    save(fig, "fig_v5_convergence.png")


def fig_dynamic_tradeoff():
    df = pd.read_csv(os.path.join(RES, "h6_dynamic", "records.csv"))
    t = df.groupby("algo").agg(gap=("post_gap", "mean"), mig=("migrations", "mean"))
    t["gap"] *= 100
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    emph = {"QI-MRFO+CXM continue", "QI-MRFO+CXM continue+elite", "P-MRFO+CXM continue+elite"}
    # label offsets (points) chosen after rendering to avoid collisions; long offsets get a hairline leader
    offs = {"GA continue": (14, 14, "left"), "QI-MRFO continue": (16, 0, "left"), "QI-MRFO continue+elite": (-12, -14, "right"),
            "Max-Min (recompute)": (-10, -14, "right"), "QI-MRFO+CXM restart": (-6, 14, "right"),
            "QI-MRFO+CXM continue+elite": (-10, 2, "right"), "QI-MRFO+CXM continue": (10, 2, "left"),
            "P-MRFO+CXM continue+elite": (10, -8, "left")}
    for name, r in t.iterrows():
        c = COLOR["QI-MRFO+CXM"] if name in emph else MUTED
        ax.plot(r.mig, r.gap, "o", color=c, markersize=8, markeredgecolor=SURF, markeredgewidth=2, zorder=3)
        dx, dy, ha = offs.get(name, (6, 4, "left"))
        lead = dict(arrowstyle="-", color=AXIS, linewidth=0.8, shrinkA=0, shrinkB=4) if abs(dx) + abs(dy) > 14 else None
        ax.annotate(name, xy=(r.mig, r.gap), xytext=(dx, dy), textcoords="offset points", fontsize=7.5, color=INK2,
                    ha=ha, va="center", arrowprops=lead)
    ax.set_yscale("log"); plain_log_ticks(ax); ax.set_xlim(-5, 100)
    style(ax, "H6: post-change makespan gap vs voluntary migrations (60 scenario-seed pairs; accent = swarm with CXM)",
          "voluntary task migrations per epoch", "post-change gap (%, log)")
    save(fig, "fig_v5_dynamic_tradeoff.png")


def fig_migration_heatmaps():
    """Pairwise contrasts of post-change COST gap by scenario type x lambda (blue = A cheaper, red = B cheaper)."""
    heatmap_figure([("h8_migration", "QI-MRFO+CXM continue", "Chooser (cheaper of the two)", "H8: swarm − Chooser"),
                    ("h10_elite_migration", "QI-MRFO+CXM continue+elite", "QI-MRFO+CXM continue", "H10: elite − no elite"),
                    ("h11_event_elite", "QI-MRFO+CXM continue+event-aware elite", "QI-MRFO+CXM continue", "H11: event-aware elite − no elite")],
                   "fig_v5_migration_heatmap.png")


def fig_h12_heatmaps():
    """H12 contrasts: the incremental-elite swarm against the H11 swarm, the Chooser and the (1+1)-EA control."""
    inc = "QI-MRFO+CXM continue+event-aware incremental elite"
    heatmap_figure([("h12_incremental_elite", inc, "QI-MRFO+CXM continue+event-aware elite", "H12a: incremental − H11 elite"),
                    ("h12_incremental_elite", inc, "Chooser (cheaper of the two)", "H12b: incremental elite − Chooser"),
                    ("h12_incremental_elite", inc, "(1+1)-EA+CXM continue, incremental repair", "H12c: swarm − (1+1)-EA, same repair")],
                   "fig_v5_h12_heatmap.png", seeds_note="all panels: the H12 run, fresh seeds 501–510")


def fig_h13_heatmaps():
    """H13 contrasts: event-aware decoherence against c = 1, against c = 0 after every change, and against the Chooser."""
    ev = "H12 swarm, event-aware gamma"
    heatmap_figure([("h13_event_gamma", ev, "H12 swarm (c = 1)", "H13a: event-aware γ − c = 1"),
                    ("h13_event_gamma", ev, "H12 swarm, c = 0 after every change", "H13b: event-aware γ − c = 0 everywhere"),
                    ("h13_event_gamma", ev, "Chooser (cheaper of the two)", "H13c: final configuration − Chooser")],
                   "fig_v5_h13_heatmap.png", seeds_note="all panels: the H13 run, fresh seeds 601–610")


def heatmap_figure(panels, name, seeds_note="each panel uses its own fresh seed set"):
    panels = [p for p in panels if os.path.exists(os.path.join(RES, p[0], "records.csv"))]
    if not panels: return
    cmap = LinearSegmentedColormap.from_list("div", ["#2a78d6", "#f0efec", "#e34948"])
    norm = SymLogNorm(linthresh=1.0, vmin=-45, vmax=45, base=10)
    fig, axes = plt.subplots(1, len(panels), figsize=(4.3 * len(panels) + 1.6, 4.2), squeeze=False)
    for k, (ax, (exp, a, b, title)) in enumerate(zip(axes[0], panels)):
        df = pd.read_csv(os.path.join(RES, exp, "records.csv"))
        df["base"] = df.scenario.str.replace(r" lam=.*$", "", regex=True)
        w = df[df.algo.isin([a, b])].pivot_table(index=["base", "mig_lambda", "seed"], columns="algo", values="post_cost_gap")
        d = ((w[a] - w[b]) * 100).groupby(level=[0, 1]).mean().unstack("mig_lambda")
        ax.imshow(d.values, cmap=cmap, norm=norm, aspect="auto")
        for i in range(d.shape[0]):
            for j in range(d.shape[1]):
                v = d.values[i, j]
                ax.text(j, i, f"{v:+.1f}", ha="center", va="center", fontsize=8.5, color="#ffffff" if abs(v) > 8 else INK)
        ax.set_xticks(range(d.shape[1])); ax.set_xticklabels([f"λ = {c:g}" for c in d.columns])
        ax.set_yticks(range(d.shape[0])); ax.set_yticklabels(d.index if k == 0 else [])
        ax.set_title(title, loc="left", fontsize=10, color=INK)
        for sp in ax.spines.values(): sp.set_visible(False)
        ax.tick_params(length=0)
        for i in range(d.shape[0] + 1): ax.axhline(i - 0.5, color=SURF, linewidth=2)      # 2 px surface gap between cells
        for j in range(d.shape[1] + 1): ax.axvline(j - 0.5, color=SURF, linewidth=2)
    fig.text(0.01, -0.03, "Cell = mean difference in post-change cost gap, A − B (percentage points; 10 seeds per cell; " + seeds_note +
                          "). Blue = A cheaper, red = B cheaper; symmetric-log colour scale.", fontsize=8, color=INK2)
    save(fig, name)


if __name__ == "__main__":
    fig_convergence(); fig_dynamic_tradeoff(); fig_migration_heatmaps(); fig_h12_heatmaps(); fig_h13_heatmaps()
