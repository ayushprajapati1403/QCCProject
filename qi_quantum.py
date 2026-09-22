"""
qi_quantum.py - SECTION 8/9: the quantum-inspired mechanism, QI-DMO and (transfer test) QI-MRFO.

Representation: each individual holds an amplitude matrix Psi in R^{n x m} (one register per task), rows
normalised so that sum_j Psi[t,j]^2 = 1.  Born rule: P(task t -> VM j) = Psi[t,j]^2.
Measurement collapses the register set to an integer schedule a (one objective evaluation).
The host algorithm's update equations are applied UNCHANGED to the amplitude matrices; attractors are the
basis states E(b) of measured schedules; decoherence = depolarising channel p <- (1-gamma) p + gamma/m.
Modes: 'born_signed' (signed amplitudes, Born rule), 'born_abs' (non-negative amplitudes, Born rule),
       'linear' (classical twin: probability vectors with linear mixing).
"""
import numpy as np
from qi_core import Tracker, critical_exchange

# %% S8 mechanism

def born_probs(psi):
    p = psi ** 2
    return p / p.sum(1, keepdims=True)

def renormalise(psi, m):
    nrm = np.sqrt((psi ** 2).sum(1, keepdims=True))
    bad = (nrm[:, 0] < 1e-12)
    psi = psi / np.where(nrm < 1e-12, 1.0, nrm)
    if bad.any():
        psi[bad] = 1.0 / np.sqrt(m)
    return psi

def probs(psi, mode):
    if mode.startswith("born"):
        return born_probs(psi)
    p = np.clip(psi, 0, None); return p / np.maximum(p.sum(1, keepdims=True), 1e-300)

def measure(psi, rng, mode):
    """Sample one schedule from the register set (Born rule or linear probabilities)."""
    p = probs(psi, mode)
    u = rng.random(len(p))
    a = (np.cumsum(p, 1) < u[:, None]).sum(1)
    return np.minimum(a, p.shape[1] - 1)

def basis_state(assign, m):
    E = np.zeros((len(assign), m)); E[np.arange(len(assign)), assign] = 1.0
    return E          # a one-hot row is both a unit amplitude vector and a probability vector

def project(psi, m, mode):
    """Bring an updated register set back to a valid state."""
    if mode == "born_signed":
        return renormalise(psi, m)
    if mode == "born_abs":
        return renormalise(np.abs(psi), m)
    p = np.clip(psi, 0, None); s = p.sum(1, keepdims=True)
    return np.where(s > 1e-12, p / np.where(s > 1e-12, s, 1.0), 1.0 / m)

def purity(psi, mode):
    return (probs(psi, mode) ** 2).sum(1)            # per task; 1 = collapsed, 1/m = uniform

def depolarise(psi, gamma, m, mode):
    """Depolarising channel: p <- (1-gamma) p + gamma/m ; signs kept for signed amplitudes."""
    if gamma <= 0: return psi
    if mode.startswith("born"):
        p2 = (1 - gamma) * born_probs(psi) + gamma / m
        return np.sign(psi + (psi == 0)) * np.sqrt(p2)
    return (1 - gamma) * psi + gamma / m

def uniform_state(n, m, mode):
    return np.full((n, m), 1.0 / np.sqrt(m)) if mode.startswith("born") else np.full((n, m), 1.0 / m)

# --- state transformations used by the dynamic-workload experiments ---------------------------------
def shock_state(state, gamma, mode):
    """Decoherence shock: apply the depolarising channel of strength gamma to every register of every individual."""
    Psi = state["Psi"]; m = Psi.shape[2]
    return {"Psi": np.stack([depolarise(Psi[i], gamma, m, mode) for i in range(len(Psi))])}

def remove_vm_state(state, j, mode):
    """VM j disappears: delete its column (projective measurement onto the surviving VMs) and renormalise."""
    Psi = np.delete(state["Psi"], j, axis=2); m = Psi.shape[2]
    return {"Psi": np.stack([project(Psi[i], m, mode) for i in range(len(Psi))])}

def add_vm_state(state, mode):
    """A new VM appears: give it the amplitude of a uniform share (1/(m+1)) in every register."""
    Psi = state["Psi"]; P, n, m = Psi.shape
    p = np.stack([probs(Psi[i], mode) for i in range(P)]) * (m / (m + 1.0))
    p = np.concatenate([p, np.full((P, n, 1), 1.0 / (m + 1.0))], axis=2)
    if mode.startswith("born"):
        return {"Psi": np.sqrt(p)}
    return {"Psi": p}

def add_tasks_state(state, idx_new, mode):
    """Tasks idx_new were replaced by new arrivals: their registers are reset to the uniform superposition."""
    Psi = state["Psi"].copy(); m = Psi.shape[2]
    Psi[:, idx_new, :] = uniform_state(len(idx_new), m, mode)[None]
    return {"Psi": Psi}

def collapse_rows(psi, rows, outcomes, gamma, m, mode):
    """Measurement back-action (V5): the registers `rows` collapse onto the measured VMs `outcomes`, then pass through the
    same depolarising floor as every candidate register (so a collapsed row keeps purity < 1 when gamma > 0)."""
    psi = psi.copy()
    psi[rows] = depolarise(basis_state(np.asarray(outcomes), m), gamma, m, mode)
    return psi

# %% S9 QI algorithms
# ----------------------------------------------------------------------------------------------
# QI-DMO: DMO dynamics (MATLAB/MEALPY-faithful) on amplitude registers
# ----------------------------------------------------------------------------------------------
def run_qidmo(inst, obj, budget, P=30, seed=0, n_baby_sitter=3, peep=2.0, mode="born_signed",
              gamma_reset=1.0, decoherence=0.0, attractor="basis", greedy_next=False, track=True, init_state=None):
    """decoherence: per-candidate depolarising strength gamma (0 = V1); gamma_reset: babysitter channel strength;
    attractor: 'basis' (alpha peeps its measured schedule) or 'register' (alpha's superposition state)."""
    rng = np.random.default_rng(seed); n, m = inst.n, inst.m
    tr = Tracker(n, m, inst); tr.purity = []
    if init_state is None:
        Psi = np.stack([uniform_state(n, m, mode) for _ in range(P)])
    else:
        Psi = init_state["Psi"].copy(); P = len(Psi)
    A = np.stack([measure(Psi[i], rng, mode) for i in range(P)]); F = np.array([obj(a) for a in A])
    C = np.zeros(P); tau = -np.inf; L = np.round(0.6 * n * n_baby_sitter)
    g = F.argmin(); gbF, gbA = F[g], A[g].copy()
    max_iter = max(1, (budget - obj.n_evals) // (3 * P))
    def snap():
        tr.snapshot(obj.n_evals, A, F, gbF); tr.purity.append(float(np.mean([purity(Psi[i], mode).mean() for i in range(P)])))
    snap()
    dec = lambda psi: depolarise(psi, decoherence, m, mode)
    for it in range(1, max_iter + 1):
        if obj.n_evals + 3 * P + n_baby_sitter > budget: break         # never exceed the evaluation budget
        CF = (1.0 - it / max_iter) ** (2.0 * it / max_iter)
        fi = np.exp(-F / F.mean()); prob = fi / fi.sum()
        # --- alpha-group foraging: candidate = alpha's peep perturbed by mongoose k
        for i in range(P):
            alpha = rng.choice(P, p=prob)
            k = rng.choice([k for k in range(P) if k not in (i, alpha)])
            phi = (peep / 2) * rng.uniform(-1, 1, (n, 1))
            E = basis_state(A[alpha], m) if attractor == "basis" else Psi[alpha]
            new = dec(project(E + phi * (E - Psi[k]), m, mode))
            a_new = measure(new, rng, mode); f = obj(a_new)
            if track: tr.candidate(A[i], a_new, F[i], f)
            if f < F[i]: Psi[i], A[i], F[i] = new, a_new, f
            else: C[i] += 1
            if f < gbF: gbF, gbA = f, a_new.copy(); tr.gb_improvements += 1
        # --- scout group + sleeping mound
        SM = np.zeros(P)
        for i in range(P):
            k = rng.choice([k for k in range(P) if k != i])
            phi = (peep / 2) * rng.uniform(-1, 1, (n, 1))
            new = dec(project(Psi[i] + phi * (Psi[i] - Psi[k]), m, mode))
            a_new = measure(new, rng, mode); f = obj(a_new)
            if track: tr.candidate(A[i], a_new, F[i], f)
            SM[i] = (f - F[i]) / max(f, F[i])
            if f < F[i]: Psi[i], A[i], F[i] = new, a_new, f
            else: C[i] += 1
            if f < gbF: gbF, gbA = f, a_new.copy(); tr.gb_improvements += 1
        # --- babysitter exchange = decoherence channel of strength gamma_reset (1 = full reset, classical DMO)
        for i in range(n_baby_sitter):
            if C[i] >= L:
                Psi[i] = depolarise(Psi[i], gamma_reset, m, mode); A[i] = measure(Psi[i], rng, mode); F[i] = obj(A[i]); C[i] = 0
                if F[i] < gbF: gbF, gbA = F[i], A[i].copy(); tr.gb_improvements += 1
        # --- next mongoose position (unconditional, CF-damped noise, as in the MATLAB code)
        new_tau = SM.mean()
        for i in range(P):
            phi = (peep / 2) * rng.uniform(-1, 1, (n, 1))
            if new_tau > tau: new = Psi[i] - CF * phi * rng.random() * (Psi[i] - SM[i])
            else:             new = Psi[i] + CF * phi * rng.random() * (Psi[i] - SM[i])
            tau = new_tau
            new = dec(project(new, m, mode))
            a_new = measure(new, rng, mode); f = obj(a_new)
            if track: tr.candidate(A[i], a_new, F[i], f)
            if (not greedy_next) or f < F[i]: Psi[i], A[i], F[i] = new, a_new, f
            if f < gbF: gbF, gbA = f, a_new.copy(); tr.gb_improvements += 1
        snap()
    return {"best_f": gbF, "best_assign": gbA, "tracker": tr, "state": {"Psi": Psi}}

# ----------------------------------------------------------------------------------------------
# QI-MRFO: MRFO dynamics (MEALPY-faithful) on amplitude registers (transfer test of the mechanism)
# ----------------------------------------------------------------------------------------------
def run_qimrfo(inst, obj, budget, P=30, seed=0, S=2.0, mode="born_signed", decoherence=0.0, track=True, init_state=None, accept_equal=False,
               exchange=0.0):
    """accept_equal=True also accepts candidates of equal fitness (neutral drift on plateaus; V4 test).
    exchange>0 (V5, hypothesis H5 'critical exchange measurement'): with this probability a measured candidate additionally
    exchanges a task of its critical VM with a shorter task on another VM (qi_core.critical_exchange), a correlated two-register
    outcome that the product-state measurement almost never produces; the pair's registers collapse onto that outcome."""
    rng = np.random.default_rng(seed); n, m = inst.n, inst.m
    tr = Tracker(n, m, inst); tr.purity = []
    if init_state is None:
        Psi = np.stack([uniform_state(n, m, mode) for _ in range(P)])
    else:
        Psi = init_state["Psi"].copy(); P = len(Psi)
    A = np.stack([measure(Psi[i], rng, mode) for i in range(P)]); F = np.array([obj(a) for a in A])
    if init_state is not None and init_state.get("elite") is not None:
        # V5 elite carry-over (dynamic runs): the previous epoch's best schedule, repaired for the change, is evaluated
        # once (charged to the budget) and replaces the worst measured individual as a (depolarised) basis state
        ea = np.asarray(init_state["elite"]); fe = obj(ea); w = int(F.argmax())
        if fe < F[w]: A[w], F[w] = ea, fe; Psi[w] = depolarise(basis_state(ea, m), decoherence, m, mode)
    g = F.argmin(); gbF, gbA = F[g], A[g].copy()
    T = max(1, (budget - obj.n_evals) // (2 * P))
    def snap():
        tr.snapshot(obj.n_evals, A, F, gbF); tr.purity.append(float(np.mean([purity(Psi[i], mode).mean() for i in range(P)])))
    snap()
    dec = lambda psi: depolarise(psi, decoherence, m, mode)
    def xmeasure(new, a_new):
        # H5: correlated exchange on top of the product-state measurement; no extra random draw when exchange == 0
        if exchange <= 0 or rng.random() >= exchange: return new, a_new, False
        a_x, tt, uu = critical_exchange(inst, a_new, rng)
        rows = [tt] if uu < 0 else [tt, uu]
        return collapse_rows(new, rows, a_x[rows], decoherence, m, mode), a_x, True
    def xtrack(xm, f, f_parent):
        if xm: tr.x_cands += 1; tr.x_improving += int(f < f_parent - 1e-12)
    for t in range(1, T + 1):
        Eb = basis_state(gbA, m)
        for i in range(P):
            if rng.random() < 0.5:                       # cyclone foraging
                r1 = rng.random()
                beta = 2 * np.exp(r1 * (T - t) / T) * np.sin(2 * np.pi * r1)
                if (t + 1) / T < rng.random():           # exploration around a random schedule
                    xr = basis_state(rng.integers(0, m, n), m)
                    if i == 0: new = xr + rng.random() * (xr - Psi[i]) + beta * (xr - Psi[i])
                    else:      new = xr + rng.random() * (Psi[i - 1] - Psi[i]) + beta * (xr - Psi[i])
                else:
                    if i == 0: new = Eb + rng.random() * (Eb - Psi[i]) + beta * (Eb - Psi[i])
                    else:      new = Eb + rng.random() * (Psi[i - 1] - Psi[i]) + beta * (Eb - Psi[i])
            else:                                        # chain foraging
                r = rng.random(); alpha = 2 * r * np.sqrt(np.abs(np.log(r)))
                if i == 0: new = Psi[i] + r * (Eb - Psi[i]) + alpha * (Eb - Psi[i])
                else:      new = Psi[i] + r * (Psi[i - 1] - Psi[i]) + alpha * (Eb - Psi[i])
            new = dec(project(new, m, mode)); a_new = measure(new, rng, mode)
            new, a_new, xm = xmeasure(new, a_new)
            f = obj(a_new)
            if track: tr.candidate(A[i], a_new, F[i], f); xtrack(xm, f, F[i])
            if f < F[i] or (accept_equal and f <= F[i]): Psi[i], A[i], F[i] = new, a_new, f
            if f < gbF: gbF, gbA = f, a_new.copy(); Eb = basis_state(gbA, m); tr.gb_improvements += 1
        for i in range(P):                               # somersault foraging
            new = dec(project(Psi[i] + S * (rng.random() * Eb - rng.random() * Psi[i]), m, mode))
            a_new = measure(new, rng, mode)
            new, a_new, xm = xmeasure(new, a_new)
            f = obj(a_new)
            if track: tr.candidate(A[i], a_new, F[i], f); xtrack(xm, f, F[i])
            if f < F[i] or (accept_equal and f <= F[i]): Psi[i], A[i], F[i] = new, a_new, f
            if f < gbF: gbF, gbA = f, a_new.copy(); Eb = basis_state(gbA, m); tr.gb_improvements += 1
        snap()
    return {"best_f": gbF, "best_assign": gbA, "tracker": tr, "state": {"Psi": Psi}}
