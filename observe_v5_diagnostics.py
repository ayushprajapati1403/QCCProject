"""V5 OBSERVE: where do QI-MRFO's evaluations go? (diagnostic only; library code untouched)

A Tracker subclass is patched into qi_quantum for the duration of the run. Per candidate it records:
move size K (tasks changed vs the parent's schedule), whether the schedule was EVER evaluated before in the run
(global duplicate), whether any changed task sat on the parent's critical (makespan) VM, and improvement.
Output: results/v5_diagnostics.txt and results/v5_diagnostics.json (new files; nothing existing is overwritten).
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qi_core, qi_quantum
from qi_core import make_instance, Objective, max_min

class DiagTracker(qi_core.Tracker):
    inst = None
    def __init__(self, n, m):
        super().__init__(n, m)
        self.seen = set(); self.rows = []
    def candidate(self, parent_assign, child_assign, f_parent, f_child):
        super().candidate(parent_assign, child_assign, f_parent, f_child)
        inst = DiagTracker.inst; ar = np.arange(inst.n)
        loads = np.bincount(parent_assign, weights=inst.et[ar, parent_assign], minlength=inst.m)
        crit = loads.argmax(); changed = parent_assign != child_assign
        key = child_assign.tobytes(); dup = key in self.seen; self.seen.add(key)
        self.rows.append((int(changed.sum()), dup, bool((changed & (parent_assign == crit)).any()), f_child < f_parent - 1e-12))

def run(spec, seeds, budget=20000, c=1.0, mode="born_signed"):
    n, m, dist, het = spec
    inst = make_instance(n, m, seed=1, task_dist=dist, hetero=het); DiagTracker.inst = inst
    orig = qi_quantum.Tracker; qi_quantum.Tracker = DiagTracker
    try:
        out = []
        for s in seeds:
            r = qi_quantum.run_qimrfo(inst, Objective(inst), budget, P=30, seed=s, decoherence=c / n, mode=mode)
            tr = r["tracker"]; R = np.array(tr.rows, dtype=float)
            K, dup, crit, imp = R[:, 0], R[:, 1].astype(bool), R[:, 2].astype(bool), R[:, 3].astype(bool)
            ev, best = np.array(tr.evals), np.array(tr.best)
            last_impr = ev[np.where(np.diff(best) < 0)[0][-1] + 1] / budget if np.any(np.diff(best) < 0) else 0.0
            out.append({"gap": (r["best_f"] - inst.lower_bound()) / inst.lower_bound(), "dup_global": dup.mean(), "wasted_parent": (K == 0).mean(),
                        "improving": imp.mean(), "K_mean": K.mean(), "K_median_improving": float(np.median(K[imp])) if imp.any() else np.nan,
                        "P_K1": (K == 1).mean(), "P_K2": (K == 2).mean(), "P_K3plus": (K >= 3).mean(),
                        "impr_rate_K1": imp[K == 1].mean() if (K == 1).any() else np.nan, "impr_rate_K2": imp[K == 2].mean() if (K == 2).any() else np.nan,
                        "impr_rate_K3plus": imp[K >= 3].mean() if (K >= 3).any() else np.nan,
                        "touch_crit": crit.mean(), "impr_rate_touch_crit": imp[crit].mean() if crit.any() else np.nan,
                        "impr_rate_no_crit": imp[~crit & (K > 0)].mean() if (~crit & (K > 0)).any() else np.nan,
                        "frac_impr_touch_crit": crit[imp].mean() if imp.any() else np.nan,
                        "last_gb_improvement_at": last_impr, "late_half_improving": imp[len(imp) // 2:].mean(),
                        "late_half_dup_global": dup[len(dup) // 2:].mean()})
        return inst, out
    finally:
        qi_quantum.Tracker = orig

if __name__ == "__main__":
    SPECS = [(30, 5, "uniform", "high"), (50, 10, "bimodal", "high"), (100, 10, "uniform", "high"), (50, 10, "uniform", "none")]
    lines, js = [], {}
    for spec in SPECS:
        inst, out = run(spec, seeds=range(5))
        agg = {k: float(np.nanmean([o[k] for o in out])) for k in out[0]}
        mm = Objective(inst)._raw(max_min(inst))[0]
        head = f"=== n={spec[0]} m={spec[1]} {spec[2]} {spec[3]}  (QI-MRFO c=1, 5 seeds, 20k evals)  MaxMin gap={(mm - inst.lower_bound()) / inst.lower_bound() * 100:.2f}%"
        lines.append(head); lines.append("  " + "  ".join(f"{k}={v:.4f}" for k, v in agg.items()))
        js[" ".join(map(str, spec))] = agg
    txt = "\n".join(lines); print(txt)
    os.makedirs("results", exist_ok=True)
    for p in ("results/v5_diagnostics.txt", "results/v5_diagnostics.json"):
        assert not os.path.exists(p), f"{p} exists (results are immutable)"
    open("results/v5_diagnostics.txt", "w").write(txt + "\n"); json.dump(js, open("results/v5_diagnostics.json", "w"), indent=1)
