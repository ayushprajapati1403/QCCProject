"""
build_algorithm_notebooks.py - assembles two STANDALONE Google Colab notebooks, one per quantum-inspired algorithm:

  QI_DMO_Colab.ipynb   Part 1: how well QI-DMO schedules cloud tasks (on its own, no other algorithms).
                       Part 2: how it was improved: DMO (original) -> QI-DMO -> QI-DMO + swap move.
  QI_MRFO_Colab.ipynb  Part 1: how well QI-MRFO schedules cloud tasks (on its own).
                       Part 2: how it was improved: MRFO (original) -> QI-MRFO -> + swap move -> + Max-Min start.
                       Part 3: how it was improved for a changing cloud (the V5 steps H6-H13).

Each notebook holds only the code its algorithm needs, copied verbatim function by function from the tested modules
(qi_core.py, qi_quantum.py, qi_dynamic.py), so it runs exactly the code covered by tests/. Every finished run is saved
to a Google Drive folder at once, so an interrupted Colab session can be resumed.
Run:  python notebooks/build/build_algorithm_notebooks.py   (writes notebooks/colab/)
"""
import ast, hashlib, json, os, re, sys, textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
# The repository root (this builder lives in notebooks/build/). `--root DIR` reads DIR/src and writes into DIR/notebooks/
# instead (used by the tests to rebuild into a temporary folder).
ROOT = sys.argv[sys.argv.index("--root") + 1] if "--root" in sys.argv else os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(ROOT, "src")
MODULES = ["qi_core.py", "qi_quantum.py", "qi_dynamic.py"]


# ============================================================================================ verbatim code extraction
def _definitions():
    """{name: source} of every top-level function / class of the modules, verbatim, with the comment lines directly
    above it (section comments), in file order."""
    defs = {}
    for mod in MODULES:
        txt = open(os.path.join(SRC, mod), encoding="utf-8").read()
        lines = txt.splitlines()
        for node in ast.parse(txt).body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                start = min([node.lineno] + [d.lineno for d in node.decorator_list])
                while start > 1 and lines[start - 2].startswith("#") and not lines[start - 2].startswith("# %%"):
                    start -= 1
                defs[node.name] = "\n".join(lines[start - 1:node.end_lineno])
    return defs


DEFS = _definitions()


def needs(name):
    """Top-level definitions that `name` refers to."""
    return {n.id for n in ast.walk(ast.parse(DEFS[name])) if isinstance(n, ast.Name) and n.id in DEFS and n.id != name}


def closure(roots):
    seen, todo = set(), list(roots)
    while todo:
        x = todo.pop()
        if x not in seen:
            seen.add(x); todo.extend(needs(x))
    return seen


def imports_block():
    txt = open(os.path.join(SRC, "qi_core.py"), encoding="utf-8").read()
    return re.search(r"^# %% S2 imports\n(.*?)\n\n", txt, flags=re.M | re.S).group(1)


# ============================================================================================ notebook assembly
class Notebook:
    def __init__(self):
        self.cells = []

    def _cid(self, text):
        return hashlib.sha1(f"{len(self.cells)}:{text}".encode("utf-8")).hexdigest()[:8]

    def md(self, text):
        self.cells.append({"cell_type": "markdown", "id": self._cid(text), "metadata": {},
                           "source": textwrap.dedent(text).strip("\n")})

    def code(self, text):
        self.cells.append({"cell_type": "code", "id": self._cid(text), "metadata": {}, "execution_count": None,
                           "outputs": [], "source": textwrap.dedent(text).strip("\n")})

    def embed(self, header, names):
        """A code cell holding module definitions verbatim, preceded by a comment header."""
        self.code("\n".join(header) + "\n\n" + "\n\n".join(DEFS[n] for n in names) + "\n")

    def save(self, path):
        nb = {"cells": self.cells,
              "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                           "language_info": {"name": "python"}, "colab": {"provenance": []}},
              "nbformat": 4, "nbformat_minor": 5}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
            f.write("\n")
        print(f"wrote {path} with {len(self.cells)} cells")


def fill(text, **kw):
    """Replace <<KEY>> placeholders (avoids brace escaping in the code templates)."""
    for k, v in kw.items():
        text = text.replace(f"<<{k}>>", v)
    assert "<<" not in text, re.findall(r"<<\w+>>", text)
    return text


RULE = "# " + "=" * 101

# ============================================================================================ per-algorithm facts
ALGO = {
    "dmo": dict(
        MAIN="QI-DMO", ORIG="DMO", FILE="QI_DMO_Colab.ipynb",
        FOLDER="QI_DMO_results", FULL_NAME="Dwarf Mongoose Optimization",
        ROOTS=["make_instance", "Objective", "run_dmo", "run_qidmo"],
        GROUPS={"problem": ["CloudInstance", "sample_task_lengths", "sample_vm_speeds", "make_instance", "Objective"],
                "tools": ["Tracker", "critical_exchange"],
                "original": ["decode", "_init_pop", "run_dmo"],
                "mechanism": ["born_probs", "renormalise", "probs", "measure", "basis_state", "project", "purity",
                              "depolarise", "uniform_state", "collapse_rows"],
                "algorithm": ["run_qidmo"]},
        VARIANTS='''{
    # the original algorithm, before our changes: continuous positions rounded to VM numbers
    "DMO (original)":  dict(fn=run_dmo),
    # step 1: quantum-inspired registers instead of rounding (decoherence c = 0.25, as in every project experiment)
    "QI-DMO":          dict(fn=run_qidmo, c=0.25),
    # step 2, first try (test H14): the swap move of QI-MRFO unchanged, on every measured candidate of all three
    # phases (probability 1)
    "QI-DMO + swap in every phase":      dict(fn=run_qidmo, c=0.25, exchange=1.0, exchange_phases="all"),
    # step 2, second version (test H15): the swap move only in the two phases that keep a candidate only if it is
    # better, with probability 0.1 (both chosen on the development problems: results/h15_selection.json)
    "QI-DMO + swap in improving phases": dict(fn=run_qidmo, c=0.25, exchange=0.1, exchange_phases="greedy"),
}''',
        CHANGES='[("QI-DMO", "DMO (original)"), ("QI-DMO + swap in every phase", "QI-DMO"),\n'
                '           ("QI-DMO + swap in improving phases", "QI-DMO")]',
        SCATTER='[("QI-DMO + swap in every phase", "QI-DMO"), ("QI-DMO + swap in improving phases", "QI-DMO")]',
        UNSEEN_SEEDS="list(range(801, 811))"),
    "mrfo": dict(
        MAIN="QI-MRFO", ORIG="MRFO",
        FILE="QI_MRFO_Colab.ipynb", FOLDER="QI_MRFO_results", FULL_NAME="Manta Ray Foraging Optimization",
        ROOTS=["make_instance", "Objective", "run_mrfo", "run_qimrfo", "max_min", "make_dynamic_sequence",
               "adapt_register_state", "repair_schedule", "count_migrations", "map_to_new_vms", "incremental_list_schedule"],
        GROUPS={"problem": ["CloudInstance", "sample_task_lengths", "sample_vm_speeds", "make_instance", "Objective"],
                "tools": ["Tracker", "_list_schedule", "max_min", "critical_exchange"],
                "original": ["decode", "_init_pop", "run_mrfo"],
                "mechanism": ["born_probs", "renormalise", "probs", "measure", "basis_state", "project", "purity",
                              "depolarise", "uniform_state", "remove_vm_state", "add_vm_state", "add_tasks_state",
                              "collapse_rows"],
                "algorithm": ["run_qimrfo"],
                "changing": ["make_dynamic_sequence", "adapt_register_state", "map_to_new_vms", "repair_schedule",
                             "count_migrations", "incremental_list_schedule"]},
        VARIANTS='''{
    # the original algorithm, before our changes: continuous positions rounded to VM numbers
    "MRFO (original)":                 dict(fn=run_mrfo),
    # step 1: quantum-inspired registers instead of rounding (decoherence c = 1, as in every project experiment)
    "QI-MRFO":                         dict(fn=run_qimrfo, c=1.0),
    # step 2: the same algorithm plus the swap move on every measured candidate (probability 1)
    "QI-MRFO + swap":                  dict(fn=run_qimrfo, c=1.0, exchange=1.0),
    # step 3: step 2, started from the Max-Min heuristic's schedule (one of the 30 starting schedules)
    "QI-MRFO + swap + Max-Min start":  dict(fn=run_qimrfo, c=1.0, exchange=1.0, maxmin_start=True),
}''',
        CHANGES='[("QI-MRFO", "MRFO (original)"), ("QI-MRFO + swap", "QI-MRFO"),\n'
                '           ("QI-MRFO + swap + Max-Min start", "QI-MRFO + swap")]',
        SCATTER='[("QI-MRFO + swap", "QI-MRFO")]',
        UNSEEN_SEEDS="list(range(101, 111))"),
}


# ============================================================================================ texts
def title_md(k):
    if k == "dmo":
        return r"""
# QI-DMO: Quantum-Inspired Dwarf Mongoose Optimization for Cloud Task Scheduling
### A standalone notebook: how well QI-DMO schedules cloud tasks, and what each improvement changed

**What this notebook does**
* **Part 1 — Performance of QI-DMO.** QI-DMO is run on its own:
  * 7 benchmark problems (30–200 tasks, 30 runs each);
  * 5 large problems (500–5 000 tasks on 50 VMs, 10 runs each).

  For every problem you get the makespan in seconds (best, worst, mean ± SD), the gap to the theoretical lower bound,
  the energy in Wh, the run time and the convergence curve.
* **Part 2 — How we improved it.** The same problems are solved at each stage of the development:
  **DMO (original) → QI-DMO (quantum-inspired) → QI-DMO + swap move (two versions)**. A third problem set checks the
  versions on 80 problems that no earlier QI-DMO experiment used.
  * **The quantum-inspired step is a large, clear improvement.**
  * **The swap move gives mixed results for QI-DMO.** It helps on the large problems, but it is not an established
    improvement on 30–300-task problems. Part 2 shows exactly where it helps and where it does not.
* **Everything is saved** to a Google Drive folder:
  * every single run (CSV);
  * every table (CSV, plus one Excel file);
  * every figure (PNG);
  * a short summary (`summary.txt`).

**How to run in Google Colab**
1. Open the notebook in Colab (*File → Upload notebook*).
2. In **Settings** (Section 1), choose the mode:
   * `MODE = "quick"`: a short check;
   * `MODE = "full"`: all problems and runs.
3. Click *Runtime → Run all*, and allow access to Google Drive when Colab asks.
4. The results appear in **My Drive → `QI_DMO_results` → `<mode>_run`**.

<<RUNTIME>>

**About "quantum-inspired".** Everything runs on an ordinary CPU; no quantum computer is used.
* **Superposition.** Each task keeps a probability for every VM.
* **Measurement.** A schedule is obtained by sampling these probabilities.
* **Decoherence.** A small noise level keeps every VM possible, so the search does not freeze.
* **What this means.** These are quantum *ideas* used inside a classical algorithm. No quantum advantage is claimed.

**Units.** Task lengths are in MI (million instructions) and VM speeds in MIPS, so times (makespan) are in
**seconds**. Energy is in **Wh**. The *gap* is how much later a schedule finishes than the lower bound, in %.
"""
    return r"""
# QI-MRFO: Quantum-Inspired Manta Ray Foraging Optimization for Cloud Task Scheduling
### A standalone notebook: how well QI-MRFO schedules cloud tasks, and how we improved it

**What this notebook does**
* **Part 1 — Performance of QI-MRFO.** QI-MRFO is run on its own:
  * 7 benchmark problems (30–200 tasks, 30 runs each);
  * 5 large problems (500–5 000 tasks on 50 VMs, 10 runs each).

  For every problem you get the makespan in seconds (best, worst, mean ± SD), the gap to the theoretical lower bound,
  the energy in Wh, the run time and the convergence curve.
* **Part 2 — How we improved it.** The same problems are solved at each stage of the development:
  **MRFO (original) → QI-MRFO (quantum-inspired) → + swap move → + Max-Min start**. A third problem set checks the
  improvements on 80 problems that were never used to set up anything.
* **Part 3 — Improvements for a changing cloud.** Tasks arrive and leave, VMs fail or are added, and moving a running
  task costs something. Six versions of QI-MRFO show step by step how each improvement lowered that cost.
* **Everything is saved** to a Google Drive folder:
  * every single run (CSV);
  * every table (CSV, plus one Excel file);
  * every figure (PNG);
  * a short summary (`summary.txt`).

**How to run in Google Colab**
1. Open the notebook in Colab (*File → Upload notebook*).
2. In **Settings** (Section 1), choose the mode:
   * `MODE = "quick"`: a short check;
   * `MODE = "full"`: all problems and runs.
3. Click *Runtime → Run all*, and allow access to Google Drive when Colab asks.
4. The results appear in **My Drive → `QI_MRFO_results` → `<mode>_run`**.

<<RUNTIME>>

**About "quantum-inspired".** Everything runs on an ordinary CPU; no quantum computer is used.
* **Superposition.** Each task keeps a probability for every VM.
* **Measurement.** A schedule is obtained by sampling these probabilities.
* **Decoherence.** A small noise level keeps every VM possible, so the search does not freeze.
* **What this means.** These are quantum *ideas* used inside a classical algorithm. No quantum advantage is claimed.

**Units.** Task lengths are in MI (million instructions) and VM speeds in MIPS, so times (makespan) are in
**seconds**. Energy is in **Wh**. The *gap* is how much later a schedule finishes than the lower bound, in %.
"""


RUNTIME = {
    "dmo": r"""**Run time.** Free Colab has 2 CPU cores, so the notebook runs 2 runs at a time there.
* **Quick mode:** <<Q>>.
* **Full mode:** <<F>>.
* **Keep the browser tab open.** Free Colab stops idle sessions. If it disconnects, reconnect and click *Run all*
  again: finished runs are read back from Google Drive and skipped.""",
    "mrfo": r"""**Run time.** Free Colab has 2 CPU cores, so the notebook runs 2 runs at a time there.
* **Quick mode:** <<Q>>.
* **Full mode:** <<F>>.
* **Keep the browser tab open.** Free Colab stops idle sessions. If it disconnects, reconnect and click *Run all*
  again: finished runs are read back from Google Drive and skipped.""",
}
RUNTIME_FACTS = {   # quick: measured (lab_log.md); full: estimated from the per-run times of the committed studies
    "dmo": dict(Q="about 3.5 minutes measured with 2 processes on a 2.1 GHz Xeon (while other experiments shared the "
                  "machine); expect about 4–12 minutes on Colab",
                F="about 3.3 CPU-hours, estimated from the measured run times of the project's experiments; with 2 "
                  "processes on free Colab, expect roughly 2–3.5 hours"),
    "mrfo": dict(Q="about 5 minutes measured with 2 processes on a 2.1 GHz Xeon (while other experiments shared the "
                   "machine); expect about 5–15 minutes on Colab",
                 F="about 4 CPU-hours, estimated from the measured run times of the project's experiments; with 2 "
                   "processes on free Colab, expect roughly 2.5–4.5 hours"),
}


def settings_code(k, a):
    part3 = ("\nRUN_PART_3 = True   # Part 3: QI-MRFO in a changing cloud, improvement by improvement\n" if k == "mrfo" else "\n")
    return fill(r'''
<<RULE>>
# SECTION 1 - SETTINGS (the only cell you normally need to edit)
<<RULE>>

# MODE sets how big the experiments are:
#   "quick" : a SUBSET of the full runs with exactly the same settings (fewer problems and runs; 500 and 1000 tasks
#             only for the large problems). Every quick run is identical to the same run in full mode, but the
#             averages use far fewer runs. Use it first to check that everything works.
#   "full"  : all problems and runs. It takes hours on free Colab, but every finished run is saved to Google Drive
#             at once, so an interrupted session can simply be resumed.
MODE = "quick"

# Which parts to run (True = run, False = skip)
RUN_PART_1 = True   # Part 1: performance of <<MAIN>> on its own
RUN_PART_2 = True   # Part 2: how <<MAIN>> was improved, step by step<<PART3>>
# Where to save the results
SAVE_TO_GOOGLE_DRIVE = True               # False: save only inside this Colab session (lost when it ends)
DRIVE_FOLDER_NAME = "<<FOLDER>>"      # this folder is created inside "My Drive"
RUN_NAME = None                           # None -> "<MODE>_run"; give a new name (e.g. "full_run_2") for a fresh folder

# Number of runs executed in parallel. None = use every CPU core (free Colab has 2).
N_WORKERS = None
''', RULE=RULE, MAIN=a["MAIN"], FOLDER=a["FOLDER"], PART3=part3)


SETUP_CODE = r'''
<<RULE>>
# SECTION 2 - SETUP: packages, Google Drive, results folder
<<RULE>>
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
'''


def variants_code(k, a):
    seed_lines = ('''
    if v.get("maxmin_start"):
        kw["init_state"] = {"elite": max_min(inst)}           # start from the Max-Min schedule''' if k == "mrfo" else "")
    return fill(r'''
<<RULE>>
# SECTION 5a - THE VERSIONS OF <<MAIN>> AND ONE RUN
<<RULE>>
# The development steps of <<MAIN>>, in order (Part 2 runs all of them, Part 1 only <<MAIN>> itself).
#   c        = decoherence strength of the quantum-inspired versions (gamma = c / number of tasks)
#   exchange = probability of the swap move
VARIANTS = <<VARIANTS>>
MAIN = "<<MAIN>>"                 # the algorithm of Part 1
STEPS = list(VARIANTS)            # the versions of Part 2, in development order
# The changes that Part 2 measures, as (version after the change, version before it)
CHANGES = <<CHANGES>>
SCATTER = <<SCATTER>>   # swap-move changes drawn problem by problem (Figure 2.2)
POPULATION = 30                   # population size (number of registers / individuals)


class RecordingObjective(Objective):
    # The normal objective (makespan) that also records the best makespan found so far after every 5 % of the
    # evaluation budget, for the convergence curves. It does not change the search in any way.
    def __init__(self, inst, budget, points=20):
        super().__init__(inst)
        self.marks = [budget * k // points for k in range(1, points + 1)]
        self.best, self.curve = np.inf, []

    def __call__(self, assign):
        f = super().__call__(assign)
        self.best = min(self.best, f)
        while len(self.curve) < len(self.marks) and self.n_evals >= self.marks[len(self.curve)]:
            self.curve.append(self.best)
        return f


def problem_name(n, m, dist, het):
    # e.g. "100 tasks, 10 VMs, uniform/high"
    return f"{n} tasks, {m} VMs, {dist}/{het}"


def run_one(job):
    # Run ONE version once on ONE problem and return one result row (makespan in seconds, gap in %, energy in Wh, ...)
    n, m, dist, het = job["problem"]
    inst = make_instance(n, m, seed=job["inst_seed"], task_dist=dist, hetero=het)   # the same problem for every version
    v = VARIANTS[job["variant"]]
    obj = RecordingObjective(inst, job["budget"])          # counts evaluations = the budget unit
    t0 = time.time()
    kw = {}
    if "c" in v:
        kw["decoherence"] = v["c"] / n                     # decoherence strength gamma = c / n
    for key in ("exchange", "exchange_phases"):            # probability of the swap move / where it is applied
        if key in v:
            kw[key] = v[key]<<SEED_LINES>>
    result = v["fn"](inst, obj, job["budget"], P=POPULATION, seed=job["run_seed"], track=False, **kw)
    runtime = time.time() - t0
    makespan, energy = Objective(inst)._raw(result["best_assign"])   # exact makespan (s) and energy (Wh) of the result
    curve = obj.curve + [obj.best] * (len(obj.marks) - len(obj.curve))  # a run may stop a few evaluations early
    lb, lb_p = inst.lower_bound(), inst.lower_bound_pmtn()
    row = {"key": job["key"], "problem_set": job["problem_set"], "variant": job["variant"],
           "problem": problem_name(n, m, dist, het), "tasks": n, "vms": m, "task_lengths": dist, "vm_heterogeneity": het,
           "instance_seed": job["inst_seed"], "run_seed": job["run_seed"], "budget": job["budget"],
           "makespan_s": float(makespan), "energy_Wh": float(energy), "lower_bound_s": float(lb),
           "lower_bound_pmtn_s": float(lb_p), "gap_pct": float(100 * (makespan - lb) / lb),
           "gap_pmtn_pct": float(100 * (makespan - lb_p) / lb_p), "runtime_s": float(runtime),
           "evaluations": int(obj.n_evals)}
    for i, b in enumerate(curve, 1):                       # best makespan after 5 %, 10 %, ..., 100 % of the budget
        row[f"best_at_{5 * i:03d}pct_s"] = float(b)
    return row


def make_jobs(problem_set, variants, problems, inst_seeds, runs, budget):
    # All (version, problem, instance, run) combinations of one problem set
    jobs = []
    for prob in problems:
        for s in inst_seeds:
            for v in variants:
                for r in range(runs):
                    key = f"{problem_set}|{v}|{prob[0]}-{prob[1]}-{prob[2]}-{prob[3]}|inst{s}|run{r}|b{budget}"
                    jobs.append({"key": key, "problem_set": problem_set, "variant": v, "problem": tuple(prob),
                                 "inst_seed": s, "run_seed": r, "budget": budget})
    return jobs
''', RULE=RULE, MAIN=a["MAIN"], VARIANTS=a["VARIANTS"], CHANGES=a["CHANGES"], SCATTER=a["SCATTER"],
                SEED_LINES=seed_lines)


CHANGING_CODE = r'''
<<RULE>>
# SECTION 5b - QI-MRFO IN A CHANGING CLOUD (used by Part 3)
<<RULE>>
# The six change scenarios (100 tasks / 10 VMs unless stated; 8 changes each)
SCENARIOS = {
    "Task churn (20% replaced)":              dict(n=100, m=10, change="churn", rho=0.2),
    "VM speed drift":                         dict(n=100, m=10, change="drift"),
    "VM failure":                             dict(n=100, m=10, change="vm_fail"),
    "VM added":                               dict(n=100, m=10, change="vm_add"),
    "Mixed events":                           dict(n=100, m=10, change="mixed", rho=0.2),
    "Mixed, 200 tasks, 20 VMs, heavy-tailed": dict(n=200, m=20, change="mixed", rho=0.2, task_dist="lognormal"),
}

# The development steps of QI-MRFO for a changing cloud, in order (each adds one improvement to the previous step)
LOCAL_CHANGES = {"churn": 0.0, "drift": 0.0, "vm_fail": 0.0}   # decoherence c after these changes (VM added: c = 1)
CHANGE_STEPS = {
    # 1. after every change, start again from scratch (no memory)
    "1. restart after each change":            dict(strategy="restart"),
    # 2. keep the registers and adapt them to the change (remove a failed VM's column, add a new VM, reset new tasks)
    "2. keeps its registers":                  dict(strategy="continue_struct", repair="greedy"),
    # 3. + the swap move
    "3. + swap move":                          dict(strategy="continue_struct", repair="greedy", exchange=1.0),
    # 4. + start from the schedule that is running now (repaired for the change): fewer tasks are moved
    "4. + starts from the running schedule":   dict(strategy="continue_struct", repair="greedy", exchange=1.0,
                                                    carry_elite=True),
    # 5. + do not do that right after a VM is added (the new VM would stay empty); place new tasks by list scheduling
    "5. + event-aware start":                  dict(strategy="continue_struct", repair="incremental", exchange=1.0,
                                                    carry_elite="except_vm_add"),
    # 6. + no decoherence noise after small changes (the final version)
    "6. + no noise after small changes":       dict(strategy="continue_struct", repair="incremental", exchange=1.0,
                                                    carry_elite="except_vm_add", decoherence_by_event=LOCAL_CHANGES),
}


def run_changing_cloud(seq, budget0, budget, seed, P=30, strategy="continue_struct", repair="greedy", carry_elite=False,
                       exchange=0.0, mig_lambda=None, decoherence_c=1.0, decoherence_by_event=None, mode="born_signed"):
    # QI-MRFO re-optimising after every change of the cloud. This is the QI-MRFO part of the project's run_dynamic
    # (qi_dynamic.py), written out for this notebook; a test (tests/test_algorithm_notebooks.py) checks that both give
    # identical results.
    #   budget0 / budget : evaluations for the first schedule / after each change
    #   mig_lambda       : price of moving a running task; the objective becomes
    #                      makespan x (1 + mig_lambda x moved tasks / movable tasks)
    rng = np.random.default_rng(seed + 7)
    kw = {"exchange": exchange} if exchange else {}
    state, out, prev_best = None, [], None
    for e, (inst, info) in enumerate(seq):
        obj = Objective(inst); B = budget0 if e == 0 else budget
        n = inst.n
        c_e = decoherence_c if (e == 0 or not decoherence_by_event) else decoherence_by_event.get(info["type"], decoherence_c)
        if mig_lambda is not None and e > 0:               # moving a task that keeps running costs something
            ref, forced = map_to_new_vms(prev_best, info)
            movable = ~forced
            if info["type"] == "churn":
                movable[info["idx"]] = False               # new tasks are placed, not moved
            obj = Objective(inst, kind="makespan_migration", ref=ref, mig_mask=movable, lam=mig_lambda)
        init = None
        if e > 0 and strategy != "restart":
            init = adapt_register_state(state, info, mode, rng, struct=(strategy != "continue"))
            use_elite = carry_elite is True or (carry_elite == "except_vm_add" and info["type"] != "vm_add")
            if use_elite:                                  # start from the running schedule, repaired for the change
                init = dict(init); init["elite"] = repair_schedule(prev_best, info, inst, rng, repair)
        r = run_qimrfo(inst, obj, B, P=P, seed=seed * 100 + e, decoherence=c_e / n, mode=mode, init_state=init,
                       track=False, **kw)
        state = r["state"]
        lb = inst.lower_bound()
        moved, forced_moves, persist = count_migrations(prev_best, r["best_assign"], info) if e > 0 else (0, 0, n)
        makespan = float(r["best_f"]) if obj.kind == "makespan" else float(Objective(inst)._raw(r["best_assign"])[0])
        out.append({"epoch": e, "type": None if info is None else info["type"], "makespan": makespan, "lb": lb,
                    "gap": (makespan - lb) / lb, "migrations": moved, "forced": forced_moves,
                    "cost": float(r["best_f"]), "cost_gap": (float(r["best_f"]) - lb) / lb})
        prev_best = np.asarray(r["best_assign"]).copy()
    return out


def run_change(job):
    # Run ONE development step on ONE changing-cloud scenario; averages over the changes (makespan in seconds)
    sc, st = SCENARIOS[job["scenario"]], CHANGE_STEPS[job["step"]]
    seq = make_dynamic_sequence(sc["n"], sc["m"], seed=job["seed"], K=job["K"], change=sc["change"],
                                rho=sc.get("rho", 0.2), task_dist=sc.get("task_dist", "uniform"), hetero="high")
    t0 = time.time()
    out = run_changing_cloud(seq, job["budget0"], job["budget"], seed=job["seed"], P=POPULATION, mig_lambda=job["price"], **st)
    post = out[1:]                                         # the schedules after each change
    return {"key": job["key"], "step": job["step"], "scenario": job["scenario"], "seed": job["seed"], "changes": job["K"],
            "migration_price": job["price"],
            "makespan_s": float(np.mean([o["makespan"] for o in post])),          # makespan after a change (s)
            "lower_bound_s": float(np.mean([o["lb"] for o in post])),
            "gap_pct": float(100 * np.mean([o["gap"] for o in post])),
            "cost_gap_pct": float(100 * np.mean([o["cost_gap"] for o in post])),  # makespan x (1 + price x moves) vs bound
            "migrations_per_change": float(np.mean([o["migrations"] for o in post])),
            "initial_makespan_s": float(out[0]["makespan"]), "runtime_s": float(time.time() - t0)}


def change_jobs(steps, scenarios, seeds, K, budget0, budget, price):
    jobs = []
    for sc in scenarios:
        for s in seeds:
            for st in steps:
                key = f"change|{st}|{sc}|price{price}|seed{s}|K{K}|b{budget0}-{budget}"
                jobs.append({"key": key, "step": st, "scenario": sc, "seed": s, "K": K, "budget0": budget0,
                             "budget": budget, "price": price})
    return jobs
'''

RUNNER_CODE = r'''
<<RULE>>
# SECTION 5<<LETTER>> - RUNNER THAT SAVES EVERY RUN TO GOOGLE DRIVE (and resumes after a disconnect)
<<RULE>>
def check_drive():
    # Stop with a clear message if Google Drive should be used but is not mounted (e.g. after the last cell unmounted
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
        t0, step = time.time(), max(1, len(todo) // 10)
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


ALL_TABLES = {}          # every table produced in this session (also written to one Excel file at the end)


def save_table(df, name, title=None):
    # Show a table in the notebook and save it as RUN_DIR/<name>.csv
    df.to_csv(os.path.join(RUN_DIR, name + ".csv"))
    ALL_TABLES[name] = df
    if title:
        print(title)
    display(df)


def wilcoxon(diff):
    # Two-sided Wilcoxon signed-rank test on paired differences (p-value)
    from scipy import stats
    d = np.asarray(diff, float); d = d[d != 0]
    return float(stats.wilcoxon(d).pvalue) if len(d) >= 2 else float("nan")


def holm(pvalues):
    # Holm-Bonferroni correction when several tests are done together
    p = np.asarray(pvalues, float); order = np.argsort(p); adj = np.empty_like(p); running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (len(p) - rank) * p[idx])); adj[idx] = running
    return adj


def mann_whitney(a, b):
    # Two-sided Mann-Whitney U test for two independent sets of runs (p-value)
    from scipy import stats
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    return float(stats.mannwhitneyu(a, b, alternative="two-sided").pvalue)


def performance_table(df):
    # One row per problem: makespan statistics over the runs (s), gap (%), energy (Wh) and run time (s)
    g = df.groupby("problem", sort=False)
    t = pd.DataFrame({"tasks": g.tasks.first(), "VMs": g.vms.first(), "runs": g.size(),
                      "lower bound (s)": g.lower_bound_s.first(), "makespan mean (s)": g.makespan_s.mean(),
                      "makespan SD (s)": g.makespan_s.std(ddof=1).fillna(0.0), "best (s)": g.makespan_s.min(),
                      "worst (s)": g.makespan_s.max(), "gap to lower bound (%)": g.gap_pct.mean(),
                      "energy (Wh)": g.energy_Wh.mean(), "run time per run (s)": g.runtime_s.mean()})
    return t.round(3)
'''

STYLE_CODE = r'''
<<RULE>>
# SECTION 5<<LETTER>> - PLOT STYLE (one consistent, colour-blind-checked palette for every figure)
<<RULE>>
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
'''


def sizes_code(k, a, letter):
    changing_quick = ('''
        changing=dict(scenarios=["Task churn (20% replaced)", "VM added"], seeds=[601, 602], K=8, budget0=20000,
                      budget=4000, price=0.2),''' if k == "mrfo" else "")
    changing_full = ('''
        changing=dict(scenarios=list(SCENARIOS), seeds=list(range(601, 611)), K=8, budget0=20000, budget=4000,
                      price=0.2),''' if k == "mrfo" else "")
    unseen_note = ("instance seeds 801-810: the fresh problems of the pre-registered swap-move test H15" if k == "dmo" else
                   "instance seeds 101-110: the held-out problems of the pre-registered swap-move test H5")
    return fill(r'''
<<RULE>>
# SECTION 5<<LETTER>> - PROBLEMS AND EXPERIMENT SIZES FOR THE TWO MODES
<<RULE>>
# Benchmark problems: (tasks, VMs, task-length distribution, VM heterogeneity); problem seed 1
BENCHMARK = [(30, 5, "uniform", "high"), (50, 10, "bimodal", "high"), (100, 10, "uniform", "high"),
             (50, 10, "uniform", "none"), (200, 20, "uniform", "high"), (100, 10, "lognormal", "low"),
             (60, 8, "bimodal", "none")]
# Unseen problems: 8 problem types x 10 problems each (<<UNSEEN_NOTE>>)
UNSEEN_TYPES = [(80, 8, "uniform", "high"), (150, 15, "uniform", "high"), (300, 30, "uniform", "high"),
                (100, 10, "bimodal", "high"), (200, 10, "bimodal", "none"), (120, 12, "lognormal", "high"),
                (60, 12, "uniform", "low"), (100, 20, "lognormal", "low")]
UNSEEN_SEEDS = <<UNSEEN_SEEDS>>
# Large problems: 500 to 5000 tasks on 50 VMs; problem seed 1
LARGE = [(n, 50, "uniform", "high") for n in [500, 1000, 1500, 2000, 5000]]

# "full"  = every problem and run.
# "quick" = a subset of the same runs: same budgets, seeds and settings; fewer problems, runs and sizes.
EXPERIMENT_SIZES = {
    "quick": dict(
        benchmark=dict(problems=[BENCHMARK[0], BENCHMARK[2], BENCHMARK[4]], inst_seeds=[1], runs=3, budget=20000),
        unseen=dict(problems=[UNSEEN_TYPES[0], UNSEEN_TYPES[3], UNSEEN_TYPES[5]], inst_seeds=UNSEEN_SEEDS[:2], runs=1,
                    budget=20000),
        large=dict(problems=LARGE[:2], inst_seeds=[1], runs=2, budget=20000),<<CHANGING_QUICK>>
    ),
    "full": dict(
        benchmark=dict(problems=BENCHMARK, inst_seeds=[1], runs=30, budget=20000),
        unseen=dict(problems=UNSEEN_TYPES, inst_seeds=UNSEEN_SEEDS, runs=2, budget=20000),
        large=dict(problems=LARGE, inst_seeds=[1], runs=10, budget=20000),<<CHANGING_FULL>>
    ),
}
SIZES = EXPERIMENT_SIZES[MODE]
CSV = {"benchmark": "benchmark_runs.csv", "unseen": "unseen_runs.csv", "large": "large_runs.csv"}


def jobs_for(problem_set, variants):
    # every run of one problem set for the given versions, in the size of the current MODE
    cfg = SIZES[problem_set]
    return make_jobs(problem_set, variants, cfg["problems"], cfg["inst_seeds"], cfg["runs"], cfg["budget"])


# Save the settings of this run next to the results (for reproducibility)
with open(os.path.join(RUN_DIR, "settings.json"), "w") as f:
    json.dump({"mode": MODE, "sizes": SIZES, "population": POPULATION, "workers": N_WORKERS,
               "python": platform.python_version(), "numpy": np.__version__, "started": time.strftime("%Y-%m-%d %H:%M:%S")},
              f, indent=1, default=str)
print(json.dumps(SIZES, indent=1, default=str))
''', RULE=RULE, LETTER=letter, UNSEEN_NOTE=unseen_note, UNSEEN_SEEDS=a["UNSEEN_SEEDS"], CHANGING_QUICK=changing_quick,
                CHANGING_FULL=changing_full)


def selfcheck_code(k, a):
    dyn = ('''
# Every changing-cloud step, twice, on the "Mixed events" scenario with 2 changes and small budgets
for _st in CHANGE_STEPS:
    _job = {"key": "check", "step": _st, "scenario": "Mixed events", "seed": 0, "K": 2, "budget0": 600, "budget": 300,
            "price": 0.2}
    _r1, _r2 = run_change(_job), run_change(_job)
    assert _r1["makespan_s"] >= _r1["lower_bound_s"] - 1e-9, f"{_st} beat the lower bound (impossible)"
    assert _r1["cost_gap_pct"] == _r2["cost_gap_pct"], f"{_st} is not reproducible"''' if k == "mrfo" else "")
    tail = ('print("Self-check passed: all", len(VARIANTS), "versions and", len(CHANGE_STEPS), "changing-cloud steps work.")'
            if k == "mrfo" else 'print("Self-check passed: all", len(VARIANTS), "versions work.")')
    return fill(r'''
<<RULE>>
# SECTION 6 - SELF-CHECK: valid schedules, budget respected, reproducible with the same seed
<<RULE>>
# Every version, twice, on a tiny problem (12 tasks, 3 VMs) with a budget of 600 evaluations
for _name in VARIANTS:
    _job = {"key": "check", "problem_set": "check", "variant": _name, "problem": (12, 3, "uniform", "high"),
            "inst_seed": 0, "run_seed": 0, "budget": 600}
    _r1, _r2 = run_one(_job), run_one(_job)
    assert _r1["evaluations"] <= 600, f"{_name} exceeded the budget"
    assert _r1["makespan_s"] == _r2["makespan_s"], f"{_name} is not reproducible"
    assert _r1["makespan_s"] >= _r1["lower_bound_s"] - 1e-9, f"{_name} beat the lower bound (impossible)"
    assert _r1["best_at_100pct_s"] == _r1["makespan_s"], f"{_name}: convergence curve does not end at the result"<<DYN>>
<<TAIL>>
''', RULE=RULE, DYN=dyn, TAIL=tail)


PART1_CODE = r'''
<<RULE>>
# PART 1 - PERFORMANCE OF <<MAIN>> ON ITS OWN
<<RULE>>
if RUN_PART_1:
    # ---- run <<MAIN>> on the benchmark problems and on the large problems (each run is saved at once) -------
    bench = run_jobs(jobs_for("benchmark", [MAIN]), run_one, CSV["benchmark"])
    large = run_jobs(jobs_for("large", [MAIN]), run_one, CSV["large"])

    # ---- Tables 1.1 and 1.2: one row per problem ------------------------------------------------------------
    save_table(performance_table(bench), "1_1_benchmark_performance",
               f"Table 1.1 - {MAIN} on the benchmark problems (makespan in seconds, energy in Wh)")
    save_table(performance_table(large), "1_2_large_performance",
               f"Table 1.2 - {MAIN} on the large problems, 50 VMs (makespan in seconds, energy in Wh)")

    # ---- Figure 1.1: convergence (gap to the lower bound vs evaluations, mean over the runs) -----------------
    cols = [c for c in bench.columns if c.startswith("best_at_")]
    frac = np.array([int(c[8:11]) for c in cols]) / 100               # 0.05, 0.10, ..., 1.00 of the budget
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    for (prob, sub), col in zip(bench.groupby("problem", sort=False), PALETTE):
        gap = ((sub[cols].values - sub.lower_bound_s.values[:, None]) / sub.lower_bound_s.values[:, None] * 100).mean(0)
        x = frac * sub.budget.iloc[0]
        ax.plot(x, gap, color=col, linewidth=2, label=prob, zorder=2)
        ax.plot(x[-1], gap[-1], "o", color=col, markersize=6, markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)
    ax.set_yscale("log"); ax.yaxis.set_major_formatter(PERCENT)
    style(ax, f"Figure 1.1 - {MAIN}: convergence on the benchmark problems (mean of the runs)",
          "evaluations (schedules tried)", "gap to the lower bound (%, log scale)")
    ax.legend(frameon=False, fontsize=8, loc="center left", bbox_to_anchor=(1.01, 0.5))
    save_figure(fig, "1_1_convergence.png")

    # ---- Figure 1.2: the best schedule found for the 100-task problem - finish time of every VM -------------
    prob = (100, 10, "uniform", "high")
    sub = bench[bench.problem == problem_name(*prob)]
    best = sub.loc[sub.makespan_s.idxmin()]
    inst = make_instance(*prob[:2], seed=int(best.instance_seed), task_dist=prob[2], hetero=prob[3])
    job = {"key": "figure", "problem_set": "figure", "variant": MAIN, "problem": prob, "inst_seed": int(best.instance_seed),
           "run_seed": int(best.run_seed), "budget": int(best.budget)}
    v = VARIANTS[MAIN]                                                  # re-run the best run to get its schedule
    res = v["fn"](inst, Objective(inst), job["budget"], P=POPULATION, seed=job["run_seed"], track=False,
                  decoherence=v["c"] / inst.n)
    a = res["best_assign"]
    loads = np.bincount(a, weights=inst.et[np.arange(inst.n), a], minlength=inst.m)   # busy time of every VM (s)
    assert abs(loads.max() - best.makespan_s) < 1e-9, "the re-run must reproduce the saved best run"
    order = np.argsort(inst.vm_mips)                                    # slowest VM on the left
    fig, ax = plt.subplots(figsize=(8.0, 3.6))
    colors = [PALETTE[1] if loads[j] == loads.max() else PALETTE[0] for j in order]
    ax.bar(range(inst.m), loads[order], color=colors, width=0.7, edgecolor=SURFACE, linewidth=2, zorder=2)
    ax.axhline(inst.lower_bound(), color=INK2, linewidth=1, linestyle="--", zorder=3)
    ax.annotate(f"lower bound {inst.lower_bound():.2f} s", (inst.m - 0.5, inst.lower_bound()), xytext=(0, 4),
                textcoords="offset points", ha="right", fontsize=8, color=INK2)
    ax.set_xticks(range(inst.m)); ax.set_xticklabels([f"{inst.vm_mips[j]:.0f}" for j in order])
    style(ax, f"Figure 1.2 - {MAIN}: finish time of every VM in the best schedule (100 tasks, 10 VMs)\n"
              f"makespan {loads.max():.2f} s (orange = the busiest VM, which sets the makespan)",
          "VM speed (MIPS), slowest to fastest", "finish time (s)")
    save_figure(fig, "1_2_vm_finish_times.png")

    # ---- Figure 1.3: large problems - gap and run time as the number of tasks grows (two charts) ------------
    per_size = large.groupby("tasks")[["gap_pct", "runtime_s"]].mean()
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.6))
    for ax, colname, label, title in [(axes[0], "gap_pct", "gap to the lower bound (%)", "gap"),
                                      (axes[1], "runtime_s", "run time per run (s)", "run time")]:
        ax.plot(per_size.index, per_size[colname], color=PALETTE[0], linewidth=2, zorder=2)
        ax.plot(per_size.index, per_size[colname], "o", color=PALETTE[0], markersize=6, markeredgecolor=SURFACE,
                markeredgewidth=2, zorder=3)
        ax.set_xticks(per_size.index); ax.set_xticklabels([f"{n:,}" for n in per_size.index])
        style(ax, f"Figure 1.3 - {MAIN}: {title} vs number of tasks", "number of tasks (50 VMs)", label)
    fig.tight_layout()
    save_figure(fig, "1_3_large_problems.png")
else:
    print("Part 1 skipped (RUN_PART_1 = False).")
'''

PART2_CODE = r'''
<<RULE>>
# PART 2 - HOW <<MAIN>> WAS IMPROVED, STEP BY STEP
<<RULE>>
if RUN_PART_2:
    # ---- run every version on the three problem sets (runs already saved in Part 1 are reused) ---------------
    R = {ps: run_jobs(jobs_for(ps, STEPS), run_one, CSV[ps]) for ps in ["benchmark", "unseen", "large"]}
    B, U, L = R["benchmark"], R["unseen"], R["large"]

    # ---- Tables 2.1-2.3: the mean result of every version on every problem ----------------------------------
    t = B.pivot_table(index="problem", columns="variant", values="makespan_s", aggfunc="mean", sort=False)[STEPS]
    t.insert(0, "lower bound (s)", B.groupby("problem", sort=False).lower_bound_s.first())
    save_table(t.round(3), "2_1_benchmark_versions", "Table 2.1 - benchmark problems: mean makespan (s) of every version")
    per_problem = U.groupby(["problem", "instance_seed", "variant"]).gap_pmtn_pct.mean().unstack("variant")[STEPS]
    t = per_problem.groupby(level=0, sort=False).mean()
    t.loc["ALL unseen problems"] = per_problem.mean()
    save_table(t.round(3), "2_2_unseen_versions",
               "Table 2.2 - unseen problems: mean gap to the (preemptive) lower bound (%) of every version")
    t = L.pivot_table(index="tasks", columns="variant", values="makespan_s", aggfunc="mean")[STEPS]
    t.insert(0, "lower bound (s)", L.groupby("tasks").lower_bound_s.first())
    save_table(t.round(3), "2_3_large_versions", "Table 2.3 - large problems (50 VMs): mean makespan (s) of every version")

    # ---- Table 2.4: what each change gained, on each problem set ---------------------------------------------
    #   benchmark / large: one unit = one problem; test = Mann-Whitney on its runs (Holm across the problems)
    #   unseen:            one unit = one problem (mean of its runs); test = Wilcoxon over the 10 problems of each
    #                      type (Holm across the 8 types), plus one Wilcoxon over all problems ("pooled")
    rows = []
    for after, before in CHANGES:
        for ps, df, col in [("benchmark", B, "gap_pct"), ("unseen", U, "gap_pmtn_pct"), ("large", L, "gap_pct")]:
            if ps == "unseen":
                d_all = per_problem[after] - per_problem[before]
                groups = [(p, d) for p, d in d_all.groupby(level=0, sort=False)]
                diffs, pvals = [d.mean() for _, d in groups], [wilcoxon(d) for _, d in groups]
                units, better, pooled = len(d_all), int((d_all < 0).sum()), wilcoxon(d_all)
                g_before, g_after = per_problem[before].mean(), per_problem[after].mean()
            else:
                diffs, pvals = [], []
                for p, sub in df.groupby("problem", sort=False):
                    xa, xb = sub[sub.variant == after][col], sub[sub.variant == before][col]
                    diffs.append(xa.mean() - xb.mean()); pvals.append(mann_whitney(xa, xb))
                units, better, pooled = len(diffs), int(sum(x < 0 for x in diffs)), float("nan")
                g_before = df[df.variant == before].groupby("problem")[col].mean().mean()
                g_after = df[df.variant == after].groupby("problem")[col].mean().mean()
            ph = holm(np.nan_to_num(pvals, nan=1.0))
            rows.append({"change": f"{before}  ->  {after}", "problem set": ps,
                         "gap before (%)": g_before, "gap after (%)": g_after, "change (percentage points)": g_after - g_before,
                         "better on": f"{better} of {units} problems",
                         "significantly better on": int(sum((x < 0) and (q < 0.05) for x, q in zip(diffs, ph))),
                         "significantly worse on": int(sum((x > 0) and (q < 0.05) for x, q in zip(diffs, ph))),
                         "p (all unseen problems)": pooled})
    gains = pd.DataFrame(rows)
    save_table(gains.round(4), "2_4_what_each_change_gained",
               "Table 2.4 - what each change gained (gap = mean over problems; lower is better; unseen problems: "
               "'significantly' counts problem types)")

    # ---- Figure 2.1: average gap of every version, for each problem set --------------------------------------
    fig, ax = plt.subplots(figsize=(8.8, 4.2))
    sets = [("benchmark problems", B, "gap_pct"), ("unseen problems (preemptive bound)", U, "gap_pmtn_pct"),
            ("large problems", L, "gap_pct")]
    ends = []                                                         # last value of each line, for the labels
    for (label, df, col), color in zip(sets, PALETTE):
        y = [df[df.variant == s].groupby("problem")[col].mean().mean() for s in STEPS]
        ax.plot(range(len(STEPS)), y, color=color, linewidth=2, label=label, zorder=2)
        ax.plot(range(len(STEPS)), y, "o", color=color, markersize=6, markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)
        ends.append(y[-1])
    order = np.argsort(ends)
    nudge = np.zeros(len(ends))
    for a, b in zip(order[:-1], order[1:]):                           # labels closer than 15 % would overlap
        if ends[b] < ends[a] * 1.15:
            nudge[b] = nudge[a] + 9
    for v, dy in zip(ends, nudge):
        ax.annotate(f"{v:.2f} %", (len(STEPS) - 1, v), xytext=(8, dy), textcoords="offset points", va="center",
                    fontsize=8, color=INK2)
    ax.set_xticks(range(len(STEPS))); ax.set_xticklabels([s.replace(" + ", "\n+ ").replace(", ", ",\n") for s in STEPS])
    ax.set_yscale("log"); ax.yaxis.set_major_formatter(PERCENT)
    style(ax, f"Figure 2.1 - {MAIN}: average gap to the lower bound of every version (lower is better)",
          "", "average gap (%, log scale)")
    ax.legend(frameon=False, fontsize=8)
    save_figure(fig, "2_1_versions.png")

    # ---- Figure 2.2: every unseen problem - with vs without the swap move ------------------------------------
    fig, axes = plt.subplots(1, len(SCATTER), figsize=(5.4 * len(SCATTER), 5.0), squeeze=False)
    floor = 1e-3                                                      # a gap of 0 % cannot be drawn on a log axis
    if (per_problem.values < floor).any():
        print(f"Figure 2.2: gaps below {floor} % (e.g. an optimal schedule) are drawn at {floor} %.")
    lo = max(floor, per_problem[[v for pair in SCATTER for v in pair]].values.min()) * 0.8
    hi = per_problem[[v for pair in SCATTER for v in pair]].values.max() * 1.25
    for ax, (after, before) in zip(axes[0], SCATTER):
        x, y = np.maximum(per_problem[before].values, floor), np.maximum(per_problem[after].values, floor)
        k = int((per_problem[after] < per_problem[before]).sum())
        ax.scatter(x, y, s=28, color=PALETTE[0], edgecolors=SURFACE, linewidths=1, zorder=3)
        ax.plot([lo, hi], [lo, hi], color=INK2, linewidth=1, linestyle="--", zorder=2)
        ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
        ax.xaxis.set_major_formatter(PERCENT); ax.yaxis.set_major_formatter(PERCENT)
        style(ax, f"{after}\nbelow the dashed line = better with the swap move ({k} of {len(per_problem)} problems)",
              f"gap without the swap move (%, {before})", "gap with the swap move (%)")
    fig.suptitle("Figure 2.2 - every unseen problem as one point (a gap of 0 %, an optimal schedule, is drawn at 0.001 %)",
                 x=0.02, ha="left", fontsize=10, color=INK)
    fig.tight_layout()
    save_figure(fig, "2_2_swap_each_problem.png")
else:
    print("Part 2 skipped (RUN_PART_2 = False).")
'''

PART3_CODE = r'''
<<RULE>>
# PART 3 - QI-MRFO IN A CHANGING CLOUD: HOW EACH IMPROVEMENT HELPED
<<RULE>>
if RUN_PART_3:
    cfg = SIZES["changing"]
    STEPS3 = list(CHANGE_STEPS)
    D = run_jobs(change_jobs(STEPS3, cfg["scenarios"], cfg["seeds"], cfg["K"], cfg["budget0"], cfg["budget"], cfg["price"]),
                 run_change, "changing_cloud_runs.csv")

    # ---- Table 3.1: every step, averaged over all scenarios and runs ------------------------------------------
    cost = D.pivot_table(index=["scenario", "seed"], columns="step", values="cost_gap_pct")[STEPS3]
    g = D.groupby("step")
    t = pd.DataFrame({"makespan after a change (s)": g.makespan_s.mean(), "tasks moved per change": g.migrations_per_change.mean(),
                      "cost gap (%)": g.cost_gap_pct.mean()}).reindex(STEPS3)
    t["better than the step before in"] = ["-"] + [f"{int((cost[b] < cost[a]).sum())} of {len(cost)} runs"
                                                   for a, b in zip(STEPS3[:-1], STEPS3[1:])]
    t["p (Wilcoxon, vs the step before)"] = [np.nan] + [wilcoxon(cost[b] - cost[a]) for a, b in zip(STEPS3[:-1], STEPS3[1:])]
    save_table(t.round(4), "3_1_changing_cloud_steps",
               f"Table 3.1 - changing cloud, migration price {cfg['price']}: every development step (lower is better)")

    # ---- Table 3.2: cost gap (%) per scenario ----------------------------------------------------------------
    t = D.pivot_table(index="scenario", columns="step", values="cost_gap_pct", aggfunc="mean", sort=False)[STEPS3]
    save_table(t.round(3), "3_2_changing_cloud_by_scenario", "Table 3.2 - cost gap (%) per scenario and step")

    # ---- Figure 3.1: cost gap and tasks moved per step (two charts) -------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.0))
    labels = [s.split(". ", 1)[0] for s in STEPS3]
    means = D.groupby("step")[["cost_gap_pct", "migrations_per_change"]].mean().reindex(STEPS3)
    for ax, col, ylabel, title in [(axes[0], "cost_gap_pct", "cost gap (%)", "cost gap"),
                                   (axes[1], "migrations_per_change", "tasks moved per change", "tasks moved")]:
        y = means[col]
        ax.plot(range(len(STEPS3)), y, color=PALETTE[0], linewidth=2, zorder=2)
        ax.plot(range(len(STEPS3)), y, "o", color=PALETTE[0], markersize=6, markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)
        ax.set_xticks(range(len(STEPS3))); ax.set_xticklabels(labels)
        style(ax, f"Figure 3.1 - {title} at every step (lower is better)", "development step (see Table 3.1)", ylabel)
    fig.tight_layout()
    save_figure(fig, "3_1_changing_cloud_steps.png")
else:
    print("Part 3 skipped (RUN_PART_3 = False).")
'''


def summary_code(k, a):
    part3 = r'''
C3 = complete_runs("changing_cloud_runs.csv",
                   change_jobs(list(CHANGE_STEPS), SIZES["changing"]["scenarios"], SIZES["changing"]["seeds"],
                               SIZES["changing"]["K"], SIZES["changing"]["budget0"], SIZES["changing"]["budget"],
                               SIZES["changing"]["price"]), "Part 3 (changing cloud)")
if C3 is not None:
    g = C3.groupby("step")[["cost_gap_pct", "migrations_per_change", "makespan_s"]].mean().reindex(list(CHANGE_STEPS))
    lines += [f"Part 3 - changing cloud (migration price {SIZES['changing']['price']}), mean over "
              f"{C3.scenario.nunique()} scenarios x {C3.seed.nunique()} runs:"]
    lines += [f"  {s}: cost gap {r.cost_gap_pct:.2f} %, tasks moved per change {r.migrations_per_change:.1f}, "
              f"makespan {r.makespan_s:.2f} s" for s, r in g.iterrows()]
    lines.append("")
''' if k == "mrfo" else ""
    return fill(r'''
<<RULE>>
# SECTION 7 - SUMMARY (computed from the saved runs) AND LIST OF SAVED FILES
<<RULE>>
lines = [f"{MAIN} for cloud task scheduling - results summary ({MODE} mode)", f"Folder: {RUN_DIR}",
         f"Written: {time.strftime('%Y-%m-%d %H:%M:%S')}", ""]
if MODE == "quick":
    lines += ["NOTE: quick mode runs a subset of the full runs with the same settings. Each run equals the same run in",
              "full mode, but the averages below use far fewer runs; set MODE = 'full' for the complete results.", ""]


def complete_runs(csv_name, jobs, label):
    # The saved runs of one part if ALL of them are saved, else None (with a note in the summary)
    df = read_runs(csv_name, jobs)
    if df is None or len(df) == 0:
        lines.extend([f"{label}: no saved runs (not run yet).", ""])
        return None
    if len(df) < len(jobs):
        lines.extend([f"{label}: only {len(df)} of {len(jobs)} runs are saved - run its cell again to finish it.", ""])
        return None
    return df


for ps, label in [("benchmark", "Benchmark problems"), ("large", "Large problems (50 VMs)")]:
    df = complete_runs(CSV[ps], jobs_for(ps, [MAIN]), f"Part 1 - {label}")
    if df is not None:
        lines.append(f"Part 1 - {MAIN} on the {label.lower()}: mean makespan (s), best (s), gap (%), run time (s)")
        for p, sub in df.groupby("problem", sort=False):
            lines.append(f"  {p}: {sub.makespan_s.mean():.2f} (best {sub.makespan_s.min():.2f}; lower bound "
                         f"{sub.lower_bound_s.iloc[0]:.2f}), gap {sub.gap_pct.mean():.3f} %, {sub.runtime_s.mean():.1f} s per run")
        lines.append("")

for ps, label, col in [("benchmark", "benchmark problems", "gap_pct"), ("unseen", "unseen problems", "gap_pmtn_pct"),
                       ("large", "large problems", "gap_pct")]:
    df = complete_runs(CSV[ps], jobs_for(ps, STEPS), f"Part 2 - {label}")
    if df is not None:
        lines.append(f"Part 2 - {label}: average gap to the lower bound of every version")
        lines += [f"  {s}: {df[df.variant == s].groupby('problem')[col].mean().mean():.3f} %" for s in STEPS]
        per = df.groupby(["problem", "instance_seed", "variant"])[col].mean().unstack("variant")   # one row per problem
        for after, before in CHANGES:
            d = per[after] - per[before]
            lines.append(f"  {before} -> {after}: better on {int((d < 0).sum())} of {len(d)} problems, worse on "
                         f"{int((d > 0).sum())}" + (f" (Wilcoxon p = {wilcoxon(d):.2g})" if ps == "unseen" else ""))
        lines.append("")
<<PART3>>
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
    print(f"  {fname:36s} {os.path.getsize(os.path.join(RUN_DIR, fname)) / 1024:8.1f} KB")
''', RULE=RULE, PART3=part3)


FINISH_CODE = r'''
<<RULE>>
# SECTION 8 - MAKE SURE EVERY FILE IS WRITTEN TO GOOGLE DRIVE
<<RULE>>
if SAVE_TO_GOOGLE_DRIVE and IN_COLAB:
    from google.colab import drive
    drive.flush_and_unmount()                       # waits until all files are in Google Drive
    print("All results are in Google Drive:", os.path.join("My Drive", DRIVE_FOLDER_NAME, os.path.basename(RUN_DIR)))
else:
    print("Results are in:", RUN_DIR)
'''


FOUND_PART2 = {
    "dmo": """**What the project's pre-registered tests found** (the tables below recompute the same comparisons from this
notebook's own runs; its unseen problems are the H15 test problems):
* **DMO → QI-DMO.** Better on all 80 fresh problems of H14 (−67 percentage points of gap). On this notebook's unseen
  problems (the H15 set) it is better on 76 of 80. DMO wins four problems of the type with 20 near-identical VMs and
  heavy-tailed tasks, where the longest task alone sets the makespan.
* **Swap move in every phase (H14).**
  * On 30–300-task problems QI-DMO got **worse**: worse on 65 of 80 fresh problems, in both H14 and H15.
  * On the large problems it was **better** at every size, e.g. 1 198.89 vs 1 402.89 s at 5 000 tasks.
* **Swap move in improving phases (H15).**
  * It removed that harm: better than the every-phase version on 71 of 80 problems.
  * Against QI-DMO without the swap it was better on average (−0.81 percentage points, better on 47 of 80), but the
    pre-registered test missed its bar (Wilcoxon p = 0.067).
  * On large problems it was better on average, but not significantly.
* **Conclusion.** For QI-DMO, the swap move is **not** an established improvement on 30–300 tasks. On large problems
  (500–5 000 tasks) the every-phase version helps.""",
    "mrfo": """**What the project's pre-registered tests found** (the tables below recompute the same comparisons from this
notebook's own runs; its unseen problems are the H5 test problems):
* **MRFO → QI-MRFO.** Better on every benchmark problem and at every large size.
* **+ swap move (H5).** Better on 76 of 80 held-out problems (−2.86 percentage points of gap). It was also better in
  every run at every large size.
* **+ Max-Min start (H7).** −0.51 percentage points, better on 67 of 80 fresh problems, worse on 11. It removes the
  plateau on problems where Max-Min is already optimal (3.11 → 0.02 %).
* **An honest limit (H7).** For one-time scheduling, a simple local search with the same swap move and start does as
  well or slightly better. QI-MRFO's own strength is the changing cloud (Part 3).""",
}

# ============================================================================================ build one notebook
def build(k):
    a = ALGO[k]
    needed = closure(a["ROOTS"])
    grouped = [n for names in a["GROUPS"].values() for n in names]
    assert set(grouped) == needed and len(grouped) == len(set(grouped)), (sorted(needed ^ set(grouped)), k)
    nb = Notebook()
    main, orig = a["MAIN"], a["ORIG"]

    nb.md(fill(title_md(k), RUNTIME=fill(RUNTIME[k], **RUNTIME_FACTS[k])))
    nb.md("## Section 1 — Settings\nThis is the only cell you normally need to change.")
    nb.code(settings_code(k, a))
    nb.md(r"""
## Section 2 — Setup: packages, Google Drive and the results folder
* Colab already has every package this notebook needs (NumPy, SciPy, pandas, Matplotlib); anything missing is installed.
* **Google Drive.** It is mounted, and the results folder is created, e.g. `My Drive/<<FOLDER>>/quick_run`.
* **Running outside Colab.** The results go to a local folder with the same name.
""".replace("<<FOLDER>>", a["FOLDER"]))
    nb.code(fill(SETUP_CODE, RULE=RULE))

    # ---------------------------------------------------------------- the code (verbatim from the tested modules)
    nb.md(r"""
## Section 3 — The cloud task scheduling problem
* **The problem.** There are $n$ independent tasks (cloudlets) with lengths $L_i$ in MI, and $m$ virtual machines with
  speeds $S_j$ in MIPS.
* **Execution time.** Task $i$ on VM $j$ takes $ET_{ij} = L_i / S_j$ seconds.
* **A schedule** assigns every task to one VM: an integer vector $a$ with $a_i \in \{0,\dots,m-1\}$.
* **Makespan.** The objective is the time at which the last VM finishes: $\max_j \sum_{i:a_i=j} ET_{ij}$. Lower is better.
* **Lower bound.** No schedule can finish before $\max(\sum L / \sum S,\ \max L / \max S)$. The tighter "preemptive"
  bound `lower_bound_pmtn` is also computed. The *gap* is how far above the lower bound a schedule is, in %.
* **Energy.** A linear power model (idle and busy power per VM) gives the energy of a schedule in Wh.
* **Problem generator.** Task lengths are uniform, lognormal (heavy-tailed) or bimodal. VM speeds have high, low or no
  heterogeneity. Everything is seeded, so every run can be reproduced exactly.

The code cells of Sections 3 and 4 are copied unchanged, function by function, from the project's tested modules
(`qi_core.py`, `qi_quantum.py`, `qi_dynamic.py`). They contain only what this notebook needs.
""")
    nb.embed([RULE, "# SECTION 3 - PROBLEM MODEL (verbatim from qi_core.py)",
              "#   CloudInstance - tasks, VMs, execution-time matrix, lower bounds",
              "#   make_instance - seeded random problem generator",
              "#   Objective     - makespan / energy of a schedule; counts evaluations (the budget unit)", RULE],
             a["GROUPS"]["problem"])
    # the imports go first (the embed helper takes definitions only)
    nb.cells[-1]["source"] = nb.cells[-1]["source"].replace(RULE + "\n\n", RULE + "\n" + imports_block() + "\n\n", 1)

    if k == "dmo":
        tools_md = r"""
## Section 4 — The algorithms
**4a. Tools.** `Tracker` records run diagnostics (switched off in the experiments; it does not change the results).
**`critical_exchange` is the swap move.**
* **What it does.** It takes a task from the *busiest* VM and swaps it with a shorter task on another VM, or moves it
  if no shorter task exists.
* **Why it can help.** QI-DMO samples every task independently, so it almost never produces this correlated two-task
  change. The move clearly helped QI-MRFO; for QI-DMO the results are mixed (Part 2).
"""
        orig_md = r"""
**4b. The original DMO** (Dwarf Mongoose Optimization; Agushaka, Ezugwu and Abualigah, 2022). The mongoose group
forages in three phases: the *alpha group* searches around a chosen alpha, *scouts* look for new sleeping mounds, and
*babysitters* are replaced when the group stops improving.
* **Rounding.** DMO is a continuous algorithm. To schedule tasks, each task's position is rounded to a VM number, as
  is usual in the cloud-scheduling literature.
* **Why this is a problem.** One DMO move then changes about half of all task assignments at once (35–61 % in the
  project's benchmark), which is close to drawing a new random schedule.
"""
        qi_md = r"""
**4c. The quantum-inspired mechanism.**
* **Register per task.** Each task keeps a *register*: an amplitude vector with one entry per VM. Its probabilities
  (amplitude² under the Born rule) give the chance that the task goes to each VM.
* **Measurement** samples a VM for every task and so gives a concrete schedule, which is then evaluated.
* **Decoherence** is a small uniform mixing of strength γ = c / n. It keeps every VM possible for every task.
* **`collapse_rows`** sets the registers of the two swapped tasks to the swapped outcome (used by the swap move).

**4d. QI-DMO.** DMO's three phases act on the registers instead of rounded positions: the alpha group moves towards
the alpha's *measured schedule*, scouts move away from another mongoose's register, and babysitters are reset by
full decoherence.
* **Why it helps.** A move changes far fewer tasks than with rounding (22–28 % in the project's benchmark).
* **The swap move.** It was first developed for QI-MRFO. For this notebook it was added to QI-DMO, in two versions:
  * **In every phase** (`exchange=1.0, exchange_phases="all"`): the QI-MRFO move unchanged, on every measured
    candidate (test H14).
  * **In improving phases** (`exchange=0.1, exchange_phases="greedy"`): only in the alpha-group and scout phases, which
    keep a candidate only if it is better, with probability 0.1 (test H15). Both settings were chosen on development
    problems before the test.
  * **Why two versions.** QI-DMO's third phase (next position) keeps every candidate, even a worse one. There, a swap
    that makes the schedule worse is kept too.
* **Settings in all experiments.** c = 0.25, population 30, 20 000 evaluations per run.
"""
    else:
        tools_md = r"""
## Section 4 — The algorithms
**4a. Tools.** `Tracker` records run diagnostics (switched off in the experiments; it does not change the results).
`max_min` is the Max-Min list-scheduling heuristic, used as a starting schedule in the last static step.
**`critical_exchange` is the swap move.**
* **What it does.** It takes a task from the *busiest* VM and swaps it with a shorter task on another VM, or moves it
  if no shorter task exists.
* **Why it helps.** QI-MRFO samples every task independently, so it almost never produces this correlated two-task
  change, which is exactly what a nearly balanced schedule needs.
"""
        orig_md = r"""
**4b. The original MRFO** (Manta Ray Foraging Optimization; Zhao, Zhang and Wang, 2020). Manta rays forage in three
ways: *chain foraging* (follow the ray in front and the best food), *cyclone foraging* (spiral around the best food,
or around a random point to explore) and *somersault foraging* (flip around the best food).
* **Rounding.** MRFO is a continuous algorithm. To schedule tasks, each task's position is rounded to a VM number, as
  is usual in the cloud-scheduling literature.
* **Why this is a problem.** One MRFO move then changes about half of all task assignments at once (40–63 % in the
  project's benchmark), which is close to drawing a new random schedule.
"""
        qi_md = r"""
**4c. The quantum-inspired mechanism.**
* **Register per task.** Each task keeps a *register*: an amplitude vector with one entry per VM. Its probabilities
  (amplitude² under the Born rule) give the chance that the task goes to each VM.
* **Measurement** samples a VM for every task and so gives a concrete schedule, which is then evaluated.
* **Decoherence** is a small uniform mixing of strength γ = c / n. It keeps every VM possible for every task.
* **`collapse_rows`** sets the registers of the two swapped tasks to the swapped outcome (used by the swap move).
* **For a changing cloud** there are simple rules: `remove_vm_state` deletes a failed VM's column, `add_vm_state` gives a
  new VM a uniform share, and `add_tasks_state` gives new tasks uniform registers.

**4d. QI-MRFO.** MRFO's chain, cyclone and somersault foraging act on the registers instead of rounded positions. The
best food is the best schedule found so far, written as a register (all probability on its VM, for every task).
* **Why it helps.** A move changes far fewer tasks than with rounding (10–14 % in the project's benchmark).
* **The swap move.** `exchange` is the probability of applying it to a measured candidate (1 in all experiments).
* **The Max-Min start.** `init_state={"elite": schedule}` puts a given schedule into the starting population.
* **Settings in all experiments.** c = 1, population 30, 20 000 evaluations per run.
"""
    nb.md(tools_md)
    nb.embed([RULE, "# SECTION 4a - TOOLS (verbatim from qi_core.py)",
              "#   Tracker            - run diagnostics (optional; switched off in the experiments for speed)"]
             + (["#   max_min            - the Max-Min list-scheduling heuristic (starting schedule of the last step)"]
                if k == "mrfo" else [])
             + ["#   critical_exchange  - THE SWAP MOVE on the busiest VM", RULE], a["GROUPS"]["tools"])
    nb.md(orig_md)
    nb.embed([RULE, f"# SECTION 4b - THE ORIGINAL {orig} WITH ROUNDING (verbatim from qi_core.py)",
              "#   decode / _init_pop - continuous positions -> VM numbers, random start", RULE], a["GROUPS"]["original"])
    nb.md(qi_md)
    nb.embed([RULE, "# SECTION 4c - QUANTUM-INSPIRED MECHANISM (verbatim from qi_quantum.py)",
              "#   born_probs / probs  - register -> probabilities (Born rule or classical linear version)",
              "#   measure             - sample one schedule from the registers",
              "#   depolarise / purity - decoherence channel and how 'collapsed' a register is",
              "#   collapse_rows       - measurement back-action used by the swap move", RULE], a["GROUPS"]["mechanism"])
    nb.embed([RULE, f"# SECTION 4d - {main} (verbatim from qi_quantum.py)",
              f"#   {'run_qidmo' if k == 'dmo' else 'run_qimrfo'}(instance, objective, budget, P=population, seed=..., "
              "decoherence=c/n, exchange=swap probability, ...)",
              "#   returns {'best_f': best makespan, 'best_assign': best schedule, 'tracker': diagnostics, 'state': registers}",
              RULE], a["GROUPS"]["algorithm"])
    if k == "mrfo":
        nb.md(r"""
**4e. A changing cloud.** `make_dynamic_sequence` creates a problem followed by a sequence of changes:
* **churn:** 20 % of the tasks finish and new tasks arrive;
* **drift:** VM speeds change;
* **vm_fail:** a VM disappears;
* **vm_add:** a VM is added;
* **mixed:** a random change each time.

The helpers repair a schedule after a change and count how many running tasks a new schedule moves (*migrations*).
""")
        nb.embed([RULE, "# SECTION 4e - CHANGING-CLOUD HELPERS (verbatim from qi_dynamic.py)",
                  "#   make_dynamic_sequence            - a problem followed by K changes",
                  "#   adapt_register_state             - apply the structural rules to the registers",
                  "#   map_to_new_vms / count_migrations - compare schedules across a change; count moved tasks",
                  "#   repair_schedule / incremental_list_schedule - make the running schedule valid after a change",
                  RULE], a["GROUPS"]["changing"])

    # ---------------------------------------------------------------- experiment helpers
    nb.md(r"""
## Section 5 — Experiment helpers
* **The versions of <<MAIN>>** compared in Part 2, and the function that runs one of them once.
* **A runner that saves every finished run to Google Drive at once** and skips runs that are already saved (resume).
* **Statistics.** The Wilcoxon signed-rank test (paired problems) and the Mann–Whitney U test (independent runs).
* **Plot style and the problem sets.**
""".replace("<<MAIN>>", main))
    nb.code(variants_code(k, a))
    letters = iter("bcde") if k == "dmo" else iter("cdef")
    if k == "mrfo":
        nb.code(fill(CHANGING_CODE, RULE=RULE))
    nb.code(fill(RUNNER_CODE, RULE=RULE, LETTER=next(letters)))
    nb.code(fill(STYLE_CODE, RULE=RULE, LETTER=next(letters)))
    nb.code(sizes_code(k, a, next(letters)))

    nb.md(r"""
## Section 6 — Quick self-check (a few seconds)
Every version is run twice on a tiny problem. The check confirms that each one returns a valid schedule, respects its
evaluation budget and gives the same answer twice with the same seed.
""")
    nb.code(selfcheck_code(k, a))

    # ---------------------------------------------------------------- Part 1
    nb.md(fill(r"""
## Part 1 — Performance of <<MAIN>>
<<MAIN>> is run on its own, with the settings used in all project experiments (population 30, 20 000 evaluations per
run).

**The problems.**
* **Benchmark problems:** 7 problems with 30–200 tasks and 5–20 VMs, with different task-length distributions and VM
  heterogeneity. Full mode: 30 independent runs each.
* **Large problems:** 500, 1 000, 1 500, 2 000 and 5 000 tasks on 50 VMs. Full mode: 10 independent runs each.

**What you get.**
* **Tables 1.1 and 1.2.** Makespan in seconds (mean ± SD, best and worst run), the lower bound, the gap, the energy
  (Wh) and the run time of one run.
* **Figure 1.1.** Convergence: how the gap falls as the algorithm tries more schedules.
* **Figure 1.2.** The best schedule for the 100-task problem: how long every VM is busy. A good schedule keeps all VMs
  close to the lower bound.
* **Figure 1.3.** How the gap and the run time grow with the number of tasks.

**Output files.** `benchmark_runs.csv` and `large_runs.csv` (every run), `1_1_benchmark_performance.csv`,
`1_2_large_performance.csv`, `1_1_convergence.png`, `1_2_vm_finish_times.png` and `1_3_large_problems.png`.
""", MAIN=main))
    nb.code(fill(PART1_CODE, RULE=RULE, MAIN=main))

    # ---------------------------------------------------------------- Part 2
    steps_txt = ("""1. **DMO (original)**: continuous positions rounded to VM numbers.
2. **QI-DMO**: quantum-inspired registers instead of rounding.
3. **QI-DMO + the swap move**, in two versions:
   * **in every phase**: the first try, the QI-MRFO swap move unchanged on every candidate (probability 1, test H14);
   * **in improving phases**: the second version, only in the two phases that keep a candidate only if it is better,
     with probability 0.1 (test H15).""" if k == "dmo" else
                 """1. **MRFO (original)**: continuous positions rounded to VM numbers.
2. **QI-MRFO**: quantum-inspired registers instead of rounding.
3. **QI-MRFO + swap**: the swap move added (probability 1).
4. **QI-MRFO + swap + Max-Min start**: one of the 30 starting schedules comes from the Max-Min heuristic.""")
    unseen_txt = ("80 problems (8 types × 10) that no earlier QI-DMO experiment used: instance seeds 801–810,\n  the "
                  "problems of the pre-registered test H15, which ran the same three QI-DMO versions" if k == "dmo" else
                  "80 problems (8 types × 10) that were never used to set up anything: instance seeds 101–110,\n  the "
                  "problems of the pre-registered test of the swap move (H5)")
    nb.md(fill(r"""
## Part 2 — How <<MAIN>> was improved, step by step
Every version is run on the same problems with the same seeds and the same budget, so the differences come only from
the changes:

<<STEPS>>

<<FOUND>>

**The problem sets.**
* **Benchmark and large problems** as in Part 1 (the <<MAIN>> runs of Part 1 are reused, not repeated).
* **Unseen problems:** <<UNSEEN>>. Full mode: 2 runs each. The gap here is measured against the tighter *preemptive*
  lower bound.

**What you get.**
* **Tables 2.1–2.3.** The mean makespan (s) or gap (%) of every version on every problem.
* **Table 2.4 — what each change gained.** For every change and problem set: the average gap before and after, on how
  many problems the change helped, and on how many it was *significantly* better or worse.
  * Benchmark and large problems: Mann–Whitney U on the runs of each problem, Holm-corrected across the problems.
  * Unseen problems: Wilcoxon signed-rank over the 10 problems of each type (Holm across the 8 types), and one
    Wilcoxon test over all 80 problems.
* **Figure 2.1.** The average gap of every version, for each problem set.
* **Figure 2.2.** Every unseen problem as one point: gap without the swap move (x) against with it (y). A point below
  the diagonal means the swap move was better on that problem.

**Output files.** `unseen_runs.csv` (every run; the other two files are shared with Part 1),
`2_1_benchmark_versions.csv`, `2_2_unseen_versions.csv`, `2_3_large_versions.csv`, `2_4_what_each_change_gained.csv`,
`2_1_versions.png` and `2_2_swap_each_problem.png`.
""", MAIN=main, STEPS=steps_txt, UNSEEN=unseen_txt, FOUND=FOUND_PART2[k]))
    nb.code(fill(PART2_CODE, RULE=RULE, MAIN=main))

    # ---------------------------------------------------------------- Part 3 (QI-MRFO)
    if k == "mrfo":
        nb.md(r"""
## Part 3 — QI-MRFO in a changing cloud: how each improvement helped
In a real cloud, tasks arrive and leave, VMs fail or are added, and VM speeds drift. After every change the scheduler
computes a new schedule. **Moving a task that is already running to another VM (a migration) costs something.**
* **The cost.** The objective is makespan × (1 + λ × moved tasks / movable tasks), with the migration price λ = 0.2.
* **The cost gap** is how far this cost is above the lower bound, in %. Lower is better.

**The six development steps** (each adds one improvement to the step before; Table 3.1 lists them):
1. restart from scratch after each change;
2. keep the registers and adapt them to the change;
3. add the swap move;
4. start from the schedule that is running now, so fewer tasks are moved;
5. do that after every change except a VM addition, and place new tasks by list scheduling;
6. no decoherence noise after small changes: the final version.

**What the project's pre-registered tests found.**
* **Swap move under change (H6).** −2.98 percentage points of gap; better in 60 of 60 runs.
* **Starting from the running schedule (H6).** It helps after churn and VM failures. After a VM addition it hurts,
  because the new VM stays empty. The event-aware start (step 5, H11) therefore skips it after a VM addition.
* **Placing new tasks by list scheduling (H12).** Fewer tasks moved after churn: 15.3 → 1.6 per change at λ = 0.2.
* **No noise after small changes (H13).** −0.26 percentage points of cost gap at λ = 0.2 (Holm p = 0.007).

Steps 5 and 6 reproduce the H13 runs exactly (seeds 601–610). Steps 1–4 are new runs on the same problems.

**Setup.** Full mode: 6 change scenarios × 10 runs (seeds 601–610), 8 changes per run; 20 000 evaluations before the
first change and 4 000 after each change.

**Output files.** `changing_cloud_runs.csv`, `3_1_changing_cloud_steps.csv`, `3_2_changing_cloud_by_scenario.csv` and
`3_1_changing_cloud_steps.png`.
""")
        nb.code(fill(PART3_CODE, RULE=RULE))

    # ---------------------------------------------------------------- summary and finish
    nb.md(r"""
## Section 7 — Summary and saved files
* **The summary** is computed from the runs saved in the results folder. A part is summarised only when *all* its runs
  are saved; otherwise the summary says how many runs are missing. It is saved as `summary.txt`.
* **All tables** of this session are also written to one Excel workbook, `all_tables.xlsx`, with one sheet per table.
* **The file list** at the end shows every file in the results folder.
""")
    nb.code(summary_code(k, a))
    nb.md(r"""
## Section 8 — Finish: write everything to Google Drive
Google Drive receives the files in the background. This last cell makes sure that everything has been written, then
disconnects Drive from this session. To run more cells afterwards, run Section 2 again first.
""")
    nb.code(fill(FINISH_CODE, RULE=RULE))
    os.makedirs(os.path.join(ROOT, "notebooks", "colab"), exist_ok=True)
    nb.save(os.path.join(ROOT, "notebooks", "colab", a["FILE"]))


if __name__ == "__main__":
    for k in ["dmo", "mrfo"]:
        build(k)
