"""Change-severity sweep: does the best decoherence-shock strength grow with the fraction of replaced tasks?"""
import numpy as np, sys, json
sys.path.insert(0, ".")
from qi_dynamic import make_dynamic_sequence, run_dynamic

if __name__ == "__main__":
    rho = float(sys.argv[1]) if len(sys.argv) > 1 else 0.2
    n, m, K = 50, 10, 6; budget0, budget = 15000, 4000; seeds = range(5)
    configs = [("QI-MRFO", "restart", {}), ("QI-MRFO", "continue_struct", {}), ("QI-MRFO", "shock", {"gamma_shock": 0.25}),
               ("QI-MRFO", "shock", {"gamma_shock": 0.5}), ("QI-MRFO", "shock", {"gamma_shock": 0.75}), ("GA", "continue", {}), ("GA", "hypermut", {})]
    print(f"=== churn severity rho={rho}", flush=True)
    rows = []
    for algo, strat, kw in configs:
        gaps, aucs = [], []
        for s in seeds:
            seq = make_dynamic_sequence(n, m, seed=s, K=K, change="churn", rho=rho)
            out = run_dynamic(seq, algo, strat, budget0, budget, seed=s, decoherence_c=1.0, **kw)
            post = out[1:]; gaps.append(np.mean([o["gap"] for o in post])); aucs.append(np.mean([o["auc_gap"] for o in post]))
        label = f"{algo} {strat} {kw.get('gamma_shock','')}"
        print(f"{label:28s} post-change gap={np.mean(gaps)*100:6.2f}% (sd {np.std(gaps)*100:4.2f})  AUC-gap={np.mean(aucs)*100:6.2f}%", flush=True)
        rows.append({"rho": rho, "algo": algo, "strategy": strat, **kw, "gap": float(np.mean(gaps)), "gap_sd": float(np.std(gaps)), "auc": float(np.mean(aucs))})
    json.dump(rows, open(f"results/dyn_severity_{rho}.json", "w"), indent=1)
