"""V4 test of the neutrality boundary: does accepting equal-fitness candidates (neutral drift) fix QI-MRFO on plateaus
without hurting it elsewhere?"""
import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repository root
sys.path.insert(0, os.path.join(_ROOT, "src")); os.chdir(_ROOT)   # the qi_* modules; paths below are relative to the root
import numpy as np, sys
from qi_core import *
from qi_quantum import run_qimrfo
seeds = range(5)
for (n, m, dist, het, budget) in [(40, 8, "identical", "none", 10000), (100, 10, "uniform", "high", 20000), (50, 10, "bimodal", "high", 20000), (30, 5, "uniform", "high", 20000)]:
    inst = make_instance(n, m, seed=1, task_dist=dist, hetero=het)
    print(f"\n=== n={n} m={m} {dist} {het} LB={inst.lower_bound():.3f} MaxMin={Objective(inst)(max_min(inst)):.3f}", flush=True)
    for ae in [False, True]:
        rs = [run_qimrfo(inst, Objective(inst), budget, seed=s, decoherence=1.0 / n, accept_equal=ae) for s in seeds]
        b = [r["best_f"] for r in rs]; w = np.mean([r["tracker"].summary()["wasted_frac"] for r in rs]); neu = np.mean([r["tracker"].summary()["neutral_frac"] for r in rs])
        print(f"QI-MRFO c=1 accept_equal={ae!s:5s} best={np.mean(b):8.3f} sd={np.std(b):6.3f} gap={(np.mean(b)-inst.lower_bound())/inst.lower_bound()*100:6.2f}%  wasted={w:.3f} neutral={neu:.3f}", flush=True)
