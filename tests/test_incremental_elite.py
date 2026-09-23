"""V5 / H12: repair='incremental' (new churn tasks and orphaned tasks placed by list scheduling) for the carried elite
and the carried schedule of the GA / (1+1)-EA. The existing 'random' / 'greedy' modes must be unchanged."""
import numpy as np
import pytest
from qi_core import Objective
from qi_dynamic import (make_dynamic_sequence, repair_schedule, incremental_list_schedule, count_migrations,
                        map_to_new_vms, adapt_ga_state, run_dynamic)


def priced(inst, info, prev, lam):
    ref, forced = map_to_new_vms(prev, info)
    elig = ~forced
    if info["type"] == "churn": elig[info["idx"]] = False
    return Objective(inst, kind="makespan_migration", ref=ref, mig_mask=elig, lam=lam)


@pytest.mark.parametrize("change", ["churn", "vm_fail", "vm_add", "drift", "mixed"])
def test_incremental_repair_is_the_incremental_heuristic(change):
    seq = make_dynamic_sequence(30, 6, seed=3, K=4, change=change)
    prev = np.random.default_rng(0).integers(0, 6, 30)
    for inst, info in seq[1:]:
        a = repair_schedule(prev, info, inst, np.random.default_rng(1), "incremental")
        assert np.array_equal(a, incremental_list_schedule(prev, info, inst, np.random.default_rng(2)))
        assert a.min() >= 0 and a.max() < inst.m
        assert count_migrations(prev, a, info)[0] == 0          # persistent tasks never move
        if info["type"] != "churn":                               # identical to 'greedy' for every other event
            assert np.array_equal(a, repair_schedule(prev, info, inst, np.random.default_rng(1), "greedy"))
        prev = np.random.default_rng(len(prev)).integers(0, inst.m, inst.n)


def test_greedy_repair_keeps_slot_inheritance_on_churn():
    """The H6-H11 behaviour is unchanged: with 'greedy' a new task keeps the VM of the departed task it replaced."""
    seq = make_dynamic_sequence(40, 5, seed=4, K=1, change="churn")
    inst, info = seq[1]
    prev = np.random.default_rng(3).integers(0, 5, 40)
    assert np.array_equal(repair_schedule(prev, info, inst, np.random.default_rng(0), "greedy"), prev)
    inc = repair_schedule(prev, info, inst, np.random.default_rng(0), "incremental")
    keep = np.ones(40, bool); keep[info["idx"]] = False
    assert np.array_equal(inc[keep], prev[keep])


def test_ga_state_incremental_repair():
    seq = make_dynamic_sequence(30, 5, seed=6, K=4, change="mixed")
    rng = np.random.default_rng(0)
    A = rng.integers(0, 5, (4, 30))
    for inst, info in seq[1:]:
        out = adapt_ga_state({"A": A}, info, inst.m, np.random.default_rng(1), inst=inst, repair="incremental")["A"]
        if info["type"] in ("churn", "vm_fail"):
            for a, b in zip(A, out):
                assert np.array_equal(b, incremental_list_schedule(a, info, inst, rng))
        else:
            assert np.array_equal(out, A)
        if info["type"] == "churn":                               # 'greedy' / 'random' leave churn untouched (as before)
            for how in ("greedy", "random"):
                assert np.array_equal(adapt_ga_state({"A": A}, info, inst.m, np.random.default_rng(1), inst=inst, repair=how)["A"], A)
        A = out


@pytest.mark.parametrize("algo,kw", [("QI-MRFO", dict(P=8, carry_elite="except_vm_add", algo_kw={"exchange": 1.0})),
                                     ("(1+1)-EA", dict(algo_kw={"exchange": 0.5}))])
@pytest.mark.parametrize("change", ["churn", "mixed"])
def test_incremental_repair_bounds_priced_cost(algo, kw, change):
    """The design guarantee of H12: after churn / VM failure the deployed schedule's priced cost is at most that of the
    incremental schedule, because that schedule is evaluated first (elite / (1+1)-EA start)."""
    seq = make_dynamic_sequence(24, 5, seed=2, K=4, change=change)
    out = run_dynamic(seq, algo, "continue_struct" if algo == "QI-MRFO" else "continue", 900, 400, seed=1,
                      decoherence_c=1.0, repair="incremental", mig_lambda=0.2, **kw)
    checked = 0
    for e in range(1, len(seq)):
        inst, info = seq[e]
        assert out[e]["evals"] <= 400
        if info["type"] in ("churn", "vm_fail"):
            prev = out[e - 1]["assign"]
            inc = incremental_list_schedule(prev, info, inst, np.random.default_rng(0))
            assert out[e]["cost"] <= priced(inst, info, prev, 0.2)(inc) + 1e-9
            checked += 1
    assert checked > 0
