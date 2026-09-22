"""V5 dynamic extensions: mixed events, repair, migration counting, incremental heuristic, elite carry-over, kwargs."""
import numpy as np
import pytest
from qi_core import make_instance, Objective
from qi_dynamic import (make_dynamic_sequence, map_to_new_vms, repair_schedule, count_migrations, incremental_list_schedule,
                        run_dynamic)


def test_mixed_sequence_valid():
    seq = make_dynamic_sequence(30, 5, seed=2, K=12, change="mixed")
    types = [info["type"] for _, info in seq[1:]]
    assert len(set(types)) >= 3 and all(inst.m >= 3 for inst, _ in seq)
    for inst, info in seq[1:]:
        if info["type"] == "churn": assert len(info["idx"]) == 6


def test_map_and_migrations_by_hand():
    prev = np.array([0, 1, 2, 3, 2, 1])
    info = {"type": "vm_fail", "j": 2}
    mapped, forced = map_to_new_vms(prev, info)
    assert mapped.tolist() == [0, 1, -1, 2, -1, 1] and forced.tolist() == [False, False, True, False, True, False]
    new = np.array([0, 0, 1, 2, 2, 1])                  # task 1 moved voluntarily (1 -> 0); tasks 2, 4 were forced
    assert count_migrations(prev, new, info) == (1, 2, 6)
    churn = {"type": "churn", "idx": np.array([0, 5])}
    assert count_migrations(prev, np.array([3, 1, 2, 3, 2, 0]), churn) == (0, 0, 4)   # replaced tasks are not migrations
    assert count_migrations(prev, np.array([0, 1, 2, 3, 0, 1]), None) == (1, 0, 6)


@pytest.mark.parametrize("how", ["random", "greedy"])
def test_repair_schedule_valid(how):
    seq = make_dynamic_sequence(25, 6, seed=1, K=3, change="vm_fail")
    rng = np.random.default_rng(0)
    prev = rng.integers(0, 6, 25)
    inst, info = seq[1]
    a = repair_schedule(prev, info, inst, rng, how)
    assert a.min() >= 0 and a.max() < inst.m
    mapped, forced = map_to_new_vms(prev, info)
    assert np.array_equal(a[~forced], mapped[~forced])


def test_greedy_repair_is_list_scheduling():
    seq = make_dynamic_sequence(40, 6, seed=4, K=1, change="vm_fail")
    inst, info = seq[1]
    prev = np.random.default_rng(1).integers(0, 6, 40)
    g = repair_schedule(prev, info, inst, np.random.default_rng(0), "greedy")
    rs = [Objective(inst)._raw(repair_schedule(prev, info, inst, np.random.default_rng(s), "random"))[0] for s in range(20)]
    assert Objective(inst)._raw(g)[0] <= np.median(rs) + 1e-9


@pytest.mark.parametrize("change", ["churn", "vm_fail", "vm_add", "drift", "mixed"])
def test_incremental_heuristic_never_migrates(change):
    seq = make_dynamic_sequence(30, 6, seed=3, K=4, change=change)
    out = run_dynamic(seq, "Incremental", "continue", 0, 0, seed=0)
    assert all(o["migrations"] == 0 for o in out) and all(o["evals"] == 1 for o in out)
    out = run_dynamic(seq, "Max-Min", "continue", 0, 0, seed=0)
    assert all(o["gap"] >= -1e-12 for o in out)


@pytest.mark.parametrize("change", ["churn", "vm_fail", "vm_add", "drift"])
@pytest.mark.parametrize("repair", ["random", "greedy"])
def test_elite_carry_over_bounds_epoch_best(change, repair):
    """With carry_elite every epoch's best is at most the value of the repaired previous best (it is evaluated first),
    and the per-epoch budget is respected."""
    seq = make_dynamic_sequence(20, 5, seed=2, K=3, change=change)
    kwargs = dict(P=8, decoherence_c=1.0, carry_elite=True, repair=repair, algo_kw={"exchange": 1.0})
    out = run_dynamic(seq, "QI-MRFO", "continue_struct", 900, 400, seed=1, **kwargs)
    for e in range(1, len(seq)):
        inst, info = seq[e]
        assert out[e]["evals"] <= 400
        if repair == "greedy" or info["type"] != "vm_fail":         # deterministic repair: reproduce the elite exactly
            elite = repair_schedule(out[e - 1]["assign"], info, inst, np.random.default_rng(0), repair)
            assert out[e]["best"] <= Objective(inst)._raw(elite)[0] + 1e-9


def test_elite_changes_nothing_at_epoch_zero():
    seq = make_dynamic_sequence(20, 5, seed=5, K=2, change="drift")
    a = run_dynamic(seq, "QI-MRFO", "continue_struct", 1500, 300, seed=0, P=8, decoherence_c=1.0, carry_elite=True)
    b = run_dynamic(seq, "QI-MRFO", "continue_struct", 1500, 300, seed=0, P=8, decoherence_c=1.0)
    assert a[0]["best"] == b[0]["best"] and np.array_equal(a[0]["assign"], b[0]["assign"])


def test_carry_elite_rejects_unsupported_algo():
    seq = make_dynamic_sequence(15, 4, seed=0, K=1, change="drift")
    with pytest.raises(ValueError):
        run_dynamic(seq, "QI-DMO", "continue", 300, 200, seed=0, P=6, carry_elite=True)
