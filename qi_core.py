"""
qi_core.py - cloud-scheduling problem + classical optimizers + instrumentation (pure NumPy).
The '# %% S<k>' markers slice this file into notebook sections.
"""
# %% S2 imports
import numpy as np, time, hashlib
from dataclasses import dataclass, field

# %% S4 problem representation
@dataclass
class CloudInstance:
    """Independent tasks (cloudlets) on heterogeneous VMs: the standard CloudSim-style model."""
    task_len: np.ndarray      # MI per task
    vm_mips: np.ndarray       # MIPS per VM
    vm_p_idle: np.ndarray     # W
    vm_p_max: np.ndarray      # W
    name: str = ""
    et: np.ndarray = field(init=False)   # execution-time matrix n x m: et[i, j] = task_len[i] / vm_mips[j]
    def __post_init__(self):
        self.et = self.task_len[:, None] / self.vm_mips[None, :]
    @property
    def n(self): return len(self.task_len)
    @property
    def m(self): return len(self.vm_mips)
    def lower_bound(self):
        # Q||Cmax lower bound: max(total work / total speed, largest task on fastest VM)
        return max(self.task_len.sum() / self.vm_mips.sum(), self.task_len.max() / self.vm_mips.max())
    def lower_bound_pmtn(self):
        """Tighter valid bound: the optimal PREEMPTIVE makespan Q|pmtn|Cmax (Liu & Yang 1974; Horvath, Lam & Sethi 1977;
        Gonzalez & Sahni 1978) = max( max_{k<K} P_k / S_k , P_n / S_K ), K = min(n, m), P_k = sum of the k largest task
        lengths, S_k = sum of the k fastest speeds. Always >= lower_bound(); used for the V5 'gap2' columns."""
        P = np.cumsum(np.sort(self.task_len)[::-1]); S = np.cumsum(np.sort(self.vm_mips)[::-1]); K = min(self.n, self.m)
        prefix = (P[:K - 1] / S[:K - 1]).max() if K > 1 else 0.0
        return max(prefix, P[-1] / S[K - 1])
    def copy_with(self, task_len=None, vm_mips=None, vm_p_idle=None, vm_p_max=None, name=None):
        return CloudInstance(self.task_len if task_len is None else task_len, self.vm_mips if vm_mips is None else vm_mips,
                             self.vm_p_idle if vm_p_idle is None else vm_p_idle, self.vm_p_max if vm_p_max is None else vm_p_max,
                             name or self.name)

def decode(x, m):
    """continuous position in [0, m) -> integer VM index (floor encoding used by most swarm schedulers)"""
    return np.clip(np.floor(x), 0, m - 1).astype(int)

# %% S5 instance generation
def sample_task_lengths(rng, n_tasks, task_dist):
    if task_dist == "uniform":
        return rng.uniform(1000, 10000, n_tasks)
    if task_dist == "lognormal":
        return rng.lognormal(np.log(3000), 1.0, n_tasks)
    if task_dist == "bimodal":          # 80% small, 20% big (heavy tail typical of cloud traces)
        big = rng.random(n_tasks) < 0.2
        return np.where(big, rng.uniform(20000, 40000, n_tasks), rng.uniform(500, 3000, n_tasks))
    if task_dist == "identical":
        return np.full(n_tasks, 5000.0)
    raise ValueError(task_dist)

def sample_vm_speeds(rng, n_vms, hetero):
    if hetero == "high":
        return rng.choice([250, 500, 1000, 1500, 2000], n_vms).astype(float) + rng.uniform(-50, 50, n_vms)
    if hetero == "low":
        return rng.uniform(900, 1100, n_vms)
    if hetero == "none":
        return np.full(n_vms, 1000.0)
    raise ValueError(hetero)

def make_instance(n_tasks, n_vms, seed, task_dist="uniform", hetero="high", name=None):
    rng = np.random.default_rng(seed)
    L = sample_task_lengths(rng, n_tasks, task_dist)
    S = sample_vm_speeds(rng, n_vms, hetero)
    p_max = 100.0 + 0.1 * S             # W, grows with speed
    p_idle = 0.6 * p_max
    return CloudInstance(L, S, p_idle, p_max, name or f"n{n_tasks}_m{n_vms}_{task_dist}_{hetero}_s{seed}")

# %% S6 objective
class Objective:
    """Evaluate integer assignment vectors (task -> VM). Counts evaluations (the budget unit for every optimizer).
    kind='makespan_migration' (V5, H8): makespan x (1 + lam * voluntary migrations / eligible tasks), where a migration is
    an eligible task (mig_mask: persistent, VM survived) assigned differently from the deployed reference schedule `ref`."""
    def __init__(self, inst: CloudInstance, kind="makespan", w_energy=0.3, ref=None, mig_mask=None, lam=0.0):
        self.inst, self.kind, self.w_energy = inst, kind, w_energy
        if kind == "makespan_migration":
            self.ref = np.asarray(ref); self.mig_mask = np.asarray(mig_mask, bool); self.lam = float(lam)
            self.n_eligible = max(1, int(self.mig_mask.sum()))
        self.n_evals = 0
        self._ar = np.arange(inst.n)
        rr = self._ar % inst.m                      # round-robin reference schedule for scaling
        self.ms_ref, self.e_ref = self._raw(rr)
    def _raw(self, assign):
        et_sel = self.inst.et[self._ar, assign]
        loads = np.bincount(assign, weights=et_sel, minlength=self.inst.m)
        ms = loads.max()
        energy = (self.inst.vm_p_idle * ms + (self.inst.vm_p_max - self.inst.vm_p_idle) * loads).sum() / 3600.0  # Wh
        return ms, energy
    def __call__(self, assign):
        self.n_evals += 1
        ms, en = self._raw(assign)
        if self.kind == "makespan":
            return ms
        if self.kind == "makespan_energy":
            return (1 - self.w_energy) * ms / self.ms_ref + self.w_energy * en / self.e_ref
        if self.kind == "makespan_migration":
            return ms * (1.0 + self.lam * self.migrations(assign) / self.n_eligible)
        raise ValueError(self.kind)
    def migrations(self, assign):
        return int(((np.asarray(assign) != self.ref) & self.mig_mask).sum())
    def details(self, assign):
        ms, en = self._raw(assign)
        d = {"makespan": ms, "energy_Wh": en}
        if self.kind == "makespan_migration": d["migrations"] = self.migrations(assign)
        return d

# %% S7a instrumentation
class Tracker:
    """Records per-iteration statistics common to all optimizers (used to test the MECHANISM, not just the score).
    With `inst` given (V5), two extra diagnostics are recorded per candidate: whether the schedule was ever evaluated
    before in the run (global duplicate; 'wasted' only counts parent-identical candidates) and whether the candidate
    moves a task off its reference schedule's critical VM (a necessary condition for a strict makespan improvement).
    They only read the candidates, so the optimizers' behaviour is unchanged."""
    def __init__(self, n, m, inst=None):
        self.n, self.m = n, m
        self.evals, self.best, self.mean, self.div_ham = [], [], [], []
        self.wasted = self.neutral = self.improving = self.worse = 0
        self.move_sizes = []
        self.gb_improvements = 0
        self.dup_global = self.touch_crit = self.x_cands = self.x_improving = 0
        self._et = None if inst is None else inst.et
        self._seen = set(); self._ar = np.arange(n)
        self.flags = []            # per candidate: 1 = improving, 0 = not (used for late-run improvement rates)
        self.t0 = time.time()
    def candidate(self, parent_assign, child_assign, f_parent, f_child):
        diff = parent_assign != child_assign
        changed = int(diff.sum())
        self.move_sizes.append(changed)
        if changed == 0: self.wasted += 1
        elif f_child < f_parent - 1e-12: self.improving += 1
        elif abs(f_child - f_parent) <= 1e-12: self.neutral += 1
        else: self.worse += 1
        if self._et is not None:
            self.flags.append(int(changed > 0 and f_child < f_parent - 1e-12))
            self._seen.add(hashlib.blake2b(parent_assign.tobytes(), digest_size=8).digest())
            key = hashlib.blake2b(child_assign.tobytes(), digest_size=8).digest()   # deterministic (no PYTHONHASHSEED salt)
            if key in self._seen: self.dup_global += 1
            else: self._seen.add(key)
            loads = np.bincount(parent_assign, weights=self._et[self._ar, parent_assign], minlength=self.m)
            crit = loads >= loads.max() * (1 - 1e-12)
            self.touch_crit += int((diff & crit[parent_assign]).any())
    def snapshot(self, n_evals, assigns, fits, best):
        self.evals.append(n_evals); self.best.append(best); self.mean.append(float(np.mean(fits)))
        A = np.asarray(assigns); P = len(A)
        if P > 1:
            ham = 0.0
            for i in range(P - 1):
                ham += (A[i + 1:] != A[i]).sum()
            self.div_ham.append(ham / (P * (P - 1) / 2) / self.n)
        else:
            self.div_ham.append(0.0)
    def summary(self):
        tot = max(1, self.wasted + self.neutral + self.improving + self.worse)
        return {"wasted_frac": self.wasted / tot, "neutral_frac": self.neutral / tot,
                "improving_frac": self.improving / tot, "worse_frac": self.worse / tot,
                "mean_move_size": float(np.mean(self.move_sizes)) if self.move_sizes else 0.0,
                "gb_impr_per_1k": 1000.0 * self.gb_improvements / max(1, self.evals[-1] if self.evals else 1),
                "runtime_s": time.time() - self.t0}
    def summary_v5(self):
        """V5 diagnostics (needs Tracker(..., inst)): global duplicates, critical-VM touches, exchange-move counts,
        late-half improvement rate and the budget fraction at which the global best last improved."""
        tot = max(1, len(self.move_sizes))
        ev, bs = np.asarray(self.evals, float), np.asarray(self.best, float)
        drops = np.where(np.diff(bs) < 0)[0]
        last = ev[drops[-1] + 1] / ev[-1] if len(drops) and ev[-1] > 0 else 0.0
        fl = np.asarray(self.flags)
        return {"dup_global_frac": self.dup_global / tot, "touch_crit_frac": self.touch_crit / tot,
                "x_frac": self.x_cands / tot, "x_success": self.x_improving / max(1, self.x_cands),
                "late_improving_frac": float(fl[len(fl) // 2:].mean()) if len(fl) > 1 else 0.0,
                "last_gb_impr_frac": float(last)}

# %% S7b heuristics
def _list_schedule(inst, pick):
    n, m = inst.n, inst.m
    ready = np.zeros(m); assign = -np.ones(n, int); left = set(range(n))
    while left:
        idx = np.array(sorted(left))
        ct = inst.et[idx] + ready[None, :]
        best_vm = ct.argmin(1); best_ct = ct[np.arange(len(idx)), best_vm]
        k = pick(best_ct); t = idx[k]; v = best_vm[k]
        assign[t] = v; ready[v] = best_ct[k]; left.remove(t)
    return assign

def min_min(inst): return _list_schedule(inst, np.argmin)
def max_min(inst): return _list_schedule(inst, np.argmax)

def local_search_1move(inst, assign, max_steps=10000):
    """Best-improvement hill climbing: move one task off the bottleneck VM."""
    a = assign.copy(); ar = np.arange(inst.n)
    for _ in range(max_steps):
        loads = np.bincount(a, weights=inst.et[ar, a], minlength=inst.m)
        ms = loads.max(); b = loads.argmax()
        best = (ms, None)
        for t in np.where(a == b)[0]:
            for v in range(inst.m):
                if v == b: continue
                new_b = ms - inst.et[t, b]; new_v = loads[v] + inst.et[t, v]
                others = np.delete(loads, [b, v]).max() if inst.m > 2 else -np.inf
                new_ms = max(new_b, new_v, others)
                if new_ms < best[0] - 1e-9: best = (new_ms, (t, v))
        if best[1] is None: return a
        t, v = best[1]; a[t] = v
    return a

def critical_exchange(inst, a, rng):
    """V5 critical exchange move (CXM). t is drawn uniformly from the tasks on the critical VM(s) of schedule a;
    u uniformly from the tasks on other VMs that are SHORTER than t (necessary for the exchange to lower the critical
    load); t and u swap VMs. If no shorter task exists elsewhere, t is relocated to a uniformly random other VM.
    Returns (new_a, t, u), u = -1 for a relocation. Shared by QI-MRFO and the GA so that both get the identical operator."""
    n, m = inst.n, inst.m
    new = a.copy()
    if m < 2: return new, -1, -1
    loads = np.bincount(a, weights=inst.et[np.arange(n), a], minlength=m)
    crit = loads >= loads.max() * (1 - 1e-12)
    T = np.flatnonzero(crit[a])
    t = T[rng.integers(len(T))]; b = a[t]
    U = np.flatnonzero((a != b) & (inst.task_len < inst.task_len[t]))
    if len(U):
        u = U[rng.integers(len(U))]
        new[t], new[u] = a[u], b
        return new, t, u
    v = rng.integers(m - 1); v += int(v >= b)
    new[t] = v
    return new, t, -1

def count_improving_moves(inst, a, eps=1e-9):
    """Landscape diagnostic at schedule a: number of STRICTLY makespan-improving (i) relocations of a critical task and
    (ii) swaps of a critical task with a task on another VM. With several VMs tied at the makespan no single move can
    improve it: returns (0, 0, n_tied). Vectorised version of observe_v5_localopt.improving_moves."""
    n, m, et = inst.n, inst.m, inst.et
    L = np.bincount(a, weights=et[np.arange(n), a], minlength=m); ms = L.max()
    tied = int((L >= ms * (1 - 1e-12)).sum())
    if tied > 1 or m < 2: return 0, 0, tied
    b = int(L.argmax()); Tb = np.flatnonzero(a == b); Ub = np.flatnonzero(a != b)
    rest = np.full(m, -np.inf)                                   # rest[v] = max load over VMs other than b and v
    for v in range(m):
        if v != b:
            mask = np.ones(m, bool); mask[[b, v]] = False
            rest[v] = L[mask].max() if mask.any() else -np.inf
    V = np.delete(np.arange(m), b)
    rel_new = np.maximum(np.maximum((ms - et[Tb, b])[:, None], L[V][None, :] + et[np.ix_(Tb, V)]), rest[V][None, :])
    n_rel = int((rel_new < ms - eps).sum())
    vu = a[Ub]
    nb = ms - et[Tb, b][:, None] + et[Ub, b][None, :]
    nv = (L[vu] - et[Ub, vu])[None, :] + et[np.ix_(Tb, np.arange(m))][:, vu]
    n_swap = int((np.maximum(np.maximum(nb, nv), rest[vu][None, :]) < ms - eps).sum())
    return n_rel, n_swap, 1

# %% S7c classical optimizers
# All optimizers share the signature (inst, obj, budget, P, seed, ...) and return a dict with best_f, best_assign,
# tracker and a 'state' that can be passed back as init_state for warm-started (dynamic) re-optimization.
def _init_pop(rng, P, n, m):
    return rng.uniform(0, m, (P, n))

def run_pso(inst, obj, budget, P=30, seed=0, w=0.729, c1=1.49445, c2=1.49445, track=True, init_state=None):
    """Standard inertia-weight PSO (Clerc constriction values), floor decoder."""
    rng = np.random.default_rng(seed); n, m = inst.n, inst.m
    tr = Tracker(n, m, inst)
    if init_state is None:
        X = _init_pop(rng, P, n, m); V = rng.uniform(-1, 1, (P, n))
    else:
        X = np.clip(init_state["X"].copy(), 0, m - 1e-9); V = init_state["V"].copy()
    A = decode(X, m); F = np.array([obj(a) for a in A])
    pb, pbF, pbA = X.copy(), F.copy(), A.copy()
    g = pbF.argmin(); gb, gbF, gbA = pb[g].copy(), pbF[g], pbA[g].copy()
    vmax = m / 2
    tr.snapshot(obj.n_evals, A, F, gbF)
    while obj.n_evals + P <= budget:
        r1, r2 = rng.random((P, n)), rng.random((P, n))
        V = np.clip(w * V + c1 * r1 * (pb - X) + c2 * r2 * (gb - X), -vmax, vmax)
        X = np.clip(X + V, 0, m - 1e-9)
        A_new = decode(X, m)
        for i in range(P):
            f = obj(A_new[i])
            if track: tr.candidate(pbA[i], A_new[i], pbF[i], f)
            if f < pbF[i]:
                pb[i], pbF[i], pbA[i] = X[i].copy(), f, A_new[i].copy()
                if f < gbF: gb, gbF, gbA = X[i].copy(), f, A_new[i].copy(); tr.gb_improvements += 1
        tr.snapshot(obj.n_evals, pbA, pbF, gbF)
    return {"best_f": gbF, "best_assign": gbA, "tracker": tr, "state": {"X": X, "V": V}}

def run_dmo(inst, obj, budget, P=30, seed=0, n_baby_sitter=3, peep=2.0, track=True, greedy_next=False, init_state=None):
    """Dwarf Mongoose Optimization, faithful to the authors' MATLAB code as reproduced in MEALPY OriginalDMOA.
    greedy_next=True replaces the unconditional 'next mongoose position' move by a greedy one (MEALPY DevDMOA style)."""
    rng = np.random.default_rng(seed); n, m = inst.n, inst.m
    tr = Tracker(n, m, inst)
    X = _init_pop(rng, P, n, m) if init_state is None else np.clip(init_state["X"].copy(), 0, m - 1e-9)
    A = decode(X, m); F = np.array([obj(a) for a in A])
    C = np.zeros(P); tau = -np.inf; L = np.round(0.6 * n * n_baby_sitter)
    g = F.argmin(); gbF, gbA = F[g], A[g].copy()
    max_iter = max(1, (budget - P) // (3 * P))
    tr.snapshot(obj.n_evals, A, F, gbF)
    def clip(x): return np.clip(x, 0, m - 1e-9)
    for it in range(1, max_iter + 1):
        if obj.n_evals + 3 * P + n_baby_sitter > budget: break         # never exceed the evaluation budget
        CF = (1.0 - it / max_iter) ** (2.0 * it / max_iter)
        fi = np.exp(-F / F.mean()); prob = fi / fi.sum()
        for i in range(P):                                             # alpha-group foraging
            alpha = rng.choice(P, p=prob)
            k = rng.choice([k for k in range(P) if k not in (i, alpha)])
            phi = (peep / 2) * rng.uniform(-1, 1, n)
            new = clip(X[alpha] + phi * (X[alpha] - X[k]))
            a_new = decode(new, m); f = obj(a_new)
            if track: tr.candidate(A[i], a_new, F[i], f)
            if f < F[i]: X[i], A[i], F[i] = new, a_new, f
            else: C[i] += 1
            if f < gbF: gbF, gbA = f, a_new.copy(); tr.gb_improvements += 1
        SM = np.zeros(P)
        for i in range(P):                                             # scout group + sleeping mound
            k = rng.choice([k for k in range(P) if k != i])
            phi = (peep / 2) * rng.uniform(-1, 1, n)
            new = clip(X[i] + phi * (X[i] - X[k]))
            a_new = decode(new, m); f = obj(a_new)
            if track: tr.candidate(A[i], a_new, F[i], f)
            SM[i] = (f - F[i]) / max(f, F[i])
            if f < F[i]: X[i], A[i], F[i] = new, a_new, f
            else: C[i] += 1
            if f < gbF: gbF, gbA = f, a_new.copy(); tr.gb_improvements += 1
        for i in range(n_baby_sitter):                                 # babysitter exchange
            if C[i] >= L:
                X[i] = rng.uniform(0, m, n); A[i] = decode(X[i], m); F[i] = obj(A[i]); C[i] = 0
                if F[i] < gbF: gbF, gbA = F[i], A[i].copy(); tr.gb_improvements += 1
        new_tau = SM.mean()
        for i in range(P):                                             # next mongoose position
            phi = (peep / 2) * rng.uniform(-1, 1, n)
            if new_tau > tau: new = X[i] - CF * phi * rng.random() * (X[i] - SM[i])
            else:             new = X[i] + CF * phi * rng.random() * (X[i] - SM[i])
            tau = new_tau
            new = clip(new); a_new = decode(new, m); f = obj(a_new)
            if track: tr.candidate(A[i], a_new, F[i], f)
            if (not greedy_next) or f < F[i]: X[i], A[i], F[i] = new, a_new, f
            if f < gbF: gbF, gbA = f, a_new.copy(); tr.gb_improvements += 1
        tr.snapshot(obj.n_evals, A, F, gbF)
    return {"best_f": gbF, "best_assign": gbA, "tracker": tr, "state": {"X": X}}

def run_mrfo(inst, obj, budget, P=30, seed=0, S=2.0, track=True, init_state=None):
    """Manta Ray Foraging Optimization, faithful to Zhao et al. 2020 as implemented in MEALPY OriginalMRFO."""
    rng = np.random.default_rng(seed); n, m = inst.n, inst.m
    tr = Tracker(n, m, inst)
    X = _init_pop(rng, P, n, m) if init_state is None else np.clip(init_state["X"].copy(), 0, m - 1e-9)
    A = decode(X, m); F = np.array([obj(a) for a in A])
    g = F.argmin(); gb, gbF, gbA = X[g].copy(), F[g], A[g].copy()
    T = max(1, (budget - P) // (2 * P))
    tr.snapshot(obj.n_evals, A, F, gbF)
    def clip(x): return np.clip(x, 0, m - 1e-9)
    for t in range(1, T + 1):
        for i in range(P):
            if rng.random() < 0.5:                       # cyclone foraging
                r1 = rng.random()
                beta = 2 * np.exp(r1 * (T - t) / T) * np.sin(2 * np.pi * r1)
                if (t + 1) / T < rng.random():           # exploration around a random reference
                    xr = rng.uniform(0, m, n)
                    if i == 0: new = xr + rng.random() * (xr - X[i]) + beta * (xr - X[i])
                    else:      new = xr + rng.random() * (X[i - 1] - X[i]) + beta * (xr - X[i])
                else:
                    if i == 0: new = gb + rng.random() * (gb - X[i]) + beta * (gb - X[i])
                    else:      new = gb + rng.random() * (X[i - 1] - X[i]) + beta * (gb - X[i])
            else:                                        # chain foraging
                r = rng.random(); alpha = 2 * r * np.sqrt(np.abs(np.log(r)))
                if i == 0: new = X[i] + r * (gb - X[i]) + alpha * (gb - X[i])
                else:      new = X[i] + r * (X[i - 1] - X[i]) + alpha * (gb - X[i])
            new = clip(new); a_new = decode(new, m); f = obj(a_new)
            if track: tr.candidate(A[i], a_new, F[i], f)
            if f < F[i]: X[i], A[i], F[i] = new, a_new, f
            if f < gbF: gb, gbF, gbA = new.copy(), f, a_new.copy(); tr.gb_improvements += 1
        for i in range(P):                               # somersault foraging
            new = clip(X[i] + S * (rng.random() * gb - rng.random() * X[i]))
            a_new = decode(new, m); f = obj(a_new)
            if track: tr.candidate(A[i], a_new, F[i], f)
            if f < F[i]: X[i], A[i], F[i] = new, a_new, f
            if f < gbF: gb, gbF, gbA = new.copy(), f, a_new.copy(); tr.gb_improvements += 1
        tr.snapshot(obj.n_evals, A, F, gbF)
    return {"best_f": gbF, "best_assign": gbA, "tracker": tr, "state": {"X": X}}

def run_ga(inst, obj, budget, P=30, seed=0, pm=None, track=True, init_state=None, hypermutation=0.0, exchange=0.0, seed_assign=None):
    """Discrete GA baseline: tournament(2), uniform crossover, per-gene reassignment mutation, 1-elitism.
    hypermutation>0: mutation rate x10 during the first `hypermutation` fraction of the budget (Cobb-style).
    exchange>0 (V5 control for H5): each child additionally undergoes the critical exchange move with this probability."""
    rng = np.random.default_rng(seed); n, m = inst.n, inst.m
    pm = pm or 1.0 / n
    tr = Tracker(n, m, inst)
    A = rng.integers(0, m, (P, n)) if init_state is None else np.clip(init_state["A"].copy(), 0, m - 1)
    if seed_assign is not None: A[0] = seed_assign             # V5 (H7): heuristic seeding of one individual
    F = np.array([obj(a) for a in A])
    g = F.argmin(); gbF, gbA = F[g], A[g].copy()
    start = obj.n_evals
    tr.snapshot(obj.n_evals, A, F, gbF)
    while obj.n_evals + P <= budget:
        rate = pm * 10 if (obj.n_evals - start) < hypermutation * (budget - start) else pm
        newA = np.empty_like(A); newF = np.empty_like(F)
        e = F.argmin(); newA[0], newF[0] = A[e], F[e]
        for c in range(1, P):
            i1, j1 = rng.integers(0, P, 2); p1 = i1 if F[i1] <= F[j1] else j1
            i2, j2 = rng.integers(0, P, 2); p2 = i2 if F[i2] <= F[j2] else j2
            child = np.where(rng.random(n) < 0.5, A[p1], A[p2])
            mut = rng.random(n) < rate
            child[mut] = rng.integers(0, m, mut.sum())
            xm = exchange > 0 and rng.random() < exchange
            if xm: child = critical_exchange(inst, child, rng)[0]
            f = obj(child)
            if track:
                tr.candidate(A[p1], child, F[p1], f)
                if xm: tr.x_cands += 1; tr.x_improving += int(f < F[p1] - 1e-12)
            newA[c], newF[c] = child, f
            if f < gbF: gbF, gbA = f, child.copy(); tr.gb_improvements += 1
        A, F = newA, newF
        tr.snapshot(obj.n_evals, A, F, gbF)
    return {"best_f": gbF, "best_assign": gbA, "tracker": tr, "state": {"A": A}}

def run_one_plus_one(inst, obj, budget, P=1, seed=0, decoherence=0.0, exchange=0.0, track=True, init_state=None, seed_assign=None):
    """V5 minimal classical control for H7: a (1+1)-EA whose mutation is exactly what a fully collapsed QI-MRFO+CXM
    register set produces. Each task is re-drawn uniformly over the VMs with probability `decoherence` (the depolarising
    floor acting on a basis state), then the critical exchange is applied with probability `exchange`. Strict
    acceptance, one evaluation per candidate. `seed_assign` / init_state['A'] give the start schedule (default: uniform
    random). P is ignored (kept for the common signature)."""
    rng = np.random.default_rng(seed); n, m = inst.n, inst.m
    tr = Tracker(n, m, inst)
    if seed_assign is not None: a = np.asarray(seed_assign).copy()
    elif init_state is not None and "A" in init_state: a = np.asarray(init_state["A"])[0].copy()
    else: a = rng.integers(0, m, n)
    f = obj(a)
    tr.snapshot(obj.n_evals, [a], [f], f)
    while obj.n_evals + 1 <= budget:
        child = a.copy()
        if decoherence > 0:
            mut = rng.random(n) < decoherence
            child[mut] = rng.integers(0, m, mut.sum())
        xm = exchange > 0 and rng.random() < exchange
        if xm: child = critical_exchange(inst, child, rng)[0]
        fc = obj(child)
        if track:
            tr.candidate(a, child, f, fc)
            if xm: tr.x_cands += 1; tr.x_improving += int(fc < f - 1e-12)
        if fc < f: a, f = child, fc; tr.gb_improvements += 1
        if obj.n_evals % 60 == 0: tr.snapshot(obj.n_evals, [a], [f], f)
    tr.snapshot(obj.n_evals, [a], [f], f)
    return {"best_f": f, "best_assign": a, "tracker": tr, "state": {"A": a[None, :]}}

def run_random(inst, obj, budget, seed=0, P=30, track=True, init_state=None):
    rng = np.random.default_rng(seed); n, m = inst.n, inst.m
    tr = Tracker(n, m, inst); gbF, gbA = np.inf, None
    while obj.n_evals + P <= budget:
        A = rng.integers(0, m, (P, n)); F = np.array([obj(a) for a in A])
        g = F.argmin()
        if F[g] < gbF: gbF, gbA = F[g], A[g].copy(); tr.gb_improvements += 1
        tr.snapshot(obj.n_evals, A, F, gbF)
    return {"best_f": gbF, "best_assign": gbA, "tracker": tr, "state": {}}

ALGOS = {"PSO": run_pso, "DMO": run_dmo, "MRFO": run_mrfo, "GA": run_ga, "Random": run_random, "(1+1)-EA": run_one_plus_one}
