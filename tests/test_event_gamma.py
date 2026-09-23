"""V5 / H13: decoherence_by_event overrides the decoherence floor after given change types (epochs e > 0 only)."""
import numpy as np
import pytest
import qi_dynamic
from qi_dynamic import make_dynamic_sequence, run_dynamic

KW = dict(P=6, decoherence_c=1.0, carry_elite="except_vm_add", repair="incremental", algo_kw={"exchange": 1.0}, mig_lambda=0.2)


def same(a, b):
    return all(x["cost"] == y["cost"] and np.array_equal(x["assign"], y["assign"]) and x["evals"] == y["evals"] for x, y in zip(a, b))


@pytest.mark.parametrize("override", [None, {}, {"drift": 1.0, "churn": 1.0}])
def test_default_path_unchanged(override):
    """None, an empty dict, or overrides equal to decoherence_c reproduce the default run exactly."""
    seq = make_dynamic_sequence(20, 4, seed=3, K=3, change="mixed")
    base = run_dynamic(seq, "QI-MRFO", "continue_struct", 600, 300, seed=2, **KW)
    assert same(base, run_dynamic(seq, "QI-MRFO", "continue_struct", 600, 300, seed=2, decoherence_by_event=override, **KW))


@pytest.mark.parametrize("algo,strategy", [("QI-MRFO", "continue_struct"), ("(1+1)-EA", "continue")])
def test_gamma_follows_the_event_type(monkeypatch, algo, strategy):
    seen = []
    target = "run_qimrfo" if algo == "QI-MRFO" else "run_one_plus_one"
    orig = getattr(qi_dynamic, target)
    def spy(inst, obj, budget, **kw):
        seen.append((inst.n, kw["decoherence"])); return orig(inst, obj, budget, **kw)
    monkeypatch.setattr(qi_dynamic, target, spy)
    seq = make_dynamic_sequence(24, 5, seed=6, K=6, change="mixed")
    kw = dict(KW) if algo == "QI-MRFO" else dict(decoherence_c=1.0, repair="incremental", algo_kw={"exchange": 0.5}, mig_lambda=0.2)
    rules = {"churn": 0.0, "drift": 0.0, "vm_fail": 0.0}
    run_dynamic(seq, algo, strategy, 500, 200, seed=1, decoherence_by_event=rules, **kw)
    assert len(seen) == len(seq)
    for (inst, info), (n, gamma) in zip(seq, seen):
        expected = 1.0 if info is None else rules.get(info["type"], 1.0)
        assert gamma == pytest.approx(expected / n)
    assert {info["type"] for _, info in seq[1:]} & {"churn", "drift", "vm_fail"}     # the override was exercised
