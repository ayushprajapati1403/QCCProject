"""V1 pilot: classical DMO vs QI-DMO (three measurement modes) vs GA, same budget, same instances as observe_v0."""
import numpy as np, sys, json, time
sys.path.insert(0, ".")
from qi_core import *
from qi_quantum import run_qidmo

def summarize(name, runs, inst):
    bests = [r["best_f"] for r in runs]
    s = {}
    for k in runs[0]["tracker"].summary():
        s[k] = float(np.mean([r["tracker"].summary()[k] for r in runs]))
    trs = [r["tracker"] for r in runs]
    s["div_end"] = float(np.mean([t.div_ham[-1] for t in trs]))
    s["best@25%"] = float(np.mean([t.best[len(t.best)//4] for t in trs]))
    s["best@50%"] = float(np.mean([t.best[len(t.best)//2] for t in trs]))
    if hasattr(trs[0], "purity"):
        s["purity_end"] = float(np.mean([t.purity[-1] for t in trs]))
        s["purity_mid"] = float(np.mean([t.purity[len(t.purity)//2] for t in trs]))
    gap = (np.mean(bests) - inst.lower_bound()) / inst.lower_bound() * 100
    print(f"{name:14s} best mean={np.mean(bests):8.2f} sd={np.std(bests):6.2f} gap={gap:5.1f}% | " + " ".join(f"{k}={v:.3f}" for k, v in s.items()))
    return bests

if __name__ == "__main__":
    seeds = range(5); budget = 20000
    for (n, m, dist, het) in [(30, 5, "uniform", "high"), (50, 10, "bimodal", "high"), (100, 10, "uniform", "high"), (50, 10, "uniform", "none")]:
        inst = make_instance(n, m, seed=1, task_dist=dist, hetero=het)
        print(f"\n=== n={n} m={m} tasks={dist} vms={het}  LB={inst.lower_bound():.2f} MaxMin={Objective(inst)(max_min(inst)):.2f}")
        summarize("DMO(classical)", [run_dmo(inst, Objective(inst), budget, seed=s) for s in seeds], inst)
        summarize("QI-DMO signed", [run_qidmo(inst, Objective(inst), budget, seed=s, mode="born_signed") for s in seeds], inst)
        summarize("QI-DMO abs", [run_qidmo(inst, Objective(inst), budget, seed=s, mode="born_abs") for s in seeds], inst)
        summarize("P-DMO linear", [run_qidmo(inst, Objective(inst), budget, seed=s, mode="linear") for s in seeds], inst)
        summarize("GA", [run_ga(inst, Objective(inst), budget, seed=s) for s in seeds], inst)
