"""
qi_dynamic.py - dynamic-workload harness (cloud-specific extension pilot).
An environment is a sequence of instances; between epochs the workload or the VM pool changes.
Each optimizer is re-run with a per-epoch evaluation budget, either from scratch (restart), from its carried
state (continue), or from a decohered state (shock, register-based optimizers only).
"""
import numpy as np
from qi_core import (CloudInstance, make_instance, sample_task_lengths, sample_vm_speeds, Objective, Tracker,
                     run_mrfo, run_dmo, run_ga, run_pso, run_one_plus_one, max_min)
from qi_quantum import (run_qimrfo, run_qidmo, shock_state, remove_vm_state, add_vm_state, add_tasks_state)

# %% S17 dynamic harness

def make_dynamic_sequence(n, m, seed, K=6, change="churn", rho=0.2, task_dist="uniform", hetero="high"):
    """Returns [(instance, change_info)]; change_info of epoch 0 is None."""
    rng = np.random.default_rng(seed + 1000)
    inst = make_instance(n, m, seed, task_dist, hetero)
    seq = [(inst, None)]
    for k in range(K):
        ctype = change
        if change == "mixed":                       # V5: a random event per epoch (VM failure only while > 3 VMs remain)
            ctype = str(rng.choice(["churn", "drift", "vm_fail", "vm_add"]))
            if ctype == "vm_fail" and inst.m <= 3: ctype = "vm_add"
        if ctype == "churn":                        # rho of the tasks complete and are replaced by new arrivals
            idx = rng.choice(inst.n, max(1, int(rho * inst.n)), replace=False)
            L = inst.task_len.copy(); L[idx] = sample_task_lengths(rng, len(idx), task_dist)
            inst = inst.copy_with(task_len=L); info = {"type": "churn", "idx": idx}
        elif ctype == "vm_fail":                   # one VM disappears (spot instance reclaimed / failure)
            j = int(rng.integers(inst.m))
            inst = CloudInstance(inst.task_len, np.delete(inst.vm_mips, j), np.delete(inst.vm_p_idle, j), np.delete(inst.vm_p_max, j))
            info = {"type": "vm_fail", "j": j}
        elif ctype == "vm_add":                    # a VM is added (scale-out)
            S = sample_vm_speeds(rng, 1, hetero); pm_ = 100.0 + 0.1 * S
            inst = CloudInstance(inst.task_len, np.append(inst.vm_mips, S), np.append(inst.vm_p_idle, 0.6 * pm_), np.append(inst.vm_p_max, pm_))
            info = {"type": "vm_add"}
        elif ctype == "drift":                     # VM speeds drift (contention / noisy neighbours)
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

def adapt_ga_state(state, info, m_new, rng, inst=None, repair="random"):
    if info is None: return state
    A = state["A"].copy()
    if repair == "incremental" and info["type"] in ("churn", "vm_fail"):
        # V5, H12: every carried schedule keeps its persistent tasks and gets the new / orphaned tasks placed longest
        # first on the VM that finishes them earliest (incremental_list_schedule)
        return {"A": np.stack([incremental_list_schedule(a, info, inst, rng) for a in A])}
    if info["type"] == "vm_fail":
        if repair == "greedy":
            return {"A": np.stack([repair_schedule(a, info, inst, rng, "greedy") for a in A])}
        j = info["j"]; A[A > j] -= 1; bad = A == j; A[bad] = rng.integers(0, m_new, bad.sum())
    return {"A": A}

def map_to_new_vms(a, info):
    """Map a schedule of the previous epoch onto the new VM indexing. Returns (mapped, forced) where forced marks the
    tasks whose VM disappeared (mapped value -1)."""
    a = np.asarray(a).copy(); forced = np.zeros(len(a), bool)
    if info is not None and info["type"] == "vm_fail":
        j = info["j"]; forced = a == j; a[a > j] -= 1; a[forced] = -1
    return a, forced

def repair_schedule(a, info, inst_new, rng, how="random"):
    """Make the previous epoch's schedule valid for the new instance. Only a VM failure invalidates it: the tasks of
    the failed VM go to uniformly random VMs ('random', as adapt_ga_state) or, longest first, to the VM that
    finishes them earliest ('greedy', list scheduling on top of the surviving loads). With 'random' and 'greedy' the
    NEW tasks of a churn event stay on the VM of the departed task whose index they took (slot inheritance).
    'incremental' (V5, H12) also places the new tasks longest first on the VM that finishes them earliest, i.e. it
    returns incremental_list_schedule (identical to 'greedy' for every event except churn)."""
    if how == "incremental": return incremental_list_schedule(a, info, inst_new, rng)
    mapped, forced = map_to_new_vms(a, info)
    if not forced.any(): return mapped
    if how == "random":
        mapped[forced] = rng.integers(0, inst_new.m, forced.sum()); return mapped
    keep = ~forced; ar = np.arange(inst_new.n)
    loads = np.bincount(mapped[keep], weights=inst_new.et[ar[keep], mapped[keep]], minlength=inst_new.m)
    for t in ar[forced][np.argsort(-inst_new.task_len[forced], kind="stable")]:
        v = int(np.argmin(loads + inst_new.et[t])); mapped[t] = v; loads[v] += inst_new.et[t, v]
    return mapped

def count_migrations(prev, new, info):
    """Voluntary migrations: tasks that existed in the previous epoch, still exist, whose VM survived, and that the
    new schedule moves. Returns (voluntary, forced, persistent_tasks)."""
    mapped, forced = map_to_new_vms(prev, info)
    persist = np.ones(len(new), bool)
    if info is not None and info["type"] == "churn": persist[info["idx"]] = False
    vol = persist & ~forced & (np.asarray(new) != mapped)
    return int(vol.sum()), int((persist & forced).sum()), int(persist.sum())

def incremental_list_schedule(prev, info, inst_new, rng):
    """Zero-voluntary-migration heuristic: persistent tasks stay; new (churned) and orphaned (failed-VM) tasks are placed
    longest first on the VM that finishes them earliest (Max-Min style on top of the existing loads)."""
    mapped, forced = map_to_new_vms(prev, info)
    place = forced.copy()
    if info is not None and info["type"] == "churn": place[info["idx"]] = True
    keep = ~place; ar = np.arange(inst_new.n)
    loads = np.bincount(mapped[keep], weights=inst_new.et[ar[keep], mapped[keep]], minlength=inst_new.m)
    for t in ar[place][np.argsort(-inst_new.task_len[place], kind="stable")]:
        v = int(np.argmin(loads + inst_new.et[t])); mapped[t] = v; loads[v] += inst_new.et[t, v]
    return mapped

# --- strategies --------------------------------------------------------------------------------------------
def run_dynamic(seq, algo, strategy, budget0, budget, seed, P=30, decoherence_c=0.5, mode="born_signed", gamma_shock=0.5,
                algo_kw=None, carry_elite=False, repair="random", mig_lambda=None, decoherence_by_event=None):
    """algo in {'QI-MRFO','QI-DMO','MRFO','DMO','GA','PSO'} or the per-epoch heuristics {'Max-Min' (full recompute),
    'Incremental' (zero voluntary migration)}; strategy in {'restart','continue','continue_struct','shock','hypermut'}.
    V5 options: algo_kw = extra optimizer kwargs (e.g. {'exchange': 1.0}); carry_elite = the previous epoch's best
    schedule, repaired for the change, seeds the register swarm (QI-MRFO); repair = 'random' | 'greedy' treatment of the
    tasks of a failed VM, or 'incremental' (H12: failed-VM and new churn tasks placed by list scheduling), used for the
    carried elite and the carried population of the GA / (1+1)-EA.
    mig_lambda (V5, H8): after the first epoch every optimizer sees the migration-aware objective
    makespan x (1 + mig_lambda * voluntary migrations / eligible tasks) relative to the previous deployed schedule;
    'Chooser' deploys whichever of Max-Min (recompute) and Incremental is cheaper under that objective.
    decoherence_by_event (V5, H13): {event type: c} overriding decoherence_c after that type of change (epochs e > 0,
    QI-MRFO and the (1+1)-EA); types not in the dict, and epoch 0, keep decoherence_c.
    Returns per-epoch dict: best makespan, LB, MaxMin makespan, normalised area under the best-so-far gap curve, and the
    voluntary / forced migrations of the deployed (best) schedule relative to the previous epoch's."""
    rng = np.random.default_rng(seed + 7)
    kw = dict(algo_kw or {})
    state = None; out = []; prev_best = None
    for e, (inst, info) in enumerate(seq):
        obj = Objective(inst); B = budget0 if e == 0 else budget
        n, m = inst.n, inst.m
        c_e = decoherence_c if (e == 0 or not decoherence_by_event) else decoherence_by_event.get(info["type"], decoherence_c)
        if mig_lambda is not None and e > 0:
            ref, forced_ = map_to_new_vms(prev_best, info)
            elig = ~forced_
            if info["type"] == "churn": elig[info["idx"]] = False
            obj = Objective(inst, kind="makespan_migration", ref=ref, mig_mask=elig, lam=mig_lambda)
        init = None
        if e > 0 and strategy != "restart":
            if algo in ("QI-MRFO", "QI-DMO"):
                init = adapt_register_state(state, info, mode, rng, struct=(strategy != "continue"))
                if strategy == "shock": init = shock_state(init, gamma_shock, mode)
                # carry_elite: True = always; "except_vm_add" (V5, H11) = event-aware, no elite after a VM addition, where
                # the carried schedule leaves the new VM empty and anchors the swarm away from it (H6b, H10a)
                use_elite = carry_elite is True or (carry_elite == "except_vm_add" and info["type"] != "vm_add")
                if carry_elite and algo != "QI-MRFO": raise ValueError("carry_elite is implemented for QI-MRFO only")
                if use_elite:
                    init = dict(init); init["elite"] = repair_schedule(prev_best, info, inst, rng, repair)
            elif algo in ("MRFO", "DMO", "PSO"):
                init = adapt_position_state(state, info, m, rng)
            elif algo in ("GA", "(1+1)-EA"):                # the (1+1)-EA carries its single schedule like a GA of size 1
                init = adapt_ga_state(state, info, m, rng, inst=inst, repair=repair)
        if algo in ("Max-Min", "Incremental", "Chooser"):
            if algo == "Max-Min" or e == 0: a = max_min(inst); f = obj(a)
            elif algo == "Incremental": a = incremental_list_schedule(prev_best, info, inst, rng); f = obj(a)
            else:                                   # Chooser: the cheaper of the two heuristics under the actual objective
                cands = [max_min(inst), incremental_list_schedule(prev_best, info, inst, rng)]
                fs = [obj(c) for c in cands]; k = int(np.argmin(fs)); a, f = cands[k], fs[k]
            tr = Tracker(n, m); tr.snapshot(obj.n_evals, [a], [f], f)
            r = {"best_f": f, "best_assign": a, "tracker": tr, "state": None}
        elif algo == "QI-MRFO": r = run_qimrfo(inst, obj, B, P=P, seed=seed * 100 + e, decoherence=c_e / n, mode=mode, init_state=init, track=False, **kw)
        elif algo == "QI-DMO": r = run_qidmo(inst, obj, B, P=P, seed=seed * 100 + e, decoherence=0.25 / n, mode=mode, init_state=init, track=False, **kw)
        elif algo == "MRFO": r = run_mrfo(inst, obj, B, P=P, seed=seed * 100 + e, init_state=init, track=False, **kw)
        elif algo == "DMO": r = run_dmo(inst, obj, B, P=P, seed=seed * 100 + e, init_state=init, track=False, **kw)
        elif algo == "PSO": r = run_pso(inst, obj, B, P=P, seed=seed * 100 + e, init_state=init, track=False, **kw)
        elif algo == "GA": r = run_ga(inst, obj, B, P=P, seed=seed * 100 + e, init_state=init, track=False, hypermutation=(0.2 if strategy == "hypermut" else 0.0), **kw)
        elif algo == "(1+1)-EA": r = run_one_plus_one(inst, obj, B, seed=seed * 100 + e, decoherence=c_e / n, init_state=init, track=False, **kw)
        else: raise ValueError(algo)
        state = r["state"]; tr = r["tracker"]
        lb = inst.lower_bound(); mm = obj._raw(max_min(inst))[0]
        ev = np.array(tr.evals, float); bs = np.array(tr.best, float)
        auc = float((getattr(np, 'trapezoid', None) or np.trapz)((bs - lb) / lb, ev) / max(1e-9, ev[-1] - ev[0])) if len(ev) > 1 else float((bs[-1] - lb) / lb)
        vol, forced, persist = count_migrations(prev_best, r["best_assign"], info) if e > 0 else (0, 0, n)
        ms_dep = float(r["best_f"]) if obj.kind == "makespan" else float(Objective(inst)._raw(r["best_assign"])[0])
        out.append({"epoch": e, "best": ms_dep, "lb": lb, "maxmin": mm, "gap": (ms_dep - lb) / lb, "auc_gap": auc, "m": m,
                    "type": None if info is None else info["type"], "migrations": vol, "forced": forced, "persist": persist,
                    "evals": obj.n_evals, "assign": np.asarray(r["best_assign"]).copy(),
                    "cost": float(r["best_f"]), "cost_gap": (float(r["best_f"]) - lb) / lb})
        prev_best = np.asarray(r["best_assign"]).copy()
    return out
