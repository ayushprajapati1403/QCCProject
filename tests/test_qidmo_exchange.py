"""H14: the swap move (critical exchange measurement, CXM) in QI-DMO. It must be strictly opt-in (exchange=0 reproduces the
unchanged algorithm, which the golden fingerprints also pin), respect the budget, be deterministic, and actually act."""
import numpy as np
import pytest

from qi_core import make_instance, Objective
from qi_quantum import run_qidmo


@pytest.fixture(scope="module")
def inst():
    return make_instance(40, 6, seed=3, task_dist="uniform", hetero="high")


def _run(inst, budget=3000, seed=5, **kw):
    obj = Objective(inst)
    r = run_qidmo(inst, obj, budget, P=12, seed=seed, decoherence=0.25 / inst.n, **kw)
    return r, obj


def test_exchange_zero_is_the_unchanged_algorithm(inst):
    r0, o0 = _run(inst)
    r1, o1 = _run(inst, exchange=0.0)
    assert r0["best_f"] == r1["best_f"] and np.array_equal(r0["best_assign"], r1["best_assign"])
    assert o0.n_evals == o1.n_evals and r1["tracker"].x_cands == 0


def test_exchange_valid_within_budget_and_deterministic(inst):
    r1, o1 = _run(inst, exchange=1.0)
    r2, o2 = _run(inst, exchange=1.0)
    a = r1["best_assign"]
    assert a.shape == (inst.n,) and a.min() >= 0 and a.max() < inst.m
    assert o1.n_evals <= 3000
    assert r1["best_f"] == r2["best_f"] and np.array_equal(a, r2["best_assign"])
    assert abs(Objective(inst)._raw(a)[0] - r1["best_f"]) < 1e-12        # reported value = makespan of returned schedule


def test_exchange_acts_on_every_candidate_at_px_1(inst):
    r0, _ = _run(inst)
    r1, o1 = _run(inst, exchange=1.0)
    tr = r1["tracker"]
    # every candidate of the three search phases is exchanged; only the initial population (and any babysitter reset)
    # is measured without it
    assert tr.x_cands > 0 and tr.x_cands <= o1.n_evals - 12
    assert 0 <= tr.x_improving <= tr.x_cands
    assert not np.array_equal(r0["best_assign"], r1["best_assign"])


def test_exchange_works_without_tracking_and_in_linear_mode(inst):
    r_t, _ = _run(inst, exchange=0.5, track=True)
    r_f, _ = _run(inst, exchange=0.5, track=False)
    assert r_t["best_f"] == r_f["best_f"]                                   # tracking never changes the search
    r_l, o_l = _run(inst, exchange=1.0, mode="linear")
    assert o_l.n_evals <= 3000 and r_l["best_assign"].max() < inst.m
