# Quantum-Inspired MRFO / DMO for Cloud Task Scheduling — code and idea

This folder is a complete, runnable research package: a Jupyter notebook that implements classical swarm schedulers (PSO, DMO, MRFO), a quantum-inspired version of them, and the whole experimental loop (baseline, convergence, statistics, ablation, sensitivity, adversarial cases, dynamic workloads). Everything runs on an ordinary CPU with NumPy/SciPy. **No quantum hardware, no quantum circuits.**

## Files

| File | What it is |
|---|---|
| `quantum_inspired_cloud_scheduler.ipynb` | The notebook (18 sections, runs top to bottom in Colab, Jupyter or local Python). Built by `build_notebook.py` from the modules below, so notebook and modules are identical code. `quantum_inspired_MRFO_cloud_scheduler.ipynb` is an identical copy under the algorithm-specific name. |
| `quantum_inspired_cloud_scheduler_executed_fast.ipynb` | The same notebook with outputs, executed in Docker in `fast` mode (3 seeds); `results/executed_smoke.ipynb` and `results/executed_full.ipynb` (30 seeds) are the other executed copies. The executed copies predate the last rebuild, which only added the Section 17c neutral-acceptance test cell (`accept_equal` flag of `run_qimrfo`). |
| `quantum_inspired_research_report.md` (+ `.pdf`) | The research report: literature, hypothesis, mathematics, measured results, ablation, failure analysis, contribution, two-year plan. |
| `phd_research_proposal.md` | The PhD proposal in the requested (Buyya-style) format. |
| `qi_core.py` | Problem model, instance generator, objective, instrumentation, heuristics, classical PSO / DMO / MRFO / GA / random. |
| `qi_quantum.py` | The quantum-inspired mechanism (registers, Born measurement, projection, depolarising channel, purity) and QI-DMO / QI-MRFO. |
| `qi_dynamic.py` | Dynamic-workload harness (task churn, VM failure, VM addition, speed drift; restart / continue / decoherence-shock / hypermutation strategies). |
| `build_notebook.py` | Assembles the notebook from the modules (`# %% S<k>` markers) plus the experiment cells. |
| `observe_v0.py … observe_v3.py`, `observe_dyn*.py` | The pilot scripts of the research loop (V0 observe → V1 → V2 → V3 → dynamic), exactly as run; their outputs are in `results/*.txt`. |
| `lab_log.md` | The Senku-style lab log: what happened, why, evidence, alternative explanation, next change — for every version. |
| `literature/` | Live-web literature maps (QPSO, DMO, MRFO, quantum-inspired cloud scheduling and classical equivalents, prior-art recheck, Australian supervisors + RTP). |
| `docker/Dockerfile` | Reproducible environment (python 3.12 + numpy/scipy/matplotlib/pandas/nbconvert/mealpy). |
| `results/` | CSV/PKL/PNG outputs of the notebook runs and the pilot logs. **Raw results are immutable**: V5 experiments write to their own write-once directories (`results/<experiment>/` with `jobs.json`, `meta.json` incl. git commit, a JSONL checkpoint, `records.csv`, `DONE`), and a notebook re-run never overwrites committed files (it writes to `results/rerun_<mode>_<timestamp>/` unless `QI_RESULTS_DIR` is set). |
| `research_plan_v5.md` | V5 audit (risks with file/function citations), profile, observations O1–O4, ranked backlog, and the pre-registered hypothesis H5 with its acceptance criteria. It was written and committed before H5 was run; its §9 amendment was committed before the held-out stage. |
| `qi_experiment.py` | V5 harness: development (TUNE) vs held-out (TEST) instance families, JSON algorithm specs, checkpointed parallel runner for static and dynamic jobs, paired statistics (bootstrap CI, Wilcoxon, rank-biserial, Cliff's δ, A12, Holm). |
| `exp_h5_cxm.py` … `exp_h13_event_gamma.py` | The V5 experiments H5–H13: each script pre-registered in `research_plan_v5.md`, writes a write-once `results/<name>/` directory, and produces `results/h*_analysis.md`. |
| `make_v5_figures.py` | V5 figures (`results/fig_v5_*.png`) drawn from the committed result files. |
| `observe_v5_*.py` | V5 observation scripts (development seeds, descriptive). They cover duplicate evaluations, the critical-VM condition, stagnation, local optimality of end points, the H8 barrier check (post hoc) and the static decoherence dose-response with and without CXM (`analyze_v5_c_sweep.py` writes the paired contrasts). They also cover the carried elite after churn (origin of H12), the decoherence dose-response under change (origin of H13) and a Max-Min recompute as the elite (not pursued). |
| `tests/` | `pytest` suite: objective, registers, measurement, channel, dynamic structural rules, determinism, budget accounting, harness, notebook/module synchronisation, and bit-exact golden fingerprints of the V0–V4 code. |
| `requirements.txt` | Pinned environment (same versions as `docker/Dockerfile`). |

## How to run

**Colab / Jupyter:** open `quantum_inspired_cloud_scheduler.ipynb` and *Run all*. Section 1 installs anything missing. The run size is controlled by the environment variable `QI_MODE` read in Section 2:

| `QI_MODE` | seeds | budget (evaluations) | instances | approximate time |
|---|---|---|---|---|
| `smoke` | 2 | 6 000 | 2 | ≈ 5 min |
| `fast` (default) | 3 | 15 000 | 4 | ≈ 30–60 min on 2 cores (Colab), ≈ 5 min on 18 cores |
| `full` | 30 | 20 000 | 7 (up to n=200, m=20) | ≈ 1.5–3 h on 18 cores |

In Colab: `import os; os.environ["QI_MODE"] = "smoke"` in a cell *before* Section 2, or leave the default.

**Docker (exactly what was used here):**

```bash
docker build -t qi-sched docker/
docker run --rm -v "$PWD:/work" -e QI_MODE=fast qi-sched jupyter nbconvert --to notebook --execute quantum_inspired_cloud_scheduler.ipynb --output results/executed_fast.ipynb --ExecutePreprocessor.timeout=36000
```

**Tests:** `pip install -r requirements.txt && pytest` (about 30 s). The golden test fails if a change alters the behaviour of any V0–V4 configuration; new behaviour must be opt-in.

**V5 experiments (held-out protocol):** `python exp_h5_cxm.py tune`, then `test`, then `analyze` (≈ 3 + 15 min on 4 cores). Set `QI_WORKERS` to the number of processes. A finished experiment directory cannot be overwritten; resume an interrupted one by re-running the same command.

**Plain Python:** `python observe_v1.py` etc. reproduce the pilot tables in `lab_log.md`; the modules can be imported directly:

```python
from qi_core import make_instance, Objective, run_mrfo, run_ga
from qi_quantum import run_qimrfo
inst = make_instance(100, 10, seed=1)            # 100 tasks, 10 heterogeneous VMs
r = run_qimrfo(inst, Objective(inst), budget=20000, P=30, seed=0, decoherence=1.0 / inst.n)
print(r["best_f"], inst.lower_bound())
```

## The problem

Independent tasks (cloudlets) with lengths $L_i$ (MI) on heterogeneous VMs with speeds $S_j$ (MIPS): $ET_{ij} = L_i/S_j$. A schedule is an integer vector $a$ (task → VM). Objective: makespan $\max_j \sum_{i:a_i=j} ET_{ij}$ (optionally a weighted makespan + energy objective with a linear power model). The lower bound $\max(\sum L / \sum S, \max L / \max S)$ turns every result into a *gap*. The problem is the standard CloudSim-style setting used by most metaheuristic cloud-scheduling papers.

## The idea in one paragraph

Swarm schedulers (PSO, DMO, MRFO) are continuous algorithms; cloud papers apply them by rounding a continuous position to a VM index. The pilot measurement (`observe_v0.py`) shows what this costs: a DMO or MRFO move changes about *half* of all task assignments per candidate, so fewer than 2 % of candidates improve and both algorithms perform at random-search level for 50–100 tasks — the encoding gives them no controllable move size. The quantum-inspired version replaces the position by one **probability-amplitude register per task** (a unit vector over the VMs); a schedule is obtained by **measurement** (Born rule, probability = amplitude²); the host algorithm's equations act on the amplitudes unchanged; the best-known schedules enter as **basis states**; and a **depolarising channel** (decoherence) with strength $\gamma = c/n$ keeps the registers from collapsing completely. The expected number of tasks changed by a measurement is $n - \sum_t \text{purity}_t$, so move size becomes a smooth, self-adapting property of the state. The classical twin (`mode='linear'`: probability vectors with linear mixing) is kept for the ablation.

## What was found (pilot, 5 seeds, 20 000 evaluations; details in `lab_log.md` and the report)

* Classical MRFO/DMO with rounding: gap to lower bound 76–99 % at n=100 (random search: 92 %); discrete GA: 1.4 %.
* QI-MRFO with decoherence c≈1: 1.0 % gap at n=100; ties or beats the GA on all four pilot instances; QI-DMO with c≈0.25: 1.6–16 %; with DMO's unconditional step made greedy, QI-DMO matches QI-MRFO.
* Decoherence shows a dose–response: none → 25–75 % of evaluations wasted on re-measuring the same schedule; c≈0.25–1 optimal; c ≥ 2 degrades monotonically.
* The classical linear-probability twin and unsigned amplitudes perform the same as the Born-rule version: the benefit is the representation (superposition + measurement + decoherence floor), not interference or amplitude squaring.
* Using the alpha's superposition instead of its measured schedule as attractor destroys the search: collapse-conditioned attraction is essential.
* Dynamic workloads: carrying the register state beats restarting on every change type (recovery AUC 2–4× lower) and beats the GA on VM drift/failure/addition, thanks to clean structural rules (column deletion = projective measurement, uniform share for new VMs, uniform registers for new tasks). The decoherence *shock* ("controlled forgetting") does **not** beat plain continuation at any churn severity tested (10–80 %): a negative result with a boundary.
* The 30-seed run (7 instances, 2 100 runs) confirms the encoding effect with p < 10⁻⁴ and Cliff's δ ≈ −1 on every instance, confirms that the Born rule adds nothing over the linear twin, softens "beats the GA" to "GA-class (significantly better on one instance)", and shows that the Max-Min list heuristic beats QI-MRFO on 6 of 7 static instances by 0.3–4.7 percentage points: the practical case for the population method is additive/multi-objective objectives and re-optimisation under change, not static makespan batches.

## What V5 found (held-out protocol; `research_plan_v5.md`, `lab_log.md` V5, report §27–§37)

**In one paragraph.** V5 diagnosed a second representation problem: the product-state measurement cannot produce the
correlated two-task exchange that relocation-optimal schedules need. Adding it (critical exchange measurement) gave the
largest gains of the project, static and dynamic. V5's own controls then narrowed the claims:
* a (1+1)-EA with the same moves is at least as good for static makespan;
* the Born rule is slightly worse than its classical twin;
* the purity-regulated decoherence controller and the unconditional elite are falsified.

What survives, measured on fresh seeds, is specific to the register representation. Under migration-priced
re-optimisation its structural rule for new capacity produces coordinated moves that local search cannot, and with an
event-aware elite the swarm beats the best heuristic chooser at every migration price tested. An elite repaired by
list scheduling (H12) turns its last losing case, pure churn, into a win at λ ≤ 0.2. Removing the noise floor after
local changes (H13) adds a further gain, and the final configuration wins at every λ on fresh seeds. Figures:
`results/fig_v5_*.png`.

* **Observation.** QI-MRFO stalls at schedules that are *relocation-optimal* but leave 1–50 improving two-task swaps
  unused. Its product-state measurement changes tasks independently and almost never produces the correlated exchange
  such a schedule needs. A third to a half of its evaluations were also re-evaluations of known schedules.
* **Critical exchange measurement (CXM, `run_qimrfo(exchange=1.0)`).**
  * *Mechanism.* A measured candidate additionally swaps a task on its critical VM with a shorter task elsewhere, and
    the two registers collapse onto the outcome.
  * *Held-out result.* 80 new instances across 8 new families, with p_x chosen only on the pilot instances.
    Gap to the preemptive bound: **3.40 % → 0.54 %**, better on 76/80 instances (p < 1e-4, 7/8 families
    Holm-significant, none worse).
  * *Against Max-Min.* QI-MRFO+CXM now **beats Max-Min on 6 of 8 held-out families** (unchanged QI-MRFO: Max-Min wins
    73/80 instances).
  * *Against the GA.* Given the same operator, the GA improves by only 0.81 pp and loses to QI-MRFO+CXM on 73/80
    instances.
* **Still no quantum advantage.** Under CXM the classical linear-probability twin is slightly but significantly
  *better* than the Born-rule version (68/80 instances). The best algorithm tested is the classical twin with CXM
  (mean rank 1.57 of 9).
* **New boundary.** On near-homogeneous VMs with a dominant task (n100 m20 lognormal/low), Max-Min is provably optimal:
  it attains the lower bound on all 10 instances. The swarm is stuck on a makespan-neutral plateau, the same failure
  mode as the identical-task case.
* **Is the swarm needed? (H7, fresh instances 201–210).** A (1+1)-EA with exactly the same moves
  (`run_one_plus_one`) beats QI-MRFO+CXM on 58/80 instances.
  * For **static** makespan the gain belongs to the exchange measurement, not to the register swarm.
  * Max-Min seeding fixes the plateau failure and improves every configuration.
  * The best static method tested is Max-Min seed + (1+1)-EA with CXM moves.
* **Under change (H6).** 6 held-out dynamic scenarios, 600 runs, migrations counted.
  * CXM lowers the post-change gap on 60/60 scenario-seed pairs.
  * The carried-state swarm with CXM has a lower gap than recomputing Max-Min after every change, with 41 % fewer
    task migrations. The exception is heavy-tailed n = 200.
  * Carrying the previous best schedule helps after churn and VM failure but hurts after VM addition, so it is not a
    default.
  * CXM triples migrations relative to the plain swarm, so migration cost has to enter the objective (next step).
* **Migrations priced (H8; λ ∈ {0.05, 0.2, 1.0}, fresh seeds).** Once each migration costs makespan-equivalent
  time, no single method dominates.
  * The swarm beats the best heuristic chooser at λ = 0.2 and λ = 1.0 (pooled). It wins on drift, mixed events and VM
    addition, and loses on churn and VM failure, where zero-migration repair is near-optimal.
  * A (1+1)-EA with the same moves is stuck after VM additions: every single-task move is uphill under the price. The
    swarm's VM-addition rule produces multi-task moves that escape. This is the first measured advantage of the
    register representation over a (1+1)-EA with identical moves.
* **Elite anchor under migration pricing (H10, fresh seeds 301–310).** Carrying the deployed schedule is change-type
  dependent.
  * It wins 10/10 after churn and VM failure at every λ.
  * It loses badly after VM addition, where it suppresses the swarm's escape onto the new VM. This is the same
    mechanism as H6b, seen a second time.
  * Pooled it is rejected, which motivates the event-aware rule tested in H11.
* **Feedback-controlled decoherence (H9, fresh seeds 301–310).** The purity-regulated γ proposed in the original
  report (§21) is falsified, with and without CXM. It *raises* duplicate evaluations (27 % → 46 %) and worsens the
  gap, because mean purity is dominated by a few diffuse registers, so the controller starves the collapsed registers
  that cause duplicates. Fixed c = 1 stays the default.
* **Event-aware elite (H11, fresh seeds 401–410).** Carrying the deployed schedule after every event *except* a VM
  addition works at every λ.
  * It beats the no-elite swarm (−0.41 / −0.78 / −2.19 pp) and the always-elite swarm.
  * It **beats the best heuristic chooser at every migration price** (−0.83 / −2.27 / −12.7 pp).
  * Remaining boundary: pure churn at λ ≥ 0.2, where zero-migration repair is best. H12 addresses it.
* **Incremental elite (H12, fresh seeds 501–510).** After churn the carried elite used to leave each new task on the
  VM of the task it replaced, starting 18–38 % above the bound. It now places new tasks by list scheduling.
  * **Against the H11 swarm.** Better at λ = 0.2 and λ = 1.0: −1.18 and −2.84 pp; 29/0 and 28/1.
  * **At λ = 0.05, not retained.** It wins 26/3, but the CI of the mean includes 0.
  * **Against the Chooser.** Better at every λ: −0.90 / −3.08 / −14.17 pp. It now also wins pure churn at
    λ ≤ 0.2.
  * **Against incremental repair + a (1+1)-EA with the same moves.** The swarm wins only through VM additions,
    its one unique mechanism.
* **Event-aware decoherence (H13, fresh seeds 601–610).** Under a migration price, the noise floor's random re-draws
  are paid migrations, and CXM already supplies the targeted moves. H13 removes the floor after local changes
  (churn, drift, VM failure) on top of H12.
  * **Against c = 1.** Better at λ = 0.2 and λ = 1.0: −0.26 and −0.93 pp; 34/16 and 41/9. Not at λ = 0.05, where the
    CI includes 0.
  * **The VM-addition exception (H13b).** Keeping c = 1 after VM additions made no difference, so that part is
    falsified.
  * **Against the Chooser.** The final configuration beats it at every λ on fresh seeds: −1.26 / −3.62 / −18.34 pp;
    58/2, 57/3 and 59/1. Pure churn is won at every λ.
  * **Recommended configuration for migration-priced re-optimisation (λ ≥ 0.2; H12 and H13 retained there):**
    `run_dynamic(..., "QI-MRFO", "continue_struct", algo_kw={"exchange": 1.0}, carry_elite="except_vm_add", repair="incremental", decoherence_by_event={"churn": 0, "drift": 0, "vm_fail": 0}, mig_lambda=λ)`.
    At λ = 0.05 neither refinement met the pre-registered bar (rank tests only). Every swarm variant beats the
    Chooser there.
* **The decoherence floor once CXM exists (descriptive, development set; report §35).**
  * Without CXM, removing the floor (c = 0) multiplies the gap by 2.6–4.3.
  * With CXM, the gap is flat for c ∈ [0, 2]: the exchange move takes over the floor's job.
  * c then only sets duplicate evaluations (29 % → 7 % → 0.1 % at c = 0 / 1 / 4), so adaptive decoherence has
    little static headroom. An evaluation cache is the better lever (UNMEASURED).
* **Research quality.**
  * 253 tests, including bit-exact golden fingerprints of the V0–V4 code.
  * Development/held-out split with instance-level statistics.
  * A tighter (preemptive) lower bound.
  * Write-once checkpointed experiments with commit hashes.
  * A pre-registration committed before each run.
  * Deterministic, synchronised notebook builds.

## Notebook sections

1 Environment · 2 Imports/config · 3 Seeds · 4 Problem representation · 5 Task/VM generation · 6 Objective · 7 Classical PSO/DMO/MRFO (+GA, heuristics) · 8 Quantum-inspired mechanism (math + demo) · 9 QI-MRFO / QI-DMO · 10 Validation tests · 11 Smoke · 12 Baseline · 13 Convergence/diversity/purity/move-size plots · 14 Statistics (Wilcoxon + Holm, Cliff's δ, A12, bootstrap CI, Friedman) · 15 Ablation · 16 Sensitivity (γ dose–response, P, S) · 17 Failure cases (tiny, m=2, trivial landscape, energy objective, many VMs, tall barriers, overhead, dynamic workloads) · 18 Interpretation · 19 V5: evaluation diagnostics and critical exchange measurement (held-out demo + committed results) · 20 V5: re-optimisation under change with migration counts (demo + committed H6 results).

## Honesty rules used throughout

Every number in the report was produced by the code in this folder; the notebook prints its own numbers when executed. Anything not measured is labelled UNMEASURED; illustrative numbers are labelled HYPOTHETICAL. Default parameters (c=1 for MRFO, c=0.25 for DMO) were chosen from the pilot sweep on the same instance family; the `full` mode adds held-out instance shapes (n=200 m=20, lognormal tasks, low heterogeneity).
