"""
make_exact_values.py - results_exact_values.pdf: the results as exact values instead of percentage gaps.

Makespan = time in seconds at which the last task finishes (task lengths in MI, VM speeds in MIPS); lower is better.
Lower bound = the theoretical minimum makespan of the problem. Every number is computed here from committed files:
  results/baseline_full.csv            V4: 7 problems x 30 runs (raw makespan per run is stored)
  results/h5_test/records.csv          V5: 80 unseen problems (raw makespan per run is stored)
  results/h6_dynamic/, results/h13_event_gamma/   V5 changing cloud: each epoch's gap and the migration counts are stored;
      the makespan is recomputed as lower bound x (1 + gap), with the lower bound regenerated from the same problem generator
      (checked against directly computed Max-Min makespans: identical to ~1e-16).

Needs reportlab (pip install reportlab).  python scripts/reports/make_exact_values.py
"""
import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repository root
sys.path[:0] = [os.path.join(_ROOT, "src"), os.path.join(_ROOT, "experiments")]   # the qi_* modules and experiment settings
import json
import os
import numpy as np
import pandas as pd
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether, PageBreak
from make_results_summary import S, table, RES, ROOT          # registers the fonts and shares the table style
from qi_dynamic import make_dynamic_sequence

OUT = os.path.join(ROOT, "docs", "summaries", "results_exact_values.pdf")


def s2(x):
    return f"{x:.2f}"


# ------------------------------------------------------------------------------------------ V4: 7 problems x 30 runs
V4_PROBLEMS = ["n30 m5 uniform high", "n50 m10 uniform none", "n50 m10 bimodal high", "n60 m8 bimodal none",
               "n100 m10 uniform high", "n100 m10 lognormal low", "n200 m20 uniform high"]
V4_ALGOS = [("DMO", "DMO (original)"), ("QI-DMO", "QI-DMO (quantum-inspired)"), ("MRFO", "MRFO (original)"),
            ("QI-MRFO", "QI-MRFO (quantum-inspired)"), ("GA", "Genetic Algorithm"), ("PSO", "PSO"),
            ("Max-Min", "Max-Min heuristic"), ("Min-Min", "Min-Min heuristic"), ("Random", "Random search")]


def head(name):
    n, m, dist, het = name.split()
    return f"{n[1:]} tasks<br/>{m[1:]} VMs<br/>{dist} · {het}"


def v4_table():
    df = pd.read_csv(os.path.join(RES, "baseline_full.csv"))
    g = df.groupby(["algo", "instance"]).makespan
    mean, sd, best = g.mean(), g.std(ddof=1), g.min()
    lb = df.groupby("instance").lb.first()
    rows = [["Algorithm<br/>(makespan in s)"] + [head(p) for p in V4_PROBLEMS]]
    for key, lab in V4_ALGOS:
        rows.append([lab] + [f"{s2(mean[key, p])} ± {s2(sd[key, p])}<br/><font color='#5f6368' size='7.4'>best {s2(best[key, p])}</font>"
                             for p in V4_PROBLEMS])
    rows.append(["Lower bound (s), theoretical minimum"] + [s2(lb[p]) for p in V4_PROBLEMS])
    runs = df.groupby(["algo", "instance"]).size()
    assert (runs == 30).all(), "expected 30 runs per algorithm and problem"
    return rows


# ------------------------------------------------------------------------------------------ V5: 80 unseen problems
V5_ALGOS = [("MRFO", "MRFO<br/>original<br/>(s)"), ("QI-MRFO", "QI-MRFO<br/>no swap<br/>(s)"), ("QI-MRFO+CXM", "QI-MRFO + swap<br/>ours<br/>(s)"),
            ("GA", "Genetic<br/>Algorithm<br/>(s)"), ("GA+CXM", "GA + swap<br/><br/>(s)"), ("Max-Min", "Max-Min<br/>heuristic<br/>(s)")]


def v5_table():
    df = pd.read_csv(os.path.join(RES, "h5_test", "records.csv"))
    per_inst = df.groupby(["family", "inst_seed", "algo"]).makespan.mean().unstack("algo")
    lb = df.groupby(["family", "inst_seed"]).lb2.first()
    fam = sorted(per_inst.index.get_level_values(0).unique(), key=lambda f: (int(f.split()[0][1:]), int(f.split()[1][1:])))
    rows = [["Problem type (10 problems each)", "Lower<br/>bound<br/>(s)"] + [lab for _, lab in V5_ALGOS]]
    for f in fam:
        n, m, dist, het = f.split()
        rows.append([f"{n[1:]} tasks, {m[1:]} VMs, {dist} · {het}", s2(lb.loc[f].mean())] +
                    [s2(per_inst.loc[f, a].mean()) for a, _ in V5_ALGOS])
    return rows


# ------------------------------------------------------------------------------------------ changing cloud
SCEN = {"n100 m10 churn20": "Task churn (20 % replaced)", "n100 m10 drift": "VM speed drift", "n100 m10 vm_fail": "VM failure",
        "n100 m10 vm_add": "VM added", "n100 m10 mixed": "Mixed events",
        "n200 m20 lognormal mixed": "Mixed, 200 tasks, 20 VMs, heavy-tailed"}


def dynamic_values(exp):
    """Per (algo, scenario, seed): mean post-change makespan (s), mean post-change lower bound (s), migrations/epoch."""
    jobs = json.load(open(os.path.join(RES, exp, "jobs.json")))
    jobs = jobs["jobs"] if isinstance(jobs, dict) else jobs          # run_experiment stores {"sha256": ..., "jobs": [...]}
    rec = pd.read_csv(os.path.join(RES, exp, "records.csv")).set_index(["algo", "scenario", "seed"])
    lbs_cache, rows = {}, []
    for j in jobs:
        s = j["scenario"]
        key = (s["n"], s["m"], j["seed"], s["K"], s["change"], s.get("rho", 0.2), s.get("task_dist", "uniform"), s.get("hetero", "high"))
        if key not in lbs_cache:
            seq = make_dynamic_sequence(s["n"], s["m"], seed=j["seed"], K=s["K"], change=s["change"], rho=s.get("rho", 0.2),
                                        task_dist=s.get("task_dist", "uniform"), hetero=s.get("hetero", "high"))
            lbs_cache[key] = [inst.lower_bound() for inst, _ in seq]
        lbs = lbs_cache[key]
        r = rec.loc[(j["algo"], s["name"], j["seed"])]
        gaps = [r[f"e{e}_gap"] for e in range(1, len(lbs))]
        assert np.isclose(np.mean(gaps), r["post_gap"]), "per-epoch gaps must reproduce the stored post-change gap"
        rows.append({"algo": j["algo"], "base": s.get("base", s["name"]), "lam": s.get("mig_lambda"), "seed": j["seed"],
                     "ms": float(np.mean([lb * (1 + g) for lb, g in zip(lbs[1:], gaps)])), "lb": float(np.mean(lbs[1:])),
                     "mig": float(r["migrations"])})
    return pd.DataFrame(rows)


def h6_table():
    d = dynamic_values("h6_dynamic")
    a, b = "QI-MRFO+CXM continue+elite", "GA+CXM continue"
    t = d[d.algo.isin([a, b])].pivot_table(index=["base", "seed"], columns="algo", values="ms")
    lb = d.groupby(["base", "seed"]).lb.first()
    rows = [["Change type (100 tasks, 10 VMs unless stated)", "Lower bound (s)", "QI-MRFO + swap, ours (s)", "GA + swap (s)",
             "QI-MRFO better in (runs)"]]
    for base, lab in SCEN.items():
        tb = t.loc[base]
        rows.append([lab, s2(lb.loc[base].mean()), s2(tb[a].mean()), s2(tb[b].mean()), f"{int((tb[a] < tb[b]).sum())} of {len(tb)}"])
    return rows


def h13_tables():
    d = dynamic_values("h13_event_gamma")
    fin, cho = "H12 swarm, event-aware gamma", "Chooser (cheaper of the two)"
    out = {}
    for lam in [0.05, 0.2, 1.0]:
        x = d[(d.lam == lam) & d.algo.isin([fin, cho])]
        ms = x.pivot_table(index=["base", "seed"], columns="algo", values="ms")
        mig = x.pivot_table(index=["base", "seed"], columns="algo", values="mig")
        lb = x.groupby(["base", "seed"]).lb.first()
        rows = [["Change type", "Lower bound (s)", "Makespan (s):<br/>best heuristic", "Makespan (s):<br/>QI-MRFO (ours)",
                 "Tasks moved:<br/>best heuristic", "Tasks moved:<br/>QI-MRFO (ours)"]]
        for base, lab in SCEN.items():
            rows.append([lab, s2(lb.loc[base].mean()), s2(ms.loc[base, cho].mean()), s2(ms.loc[base, fin].mean()),
                         f"{mig.loc[base, cho].mean():.1f}", f"{mig.loc[base, fin].mean():.1f}"])
        out[lam] = rows
    return out


# ------------------------------------------------------------------------------------------ document
def build():
    W = landscape(A4)[0] - 30 * mm
    story = [Paragraph("Quantum-Inspired MRFO and DMO — Results as Exact Values", S["title"]),
             Paragraph("Companion to results_summary.pdf · makespan in seconds instead of percentage gaps", S["sub"]),
             Paragraph("<b>What the numbers are.</b> <i>Makespan</i> is the time, in seconds, at which the last task finishes; "
                       "lower is better. Task lengths are in MI (million instructions) and VM speeds in MIPS. The <i>lower bound</i> "
                       "is the theoretical minimum makespan of a problem: no schedule can finish earlier. The percentage gaps in "
                       "the summary are (makespan − lower bound) / lower bound.", S["body"]),
             Spacer(1, 4),
             Paragraph("<b>Units.</b> Makespan, lower bound and standard deviation: <b>seconds (s)</b>. Task length: <b>MI</b> "
                       "(million instructions). VM speed: <b>MIPS</b> (million instructions per second), so a task's execution time "
                       "= length ÷ speed is in seconds. Migrations: <b>number of running tasks</b> moved to another VM per change. "
                       "λ (migration price) has no unit.", S["body"])]

    story.append(KeepTogether([
        Paragraph("Table 1 · DMO and MRFO, original vs quantum-inspired: makespan in seconds (s) (V4 study)", S["h"]),
        table(v4_table(), [52 * mm] + [(W - 52 * mm) / 7] * 7, ours=(2, 4)),
        Paragraph("Each cell: mean ± standard deviation over 30 independent runs of 20 000 evaluations, in seconds; below it, "
                  "the best of the 30 runs, in seconds. Column headings: tasks, VMs, task-length distribution · VM speed heterogeneity (high = 250–2000 MIPS, "
                  "low = 900–1100 MIPS, none = all 1000 MIPS). Max-Min and Min-Min are deterministic, so their standard deviation "
                  "is 0. Source: results/baseline_full.csv.", S["note"])]))
    story.append(PageBreak())

    story.append(KeepTogether([
        Paragraph("Table 2 · Adding the swap move: makespan in seconds (s) on 80 unseen problems (V5 held-out test)", S["h"]),
        table(v5_table(), [66 * mm, 25 * mm] + [(W - 91 * mm) / 6] * 6, ours=()),
        Paragraph("Each cell: mean makespan over the 10 problems of that type (each problem averaged over its 2 runs; the "
                  "heuristic is deterministic). The lower bound here is the tighter preemptive bound. Source: "
                  "results/h5_test/records.csv.", S["note"])]))
    story.append(Spacer(1, 6))
    story.append(KeepTogether([
        Paragraph("Table 3 · Changing cloud, against the GA: makespan in seconds (s) after each change (V5)", S["h"]),
        table(h6_table(), [82 * mm, 36 * mm, 46 * mm, 40 * mm, W - 204 * mm], ours=()),
        Paragraph("Each cell: mean over the 8 changes of a scenario and 10 independent runs. Both methods use the swap move and keep "
                  "their state between changes. Source: results/h6_dynamic (makespans recomputed from the stored gaps and the "
                  "regenerated lower bounds; exact to rounding).", S["note"])]))
    story.append(PageBreak())

    story.append(Paragraph("Table 4 · Changing cloud with a cost for moving running tasks: makespan (s) and migrations "
                           "(tasks per change) (V5)", S["h"]))
    story.append(Paragraph("Best heuristic = the cheaper of full Max-Min recompute and zero-migration repair. Each cell: mean over the "
                           "8 changes and 10 runs. <i>Tasks moved</i> = number of running tasks migrated to another VM at each change "
                           "(a count, unit: tasks per change). The price "
                           "λ says how much one migration costs relative to makespan: the methods optimise makespan × (1 + λ × "
                           "migrations / movable tasks), so at a low price extra migrations are worth a shorter makespan and at a high "
                           "price they are not. Source: results/h13_event_gamma.", S["note"]))
    for lam, rows in h13_tables().items():
        story.append(KeepTogether([
            Paragraph({0.05: "Low migration price (λ = 0.05)", 0.2: "Medium migration price (λ = 0.2)",
                       1.0: "High migration price (λ = 1.0)"}[lam], S["h"]),
            table(rows, [72 * mm, 30 * mm] + [(W - 102 * mm) / 4] * 4, ours=())]))

    doc = SimpleDocTemplate(OUT, pagesize=landscape(A4), leftMargin=15 * mm, rightMargin=15 * mm, topMargin=13 * mm,
                            bottomMargin=12 * mm, title="Quantum-Inspired MRFO and DMO — Exact Values", author="QCCProject")
    doc.build(story)
    print("wrote", OUT)


if __name__ == "__main__":
    build()
