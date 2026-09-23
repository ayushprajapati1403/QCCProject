"""Dynamic-workload pilot: does decoherence-based controlled forgetting beat restart / naive continuation?"""
import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the repository root
sys.path.insert(0, os.path.join(_ROOT, "src")); os.chdir(_ROOT)   # the qi_* modules; paths below are relative to the root
import numpy as np, sys, json
from qi_dynamic import make_dynamic_sequence, run_dynamic

if __name__ == "__main__":
    change = sys.argv[1] if len(sys.argv) > 1 else "churn"
    n, m, K = 50, 10, 6; budget0, budget = 15000, 4000; seeds = range(5)
    configs = [("QI-MRFO", "restart", {}), ("QI-MRFO", "continue", {}), ("QI-MRFO", "continue_struct", {}),
               ("QI-MRFO", "shock", {"gamma_shock": 0.25}), ("QI-MRFO", "shock", {"gamma_shock": 0.5}), ("QI-MRFO", "shock", {"gamma_shock": 0.75}),
               ("MRFO", "restart", {}), ("MRFO", "continue", {}),
               ("GA", "restart", {}), ("GA", "continue", {}), ("GA", "hypermut", {})]
    print(f"=== dynamic pilot: change={change} n={n} m={m} K={K} budget0={budget0} budget={budget}", flush=True)
    rows = []
    for algo, strat, kw in configs:
        gaps, aucs, vs_mm = [], [], []
        for s in seeds:
            seq = make_dynamic_sequence(n, m, seed=s, K=K, change=change)
            out = run_dynamic(seq, algo, strat, budget0, budget, seed=s, **kw)
            post = out[1:]                                   # epochs after the first change
            gaps.append(np.mean([o["gap"] for o in post])); aucs.append(np.mean([o["auc_gap"] for o in post]))
            vs_mm.append(np.mean([o["best"] / o["maxmin"] for o in post]))
        label = f"{algo} {strat} {kw.get('gamma_shock','')}"
        print(f"{label:28s} mean post-change gap={np.mean(gaps)*100:6.2f}% (sd {np.std(gaps)*100:4.2f})  AUC-gap={np.mean(aucs)*100:6.2f}%  best/MaxMin={np.mean(vs_mm):.4f}", flush=True)
        rows.append({"algo": algo, "strategy": strat, **kw, "gap": float(np.mean(gaps)), "gap_sd": float(np.std(gaps)), "auc": float(np.mean(aucs)), "vs_maxmin": float(np.mean(vs_mm))})
    json.dump(rows, open(f"results/dyn_{change}.json", "w"), indent=1)
