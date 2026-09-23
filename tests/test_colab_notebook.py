"""QI_MRFO_DMO_Colab.ipynb: it must be exactly what notebooks/build/build_colab_notebook.py generates from the current modules, its own
cells must run outside Colab (self-check included), and its full-mode settings must reproduce committed records."""
import json, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTEBOOK = "QI_MRFO_DMO_Colab.ipynb"


def build_into(tmp_path, builder):
    """Run notebooks/build/<builder> with --root tmp_path (a copy of src/), so the committed notebooks are not touched."""
    os.makedirs(tmp_path / "src", exist_ok=True)
    for f in ["qi_core.py", "qi_quantum.py", "qi_dynamic.py"]:
        shutil.copy(os.path.join(ROOT, "src", f), tmp_path / "src" / f)
    subprocess.run([sys.executable, os.path.join(ROOT, "notebooks", "build", builder), "--root", str(tmp_path)],
                   check=True, capture_output=True)


def test_colab_notebook_matches_builder(tmp_path):
    build_into(tmp_path, "build_colab_notebook.py")
    built = json.load(open(tmp_path / "notebooks" / "colab" / NOTEBOOK, encoding="utf-8"))
    committed = json.load(open(os.path.join(ROOT, "notebooks", "colab", NOTEBOOK), encoding="utf-8"))
    assert built == committed, f"{NOTEBOOK} is out of sync with the modules: run `python notebooks/build/build_colab_notebook.py`"


def _exec_cells(until, mode):
    """Execute the notebook's code cells up to and including the one containing `until` (results to a local folder)."""
    nb = json.load(open(os.path.join(ROOT, "notebooks", "colab", NOTEBOOK), encoding="utf-8"))
    ns = {"__name__": "__main__"}
    for c in nb["cells"]:
        if c["cell_type"] != "code":
            continue
        src = c["source"].replace('MODE = "quick"', f'MODE = "{mode}"').replace("SAVE_TO_GOOGLE_DRIVE = True ", "SAVE_TO_GOOGLE_DRIVE = False")
        exec(compile(src, NOTEBOOK, "exec"), ns)
        if until in src:
            return ns
    raise AssertionError(f"no cell contains {until!r}")


def test_colab_notebook_runs_and_reproduces_committed_records(tmp_path, monkeypatch):
    import pandas as pd
    monkeypatch.chdir(tmp_path)
    ns = _exec_cells("SECTION 9 - SELF-CHECK", mode="full")        # also runs the notebook's own self-check
    assert ns["MODE"] == "full" and os.path.exists(os.path.join(ns["RUN_DIR"], "settings.json"))
    assert ns["SIZES"]["A"]["budget"] == 20000 and ns["SIZES"]["C"]["sizes"] == [500, 1000, 1500, 2000, 5000]
    # Experiment A in full mode = the V4 baseline (results/baseline_full.csv)
    r = ns["run_static"]({"key": "k", "experiment": "A", "algorithm": "QI-MRFO", "problem": (100, 10, "uniform", "high"),
                          "inst_seed": 1, "run_seed": 0, "budget": 20000})
    base = pd.read_csv(os.path.join(ROOT, "results", "baseline_full.csv"), float_precision="round_trip")
    row = base[(base.algo == "QI-MRFO") & (base.instance == "n100 m10 uniform high") & (base.seed == 0)].iloc[0]
    assert r["makespan_s"] == row.makespan and r["lower_bound_s"] == row.lb
    # Experiment D2 in full mode = H13 (results/h13_event_gamma), final configuration
    d = ns["SIZES"]["D"]
    r = ns["run_changing"]({"key": "k", "experiment": "D2", "strategy": "QI-MRFO final", "scenario": "Task churn (20% replaced)",
                            "seed": 601, "K": d["K"], "budget0": d["budget0"], "budget": d["budget"], "lam": 0.2})
    h13 = pd.read_csv(os.path.join(ROOT, "results", "h13_event_gamma", "records.csv"), float_precision="round_trip")
    row = h13[(h13.algo == "H12 swarm, event-aware gamma") & (h13.scenario == "n100 m10 churn20 lam=0.2") & (h13.seed == 601)].iloc[0]
    assert abs(r["cost_gap_pct"] - 100 * row.post_cost_gap) < 1e-9 and r["migrations_per_change"] == row.migrations
