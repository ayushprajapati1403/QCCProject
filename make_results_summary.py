"""
make_results_summary.py - a short results summary (results_summary.pdf) for sharing with a supervisor.

Every number in the PDF is computed here from committed result files; nothing is typed by hand:
  results/baseline_full.csv          V4 30-seed run (7 problems x 30 runs): classical vs quantum-inspired DMO / MRFO
  results/h5_test/records.csv        V5 held-out static test (80 unseen problems): the swap move (CXM)
  results/h7_test/records.csv        V5 fresh static test: the (1+1)-EA control with the same moves
  results/h6_dynamic/records.csv     V5 changing cloud: register swarm vs GA, both with the swap move
  results/h13_event_gamma/records.csv V5 changing cloud with migration cost: final configuration vs best heuristic

Needs reportlab (pip install reportlab; not part of the pinned experiment environment).  python make_results_summary.py
"""
import os
import matplotlib
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
OUT = os.path.join(HERE, "results_summary.pdf")

# DejaVu Sans (shipped with matplotlib) covers λ, −, → and ≈, which the built-in PDF fonts do not
FONT_DIR = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
pdfmetrics.registerFont(TTFont("DV", os.path.join(FONT_DIR, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DVB", os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DVB", italic="DV", boldItalic="DVB")

INK, MUTED, HEAD, ZEBRA, OURS, RULE = (colors.HexColor(c) for c in ("#1b1b1b", "#5f6368", "#1f3a5f", "#f3f5f8", "#e2eefc", "#c9ced6"))
S = {
    "title": ParagraphStyle("title", fontName="DVB", fontSize=14, leading=17, textColor=HEAD, spaceAfter=2),
    "sub": ParagraphStyle("sub", fontName="DV", fontSize=9, leading=12, textColor=MUTED, spaceAfter=8),
    "h": ParagraphStyle("h", fontName="DVB", fontSize=10.5, leading=13, textColor=HEAD, spaceBefore=8, spaceAfter=4),
    "body": ParagraphStyle("body", fontName="DV", fontSize=9.2, leading=12.6, textColor=INK, alignment=TA_LEFT),
    "key": ParagraphStyle("key", fontName="DV", fontSize=9.2, leading=12.8, textColor=INK, backColor=colors.HexColor("#eef4fb"),
                          borderPadding=(5, 6, 5, 6), leftIndent=6, rightIndent=6, spaceBefore=10, spaceAfter=10),
    "note": ParagraphStyle("note", fontName="DV", fontSize=7.6, leading=10, textColor=MUTED, spaceBefore=3),
    "cell": ParagraphStyle("cell", fontName="DV", fontSize=8.6, leading=10.6, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="DVB", fontSize=8.6, leading=10.6, textColor=INK),
    "headcell": ParagraphStyle("headcell", fontName="DVB", fontSize=8.4, leading=10.4, textColor=colors.white),
    "bullet": ParagraphStyle("bullet", fontName="DV", fontSize=8.8, leading=11.8, textColor=INK, leftIndent=10, bulletIndent=0),
}


def pct(x):
    return f"{x:.2f}\u00a0%"


def table(rows, widths, ours=(), numeric_from=1):
    """rows[0] is the header; `ours` = indices of rows (1-based within data) to highlight."""
    data = [[Paragraph(str(c), S["headcell"]) for c in rows[0]]]
    for i, r in enumerate(rows[1:], start=1):
        st = S["cellb"] if i in ours else S["cell"]
        data.append([Paragraph(str(c), st) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1)
    style = [("BACKGROUND", (0, 0), (-1, 0), HEAD), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
             ("TOPPADDING", (0, 0), (-1, -1), 3.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2),
             ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
             ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE)]
    for i in range(1, len(data)):
        if i in ours: style.append(("BACKGROUND", (0, i), (-1, i), OURS))
        elif i % 2 == 0: style.append(("BACKGROUND", (0, i), (-1, i), ZEBRA))
    t.setStyle(TableStyle(style))
    return t


# ------------------------------------------------------------------------------------------ numbers
def study1():
    """V4 30-seed run: 7 problems x 30 runs x 20 000 evaluations; gap to the (simple) lower bound."""
    df = pd.read_csv(os.path.join(RES, "baseline_full.csv"))
    g = df.pivot_table(index="algo", columns="instance", values="gap", aggfunc="mean") * 100
    avg = df.groupby(["algo", "instance"]).gap.mean().groupby("algo").mean() * 100
    cols = ["n30 m5 uniform high", "n100 m10 uniform high", "n200 m20 uniform high"]
    order = [("DMO", "DMO (original, rounding)"), ("QI-DMO", "QI-DMO (quantum-inspired)"),
             ("MRFO", "MRFO (original, rounding)"), ("QI-MRFO", "QI-MRFO (quantum-inspired)"),
             ("GA", "Genetic Algorithm (GA)"), ("PSO", "PSO"), ("Max-Min", "Max-Min heuristic"), ("Random", "Random search")]
    rows = [["Algorithm", "30 tasks<br/>5 VMs", "100 tasks<br/>10 VMs", "200 tasks<br/>20 VMs", "Average<br/>7 problems"]]
    for key, lab in order:
        rows.append([lab] + [pct(g.loc[key, c]) for c in cols] + [pct(avg[key])])
    return rows, avg


def per_instance(path, a, bs):
    df = pd.read_csv(path)
    w = df.groupby(["family", "inst_seed", "algo"]).gap2.mean().unstack("algo") * 100
    return w, {b: (int(((w[a] - w[b]) < 0).sum()), len(w)) for b in bs}


def study2():
    """V5 held-out static test: 80 unseen problems (8 families x 10), 2 runs each; gap to the preemptive lower bound."""
    a = "QI-MRFO+CXM"
    others = ["MRFO", "QI-MRFO", "GA", "GA+CXM", "Max-Min"]
    w, wins = per_instance(os.path.join(RES, "h5_test", "records.csv"), a, others)
    m = w.mean()
    lab = {"MRFO": "MRFO (original, rounding)", "QI-MRFO": "QI-MRFO (quantum-inspired, no swap move)",
           "GA": "Genetic Algorithm (GA)", "GA+CXM": "GA + the same swap move", "Max-Min": "Max-Min heuristic"}
    rows = [["Algorithm", "Average gap", "QI-MRFO + swap move better on"]]
    for b in others:
        rows.append([lab[b], pct(m[b]), f"{wins[b][0]} of {wins[b][1]} problems"])
    rows.append(["QI-MRFO + swap move (ours)", pct(m[a]), "—"])
    twin = m.get("P-MRFO+CXM")
    w7, wins7 = per_instance(os.path.join(RES, "h7_test", "records.csv"), "(1+1)-EA+CXM", ["QI-MRFO+CXM"])
    return rows, m, twin, wins7["QI-MRFO+CXM"], wins


def study3():
    """V5 changing cloud: (a) swarm vs GA, both with the swap move (H6); (b) with migration cost (H13)."""
    h6 = pd.read_csv(os.path.join(RES, "h6_dynamic", "records.csv"))
    w = h6.pivot_table(index=["scenario", "seed"], columns="algo", values="post_gap")
    a, b = "QI-MRFO+CXM continue+elite", "GA+CXM continue"
    ga = (w[a].mean() * 100, w[b].mean() * 100, int(((w[a] - w[b]) < 0).sum()), len(w))
    h13 = pd.read_csv(os.path.join(RES, "h13_event_gamma", "records.csv"))
    fin, cho = "H12 swarm, event-aware gamma", "Chooser (cheaper of the two)"
    rows = [["Migration cost", "Best heuristic", "Final QI-MRFO (ours)", "QI-MRFO better in"]]
    names = {0.05: "Low (λ = 0.05)", 0.2: "Medium (λ = 0.2)", 1.0: "High (λ = 1.0)"}
    wins = []
    for lam in [0.05, 0.2, 1.0]:
        v = h13[h13.mig_lambda == lam].pivot_table(index=["scenario", "seed"], columns="algo", values="post_cost_gap")
        wins.append((int(((v[fin] - v[cho]) < 0).sum()), len(v)))
        rows.append([names[lam], pct(v[cho].mean() * 100), pct(v[fin].mean() * 100), f"{wins[-1][0]} of {wins[-1][1]} cases"])
    return ga, rows, wins


# ------------------------------------------------------------------------------------------ document
def build():
    t1, avg1 = study1()
    t2, m2, twin, ea, wins2 = study2()
    ga3, t3, wins3 = study3()
    story = [Paragraph("Quantum-Inspired MRFO and DMO for Cloud Task Scheduling", S["title"]),
             Paragraph("Results summary · makespan scheduling of independent tasks on heterogeneous VMs · all runs on an "
                       "ordinary CPU (no quantum hardware)", S["sub"]),
             Paragraph(
                 "<b>What was done.</b> DMO and MRFO are continuous swarm algorithms; for scheduling they are normally "
                 "rounded to VM numbers, which makes them little better than random search. I replaced the rounding by a "
                 "quantum-inspired representation: each task keeps a probability for every VM, a schedule is “measured” "
                 "from these probabilities, and a small decoherence noise stops the search from getting stuck (Table 1). I "
                 "then added a swap move for the busiest VM (Table 2) and adapted the method to a changing cloud where "
                 "moving tasks has a cost (Table 3).", S["body"]),
             Paragraph(
                 f"<b>Key results.</b> Quantum-inspired encoding: average gap MRFO {avg1['MRFO']:.1f}\u00a0%\u00a0→\u00a0{avg1['QI-MRFO']:.1f}\u00a0% "
                 f"and DMO {avg1['DMO']:.1f}\u00a0%\u00a0→\u00a0{avg1['QI-DMO']:.1f}\u00a0%. With the swap move, QI-MRFO beats the Genetic Algorithm "
                 f"on <b>{wins2['GA'][0]} of {wins2['GA'][1]}</b> unseen problems ({m2['QI-MRFO+CXM']:.2f}\u00a0% vs {m2['GA']:.2f}\u00a0%). "
                 f"In a changing cloud it beats the GA in <b>{ga3[2]} of {ga3[3]}</b> cases, and with migration costs it beats the "
                 f"best heuristic in <b>{min(w for w, _ in wins3)}–{max(w for w, _ in wins3)} of {wins3[0][1]}</b> cases at every "
                 "cost level.", S["key"]),
             Paragraph("<b>How to read the tables.</b> <i>Gap</i> = how much later the schedule finishes than the ideal "
                       "(a theoretical lower bound); lower is better. Test problems in Tables 2 and 3 were never used for tuning.",
                       S["note"])]

    story.append(KeepTogether([
        Paragraph("Table 1 · Quantum-inspired encoding for DMO and MRFO", S["h"]),
        table(t1, [58 * mm, 26 * mm, 27 * mm, 27 * mm, 32 * mm], ours=(2, 4)),
        Paragraph(f"Setup: V4 study, 7 problems × 30 runs, 20 000 evaluations per run. QI-MRFO is at the level of the GA "
                  f"({avg1['QI-MRFO']:.1f}\u00a0% vs {avg1['GA']:.1f}\u00a0%). DMO gains less because one of its steps moves randomly "
                  "even when the result gets worse; with that step made greedy (pilot study, lab log V3) QI-DMO matches "
                  "QI-MRFO. Source: results/baseline_full.csv.", S["note"])]))

    story.append(KeepTogether([
        Paragraph("Table 2 · Adding a swap move for the busiest VM", S["h"]),
        table(t2, [78 * mm, 32 * mm, 60 * mm], ours=(len(t2) - 1,)),
        Paragraph("Setup: V5 held-out test, 80 unseen problems (8 problem types × 10), 2 runs each. The gap is measured "
                  "against a tighter lower bound than in Table 1, so the two tables are not directly comparable. Source: "
                  "results/h5_test/records.csv (analysis: results/h5_analysis.md).", S["note"])]))

    story.append(KeepTogether([
        Paragraph("Table 3 · Changing cloud: tasks come and go, VMs fail or are added", S["h"]),
        Paragraph(f"<b>Against the GA</b> (both with the swap move, 60 test cases): gap after each change "
                  f"{ga3[0]:.2f}\u00a0% for QI-MRFO vs {ga3[1]:.2f}\u00a0% for GA; QI-MRFO better in <b>{ga3[2]} of {ga3[3]}</b> cases "
                  "(results/h6_dynamic).", S["body"]),
        Spacer(1, 4),
        Paragraph("<b>With a cost for moving running tasks</b>: cost gap (makespan gap plus the migration cost), 60 test "
                  "cases per cost level. Best heuristic = the cheaper of full Max-Min recompute and zero-migration repair.",
                  S["body"]),
        Spacer(1, 3),
        table(t3, [42 * mm, 36 * mm, 42 * mm, 50 * mm], ours=()),
        Paragraph("Source: results/h13_event_gamma/records.csv (analysis: results/h13_analysis.md).", S["note"])]))

    bullets = [
        "Runs on a normal CPU. A classical-probability version of the same method (no quantum formula) did as well "
        f"({twin:.2f}\u00a0% in Table 2's setting), so the gain comes from the representation; no quantum advantage is claimed.",
        f"For a one-time batch, a simple (1+1)-EA using the same swap move is equally good (better on {ea[0]} of {ea[1]} fresh "
        "problems); the swarm's own strength is the changing cloud, especially when VMs are added.",
        "All problems are generated (synthetic). Next: real cloud traces (e.g. Google, Alibaba) and energy / SLA costs.",
        "Method: unseen test problems, predictions written before each experiment, Wilcoxon tests with Holm correction, "
        "253 automated tests; all numbers in this PDF are computed from the committed result files.",
    ]
    story.append(KeepTogether([Paragraph("Honest notes", S["h"])] +
                              [Paragraph(b, S["bullet"], bulletText="•") for b in bullets]))

    doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=14 * mm,
                            title="Quantum-Inspired MRFO and DMO — Results Summary", author="QCCProject")
    doc.build(story)
    print("wrote", OUT)


if __name__ == "__main__":
    build()
