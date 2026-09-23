"""OBSERVE step: what goes wrong for classical PSO/DMO/MRFO on the makespan landscape?"""
import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repository root
sys.path.insert(0, os.path.join(_ROOT, "src")); os.chdir(_ROOT)   # the qi_* modules; paths below are relative to the root
import numpy as np, sys, json
from qi_core import *

def landscape_probe(inst, n_starts=30, seed=0):
    """At 1-move local optima: neutrality of the 1-move neighbourhood and 2-move (swap) improvability + barrier height."""
    rng = np.random.default_rng(seed); n, m = inst.n, inst.m; ar = np.arange(n)
    neutral_fracs, worse_fracs, swap_improvable, barriers, gaps = [], [], [], [], []
    for s in range(n_starts):
        a = local_search_1move(inst, rng.integers(0, m, n))
        loads = np.bincount(a, weights=inst.et[ar, a], minlength=m); ms = loads.max()
        neu = wor = 0
        for t in range(n):
            for v in range(m):
                if v == a[t]: continue
                b = a.copy(); b[t] = v
                l2 = np.bincount(b, weights=inst.et[ar, b], minlength=m).max()
                if abs(l2 - ms) < 1e-9: neu += 1
                elif l2 > ms: wor += 1
        tot = n * (m - 1)
        neutral_fracs.append(neu / tot); worse_fracs.append(wor / tot)
        bvm = loads.argmax(); best_barrier = None
        for t in np.where(a == bvm)[0]:
            for u in np.where(a != bvm)[0]:
                b = a.copy(); b[t], b[u] = a[u], a[t]
                l2 = np.bincount(b, weights=inst.et[ar, b], minlength=m).max()
                if l2 < ms - 1e-9:
                    c = a.copy(); c[t] = a[u]
                    l_int = np.bincount(c, weights=inst.et[ar, c], minlength=m).max()
                    bar = (l_int - ms) / ms
                    if best_barrier is None or bar < best_barrier: best_barrier = bar
        swap_improvable.append(best_barrier is not None)
        if best_barrier is not None: barriers.append(best_barrier)
        gaps.append((ms - inst.lower_bound()) / inst.lower_bound())
    return {"neutral_frac_1move": float(np.mean(neutral_fracs)), "worse_frac_1move": float(np.mean(worse_fracs)),
            "frac_local_opt_improvable_by_swap": float(np.mean(swap_improvable)),
            "median_barrier_rel": float(np.median(barriers)) if barriers else None,
            "min_barrier_rel": float(np.min(barriers)) if barriers else None,
            "mean_gap_to_LB_at_1move_localopt": float(np.mean(gaps))}

if __name__ == "__main__":
    for (n, m, dist, het) in [(30, 5, "uniform", "high"), (50, 10, "bimodal", "high"), (100, 10, "uniform", "high"), (50, 10, "uniform", "none")]:
        inst = make_instance(n, m, seed=1, task_dist=dist, hetero=het)
        print(f"\n=== instance n={n} m={m} tasks={dist} vms={het}  LB={inst.lower_bound():.2f}  MinMin={Objective(inst)(min_min(inst)):.2f}  MaxMin={Objective(inst)(max_min(inst)):.2f}")
        print("landscape:", json.dumps(landscape_probe(inst, n_starts=20), indent=None))
        budget = 20000
        for name in ["PSO", "DMO", "MRFO", "GA", "Random"]:
            bests, summ = [], []
            for seed in range(5):
                obj = Objective(inst)
                r = ALGOS[name](inst, obj, budget, seed=seed)
                bests.append(r["best_f"]); tr = r["tracker"]; s = tr.summary()
                s["div_ham_start"] = tr.div_ham[1] if len(tr.div_ham) > 1 else tr.div_ham[0]
                s["div_ham_mid"] = tr.div_ham[len(tr.div_ham)//2]; s["div_ham_end"] = tr.div_ham[-1]
                s["best_at_25%"] = tr.best[len(tr.best)//4]; s["best_at_50%"] = tr.best[len(tr.best)//2]
                summ.append(s)
            agg = {k: float(np.mean([s[k] for s in summ])) for k in summ[0]}
            print(f"{name:7s} best mean={np.mean(bests):9.2f} sd={np.std(bests):7.2f}  gap={(np.mean(bests)-inst.lower_bound())/inst.lower_bound()*100:5.1f}% | " +
                  " ".join(f"{k}={v:.3f}" for k, v in agg.items()))
