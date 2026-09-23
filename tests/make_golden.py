"""Record golden regression fingerprints of every optimizer (run ONCE on unchanged code; see tests/test_golden.py).

Each fingerprint hashes the complete observable behaviour of a run (best value, best schedule, evaluation count,
best-so-far curve, diversity curve, per-candidate move sizes, purity curve), so a later refactoring or runtime
optimisation passes only if it is bit-for-bit semantics-preserving.
Usage: python tests/make_golden.py  (writes tests/golden_v0.json; refuses to overwrite)
"""
import hashlib, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
from qi_core import make_instance, Objective, run_pso, run_dmo, run_mrfo, run_ga, run_random  # noqa: E402
from qi_quantum import run_qimrfo, run_qidmo  # noqa: E402
from qi_dynamic import make_dynamic_sequence, run_dynamic  # noqa: E402


def _h(x):
    return hashlib.sha1(np.ascontiguousarray(np.asarray(x, dtype=float)).tobytes()).hexdigest()[:16]


def fingerprint(r, obj):
    tr = r["tracker"]
    return {"best_f": repr(float(r["best_f"])), "best_assign": _h(r["best_assign"]), "n_evals": int(obj.n_evals),
            "evals": _h(tr.evals), "best": _h(tr.best), "mean": _h(tr.mean), "div": _h(tr.div_ham),
            "moves": _h(tr.move_sizes), "counts": [tr.wasted, tr.neutral, tr.improving, tr.worse, tr.gb_improvements],
            "purity": _h(getattr(tr, "purity", []))}


CONFIGS = {
    "PSO": (run_pso, {}), "DMO": (run_dmo, {}), "DMO_greedy": (run_dmo, {"greedy_next": True}), "MRFO": (run_mrfo, {}),
    "GA": (run_ga, {}), "GA_hyper": (run_ga, {"hypermutation": 0.2}), "Random": (run_random, {}),
    "QIMRFO_c0": (run_qimrfo, {}), "QIMRFO_c1": (run_qimrfo, {"decoherence": "1/n"}),
    "QIMRFO_abs": (run_qimrfo, {"decoherence": "1/n", "mode": "born_abs"}),
    "QIMRFO_lin": (run_qimrfo, {"decoherence": "1/n", "mode": "linear"}),
    "QIMRFO_acceq": (run_qimrfo, {"decoherence": "1/n", "accept_equal": True}),
    "QIDMO_c0": (run_qidmo, {}), "QIDMO_c025": (run_qidmo, {"decoherence": "0.25/n"}),
    "QIDMO_lin": (run_qidmo, {"decoherence": "0.25/n", "mode": "linear"}),
    "QIDMO_reg": (run_qidmo, {"decoherence": "0.25/n", "attractor": "register"}),
    "QIDMO_greedy": (run_qidmo, {"decoherence": "0.25/n", "greedy_next": True}),
    "QIDMO_reset05": (run_qidmo, {"decoherence": "0.25/n", "gamma_reset": 0.5}),
}
INSTANCES = {"n20m4_uniform": (20, 4, "uniform", "high"), "n30m5_bimodal": (30, 5, "bimodal", "high")}


def resolve(kw, n):
    out = {}
    for k, v in kw.items():
        if isinstance(v, str) and v.endswith("/n"):
            v = float(v[:-2]) / n
        out[k] = v
    return out


def make_all():
    gold = {}
    for iname, (n, m, dist, het) in INSTANCES.items():
        inst = make_instance(n, m, seed=3, task_dist=dist, hetero=het)
        for cname, (fn, kw) in CONFIGS.items():
            for seed in (0, 1):
                obj = Objective(inst)
                r = fn(inst, obj, 1500, P=12, seed=seed, **resolve(kw, n))
                gold[f"{iname}|{cname}|{seed}"] = fingerprint(r, obj)
    inst = make_instance(25, 5, seed=4)
    obj = Objective(inst, kind="makespan_energy")
    r = run_qimrfo(inst, obj, 1200, P=10, seed=2, decoherence=1.0 / 25)
    gold["energy|QIMRFO_c1|2"] = fingerprint(r, obj)
    for change in ("churn", "vm_fail", "vm_add", "drift"):
        seq = make_dynamic_sequence(20, 5, seed=1, K=3, change=change)
        for algo, strat, kw in (("QI-MRFO", "continue", {}), ("QI-MRFO", "continue_struct", {}), ("QI-MRFO", "shock", {"gamma_shock": 0.5}),
                                ("QI-MRFO", "restart", {}), ("QI-DMO", "continue", {}), ("MRFO", "continue", {}), ("DMO", "continue", {}),
                                ("PSO", "continue", {}), ("GA", "continue", {}), ("GA", "hypermut", {})):
            out = run_dynamic(seq, algo, strat, 1200, 600, seed=1, P=10, **kw)
            gold[f"dyn|{change}|{algo}|{strat}"] = [repr(float(o["best"])) + "|" + repr(float(o["auc_gap"])) for o in out]
    return gold


if __name__ == "__main__":
    path = os.path.join(HERE, "golden_v0.json")
    if os.path.exists(path):
        sys.exit(f"{path} exists; golden values are immutable (delete deliberately to re-record)")
    g = make_all()
    json.dump({"numpy": np.__version__, "python": sys.version.split()[0], "fingerprints": g}, open(path, "w"), indent=1, sort_keys=True)
    print("wrote", path, len(g), "fingerprints")
