"""
qi_dynamic.py - dynamic-workload harness (cloud-specific extension pilot).
An environment is a sequence of instances; between epochs the workload or the VM pool changes.
Each optimizer is re-run with a per-epoch evaluation budget, either from scratch (restart), from its carried
state (continue), or from a decohered state (shock, register-based optimizers only).
"""
import numpy as np
from qi_core import (CloudInstance, make_instance, sample_task_lengths, sample_vm_speeds, Objective,
                     run_mrfo, run_dmo, run_ga, run_pso, max_min)
from qi_quantum import (run_qimrfo, run_qidmo, shock_state, remove_vm_state, add_vm_state, add_tasks_state)

# %% S17 dynamic harness

def make_dynamic_sequence(n, m, seed, K=6, change="churn", rho=0.2, task_dist="uniform", hetero="high"):
    """Returns [(instance, change_info)]; change_info of epoch 0 is None."""
    rng = np.random.default_rng(seed + 1000)
    inst = make_instance(n, m, seed, task_dist, hetero)
    seq = [(inst, None)]
    for k in range(K):
        if change == "churn":                       # rho of the tasks complete and are replaced by new arrivals
            idx = rng.choice(inst.n, max(1, int(rho * inst.n)), replace=False)
            L = inst.task_len.copy(); L[idx] = sample_task_lengths(rng, len(idx), task_dist)
            inst = inst.copy_with(task_len=L); info = {"type": "churn", "idx": idx}
        elif change == "vm_fail":                   # one VM disappears (spot instance reclaimed / failure)
            j = int(rng.integers(inst.m))
            inst = CloudInstance(inst.task_len, np.delete(inst.vm_mips, j), np.delete(inst.vm_p_idle, j), np.delete(inst.vm_p_max, j))
            info = {"type": "vm_fail", "j": j}
        elif change == "vm_add":                    # a VM is added (scale-out)
            S = sample_vm_speeds(rng, 1, hetero); pm_ = 100.0 + 0.1 * S
            inst = CloudInstance(inst.task_len, np.append(inst.vm_mips, S), np.append(inst.vm_p_idle, 0.6 * pm_), np.append(inst.vm_p_max, pm_))
            info = {"type": "vm_add"}
        elif change == "drift":                     # VM speeds drift (contention / noisy neighbours)
            inst = inst.copy_with(vm_mips=inst.vm_mips * rng.lognormal(0, 0.3, inst.m)); info = {"type": "drift"}
        else:
            raise ValueError(change)
        seq.append((inst, info))
    return seq

# --- state adaptation to structural changes ---------------------------------------------------------------
def adapt_register_state(state, info, mode, rng, struct=True):
    """Shape changes (VM removed/added) must always be applied; `struct` additionally resets the registers of
    replaced (new) tasks to the uniform superposition instead of keeping the old task's register."""
    if info is None: return state
    if info["type"] == "vm_fail": return remove_vm_state(state, info["j"], mode)
    if info["type"] == "vm_add": return add_vm_state(state, mode)
    if info["type"] == "churn" and struct: return add_tasks_state(state, info["idx"], mode)
    return state

def adapt_position_state(state, info, m_new, rng):
    """Continuous floor-encoded positions under structural change (the standard swarm encoding has no clean rule)."""
    if info is None: return state
    X = state["X"].copy()
    if info["type"] == "vm_fail":
        j = info["j"]
        on_j = (X >= j) & (X < j + 1)
        X[X >= j + 1] -= 1
        X[on_j] = rng.uniform(0, m_new, on_j.sum())
    new = dict(state); new["X"] = X
    return new

def adapt_ga_state(state, info, m_new, rng):
    if info is None: return state
    A = state["A"].copy()
    if info["type"] == "vm_fail":
        j = info["j"]; A[A > j] -= 1; bad = A == j; A[bad] = rng.integers(0, m_new, bad.sum())
    return {"A": A}

# --- strategies --------------------------------------------------------------------------------------------
def run_dynamic(seq, algo, strategy, budget0, budget, seed, P=30, decoherence_c=0.5, mode="born_signed", gamma_shock=0.5):
    """algo in {'QI-MRFO','QI-DMO','MRFO','DMO','GA','PSO'}; strategy in {'restart','continue','continue_struct','shock','hypermut'}.
    Returns per-epoch dict: best makespan, LB, MaxMin makespan, and normalised area under the best-so-far curve."""
    rng = np.random.default_rng(seed + 7)
    state = None; out = []
    for e, (inst, info) in enumerate(seq):
        obj = Objective(inst); B = budget0 if e == 0 else budget
        n, m = inst.n, inst.m
        init = None
        if e > 0 and strategy != "restart":
            if algo in ("QI-MRFO", "QI-DMO"):
                init = adapt_register_state(state, info, mode, rng, struct=(strategy != "continue"))
                if strategy == "shock": init = shock_state(init, gamma_shock, mode)
            elif algo in ("MRFO", "DMO", "PSO"):
                init = adapt_position_state(state, info, m, rng)
            elif algo == "GA":
                init = adapt_ga_state(state, info, m, rng)
        if algo == "QI-MRFO": r = run_qimrfo(inst, obj, B, P=P, seed=seed * 100 + e, decoherence=decoherence_c / n, mode=mode, init_state=init, track=False)
        elif algo == "QI-DMO": r = run_qidmo(inst, obj, B, P=P, seed=seed * 100 + e, decoherence=0.25 / n, mode=mode, init_state=init, track=False)
        elif algo == "MRFO": r = run_mrfo(inst, obj, B, P=P, seed=seed * 100 + e, init_state=init, track=False)
        elif algo == "DMO": r = run_dmo(inst, obj, B, P=P, seed=seed * 100 + e, init_state=init, track=False)
        elif algo == "PSO": r = run_pso(inst, obj, B, P=P, seed=seed * 100 + e, init_state=init, track=False)
        elif algo == "GA": r = run_ga(inst, obj, B, P=P, seed=seed * 100 + e, init_state=init, track=False, hypermutation=(0.2 if strategy == "hypermut" else 0.0))
        else: raise ValueError(algo)
        state = r["state"]; tr = r["tracker"]
        lb = inst.lower_bound(); mm = obj._raw(max_min(inst))[0]
        ev = np.array(tr.evals, float); bs = np.array(tr.best, float)
        auc = float((getattr(np, 'trapezoid', None) or np.trapz)((bs - lb) / lb, ev) / max(1e-9, ev[-1] - ev[0])) if len(ev) > 1 else float((bs[-1] - lb) / lb)
        out.append({"epoch": e, "best": float(r["best_f"]), "lb": lb, "maxmin": mm, "gap": (r["best_f"] - lb) / lb, "auc_gap": auc, "m": m})
    return out
