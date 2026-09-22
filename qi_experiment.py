"""
qi_experiment.py - V5 experiment harness.

* Instance families with a strict development/held-out split: TUNE = the 4 pilot instances (inst_seed 1, where every
  parameter of the project was chosen); TEST = 8 new families x 10 new instance seeds (101-110), never used for choices.
* Algorithm specs are plain JSON-serialisable dicts, so every experiment records exactly what ran.
* Checkpointed, parallel runner: one JSON line per finished run (resumable), `meta.json` (git commit, versions,
  configuration), `jobs.json` (the full job list; a resume with a different list is refused), `records.csv` and a
  `DONE` marker. A finished experiment directory is immutable: running it again raises.
* Paired statistics by instance: mean difference with bootstrap CI, Wilcoxon signed-rank, matched-pairs rank-biserial
  correlation, Cliff's delta, Vargha-Delaney A12, win/tie/loss, Holm correction within a comparison family.
"""
import hashlib, json, os, platform, subprocess, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np

from qi_core import (make_instance, Objective, Tracker, max_min, min_min, count_improving_moves,
                     run_ga, run_mrfo, run_dmo, run_pso, run_random)
from qi_quantum import run_qimrfo, run_qidmo

# ------------------------------------------------------------------------------------------------ instance families
TUNE_FAMILIES = [(30, 5, "uniform", "high"), (50, 10, "bimodal", "high"), (100, 10, "uniform", "high"), (50, 10, "uniform", "none")]
TUNE_INST_SEEDS = [1]
TEST_FAMILIES = [(80, 8, "uniform", "high"), (150, 15, "uniform", "high"), (300, 30, "uniform", "high"), (100, 10, "bimodal", "high"),
                 (200, 10, "bimodal", "none"), (120, 12, "lognormal", "high"), (60, 12, "uniform", "low"), (100, 20, "lognormal", "low")]
TEST_INST_SEEDS = list(range(101, 111))


def family_name(fam):
    n, m, dist, het = fam
    return f"n{n} m{m} {dist} {het}"


# ------------------------------------------------------------------------------------------------ algorithm registry
FUNCS = {"run_qimrfo": run_qimrfo, "run_qidmo": run_qidmo, "run_ga": run_ga, "run_mrfo": run_mrfo, "run_dmo": run_dmo,
         "run_pso": run_pso, "run_random": run_random}
HEURISTICS = {"max_min": max_min, "min_min": min_min}


def spec(fn, **kw):
    """An algorithm spec. `decoherence_c=c` is resolved to decoherence = c / n at run time."""
    return {"fn": fn, "kw": kw}


def resolve_kwargs(kw, inst):
    out = dict(kw)
    if "decoherence_c" in out:
        out["decoherence"] = out.pop("decoherence_c") / inst.n
    return out


# ------------------------------------------------------------------------------------------------ one run
N_CHECKPOINTS = 20


def run_job(job):
    """Run one (algorithm, instance, seed) job and return a flat record of results and mechanism diagnostics."""
    n, m, dist, het = job["family"]
    inst = make_instance(n, m, seed=job["inst_seed"], task_dist=dist, hetero=het)
    obj = Objective(inst, kind=job.get("objective", "makespan"))
    lb, lb2 = inst.lower_bound(), inst.lower_bound_pmtn()
    mm = Objective(inst)._raw(max_min(inst))[0]
    sp = job["spec"]
    rec = {"exp": job["exp"], "algo": job["algo"], "family": family_name(job["family"]), "n": n, "m": m, "dist": dist, "het": het,
           "inst_seed": job["inst_seed"], "run_seed": job["run_seed"], "budget": job["budget"], "lb": lb, "lb2": lb2, "maxmin": mm}
    t0 = time.time()
    if sp["fn"] in HEURISTICS:
        a = HEURISTICS[sp["fn"]](inst); f = obj(a); tr = None
    else:
        r = FUNCS[sp["fn"]](inst, obj, job["budget"], P=job.get("P", 30), seed=job["run_seed"], **resolve_kwargs(sp["kw"], inst))
        a, f, tr = r["best_assign"], r["best_f"], r["tracker"]
    rec["runtime_s"] = time.time() - t0
    det = Objective(inst).details(a)
    rec.update({"best": float(f), "makespan": det["makespan"], "energy_Wh": det["energy_Wh"], "evals": obj.n_evals,
                "gap": (det["makespan"] - lb) / lb, "gap2": (det["makespan"] - lb2) / lb2, "ratio_mm": det["makespan"] / mm})
    rel, swp, tied = count_improving_moves(inst, a)
    rec.update({"end_impr_reloc": rel, "end_impr_swap": swp, "end_tied_crit": tied})
    if tr is not None:
        s = tr.summary(); s5 = tr.summary_v5()
        rec.update({"wasted": s["wasted_frac"], "neutral": s["neutral_frac"], "improving": s["improving_frac"], "worse": s["worse_frac"],
                    "move_size": s["mean_move_size"], "gb_impr_per_1k": s["gb_impr_per_1k"], **s5,
                    "div_end": tr.div_ham[-1] if tr.div_ham else np.nan,
                    "purity_end": tr.purity[-1] if getattr(tr, "purity", None) else np.nan})
        ev, bs = np.asarray(tr.evals, float), np.asarray(tr.best, float)
        for k in range(1, N_CHECKPOINTS + 1):              # best-so-far makespan at 5 %, 10 %, ..., 100 % of the budget
            x = job["budget"] * k / N_CHECKPOINTS
            idx = np.searchsorted(ev, x, side="right") - 1
            rec[f"bsf_{5 * k:03d}"] = float(bs[max(idx, 0)])
    return {k: (v.item() if isinstance(v, np.generic) else v) for k, v in rec.items()}


def job_key(job):
    n, m, dist, het = job["family"]
    return f"{job['algo']}|{n}|{m}|{dist}|{het}|{job['inst_seed']}|{job['run_seed']}"


def make_jobs(exp, algos, families, inst_seeds, run_seeds, budget, P=30, objective="makespan"):
    return [{"exp": exp, "algo": name, "spec": sp, "family": list(fam), "inst_seed": i, "run_seed": (0 if sp["fn"] in HEURISTICS else r),
             "budget": budget, "P": P, "objective": objective}
            for fam in families for i in inst_seeds for name, sp in algos.items()
            for r in (run_seeds[:1] if sp["fn"] in HEURISTICS else run_seeds)]


# ------------------------------------------------------------------------------------------------ dynamic jobs
def dyn_job_key(job):
    s = job["scenario"]
    return f"{job['algo']}|{s['name']}|{job['seed']}"


def run_dyn_job(job):
    """One dynamic scenario (sequence of K changes) for one strategy; aggregates over the post-change epochs plus
    per-epoch columns (gap, AUC, migrations)."""
    from qi_dynamic import make_dynamic_sequence, run_dynamic
    s, d = job["scenario"], job["dyn"]
    seq = make_dynamic_sequence(s["n"], s["m"], seed=job["seed"], K=s["K"], change=s["change"], rho=s.get("rho", 0.2),
                                task_dist=s.get("task_dist", "uniform"), hetero=s.get("hetero", "high"))
    t0 = time.time()
    out = run_dynamic(seq, d["algo"], d.get("strategy", "continue_struct"), job["budget0"], job["budget"], seed=job["seed"],
                      P=job.get("P", 30), decoherence_c=d.get("decoherence_c", 1.0), mode=d.get("mode", "born_signed"),
                      algo_kw=d.get("algo_kw"), carry_elite=d.get("carry_elite", False), repair=d.get("repair", "random"))
    post = out[1:]
    rec = {"exp": job["exp"], "algo": job["algo"], "scenario": s["name"], "change": s["change"], "n": s["n"], "m0": s["m"],
           "seed": job["seed"], "budget0": job["budget0"], "budget": job["budget"], "runtime_s": time.time() - t0,
           "epoch0_gap": out[0]["gap"], "post_gap": float(np.mean([o["gap"] for o in post])),
           "post_auc": float(np.mean([o["auc_gap"] for o in post])),
           "post_ratio_mm": float(np.mean([o["best"] / o["maxmin"] for o in post])),
           "migrations": float(np.mean([o["migrations"] for o in post])),
           "migr_frac": float(np.mean([o["migrations"] / max(1, o["persist"] - o["forced"]) for o in post])),
           "forced": float(np.mean([o["forced"] for o in post]))}
    for o in out:
        e = o["epoch"]
        rec.update({f"e{e}_type": o["type"], f"e{e}_gap": o["gap"], f"e{e}_auc": o["auc_gap"], f"e{e}_mig": o["migrations"]})
    return {k: (v.item() if isinstance(v, np.generic) else v) for k, v in rec.items()}


# ------------------------------------------------------------------------------------------------ runner
def _git_commit():
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        c = subprocess.run(["git", "rev-parse", "HEAD"], cwd=here, capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "qi_core.py", "qi_quantum.py", "qi_dynamic.py", "qi_experiment.py"],
                               cwd=here, capture_output=True, text=True).stdout.strip()
        return c + ("+uncommitted-changes" if dirty else "")
    except Exception:
        return "unknown"


def run_experiment(name, jobs, workers=None, out_root=None, config=None, quiet=False, runner=None, keyfn=None, sort_cols=None):
    """Run `jobs` into results/<name>/ with checkpointing; returns the records as a pandas DataFrame.
    `runner`/`keyfn` default to static jobs (run_job/job_key); dynamic scenarios use run_dyn_job/dyn_job_key."""
    runner = runner or run_job; keyfn = keyfn or job_key
    import pandas as pd
    out_root = out_root or os.environ.get("QI_RESULTS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "results"))
    d = os.path.join(out_root, name)
    if os.path.exists(os.path.join(d, "DONE")):
        raise RuntimeError(f"{d} is a finished experiment; results are immutable (use a new experiment name)")
    os.makedirs(d, exist_ok=True)
    jobs_path, ckpt = os.path.join(d, "jobs.json"), os.path.join(d, "records.jsonl")
    digest = hashlib.sha256(json.dumps(jobs, sort_keys=True).encode()).hexdigest()
    if os.path.exists(jobs_path):
        if json.load(open(jobs_path))["sha256"] != digest:
            raise RuntimeError(f"{d} holds a checkpoint of a DIFFERENT job list; refusing to mix results")
    else:
        json.dump({"sha256": digest, "jobs": jobs}, open(jobs_path, "w"))
        json.dump({"experiment": name, "git_commit": _git_commit(), "python": sys.version.split()[0], "numpy": np.__version__,
                   "platform": platform.platform(), "started": time.strftime("%Y-%m-%d %H:%M:%S"), "n_jobs": len(jobs),
                   "config": config or {}}, open(os.path.join(d, "meta.json"), "w"), indent=1)
    done = set()
    if os.path.exists(ckpt):
        for line in open(ckpt):
            if line.strip():
                done.add(json.loads(line)["key"])
    todo = [j for j in jobs if keyfn(j) not in done]
    workers = workers or int(os.environ.get("QI_WORKERS", os.cpu_count() or 1))
    t0 = time.time()
    if not quiet:
        print(f"[{name}] {len(jobs)} jobs, {len(done)} already done, running {len(todo)} on {workers} workers", flush=True)
    with open(ckpt, "a") as fh:
        if workers > 1 and len(todo) > 1:
            with ProcessPoolExecutor(max_workers=workers) as ex:
                futs = {ex.submit(runner, j): j for j in todo}
                for k, fut in enumerate(as_completed(futs), 1):
                    rec = fut.result(); rec["key"] = keyfn(futs[fut])
                    fh.write(json.dumps(rec) + "\n"); fh.flush()
                    if not quiet and (k % 100 == 0 or k == len(todo)):
                        print(f"[{name}] {k}/{len(todo)} runs ({time.time() - t0:.0f}s)", flush=True)
        else:
            for j in todo:
                rec = runner(j); rec["key"] = keyfn(j); fh.write(json.dumps(rec) + "\n"); fh.flush()
    recs = [json.loads(line) for line in open(ckpt) if line.strip()]
    df = pd.DataFrame(recs)
    sort_cols = [c for c in (sort_cols or ["family", "algo", "inst_seed", "run_seed"]) if c in df.columns]
    df = df.sort_values(sort_cols).reset_index(drop=True)
    df.to_csv(os.path.join(d, "records.csv"), index=False)
    meta = json.load(open(os.path.join(d, "meta.json")))
    meta.update({"finished": time.strftime("%Y-%m-%d %H:%M:%S"), "n_records": len(df), "wall_s_last_session": time.time() - t0})
    json.dump(meta, open(os.path.join(d, "meta.json"), "w"), indent=1)
    open(os.path.join(d, "DONE"), "w").write(f"{len(df)} records\n")
    return df


def load_experiment(name, out_root=None):
    import pandas as pd
    out_root = out_root or os.environ.get("QI_RESULTS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "results"))
    return pd.read_csv(os.path.join(out_root, name, "records.csv"))


# ------------------------------------------------------------------------------------------------ statistics
def holm(pvals):
    p = np.asarray(pvals, float); order = np.argsort(p); adj = np.empty_like(p); running = 0.0; k = len(p)
    for rank, idx in enumerate(order):
        running = max(running, (k - rank) * p[idx]); adj[idx] = min(1.0, running)
    return adj


def cliffs_delta(x, y):
    x, y = np.asarray(x), np.asarray(y)
    return float((x[:, None] > y[None, :]).mean() - (x[:, None] < y[None, :]).mean())


def a12(x, y):
    """P(x < y) + 0.5 P(x = y): > 0.5 means x tends to be smaller (better, minimisation)."""
    x, y = np.asarray(x), np.asarray(y)
    return float((x[:, None] < y[None, :]).mean() + 0.5 * (x[:, None] == y[None, :]).mean())


def rank_biserial(d):
    """Matched-pairs rank-biserial correlation of paired differences d (negative = first sample smaller)."""
    from scipy.stats import rankdata
    d = np.asarray(d, float); d = d[d != 0]
    if len(d) == 0: return 0.0
    r = rankdata(np.abs(d)); return float((r[d > 0].sum() - r[d < 0].sum()) / r.sum())


def boot_ci(d, B=10000, seed=0, alpha=0.05):
    d = np.asarray(d, float); rng = np.random.default_rng(seed)
    means = d[rng.integers(0, len(d), (B, len(d)))].mean(1)
    return tuple(np.percentile(means, [100 * alpha / 2, 100 * (1 - alpha / 2)]))


def wilcoxon_p(d):
    from scipy.stats import wilcoxon
    d = np.asarray(d, float)
    if len(d) < 2 or np.all(d == 0): return 1.0
    return float(wilcoxon(d, zero_method="wilcox", alternative="two-sided").pvalue)


def paired_table(df, a, b, metric="gap2", by="family", unit="inst_seed", scale=100.0):
    """Compare algorithm a with b: runs are averaged over run seeds per (family, unit) first, then paired by unit.
    One row per family plus a pooled 'ALL' row (pairs = every (family, unit)). Holm is applied across the family rows."""
    import pandas as pd
    g = df[df.algo.isin([a, b])].groupby([by, unit, "algo"])[metric].mean().unstack("algo").dropna()
    rows = []
    for fam, sub in list(g.groupby(level=0)) + [("ALL", g)]:
        xa, xb = sub[a].values * scale, sub[b].values * scale; d = xa - xb
        lo, hi = boot_ci(d)
        rows.append({"family": fam, "A": a, "B": b, "pairs": len(d), f"mean A": xa.mean(), f"mean B": xb.mean(), "diff A-B": d.mean(),
                     "CI95 lo": lo, "CI95 hi": hi, "wins A": int((d < 0).sum()), "ties": int((d == 0).sum()), "wins B": int((d > 0).sum()),
                     "p": wilcoxon_p(d), "r_rb": rank_biserial(d), "cliffs_delta": cliffs_delta(xa, xb), "A12": a12(xa, xb)})
    t = pd.DataFrame(rows)
    fam_mask = t.family != "ALL"
    t["p_holm"] = np.nan
    t.loc[fam_mask, "p_holm"] = holm(t.loc[fam_mask, "p"].values)
    t.loc[~fam_mask, "p_holm"] = t.loc[~fam_mask, "p"]                  # the pooled row is a single pre-registered test
    return t


def mean_ranks(df, algos, metric="gap2", block=("family", "inst_seed", "run_seed")):
    """Average rank of each algorithm over blocks (lower = better)."""
    w = df[df.algo.isin(algos)].pivot_table(index=list(block), columns="algo", values=metric)
    if "run_seed" in block and len(block) > 1:
        # deterministic heuristics run once per instance (run_seed 0): copy their value to the other run seeds of the same
        # instance, otherwise blocks with a missing heuristic would rank the remaining algorithms among fewer entries
        keys = [b for b in block if b != "run_seed"]
        w = w.groupby(level=keys).transform(lambda s: s.fillna(s.mean()))
    return w.rank(axis=1, method="average").mean().sort_values()
