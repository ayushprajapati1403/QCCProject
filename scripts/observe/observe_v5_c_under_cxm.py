"""V5 OBSERVE (before designing any adaptive-decoherence hypothesis): under CXM, does the decoherence floor still matter?

Dose-response of the fixed floor gamma = c/n for QI-MRFO+CXM and its classical twin P-MRFO+CXM (p_x = 1) on the
DEVELOPMENT set only (4 pilot instances, 10 seeds, 20 000 evaluations). Descriptive: it decides whether an adaptive
controller is worth a pre-registered test (a flat response leaves nothing to adapt). Output: results/v5_c_under_cxm/
(write-once) and results/v5_c_under_cxm.md.
"""
import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repository root
sys.path.insert(0, os.path.join(_ROOT, "src")); os.chdir(_ROOT)   # the qi_* modules; paths below are relative to the root
import os
import pandas as pd
from qi_experiment import spec, make_jobs, run_experiment, TUNE_FAMILIES, TUNE_INST_SEEDS

C_GRID = [0.0, 0.25, 0.5, 1.0, 2.0, 4.0]

if __name__ == "__main__":
    algos = {}
    for c in C_GRID:
        algos[f"QI-MRFO+CXM c={c}"] = spec("run_qimrfo", decoherence_c=c, exchange=1.0)
        algos[f"P-MRFO+CXM c={c}"] = spec("run_qimrfo", decoherence_c=c, exchange=1.0, mode="linear")
    df = run_experiment("v5_c_under_cxm", make_jobs("v5_c_under_cxm", algos, TUNE_FAMILIES, TUNE_INST_SEEDS, list(range(10)), 20000, 30),
                        config={"note": "development set, descriptive observation", "c_grid": C_GRID})
    df["host"] = df.algo.str.split(" c=").str[0]; df["c"] = df.algo.str.split("c=").str[1].astype(float)
    out = ["# V5 observation: decoherence dose-response under CXM (development set, 10 seeds; descriptive)\n"]
    for metric, lab, sc in [("gap2", "mean gap2 (%)", 100), ("dup_global_frac", "global duplicate evaluations", 1),
                            ("last_gb_impr_frac", "last global-best improvement (fraction of budget)", 1), ("div_end", "end diversity", 1)]:
        pv = df.pivot_table(index=["host", "c"], columns="family", values=metric, aggfunc="mean") * sc
        pv["mean"] = pv.mean(1)
        out.append(f"## {lab}\n"); out.append(pv.round(4).reset_index().to_markdown(index=False, floatfmt=".4f") + "\n")
    path = os.path.join("results", "v5_c_under_cxm.md")
    assert not os.path.exists(path), f"{path} exists (write-once)"
    open(path, "w").write("\n".join(out)); print("\n".join(out))
