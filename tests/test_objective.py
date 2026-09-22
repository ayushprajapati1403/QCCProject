"""Objective, lower bound, instance model and list heuristics."""
import itertools
import numpy as np
import pytest
from qi_core import CloudInstance, make_instance, Objective, max_min, min_min, local_search_1move


def brute_force(inst):
    best = np.inf
    for a in itertools.product(range(inst.m), repeat=inst.n):
        best = min(best, Objective(inst)._raw(np.array(a))[0])
    return best


def test_execution_time_matrix():
    inst = make_instance(7, 3, seed=2)
    assert inst.et.shape == (7, 3)
    assert np.allclose(inst.et, inst.task_len[:, None] / inst.vm_mips[None, :])


def test_makespan_matches_manual_loads():
    inst = make_instance(12, 4, seed=0)
    rng = np.random.default_rng(1)
    for _ in range(20):
        a = rng.integers(0, 4, 12)
        loads = np.zeros(4)
        for t, v in enumerate(a):
            loads[v] += inst.task_len[t] / inst.vm_mips[v]
        assert Objective(inst)(a) == pytest.approx(loads.max(), rel=1e-12)


def test_energy_formula():
    inst = make_instance(9, 3, seed=4)
    a = np.array([0, 1, 2, 0, 1, 2, 0, 0, 1])
    loads = np.bincount(a, weights=inst.et[np.arange(9), a], minlength=3)
    ms = loads.max()
    e = sum(inst.vm_p_idle[j] * ms + (inst.vm_p_max[j] - inst.vm_p_idle[j]) * loads[j] for j in range(3)) / 3600.0
    d = Objective(inst).details(a)
    assert d["makespan"] == pytest.approx(ms) and d["energy_Wh"] == pytest.approx(e)


def test_combined_objective_is_one_on_reference_schedule():
    inst = make_instance(15, 4, seed=1)
    obj = Objective(inst, kind="makespan_energy", w_energy=0.3)
    assert obj(np.arange(15) % 4) == pytest.approx(1.0)


def test_unknown_objective_kind_raises():
    inst = make_instance(5, 2, seed=0)
    with pytest.raises(ValueError):
        Objective(inst, kind="nope")(np.zeros(5, int))


def test_evaluation_counter_counts_calls_only():
    inst = make_instance(10, 3, seed=0)
    obj = Objective(inst)
    a = np.zeros(10, int)
    obj(a); obj(a); obj._raw(a); obj.details(a)
    assert obj.n_evals == 2


@pytest.mark.parametrize("seed", range(4))
def test_lower_bound_is_valid_and_formula(seed):
    inst = make_instance(6, 3, seed=seed, task_dist="bimodal")
    lb = max(inst.task_len.sum() / inst.vm_mips.sum(), inst.task_len.max() / inst.vm_mips.max())
    assert inst.lower_bound() == pytest.approx(lb)
    assert brute_force(inst) >= inst.lower_bound() - 1e-9


@pytest.mark.parametrize("dist", ["uniform", "lognormal", "bimodal", "identical"])
@pytest.mark.parametrize("het", ["high", "low", "none"])
def test_generator_ranges(dist, het):
    inst = make_instance(40, 6, seed=3, task_dist=dist, hetero=het)
    assert inst.n == 40 and inst.m == 6
    assert np.all(inst.task_len > 0) and np.all(inst.vm_mips > 0)
    assert np.all(inst.vm_p_idle < inst.vm_p_max)


def test_heuristics_return_complete_valid_schedules():
    inst = make_instance(30, 5, seed=2)
    for h in (max_min, min_min):
        a = h(inst)
        assert a.shape == (30,) and a.min() >= 0 and a.max() < 5


def test_local_search_never_worsens():
    inst = make_instance(25, 4, seed=5)
    rng = np.random.default_rng(0)
    obj = Objective(inst)
    for _ in range(5):
        a = rng.integers(0, 4, 25)
        assert obj._raw(local_search_1move(inst, a))[0] <= obj._raw(a)[0] + 1e-12


def test_copy_with_recomputes_et():
    inst = make_instance(5, 2, seed=0)
    new = inst.copy_with(vm_mips=inst.vm_mips * 2)
    assert np.allclose(new.et, inst.et / 2)
