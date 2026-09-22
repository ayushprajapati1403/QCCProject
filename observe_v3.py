"""V3 ablations: (a) is DMO's unconditional step the reason QI-DMO < QI-MRFO? (b) attractor basis vs register,
(c) QI-MRFO decoherence sweep + classical twin (linear) + unsigned amplitudes. Same instances/budget/seeds."""
import numpy as np, sys
sys.path.insert(0, ".")
from qi_core import *
from qi_quantum import run_qidmo, run_qimrfo

def summarize(name, runs, inst):
    bests = [r["best_f"] for r in runs]; trs = [r["tracker"] for r in runs]
    s = {k: float(np.mean([t.summary()[k] for t in trs])) for k in ["wasted_frac", "mean_move_size", "gb_impr_per_1k", "runtime_s"]}
    s["div_end"] = float(np.mean([t.div_ham[-1] for t in trs]))
    s["best@25%"] = float(np.mean([t.best[len(t.best)//4] for t in trs]))
    if hasattr(trs[0], "purity"): s["purity_end"] = float(np.mean([t.purity[-1] for t in trs]))
    gap = (np.mean(bests) - inst.lower_bound()) / inst.lower_bound() * 100
    print(f"{name:26s} best={np.mean(bests):8.2f} sd={np.std(bests):5.2f} gap={gap:5.1f}% | " + " ".join(f"{k}={v:.3f}" for k, v in s.items()), flush=True)

if __name__ == "__main__":
    seeds = range(5); budget = 20000
    INSTANCES = [(30, 5, "uniform", "high"), (50, 10, "bimodal", "high"), (100, 10, "uniform", "high"), (50, 10, "uniform", "none")]
    sel = [INSTANCES[int(sys.argv[1])]] if len(sys.argv) > 1 else INSTANCES
    for (n, m, dist, het) in sel:
        inst = make_instance(n, m, seed=1, task_dist=dist, hetero=het)
        print(f"\n=== n={n} m={m} tasks={dist} vms={het}  LB={inst.lower_bound():.2f} MaxMin={Objective(inst)(max_min(inst)):.2f} MinMin={Objective(inst)(min_min(inst)):.2f}", flush=True)
        summarize("DMO greedy_next", [run_dmo(inst, Objective(inst), budget, seed=s, greedy_next=True) for s in seeds], inst)
        summarize("QI-DMO g=.25/n greedy_next", [run_qidmo(inst, Objective(inst), budget, seed=s, decoherence=0.25 / n, greedy_next=True) for s in seeds], inst)
        summarize("QI-DMO g=.25/n attr=register", [run_qidmo(inst, Objective(inst), budget, seed=s, decoherence=0.25 / n, attractor="register") for s in seeds], inst)
        for c in [0.25, 1.0, 2.0]:
            summarize(f"QI-MRFO g={c}/n", [run_qimrfo(inst, Objective(inst), budget, seed=s, decoherence=c / n) for s in seeds], inst)
        summarize("QI-MRFO g=.5/n linear", [run_qimrfo(inst, Objective(inst), budget, seed=s, decoherence=0.5 / n, mode="linear") for s in seeds], inst)
        summarize("QI-MRFO g=.5/n abs", [run_qimrfo(inst, Objective(inst), budget, seed=s, decoherence=0.5 / n, mode="born_abs") for s in seeds], inst)
        summarize("QI-MRFO g=.5/n P=15", [run_qimrfo(inst, Objective(inst), budget, seed=s, decoherence=0.5 / n, P=15) for s in seeds], inst)
        summarize("QI-MRFO g=.5/n P=60", [run_qimrfo(inst, Objective(inst), budget, seed=s, decoherence=0.5 / n, P=60) for s in seeds], inst)
