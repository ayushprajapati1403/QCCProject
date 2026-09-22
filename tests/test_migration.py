"""V5 H8: migration-aware objective and its use in the dynamic harness."""
import numpy as np
import pytest
from qi_core import make_instance, Objective
from qi_dynamic import make_dynamic_sequence, run_dynamic, map_to_new_vms


def test_migration_objective_formula():
    inst = make_instance(10, 3, seed=0)
    ref = np.array([0, 1, 2, 0, 1, 2, 0, 1, 2, 0]); mask = np.ones(10, bool); mask[[8, 9]] = False
    obj = Objective(inst, kind="makespan_migration", ref=ref, mig_mask=mask, lam=0.5)
    a = ref.copy(); a[0] = 1; a[9] = 2                 # one eligible migration (task 0); task 9 is not eligible
    ms = Objective(inst)._raw(a)[0]
    assert obj.migrations(a) == 1 and obj(a) == pytest.approx(ms * (1 + 0.5 * 1 / 8))
    assert obj.details(a)["migrations"] == 1 and obj.n_evals == 1
    zero = Objective(inst, kind="makespan_migration", ref=ref, mig_mask=mask, lam=0.0)
    assert zero(a) == pytest.approx(ms)


@pytest.mark.parametrize("change", ["churn", "vm_fail", "vm_add", "drift", "mixed"])
def test_dynamic_costs_consistent(change):
    seq = make_dynamic_sequence(20, 5, seed=3, K=3, change=change)
    lam = 0.2
    out = run_dynamic(seq, "QI-MRFO", "continue_struct", 800, 400, seed=0, P=8, decoherence_c=1.0, algo_kw={"exchange": 1.0}, mig_lambda=lam)
    assert out[0]["cost"] == pytest.approx(out[0]["best"])            # epoch 0: nothing deployed yet, plain makespan
    for e in range(1, len(seq)):
        o, info = out[e], seq[e][1]
        eligible = o["persist"] - o["forced"]
        assert o["cost"] == pytest.approx(o["best"] * (1 + lam * o["migrations"] / max(1, eligible)))
        assert o["evals"] <= 400


def test_incremental_costs_equal_makespan_and_chooser_picks_cheaper():
    seq = make_dynamic_sequence(30, 6, seed=1, K=2, change="drift")
    kw = dict(mig_lambda=0.2)
    mm = run_dynamic(seq, "Max-Min", "continue", 0, 0, seed=0, **kw)
    inc = run_dynamic(seq, "Incremental", "continue", 0, 0, seed=0, **kw)
    ch = run_dynamic(seq, "Chooser", "continue", 0, 0, seed=0, **kw)
    assert all(o["cost"] == pytest.approx(o["best"]) for o in inc[1:])
    # epoch 1 shares the same reference (the epoch-0 Max-Min schedule) for all three strategies
    assert ch[1]["cost"] == pytest.approx(min(mm[1]["cost"], inc[1]["cost"]))
    assert ch[1]["evals"] == 2
