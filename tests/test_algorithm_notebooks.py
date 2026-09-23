"""QI_DMO_Colab.ipynb and QI_MRFO_Colab.ipynb (standalone notebooks): they must be exactly what
build_algorithm_notebooks.py generates from the current modules, their cells must run outside Colab (self-check included),
their full-mode settings must reproduce committed records, and QI-MRFO's changing-cloud driver must equal run_dynamic."""
import itertools, json, os, shutil, subprocess, sys

import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTEBOOKS = ["QI_DMO_Colab.ipynb", "QI_MRFO_Colab.ipynb"]
RT = dict(float_precision="round_trip")


def test_algorithm_notebooks_match_builder(tmp_path):
    for f in ["qi_core.py", "qi_quantum.py", "qi_dynamic.py", "build_algorithm_notebooks.py"]:
        shutil.copy(os.path.join(ROOT, f), tmp_path / f)
    subprocess.run([sys.executable, "build_algorithm_notebooks.py"], cwd=tmp_path, check=True, capture_output=True)
    for nb in NOTEBOOKS:
        built = json.load(open(tmp_path / nb, encoding="utf-8"))
        committed = json.load(open(os.path.join(ROOT, nb), encoding="utf-8"))
        assert built == committed, f"{nb} is out of sync with the modules: run `python build_algorithm_notebooks.py`"


def _exec_cells(notebook, until, mode="full"):
    """Execute the notebook's code cells up to and including the one containing `until` (results to a local folder)."""
    nb = json.load(open(os.path.join(ROOT, notebook), encoding="utf-8"))
    ns = {"__name__": "__main__"}
    for c in nb["cells"]:
        if c["cell_type"] != "code":
            continue
        src = c["source"].replace('MODE = "quick"', f'MODE = "{mode}"').replace("SAVE_TO_GOOGLE_DRIVE = True ", "SAVE_TO_GOOGLE_DRIVE = False")
        exec(compile(src, notebook, "exec"), ns)
        if until in src:
            return ns
    raise AssertionError(f"no cell contains {until!r}")


def _static(ns, problem_set, variant, problem, inst_seed, run_seed):
    return ns["run_one"]({"key": "k", "problem_set": problem_set, "variant": variant, "problem": problem,
                          "inst_seed": inst_seed, "run_seed": run_seed, "budget": 20000})


def _family(p):
    return f"n{p[0]} m{p[1]} {p[2]} {p[3]}"


def test_qi_dmo_notebook_runs_and_reproduces_committed_records(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ns = _exec_cells("QI_DMO_Colab.ipynb", "SECTION 6 - SELF-CHECK")     # also runs the notebook's own self-check
    assert ns["SIZES"]["unseen"]["inst_seeds"] == list(range(801, 811)) and ns["SIZES"]["benchmark"]["runs"] == 30
    base = pd.read_csv(os.path.join(ROOT, "results", "baseline_full.csv"), **RT)
    for variant, algo, prob, seed in [("QI-DMO", "QI-DMO", (100, 10, "uniform", "high"), 0), ("DMO (original)", "DMO", (30, 5, "uniform", "high"), 3)]:
        r = _static(ns, "benchmark", variant, prob, 1, seed)
        row = base[(base.algo == algo) & (base.instance == _family(prob)) & (base.seed == seed)].iloc[0]
        assert r["makespan_s"] == row.makespan and r["best_at_100pct_s"] == row.makespan
    h14 = pd.read_csv(os.path.join(ROOT, "results", "h14_test", "records.csv"), **RT)
    prob = (80, 8, "uniform", "high")
    r = _static(ns, "unseen", "QI-DMO + swap in every phase", prob, 701, 0)
    row = h14[(h14.algo == "QI-DMO+CXM") & (h14.family == _family(prob)) & (h14.inst_seed == 701) & (h14.run_seed == 0)].iloc[0]
    assert r["makespan_s"] == row.makespan
    # the notebook's unseen problems are the H15 test set (results/h15_test), with the same QI-DMO versions
    h15 = pd.read_csv(os.path.join(ROOT, "results", "h15_test", "records.csv"), **RT)
    prob = (100, 10, "bimodal", "high")
    for variant, algo in [("QI-DMO + swap in improving phases", "QI-DMO+CXM selected"), ("QI-DMO", "QI-DMO"),
                          ("QI-DMO + swap in every phase", "QI-DMO+CXM H14 (all, px=1)")]:
        r = _static(ns, "unseen", variant, prob, 801, 1)
        row = h15[(h15.algo == algo) & (h15.family == _family(prob)) & (h15.inst_seed == 801) & (h15.run_seed == 1)].iloc[0]
        assert r["makespan_s"] == row.makespan, variant


def test_qi_mrfo_notebook_runs_and_reproduces_committed_records(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ns = _exec_cells("QI_MRFO_Colab.ipynb", "SECTION 6 - SELF-CHECK")
    assert ns["SIZES"]["unseen"]["inst_seeds"] == list(range(101, 111)) and ns["SIZES"]["changing"]["price"] == 0.2
    h5 = pd.read_csv(os.path.join(ROOT, "results", "h5_test", "records.csv"), **RT)
    prob = (100, 10, "bimodal", "high")
    r = _static(ns, "unseen", "QI-MRFO + swap", prob, 101, 0)
    row = h5[(h5.algo == "QI-MRFO+CXM") & (h5.family == _family(prob)) & (h5.inst_seed == 101) & (h5.run_seed == 0)].iloc[0]
    assert r["makespan_s"] == row.makespan
    h7 = pd.read_csv(os.path.join(ROOT, "results", "h7_test", "records.csv"), **RT)       # the Max-Min start (H7)
    prob = (80, 8, "uniform", "high")
    r = _static(ns, "unseen", "QI-MRFO + swap + Max-Min start", prob, 201, 0)
    row = h7[(h7.algo == "QI-MRFO+CXM+seed") & (h7.family == _family(prob)) & (h7.inst_seed == 201) & (h7.run_seed == 0)].iloc[0]
    assert r["makespan_s"] == row.makespan
    # Part 3, steps 5 and 6 at price 0.2 = the H12 and final configurations of H13 (results/h13_event_gamma)
    h13 = pd.read_csv(os.path.join(ROOT, "results", "h13_event_gamma", "records.csv"), **RT)
    c = ns["SIZES"]["changing"]
    for step, algo in [("5. + event-aware start", "H12 swarm (c = 1)"), ("6. + no noise after small changes", "H12 swarm, event-aware gamma")]:
        r = ns["run_change"]({"key": "k", "step": step, "scenario": "Task churn (20% replaced)", "seed": 601, "K": c["K"],
                              "budget0": c["budget0"], "budget": c["budget"], "price": 0.2})
        row = h13[(h13.algo == algo) & (h13.scenario == "n100 m10 churn20 lam=0.2") & (h13.seed == 601)].iloc[0]
        assert abs(r["cost_gap_pct"] - 100 * row.post_cost_gap) < 1e-9 and r["migrations_per_change"] == row.migrations


@pytest.mark.parametrize("change", ["churn", "vm_fail", "vm_add", "drift", "mixed"])
def test_qi_mrfo_changing_cloud_driver_equals_run_dynamic(tmp_path, monkeypatch, change):
    from qi_dynamic import run_dynamic, make_dynamic_sequence
    monkeypatch.chdir(tmp_path)
    ns = _exec_cells("QI_MRFO_Colab.ipynb", "SECTION 5b", mode="quick")
    seq = make_dynamic_sequence(30, 5, seed=11, K=3, change=change)
    for (name, st), lam in itertools.product(ns["CHANGE_STEPS"].items(), [None, 0.2]):
        mine = ns["run_changing_cloud"](seq, 800, 400, seed=11, P=10, mig_lambda=lam, **st)
        kw = dict(st); ex = kw.pop("exchange", 0.0)
        ref = run_dynamic(seq, "QI-MRFO", kw.pop("strategy"), 800, 400, seed=11, P=10, decoherence_c=1.0, mode="born_signed",
                          algo_kw={"exchange": ex} if ex else None, carry_elite=kw.pop("carry_elite", False),
                          repair=kw.pop("repair", "random"), mig_lambda=lam, decoherence_by_event=kw.pop("decoherence_by_event", None))
        assert not kw
        for x, y in zip(mine, ref):
            assert (x["makespan"], x["migrations"], x["forced"], x["cost"]) == (y["best"], y["migrations"], y["forced"], y["cost"]), (name, lam)
