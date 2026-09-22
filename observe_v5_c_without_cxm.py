"""V5 OBSERVE, control for observe_v5_c_under_cxm.py: is the decoherence floor needed WITHOUT CXM on the same instances?

The dose-response under CXM (results/v5_c_under_cxm.md) is flat for c in [0, 2]. Reading that as "CXM takes over the
floor's role" needs the same contrast without CXM: c = 0 vs c = 1 for QI-MRFO and its classical twin P-MRFO, on the
same DEVELOPMENT set (4 pilot instances, 10 seeds, 20 000 evaluations). Descriptive, not a hypothesis test (run-level
pairs on 4 instances, no held-out seeds). Output: results/v5_c_without_cxm/ (write-once) and
results/v5_c_without_cxm.md, which also tabulates the paired c = 0 - c = 1 contrast of the committed CXM sweep.
"""
import os
import numpy as np
import pandas as pd
from qi_experiment import spec, make_jobs, run_experiment, boot_ci, wilcoxon_p, TUNE_FAMILIES, TUNE_INST_SEEDS

C_GRID = [0.0, 1.0]


def split(df):
    df = df.copy()
    df["host"] = df.algo.str.split(" c=").str[0]; df["c"] = df.algo.str.split("c=").str[1].astype(float)
    return df


def contrast(df, metric, scale):
    """Paired c = 0 - c = 1 per host; pairs = (family, instance seed, run seed)."""
    rows = []
    for host, d in df.groupby("host"):
        w = d.pivot_table(index=["family", "inst_seed", "run_seed"], columns="c", values=metric)
        diff = (w[0.0] - w[1.0]).values * scale
        lo, hi = boot_ci(diff)
        rows.append({"host": host, "pairs": len(diff), "mean c=0": w[0.0].mean() * scale, "mean c=1": w[1.0].mean() * scale,
                     "diff c0-c1": diff.mean(), "CI95 lo": lo, "CI95 hi": hi, "c=0 better": int((diff < 0).sum()),
                     "c=1 better": int((diff > 0).sum()), "p (run-level, descriptive)": wilcoxon_p(diff)})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    algos = {}
    for c in C_GRID:
        algos[f"QI-MRFO c={c}"] = spec("run_qimrfo", decoherence_c=c, exchange=0.0)
        algos[f"P-MRFO c={c}"] = spec("run_qimrfo", decoherence_c=c, exchange=0.0, mode="linear")
    df = split(run_experiment("v5_c_without_cxm", make_jobs("v5_c_without_cxm", algos, TUNE_FAMILIES, TUNE_INST_SEEDS,
                                                            list(range(10)), 20000, 30),
                              config={"note": "development set, descriptive control for v5_c_under_cxm", "c_grid": C_GRID}))
    cxm = split(pd.read_csv(os.path.join("results", "v5_c_under_cxm", "records.csv")))
    cxm = cxm[cxm.c.isin(C_GRID)]
    out = ["# V5 observation: is the decoherence floor needed without CXM? (development set, 10 seeds; descriptive)\n",
           "Same 4 development instances, seeds and budget as `results/v5_c_under_cxm.md`. Pairs = (family, instance seed, "
           "run seed); p values are run-level Wilcoxon tests, descriptive only (4 instances, no held-out seeds).\n"]
    for metric, lab, sc in [("gap2", "gap2 (%)", 100), ("dup_global_frac", "global duplicate evaluations (%)", 100)]:
        out.append(f"## Paired contrast c = 0 − c = 1, {lab}\n")
        tab = pd.concat([contrast(df, metric, sc).assign(condition="without CXM"),
                         contrast(cxm, metric, sc).assign(condition="with CXM (from v5_c_under_cxm)")])
        out.append(tab[["condition"] + [c for c in tab.columns if c != "condition"]].to_markdown(index=False, floatfmt=".4f") + "\n")
    out.append("## mean gap2 (%) by family, without CXM\n")
    pv = df.pivot_table(index=["host", "c"], columns="family", values="gap2", aggfunc="mean") * 100
    pv["mean"] = pv.mean(1)
    out.append(pv.round(4).reset_index().to_markdown(index=False, floatfmt=".4f") + "\n")
    path = os.path.join("results", "v5_c_without_cxm.md")
    assert not os.path.exists(path), f"{path} exists (write-once)"
    open(path, "w").write("\n".join(out)); print("\n".join(out))
