"""V5 OBSERVE (part 2): are the end points of QI-MRFO / GA / Max-Min local optima w.r.t. critical-VM relocation and swap?
Strict makespan improvement only. Output: results/v5_localopt.txt (new file)."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qi_core import make_instance, Objective, max_min, run_ga
from qi_quantum import run_qimrfo

def improving_moves(inst, a):
    """count strictly improving relocations and swaps that move a task off the (unique) critical VM"""
    ar = np.arange(inst.n); L = np.bincount(a, weights=inst.et[ar, a], minlength=inst.m); ms = L.max()
    crit = np.where(np.isclose(L, ms, rtol=0, atol=1e-12))[0]
    if len(crit) > 1: return 0, 0, len(crit)            # ties: no single move can reduce the makespan
    b = crit[0]; Tb = np.where(a == b)[0]; others = np.delete(L, b)
    rel = 0
    for v in range(inst.m):
        if v == b: continue
        rest = np.delete(L, [b, v]).max() if inst.m > 2 else -np.inf
        new = np.maximum(np.maximum(ms - inst.et[Tb, b], L[v] + inst.et[Tb, v]), rest)
        rel += int((new < ms - 1e-9).sum())
    sw = 0
    for u in np.where(a != b)[0]:
        v = a[u]; rest = np.delete(L, [b, v]).max() if inst.m > 2 else -np.inf
        nb = ms - inst.et[Tb, b] + inst.et[u, b]; nv = L[v] - inst.et[u, v] + inst.et[Tb, v]
        sw += int((np.maximum(np.maximum(nb, nv), rest) < ms - 1e-9).sum())
    return rel, sw, 1

if __name__ == "__main__":
    lines = []
    for spec in [(30, 5, "uniform", "high"), (50, 10, "bimodal", "high"), (100, 10, "uniform", "high"), (50, 10, "uniform", "none")]:
        n, m, dist, het = spec; inst = make_instance(n, m, seed=1, task_dist=dist, hetero=het)
        rows = {"Max-Min": [max_min(inst)]}
        rows["QI-MRFO c=1"] = [run_qimrfo(inst, Objective(inst), 20000, P=30, seed=s, decoherence=1.0 / n)["best_assign"] for s in range(5)]
        rows["GA"] = [run_ga(inst, Objective(inst), 20000, P=30, seed=s)["best_assign"] for s in range(5)]
        lines.append(f"=== n={n} m={m} {dist} {het}")
        for k, lst in rows.items():
            res = np.array([improving_moves(inst, a) for a in lst])
            gaps = [(Objective(inst)._raw(a)[0] - inst.lower_bound()) / inst.lower_bound() * 100 for a in lst]
            lines.append(f"  {k:12s} gap={np.mean(gaps):6.2f}%  relocation-optimal={np.mean(res[:, 0] == 0):.2f}  swap-optimal={np.mean(res[:, 1] == 0):.2f}  "
                         f"mean #improving relocations={res[:, 0].mean():6.1f}  mean #improving swaps={res[:, 1].mean():7.1f}  tied-critical-VMs={np.mean(res[:, 2] > 1):.2f}")
    txt = "\n".join(lines); print(txt)
    assert not os.path.exists("results/v5_localopt.txt"); open("results/v5_localopt.txt", "w").write(txt + "\n")
