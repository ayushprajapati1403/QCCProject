"""Deterministic seeds and strict evaluation-budget accounting for every optimizer."""
import numpy as np
import pytest
from qi_core import make_instance, Objective, run_pso, run_dmo, run_mrfo, run_ga, run_random
from qi_quantum import run_qimrfo, run_qidmo

OPT = {"PSO": (run_pso, {}), "DMO": (run_dmo, {}), "MRFO": (run_mrfo, {}), "GA": (run_ga, {}), "Random": (run_random, {}),
       "QI-MRFO": (run_qimrfo, {"decoherence": 0.05}), "QI-MRFO-lin": (run_qimrfo, {"decoherence": 0.05, "mode": "linear"}),
       "QI-DMO": (run_qidmo, {"decoherence": 0.0125}), "QI-DMO-greedy": (run_qidmo, {"decoherence": 0.0125, "greedy_next": True})}
# largest number of evaluations one iteration can consume (so a run may stop at most this far below the budget)
ITER_COST = {"PSO": lambda P: P, "DMO": lambda P: 3 * P + 3, "MRFO": lambda P: 2 * P, "GA": lambda P: P, "Random": lambda P: P,
             "QI-MRFO": lambda P: 2 * P, "QI-MRFO-lin": lambda P: 2 * P, "QI-DMO": lambda P: 3 * P + 3, "QI-DMO-greedy": lambda P: 3 * P + 3}


@pytest.mark.parametrize("name", list(OPT))
def test_same_seed_same_result(name):
    fn, kw = OPT[name]
    inst = make_instance(20, 4, seed=2)
    r1 = fn(inst, Objective(inst), 800, P=8, seed=5, **kw)
    r2 = fn(inst, Objective(inst), 800, P=8, seed=5, **kw)
    assert r1["best_f"] == r2["best_f"] and np.array_equal(r1["best_assign"], r2["best_assign"])
    assert r1["tracker"].best == r2["tracker"].best and r1["tracker"].move_sizes == r2["tracker"].move_sizes


@pytest.mark.parametrize("name", list(OPT))
def test_different_seeds_differ(name):
    fn, kw = OPT[name]
    inst = make_instance(30, 5, seed=2)
    curves = {tuple(fn(inst, Objective(inst), 600, P=8, seed=s, **kw)["tracker"].best) for s in range(4)}
    assert len(curves) > 1


def test_instances_are_deterministic():
    a, b = make_instance(30, 5, seed=9, task_dist="bimodal"), make_instance(30, 5, seed=9, task_dist="bimodal")
    assert np.array_equal(a.task_len, b.task_len) and np.array_equal(a.vm_mips, b.vm_mips)


@pytest.mark.parametrize("name", list(OPT))
@pytest.mark.parametrize("budget,P", [(700, 10), (1001, 7), (2500, 30), (95, 5)])
def test_budget_respected_and_used(name, budget, P):
    fn, kw = OPT[name]
    inst = make_instance(15, 4, seed=1)
    obj = Objective(inst)
    fn(inst, obj, budget, P=P, seed=0, **kw)
    assert obj.n_evals <= budget
    if budget >= 4 * ITER_COST[name](P):
        assert obj.n_evals > budget - ITER_COST[name](P) - P, "optimizer left too much of the budget unused"


@pytest.mark.parametrize("fn,kw,key", [(run_qimrfo, {"decoherence": 0.05}, "Psi"), (run_qidmo, {"decoherence": 0.01}, "Psi"),
                                       (run_ga, {}, "A"), (run_mrfo, {}, "X")])
def test_warm_start_respects_budget(fn, kw, key):
    inst = make_instance(15, 4, seed=1)
    r = fn(inst, Objective(inst), 600, P=8, seed=0, **kw)
    obj = Objective(inst)
    fn(inst, obj, 333, P=8, seed=1, init_state=r["state"], **kw)
    assert obj.n_evals <= 333
