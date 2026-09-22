"""Dynamic structural changes: state adaptation rules and the dynamic harness."""
import numpy as np
import pytest
from qi_quantum import (probs, remove_vm_state, add_vm_state, add_tasks_state, shock_state, depolarise, project)
from qi_dynamic import make_dynamic_sequence, adapt_position_state, adapt_ga_state, run_dynamic
from qi_core import make_instance

MODES = ["born_signed", "born_abs", "linear"]


def random_state(P, n, m, mode, seed=0):
    rng = np.random.default_rng(seed)
    return {"Psi": np.stack([project(rng.normal(size=(n, m)), m, mode) for _ in range(P)])}


@pytest.mark.parametrize("mode", MODES)
def test_remove_vm_is_projective_measurement(mode):
    st = random_state(4, 10, 5, mode)
    out = remove_vm_state(st, 2, mode)
    assert out["Psi"].shape == (4, 10, 4)
    for i in range(4):
        p_old = probs(st["Psi"][i], mode)
        p_new = probs(out["Psi"][i], mode)
        cond = np.delete(p_old, 2, axis=1)
        mass = cond.sum(1, keepdims=True)
        # conditional distribution on the surviving VMs; a register whose whole mass sat on the failed VM
        # (conditioning on a zero-probability event) is reset to the uniform superposition
        cond = np.where(mass > 1e-12, cond / np.where(mass > 1e-12, mass, 1.0), 1.0 / 4)
        assert np.allclose(p_new, cond)


def test_remove_vm_collapsed_on_failed_vm_becomes_uniform():
    from qi_quantum import basis_state
    for mode in MODES:
        st = {"Psi": basis_state(np.array([2, 0, 2]), 4)[None]}
        p = probs(remove_vm_state(st, 2, mode)["Psi"][0], mode)
        assert np.allclose(p[0], 1 / 3) and np.allclose(p[1], [1, 0, 0]) and np.allclose(p[2], 1 / 3)


@pytest.mark.parametrize("mode", MODES)
def test_add_vm_uniform_share(mode):
    st = random_state(3, 8, 4, mode)
    out = add_vm_state(st, mode)
    assert out["Psi"].shape == (3, 8, 5)
    for i in range(3):
        p_new = probs(out["Psi"][i], mode)
        assert np.allclose(p_new[:, -1], 1 / 5)
        assert np.allclose(p_new[:, :4], probs(st["Psi"][i], mode) * 4 / 5)
        assert np.allclose(p_new.sum(1), 1.0)


@pytest.mark.parametrize("mode", MODES)
def test_add_tasks_resets_only_new_tasks(mode):
    st = random_state(3, 10, 4, mode)
    before = st["Psi"].copy()
    idx = np.array([1, 7])
    out = add_tasks_state(st, idx, mode)
    assert np.array_equal(st["Psi"], before), "input state must not be mutated"
    keep = np.setdiff1d(np.arange(10), idx)
    assert np.array_equal(out["Psi"][:, keep], before[:, keep])
    for i in range(3):
        assert np.allclose(probs(out["Psi"][i], mode)[idx], 0.25)


def test_shock_equals_channel_per_individual():
    st = random_state(3, 6, 4, "born_signed")
    out = shock_state(st, 0.4, "born_signed")
    for i in range(3):
        assert np.allclose(out["Psi"][i], depolarise(st["Psi"][i], 0.4, 4, "born_signed"))


def test_sequence_shapes_and_changes():
    base = make_instance(20, 6, seed=3)
    seq = make_dynamic_sequence(20, 6, seed=3, K=3, change="vm_fail")
    assert np.array_equal(seq[0][0].task_len, base.task_len) and seq[0][1] is None
    assert [s[0].m for s in seq] == [6, 5, 4, 3]
    seq = make_dynamic_sequence(20, 6, seed=3, K=3, change="vm_add")
    assert [s[0].m for s in seq] == [6, 7, 8, 9]
    seq = make_dynamic_sequence(20, 6, seed=3, K=3, change="churn", rho=0.25)
    for (prev, _), (cur, info) in zip(seq[:-1], seq[1:]):
        changed = np.where(prev.task_len != cur.task_len)[0]
        assert set(changed) <= set(info["idx"]) and len(info["idx"]) == 5
        assert np.array_equal(prev.vm_mips, cur.vm_mips)
    seq = make_dynamic_sequence(20, 6, seed=3, K=3, change="drift")
    for (prev, _), (cur, _) in zip(seq[:-1], seq[1:]):
        assert np.array_equal(prev.task_len, cur.task_len) and not np.array_equal(prev.vm_mips, cur.vm_mips)


def test_position_and_ga_adaptation_stay_in_range():
    rng = np.random.default_rng(0)
    X = rng.uniform(0, 6, (5, 20))
    out = adapt_position_state({"X": X}, {"type": "vm_fail", "j": 2}, 5, rng)
    assert out["X"].min() >= 0 and out["X"].max() < 5
    A = rng.integers(0, 6, (5, 20))
    out = adapt_ga_state({"A": A}, {"type": "vm_fail", "j": 5}, 5, rng)
    assert out["A"].min() >= 0 and out["A"].max() < 5


@pytest.mark.parametrize("change", ["churn", "vm_fail", "vm_add", "drift"])
@pytest.mark.parametrize("algo,strategy", [("QI-MRFO", "continue"), ("QI-MRFO", "continue_struct"), ("QI-MRFO", "shock"),
                                           ("QI-DMO", "continue"), ("MRFO", "continue"), ("DMO", "restart"), ("PSO", "continue"),
                                           ("GA", "continue"), ("GA", "hypermut")])
def test_run_dynamic_end_to_end(change, algo, strategy):
    seq = make_dynamic_sequence(15, 4, seed=0, K=2, change=change)
    out = run_dynamic(seq, algo, strategy, 400, 200, seed=0, P=6)
    assert len(out) == 3
    for o, (inst, _) in zip(out, seq):
        assert o["m"] == inst.m and o["gap"] >= -1e-12 and np.isfinite(o["auc_gap"])
