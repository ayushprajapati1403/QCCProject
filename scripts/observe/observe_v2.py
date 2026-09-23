"""V2 pilot: decoherence channel strength sweep for QI-DMO + transfer test QI-MRFO. Same instances/budget/seeds as V1."""
import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repository root
sys.path.insert(0, os.path.join(_ROOT, "src")); os.chdir(_ROOT)   # the qi_* modules; paths below are relative to the root
import numpy as np, sys
from qi_core import *
from qi_quantum import run_qidmo, run_qimrfo

def summarize(name, runs, inst):
    bests = [r["best_f"] for r in runs]; trs = [r["tracker"] for r in runs]
    s = {k: float(np.mean([t.summary()[k] for t in trs])) for k in ["wasted_frac", "improving_frac", "mean_move_size", "runtime_s"]}
    s["div_end"] = float(np.mean([t.div_ham[-1] for t in trs]))
    s["best@25%"] = float(np.mean([t.best[len(t.best)//4] for t in trs]))
    if hasattr(trs[0], "purity"): s["purity_end"] = float(np.mean([t.purity[-1] for t in trs]))
    gap = (np.mean(bests) - inst.lower_bound()) / inst.lower_bound() * 100
    print(f"{name:22s} best={np.mean(bests):8.2f} sd={np.std(bests):5.2f} gap={gap:5.1f}% | " + " ".join(f"{k}={v:.3f}" for k, v in s.items()), flush=True)

if __name__ == "__main__":
    seeds = range(5); budget = 20000
    INSTANCES = [(30, 5, "uniform", "high"), (50, 10, "bimodal", "high"), (100, 10, "uniform", "high"), (50, 10, "uniform", "none")]
    sel = [INSTANCES[int(sys.argv[1])]] if len(sys.argv) > 1 else INSTANCES
    for (n, m, dist, het) in sel:
        inst = make_instance(n, m, seed=1, task_dist=dist, hetero=het)
        print(f"\n=== n={n} m={m} tasks={dist} vms={het}  LB={inst.lower_bound():.2f} MaxMin={Objective(inst)(max_min(inst)):.2f}", flush=True)
        summarize("DMO(classical)", [run_dmo(inst, Objective(inst), budget, seed=s) for s in seeds], inst)
        for c in [0.0, 0.25, 0.5, 1.0, 2.0]:
            summarize(f"QI-DMO gamma={c}/n", [run_qidmo(inst, Objective(inst), budget, seed=s, decoherence=c / n) for s in seeds], inst)
        summarize("P-DMO linear g=0.5/n", [run_qidmo(inst, Objective(inst), budget, seed=s, mode="linear", decoherence=0.5 / n) for s in seeds], inst)
        summarize("MRFO(classical)", [run_mrfo(inst, Objective(inst), budget, seed=s) for s in seeds], inst)
        summarize("QI-MRFO gamma=0", [run_qimrfo(inst, Objective(inst), budget, seed=s) for s in seeds], inst)
        summarize("QI-MRFO gamma=0.5/n", [run_qimrfo(inst, Objective(inst), budget, seed=s, decoherence=0.5 / n) for s in seeds], inst)
        summarize("GA", [run_ga(inst, Objective(inst), budget, seed=s) for s in seeds], inst)
