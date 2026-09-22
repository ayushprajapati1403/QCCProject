"""POST HOC mechanism check for H8 (exploratory; written after reading results/h8_analysis.md).
Claim: after a VM addition, on a well-balanced deployed schedule, every SINGLE-task move onto the new VM is uphill under
the migration-aware cost (tiny makespan gain < one migration's price), whereas a COORDINATED move (one task from each
old VM onto the new VM) is downhill. That would explain why the (1+1)-EA never leaves the deployed schedule in vm_add
epochs while the register swarm (whose VM-addition rule gives the new VM a uniform share in every register) does.
Output: results/h8_posthoc_barrier.md (write-once)."""
import os, numpy as np
from qi_dynamic import make_dynamic_sequence, run_dynamic
from qi_core import Objective

rows = []
for seed in range(201, 211):
    seq = make_dynamic_sequence(100, 10, seed=seed, K=1, change="vm_add")
    a0 = run_dynamic(seq[:1], "QI-MRFO", "continue_struct", 20000, 4000, seed=seed, decoherence_c=1.0, algo_kw={"exchange": 1.0})[0]["assign"]
    inst = seq[1][0]; n, m = inst.n, inst.m; new = m - 1
    for lam in (0.05, 0.2, 1.0):
        obj = Objective(inst, kind="makespan_migration", ref=a0, mig_mask=np.ones(n, bool), lam=lam)
        base = obj(a0)
        singles = [obj(np.where(np.arange(n) == t, new, a0)) - base for t in range(n)]
        # coordinated: from every old VM move its shortest task to the new VM
        coord = a0.copy()
        for v in range(m - 1):
            T = np.flatnonzero(a0 == v)
            if len(T): coord[T[np.argmin(inst.task_len[T])]] = new
        rows.append((seed, lam, min(singles) / base * 100, (obj(coord) - base) / base * 100, int((coord != a0).sum())))
out = ["# H8 post hoc barrier check (EXPLORATORY)\n",
       "Deployed schedule = QI-MRFO+CXM epoch-0 best (n=100, m=10); one VM added. Relative cost change (%) under the migration-aware objective.\n",
       "| seed | lambda | best single-task move onto the new VM | coordinated move (shortest task of every old VM) | tasks moved |", "|---|---|---|---|---|"]
out += [f"| {s} | {l} | {a:+.3f} | {b:+.3f} | {k} |" for s, l, a, b, k in rows]
single_up = np.mean([r[2] > 0 for r in rows]); coord_down = np.mean([r[3] < 0 for r in rows])
out.append(f"\nSingle-task moves uphill in {single_up:.0%} of cases; coordinated move downhill in {coord_down:.0%} of cases.\n")
path = "results/h8_posthoc_barrier.md"; assert not os.path.exists(path)
open(path, "w").write("\n".join(out)); print("\n".join(out[-12:]))
