"""V5 experiment harness: statistics, checkpoint/resume, immutability."""
import json, os
import numpy as np
import pandas as pd
import pytest
from qi_experiment import (holm, rank_biserial, cliffs_delta, a12, boot_ci, wilcoxon_p, paired_table, spec, make_jobs,
                           run_job, run_experiment, job_key, resolve_kwargs, TEST_FAMILIES, TEST_INST_SEEDS, TUNE_FAMILIES)
from qi_core import make_instance


def test_holm_known_values():
    assert np.allclose(holm([0.01, 0.04, 0.03, 0.005]), [0.03, 0.06, 0.06, 0.02])
    assert np.allclose(holm([0.5]), [0.5])


def test_effect_sizes():
    assert rank_biserial([-1, -2, -3]) == -1.0 and rank_biserial([1, -1]) == 0.0
    assert cliffs_delta([1, 2], [3, 4]) == -1.0 and a12([1, 2], [3, 4]) == 1.0 and a12([1], [1]) == 0.5
    lo, hi = boot_ci(np.full(20, 2.0)); assert lo == hi == 2.0
    assert wilcoxon_p(np.zeros(5)) == 1.0 and wilcoxon_p(-np.arange(1, 11)) < 0.01


def test_split_is_disjoint():
    assert 1 not in TEST_INST_SEEDS and not (set(map(tuple, TEST_FAMILIES)) & set(map(tuple, TUNE_FAMILIES)))


def test_resolve_decoherence():
    inst = make_instance(40, 5, seed=0)
    assert resolve_kwargs({"decoherence_c": 2.0, "exchange": 0.5}, inst) == {"decoherence": 0.05, "exchange": 0.5}


def test_run_job_records():
    algos = {"Max-Min": spec("max_min"), "QI-MRFO+CXM": spec("run_qimrfo", decoherence_c=1.0, exchange=0.5)}
    jobs = make_jobs("t", algos, [(20, 4, "uniform", "high")], [7], [0, 1], budget=600, P=8)
    assert len(jobs) == 3                                     # heuristic once, stochastic per run seed
    recs = [run_job(j) for j in jobs]
    h = recs[0]; assert h["evals"] == 1 and h["ratio_mm"] == pytest.approx(1.0)
    q = recs[1]; assert q["evals"] <= 600 and q["gap2"] >= -1e-12 and q["gap"] >= q["gap2"] - 1e-12
    assert q["x_frac"] > 0 and q["bsf_100"] == pytest.approx(q["makespan"]) and q["bsf_005"] >= q["bsf_100"]


def test_checkpoint_resume_and_immutability(tmp_path):
    algos = {"GA": spec("run_ga"), "Min-Min": spec("min_min")}
    jobs = make_jobs("exp1", algos, [(15, 3, "uniform", "high")], [1, 2], [0, 1], budget=300, P=6)
    d = tmp_path / "exp1"; d.mkdir()
    # simulate an interrupted run: one record already checkpointed
    first = run_job(jobs[0]); first["key"] = job_key(jobs[0])
    open(d / "records.jsonl", "w").write(json.dumps(first) + "\n")
    df = run_experiment("exp1", jobs, workers=1, out_root=str(tmp_path), quiet=True)
    assert len(df) == len(jobs) and df.key.nunique() == len(jobs)
    assert (d / "DONE").exists() and (d / "meta.json").exists() and (d / "records.csv").exists()
    with pytest.raises(RuntimeError):
        run_experiment("exp1", jobs, workers=1, out_root=str(tmp_path), quiet=True)


def test_refuses_different_job_list(tmp_path):
    algos = {"GA": spec("run_ga")}
    j1 = make_jobs("e", algos, [(15, 3, "uniform", "high")], [1], [0], budget=200, P=6)
    j2 = make_jobs("e", algos, [(15, 3, "uniform", "high")], [1], [0, 1], budget=200, P=6)
    d = tmp_path / "e"; d.mkdir()
    json.dump({"sha256": "different", "jobs": j1}, open(d / "jobs.json", "w"))
    with pytest.raises(RuntimeError):
        run_experiment("e", j2, workers=1, out_root=str(tmp_path), quiet=True)


def test_paired_table_direction_and_pooling():
    rows = []
    for fam in ["f1", "f2"]:
        for s in range(8):
            rows.append({"family": fam, "inst_seed": s, "run_seed": 0, "algo": "A", "gap2": 0.01})
            rows.append({"family": fam, "inst_seed": s, "run_seed": 0, "algo": "B", "gap2": 0.02 + 0.001 * s})
    t = paired_table(pd.DataFrame(rows), "A", "B")
    assert list(t.family) == ["f1", "f2", "ALL"] and (t["diff A-B"] < 0).all() and (t["wins A"] == [8, 8, 16]).all()
    assert t.loc[t.family == "ALL", "pairs"].item() == 16 and (t.p_holm >= t.p - 1e-15).all()


def test_dynamic_job_runner(tmp_path):
    from qi_experiment import run_dyn_job, dyn_job_key
    sc = {"name": "t-churn", "n": 15, "m": 4, "K": 2, "change": "churn", "rho": 0.2}
    jobs = [{"exp": "d", "algo": a, "dyn": d, "scenario": sc, "seed": 0, "budget0": 400, "budget": 200, "P": 6}
            for a, d in {"QI-MRFO": {"algo": "QI-MRFO", "strategy": "continue_struct"},
                         "QI-MRFO+CXM+elite": {"algo": "QI-MRFO", "strategy": "continue_struct", "algo_kw": {"exchange": 1.0}, "carry_elite": True},
                         "Incremental": {"algo": "Incremental"}}.items()]
    df = run_experiment("d", jobs, workers=1, out_root=str(tmp_path), quiet=True, runner=run_dyn_job, keyfn=dyn_job_key,
                        sort_cols=["scenario", "algo", "seed"])
    assert len(df) == 3 and (df[df.algo == "Incremental"].migrations == 0).all()
    assert {"e1_gap", "e2_mig", "post_auc", "migr_frac"} <= set(df.columns)
