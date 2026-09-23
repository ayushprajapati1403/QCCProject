"""
make_scale_pdf.py - results_scale_tasks.pdf: the 500-5000 task scaling study (exp_scale_tasks.py) as exact values.

Every number is computed from results/scale_tasks/records.csv (write-once). Also writes the figure
results/fig_scale_tasks_gap.png (write-once unless --force). Makespan in seconds (task lengths in MI, VM speeds in MIPS).
Needs reportlab (pip install reportlab).  python scripts/reports/make_scale_pdf.py
"""
import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repository root
sys.path[:0] = [os.path.join(_ROOT, "src"), os.path.join(_ROOT, "experiments")]   # the qi_* modules and experiment settings
import os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, FixedLocator, NullLocator
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether, PageBreak, Image
from make_results_summary import S, table, RES, ROOT
from exp_scale_tasks import SIZES, ALGOS, LABELS, M

OUT = os.path.join(ROOT, "docs", "summaries", "results_scale_tasks.pdf")
FIG = os.path.join(RES, "fig_scale_tasks_gap.png")
SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
# the validated categorical palette of make_v5_figures.py, assigned in its fixed order
PLOT = [("QI-MRFO+CXM", "#2a78d6"), ("QI-MRFO", "#eb6834"), ("QI-DMO", "#1baf7a"), ("GA", "#eda100"),
        ("Max-Min", "#e87ba4"), ("MRFO", "#008300"), ("DMO", "#4a3aa7")]


def load():
    df = pd.read_csv(os.path.join(RES, "scale_tasks", "records.csv"))
    g = df.groupby(["n", "algo"])
    t = g.agg(runs=("makespan", "size"), mean=("makespan", "mean"), sd=("makespan", "std"), best=("makespan", "min"),
              gap=("gap", "mean"), rt=("runtime_s", "mean")).reset_index()
    t["sd"] = t["sd"].fillna(0.0); t["gap"] *= 100
    return df, t.set_index(["algo", "n"]), df.groupby("n").lb.first()


def figure(t):
    if os.path.exists(FIG) and "--force" not in sys.argv:
        return
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
                         "xtick.color": MUTED, "ytick.color": MUTED, "figure.facecolor": SURF, "axes.facecolor": SURF,
                         "savefig.facecolor": SURF, "text.color": INK})
    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    x = np.array(SIZES)
    for algo, col in PLOT:
        y = np.array([t.loc[(algo, n), "gap"] for n in SIZES])
        ax.plot(x, y, color=col, linewidth=2, solid_capstyle="round", solid_joinstyle="round", label=LABELS[algo], zorder=2)
        ax.plot(x, y, "o", color=col, markersize=6, markeredgecolor=SURF, markeredgewidth=2, zorder=3)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.xaxis.set_major_locator(FixedLocator(SIZES)); ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v):,}"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_title(f"Gap to the lower bound as the number of tasks grows ({M} VMs, 20 000 evaluations, mean of 10 runs)",
                 loc="left", fontsize=10, color=INK)
    ax.set_xlabel("number of tasks (log scale)", color=INK2); ax.set_ylabel("gap to the lower bound (%, log scale)", color=INK2)
    ax.grid(True, which="major", color=GRID, linewidth=0.8, linestyle="-"); ax.set_axisbelow(True)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    ax.legend(frameon=False, fontsize=8, loc="center left", bbox_to_anchor=(1.01, 0.5), labelcolor=INK2)
    fig.savefig(FIG, dpi=170, bbox_inches="tight"); plt.close(fig)


def separated(df, a, b, n):
    """True when every run of A has a lower makespan than every run of B (B may be a deterministic heuristic)."""
    xa = df[(df.n == n) & (df.algo == a)].makespan; xb = df[(df.n == n) & (df.algo == b)].makespan
    return bool(xa.max() < xb.min())


def key_results(df, t, lb):
    lo, hi = SIZES[0], SIZES[-1]
    m = lambda a, n: t.loc[(a, n), "mean"]
    every = lambda a, b: all(separated(df, a, b, n) for n in SIZES)
    q = lambda a, b: "in every run at every size" if every(a, b) else "on average at every size" if all(m(a, n) < m(b, n) for n in SIZES) else "not at every size"
    seed_gap = [t.loc[("QI-MRFO+CXM+seed", n), "gap"] for n in SIZES]
    items = [
        f"<b>Quantum-inspired vs original</b> ({q('QI-MRFO', 'MRFO')} for MRFO, {q('QI-DMO', 'DMO')} for DMO): at {lo:,} tasks "
        f"MRFO {m('MRFO', lo):.2f} s → QI-MRFO {m('QI-MRFO', lo):.2f} s and DMO {m('DMO', lo):.2f} s → QI-DMO "
        f"{m('QI-DMO', lo):.2f} s; at {hi:,} tasks MRFO {m('MRFO', hi):.2f} s → {m('QI-MRFO', hi):.2f} s and DMO "
        f"{m('DMO', hi):.2f} s → {m('QI-DMO', hi):.2f} s.",
        f"<b>With the swap move, QI-MRFO beats the Genetic Algorithm</b> {q('QI-MRFO+CXM', 'GA')}: {m('QI-MRFO+CXM', lo):.2f} s vs "
        f"{m('GA', lo):.2f} s at {lo:,} tasks and {m('QI-MRFO+CXM', hi):.2f} s vs {m('GA', hi):.2f} s at {hi:,} tasks "
        f"(and GA with the same swap move {q('QI-MRFO+CXM', 'GA+CXM')}).",
        f"<b>Seeded with Max-Min, QI-MRFO + swap</b> is within {min(seed_gap):.2f}–{max(seed_gap):.2f} % of the theoretical "
        f"minimum at every size and beats the Max-Min heuristic {q('QI-MRFO+CXM+seed', 'Max-Min')}.",
    ]
    return items


def honest_notes(df, t):
    m = lambda a, n: t.loc[(a, n), "mean"]; hi = SIZES[-1]
    ga_ahead = [n for n in SIZES if m("GA", n) < m("QI-MRFO", n)]
    ea_ahead = [n for n in SIZES if m("(1+1)-EA+CXM", n) < m("QI-MRFO+CXM", n)]
    rt = lambda a: t.loc[(a, hi), "rt"]
    notes = [
        (f"Without the swap move, QI-MRFO is behind the GA on average at {len(ga_ahead)} of {len(SIZES)} sizes; the swap move is what "
         "makes it competitive at this scale."),
        (f"A simple (1+1)-EA using the same swap move is better than the unseeded QI-MRFO + swap at {len(ea_ahead)} of {len(SIZES)} "
         f"sizes{', in every run' if all(separated(df, '(1+1)-EA+CXM', 'QI-MRFO+CXM', n) for n in SIZES) else ', on average'} "
         f"({m('(1+1)-EA+CXM', hi):.2f} s vs {m('QI-MRFO+CXM', hi):.2f} s at {hi:,} tasks); seeded, the two are within "
         f"{abs(m('QI-MRFO+CXM+seed', hi) - m('(1+1)-EA+CXM+seed', hi)):.2f} s of each other, and the (1+1)-EA takes "
         f"{rt('(1+1)-EA+CXM+seed'):.1f} s per run against {rt('QI-MRFO+CXM+seed'):.1f} s. For one-time batches the gain "
         "comes from the swap move and the seed, not from the swarm (as in the earlier held-out test H7)."),
        (f"All methods used the same fixed budget of 20 000 evaluations. At {hi:,} tasks this is small: the unseeded population "
         f"methods end far from the bound (QI-MRFO + swap {t.loc[('QI-MRFO+CXM', hi), 'gap']:.1f} % above it), so at thousands "
         "of tasks they need a larger budget or a heuristic seed."),
        "One problem per size and a synthetic workload; 10 runs per algorithm. Real traces are the next step.",
    ]
    return notes


def cell(t, a, n):
    r = t.loc[(a, n)]
    if r["runs"] == 1:
        return f"{r['mean']:.2f}<br/><font color='#5f6368' size='7.4'>deterministic</font>"
    return f"{r['mean']:.2f} ± {r['sd']:.2f}<br/><font color='#5f6368' size='7.4'>best {r['best']:.2f}</font>"


def build():
    df, t, lb = load()
    figure(t)
    W = landscape(A4)[0] - 30 * mm
    order = list(ALGOS)
    ours = tuple(i + 1 for i, a in enumerate(order) if a in ("QI-MRFO+CXM", "QI-MRFO+CXM+seed"))
    head = ["Algorithm<br/>(makespan in s)"] + [f"{n:,} tasks<br/>{M} VMs" for n in SIZES]
    t1 = [head] + [[LABELS[a]] + [cell(t, a, n) for n in SIZES] for a in order] + [["Lower bound (s)"] + [f"{lb[n]:.2f}" for n in SIZES]]
    t2 = [["Algorithm<br/>(gap in %)"] + [f"{n:,} tasks" for n in SIZES]] + \
         [[LABELS[a]] + [f"{t.loc[(a, n), 'gap']:.2f}" for n in SIZES] for a in order]
    t3 = [["Algorithm<br/>(runtime in s)"] + [f"{n:,} tasks" for n in SIZES]] + \
         [[LABELS[a]] + [f"{t.loc[(a, n), 'rt']:.1f}" for n in SIZES] for a in order]
    best_at = {n: min(order, key=lambda a: t.loc[(a, n), "mean"]) for n in SIZES}
    story = [Paragraph("Scaling to 500–5000 Tasks: Results as Exact Values", S["title"]),
             Paragraph("Quantum-inspired MRFO / DMO for cloud task scheduling · makespan in seconds · requested scaling study", S["sub"]),
             Paragraph(f"<b>Setup.</b> One problem per size with {', '.join(f'{n:,}' for n in SIZES)} tasks on the same kind of VM "
                       f"pool: {M} heterogeneous VMs (speeds 250–2000 MIPS), task lengths uniform 1000–10000 MI. Each algorithm ran "
                       "10 independent times (the deterministic heuristics once) with 20 000 evaluations per run and population 30, "
                       "using the settings of the earlier studies without re-tuning (research_plan_v5.md §29).", S["body"]),
             Spacer(1, 4),
             Paragraph("<b>Units.</b> Makespan, lower bound and standard deviation: <b>seconds (s)</b> (task length in MI ÷ VM speed "
                       "in MIPS). Gap: <b>%</b> above the lower bound, the theoretical minimum makespan. Runtime: <b>seconds (s)</b> "
                       "of computer time per run.", S["body"]),
             Paragraph("<b>Key results.</b><br/>" + "<br/>".join("• " + k for k in key_results(df, t, lb)), S["key"])]
    story.append(KeepTogether([
        Paragraph("Figure 1 · Gap to the lower bound vs number of tasks", S["h"]),
        Image(FIG, width=168 * mm, height=168 * mm * 0.5),
        Paragraph("Mean of 10 runs per point (heuristic: one deterministic run). The Max-Min-seeded variants are not drawn: they "
                  f"stay within {max(t.loc[('QI-MRFO+CXM+seed', n), 'gap'] for n in SIZES):.2f}\u00a0% of the bound at every size (Table 2). Source: "
                  "results/scale_tasks/records.csv.", S["note"])]))
    story.append(PageBreak())
    story.append(KeepTogether([
        Paragraph("Table 1 · Makespan in seconds (s): mean ± standard deviation over 10 runs, best run below", S["h"]),
        table(t1, [62 * mm] + [(W - 62 * mm) / len(SIZES)] * len(SIZES), ours=ours),
        Paragraph("Lowest mean makespan per size: " + "; ".join(f"{n:,} tasks: {LABELS[best_at[n]]}" for n in SIZES) +
                  ". Source: results/scale_tasks/records.csv (analysis: results/scale_tasks_analysis.md).", S["note"])]))
    story.append(PageBreak())
    story.append(KeepTogether([
        Paragraph("Table 2 · Gap to the lower bound (%), mean over 10 runs", S["h"]),
        table(t2, [62 * mm] + [(W - 62 * mm) / len(SIZES)] * len(SIZES), ours=ours)]))
    story.append(KeepTogether([
        Paragraph("Table 3 · Runtime per run in seconds (s), mean over 10 runs", S["h"]),
        table(t3, [62 * mm] + [(W - 62 * mm) / len(SIZES)] * len(SIZES), ours=ours),
        Paragraph("Measured on one shared machine with 4 runs in parallel, so the values compare the algorithms with each other "
                  "rather than giving absolute speeds. The quantum-inspired methods keep a probability for every (task, VM) "
                  "pair, so their time per evaluation grows with tasks × VMs.", S["note"])]))
    story.append(KeepTogether([Paragraph("Honest notes", S["h"])] +
                              [Paragraph(x, S["bullet"], bulletText="•") for x in honest_notes(df, t)]))
    doc = SimpleDocTemplate(OUT, pagesize=landscape(A4), leftMargin=15 * mm, rightMargin=15 * mm, topMargin=13 * mm,
                            bottomMargin=12 * mm, title="Scaling to 500–5000 Tasks", author="QCCProject")
    doc.build(story)
    print("wrote", OUT)


if __name__ == "__main__":
    build()
