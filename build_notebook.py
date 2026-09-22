"""
build_notebook.py - assembles quantum_inspired_cloud_scheduler.ipynb from the tested modules
(qi_core.py, qi_quantum.py, qi_dynamic.py) plus the experiment cells defined here.
Run:  python build_notebook.py
"""
import json, re, uuid, textwrap, os

HERE = os.path.dirname(os.path.abspath(__file__))

def slice_module(path):
    """Split a module on '# %% <tag>' markers -> {tag: code}; the header before the first marker is dropped."""
    txt = open(os.path.join(HERE, path), encoding="utf-8").read()
    parts = re.split(r"^# %% (.+)$", txt, flags=re.M)
    out = {}
    for i in range(1, len(parts), 2):
        out[parts[i].strip()] = parts[i + 1].strip("\n") + "\n"
    return out

core = slice_module("qi_core.py")
quant = slice_module("qi_quantum.py")
dyn = slice_module("qi_dynamic.py")

cells = []
def _cid(text):   # deterministic cell id (position + content), so rebuilding an unchanged notebook is byte-identical
    import hashlib
    return hashlib.sha1(f"{len(cells)}:{text}".encode("utf-8")).hexdigest()[:8]
def md(text): cells.append({"cell_type": "markdown", "id": _cid(text), "metadata": {}, "source": textwrap.dedent(text).strip("\n")})
def code(text): cells.append({"cell_type": "code", "id": _cid(text), "metadata": {}, "execution_count": None, "outputs": [], "source": textwrap.dedent(text).strip("\n")})

# =====================================================================================================
md(r"""
# Quantum-Inspired Manta Ray Foraging Optimization for Cloud Task Scheduling
### An implementation-first research notebook (QI-MRFO, with QI-DMO as a second host)

**Scope.** Quantum-*inspired* classical optimization for cloud computing. Everything runs on an ordinary CPU with NumPy/SciPy.
No quantum hardware, no quantum circuits, no QPU/annealer access is used or required. The "quantum" content is a
mathematical search mechanism: probability-amplitude registers, Born-rule measurement and a depolarising (decoherence) channel.

**Research loop.** OBSERVE the failure mode of the classical optimizer → HYPOTHESIS → MECHANISM → IMPLEMENT → RUN → ABLATE →
ADVERSARIAL TESTS → INTERPRET. All numbers printed by this notebook are produced when it is executed; the accompanying
report only quotes measured numbers and labels anything else UNMEASURED or HYPOTHETICAL.

**Host algorithm choice (Phase 3).** The mechanism is host-agnostic. The pilot experiments (see the report) showed the
identical mechanism applied to MRFO (Zhao, Zhang & Wang 2020) and to DMO (Agushaka, Ezugwu & Abualigah 2022); MRFO is the
primary host because the effect was largest and the literature gap is documented; DMO is kept as a second host to show transfer.

**Runtime modes.** Set the environment variable `QI_MODE` to `smoke` (≈5 min), `fast` (default, ≈30–60 min on 2 cores) or `full`
(30 seeds, several hours) before starting the kernel. On Linux (Colab, Docker) runs are parallelised with `fork`.
""")

# ----------------------------------------------------------------------------------------------------- S1
md(r"""
## SECTION 1 — Environment / setup
Installs the few missing packages (Colab already has them), detects the platform, prints versions.
""")
code(r"""
import sys, os, importlib, subprocess, platform, time
REQUIRED = ["numpy", "scipy", "pandas", "matplotlib"]
missing = [p for p in REQUIRED if importlib.util.find_spec(p) is None]
if missing:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *missing])
IN_COLAB = "google.colab" in sys.modules
import numpy, scipy, pandas, matplotlib
print(f"python {platform.python_version()} | numpy {numpy.__version__} | scipy {scipy.__version__} | pandas {pandas.__version__} | matplotlib {matplotlib.__version__}")
print(f"platform: {platform.system()} {platform.machine()} | cores: {os.cpu_count()} | colab: {IN_COLAB}")
""")

# ----------------------------------------------------------------------------------------------------- S2
md(r"""
## SECTION 2 — Imports and configuration
One configuration dictionary drives every experiment. `QI_MODE` selects the size of the study; nothing else needs editing.
""")
code(core["S2 imports"] + r"""
import json, math, itertools, warnings, pickle, functools
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
warnings.filterwarnings("ignore")

MODE = os.environ.get("QI_MODE", "fast").lower()
_presets = {
    "smoke": dict(seeds=list(range(2)),  budget=6000,  instances=[(30, 5, "uniform", "high"), (50, 10, "bimodal", "high")], dyn_seeds=list(range(2)), dyn_budget0=6000, dyn_budget=2000),
    "fast":  dict(seeds=list(range(3)),  budget=15000, instances=[(30, 5, "uniform", "high"), (50, 10, "bimodal", "high"), (100, 10, "uniform", "high"), (50, 10, "uniform", "none")], dyn_seeds=list(range(2)), dyn_budget0=12000, dyn_budget=4000),
    "full":  dict(seeds=list(range(30)), budget=20000, instances=[(30, 5, "uniform", "high"), (50, 10, "bimodal", "high"), (100, 10, "uniform", "high"), (50, 10, "uniform", "none"), (200, 20, "uniform", "high"), (100, 10, "lognormal", "low"), (60, 8, "bimodal", "none")], dyn_seeds=list(range(10)), dyn_budget0=15000, dyn_budget=4000),
}
CFG = dict(
    P=30,                       # population size for every population optimizer
    gamma_c_mrfo=1.0,           # decoherence strength gamma = c / n for QI-MRFO   (chosen from the pilot sweep, Section 16 re-checks it)
    gamma_c_dmo=0.25,           # decoherence strength gamma = c / n for QI-DMO
    objective="makespan",       # 'makespan' or 'makespan_energy'
    inst_seed=1,                # seed used to generate the benchmark instances
    parallel=True,              # multiprocessing with fork on Linux; silently sequential elsewhere
    results_dir=os.environ.get("QI_RESULTS_DIR", "results"),
    **_presets[MODE],
)
# raw results are immutable: never overwrite the committed files of a mode; a re-run goes to a new sub-directory
if "QI_RESULTS_DIR" not in os.environ and os.path.exists(os.path.join(CFG["results_dir"], f"baseline_{MODE}.csv")):
    CFG["results_dir"] = os.path.join(CFG["results_dir"], f"rerun_{MODE}_{time.strftime('%Y%m%d_%H%M%S')}")
    print("committed results for this mode exist -> writing this run to", CFG["results_dir"])
os.makedirs(CFG["results_dir"], exist_ok=True)
print(f"mode = {MODE}: seeds={len(CFG['seeds'])}, budget={CFG['budget']} evaluations, instances={len(CFG['instances'])}")
""")

# ----------------------------------------------------------------------------------------------------- S3
md(r"""
## SECTION 3 — Random-seed control
Every optimizer receives an explicit `seed` and builds its own `numpy.random.default_rng(seed)`. Instances are generated from
`CFG['inst_seed']`, so instance *k* is identical for every algorithm and every run seed. Re-running the notebook with the same
mode reproduces the same numbers (up to floating-point associativity in NumPy reductions).
""")
code(r"""
GLOBAL_SEED = 2026
np.random.seed(GLOBAL_SEED)          # only affects legacy global calls; all optimizers use per-run Generators
def rng_for(seed): return np.random.default_rng(seed)
assert rng_for(3).random() == rng_for(3).random(), "Generator must be deterministic for a fixed seed"
print("seed control OK")
""")

# ----------------------------------------------------------------------------------------------------- S4
md(r"""
## SECTION 4 — Cloud scheduling problem representation

**Model (CloudSim-style independent-task scheduling).** $n$ tasks (cloudlets) with lengths $L_i$ (million instructions) are
assigned to $m$ heterogeneous VMs with speeds $S_j$ (MIPS). The execution-time matrix is $ET_{ij} = L_i / S_j$.
A schedule is an integer vector $a \in \{0,\dots,m-1\}^n$ (task $i$ runs on VM $a_i$). The load of VM $j$ is
$\mathrm{Load}_j(a) = \sum_{i: a_i = j} ET_{ij}$ and the **makespan** is $C_{\max}(a) = \max_j \mathrm{Load}_j(a)$.

**Lower bound** used to express results as a *gap*: $LB = \max\!\left(\frac{\sum_i L_i}{\sum_j S_j},\ \frac{\max_i L_i}{\max_j S_j}\right)$ (Q||Cmax bound).

**Encodings.**
* Classical swarm schedulers use a *continuous* position $x \in [0,m)^n$ and the floor decoder $a_i = \lfloor x_i \rfloor$ (`decode`). This is the encoding used by the large majority of PSO/DMO/MRFO cloud-scheduling papers.
* The quantum-inspired version (Section 8) replaces the position by an $n \times m$ **amplitude register** whose *measurement* yields $a$.
""")
code(core["S4 problem representation"])

# ----------------------------------------------------------------------------------------------------- S5
md(r"""
## SECTION 5 — Task / VM generation
Task lengths: `uniform` U(1000, 10000) MI; `bimodal` (80 % small U(500, 3000), 20 % large U(20000, 40000) — a heavy tail as in
cloud traces); `lognormal`; `identical`. VM speeds: `high` heterogeneity (250–2000 MIPS as in the CloudSim examples), `low`, or
`none` (homogeneous). A linear power model $P_j(u) = P^{idle}_j + (P^{max}_j - P^{idle}_j)\,u$ with $P^{idle} = 0.6\,P^{max}$ supports the energy objective.
""")
code(core["S5 instance generation"] + r"""
_demo = make_instance(8, 3, seed=CFG["inst_seed"])
print(_demo.name, "| LB =", round(_demo.lower_bound(), 3))
pd.DataFrame(_demo.et, columns=[f"VM{j} ({_demo.vm_mips[j]:.0f} MIPS)" for j in range(_demo.m)], index=[f"task{i} ({_demo.task_len[i]:.0f} MI)" for i in range(_demo.n)]).round(2)
""")

# ----------------------------------------------------------------------------------------------------- S6
md(r"""
## SECTION 6 — Objective function
`Objective(inst, kind)` evaluates an integer schedule and **counts evaluations**: the evaluation count is the budget unit shared by
every optimizer (equal-budget fairness). Two objective kinds:

* `makespan`: $f(a) = C_{\max}(a)$ (primary; the landscape is a max-of-sums with plateaus).
* `makespan_energy`: $f(a) = (1-w)\,\frac{C_{\max}(a)}{C^{ref}_{\max}} + w\,\frac{E(a)}{E^{ref}}$ with
  $E(a) = \sum_j \big[P^{idle}_j\,C_{\max}(a) + (P^{max}_j - P^{idle}_j)\,\mathrm{Load}_j(a)\big]/3600$ Wh
  (VMs draw idle power until the last task finishes); the reference values come from a round-robin schedule. This smoother, additive objective is one of the adversarial cases in Section 17.
""")
code(core["S6 objective"] + r"""
_obj = Objective(_demo)
_a = np.array([0, 1, 2, 0, 1, 2, 0, 1])
print("round-robin makespan:", round(_obj(_a), 3), "| details:", {k: round(v, 3) for k, v in _obj.details(_a).items()}, "| evaluations so far:", _obj.n_evals)
""")

# ----------------------------------------------------------------------------------------------------- S7
md(r"""
## SECTION 7 — Classical PSO / DMO / MRFO implementations (+ GA, random, list heuristics)

All population optimizers use the same floor encoding, the same evaluation budget and the same instrumentation
(`Tracker`: best-so-far curve, population diversity as mean pairwise Hamming distance / $n$, the number of tasks changed by
every candidate ("move size"), and the fraction of candidates that are *wasted* (identical schedule to the parent), *neutral*,
*improving* or *worse*).

### 7.1 MRFO — original equations (Zhao, Zhang & Wang, 2020)
With $r, r_1, r_2, r_3 \sim U(0,1)$, $t$ the iteration, $T$ the iteration budget:

* **Chain foraging** $\;x_i^{t+1} = x_i^t + r\,(x_{i-1}^t - x_i^t) + \alpha\,(x_{best}^t - x_i^t),\quad \alpha = 2r\sqrt{|\log r|}$ (for $i=1$ the predecessor is $x_{best}$).
* **Cyclone foraging** $\;x_i^{t+1} = x_{best} + r\,(x_{i-1}^t - x_i^t) + \beta\,(x_{best} - x_i^t),\quad \beta = 2e^{r_1 (T-t+1)/T}\sin(2\pi r_1)$;
  while $t/T < \mathrm{rand}$ a random position $x_{rand}$ replaces $x_{best}$ (exploration).
* **Somersault foraging** $\;x_i^{t+1} = x_i^t + S\,(r_2\,x_{best} - r_3\,x_i^t),\quad S = 2$.
* Greedy replacement after each phase; per iteration each individual is evaluated twice.

### 7.2 DMO — original equations (Agushaka, Ezugwu & Abualigah, 2022; MATLAB/MEALPY form)
* Alpha selection by roulette on $\phi_i = e^{-f_i/\bar f}$.
* **Alpha group**: candidate $X_{cand} = X_\alpha + \varphi \odot (X_\alpha - X_k)$, $\varphi \sim \tfrac{peep}{2}\,U(-1,1)^n$, accepted if better, else the counter $C_i$ grows.
* **Scouts**: $X_{cand} = X_i + \varphi \odot (X_i - X_k)$; sleeping mound $sm_i = (f_{cand} - f_i)/\max(f_{cand}, f_i)$.
* **Babysitter exchange**: the first $B$ mongooses are re-initialised uniformly when $C_i \ge L = 0.6\,n\,B$.
* **Next position**: $X_i \leftarrow X_i \mp CF\,\varphi\,r\,(X_i - sm_i)$ with $CF = (1 - t/T)^{2t/T}$, sign set by the trend of the average sleeping mound; this move is **unconditional** in the authors' code (kept faithfully; `greedy_next=True` is the MEALPY "developed" variant).

### 7.3 PSO, GA and heuristics
Inertia-weight PSO ($w=0.729$, $c_1=c_2=1.49445$); a discrete GA (tournament-2, uniform crossover, $1/n$ reassignment mutation, elitism) as an independent classical baseline that works natively in the assignment space; random search; Min-Min and Max-Min list-scheduling heuristics; a 1-move hill climber for landscape probes.
""")
code(core["S7a instrumentation"])
code(core["S7b heuristics"])
code(core["S7c classical optimizers"])

# ----------------------------------------------------------------------------------------------------- S8
md(r"""
## SECTION 8 — The quantum-inspired mechanism

### 8.1 Observation that motivates it (measured in the pilot, reproduced in Section 12)
With the floor encoding, a DMO or MRFO move changes about half of all task assignments per candidate (the moves are
proportional to inter-individual distances in $[0,m)^n$, and rounding turns them into random re-draws), while an improving move
on the assignment landscape changes 1–5 tasks. The result is ≤ 2 % improving candidates and performance at or below random
search for $n \ge 50$. The encoding gives the optimizer no controllable notion of **move size**.

### 8.2 Representation: one probability-amplitude register per task
Individual $i$ holds $\Psi_i \in \mathbb{R}^{n \times m}$, one row per task, each row a **unit vector** (an $m$-level generalisation of a real
Q-bit / "rebit"): $\sum_j \Psi_i[t,j]^2 = 1$. The uniform superposition $\Psi = m^{-1/2}\mathbf{1}$ is the initial state.

**Measurement (Born rule).** A schedule is *measured* by sampling every task independently:
$\Pr(a_t = j) = \Psi[t,j]^2$. One measurement = one objective evaluation. A measured schedule $b$ is encoded back as the
**basis state** $E(b)$ (one-hot rows).

**Purity and move size.** The purity of register $t$ is $\pi_t = \sum_j p_{tj}^2 \in [1/m, 1]$. Two independent measurements of the same
register set differ, in expectation, in $\;n - \sum_t \pi_t\;$ tasks. Purity therefore *is* the move-size control that the floor encoding lacks:
concentrated registers make small moves, diffuse registers make large ones, and the host algorithm's own dynamics move purity continuously.

### 8.3 Host dynamics applied unchanged to amplitudes
Every MRFO/DMO equation of Section 7 is applied to the amplitude matrices, followed by row renormalisation
$\Pi(\Psi)[t,:] = \Psi[t,:]/\|\Psi[t,:]\|$ (the projection back onto the state space). **Attractors are basis states**: the best-known schedule enters
the equations as $E(b_{best})$ (MRFO) or the alpha's measured schedule $E(b_\alpha)$ (DMO: "the alpha peeps its food position").
Section 15 shows that using the alpha's superposition instead of its measured schedule destroys the search — collapse-conditioned attraction is essential.

### 8.4 Decoherence: the depolarising channel
After every update the candidate register passes through the depolarising channel
$$\mathcal{D}_\gamma(p) = (1-\gamma)\,p + \gamma\,\tfrac{1}{m}\mathbf{1}, \qquad \Psi \leftarrow \operatorname{sign}(\Psi)\sqrt{\mathcal{D}_\gamma(\Psi^2)} .$$
It bounds purity away from 1: with $\gamma = c/n$ a fully collapsed register keeps an expected $\approx 2c\,(1-1/m)$ random reassignments per measurement,
i.e. a controllable floor on move size ("the environment never lets the swarm fully collapse"). With $\gamma = 1$ it is the classical random reset
(DMO's babysitter exchange); with intermediate $\gamma$ it is **controlled forgetting**, used in Section 17 for dynamic workloads.

### 8.5 What is quantum-inspired, what is its classical equivalent
| Ingredient | Quantum origin | Classical equivalent (the *twin*, `mode='linear'`) |
|---|---|---|
| Amplitude register, Born rule $p = \psi^2$ | measurement postulate | probability vector with linear normalisation |
| Signed amplitudes (can cancel when mixed) | interference | none (probabilities are non-negative) |
| Basis-state attractor | measurement collapse | one-hot probability vector |
| Depolarising channel | decoherence / noise channel | mutation floor / partial re-initialisation (PBIL-style) |
| Column deletion at VM failure | projective measurement | delete + renormalise |

The classical twin keeps everything except the squaring and the signs. Whether the *quantum* part (squaring, sign) matters beyond
the *representational* part (superposition + measurement + decoherence) is exactly what the ablation in Section 15 tests.
This is **not** quantum computing: no qubits are simulated as a joint state, no unitary evolution, no entanglement; the registers are $n$ independent
$m$-dimensional real unit vectors updated by classical arithmetic in $O(nm)$ per candidate.

### 8.6 Complexity
Per candidate: $O(nm)$ arithmetic + one $O(nm)$ measurement (cumulative sums) + one $O(n)$ objective evaluation, versus $O(n)$ for the floor encoding.
Memory: $P\,n\,m$ floats (e.g. $30 \times 100 \times 10 \times 8$ B = 240 kB). Section 17 measures the actual overhead.
""")
code(quant["S8 mechanism"] + r"""
# --- demonstration of the purity / move-size relation and of Born-vs-linear mixing -------------------------------
_rng = np.random.default_rng(0); _m = 10
_cs = [0.0, 0.25, 0.5, 1.0, 2.0, 4.0]
print("expected tasks changed per measurement of a COLLAPSED register set (n=100) after the channel gamma=c/n:")
for c in _cs:
    E = basis_state(_rng.integers(0, _m, 100), _m)
    D = depolarise(E, c / 100, _m, "born_signed")
    print(f"  c={c:4.2f}: purity={purity(D, 'born_signed').mean():.4f}  E[changed tasks]={100 - purity(D, 'born_signed').sum():.2f}")
phi = np.linspace(-1, 1, 9)
print("\nprobability of the attractor's VM after mixing E + phi*(E - U) with a UNIFORM register U (m=10):")
for f in phi:
    e = np.zeros((1, _m)); e[0, 0] = 1
    born = born_probs(renormalise(e + f * (e - np.full((1, _m), 1 / np.sqrt(_m))), _m))[0, 0]
    lin = project(e + f * (e - np.full((1, _m), 1 / _m)), _m, "linear")[0, 0]
    print(f"  phi={f:+.2f}: Born={born:.3f}  linear={lin:.3f}")
""")

# ----------------------------------------------------------------------------------------------------- S9
md(r"""
## SECTION 9 — Quantum-inspired algorithm implementation (QI-MRFO and QI-DMO)

**Modified equations (MRFO → QI-MRFO).** Replace $x_i$ by $\Psi_i$, $x_{best}$ by $E(b_{best})$, $x_{rand}$ by the basis state of a random schedule, and wrap every update as
$\Psi_{cand} = \mathcal{D}_\gamma\big(\Pi(\cdot)\big)$, then *measure* $\Psi_{cand}$ to obtain the candidate schedule that is evaluated and compared greedily:

* chain: $\Psi_{cand} = \mathcal{D}_\gamma\Pi\big[\Psi_i + r(\Psi_{i-1} - \Psi_i) + \alpha(E(b_{best}) - \Psi_i)\big]$
* cyclone: $\Psi_{cand} = \mathcal{D}_\gamma\Pi\big[E(b_{best}) + r(\Psi_{i-1} - \Psi_i) + \beta(E(b_{best}) - \Psi_i)\big]$ (or $E(b_{rand})$ during exploration)
* somersault: $\Psi_{cand} = \mathcal{D}_\gamma\Pi\big[\Psi_i + S(r_2 E(b_{best}) - r_3 \Psi_i)\big]$ — a reflection-like move about the best basis state.

**Modified equations (DMO → QI-DMO).** Alpha group: $\Psi_{cand} = \mathcal{D}_\gamma\Pi[E(b_\alpha) + \varphi \odot (E(b_\alpha) - \Psi_k)]$; scouts:
$\mathcal{D}_\gamma\Pi[\Psi_i + \varphi \odot (\Psi_i - \Psi_k)]$; babysitter exchange: $\Psi_i \leftarrow \mathcal{D}_{\gamma_{reset}}(\Psi_i)$ ($\gamma_{reset}=1$ reproduces the classical reset);
next position: $\mathcal{D}_\gamma\Pi[\Psi_i \mp CF\,\varphi\,r\,(\Psi_i - sm_i)]$ (unconditional, as in the original). $\varphi$ is drawn per task (per row).

**State-transition process.** $(\Psi_i, b_i, f_i) \to$ candidate register $\to$ measurement $\to$ evaluation $\to$ greedy acceptance of $(\Psi_{cand}, a_{cand}, f_{cand})$.
The identity of the host algorithm is untouched: same operators, same control flow, same number of evaluations per iteration.
""")
code(quant["S9 QI algorithms"])

# ----------------------------------------------------------------------------------------------------- S10
md(r"""
## SECTION 10 — Validation tests
Unit tests for the objective, the encodings, the measurement law, the channel, budget accounting and determinism.
""")
code(r"""
def _brute_force_best(inst):
    best = np.inf
    for a in itertools.product(range(inst.m), repeat=inst.n):
        best = min(best, Objective(inst)._raw(np.array(a))[0])
    return best

tests = {}
_t = make_instance(6, 3, seed=5)
# 1. objective vs brute force + lower bound validity
_bf = _brute_force_best(_t); tests["brute_force_optimum >= LB"] = _bf >= _t.lower_bound() - 1e-9
_ga = run_ga(_t, Objective(_t), 3000, P=20, seed=0); tests["GA on 6x3 finds the brute-force optimum"] = abs(_ga["best_f"] - _bf) < 1e-9
# 2. decoder bounds
tests["decode stays in [0, m-1]"] = decode(np.array([-1.0, 0.0, 2.999, 3.0, 99.0]), 3).tolist() == [0, 0, 2, 2, 2]
# 3. measurement follows the Born rule (chi-square goodness of fit on 20000 draws)
_psi = renormalise(np.array([[0.1, 0.5, 0.3, 0.8]]), 4); _p = born_probs(_psi)[0]
_draws = np.array([measure(_psi, np.random.default_rng(k), "born_signed")[0] for k in range(20000)])
_counts = np.bincount(_draws, minlength=4); _chi2, _pv = stats.chisquare(_counts, 20000 * _p)
tests["measurement ~ Born rule (chi2 p>0.001)"] = _pv > 0.001
# 4. channel keeps normalisation and lowers purity monotonically
_E = basis_state(np.array([1, 2, 0]), 4); _pur = [purity(depolarise(_E, g, 4, "born_signed"), "born_signed").mean() for g in [0, 0.1, 0.5, 1.0]]
tests["channel preserves normalisation"] = np.allclose((depolarise(_E, 0.3, 4, "born_signed") ** 2).sum(1), 1)
tests["purity decreases with gamma, uniform at gamma=1"] = all(np.diff(_pur) < 0) and abs(_pur[-1] - 0.25) < 1e-12
# 5. budget accounting: no optimizer exceeds its evaluation budget
for _name, _fn in {"PSO": run_pso, "DMO": run_dmo, "MRFO": run_mrfo, "GA": run_ga, "QI-MRFO": run_qimrfo, "QI-DMO": run_qidmo}.items():
    _o = Objective(_t); _fn(_t, _o, 700, P=10, seed=1); tests[f"{_name} respects the budget"] = _o.n_evals <= 700
# 6. determinism
_r1 = run_qimrfo(_t, Objective(_t), 600, P=10, seed=7, decoherence=0.1); _r2 = run_qimrfo(_t, Objective(_t), 600, P=10, seed=7, decoherence=0.1)
tests["same seed -> same result"] = _r1["best_f"] == _r2["best_f"] and np.array_equal(_r1["best_assign"], _r2["best_assign"])
# 7. gamma = 1 on every candidate makes QI-MRFO a random sampler (purity stays 1/m)
_r3 = run_qimrfo(_t, Objective(_t), 600, P=10, seed=7, decoherence=1.0); tests["gamma=1 -> uniform registers (purity 1/m)"] = abs(_r3["tracker"].purity[-1] - 1 / _t.m) < 1e-9
# 8. valid schedules from all modes
for _mode in ["born_signed", "born_abs", "linear"]:
    _r = run_qimrfo(_t, Objective(_t), 400, P=8, seed=2, mode=_mode, decoherence=0.05); tests[f"valid schedule ({_mode})"] = _r["best_assign"].min() >= 0 and _r["best_assign"].max() < _t.m
# 9. the linear twin's basis-state and measurement agree with the Born version for a one-hot register
tests["one-hot register measures deterministically"] = np.array_equal(measure(basis_state(np.array([2, 0, 1]), 3), np.random.default_rng(0), "born_signed"), np.array([2, 0, 1]))
for k, v in tests.items(): print(("PASS" if v else "FAIL"), "-", k)
assert all(tests.values()), "validation failed"
""")

# ----------------------------------------------------------------------------------------------------- experiment harness
md(r"""
### Experiment harness
`run_suite` runs every (algorithm, instance, seed) combination with equal evaluation budgets and returns one record per run
(best value, gap to LB, runtime, wasted/neutral/improving fractions, mean move size, final diversity, final purity, curves).
Runs are parallelised with `fork` when available and silently fall back to a sequential loop otherwise.
""")
code(r"""
def _heur(fn):
    def _run(inst, obj, budget, seed):
        a = fn(inst); f = obj(a); tr = Tracker(inst.n, inst.m); tr.snapshot(obj.n_evals, [a], [f], f)
        return {"best_f": f, "best_assign": a, "tracker": tr}
    return _run

def _mk(fn, **kw):
    def _run(inst, obj, budget, seed):
        k = {key: (val(inst) if callable(val) else val) for key, val in kw.items()}
        return fn(inst, obj, budget, seed=seed, **k)
    return _run

REGISTRY = {
    "Max-Min": _heur(max_min), "Min-Min": _heur(min_min),
    "Random": _mk(run_random, P=CFG["P"]),
    "PSO": _mk(run_pso, P=CFG["P"]), "DMO": _mk(run_dmo, P=CFG["P"]), "MRFO": _mk(run_mrfo, P=CFG["P"]), "GA": _mk(run_ga, P=CFG["P"]),
    "QI-MRFO": _mk(run_qimrfo, P=CFG["P"], decoherence=lambda inst: CFG["gamma_c_mrfo"] / inst.n),
    "QI-DMO": _mk(run_qidmo, P=CFG["P"], decoherence=lambda inst: CFG["gamma_c_dmo"] / inst.n),
    "P-MRFO (linear twin)": _mk(run_qimrfo, P=CFG["P"], mode="linear", decoherence=lambda inst: CFG["gamma_c_mrfo"] / inst.n),
    "P-DMO (linear twin)": _mk(run_qidmo, P=CFG["P"], mode="linear", decoherence=lambda inst: CFG["gamma_c_dmo"] / inst.n),
    "QI-MRFO no-decoherence": _mk(run_qimrfo, P=CFG["P"], decoherence=0.0),
    "QI-DMO no-decoherence": _mk(run_qidmo, P=CFG["P"], decoherence=0.0),
    "QI-MRFO unsigned": _mk(run_qimrfo, P=CFG["P"], mode="born_abs", decoherence=lambda inst: CFG["gamma_c_mrfo"] / inst.n),
    "QI-DMO register-attractor": _mk(run_qidmo, P=CFG["P"], attractor="register", decoherence=lambda inst: CFG["gamma_c_dmo"] / inst.n),
    "DMO greedy-next": _mk(run_dmo, P=CFG["P"], greedy_next=True),
    "QI-DMO greedy-next": _mk(run_qidmo, P=CFG["P"], greedy_next=True, decoherence=lambda inst: CFG["gamma_c_dmo"] / inst.n),
}

def instance_from_spec(spec, inst_seed=None):
    n, m, dist, het = spec
    return make_instance(n, m, seed=CFG["inst_seed"] if inst_seed is None else inst_seed, task_dist=dist, hetero=het)

def run_one(job):
    algo, spec, seed, budget, objective, inst_seed = job
    inst = instance_from_spec(spec, inst_seed); obj = Objective(inst, kind=objective)
    t0 = time.time(); r = REGISTRY[algo](inst, obj, budget, seed); rt = time.time() - t0
    tr = r["tracker"]; s = tr.summary(); lb = inst.lower_bound(); det = obj.details(r["best_assign"])
    rec = {"algo": algo, "instance": f"n{spec[0]} m{spec[1]} {spec[2]} {spec[3]}", "n": spec[0], "m": spec[1], "seed": seed, "budget": budget,
           "best": float(r["best_f"]), "makespan": det["makespan"], "energy_Wh": det["energy_Wh"], "lb": lb,
           "gap": (det["makespan"] - lb) / lb if objective == "makespan" else np.nan, "runtime_s": rt, "evals": obj.n_evals,
           "wasted": s["wasted_frac"], "neutral": s["neutral_frac"], "improving": s["improving_frac"], "move_size": s["mean_move_size"],
           "gb_impr_per_1k": s["gb_impr_per_1k"], "div_end": tr.div_ham[-1], "purity_end": (tr.purity[-1] if hasattr(tr, "purity") else np.nan),
           "curve_evals": np.array(tr.evals), "curve_best": np.array(tr.best), "curve_div": np.array(tr.div_ham),
           "curve_purity": (np.array(tr.purity) if hasattr(tr, "purity") else None),
           "move_sizes_early": float(np.mean(tr.move_sizes[: len(tr.move_sizes) // 2])) if tr.move_sizes else np.nan,
           "move_sizes_late": float(np.mean(tr.move_sizes[len(tr.move_sizes) // 2:])) if tr.move_sizes else np.nan}
    # V5 diagnostics (Section 19): tighter preemptive LB, global duplicates, critical-VM touches, exchange moves,
    # stagnation time, and the improving relocations / swaps still available at the returned schedule
    s5 = tr.summary_v5(); lb2 = inst.lower_bound_pmtn(); rel, swp, _ = count_improving_moves(inst, r["best_assign"])
    rec.update({"lb2": lb2, "gap2": (det["makespan"] - lb2) / lb2 if objective == "makespan" else np.nan,
                "dup_global": s5["dup_global_frac"], "touch_crit": s5["touch_crit_frac"], "x_frac": s5["x_frac"], "x_success": s5["x_success"],
                "late_improving": s5["late_improving_frac"], "last_gb_impr_frac": s5["last_gb_impr_frac"], "end_impr_reloc": rel, "end_impr_swap": swp})
    return rec

def run_suite(algos, specs, seeds, budget, objective=None, inst_seed=None, label=""):
    objective = objective or CFG["objective"]
    jobs = [(a, s, sd, budget, objective, inst_seed) for s in specs for a in algos for sd in seeds]
    t0 = time.time(); recs = None
    if CFG["parallel"] and len(jobs) > 1:
        try:
            import multiprocessing as mp
            if mp.get_start_method(allow_none=True) in (None, "fork") and hasattr(os, "fork"):
                from concurrent.futures import ProcessPoolExecutor
                with ProcessPoolExecutor(max_workers=min(os.cpu_count() or 1, len(jobs)), mp_context=mp.get_context("fork")) as ex:
                    recs = list(ex.map(run_one, jobs, chunksize=1))
        except Exception as e:
            print("parallel execution unavailable ->", type(e).__name__, "; running sequentially"); recs = None
    if recs is None:
        recs = []
        for k, j in enumerate(jobs):
            recs.append(run_one(j))
            if (k + 1) % 20 == 0: print(f"  {k + 1}/{len(jobs)} runs done ({time.time() - t0:.0f}s)")
    df = pd.DataFrame(recs)
    print(f"{label}: {len(jobs)} runs in {time.time() - t0:.0f}s")
    return df

def summarize(df, by=("instance", "algo")):
    g = df.groupby(list(by))
    out = g.agg(best_mean=("best", "mean"), best_sd=("best", "std"), best_median=("best", "median"), best_min=("best", "min"),
                gap_mean=("gap", "mean"), runtime_s=("runtime_s", "mean"), wasted=("wasted", "mean"), move_size=("move_size", "mean"),
                div_end=("div_end", "mean"), purity_end=("purity_end", "mean"), gb_impr_per_1k=("gb_impr_per_1k", "mean")).reset_index()
    out["gap_mean"] = (100 * out["gap_mean"]).round(2)
    return out.round(3)

# fixed categorical palette (colour follows the entity, never the rank); thin marks, hairline grid
PALETTE = {"QI-MRFO": "#2a78d6", "MRFO": "#eb6834", "GA": "#1baf7a", "QI-DMO": "#eda100", "DMO": "#e87ba4", "PSO": "#008300",
           "P-MRFO (linear twin)": "#4a3aa7", "Random": "#e34948", "P-DMO (linear twin)": "#4a3aa7", "Max-Min": "#898781"}
def style_axes(ax, title="", xlabel="", ylabel=""):
    ax.set_title(title, fontsize=10, loc="left", color="#0b0b0b"); ax.set_xlabel(xlabel, fontsize=9, color="#52514e"); ax.set_ylabel(ylabel, fontsize=9, color="#52514e")
    ax.grid(True, color="#e1e0d9", linewidth=0.6); ax.set_axisbelow(True)
    for sp in ["top", "right"]: ax.spines[sp].set_visible(False)
    for sp in ["left", "bottom"]: ax.spines[sp].set_color("#c3c2b7")
    ax.tick_params(colors="#898781", labelsize=8)
def color_of(name): return PALETTE.get(name, "#898781")
print("harness ready;", len(REGISTRY), "algorithms registered")
""")

# ----------------------------------------------------------------------------------------------------- S11
md(r"""
## SECTION 11 — Small smoke experiment
A 10-task / 3-VM instance, two seeds, 2000 evaluations: every algorithm must run end-to-end and return a valid schedule.
""")
code(r"""
_smoke_specs = [(10, 3, "uniform", "high")]
smoke = run_suite(["Max-Min", "Random", "PSO", "DMO", "MRFO", "GA", "QI-MRFO", "QI-DMO"], _smoke_specs, [0, 1], 2000, label="smoke")
summarize(smoke)[["instance", "algo", "best_mean", "gap_mean", "runtime_s", "wasted", "move_size", "purity_end"]]
""")

# ----------------------------------------------------------------------------------------------------- S12
md(r"""
## SECTION 12 — Baseline experiment (equal budget, common instances, multiple seeds)

**Prediction stated before running (from the pilot):** classical DMO/MRFO degrade towards random search as $n$ grows; the
quantum-inspired versions remove that pathology (move size becomes controllable), with the gain growing with $n$; QI-MRFO should
match the discrete GA; the linear twin should capture most of the gain if the benefit is representational. Effect sizes are only
claimed after the run below. The Max-Min list heuristic is a strong, cheap reference: a metaheuristic that cannot beat it on a static
makespan batch has no practical case there.
""")
code(r"""
BASE_ALGOS = ["Max-Min", "Min-Min", "Random", "PSO", "DMO", "MRFO", "GA", "QI-MRFO", "QI-DMO", "P-MRFO (linear twin)"]
baseline = run_suite(BASE_ALGOS, CFG["instances"], CFG["seeds"], CFG["budget"], label="baseline")
baseline.drop(columns=[c for c in baseline.columns if c.startswith("curve_")]).to_csv(os.path.join(CFG["results_dir"], f"baseline_{MODE}.csv"), index=False)
pickle.dump(baseline, open(os.path.join(CFG["results_dir"], f"baseline_{MODE}.pkl"), "wb"))
base_sum = summarize(baseline)
base_sum.to_csv(os.path.join(CFG["results_dir"], f"baseline_summary_{MODE}.csv"), index=False)
pd.set_option("display.width", 200); pd.set_option("display.max_rows", 200)
base_sum[["instance", "algo", "best_mean", "best_sd", "best_median", "gap_mean", "runtime_s", "wasted", "move_size", "div_end", "purity_end", "gb_impr_per_1k"]]
""")
code(r"""
# gap-to-lower-bound table: instances x algorithms (mean over seeds, %)
pivot_gap = baseline.pivot_table(index="instance", columns="algo", values="gap", aggfunc="mean") * 100
pivot_gap = pivot_gap[[a for a in BASE_ALGOS if a in pivot_gap.columns]].round(2)
print("Mean gap to the lower bound (%):"); pivot_gap
""")

# ----------------------------------------------------------------------------------------------------- S13
md(r"""
## SECTION 13 — Convergence plots
Median best-so-far gap (inter-quartile band) versus evaluations, population diversity, register purity, and the move-size
diagnostic (early vs late half of the run). One axis per panel; colours follow the algorithm identity throughout the notebook.
""")
code(r"""
def curve_grid(df, algo, instance, key="curve_best", npts=120):
    sub = df[(df.algo == algo) & (df.instance == instance)]
    if len(sub) == 0: return None, None
    xmax = max(r.curve_evals[-1] for r in sub.itertuples())
    grid = np.linspace(0, xmax, npts); ys = []
    for r in sub.itertuples():
        y = getattr(r, key)
        if y is None: return None, None
        ys.append(np.interp(grid, r.curve_evals, y))
    return grid, np.array(ys)

PLOT_ALGOS = ["MRFO", "QI-MRFO", "GA", "DMO", "QI-DMO", "PSO"]
insts = list(dict.fromkeys(baseline.instance))
fig, axes = plt.subplots(1, len(insts), figsize=(4.2 * len(insts), 3.4), squeeze=False)
for ax, inst_name in zip(axes[0], insts):
    lb = baseline[baseline.instance == inst_name].lb.iloc[0]
    for algo in PLOT_ALGOS:
        grid, ys = curve_grid(baseline, algo, inst_name)
        if grid is None: continue
        gap = (ys - lb) / lb * 100
        ax.plot(grid, np.median(gap, 0), color=color_of(algo), linewidth=1.8, label=algo)
        ax.fill_between(grid, np.percentile(gap, 25, 0), np.percentile(gap, 75, 0), color=color_of(algo), alpha=0.12, linewidth=0)
    ax.set_yscale("log"); style_axes(ax, inst_name, "evaluations", "gap to LB (%)  [log]")
axes[0][0].legend(fontsize=8, frameon=False)
fig.suptitle("Convergence (median, IQR band)", x=0.01, ha="left", fontsize=11); fig.tight_layout(); plt.savefig(os.path.join(CFG["results_dir"], f"fig_convergence_{MODE}.png"), dpi=130); plt.show()
""")
code(r"""
fig, axes = plt.subplots(1, len(insts), figsize=(4.2 * len(insts), 3.2), squeeze=False)
for ax, inst_name in zip(axes[0], insts):
    for algo in PLOT_ALGOS:
        grid, ys = curve_grid(baseline, algo, inst_name, key="curve_div")
        if grid is None: continue
        ax.plot(grid, np.median(ys, 0), color=color_of(algo), linewidth=1.8, label=algo)
    style_axes(ax, inst_name, "evaluations", "diversity (mean Hamming / n)")
axes[0][0].legend(fontsize=8, frameon=False)
fig.suptitle("Population diversity", x=0.01, ha="left", fontsize=11); fig.tight_layout(); plt.savefig(os.path.join(CFG["results_dir"], f"fig_diversity_{MODE}.png"), dpi=130); plt.show()

fig, axes = plt.subplots(1, len(insts), figsize=(4.2 * len(insts), 3.2), squeeze=False)
for ax, inst_name in zip(axes[0], insts):
    for algo in ["QI-MRFO", "QI-DMO", "P-MRFO (linear twin)"]:
        grid, ys = curve_grid(baseline, algo, inst_name, key="curve_purity")
        if grid is None: continue
        ax.plot(grid, np.median(ys, 0), color=color_of(algo), linewidth=1.8, label=algo)
    style_axes(ax, inst_name, "evaluations", "mean register purity")
axes[0][0].legend(fontsize=8, frameon=False)
fig.suptitle("Register purity (1 = collapsed, 1/m = uniform)", x=0.01, ha="left", fontsize=11); fig.tight_layout(); plt.savefig(os.path.join(CFG["results_dir"], f"fig_purity_{MODE}.png"), dpi=130); plt.show()
""")
code(r"""
# move-size diagnostic: how many tasks does a candidate change, early vs late in the run (largest instance)
big = max(insts, key=lambda s: int(s.split()[0][1:]))
ms = baseline[baseline.instance == big].groupby("algo")[["move_sizes_early", "move_sizes_late"]].mean().reindex([a for a in PLOT_ALGOS + ["P-MRFO (linear twin)"] if a in set(baseline.algo)])
fig, ax = plt.subplots(figsize=(7, 3.2)); x = np.arange(len(ms)); w = 0.38
ax.bar(x - w / 2, ms.move_sizes_early, w, color=[color_of(a) for a in ms.index], alpha=0.55, label="first half of run", linewidth=0)
ax.bar(x + w / 2, ms.move_sizes_late, w, color=[color_of(a) for a in ms.index], label="second half of run", linewidth=0)
ax.set_xticks(x); ax.set_xticklabels(ms.index, fontsize=8, rotation=15); style_axes(ax, f"Mean number of tasks changed per candidate — {big}", "", "tasks changed")
ax.legend(fontsize=8, frameon=False); fig.tight_layout(); plt.savefig(os.path.join(CFG["results_dir"], f"fig_movesize_{MODE}.png"), dpi=130); plt.show()
ms.round(2)
""")

# ----------------------------------------------------------------------------------------------------- S14
md(r"""
## SECTION 14 — Statistical analysis
Paired comparisons by seed (Wilcoxon signed-rank; Holm correction across instances), non-parametric effect sizes
(Cliff's $\delta$ and Vargha–Delaney $A_{12}$), bootstrap 95 % confidence intervals of the mean gap difference, and a Friedman test over
algorithms. With few seeds (smoke/fast modes) p-values are reported but are not expected to reach significance; the `full` mode has 30 seeds.
""")
code(r"""
def cliffs_delta(x, y):
    x, y = np.asarray(x), np.asarray(y); gt = (x[:, None] > y[None, :]).mean(); lt = (x[:, None] < y[None, :]).mean(); return gt - lt
def a12(x, y):
    x, y = np.asarray(x), np.asarray(y); return ((x[:, None] < y[None, :]).mean() + 0.5 * (x[:, None] == y[None, :]).mean())   # P(x < y): >0.5 means x is better (minimisation)
def boot_ci(d, B=4000, seed=0):
    d = np.asarray(d); rng = np.random.default_rng(seed); bs = [rng.choice(d, len(d), replace=True).mean() for _ in range(B)]; return np.percentile(bs, [2.5, 97.5])
def holm(pvals):
    p = np.asarray(pvals, float); order = np.argsort(p); adj = np.empty_like(p); m = len(p); running = 0
    for rank, idx in enumerate(order):
        running = max(running, (m - rank) * p[idx]); adj[idx] = min(1.0, running)
    return adj

PAIRS = [("QI-MRFO", "MRFO"), ("QI-MRFO", "GA"), ("QI-MRFO", "P-MRFO (linear twin)"), ("QI-MRFO", "Max-Min"), ("QI-DMO", "DMO"), ("QI-DMO", "GA"), ("QI-MRFO", "QI-DMO")]
rows = []
for a, b in PAIRS:
    for inst_name in insts:
        xa = baseline[(baseline.algo == a) & (baseline.instance == inst_name)].sort_values("seed").gap.values
        xb = baseline[(baseline.algo == b) & (baseline.instance == inst_name)].sort_values("seed").gap.values
        if len(xa) == 0 or len(xb) == 0: continue
        if len(xa) == len(xb) and len(xa) >= 2 and np.any(xa != xb):
            p = stats.wilcoxon(xa, xb, zero_method="zsplit").pvalue if len(xa) >= 5 else stats.ttest_rel(xa, xb).pvalue
        else: p = np.nan
        d = 100 * (xa - xb); lo, hi = boot_ci(d) if len(d) >= 2 else (np.nan, np.nan)
        rows.append({"A": a, "B": b, "instance": inst_name, "gap A %": 100 * xa.mean(), "gap B %": 100 * xb.mean(), "diff (A-B) pp": d.mean(), "CI95 lo": lo, "CI95 hi": hi,
                     "p": p, "cliffs_delta": cliffs_delta(xa, xb), "A12 (P[A better])": a12(xa, xb)})
stat = pd.DataFrame(rows)
stat["p_holm"] = np.nan
for (a, b), g in stat.groupby(["A", "B"]):
    mask = g.p.notna()
    if mask.any(): stat.loc[g.index[mask], "p_holm"] = holm(g.p[mask].values)
stat.to_csv(os.path.join(CFG["results_dir"], f"stats_{MODE}.csv"), index=False)
stat.round(4)
""")
code(r"""
# average ranks across instances (lower is better) + Friedman test on per-(instance, seed) blocks
wide = baseline.pivot_table(index=["instance", "seed"], columns="algo", values="best")
ranks = wide.rank(axis=1, method="average")
print("mean rank over all (instance, seed) blocks:"); print(ranks.mean().sort_values().round(2).to_string())
if wide.shape[0] >= 3 and wide.shape[1] >= 3:
    fr = stats.friedmanchisquare(*[wide[c].values for c in wide.columns]); print(f"\nFriedman chi2 = {fr.statistic:.2f}, p = {fr.pvalue:.2e}")
""")

# ----------------------------------------------------------------------------------------------------- S15
md(r"""
## SECTION 15 — Ablation: did the quantum-inspired component cause the effect?
Four ladders on the primary host (and the same on DMO):
1. **MRFO** (classical, floor encoding) → 2. **QI-MRFO no-decoherence** (registers + measurement only) → 3. **QI-MRFO** (full) — isolates the representation and the channel.
4. **QI-MRFO unsigned** removes the sign (no interference possible). 5. **P-MRFO (linear twin)** replaces the Born rule by linear probability mixing: the classical equivalent.
6. **QI-DMO register-attractor** uses the alpha's superposition instead of its measured schedule as attractor (negative control for collapse-conditioned attraction).
7. **DMO greedy-next / QI-DMO greedy-next** test whether DMO's unconditional 'next position' move explains the QI-DMO vs QI-MRFO difference.
""")
code(r"""
ABL_SPECS = CFG["instances"][:4] if MODE == "full" else CFG["instances"][:2] + CFG["instances"][2:3]
ABL_ALGOS = ["MRFO", "QI-MRFO no-decoherence", "QI-MRFO", "QI-MRFO unsigned", "P-MRFO (linear twin)",
             "DMO", "QI-DMO no-decoherence", "QI-DMO", "P-DMO (linear twin)", "QI-DMO register-attractor", "DMO greedy-next", "QI-DMO greedy-next", "GA"]
ablation = run_suite(ABL_ALGOS, ABL_SPECS, CFG["seeds"], CFG["budget"], label="ablation")
ablation.drop(columns=[c for c in ablation.columns if c.startswith("curve_")]).to_csv(os.path.join(CFG["results_dir"], f"ablation_{MODE}.csv"), index=False)
abl_sum = summarize(ablation)
abl_pivot = ablation.pivot_table(index="algo", columns="instance", values="gap", aggfunc="mean").reindex(ABL_ALGOS) * 100
print("Ablation: mean gap to LB (%)"); abl_pivot.round(2)
""")
code(r"""
abl_sum[["instance", "algo", "best_mean", "best_sd", "gap_mean", "wasted", "move_size", "div_end", "purity_end"]]
""")

# ----------------------------------------------------------------------------------------------------- S16
md(r"""
## SECTION 16 — Parameter sensitivity
Decoherence strength $\gamma = c/n$ (dose–response), population size $P$ and the somersault factor $S$ for QI-MRFO; $\gamma$ for QI-DMO.
The pilot chose $c=1$ (MRFO) and $c=0.25$ (DMO); this section shows how flat or sharp the optimum is.
""")
code(r"""
SENS_SPECS = [CFG["instances"][1], CFG["instances"][2], CFG["instances"][4]] if MODE == "full" else CFG["instances"][1:3]
for c in [0.0, 0.25, 0.5, 1.0, 2.0, 4.0]:
    REGISTRY[f"QI-MRFO c={c}"] = _mk(run_qimrfo, P=CFG["P"], decoherence=(lambda inst, c=c: c / inst.n))
    REGISTRY[f"QI-DMO c={c}"] = _mk(run_qidmo, P=CFG["P"], decoherence=(lambda inst, c=c: c / inst.n))
for Pp in [15, 60]:
    REGISTRY[f"QI-MRFO P={Pp}"] = _mk(run_qimrfo, P=Pp, decoherence=lambda inst: CFG["gamma_c_mrfo"] / inst.n)
for Ss in [1.0, 3.0]:
    REGISTRY[f"QI-MRFO S={Ss}"] = _mk(run_qimrfo, P=CFG["P"], S=Ss, decoherence=lambda inst: CFG["gamma_c_mrfo"] / inst.n)
SENS_ALGOS = [f"QI-MRFO c={c}" for c in [0.0, 0.25, 0.5, 1.0, 2.0, 4.0]] + [f"QI-DMO c={c}" for c in [0.0, 0.25, 0.5, 1.0, 2.0, 4.0]] + ["QI-MRFO P=15", "QI-MRFO P=60", "QI-MRFO S=1.0", "QI-MRFO S=3.0"]
sens = run_suite(SENS_ALGOS, SENS_SPECS, CFG["seeds"], CFG["budget"], label="sensitivity")
sens.drop(columns=[c for c in sens.columns if c.startswith("curve_")]).to_csv(os.path.join(CFG["results_dir"], f"sensitivity_{MODE}.csv"), index=False)
sens_pivot = sens.pivot_table(index="algo", columns="instance", values="gap", aggfunc="mean").reindex(SENS_ALGOS) * 100
sens_w = sens.pivot_table(index="algo", columns="instance", values="wasted", aggfunc="mean").reindex(SENS_ALGOS)
print("Sensitivity: mean gap to LB (%)"); display(sens_pivot.round(2)); print("wasted candidate fraction"); sens_w.round(3)
""")
code(r"""
fig, axes = plt.subplots(1, 2, figsize=(9, 3.2))
cs = [0.0, 0.25, 0.5, 1.0, 2.0, 4.0]
for ax, host, col in zip(axes, ["QI-MRFO", "QI-DMO"], ["#2a78d6", "#eda100"]):
    for k, inst_name in enumerate(list(dict.fromkeys(sens.instance))):
        y = [sens[(sens.algo == f"{host} c={c}") & (sens.instance == inst_name)].gap.mean() * 100 for c in cs]
        ax.plot(range(len(cs)), y, marker="o", markersize=5, linewidth=1.8, color=col, alpha=1 - 0.35 * k, label=inst_name)
    ax.set_xticks(range(len(cs))); ax.set_xticklabels([str(c) for c in cs]); style_axes(ax, f"{host}: decoherence dose-response", "c  (gamma = c / n)", "gap to LB (%)"); ax.legend(fontsize=7, frameon=False)
fig.tight_layout(); plt.savefig(os.path.join(CFG["results_dir"], f"fig_sensitivity_{MODE}.png"), dpi=130); plt.show()
""")

# ----------------------------------------------------------------------------------------------------- S17
md(r"""
## SECTION 17 — Failure-case (adversarial) experiments
Regimes where the mechanism is *expected not to help* or to lose:
* **17a** tiny search space ($n=10, m=3$) — random search may suffice;
* **17b** two VMs ($m=2$) — the floor encoding is almost lossless, so the representational advantage should vanish;
* **17c** identical tasks on homogeneous VMs — a trivial landscape, exploitation should dominate;
* **17d** the smooth `makespan_energy` objective — additive, no plateaus; heuristics are not designed for it;
* **17e** many VMs ($n=40, m=20$) — large registers, possible over-fast collapse;
* **17f** the bimodal (tall-barrier) instance against the Max-Min heuristic;
* **17g** runtime and memory overhead of the register representation;
* **17h** dynamic workloads (task churn, VM failure, VM addition, speed drift) — the cloud-specific extension: restart vs continue vs decoherence shock vs GA hypermutation.
""")
code(r"""
FAIL_ALGOS = ["Max-Min", "Random", "MRFO", "QI-MRFO", "GA", "DMO", "QI-DMO"]
fail_cases = {"17a tiny": (10, 3, "uniform", "high"), "17b two VMs": (40, 2, "uniform", "high"), "17c identical tasks, homogeneous VMs": (40, 8, "identical", "none"),
              "17e many VMs": (40, 20, "uniform", "high"), "17f bimodal tall barriers": (50, 10, "bimodal", "high")}
fail_frames = []
for label, spec in fail_cases.items():
    df = run_suite(FAIL_ALGOS, [spec], CFG["seeds"], min(CFG["budget"], 10000), label=label); df["case"] = label; fail_frames.append(df)
# 17d smooth objective (makespan + energy); the 'best' column is the combined objective, 'makespan'/'energy_Wh' are the components
df = run_suite(FAIL_ALGOS, [CFG["instances"][min(2, len(CFG["instances"]) - 1)]], CFG["seeds"], min(CFG["budget"], 10000), objective="makespan_energy", label="17d makespan_energy"); df["case"] = "17d makespan+energy"; fail_frames.append(df)
# 17c follow-up (V4 of the research loop): the identical-task plateau exposed that QI-MRFO's strict greedy acceptance blocks
# neutral drift. Test the classical fix — accept equal-fitness candidates — on the plateau instance and on a normal one.
REGISTRY["QI-MRFO neutral-accept"] = _mk(run_qimrfo, P=CFG["P"], accept_equal=True, decoherence=lambda inst: CFG["gamma_c_mrfo"] / inst.n)
for label, spec in {"17c identical tasks, homogeneous VMs": (40, 8, "identical", "none"), "17c-control uniform n100": CFG["instances"][min(2, len(CFG["instances"]) - 1)]}.items():
    df = run_suite(["QI-MRFO", "QI-MRFO neutral-accept"], [spec], CFG["seeds"], min(CFG["budget"], 10000), label=label + " (neutral acceptance)"); df["case"] = label + " / neutral-accept test"; fail_frames.append(df)
fail = pd.concat(fail_frames, ignore_index=True)
fail.drop(columns=[c for c in fail.columns if c.startswith("curve_")]).to_csv(os.path.join(CFG["results_dir"], f"failure_cases_{MODE}.csv"), index=False)
fail_tab = fail.groupby(["case", "algo"]).agg(best_mean=("best", "mean"), best_sd=("best", "std"), makespan=("makespan", "mean"), energy_Wh=("energy_Wh", "mean"), gap_pct=("gap", lambda g: 100 * g.mean()), wasted=("wasted", "mean"), move_size=("move_size", "mean")).round(3)
fail_tab
""")
code(r"""
# 17g runtime / memory overhead of the register representation
ov_spec = (100, 10, "uniform", "high"); ov_inst = instance_from_spec(ov_spec)
ov = {}
for name in ["MRFO", "QI-MRFO", "DMO", "QI-DMO", "GA"]:
    t0 = time.time(); r = REGISTRY[name](ov_inst, Objective(ov_inst), 6000, 0); ov[name] = {"s_per_1k_evals": (time.time() - t0) / 6.0,
          "state_bytes": (CFG["P"] * ov_inst.n * ov_inst.m * 8 if name.startswith("QI") else CFG["P"] * ov_inst.n * 8)}
ov = pd.DataFrame(ov).T; ov["overhead_vs_classical"] = [ov.loc[k, "s_per_1k_evals"] / ov.loc[k[3:], "s_per_1k_evals"] if k.startswith("QI") else 1.0 for k in ov.index]
print(f"instance n={ov_inst.n}, m={ov_inst.m}, P={CFG['P']}"); ov.round(4)
""")
md(r"""
### 17h — Dynamic workloads (cloud-specific extension pilot)
Hypothesis: after a workload change, a swarm that has collapsed must re-diversify; full restart discards all information, naive
continuation keeps a stale, collapsed population. The depolarising channel gives a *controlled forgetting* knob $\gamma_{shock}$; the
classical equivalent for the GA is hypermutation. The register representation also has clean rules for structural change:
VM removal = column deletion (projective measurement), VM addition = a new column with a uniform share, new tasks = uniform registers.
""")
code(dyn["S17 dynamic harness"] + r"""
DYN_CONFIGS = [("QI-MRFO", "restart", {}), ("QI-MRFO", "continue", {}), ("QI-MRFO", "shock", {"gamma_shock": 0.25}), ("QI-MRFO", "shock", {"gamma_shock": 0.5}), ("QI-MRFO", "shock", {"gamma_shock": 0.75}),
               ("MRFO", "restart", {}), ("MRFO", "continue", {}), ("GA", "restart", {}), ("GA", "continue", {}), ("GA", "hypermut", {})]
DYN_CHANGES = ["churn", "vm_fail", "vm_add", "drift"]

def run_dyn_job(job):
    change, algo, strat, kw, s = job
    seq = make_dynamic_sequence(50, 10, seed=s, K=5, change=change)
    out = run_dynamic(seq, algo, strat, CFG["dyn_budget0"], CFG["dyn_budget"], seed=s, P=CFG["P"], decoherence_c=CFG["gamma_c_mrfo"], **kw)
    post = out[1:]
    return {"change": change, "algo": algo, "strategy": strat + (f" g={kw['gamma_shock']}" if kw else ""), "seed": s,
            "post_gap": np.mean([o["gap"] for o in post]), "auc_gap": np.mean([o["auc_gap"] for o in post]), "vs_maxmin": np.mean([o["best"] / o["maxmin"] for o in post]),
            "epoch0_gap": out[0]["gap"]}

dyn_jobs = [(ch, a, st, kw, s) for ch in DYN_CHANGES for a, st, kw in DYN_CONFIGS for s in CFG["dyn_seeds"]]
t0 = time.time(); dyn_rows = None
if CFG["parallel"]:
    try:
        import multiprocessing as mp
        if mp.get_start_method(allow_none=True) in (None, "fork") and hasattr(os, "fork"):
            from concurrent.futures import ProcessPoolExecutor
            with ProcessPoolExecutor(max_workers=min(os.cpu_count() or 1, len(dyn_jobs)), mp_context=mp.get_context("fork")) as ex:
                dyn_rows = list(ex.map(run_dyn_job, dyn_jobs, chunksize=1))
    except Exception as e:
        print("parallel execution unavailable ->", type(e).__name__, "; running sequentially"); dyn_rows = None
if dyn_rows is None:
    dyn_rows = [run_dyn_job(j) for j in dyn_jobs]
print(f"dynamic pilot: {len(dyn_jobs)} runs in {time.time() - t0:.0f}s")
dyn = pd.DataFrame(dyn_rows); dyn.to_csv(os.path.join(CFG["results_dir"], f"dynamic_{MODE}.csv"), index=False)
dyn_tab = dyn.groupby(["change", "algo", "strategy"]).agg(post_gap_pct=("post_gap", lambda g: 100 * g.mean()), post_gap_sd=("post_gap", lambda g: 100 * g.std()), auc_gap_pct=("auc_gap", lambda g: 100 * g.mean()), vs_maxmin=("vs_maxmin", "mean")).round(2)
dyn_tab
""")
code(r"""
fig, axes = plt.subplots(1, len(DYN_CHANGES), figsize=(4.0 * len(DYN_CHANGES), 3.4), squeeze=False)
for ax, change in zip(axes[0], DYN_CHANGES):
    sub = dyn[dyn.change == change].groupby(["algo", "strategy"]).auc_gap.mean().reset_index()
    labels = [f"{a}\n{s}" for a, s in zip(sub.algo, sub.strategy)]
    ax.barh(range(len(sub)), sub.auc_gap * 100, color=[color_of(a) for a in sub.algo], linewidth=0, height=0.7)
    ax.set_yticks(range(len(sub))); ax.set_yticklabels(labels, fontsize=6.5); ax.invert_yaxis()
    style_axes(ax, f"{change}: area under the gap curve after changes (%)", "AUC of gap (%) — lower is faster recovery", "")
fig.tight_layout(); plt.savefig(os.path.join(CFG["results_dir"], f"fig_dynamic_{MODE}.png"), dpi=130); plt.show()
""")

# ----------------------------------------------------------------------------------------------------- S18
md(r"""
## SECTION 18 — Interpretation

The cell below prints the key comparisons from the results produced *in this execution*; the text that follows interprets the
pattern that the pilot study (5 seeds, 20 000 evaluations, documented in `lab_log.md` and the report) established and that the
`fast`/`full` modes re-test. Read the printed numbers first: if they contradict the text, the numbers win.
""")
code(r"""
def _g(df, algo, inst_name):
    s = df[(df.algo == algo) & (df.instance == inst_name)].gap; return 100 * s.mean() if len(s) else np.nan
print("=== Baseline: mean gap to LB (%) ===")
for inst_name in insts:
    print(f"{inst_name:26s} " + "  ".join(f"{a}={_g(baseline, a, inst_name):6.2f}" for a in ["MRFO", "QI-MRFO", "P-MRFO (linear twin)", "GA", "Max-Min", "DMO", "QI-DMO", "Random"]))
print("\n=== Mechanism diagnostics on the largest instance ===")
for a in ["MRFO", "QI-MRFO", "DMO", "QI-DMO", "GA"]:
    sub = baseline[(baseline.algo == a) & (baseline.instance == big)]
    print(f"{a:10s} move size early/late = {sub.move_sizes_early.mean():5.1f}/{sub.move_sizes_late.mean():5.1f}   wasted = {sub.wasted.mean():.3f}   end diversity = {sub.div_end.mean():.3f}   gb-improvements/1k evals = {sub.gb_impr_per_1k.mean():.2f}")
print("\n=== Ablation (mean gap %, averaged over ablation instances) ===")
print(abl_pivot.mean(1).round(2).to_string())
print("\n=== Dynamic pilot: mean post-change gap (%) / AUC (%) ===")
for (ch, a, s), g in dyn.groupby(["change", "algo", "strategy"]):
    print(f"{ch:8s} {a:8s} {s:16s} gap={100 * g.post_gap.mean():6.2f}  auc={100 * g.auc_gap.mean():6.2f}")
""")
md(r"""
### Reading the results (pattern established in the pilot; verify against the printout above)

1. **The classical failure mode is the encoding, not the metaphor.** With the floor encoding, MRFO and DMO change ~half of all task assignments per candidate and fall to random-search level for $n \ge 50$; a discrete GA with 1/n mutation does not. This is the *observation* that motivated the mechanism.
2. **Superposition + measurement fixes it.** QI-MRFO/QI-DMO make move size a function of register purity; the gap to the lower bound at $n=100$ falls from ~100 % (MRFO) to ~1 % (QI-MRFO). The gain grows with $n$ as predicted.
3. **Decoherence is necessary and must be weak.** Without the channel the registers collapse (purity → 1) and 25–75 % of evaluations re-measure the same schedule. A depolarising strength $\gamma \approx (0.25\text{–}1)/n$ removes the waste and improves every instance; larger $\gamma$ degrades monotonically (dose–response). The optimum is host-dependent (MRFO tolerates more than DMO because it is greedy in every phase).
4. **The quantum-specific part is not what carries the effect.** The linear-probability twin matches the Born-rule version at the end of the run; signed vs unsigned amplitudes are indistinguishable. The Born rule only accelerates concentration (higher purity early). The honest statement is therefore: *a quantum-inspired representation (superposition, measurement, decoherence) repairs a real defect of swarm schedulers; its classical equivalent (a probability-vector swarm with a mutation floor) works equally well.*
5. **Collapse-conditioned attraction is essential.** Using the alpha's superposition instead of its measured schedule as attractor destroys the search (purity stays at 1/m).
6. **Boundary of usefulness.** On a static makespan batch the Max-Min list heuristic remains competitive or better on tall-barrier (bimodal) instances; with $m=2$ or trivial landscapes every method converges; the practical case for the population method is where heuristics do not apply: additive/multi-objective objectives and dynamic re-optimisation.
7. **Dynamic workloads (pilot).** Carrying the register state across a change beats restarting on every change type (recovery AUC 2–4× lower) and beats the GA's carried population on VM drift, VM addition and VM failure, because the representation has clean structural rules (column deletion = projective measurement, uniform share for a new VM, uniform registers for new tasks). The decoherence *shock* — the strong form of the "controlled forgetting" hypothesis — is **not** supported at 20 % churn / mild drift: $\gamma_{shock}=0.5$ gives at most a small final-gap gain at the cost of slower recovery, and shocks hurt on structural changes; GA hypermutation (its classical analogue) hurts everywhere. The open question is whether forgetting pays off only above a change-severity threshold (the report's next experiment).
8. **Overhead.** The register representation costs roughly $m$ times the memory and ~2× wall time per evaluation of the floor encoding at $n=100, m=10$; negligible against evaluation costs in a real simulator.

**Decision (see the report):** PROCEED with a *revised* framing — the research question is not "does the quantum metaphor beat the classical one?" (it does not) but "which properties of a measurement-based (superposition) schedule representation — purity-controlled move size, structural adaptation rules, and severity-dependent forgetting — matter for cloud re-scheduling under change, and where is the boundary?"
""")

# ----------------------------------------------------------------------------------------------------- S19 (V5)
md(r"""
## SECTION 19 — V5: where the evaluations go, and critical exchange measurement (hypothesis H5)

**Observation (V5, `observe_v5_diagnostics.py`, `observe_v5_localopt.py`; reproduced below on this run's baseline).**
Four facts about QI-MRFO with $c=1$:
* **O1.** 31–46 % of its evaluations re-evaluate a schedule already seen in the run. The earlier "wasted" metric only
  counted parent-identical candidates.
* **O2.** A candidate can lower the makespan only if it moves a task off its reference schedule's critical VM. Every
  improving candidate does this, but only 20–45 % of candidates do.
* **O3.** The global best stops improving early, at 16–54 % of the budget.
* **O4.** QI-MRFO's end points are always *relocation-optimal*, yet 1–50 strictly improving critical **swaps** remain.

The product-state measurement samples tasks independently and so almost never produces the correlated two-task
change a relocation-optimal schedule needs.

**Mechanism (H5, `qi_core.critical_exchange`, `run_qimrfo(exchange=p_x)`).** With probability $p_x$ a measured candidate
$a$ additionally undergoes a *critical exchange*. A task $t$ is drawn uniformly from the critical VM $b$ of $a$, and a
task $u$ uniformly from the tasks on other VMs that are shorter than $t$ (necessary for $\mathrm{Load}_b$ to fall).
Then $a_t \leftrightarrow a_u$; if no shorter task exists, $t$ is relocated. The two registers then collapse onto the
outcome, $\Psi[t] \leftarrow \mathcal{D}_\gamma(E(a_t))$ and $\Psi[u] \leftarrow \mathcal{D}_\gamma(E(a_u))$, so an
accepted register remembers the exchange. Quantum reading: a *correlated* (non-product) measurement of a register pair,
followed by measurement back-action. Classical equivalent: swap mutation. The GA gets the identical operator
(`run_ga(exchange=p_x)`) as the control that decides whether the gain is specific to the register swarm.

**Protocol (pre-registered in `research_plan_v5.md`).** $p_x$ was tuned on the pilot instances only (development set,
selection-biased), then frozen at $p_x = 1$ and tested on 8 new families × 10 new instances (seeds 101–110) × 2 run
seeds at 20 000 evaluations. The committed results are `results/h5_tune/`, `results/h5_test/` and
`results/h5_analysis.md`. The cells below (i) reproduce the O1–O4 diagnostics on this run's baseline, (ii) run a small
held-out demonstration sized by `QI_MODE`, and (iii) print the committed held-out results when present.
""")
code(r"""
# (i) O1-O4 on this execution's baseline runs (Section 12)
diag_cols = ["gap", "gap2", "dup_global", "wasted", "touch_crit", "last_gb_impr_frac", "late_improving", "end_impr_reloc", "end_impr_swap"]
print("V5 diagnostics on the Section-12 baseline (means over seeds):")
baseline[baseline.algo.isin(["QI-MRFO", "P-MRFO (linear twin)", "GA", "Max-Min"])].groupby(["instance", "algo"])[diag_cols].mean().round(4)
""")
code(r"""
# (ii) held-out demonstration: new instances (inst_seed 101), CXM on QI-MRFO, its linear twin and the GA control
REGISTRY["QI-MRFO+CXM"] = _mk(run_qimrfo, P=CFG["P"], exchange=1.0, decoherence=lambda inst: CFG["gamma_c_mrfo"] / inst.n)
REGISTRY["P-MRFO+CXM (linear twin)"] = _mk(run_qimrfo, P=CFG["P"], mode="linear", exchange=1.0, decoherence=lambda inst: CFG["gamma_c_mrfo"] / inst.n)
REGISTRY["GA+CXM"] = _mk(run_ga, P=CFG["P"], exchange=1.0)
# H7 control: a (1+1)-EA with exactly the moves of a collapsed QI-MRFO+CXM (c and p_x tuned on the pilot instances only)
REGISTRY["(1+1)-EA+CXM"] = _mk(run_one_plus_one, decoherence=lambda inst: 1.0 / inst.n, exchange=0.5)
PALETTE.update({"QI-MRFO+CXM": "#0b4f9c", "GA+CXM": "#0e7a52", "P-MRFO+CXM (linear twin)": "#2e2370"})
H5_SPECS = {"smoke": [(80, 8, "uniform", "high"), (100, 10, "bimodal", "high")],
            "fast": [(80, 8, "uniform", "high"), (100, 10, "bimodal", "high"), (120, 12, "lognormal", "high"), (60, 12, "uniform", "low")],
            "full": [(80, 8, "uniform", "high"), (150, 15, "uniform", "high"), (100, 10, "bimodal", "high"), (200, 10, "bimodal", "none"),
                     (120, 12, "lognormal", "high"), (60, 12, "uniform", "low"), (100, 20, "lognormal", "low")]}[MODE]
H5_ALGOS = ["Max-Min", "GA", "GA+CXM", "(1+1)-EA+CXM", "QI-MRFO", "QI-MRFO+CXM", "P-MRFO+CXM (linear twin)"]
h5 = run_suite(H5_ALGOS, H5_SPECS, CFG["seeds"], CFG["budget"], inst_seed=101, label="H5 demo (inst_seed 101)")
h5.drop(columns=[c for c in h5.columns if c.startswith("curve_")]).to_csv(os.path.join(CFG["results_dir"], f"h5_demo_{MODE}.csv"), index=False)
print("gap to the preemptive LB (%), mean over seeds:")
display((h5.pivot_table(index="instance", columns="algo", values="gap2", aggfunc="mean")[H5_ALGOS] * 100).round(3))
h5.groupby("algo")[["end_impr_swap", "last_gb_impr_frac", "x_success", "dup_global", "move_size", "runtime_s"]].mean().reindex(H5_ALGOS).round(4)
""")
code(r"""
# (iii) the committed held-out experiment (80 new instances x 2 seeds), if the repository's results/ folder is present
_h5p = os.path.join("results", "h5_test", "records.csv")
if os.path.exists(_h5p):
    h5t = pd.read_csv(_h5p)
    _alg = ["Max-Min", "GA", "GA+CXM", "P-MRFO", "P-MRFO+CXM", "QI-MRFO", "QI-MRFO+CXM"]
    print("committed H5 held-out results: mean gap to the preemptive LB (%)")
    display((h5t.pivot_table(index="family", columns="algo", values="gap2", aggfunc="mean")[_alg] * 100).round(3))
    _w = h5t[h5t.algo.isin(["QI-MRFO", "QI-MRFO+CXM"])].groupby(["family", "inst_seed", "algo"]).gap2.mean().unstack("algo")
    _d = 100 * (_w["QI-MRFO+CXM"] - _w["QI-MRFO"]).values
    print(f"P1 (pooled over {len(_d)} instances): mean diff = {_d.mean():.3f} pp, 95% bootstrap CI = {np.round(boot_ci(_d), 3)}, "
          f"Wilcoxon p = {stats.wilcoxon(_d).pvalue:.2e}, CXM better on {(_d < 0).sum()}/{len(_d)} instances")
else:
    print("results/h5_test/records.csv not found (run `python exp_h5_cxm.py tune test analyze` in the repository)")
""")
md(r"""
### 19.1 What the held-out experiment showed (committed run; `results/h5_analysis.md`, `results/h5_posthoc.md`)

The printout above is authoritative; where it disagrees with this text, the numbers win.

* **P1 (primary) confirmed.** CXM lowers QI-MRFO's gap to the preemptive bound from 3.40 % to 0.54 %: −2.86 pp,
  95 % CI [−3.58, −2.21], better on 76/80 new instances. Seven of 8 families are Holm-significant, and no family is
  worse. With $p_x = 0.5$ the result is the same (−2.81 pp).
* **Against Max-Min.** Unchanged QI-MRFO loses on 73/80 instances. QI-MRFO+CXM wins on 6 of 8 families and loses
  on n100 m20 lognormal/low. There Max-Min attains the lower bound on every instance: the largest task alone on the
  fastest VM is provably optimal, and reaching it by local moves needs makespan-neutral steps that strict acceptance
  rejects (a plateau).
* **P5.** CXM is *not* a generic fix. The GA gains 0.81 pp, and QI-MRFO+CXM beats GA+CXM on 73/80 instances. The
  exchange works because the register swarm applies it greedily around a collapsed best and stores it through
  back-action.
* **P4 falsified.** Under CXM the classical linear twin is slightly but significantly **better** than the Born-rule
  version (68/80 instances, margins below 0.2 pp). The quantum-specific ingredient is again not a source of advantage.
* **P3 partially supported.** The end points are nearly swap-optimal (improving swaps 140 → 11) and the last
  improvement comes later (54 % → 76 % of the budget). The late-half improving rate fell because CXM converges early.
* **P2** (absolute dose–response) not supported; the post hoc relative version is ρ = 0.71 and is exploratory.
""")

code(r"""
# (iv) committed H7 run (fresh instances, seeds 201-210): is the register swarm needed once CXM exists? Max-Min seeding
_h7p = os.path.join("results", "h7_test", "records.csv")
if os.path.exists(_h7p):
    h7t = pd.read_csv(_h7p)
    _alg7 = ["Max-Min", "GA+CXM+seed", "(1+1)-EA+CXM", "(1+1)-EA+CXM+seed", "P-MRFO+CXM", "P-MRFO+CXM+seed", "QI-MRFO+CXM", "QI-MRFO+CXM+seed"]
    print("committed H7 results: mean gap to the preemptive LB (%)")
    display((h7t.pivot_table(index="family", columns="algo", values="gap2", aggfunc="mean")[_alg7] * 100).round(3))
    for _a, _b in [("QI-MRFO+CXM", "(1+1)-EA+CXM"), ("QI-MRFO+CXM+seed", "QI-MRFO+CXM")]:
        _w = h7t[h7t.algo.isin([_a, _b])].groupby(["family", "inst_seed", "algo"]).gap2.mean().unstack("algo")
        _d = 100 * (_w[_a] - _w[_b]).values
        print(f"{_a} - {_b}: mean {_d.mean():.3f} pp, CI {np.round(boot_ci(_d), 3)}, Wilcoxon p = {stats.wilcoxon(_d).pvalue:.2e}, {_a} better on {(_d < 0).sum()}/{len(_d)}")
else:
    print("results/h7_test/records.csv not found (run `python exp_h7_swarm_seed.py tune test analyze` in the repository)")
""")
md(r"""
### 19.2 H7: the swarm vs a (1+1)-EA with the same moves, and Max-Min seeding (`results/h7_analysis.md`)

* **Pre-registered primary H7a failed.** The (1+1)-EA with identical moves beats QI-MRFO+CXM on 58/80 fresh instances,
  and no family favours the swarm. For static makespan the exchange measurement, not the register swarm, carries the
  gain.
* **Seeding (H7b) confirmed.** A Max-Min basis state fixes the big-task plateau (3.11 % → 0.02 %) and harms nothing.
* **Best static method tested.** Max-Min seed + (1+1)-EA with CXM moves (mean rank 2.70 of 8).
* **What remains for the swarm.** Its case is re-optimisation under change (Section 20).
""")

# ----------------------------------------------------------------------------------------------------- S20 (V5 dynamic)
md(r"""
## SECTION 20 — V5: re-optimisation under change with migration cost (hypothesis H6)

Section 17h compared strategies by the makespan after each change. A running cloud also pays for every task that the
new schedule **migrates** away from the previous deployed one. V5 therefore counts *voluntary migrations*: persistent
tasks whose VM survived but that the new schedule moves. Replaced tasks and tasks of a failed VM are excluded.
`qi_dynamic.run_dynamic` gains four things:
* optimizer kwargs, so CXM can be used under change;
* **elite carry-over**: the previous best schedule, repaired for the change, seeds the register swarm (fixing audit risk
  R4: the GA always carried its elite, QI-MRFO did not);
* greedy repair of the tasks of a failed VM;
* two heuristic competitors: **Max-Min recomputed every epoch** (unlimited migration) and an **incremental list
  heuristic** (zero voluntary migration).

The pre-registered design is `research_plan_v5.md` §11. The committed run is `results/h6_dynamic/` with its analysis
in `results/h6_analysis.md`. The cells below run a small demonstration sized by `QI_MODE` and print the committed
results when present.
""")
code(r"""
# small held-out dynamic demonstration (instance seed 101): post-change gap, recovery AUC and voluntary migrations
DYN5 = {"Max-Min (recompute)": dict(algo="Max-Min"), "Incremental (no migration)": dict(algo="Incremental"),
        "GA+CXM continue": dict(algo="GA", strategy="continue", repair="greedy", algo_kw={"exchange": 1.0}),
        "QI-MRFO continue": dict(algo="QI-MRFO", strategy="continue_struct", repair="greedy"),
        "QI-MRFO+CXM continue+elite": dict(algo="QI-MRFO", strategy="continue_struct", repair="greedy", carry_elite=True, algo_kw={"exchange": 1.0})}
_dyn_n, _dyn_changes = (60, ["mixed"]) if MODE == "smoke" else (100, ["churn", "drift", "mixed"])
rows5 = []
for ch in _dyn_changes:
    seq5 = make_dynamic_sequence(_dyn_n, 10, seed=101, K=4, change=ch)
    for name, spec5 in DYN5.items():
        kw = dict(spec5)                                  # copy: the specs are reused for every change type
        o = run_dynamic(seq5, kw.pop("algo"), kw.pop("strategy", "continue_struct"), CFG["dyn_budget0"], CFG["dyn_budget"], seed=101,
                        P=CFG["P"], decoherence_c=CFG["gamma_c_mrfo"], **kw)
        post = o[1:]
        rows5.append({"change": ch, "strategy": name, "post_gap_%": 100 * np.mean([x["gap"] for x in post]),
                      "auc_%": 100 * np.mean([x["auc_gap"] for x in post]), "migrations/epoch": np.mean([x["migrations"] for x in post])})
pd.DataFrame(rows5).round(3)
""")
code(r"""
_h6p = os.path.join("results", "h6_dynamic", "records.csv")
if os.path.exists(_h6p):
    h6 = pd.read_csv(_h6p)
    for metric, lab, sc in [("post_gap", "post-change gap (%)", 100), ("post_auc", "recovery AUC (%)", 100), ("migrations", "voluntary migrations per epoch", 1)]:
        print(f"committed H6 results — {lab}:")
        display((h6.pivot_table(index="scenario", columns="algo", values=metric, aggfunc="mean") * sc).round(3))
else:
    print("results/h6_dynamic/records.csv not found (run `python exp_h6_dynamic.py run analyze` in the repository)")
""")
md(r"""
### 20.1 What the committed H6 run showed (`results/h6_analysis.md`; the printout above is authoritative)

* **CXM under change (H6a, primary) confirmed.** The post-change gap drops by 2.98 pp on 60/60 scenario-seed pairs.
* **Elite carry-over (H6b) rejected as a default.** It helps after churn and VM failure but hurts after VM addition:
  the carried schedule leaves the new VM empty and becomes the attractor, and an exchange cannot fill an empty VM.
* **Against recomputing Max-Min every epoch (H6d).** The carried-state swarm with CXM reaches a lower gap (−0.33 pp,
  48/60) with 41 % fewer voluntary migrations. The exception is heavy-tailed n = 200, where Max-Min is better.
* **Against the GA.** Carried-state QI-MRFO+CXM beats GA+CXM on 60/60, and CXM makes the GA worse under change.
* **Quantum-specific part.** The classical linear twin is again better than the Born rule (55/60).
* **Open cost.** CXM triples migrations, because the objective ignores them. A migration-aware objective is the next
  hypothesis.
""")

code(r"""
# committed migration-priced runs: H8 (seeds 201-210), H10 elite anchor (301-310), H11 event-aware elite (401-410)
for _exp, _lab in [("h8_migration", "H8"), ("h10_elite_migration", "H10"), ("h11_event_elite", "H11")]:
    _p = os.path.join("results", _exp, "records.csv")
    if not os.path.exists(_p):
        print(f"{_p} not found (run the corresponding exp_*.py in the repository)"); continue
    _d = pd.read_csv(_p)
    print(f"{_lab}: pooled post-change cost gap (%), makespan gap (%) and voluntary migrations per epoch")
    display((_d.groupby(["mig_lambda", "algo"])[["post_cost_gap", "post_gap"]].mean() * 100).round(3).join(
        _d.groupby(["mig_lambda", "algo"])[["migrations"]].mean().round(1)))
""")
md(r"""
### 20.2 H8: migrations priced (`results/h8_analysis.md`)

* **Setup.** After each change every method optimises makespan × (1 + λ · migrations / eligible tasks).
* **Against the best heuristic chooser.** The carried-state swarm with CXM wins pooled at λ = 0.2 and λ = 1.0 but not
  at λ = 0.05. The effect depends on the change type: the swarm wins where change calls for coordinated
  reconfiguration (drift, mixed events, VM addition) and loses where zero-migration repair is near-optimal (churn, VM
  failure).
* **Against the (1+1)-EA with the same moves.** It cannot recover from VM additions: every single-task move onto the
  new VM is uphill under the price. The register swarm's uniform-share rule for new VMs produces multi-task moves that
  escape.
* **What H10 tests next.** Anchoring the swarm on the deployed schedule (the elite) for local changes.
""")
md(r"""
### 20.3 H9–H11 (`results/h9_analysis.md`, `h10_analysis.md`, `h11_analysis.md`)

* **H9: purity-regulated decoherence (the original report's §21 proposal) is falsified.** It raises duplicate
  evaluations (27 % → 46 %) and worsens the gap. Mean purity is dominated by a few diffuse registers, so the controller
  lowers γ exactly where the collapsed registers needed it.
* **H10: an unconditional elite is rejected.** It wins every churn and VM-failure pair but loses badly after VM
  additions, where the carried schedule leaves the new VM empty and anchors the swarm away from it.
* **H11: the event-aware elite (none after a VM addition) is confirmed on fresh seeds at every λ.** It beats the best
  heuristic chooser at every migration price. The remaining boundary is pure churn at λ ≥ 0.2, where zero-migration
  repair is best.
""")

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
      "language_info": {"name": "python", "version": "3.12"}}, "nbformat": 4, "nbformat_minor": 5}
for c in nb["cells"]:
    c["source"] = c["source"]  # nbformat accepts a single string
for fname in ("quantum_inspired_cloud_scheduler.ipynb", "quantum_inspired_MRFO_cloud_scheduler.ipynb"):   # identical copies
    out = os.path.join(HERE, fname)
    json.dump(nb, open(out, "w", encoding="utf-8"), indent=1)
    print("wrote", out, "with", len(cells), "cells")
