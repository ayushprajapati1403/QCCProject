"""V5 additions: tighter lower bound, critical exchange move (H5), landscape move counter, V5 diagnostics."""
import itertools
import numpy as np
import pytest
from qi_core import (make_instance, Objective, Tracker, critical_exchange, count_improving_moves, run_ga)
from qi_quantum import run_qimrfo, collapse_rows, probs, depolarise, basis_state, uniform_state
from test_objective import brute_force


@pytest.mark.parametrize("n,m,dist,het,seed", [(6, 3, "uniform", "high", 0), (5, 3, "bimodal", "high", 1), (7, 2, "lognormal", "low", 2),
                                                (3, 5, "uniform", "high", 3), (6, 4, "bimodal", "high", 4), (4, 4, "identical", "none", 5)])
def test_preemptive_bound_valid_and_tighter(n, m, dist, het, seed):
    inst = make_instance(n, m, seed=seed, task_dist=dist, hetero=het)
    assert inst.lower_bound_pmtn() >= inst.lower_bound() - 1e-12
    assert inst.lower_bound_pmtn() <= brute_force(inst) + 1e-9


def test_preemptive_bound_known_value():
    from qi_core import CloudInstance
    inst = CloudInstance(np.array([10.0, 2.0, 2.0]), np.array([2.0, 1.0]), np.ones(2), 2 * np.ones(2))
    # k=1: 10/2 = 5 ; total: 14/3 -> 5 ; old LB: max(14/3, 10/2) = 5 as well
    assert inst.lower_bound_pmtn() == pytest.approx(5.0)
    inst = CloudInstance(np.array([6.0, 6.0, 1.0]), np.array([3.0, 1.0, 1.0]), np.ones(3), 2 * np.ones(3))
    # k=1: 6/3=2 ; k=2: 12/4 = 3 ; total 13/5 = 2.6 -> 3 (old LB = max(2.6, 2) = 2.6)
    assert inst.lower_bound_pmtn() == pytest.approx(3.0) and inst.lower_bound() == pytest.approx(2.6)


@pytest.mark.parametrize("dist,het", [("uniform", "high"), ("bimodal", "high"), ("identical", "none"), ("lognormal", "low")])
def test_critical_exchange_invariants(dist, het):
    inst = make_instance(30, 5, seed=2, task_dist=dist, hetero=het)
    rng = np.random.default_rng(0)
    for _ in range(300):
        a = rng.integers(0, 5, 30)
        L = np.bincount(a, weights=inst.et[np.arange(30), a], minlength=5)
        new, t, u = critical_exchange(inst, a, rng)
        assert L[a[t]] >= L.max() * (1 - 1e-12), "t must come from a critical VM"
        changed = np.flatnonzero(new != a)
        if u >= 0:
            assert a[u] != a[t] and inst.task_len[u] < inst.task_len[t]
            assert new[t] == a[u] and new[u] == a[t] and set(changed) == {t, u}
            assert np.array_equal(np.bincount(new, minlength=5), np.bincount(a, minlength=5)), "an exchange keeps VM task counts"
        else:
            assert list(changed) == [t] and new[t] != a[t]
            assert not np.any((a != a[t]) & (inst.task_len < inst.task_len[t])), "relocation only when no shorter task exists elsewhere"


def test_critical_exchange_deterministic():
    inst = make_instance(20, 4, seed=1)
    a = np.random.default_rng(3).integers(0, 4, 20)
    r1 = critical_exchange(inst, a, np.random.default_rng(9)); r2 = critical_exchange(inst, a, np.random.default_rng(9))
    assert np.array_equal(r1[0], r2[0]) and r1[1:] == r2[1:]


def _brute_moves(inst, a):
    obj = Objective(inst); ms = obj._raw(a)[0]; ar = np.arange(inst.n)
    L = np.bincount(a, weights=inst.et[ar, a], minlength=inst.m); b = L.argmax()
    rel = sum(obj._raw(np.where(ar == t, v, a))[0] < ms - 1e-9 for t in np.flatnonzero(a == b) for v in range(inst.m) if v != b)
    sw = 0
    for t in np.flatnonzero(a == b):
        for u in np.flatnonzero(a != b):
            c = a.copy(); c[t], c[u] = a[u], a[t]; sw += obj._raw(c)[0] < ms - 1e-9
    return rel, sw


@pytest.mark.parametrize("seed", range(6))
def test_count_improving_moves_matches_enumeration(seed):
    inst = make_instance(14, 4, seed=seed, task_dist=["uniform", "bimodal"][seed % 2])
    rng = np.random.default_rng(seed)
    for _ in range(10):
        a = rng.integers(0, 4, 14)
        r, s, tied = count_improving_moves(inst, a)
        if tied == 1:
            assert (r, s) == _brute_moves(inst, a)


def test_tracker_v5_duplicates_and_critical_touch():
    inst = make_instance(6, 3, seed=0)
    tr = Tracker(6, 3, inst)
    p = np.array([0, 0, 1, 1, 2, 2])
    L = np.bincount(p, weights=inst.et[np.arange(6), p], minlength=3); b = int(L.argmax())
    on_b = int(np.flatnonzero(p == b)[0]); off_b = int(np.flatnonzero(p != b)[0])
    c1 = p.copy(); c1[on_b] = (b + 1) % 3                 # touches the critical VM
    c2 = p.copy(); c2[off_b] = b                          # does not
    for child in (p.copy(), c1, c1.copy(), c2):
        tr.candidate(p, child, 1.0, 1.0)
    s = tr.summary_v5()
    assert tr.dup_global == 2                             # p itself (seen as parent) and the second c1
    assert tr.touch_crit == 2 and s["touch_crit_frac"] == 0.5


def test_collapse_rows():
    psi = uniform_state(4, 3, "born_signed")
    out = collapse_rows(psi, [1, 3], np.array([2, 0]), 0.1, 3, "born_signed")
    assert np.array_equal(out[[0, 2]], psi[[0, 2]])
    assert np.allclose(probs(out[[1, 3]], "born_signed"), probs(depolarise(basis_state(np.array([2, 0]), 3), 0.1, 3, "born_signed"), "born_signed"))
    assert np.allclose((out ** 2).sum(1), 1.0)


@pytest.mark.parametrize("fn,kw", [(run_qimrfo, {"decoherence": 0.05}), (run_qimrfo, {"decoherence": 0.05, "mode": "linear"}),
                                   (run_qimrfo, {"decoherence": 0.0}), (run_ga, {})])
@pytest.mark.parametrize("x", [0.25, 1.0])
def test_exchange_budget_determinism_validity(fn, kw, x):
    inst = make_instance(25, 5, seed=1, task_dist="bimodal")
    o1, o2 = Objective(inst), Objective(inst)
    r1 = fn(inst, o1, 1301, P=10, seed=3, exchange=x, **kw); r2 = fn(inst, o2, 1301, P=10, seed=3, exchange=x, **kw)
    assert o1.n_evals <= 1301 and o1.n_evals == o2.n_evals
    assert r1["best_f"] == r2["best_f"] and np.array_equal(r1["best_assign"], r2["best_assign"])
    a = r1["best_assign"]; assert a.min() >= 0 and a.max() < 5
    assert r1["best_f"] == pytest.approx(Objective(inst)(a))
    tr = r1["tracker"]; assert tr.x_cands > 0 and 0 <= tr.x_improving <= tr.x_cands


@pytest.mark.parametrize("fn,kw", [(run_qimrfo, {"decoherence": 0.05}), (run_ga, {})])
def test_exchange_zero_is_default(fn, kw):
    inst = make_instance(20, 4, seed=2)
    r1 = fn(inst, Objective(inst), 900, P=8, seed=1, **kw); r2 = fn(inst, Objective(inst), 900, P=8, seed=1, exchange=0.0, **kw)
    assert r1["best_f"] == r2["best_f"] and r1["tracker"].best == r2["tracker"].best
