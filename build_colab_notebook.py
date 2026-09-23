"""
build_colab_notebook.py - assembles QI_MRFO_DMO_Colab.ipynb: ONE self-contained, commented notebook for Google Colab.

The algorithm cells are copied verbatim from the tested modules (qi_core.py, qi_quantum.py, qi_dynamic.py), so the notebook
runs exactly the code covered by tests/. The experiment cells reproduce the reported studies (Experiment A = V4 baseline,
B = H5 held-out swap-move test, C = the 500-5000 task scaling study, D = H6c and H13 changing-cloud tests) and save every
finished run to a Google Drive folder, so an interrupted Colab session can be resumed.
Run:  python build_colab_notebook.py
"""
import json, os, re, textwrap, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "QI_MRFO_DMO_Colab.ipynb")


def slice_module(path):
    """Split a module on '# %% <tag>' markers -> {tag: code}; the header before the first marker is dropped."""
    txt = open(os.path.join(HERE, path), encoding="utf-8").read()
    parts = re.split(r"^# %% (.+)$", txt, flags=re.M)
    return {parts[i].strip(): parts[i + 1].strip("\n") + "\n" for i in range(1, len(parts), 2)}


core, quant, dyn = slice_module("qi_core.py"), slice_module("qi_quantum.py"), slice_module("qi_dynamic.py")
cells = []


def _cid(text):
    return hashlib.sha1(f"{len(cells)}:{text}".encode("utf-8")).hexdigest()[:8]


def md(text):
    cells.append({"cell_type": "markdown", "id": _cid(text), "metadata": {}, "source": textwrap.dedent(text).strip("\n")})


def code(text):
    cells.append({"cell_type": "code", "id": _cid(text), "metadata": {}, "execution_count": None, "outputs": [],
                  "source": textwrap.dedent(text).strip("\n")})


def embed(header, *sections):
    """A code cell holding module sections verbatim, preceded by a comment header."""
    code("\n".join(header) + "\n\n" + "\n".join(s.rstrip("\n") + "\n" for s in sections))


# =========================================================================================================== title
md(r"""
# Quantum-Inspired MRFO and DMO for Cloud Task Scheduling
### Complete, runnable notebook for Google Colab: all algorithms, all experiments, results saved to Google Drive

**What is inside**
* **All algorithms**, copied unchanged from the project's tested code:
  * the cloud scheduling problem;
  * the Max-Min / Min-Min heuristics;
  * the classical optimizers: DMO, MRFO, PSO, a genetic algorithm (GA), a (1+1)-EA and random search;
  * the **quantum-inspired** QI-DMO and QI-MRFO;
  * the **swap move** for the busiest VM;
  * a simulator of a **changing cloud** (tasks arriving and leaving, VMs failing or being added, speed drift, migration cost).
* **Four experiments** behind the reported results:
  * **A.** Original DMO / MRFO vs quantum-inspired QI-DMO / QI-MRFO, GA, PSO and heuristics (7 problems).
  * **B.** The swap move on 80 unseen problems (8 problem types × 10 problems).
  * **C.** Scaling to 500, 1 000, 1 500, 2 000 and 5 000 tasks on 50 VMs.
  * **D.** Changing cloud: QI-MRFO vs GA, and QI-MRFO vs the best heuristic when moving a running task has a cost.
* **Saving to Google Drive.** Every finished run is written to a folder in your Google Drive at once. Tables go into CSV
  files and an Excel workbook, figures into PNG files, and a short text summary is written at the end.

**How to run in Google Colab**
1. Open this notebook in Colab (*File → Upload notebook*, or double-click it in Google Drive).
2. Optionally edit the **SETTINGS** cell in Section 1.
   * `MODE = "quick"` is a fast check. It runs a subset of the reported runs with the same settings.
   * `MODE = "full"` runs everything behind the reported results.
3. Click *Runtime → Run all*. When Colab asks, allow access to Google Drive.
4. Results appear in **My Drive → `QI_MRFO_DMO_results` → `<mode>_run`**.

**Run time.** Free Colab has 2 CPU cores, so the notebook runs 2 runs at a time there.
* **Quick mode:** 5.4 minutes measured with 2 processes on a 2.1 GHz Xeon; expect about 5–15 minutes on Colab.
* **Full mode:** about 5 CPU-hours in total (measured: A 0.5 h, B 0.7 h, C 3.4 h, D 0.8 h). With 2 processes on free
  Colab, expect roughly 3–5 hours; Experiment C (up to 5 000 tasks) is most of it.
* **Keep the browser tab open.** Free Colab stops idle sessions. If it disconnects, reconnect and click *Run all* again:
  finished runs are read back from Google Drive and skipped.

**About "quantum-inspired".** Everything runs on an ordinary CPU; no quantum computer is used.
* **The idea.** Each task keeps a probability for every VM, which is the quantum-inspired idea of a *superposition*. A
  schedule is obtained by sampling these probabilities, called *measurement*. A small noise level, *decoherence*, stops the
  search from freezing.
* **What the project found.** The benefit comes from this representation. A classical-probability version, without the
  quantum formula, works as well. No quantum advantage is claimed.

**Units.** Task lengths are in MI (million instructions) and VM speeds in MIPS, so times (makespan) are in **seconds**.
The *gap* is how much later a schedule finishes than the theoretical minimum (the lower bound), in %.
""")

# =========================================================================================================== settings
md(r"""
## Section 1 — Settings
This is the only cell you normally need to change.
""")
code(r"""
# =====================================================================================================
# SECTION 1 - SETTINGS (the only cell you normally need to edit)
# =====================================================================================================

# MODE sets how big the experiments are:
#   "quick" : a SUBSET of the full experiments with the same settings (fewer problems and runs; 500 and 1000 tasks
#             only in Experiment C). Every quick run is identical to the same run in full mode, but the averages and
#             tests use far fewer runs than the reported results. Use it first to check that everything works.
#   "full"  : exactly the settings behind the reported results. It takes several hours on free Colab, but every
#             finished run is saved to Google Drive, so an interrupted session can simply be resumed.
MODE = "quick"

# Which experiments to run (True = run, False = skip)
RUN_EXPERIMENT_A = True   # A: original DMO/MRFO vs quantum-inspired QI-DMO/QI-MRFO, GA, PSO, heuristics (7 problems)
RUN_EXPERIMENT_B = True   # B: the swap move on 80 unseen problems (8 problem types x 10 problems)
RUN_EXPERIMENT_C = True   # C: scaling to 500, 1000, 1500, 2000 and 5000 tasks on 50 VMs
RUN_EXPERIMENT_D = True   # D: changing cloud (vs GA, and with a cost for moving running tasks)

# Where to save the results
SAVE_TO_GOOGLE_DRIVE = True                 # False: save only inside this Colab session (lost when it ends)
DRIVE_FOLDER_NAME = "QI_MRFO_DMO_results"   # this folder is created inside "My Drive"
RUN_NAME = None                             # None -> "<MODE>_run"; give a new name (e.g. "full_run_2") for a fresh folder

# Number of runs executed in parallel. None = use every CPU core (free Colab has 2).
N_WORKERS = None
""")

# =========================================================================================================== setup
md(r"""
## Section 2 — Setup: packages, Google Drive and the results folder
* Colab already has every package this notebook needs (NumPy, SciPy, pandas, Matplotlib); anything missing is installed.
* **Google Drive.** It is mounted, and the results folder is created, e.g. `My Drive/QI_MRFO_DMO_results/quick_run`.
* **Running outside Colab.** The results go to a local folder with the same name.
""")
code(r"""
# =====================================================================================================
# SECTION 2 - SETUP: packages, Google Drive, results folder
# =====================================================================================================
import sys, os, time, json, platform, subprocess
import importlib.util
import multiprocessing as mp

# Install a package only if it is missing (on Colab nothing needs installing)
for pkg in ["numpy", "scipy", "pandas", "matplotlib"]:
    if importlib.util.find_spec(pkg) is None:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])

import numpy as np
import scipy
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from IPython.display import display

IN_COLAB = "google.colab" in sys.modules      # True when this notebook runs inside Google Colab

# ---- Google Drive: mount it and choose the base folder for all results --------------------------
if SAVE_TO_GOOGLE_DRIVE and IN_COLAB:
    from google.colab import drive
    drive.mount("/content/drive")                         # Colab asks for permission the first time
    BASE_DIR = os.path.join("/content/drive/MyDrive", DRIVE_FOLDER_NAME)
else:
    if SAVE_TO_GOOGLE_DRIVE:
        print("Not running in Google Colab: results are saved to a local folder instead of Google Drive.")
    BASE_DIR = os.path.abspath(DRIVE_FOLDER_NAME)

# ---- One sub-folder per run: re-running with the same RUN_NAME resumes it ------------------------
RUN_DIR = os.path.join(BASE_DIR, RUN_NAME or f"{MODE}_run")
os.makedirs(RUN_DIR, exist_ok=True)
N_WORKERS = N_WORKERS or os.cpu_count() or 1

print(f"Python {platform.python_version()} | numpy {np.__version__} | scipy {scipy.__version__} | "
      f"pandas {pd.__version__} | matplotlib {matplotlib.__version__}")
print(f"Running in Colab: {IN_COLAB} | CPU cores: {os.cpu_count()} | parallel workers: {N_WORKERS}")
print(f"MODE = {MODE!r}. All results of this run are saved in:\n  {RUN_DIR}")
""")

# =========================================================================================================== problem
md(r"""
## Section 3 — The cloud task scheduling problem
* **The problem.** There are $n$ independent tasks (cloudlets) with lengths $L_i$ in MI, and $m$ virtual machines with
  speeds $S_j$ in MIPS.
* **Execution time.** Task $i$ on VM $j$ takes $ET_{ij} = L_i / S_j$ seconds.
* **A schedule** assigns every task to one VM: an integer vector $a$ with $a_i \in \{0,\dots,m-1\}$.
* **Makespan.** The objective is the time at which the last VM finishes: $\max_j \sum_{i:a_i=j} ET_{ij}$. Lower is better.
* **Lower bound.** No schedule can beat $\max(\sum L / \sum S,\ \max L / \max S)$. The tighter "preemptive" bound
  `lower_bound_pmtn` is also computed. The *gap* is how far above the lower bound a schedule is, in %.
* **Energy.** A linear power model (idle and busy power per VM) gives the energy of a schedule in Wh.
* **Problem generator.** Task lengths are uniform, lognormal (heavy-tailed) or bimodal. VM speeds have high, low or no
  heterogeneity. Everything is seeded, so every run can be reproduced.

The next cell is copied unchanged from `qi_core.py`.
""")
embed(["# =====================================================================================================",
       "# SECTION 3 - PROBLEM MODEL (verbatim from qi_core.py): data classes, instance generator, objective",
       "#   CloudInstance      - tasks, VMs, execution-time matrix, lower bounds",
       "#   make_instance      - seeded random problem generator",
       "#   Objective          - makespan / energy of a schedule; counts evaluations (the budget unit)",
       "# ====================================================================================================="],
      core["S2 imports"], core["S4 problem representation"], core["S5 instance generation"], core["S6 objective"])

md(r"""
## Section 4 — Heuristics, the swap move and run instrumentation
* **Max-Min / Min-Min** are the classic list-scheduling heuristics. They are deterministic and very fast.
* **`critical_exchange` is the swap move.** It takes a task from the *busiest* VM and swaps it with a shorter task on
  another VM, or moves it if no swap helps. A one-task-at-a-time search cannot make this correlated two-task change.
* **`Tracker`** records diagnostics during a run: the best-so-far curve, diversity and duplicate evaluations. The
  experiments below switch it off, which does not change the results, to run faster.
""")
embed(["# =====================================================================================================",
       "# SECTION 4 - INSTRUMENTATION AND HEURISTICS (verbatim from qi_core.py)",
       "#   Tracker                    - run diagnostics (optional; switched off in the experiments for speed)",
       "#   max_min / min_min          - list-scheduling heuristics",
       "#   critical_exchange          - the SWAP MOVE on the busiest VM",
       "#   count_improving_moves      - how many improving single moves / swaps a schedule still has",
       "# ====================================================================================================="],
      core["S7a instrumentation"], core["S7b heuristics"])

md(r"""
## Section 5 — Classical optimizers
**Rounding encoding.** DMO, MRFO and PSO are continuous algorithms. To schedule tasks, each task's continuous position is
rounded to a VM number, as is usual in the cloud-scheduling literature.
* **Why this fails.** For DMO and MRFO, one move then changes about half of all task assignments at once (35–63 % in
  the reported baseline). That is close to drawing a new random schedule.
* **The result** is that the original DMO and MRFO perform about as well as random search, sometimes worse
  (Experiment A shows this).

**The optimizers in this cell.**
* **DMO** (Dwarf Mongoose Optimization) and **MRFO** (Manta Ray Foraging Optimization): the original algorithms with rounding.
* **PSO**: particle swarm optimization.
* **GA**: a discrete genetic algorithm, a strong standard baseline.
* **(1+1)-EA**: a simple local search that keeps one schedule and accepts only improvements. It is the honest control
  for the swap move.
* **Random search**: the floor that every method should beat.

Every optimizer gets the **same evaluation budget** (one evaluation = computing the makespan of one schedule).
""")
embed(["# =====================================================================================================",
       "# SECTION 5 - CLASSICAL OPTIMIZERS (verbatim from qi_core.py): PSO, DMO, MRFO, GA, (1+1)-EA, random search",
       "# All share the signature run_xxx(instance, objective, budget, P=population, seed=..., track=...) and return",
       "# {'best_f': best makespan, 'best_assign': best schedule, 'tracker': diagnostics, 'state': state for dynamic runs}.",
       "# ====================================================================================================="],
      core["S7c classical optimizers"])

md(r"""
## Section 6 — The quantum-inspired mechanism: QI-MRFO and QI-DMO
**Register per task.** Each task keeps a *register*: an amplitude vector with one entry per VM. Its probabilities
(amplitude² under the Born rule, or plain probabilities in the classical "linear twin") give the chance that the task goes
to each VM.

**The operations on a register.**
* **Measurement** samples a VM for every task and so gives a concrete schedule, which is then evaluated.
* **MRFO / DMO moves** act on the registers: they pull them towards the registers of good schedules. A move then
  changes far fewer tasks than with rounding: about 10–14 % of them for QI-MRFO and 22–28 % for QI-DMO in the reported
  baseline, against 35–63 % for the originals.
* **Decoherence** is a small uniform mixing, strength γ = c / n. It keeps every VM possible for every task, so the search
  cannot freeze on one schedule.
* **The swap move** (`exchange` = probability of applying it) is a correlated measurement of two tasks: it swaps a task on
  the busiest VM with a shorter task elsewhere.
* **The Max-Min seed** (optional) inserts the Max-Min schedule as a starting point.

**Settings used in all experiments.** QI-MRFO c = 1, QI-DMO c = 0.25, population 30. With the swap move, `exchange = 1`.

The next two cells are copied unchanged from `qi_quantum.py`.
""")
embed(["# =====================================================================================================",
       "# SECTION 6a - QUANTUM-INSPIRED MECHANISM (verbatim from qi_quantum.py)",
       "#   born_probs / probs      - register -> probabilities (Born rule or classical linear twin)",
       "#   measure                 - sample one schedule from the registers",
       "#   depolarise / purity     - decoherence channel and how 'collapsed' a register is",
       "#   remove/add_vm_state ... - structural rules used when the cloud changes (Section 7)",
       "#   collapse_rows           - measurement back-action used by the swap move",
       "# ====================================================================================================="],
      quant["S8 mechanism"])
embed(["# =====================================================================================================",
       "# SECTION 6b - QUANTUM-INSPIRED OPTIMIZERS (verbatim from qi_quantum.py): run_qidmo, run_qimrfo",
       "#   run_qimrfo(..., decoherence=c/n, exchange=probability of the swap move, mode='born_signed' or 'linear',",
       "#              init_state={'elite': schedule} to start from e.g. the Max-Min schedule)",
       "# ====================================================================================================="],
      quant["S9 QI algorithms"])

md(r"""
## Section 7 — Changing cloud (dynamic scheduling)
A real cloud changes while tasks run. `make_dynamic_sequence` creates a problem followed by a sequence of changes of one
of these types:
* **churn:** 20 % of the tasks finish and new tasks arrive;
* **drift:** VM speeds change;
* **vm_fail:** a VM disappears;
* **vm_add:** a VM is added;
* **mixed:** a random change each time.

**What `run_dynamic` does after each change.**
* **The heuristics** either recompute everything with Max-Min (many task moves) or repair the old schedule with zero
  moves ("Incremental"). The **Chooser** deploys the cheaper of the two.
* **The optimizers** can *continue* from their previous state instead of restarting. The quantum-inspired registers
  have simple structural rules: delete a failed VM's column, give a new VM a uniform share, give new tasks uniform
  registers.

**Migration cost.** With `mig_lambda = λ`, moving a running task to another VM costs something. The objective becomes
makespan × (1 + λ × migrations / movable tasks).

**The final QI-MRFO configuration.** It uses three options from later tests:
* `carry_elite="except_vm_add"`: start from the running schedule, except right after a VM is added;
* `repair="incremental"`: place new tasks sensibly;
* `decoherence_by_event`: no decoherence noise after small changes.

The next cell is copied unchanged from `qi_dynamic.py`.
""")
embed(["# =====================================================================================================",
       "# SECTION 7 - CHANGING-CLOUD SIMULATOR (verbatim from qi_dynamic.py)",
       "#   make_dynamic_sequence  - a problem followed by K changes (churn / drift / vm_fail / vm_add / mixed)",
       "#   incremental_list_schedule, repair_schedule, count_migrations - repair rules and migration counting",
       "#   run_dynamic            - re-optimise after every change and report makespan, migrations and cost per change",
       "# ====================================================================================================="],
      dyn["S17 dynamic harness"])

# =========================================================================================================== helpers
md(r"""
## Section 8 — Experiment helpers
These cells define the tools the experiments use:
* the list of algorithms with their settings;
* the functions that run one static or dynamic run;
* a **runner that saves every finished run to Google Drive at once** and skips runs that are already saved (resume);
* the statistics (Mann-Whitney U, Wilcoxon signed-rank, Holm correction), table helpers and plot style.
""")
code(r"""
# =====================================================================================================
# SECTION 8a - ALGORITHMS AND THEIR SETTINGS (the same settings as in the reported studies)
# =====================================================================================================
# c        = decoherence strength of the quantum-inspired methods (gamma = c / number of tasks)
# exchange = probability of applying the swap move
# seed     = start from the Max-Min schedule
ALGORITHMS = {
    # ---- list-scheduling heuristics (deterministic: run once) --------------------------------------
    "Max-Min":                  dict(heuristic=max_min),
    "Min-Min":                  dict(heuristic=min_min),
    # ---- classical optimizers (continuous algorithms with rounding, plus GA / (1+1)-EA / random) -----
    "Random search":            dict(fn=run_random),
    "PSO":                      dict(fn=run_pso),
    "DMO":                      dict(fn=run_dmo),
    "MRFO":                     dict(fn=run_mrfo),
    "GA":                       dict(fn=run_ga),
    "GA+swap":                  dict(fn=run_ga, exchange=1.0),
    "(1+1)-EA+swap":            dict(fn=run_one_plus_one, c=1.0, exchange=0.5),
    "(1+1)-EA+swap+seed":       dict(fn=run_one_plus_one, c=1.0, exchange=0.5, seed=max_min),
    # ---- quantum-inspired optimizers ---------------------------------------------------------------
    "QI-DMO":                   dict(fn=run_qidmo, c=0.25),
    "QI-MRFO":                  dict(fn=run_qimrfo, c=1.0),
    "P-MRFO (classical twin)":  dict(fn=run_qimrfo, c=1.0, mode="linear"),     # same method without the quantum formula
    "QI-MRFO+swap":             dict(fn=run_qimrfo, c=1.0, exchange=1.0),
    "P-MRFO+swap (classical twin)": dict(fn=run_qimrfo, c=1.0, exchange=1.0, mode="linear"),
    "QI-MRFO+swap+seed":        dict(fn=run_qimrfo, c=1.0, exchange=1.0, seed=max_min),
}
POPULATION = 30          # population size of every population-based optimizer


def problem_name(n, m, dist, het):
    # e.g. "100 tasks, 10 VMs, uniform/high"
    return f"{n} tasks, {m} VMs, {dist}/{het}"


def run_static(job):
    # Run ONE algorithm once on ONE problem and return one result row (makespan in seconds, gap in %, ...).
    n, m, dist, het = job["problem"]
    inst = make_instance(n, m, seed=job["inst_seed"], task_dist=dist, hetero=het)   # same problem for every algorithm
    spec = ALGORITHMS[job["algorithm"]]
    obj = Objective(inst)                                  # counts evaluations = the budget unit
    t0 = time.time()
    if "heuristic" in spec:                                # heuristics: one deterministic schedule
        schedule = spec["heuristic"](inst)
        obj(schedule)
    else:
        kw = {k: spec[k] for k in ("exchange", "mode") if k in spec}
        if "c" in spec:
            kw["decoherence"] = spec["c"] / n              # gamma = c / n
        if "seed" in spec:                                 # start from the Max-Min schedule
            start = spec["seed"](inst)
            if spec["fn"] is run_qimrfo:
                kw["init_state"] = {"elite": start}
            else:
                kw["seed_assign"] = start
        schedule = spec["fn"](inst, obj, job["budget"], P=POPULATION, seed=job["run_seed"], track=False, **kw)["best_assign"]
    runtime = time.time() - t0
    makespan, energy = Objective(inst)._raw(schedule)     # exact makespan (s) and energy (Wh) of the final schedule
    lb, lb_p = inst.lower_bound(), inst.lower_bound_pmtn()
    return {"key": job["key"], "experiment": job["experiment"], "algorithm": job["algorithm"],
            "problem": problem_name(n, m, dist, het), "tasks": n, "vms": m, "task_lengths": dist, "vm_heterogeneity": het,
            "instance_seed": job["inst_seed"], "run_seed": job["run_seed"], "budget": job["budget"],
            "makespan_s": float(makespan), "energy_Wh": float(energy), "lower_bound_s": float(lb),
            "lower_bound_pmtn_s": float(lb_p), "gap_pct": float(100 * (makespan - lb) / lb),
            "gap_pmtn_pct": float(100 * (makespan - lb_p) / lb_p), "runtime_s": float(runtime), "evaluations": int(obj.n_evals)}


def static_jobs(experiment, algorithms, problems, inst_seeds, runs, budget):
    # All (algorithm, problem, instance, run) combinations; deterministic heuristics are run once.
    jobs = []
    for prob in problems:
        for s in inst_seeds:
            for a in algorithms:
                for r in (range(1) if "heuristic" in ALGORITHMS[a] else range(runs)):
                    key = f"{experiment}|{a}|{prob[0]}-{prob[1]}-{prob[2]}-{prob[3]}|inst{s}|run{r}|b{budget}"
                    jobs.append({"key": key, "experiment": experiment, "algorithm": a, "problem": tuple(prob),
                                 "inst_seed": s, "run_seed": r, "budget": budget})
    return jobs
""")
code(r"""
# =====================================================================================================
# SECTION 8b - CHANGING-CLOUD RUNS
# =====================================================================================================
# The six change scenarios used in Experiment D (100 tasks / 10 VMs unless stated; K changes each)
SCENARIOS = {
    "Task churn (20% replaced)":         dict(n=100, m=10, change="churn", rho=0.2),
    "VM speed drift":                    dict(n=100, m=10, change="drift"),
    "VM failure":                        dict(n=100, m=10, change="vm_fail"),
    "VM added":                          dict(n=100, m=10, change="vm_add"),
    "Mixed events":                      dict(n=100, m=10, change="mixed", rho=0.2),
    "Mixed, 200 tasks, 20 VMs, heavy-tailed": dict(n=200, m=20, change="mixed", rho=0.2, task_dist="lognormal"),
}

# Strategies (how each method reacts to a change)
STRATEGIES = {
    # D1: the register swarm with the swap move keeps its state (and the running schedule) between changes
    "QI-MRFO+swap (keeps its state)": dict(algo="QI-MRFO", strategy="continue_struct", repair="greedy", carry_elite=True,
                                           algo_kw={"exchange": 1.0}),
    # D1: the GA with the same swap move keeps its population between changes
    "GA+swap (keeps its population)": dict(algo="GA", strategy="continue", repair="greedy", algo_kw={"exchange": 1.0}),
    # D1: Max-Min recomputed from scratch after every change (moves many tasks)
    "Max-Min (recompute)":            dict(algo="Max-Min"),
    # D2: the best heuristic = the cheaper of Max-Min recompute and zero-migration repair
    "Best heuristic (Chooser)":       dict(algo="Chooser"),
    # D2: the final QI-MRFO configuration (event-aware elite + incremental repair + no noise after small changes)
    "QI-MRFO final":                  dict(algo="QI-MRFO", strategy="continue_struct", repair="incremental",
                                           carry_elite="except_vm_add", algo_kw={"exchange": 1.0},
                                           decoherence_by_event={"churn": 0.0, "drift": 0.0, "vm_fail": 0.0}),
}


def run_changing(job):
    # Run ONE strategy on ONE changing-cloud scenario and return averages over the changes (makespan in seconds).
    sc, st = SCENARIOS[job["scenario"]], STRATEGIES[job["strategy"]]
    seq = make_dynamic_sequence(sc["n"], sc["m"], seed=job["seed"], K=job["K"], change=sc["change"],
                                rho=sc.get("rho", 0.2), task_dist=sc.get("task_dist", "uniform"), hetero="high")
    t0 = time.time()
    out = run_dynamic(seq, st["algo"], st.get("strategy", "continue_struct"), job["budget0"], job["budget"], seed=job["seed"],
                      P=POPULATION, decoherence_c=1.0, mode="born_signed", algo_kw=st.get("algo_kw"),
                      carry_elite=st.get("carry_elite", False), repair=st.get("repair", "random"),
                      mig_lambda=job["lam"], decoherence_by_event=st.get("decoherence_by_event"))
    post = out[1:]                                         # the epochs after each change
    return {"key": job["key"], "experiment": job["experiment"], "strategy": job["strategy"], "scenario": job["scenario"],
            "migration_price": job["lam"] if job["lam"] is not None else 0.0, "seed": job["seed"], "changes": job["K"],
            "makespan_s": float(np.mean([o["best"] for o in post])),              # makespan after each change (s)
            "lower_bound_s": float(np.mean([o["lb"] for o in post])),
            "gap_pct": float(100 * np.mean([o["gap"] for o in post])),
            "cost_gap_pct": float(100 * np.mean([o["cost_gap"] for o in post])),  # makespan x (1 + price x moves) vs bound
            "migrations_per_change": float(np.mean([o["migrations"] for o in post])),
            "initial_makespan_s": float(out[0]["best"]), "runtime_s": float(time.time() - t0)}


def changing_jobs(experiment, strategies, scenarios, seeds, K, budget0, budget, lams=(None,)):
    jobs = []
    for lam in lams:
        for sc in scenarios:
            for s in seeds:
                for st in strategies:
                    key = f"{experiment}|{st}|{sc}|lam{lam}|seed{s}|K{K}|b{budget0}-{budget}"
                    jobs.append({"key": key, "experiment": experiment, "strategy": st, "scenario": sc, "seed": s, "K": K,
                                 "budget0": budget0, "budget": budget, "lam": lam})
    return jobs
""")
code(r"""
# =====================================================================================================
# SECTION 8c - RUNNER THAT SAVES EVERY RUN TO GOOGLE DRIVE (and resumes after a disconnect)
# =====================================================================================================
def check_drive():
    # Stop with a clear message if Google Drive should be used but is not mounted (e.g. after the final cell unmounted
    # it): otherwise results would silently go to a temporary folder of this Colab session.
    if SAVE_TO_GOOGLE_DRIVE and IN_COLAB and not os.path.isdir("/content/drive/MyDrive"):
        raise RuntimeError("Google Drive is not mounted: run the Section 2 cell again, then re-run this cell.")


def read_runs(csv_name, jobs=None):
    # Read a saved results file back with exact floating-point values (None if it does not exist yet).
    # If `jobs` is given, keep only the runs of those jobs (so settings of an earlier run cannot mix in).
    path = os.path.join(RUN_DIR, csv_name)
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, float_precision="round_trip").drop_duplicates("key", keep="last")
    if jobs is not None:
        df = df[df["key"].isin({j["key"] for j in jobs})].reset_index(drop=True)
    return df


def run_jobs(jobs, worker, csv_name):
    # Run all jobs in parallel. Each finished run is appended to RUN_DIR/csv_name immediately, so nothing is lost
    # if Colab disconnects. Runs already in that file are skipped: re-running a cell resumes the experiment.
    check_drive()
    path = os.path.join(RUN_DIR, csv_name)
    saved = read_runs(csv_name, jobs)
    done = set(saved["key"]) if saved is not None else set()
    todo = [j for j in jobs if j["key"] not in done]
    print(f"{csv_name}: {len(jobs)} runs in total | {len(done)} already saved | {len(todo)} to run on {N_WORKERS} worker(s)",
          flush=True)
    if todo:
        t0, step = time.time(), max(1, len(todo) // 20)
        pool = mp.get_context("fork").Pool(N_WORKERS) if (N_WORKERS > 1 and hasattr(os, "fork")) else None
        results = pool.imap_unordered(worker, todo) if pool else map(worker, todo)
        try:
            for i, row in enumerate(results, 1):
                pd.DataFrame([row]).to_csv(path, mode="a", header=not os.path.exists(path), index=False)   # save now
                if i % step == 0 or i == len(todo):
                    el = time.time() - t0
                    print(f"  {i}/{len(todo)} runs done | {el / 60:.1f} min elapsed | about {el / i * (len(todo) - i) / 60:.1f} min left",
                          flush=True)
        finally:
            if pool:                       # stop the worker processes (at once if the cell was interrupted)
                pool.terminate(); pool.join()
    return read_runs(csv_name, jobs)


def save_table(df, name, title=None):
    # Show a table in the notebook and save it as RUN_DIR/<name>.csv
    df.to_csv(os.path.join(RUN_DIR, name + ".csv"))
    ALL_TABLES[name] = df
    if title:
        print(title)
    display(df)


ALL_TABLES = {}          # every table produced in this session (also written to one Excel file at the end)
""")
code(r"""
# =====================================================================================================
# SECTION 8d - STATISTICS AND TABLE HELPERS
# =====================================================================================================
from scipy import stats


def holm(pvalues):
    # Holm-Bonferroni correction for several tests done together
    p = np.asarray(pvalues, float); order = np.argsort(p); adj = np.empty_like(p); running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (len(p) - rank) * p[idx])); adj[idx] = running
    return adj


def mann_whitney(a, b):
    # Two-sided Mann-Whitney U test for two independent sets of runs (p-value)
    a, b = np.asarray(a), np.asarray(b)
    if len(a) < 2 or len(b) < 2 or (np.all(a == a[0]) and np.all(b == b[0]) and a[0] == b[0]):
        return np.nan
    return float(stats.mannwhitneyu(a, b, alternative="two-sided").pvalue)


def wilcoxon(diff):
    # Two-sided Wilcoxon signed-rank test on paired differences (p-value)
    d = np.asarray(diff, float); d = d[d != 0]
    return float(stats.wilcoxon(d).pvalue) if len(d) >= 2 else np.nan


def mean_sd_best(df, row, col, value="makespan_s", order_rows=None, order_cols=None):
    # Table of "mean ± standard deviation" with the best run on a second line (as text), e.g. for makespan in seconds
    g = df.groupby([row, col])[value]
    mean, sd, best, count = g.mean(), g.std(ddof=1).fillna(0.0), g.min(), g.size()
    rows = order_rows or list(dict.fromkeys(df[row])); cols = order_cols or list(dict.fromkeys(df[col]))
    table = pd.DataFrame(index=rows, columns=cols, dtype=object)
    for r in rows:
        for c in cols:
            if (r, c) in mean.index:
                table.loc[r, c] = (f"{mean[r, c]:.2f}" if count[r, c] == 1 else
                                   f"{mean[r, c]:.2f} ± {sd[r, c]:.2f} (best {best[r, c]:.2f})")
    return table


def pivot_mean(df, row, col, value, order_rows=None, order_cols=None, digits=2):
    t = df.pivot_table(index=row, columns=col, values=value, aggfunc="mean")
    t = t.reindex(index=order_rows or list(dict.fromkeys(df[row])), columns=order_cols or list(dict.fromkeys(df[col])))
    return t.round(digits)
""")
code(r"""
# =====================================================================================================
# SECTION 8e - PLOT STYLE (one consistent, colour-blind-checked palette for every figure)
# =====================================================================================================
from matplotlib.ticker import FuncFormatter
PERCENT = FuncFormatter(lambda v, _: f"{v:g} %")          # axis labels such as "1 %", "10 %", "100 %"
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7"]
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": MUTED,
                     "ytick.color": MUTED, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
                     "savefig.facecolor": SURFACE, "text.color": INK})


def style(ax, title, xlabel, ylabel):
    ax.set_title(title, loc="left", fontsize=10, color=INK)
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
    ax.grid(True, color=GRID, linewidth=0.8); ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def save_figure(fig, name):
    # Save a figure as RUN_DIR/<name> (PNG) and show it
    fig.savefig(os.path.join(RUN_DIR, name), dpi=160, bbox_inches="tight")
    plt.show()
    plt.close(fig)
""")
code(r"""
# =====================================================================================================
# SECTION 8f - EXPERIMENT SIZES FOR THE TWO MODES
# =====================================================================================================
# "full"  = exactly the settings of the reported studies.
# "quick" = a subset of the same runs: same budgets, seeds and settings, fewer problems / runs / sizes.
V4_PROBLEMS = [(30, 5, "uniform", "high"), (50, 10, "bimodal", "high"), (100, 10, "uniform", "high"),
               (50, 10, "uniform", "none"), (200, 20, "uniform", "high"), (100, 10, "lognormal", "low"),
               (60, 8, "bimodal", "none")]
TEST_PROBLEM_TYPES = [(80, 8, "uniform", "high"), (150, 15, "uniform", "high"), (300, 30, "uniform", "high"),
                      (100, 10, "bimodal", "high"), (200, 10, "bimodal", "none"), (120, 12, "lognormal", "high"),
                      (60, 12, "uniform", "low"), (100, 20, "lognormal", "low")]
EXPERIMENT_SIZES = {
    "quick": dict(
        A=dict(problems=[V4_PROBLEMS[0], V4_PROBLEMS[2], V4_PROBLEMS[4]], inst_seed=1, runs=3, budget=20000),
        B=dict(problems=[TEST_PROBLEM_TYPES[0], TEST_PROBLEM_TYPES[3], TEST_PROBLEM_TYPES[5]], inst_seeds=[101, 102],
               runs=1, budget=20000),
        C=dict(sizes=[500, 1000], vms=50, inst_seed=1, runs=2, budget=20000),
        D=dict(scenarios=["Task churn (20% replaced)", "VM added"], seeds_ga=[101, 102], seeds_cost=[601, 602],
               K=8, budget0=20000, budget=4000, prices=[0.05, 0.2, 1.0]),
    ),
    "full": dict(
        A=dict(problems=V4_PROBLEMS, inst_seed=1, runs=30, budget=20000),
        B=dict(problems=TEST_PROBLEM_TYPES, inst_seeds=list(range(101, 111)), runs=2, budget=20000),
        C=dict(sizes=[500, 1000, 1500, 2000, 5000], vms=50, inst_seed=1, runs=10, budget=20000),
        D=dict(scenarios=list(SCENARIOS), seeds_ga=list(range(101, 111)), seeds_cost=list(range(601, 611)),
               K=8, budget0=20000, budget=4000, prices=[0.05, 0.2, 1.0]),
    ),
}
SIZES = EXPERIMENT_SIZES[MODE]

# Save the settings of this run next to the results (for reproducibility)
with open(os.path.join(RUN_DIR, "settings.json"), "w") as f:
    json.dump({"mode": MODE, "sizes": SIZES, "population": POPULATION, "workers": N_WORKERS,
               "python": platform.python_version(), "numpy": np.__version__, "started": time.strftime("%Y-%m-%d %H:%M:%S")},
              f, indent=1, default=str)
print(json.dumps(SIZES, indent=1, default=str))
""")

# =========================================================================================================== self-check
md(r"""
## Section 9 — Quick self-check (a few seconds)
Before the long experiments, every algorithm is run once on a tiny problem. The check confirms that each one returns a
valid schedule, respects its evaluation budget and gives the same answer twice with the same seed.
""")
code(r"""
# =====================================================================================================
# SECTION 9 - SELF-CHECK: valid schedules, budget respected, reproducible with the same seed
# =====================================================================================================
# Every static algorithm, twice, on a tiny problem (12 tasks, 3 VMs) with a budget of 600 evaluations
for _name in ALGORITHMS:
    _job = {"key": "check", "experiment": "check", "algorithm": _name, "problem": (12, 3, "uniform", "high"),
            "inst_seed": 0, "run_seed": 0, "budget": 600}
    _r1, _r2 = run_static(_job), run_static(_job)
    assert _r1["evaluations"] <= 600, f"{_name} exceeded the budget"
    assert _r1["makespan_s"] == _r2["makespan_s"], f"{_name} is not reproducible"
    assert _r1["makespan_s"] >= _r1["lower_bound_s"] - 1e-9, f"{_name} beat the lower bound (impossible)"
# Every changing-cloud strategy, twice, on the "Mixed events" scenario with 2 changes and small budgets
for _st in STRATEGIES:
    _job = {"key": "check", "experiment": "check", "strategy": _st, "scenario": "Mixed events", "seed": 0, "K": 2,
            "budget0": 600, "budget": 300, "lam": 0.2}
    _r1, _r2 = run_changing(_job), run_changing(_job)
    assert _r1["makespan_s"] >= _r1["lower_bound_s"] - 1e-9, f"{_st} beat the lower bound (impossible)"
    assert _r1["cost_gap_pct"] == _r2["cost_gap_pct"], f"{_st} is not reproducible"
print("Self-check passed: all", len(ALGORITHMS), "algorithms and", len(STRATEGIES), "changing-cloud strategies work.")
""")

# =========================================================================================================== experiment A
md(r"""
## Experiment A — Original DMO / MRFO vs quantum-inspired QI-DMO / QI-MRFO
**Question.** Does the quantum-inspired representation improve DMO and MRFO over the usual rounding, and how do they
compare with GA, PSO, the heuristics and random search?

**Setup.** Full mode: 7 problems (30–200 tasks, 5–20 VMs), 30 independent runs per algorithm, 20 000 evaluations per run.
`P-MRFO (classical twin)` is QI-MRFO without the quantum formula: it checks whether the quantum part itself matters.

**Output files.** `A_runs.csv` (every run), `A_makespan_seconds.csv`, `A_gap_percent.csv`, `A_tests.csv` and
`A_gap.png`.
""")
code(r"""
# =====================================================================================================
# EXPERIMENT A - DMO / MRFO vs QI-DMO / QI-MRFO (and GA, PSO, heuristics, random search)
# =====================================================================================================
ALGS_A = ["DMO", "QI-DMO", "MRFO", "QI-MRFO", "P-MRFO (classical twin)", "GA", "PSO", "Max-Min", "Min-Min", "Random search"]
cfg = SIZES["A"]
JOBS_A = static_jobs("A", ALGS_A, cfg["problems"], [cfg["inst_seed"]], cfg["runs"], cfg["budget"])   # all runs of A

if RUN_EXPERIMENT_A:
    A = run_jobs(JOBS_A, run_static, "A_runs.csv")                  # runs (or resumes) A; one row per run
    problems = list(dict.fromkeys(A["problem"]))

    # Table A1: makespan in seconds, mean ± standard deviation over the runs (best run in brackets) + lower bound
    t = mean_sd_best(A, "algorithm", "problem", order_rows=ALGS_A, order_cols=problems)
    t.loc["Lower bound (s)"] = [f"{A[A.problem == p].lower_bound_s.iloc[0]:.2f}" for p in problems]
    save_table(t, "A_makespan_seconds", "Table A1 - makespan in seconds: mean ± SD over the runs (best run)")

    # Table A2: gap to the lower bound in %, mean over the runs, plus the average over all problems
    g = pivot_mean(A, "algorithm", "problem", "gap_pct", ALGS_A, problems)
    g["Average"] = g.mean(axis=1).round(2)
    save_table(g, "A_gap_percent", "Table A2 - gap to the lower bound (%), mean over the runs")

    # Table A3: is the quantum-inspired version better than the original? (Mann-Whitney U per problem, Holm across problems)
    rows = []
    for a, b in [("QI-DMO", "DMO"), ("QI-MRFO", "MRFO"), ("QI-MRFO", "GA"), ("QI-MRFO", "P-MRFO (classical twin)")]:
        ps = [mann_whitney(A[(A.algorithm == a) & (A.problem == p)].makespan_s, A[(A.algorithm == b) & (A.problem == p)].makespan_s)
              for p in problems]
        for p, pv, ph in zip(problems, ps, holm(np.nan_to_num(ps, nan=1.0))):
            xa, xb = A[(A.algorithm == a) & (A.problem == p)].makespan_s, A[(A.algorithm == b) & (A.problem == p)].makespan_s
            rows.append({"A": a, "B": b, "problem": p, "mean A (s)": round(xa.mean(), 2), "mean B (s)": round(xb.mean(), 2),
                         "A better on average": xa.mean() < xb.mean(), "p (Mann-Whitney)": pv, "p (Holm)": ph})
    save_table(pd.DataFrame(rows), "A_tests", "Table A3 - pairwise tests (lower makespan is better)")

    # Figure A: average gap per algorithm (log scale), best at the top
    avg = g["Average"].sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    colors = [PALETTE[0] if a.startswith("QI") else PALETTE[6] if a.startswith("P-MRFO") else MUTED for a in avg.index]
    ax.scatter(avg.values, range(len(avg)), s=60, color=colors, edgecolors=SURFACE, linewidths=2, zorder=3)
    for y, (a, v) in enumerate(avg.items()):
        ax.annotate(f"{v:.2f} %", (v, y), xytext=(8, 0), textcoords="offset points", va="center", fontsize=8, color=INK2)
    ax.set_yticks(range(len(avg))); ax.set_yticklabels(avg.index); ax.set_xscale("log"); ax.xaxis.set_major_formatter(PERCENT)
    style(ax, "Experiment A: average gap to the lower bound\n(blue = quantum-inspired, purple = its classical twin, grey = others)",
          "gap (%, log scale)", "")
    save_figure(fig, "A_gap.png")
else:
    print("Experiment A skipped (RUN_EXPERIMENT_A = False).")
""")

# =========================================================================================================== experiment B
md(r"""
## Experiment B — The swap move on 80 unseen problems
**Question.** Does adding the swap move make QI-MRFO better than GA and the Max-Min heuristic on problems that were
never used for tuning?

**Setup.** Full mode: 8 problem types × 10 problems (80 problems), 2 runs each, 20 000 evaluations.
* **Fair comparison.** The same swap move is also given to the GA (`GA+swap`) and to a simple (1+1)-EA (`(1+1)-EA+swap`).
  This checks whether the benefit comes from the swarm or from the move itself.
* **Note on the (1+1)-EA.** In the reported study it was tested on a second set of 80 unseen problems (instance seeds
  201–210). Here it runs on the same problems as the other methods, so its numbers are new.
* **Gap here.** It is measured against the tighter *preemptive* lower bound.

**Output files.** `B_runs.csv`, `B_makespan_seconds.csv`, `B_gap_percent.csv`, `B_wins.csv` and `B_gap.png`.
""")
code(r"""
# =====================================================================================================
# EXPERIMENT B - THE SWAP MOVE ON UNSEEN PROBLEMS
# =====================================================================================================
ALGS_B = ["MRFO", "QI-MRFO", "QI-MRFO+swap", "P-MRFO+swap (classical twin)", "GA", "GA+swap", "(1+1)-EA+swap", "Max-Min"]
cfg = SIZES["B"]
JOBS_B = static_jobs("B", ALGS_B, cfg["problems"], cfg["inst_seeds"], cfg["runs"], cfg["budget"])      # all runs of B

if RUN_EXPERIMENT_B:
    B = run_jobs(JOBS_B, run_static, "B_runs.csv")
    types = list(dict.fromkeys(B["problem"]))

    # Table B1: mean makespan (s) per problem type; B2: mean gap (%) to the tight lower bound per type
    save_table(pivot_mean(B, "algorithm", "problem", "makespan_s", ALGS_B, types), "B_makespan_seconds",
               "Table B1 - makespan in seconds, mean over the problems of each type and their runs")
    gb = pivot_mean(B, "algorithm", "problem", "gap_pmtn_pct", ALGS_B, types)
    gb["Average"] = B.groupby(["algorithm", "problem", "instance_seed"]).gap_pmtn_pct.mean().groupby("algorithm").mean().reindex(ALGS_B).round(2)
    save_table(gb, "B_gap_percent", "Table B2 - gap to the (preemptive) lower bound in %, mean")

    # Table B3: on how many problems is QI-MRFO+swap better? (paired per problem; Wilcoxon signed-rank test)
    per_problem = B.groupby(["problem", "instance_seed", "algorithm"]).makespan_s.mean().unstack("algorithm")
    rows = []
    for b in [x for x in ALGS_B if x != "QI-MRFO+swap"]:
        d = per_problem["QI-MRFO+swap"] - per_problem[b]
        rows.append({"QI-MRFO+swap vs": b, "problems": len(d), "QI-MRFO+swap better on": int((d < 0).sum()),
                     "worse on": int((d > 0).sum()), "mean difference (s)": round(d.mean(), 3), "p (Wilcoxon)": wilcoxon(d)})
    save_table(pd.DataFrame(rows), "B_wins", "Table B3 - QI-MRFO+swap against each method (lower makespan = better)")

    # Figure B: average gap per algorithm (log scale)
    avg = gb["Average"].sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    colors = [PALETTE[0] if a.startswith("QI") else PALETTE[6] if a.startswith("P-MRFO") else MUTED for a in avg.index]
    ax.scatter(avg.values, range(len(avg)), s=60, color=colors, edgecolors=SURFACE, linewidths=2, zorder=3)
    for y, (a, v) in enumerate(avg.items()):
        ax.annotate(f"{v:.2f} %", (v, y), xytext=(8, 0), textcoords="offset points", va="center", fontsize=8, color=INK2)
    ax.set_yticks(range(len(avg))); ax.set_yticklabels(avg.index); ax.set_xscale("log"); ax.xaxis.set_major_formatter(PERCENT)
    style(ax, "Experiment B: average gap to the (preemptive) lower bound on unseen problems\n"
              "(blue = quantum-inspired, purple = its classical twin, grey = others)", "gap (%, log scale)", "")
    save_figure(fig, "B_gap.png")
else:
    print("Experiment B skipped (RUN_EXPERIMENT_B = False).")
""")

# =========================================================================================================== experiment C
md(r"""
## Experiment C — Scaling to 500, 1 000, 1 500, 2 000 and 5 000 tasks
**Question.** How do the methods behave when the number of tasks grows?

**Setup.** Full mode: one problem per size on 50 heterogeneous VMs, 10 independent runs per algorithm (the heuristics
run once), 20 000 evaluations per run.
* **Max-Min start.** "+seed" means the method starts from the Max-Min schedule.
* **Run time.** The quantum-inspired methods keep a probability for every (task, VM) pair, so their run time grows
  with tasks × VMs. At 5 000 tasks one run takes about 2–4 minutes.

**Output files.** `C_runs.csv`, `C_makespan_seconds.csv`, `C_gap_percent.csv`, `C_runtime_seconds.csv`, `C_tests.csv`
and `C_scaling.png`.
""")
code(r"""
# =====================================================================================================
# EXPERIMENT C - SCALING TO THOUSANDS OF TASKS (50 VMs)
# =====================================================================================================
ALGS_C = ["DMO", "QI-DMO", "MRFO", "QI-MRFO", "QI-MRFO+swap", "QI-MRFO+swap+seed", "GA", "GA+swap", "PSO",
          "Random search", "(1+1)-EA+swap", "(1+1)-EA+swap+seed", "Max-Min", "Min-Min"]
cfg = SIZES["C"]
problems_c = [(n, cfg["vms"], "uniform", "high") for n in cfg["sizes"]]          # one problem per size, 50 VMs
JOBS_C = static_jobs("C", ALGS_C, problems_c, [cfg["inst_seed"]], cfg["runs"], cfg["budget"])      # all runs of C

if RUN_EXPERIMENT_C:
    C = run_jobs(JOBS_C, run_static, "C_runs.csv")
    C["size"] = C["tasks"].map(lambda n: f"{n} tasks")
    sizes = [f"{n} tasks" for n in cfg["sizes"]]

    # Table C1: makespan (s) mean ± SD (best run) per size, plus the lower bound
    t = mean_sd_best(C, "algorithm", "size", order_rows=ALGS_C, order_cols=sizes)
    t.loc["Lower bound (s)"] = [f"{C[C['size'] == s].lower_bound_s.iloc[0]:.2f}" for s in sizes]
    save_table(t, "C_makespan_seconds", "Table C1 - makespan in seconds: mean ± SD over the runs (best run)")
    # Table C2: gap (%) and Table C3: run time per run (s)
    save_table(pivot_mean(C, "algorithm", "size", "gap_pct", ALGS_C, sizes), "C_gap_percent",
               "Table C2 - gap to the lower bound (%), mean over the runs")
    save_table(pivot_mean(C, "algorithm", "size", "runtime_s", ALGS_C, sizes, digits=1), "C_runtime_seconds",
               "Table C3 - run time per run in seconds (mean)")

    # Table C4: key comparisons per size (Mann-Whitney U, Holm across sizes)
    rows = []
    for a, b in [("QI-DMO", "DMO"), ("QI-MRFO", "MRFO"), ("QI-MRFO+swap", "GA"), ("QI-MRFO+swap", "GA+swap"),
                 ("QI-MRFO+swap", "(1+1)-EA+swap"), ("QI-MRFO+swap+seed", "Max-Min")]:
        ps = [mann_whitney(C[(C.algorithm == a) & (C['size'] == s)].makespan_s, C[(C.algorithm == b) & (C['size'] == s)].makespan_s)
              for s in sizes]
        for s, pv, ph in zip(sizes, ps, holm(np.nan_to_num(ps, nan=1.0))):
            xa, xb = C[(C.algorithm == a) & (C['size'] == s)].makespan_s, C[(C.algorithm == b) & (C['size'] == s)].makespan_s
            rows.append({"A": a, "B": b, "size": s, "mean A (s)": round(xa.mean(), 2), "mean B (s)": round(xb.mean(), 2),
                         "every run of A better": bool(xa.max() < xb.min()), "p (Mann-Whitney)": pv, "p (Holm)": ph})
    save_table(pd.DataFrame(rows), "C_tests", "Table C4 - key comparisons per size (lower makespan is better)")

    # Figure C: gap to the lower bound vs number of tasks (log-log), main methods
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    for algo, col in zip(["QI-MRFO+swap", "QI-MRFO", "QI-DMO", "GA", "Max-Min", "MRFO", "DMO"], PALETTE):
        y = [C[(C.algorithm == algo) & (C.tasks == n)].gap_pct.mean() for n in cfg["sizes"]]
        ax.plot(cfg["sizes"], y, color=col, linewidth=2, label=algo, zorder=2)
        ax.plot(cfg["sizes"], y, "o", color=col, markersize=6, markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xticks(cfg["sizes"]); ax.set_xticklabels([f"{n:,}" for n in cfg["sizes"]])
    ax.minorticks_off(); ax.yaxis.set_major_formatter(PERCENT)
    style(ax, "Experiment C: gap to the lower bound as the number of tasks grows", "number of tasks (log scale)",
          "gap to the lower bound (%, log scale)")
    ax.legend(frameon=False, fontsize=8, loc="center left", bbox_to_anchor=(1.01, 0.5))
    save_figure(fig, "C_scaling.png")
else:
    print("Experiment C skipped (RUN_EXPERIMENT_C = False).")
""")

# =========================================================================================================== experiment D
md(r"""
## Experiment D — Changing cloud
**D1. QI-MRFO vs GA.** After each change, both methods continue from where they were, with the same swap move and the
same budget. Max-Min recomputed from scratch is shown for reference.

**D2. Moving a running task costs something.** The final QI-MRFO configuration is compared with the **best heuristic**,
the cheaper of full Max-Min recompute and zero-migration repair. Three migration prices are used: λ = 0.05, 0.2 and 1.0.
The *cost gap* combines makespan and migrations: makespan × (1 + λ × moved tasks / movable tasks), in % above the lower
bound.

**Setup.** Full mode: 6 change scenarios, 10 runs each, 8 changes per run; 20 000 evaluations before the first change
and 4 000 after each change.

**Output files.** `D1_runs.csv`, `D1_makespan_seconds.csv`, `D1_wins.csv`, `D2_runs.csv`, `D2_results.csv`,
`D2_by_scenario.csv` and `D2_cost.png`.
""")
code(r"""
# =====================================================================================================
# EXPERIMENT D - CHANGING CLOUD
# =====================================================================================================
cfg = SIZES["D"]
S1 = ["QI-MRFO+swap (keeps its state)", "GA+swap (keeps its population)", "Max-Min (recompute)"]      # D1 strategies
S2 = ["Best heuristic (Chooser)", "QI-MRFO final"]                                                   # D2 strategies
JOBS_D1 = changing_jobs("D1", S1, cfg["scenarios"], cfg["seeds_ga"], cfg["K"], cfg["budget0"], cfg["budget"])
JOBS_D2 = changing_jobs("D2", S2, cfg["scenarios"], cfg["seeds_cost"], cfg["K"], cfg["budget0"], cfg["budget"],
                        lams=cfg["prices"])

if RUN_EXPERIMENT_D:
    # ---- D1: QI-MRFO+swap vs GA+swap (and Max-Min recompute), makespan after each change -------------
    D1 = run_jobs(JOBS_D1, run_changing, "D1_runs.csv")
    t = pivot_mean(D1, "scenario", "strategy", "makespan_s", cfg["scenarios"], S1)
    t.insert(0, "Lower bound (s)", D1.groupby("scenario").lower_bound_s.mean().reindex(cfg["scenarios"]).round(2))
    save_table(t, "D1_makespan_seconds", "Table D1 - makespan in seconds after each change (mean over changes and runs)")
    w = D1.pivot_table(index=["scenario", "seed"], columns="strategy", values="makespan_s")
    d = w[S1[0]] - w[S1[1]]
    rows = [{"scenario": sc, "runs": len(d[sc]), "QI-MRFO better in": int((d[sc] < 0).sum())} for sc in cfg["scenarios"]]
    rows.append({"scenario": "ALL", "runs": len(d), "QI-MRFO better in": int((d < 0).sum()), "p (Wilcoxon)": wilcoxon(d)})
    save_table(pd.DataFrame(rows), "D1_wins", "Table D1b - QI-MRFO+swap vs GA+swap (lower makespan is better)")

    # ---- D2: moving a running task has a cost: final QI-MRFO vs the best heuristic -------------------
    D2 = run_jobs(JOBS_D2, run_changing, "D2_runs.csv")
    rows = []
    for lam in cfg["prices"]:
        x = D2[D2.migration_price == lam]
        w = x.pivot_table(index=["scenario", "seed"], columns="strategy", values="cost_gap_pct")
        d = w[S2[1]] - w[S2[0]]
        rows.append({"migration price λ": lam,
                     "cost gap %: best heuristic": round(w[S2[0]].mean(), 2), "cost gap %: QI-MRFO final": round(w[S2[1]].mean(), 2),
                     "makespan (s): best heuristic": round(x[x.strategy == S2[0]].makespan_s.mean(), 2),
                     "makespan (s): QI-MRFO final": round(x[x.strategy == S2[1]].makespan_s.mean(), 2),
                     "tasks moved per change: best heuristic": round(x[x.strategy == S2[0]].migrations_per_change.mean(), 1),
                     "tasks moved per change: QI-MRFO final": round(x[x.strategy == S2[1]].migrations_per_change.mean(), 1),
                     "QI-MRFO better in": f"{int((d < 0).sum())} of {len(d)}", "p (Wilcoxon)": wilcoxon(d)})
    save_table(pd.DataFrame(rows), "D2_results", "Table D2 - with a migration cost (lower cost gap is better)")
    by = D2.pivot_table(index=["migration_price", "scenario"], columns="strategy",
                        values=["makespan_s", "migrations_per_change", "cost_gap_pct"]).round(2)
    save_table(by, "D2_by_scenario", "Table D2b - per scenario: makespan (s), tasks moved per change, cost gap (%)")

    # Figure D: cost gap vs migration price
    fig, ax = plt.subplots(figsize=(6.6, 3.8))
    for s, col in zip(S2, [MUTED, PALETTE[0]]):
        y = [D2[(D2.migration_price == lam) & (D2.strategy == s)].cost_gap_pct.mean() for lam in cfg["prices"]]
        ax.plot(cfg["prices"], y, color=col, linewidth=2, label=s, zorder=2)
        ax.plot(cfg["prices"], y, "o", color=col, markersize=6, markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)
    ax.set_xscale("log"); ax.set_xticks(cfg["prices"]); ax.set_xticklabels([f"{p:g}" for p in cfg["prices"]]); ax.minorticks_off()
    style(ax, "Experiment D2: cost gap vs migration price (lower is better)", "migration price λ (log scale)", "cost gap (%)")
    ax.legend(frameon=False, fontsize=8)
    save_figure(fig, "D2_cost.png")
else:
    print("Experiment D skipped (RUN_EXPERIMENT_D = False).")
""")

# =========================================================================================================== summary
md(r"""
## Section 10 — Summary and saved files
* **The summary** is computed from the runs saved in the results folder. An experiment is summarised only when *all* its
  runs are saved; for an unfinished experiment the summary says how many runs are missing. It is saved as `summary.txt`.
* **All tables** of this session are also written to one Excel workbook, `all_tables.xlsx`, with one sheet per table.
* **The file list** at the end shows every file in the results folder.
""")
code(r"""
# =====================================================================================================
# SECTION 10 - SUMMARY (computed from the saved runs) AND LIST OF SAVED FILES
# =====================================================================================================
lines = [f"Quantum-inspired MRFO / DMO for cloud task scheduling - results summary ({MODE} mode)",
         f"Folder: {RUN_DIR}", f"Written: {time.strftime('%Y-%m-%d %H:%M:%S')}", ""]
if MODE == "quick":
    lines += ["NOTE: quick mode runs a subset of the full experiments with the same settings. Each run equals the same run",
              "in full mode, but the averages below use far fewer runs than the reported results; set MODE = 'full' for those.", ""]


def complete_runs(csv_name, jobs, label):
    # The saved runs of one experiment if ALL of them are saved, else None (with a note in the summary)
    df = read_runs(csv_name, jobs)
    if df is None or len(df) == 0:
        lines.extend([f"{label}: no saved runs (not run yet).", ""])
        return None
    if len(df) < len(jobs):
        lines.extend([f"{label}: only {len(df)} of {len(jobs)} runs are saved - run its cell again to finish it.", ""])
        return None
    return df


def mean_of(df, value, **where):
    # Mean of one column over the rows matching all conditions, e.g. mean_of(C, "makespan_s", algorithm="GA", tasks=500)
    for k, v in where.items():
        df = df[df[k] == v]
    return df[value].mean()


A = complete_runs("A_runs.csv", JOBS_A, "Experiment A")
if A is not None:
    g = A.groupby(["algorithm", "problem"]).gap_pct.mean().groupby("algorithm").mean()     # average over problems
    lines += [f"Experiment A ({A.problem.nunique()} problems): average gap to the lower bound",
              f"  DMO {g['DMO']:.2f} % -> QI-DMO {g['QI-DMO']:.2f} %;  MRFO {g['MRFO']:.2f} % -> QI-MRFO {g['QI-MRFO']:.2f} %",
              f"  classical twin P-MRFO {g['P-MRFO (classical twin)']:.2f} %;  GA {g['GA']:.2f} %;  PSO {g['PSO']:.2f} %;  "
              f"Max-Min {g['Max-Min']:.2f} %;  Random search {g['Random search']:.2f} %", ""]

B = complete_runs("B_runs.csv", JOBS_B, "Experiment B")
if B is not None:
    pp = B.groupby(["problem", "instance_seed", "algorithm"]).makespan_s.mean().unstack("algorithm")   # one row per problem
    lines += [f"Experiment B ({len(pp)} unseen problems): QI-MRFO+swap compared with each method (mean makespan per problem)",
              *[f"  vs {b}: lower on {int((pp['QI-MRFO+swap'] < pp[b]).sum())} of {len(pp)} problems, "
                f"higher on {int((pp['QI-MRFO+swap'] > pp[b]).sum())}" for b in ["QI-MRFO", "GA", "GA+swap", "(1+1)-EA+swap", "Max-Min"]],
              ""]

C = complete_runs("C_runs.csv", JOBS_C, "Experiment C")
if C is not None:
    lines += ["Experiment C: mean makespan in seconds per number of tasks (LB = lower bound)"]
    for n in sorted(C.tasks.unique()):
        ms = {a: mean_of(C, "makespan_s", algorithm=a, tasks=n) for a in
              ["MRFO", "QI-MRFO", "GA", "QI-MRFO+swap", "(1+1)-EA+swap", "Max-Min", "QI-MRFO+swap+seed"]}
        lines.append(f"  {n} tasks (LB {mean_of(C, 'lower_bound_s', tasks=n):.2f} s): "
                     + "; ".join(f"{a} {v:.2f}" for a, v in ms.items()))
    lines.append("")

D1 = complete_runs("D1_runs.csv", JOBS_D1, "Experiment D1")
if D1 is not None:
    w = D1.pivot_table(index=["scenario", "seed"], columns="strategy", values="makespan_s")
    k = int((w["QI-MRFO+swap (keeps its state)"] < w["GA+swap (keeps its population)"]).sum())
    lines += [f"Experiment D1 (changing cloud): QI-MRFO+swap has a lower makespan than GA+swap in {k} of {len(w)} runs",
              f"  mean makespan after a change: QI-MRFO+swap {w['QI-MRFO+swap (keeps its state)'].mean():.2f} s, "
              f"GA+swap {w['GA+swap (keeps its population)'].mean():.2f} s, Max-Min {w['Max-Min (recompute)'].mean():.2f} s", ""]

D2 = complete_runs("D2_runs.csv", JOBS_D2, "Experiment D2")
if D2 is not None:
    lines += ["Experiment D2 (moving a running task has a cost): QI-MRFO final vs the best heuristic, cost gap in %"]
    for lam in sorted(D2.migration_price.unique()):
        w = D2[D2.migration_price == lam].pivot_table(index=["scenario", "seed"], columns="strategy", values="cost_gap_pct")
        k = int((w["QI-MRFO final"] < w["Best heuristic (Chooser)"]).sum())
        lines.append(f"  price {lam:g}: best heuristic {w['Best heuristic (Chooser)'].mean():.2f} % -> QI-MRFO final "
                     f"{w['QI-MRFO final'].mean():.2f} %; QI-MRFO better in {k} of {len(w)} runs")
    lines.append("")

lines += ["Units: makespan in seconds (task length in MI / VM speed in MIPS); energy in Wh; gap in % above the lower bound.",
          "Quantum-inspired = a classical algorithm that uses quantum ideas (registers, measurement, decoherence); no quantum",
          "hardware is used and no quantum advantage is claimed."]
summary = "\n".join(lines)
print(summary)
with open(os.path.join(RUN_DIR, "summary.txt"), "w") as f:
    f.write(summary + "\n")

# All tables of this session in one Excel workbook (one sheet per table)
if ALL_TABLES:
    try:
        with pd.ExcelWriter(os.path.join(RUN_DIR, "all_tables.xlsx")) as xl:
            for name, df in ALL_TABLES.items():
                df.to_excel(xl, sheet_name=name[:31])
    except Exception as err:                         # e.g. openpyxl not installed outside Colab
        print("Excel workbook not written:", err)

print("\nFiles saved in", RUN_DIR)
for fname in sorted(os.listdir(RUN_DIR)):
    print(f"  {fname:32s} {os.path.getsize(os.path.join(RUN_DIR, fname)) / 1024:8.1f} KB")
""")

md(r"""
## Section 11 — Finish: write everything to Google Drive
Google Drive receives the files in the background. This last cell makes sure that everything has been written, then
disconnects Drive from this session. To run more cells afterwards, run Section 2 again first.
""")
code(r"""
# =====================================================================================================
# SECTION 11 - MAKE SURE EVERY FILE IS WRITTEN TO GOOGLE DRIVE
# =====================================================================================================
if SAVE_TO_GOOGLE_DRIVE and IN_COLAB:
    from google.colab import drive
    drive.flush_and_unmount()                       # waits until all files are in Google Drive
    print("All results are in Google Drive:", os.path.join("My Drive", DRIVE_FOLDER_NAME, os.path.basename(RUN_DIR)))
else:
    print("Results are in:", RUN_DIR)
""")

nb = {"cells": cells,
      "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                   "language_info": {"name": "python"}, "colab": {"provenance": []}},
      "nbformat": 4, "nbformat_minor": 5}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write("\n")
print(f"wrote {OUT} with {len(cells)} cells")
