# Research plan V5 — audit, risks, ranked backlog, pre-registered H5

Written on 22 September 2026, **before** any V5 algorithm change was implemented or run. Every number here comes from
committed code and files (`tests/`, `observe_v5_diagnostics.py`, `observe_v5_localopt.py`,
`results/v5_diagnostics.txt`, `results/v5_localopt.txt`). Anything not measured is labelled UNMEASURED.

## 1. Reproducible baseline (step 1)

* The unchanged notebook was executed with `QI_MODE=smoke` in a scratch copy (so `results/` stayed untouched):
  49 s wall on 4 cores, zero cell errors. Every `results/*_smoke.csv` it regenerated is identical to the committed file
  (maximum absolute numeric difference 1.1e-16, from summation order in one energy value) under Python 3.11 / NumPy 2.2.6,
  whereas the committed files were produced under Python 3.12 / NumPy 2.2.6 in Docker.
* The committed notebook is byte-identical in cell sources to a fresh `python build_notebook.py`, and so is its
  `quantum_inspired_MRFO_cloud_scheduler.ipynb` copy.

## 2. Tests (step 2)

`pytest` (152 tests, 18 s) covers the objective (manual loads, energy formula, combined-objective normalisation,
evaluation counting, the lower bound checked against brute force), register normalisation, projection in all modes,
the depolarising channel (exact mixture, sign preservation, monotone purity, γ=1 → uniform), Born and linear measurement
laws (chi-square), one-hot determinism, zero-probability VMs never sampled, and the move-size identity
E[Hamming] = n − Σ purity. It also covers the dynamic structural rules: VM removal as a projective measurement,
including the zero-mass edge case → uniform; VM addition as a uniform share; task reset; the shock. Finally it checks
deterministic seeds and strict budget accounting (incl. warm starts).
`tests/golden_v0.json` holds bit-exact fingerprints of 113 runs (best value, schedule, curves, move sizes, purity)
recorded from the unchanged code. Every later change must keep them identical, so new behaviour has to be opt-in.

## 3. Profile (step 3)

On this machine a 20 000-evaluation run takes 1.8 s for QI-MRFO at n=100, m=10, against 0.8 s for the GA and 0.6 s for
MRFO. At n=500, m=50 QI-MRFO takes 12 s. The report's 14–41 s were measured on a laptop and in an 18-process container.
cProfile shows no dominant hotspot: the cost is about 10 small NumPy reductions per candidate. `born_probs` is recomputed
2.5× per candidate, followed by `renormalise`, `depolarise`, the cumulative-sum measurement and `Objective._raw`.
Removing the redundant normalisations would change floating-point bits and break the golden fingerprints.
**Decision:** do not micro-optimise existing code. Experiments are cheap enough (≈ 5 000 runs/hour on 4 cores); new
code is written vectorised from the start.

## 4. Audit of the current implementation

What is solid: the three modules are small, pure NumPy and deterministic per seed. Every optimizer shares one budget
unit (`Objective.n_evals`) and never exceeds it (tested). The QI mechanism is cleanly separated
(`qi_quantum.py` S8) from the host dynamics (S9). The classical twin (`mode='linear'`) and the ablations exist. The
notebook is generated from the modules, and the report labels unmeasured claims.

### Correctness / reproducibility risks (exact locations)

| # | Risk | Where | Severity | Action |
|---|---|---|---|---|
| R1 | Every statistical test pairs **run seeds on a single instance per shape** (all shapes use `inst_seed=1`). "Max-Min beats QI-MRFO on 6 of 7 shapes" is therefore a statement about 7 instances, not about the shape distributions | `build_notebook.py` `instance_from_spec`, S14 | high (inference scope) | new harness blocks on instance seeds (10 instances per family) |
| R2 | Parameter-selection bias: c=1 (MRFO) and c=0.25 (DMO) were chosen on the pilot instances, which are 4 of the 7 evaluation instances (the README acknowledges this) | `observe_v2.py`, `observe_v3.py`, notebook `CFG` | medium | TUNE/TEST split with disjoint instance seeds; tuned values never evaluated on TUNE |
| R3 | The notebook's dynamic runs use strategy `continue`, which does **not** reset the registers of replaced tasks under churn (`struct=(strategy != "continue")`). Report §26 labels this row "carried registers + structural rules" | `qi_dynamic.run_dynamic`, `adapt_register_state`; notebook S17 `DYN_CONFIGS` | medium (label) | correct the label; test `continue_struct` explicitly |
| R4 | Warm-start asymmetry: QI-MRFO/QI-DMO carry only `Psi`, but the GA carries its population including its elite. After a change QI-MRFO never re-evaluates the previous best schedule | `qi_quantum.run_qimrfo` return value vs `qi_core.run_ga` | medium (biases the dynamic comparison against QI) | backlog item 7 |
| R5 | `Tracker.candidate` counts only **parent-identical** candidates as wasted. The measured global duplicate rate is 31–46 % against the reported 12–21 % (O1) | `qi_core.Tracker.candidate` | medium (diagnostic understates waste ~2×) | add a global-duplicate diagnostic |
| R6 | The lower bound uses only the k=1 and k=m terms of the Q\|pmtn\|Cmax bound, so it is loose on heavy-tailed instances and gaps are overstated. Relative comparisons are unaffected | `qi_core.CloudInstance.lower_bound` | low | add the exact preemptive bound (Gonzalez–Sahni) as a second, tighter LB |
| R7 | Holm correction is applied per comparison pair across instances, not across the 7×7 table, and the family definition is unstated | `build_notebook.py` S14 | low | state the families explicitly in V5 analyses |
| R8 | Deviations from MEALPY `OriginalMRFO`: the global best is updated inside a phase, and β uses (T−t)/T instead of (T−t+1)/T | `run_mrfo`, `run_qimrfo` | low (wording "faithful") | document |
| R9 | `build_notebook.py` writes only one notebook; the `_MRFO_` copy is manual | `build_notebook.py` end | low | builder writes both |
| R10 | Executing the notebook overwrites committed raw results (`results/baseline_{MODE}.csv`, …) | notebook S2 `CFG["results_dir"]` | medium (immutability) | `QI_RESULTS_DIR` override |
| R11 | `measure` clips the inverse-CDF index to m−1, so a zero-probability last VM could be drawn if the float cumsum < u (≈1e-16). Tested harmless | `qi_quantum.measure` | negligible | none |
| R12 | QI-DMO decoherence in the dynamic harness is hard-coded (0.25/n) | `qi_dynamic.run_dynamic` | negligible | document |

## 5. V5 OBSERVE — where QI-MRFO's evaluations go (measured, 5 seeds, 20k evals, c=1, pilot instances)

| Instance | final gap | global duplicate evals | parent-identical ("wasted") | candidates touching the parent's critical VM | improving candidates touching it | last global-best improvement (fraction of budget) | end points relocation-optimal | improving swaps left at the end point (mean) |
|---|---|---|---|---|---|---|---|---|
| n30 m5 uniform | 0.91 % | 45.8 % | 20.6 % | 44.8 % | 100 % | 0.94 | 5/5 | 4.8 |
| n50 m10 bimodal | 9.68 % | 38.8 % | 11.7 % | 19.8 % | 100 % | 0.16 | 5/5 | 1.0 |
| n100 m10 uniform | 0.96 % | 30.6 % | 16.5 % | 36.9 % | 100 % | 0.54 | 5/5 | 50.0 |
| n50 m10 homogeneous | 2.95 % | 38.3 % | 18.2 % | 33.5 % | 100 % | 0.47 | 5/5 | 22.8 |

* **O1 duplicates.** 31–46 % of evaluations re-evaluate a schedule already seen in the same run (38–51 % in the second half).
* **O2 necessary condition.** A candidate that does not move any task off its reference schedule's critical VM cannot lower
  the makespan, because that VM's load cannot fall. As expected, 100 % of improving candidates move such a task, yet only
  20–45 % of candidates do. Everything else is provably non-improving under strict acceptance.
* **O3 stagnation.** The last improvement of the global best comes at 16–54 % of the budget on three of four instances.
  The late-half improving fraction is 0–0.55 %.
* **O4 missing move type.** QI-MRFO's end points are **always relocation-optimal**: no single task move off the critical
  VM improves them. They are swap-optimal in only 0–40 % of runs, with 1–50 strictly improving critical swaps left.
  Max-Min's schedule is also relocation-optimal but never swap-optimal (2–85 improving swaps). The GA's end points
  still admit a few relocations.

Interpretation: QI-MRFO does not stall for lack of budget or noise. It stalls because its measurement operator samples
tasks **independently** (a product state). At a relocation-optimal schedule the next improvement needs a *correlated*
change of two tasks: t leaves the critical VM and u takes its place. Independent resampling almost never produces that.
A rough estimate at n=100: a specific useful pair needs t → v and u → b at the same time, about 10⁻⁴ per candidate at
c=1 (HYPOTHETICAL arithmetic, not measured).

## 6. Ranked optimisation backlog (step 4)

Expected value = expected improvement of the quantity the project reports (equal-budget makespan, dynamic recovery),
judged from the evidence above.

| Rank | Change | Evidence | Expected value | Novelty | Risk |
|---|---|---|---|---|---|
| 1 | **Critical exchange measurement (CXM)**: a fraction p_x of the measured candidates also exchanges a task on the candidate's critical VM with a shorter task on another VM; the measured pair collapses (back-action) | O4, O2, O3 | high: 5–50 improving swaps sit unused at every end point | moderate. A correlated two-register measurement inside a register swarm; the classical equivalent is swap mutation, which the GA+CXM control tests | low–moderate |
| 2 | Memetic critical-VM local search (relocation + swap descent, delta evaluation, Lamarckian write-back) | O4 | high on makespan | low (memetic) | moderate: how delta evaluations are charged decides the result; needs Max-Min+LS and GA+LS controls |
| 3 | Heuristic seeding (Max-Min/Min-Min as partially decohered basis states) | Max-Min wins 6/7 static instances (§26) | moderate–high against Max-Min | low | risk of diversity collapse |
| 4 | Post-selected measurement on the O2 necessary condition | O2 | moderate early, low late (end points are already relocation-optimal, O4) | moderate | low |
| 5 | Stagnation-triggered partial register reset / success-based (1/5-rule) decoherence | O3 (bimodal stalls at 16 %), c-optimum differs by family (§26 sensitivity) | moderate on bimodal | moderate | moderate (the controller brings its own constants) |
| 6 | Evaluation cache (never re-evaluate a known schedule) | O1 | accounting only (identical trajectory); helps where budget binds (n ≥ 200) | low | low |
| 7 | Dynamic: elite carry-over + change-aware, task-selective decoherence | R4, lab log §Dyn | moderate on recovery AUC | moderate | low |
| 8 | Multi-objective (energy, SLA, cost, migration) | §20: heuristics cannot handle it | high for the thesis framing | moderate | large scope |
| 9 | Larger and more diverse held-out families, tighter LB | R1, R2, R6 | research quality | — | low (done with the V5 harness) |

Adaptive decoherence, the brief's first suggestion, ranks 5th here. The evidence says the binding constraint is the
**type** of move the measurement can express, not the per-task noise rate, and a decoherence controller only rescales
that noise. It stays in the backlog for the stagnation it may fix on bimodal instances (O3).

## 7. Strongest next hypothesis — H5 (critical exchange measurement)

**Statement.** QI-MRFO stagnates at relocation-optimal schedules because its product-state measurement changes tasks
independently and so almost never produces the correlated two-task exchange the makespan landscape requires there (O4).
The change: for a fraction p_x of the candidates, after the ordinary measurement, draw t uniformly from the tasks on the
candidate's critical VM(s) and u uniformly from the tasks on other VMs that are shorter than t (a necessary condition
for the exchange to lower the critical VM's load; if none exist, t is relocated to a uniformly random other VM). The two
tasks exchange VMs, and the two registers collapse onto the measured outcome (depolarised basis states) so that an
accepted register encodes the exchange. Everything else is unchanged: same evaluation budget, same host dynamics, same
decoherence, same greedy acceptance.

**Why it is falsifiable.** It makes directional, quantitative predictions on instances never used for tuning.
A null or negative result on the primary endpoint rejects it.

* **P1 (primary).** On the TEST set, QI-MRFO+CXM − QI-MRFO has a negative mean paired gap difference, with a 95 % bootstrap
  CI excluding 0 and a two-sided Wilcoxon p < 0.05 over the 80 TEST instances. The unit is the instance, averaged over
  2 run seeds.
* **P2 (dose–response across families).** The improvement is larger on uniform/lognormal families than on bimodal
  families, the same ordering as the number of improving swaps left at baseline end points (O4).
* **P3 (mechanism).** Improving swaps left at the end point fall; the last global-best improvement moves later; the
  late-half improving fraction rises.
* **P4 (representation).** P-MRFO+CXM (linear twin) ≈ QI-MRFO+CXM: no family differs with Holm p < 0.05.
* **P5 (open, reported not predicted).** Whether GA+CXM gains as much. That decides whether CXM is generic problem
  knowledge or interacts with the register swarm.

**Acceptance criteria.**
* **RETAIN** (adopt CXM as the recommended QI-MRFO option for makespan) if P1 holds and no TEST family shows a
  Holm-significant deterioration.
* **RETAIN WITH BOUNDARY** if P1 holds but some family deteriorates significantly.
* **REJECT** if P1 fails. The negative result is then documented and the next backlog item is taken.

If P1 holds but P3 does not, the result is flagged as "gain without the predicted mechanism".

## 8. Experiment design (H5)

* **Development (TUNE) set, selection bias labelled.** The 4 pilot instances (inst_seed 1), 10 run seeds, 20 000
  evaluations, P=30. p_x ∈ {0.1, 0.25, 0.5, 1.0} is swept for QI-MRFO+CXM and **separately with the same protocol** for
  GA+CXM, so the control is tuned as fairly as the treatment. The value with the best mean rank of gap is kept.
  c stays 1 and is not re-tuned.
* **Held-out (TEST) set.** 8 families × 10 instances (inst_seed 101–110, never used before), 2 run seeds each, 20 000
  evaluations, P=30:
  (80, 8, uniform, high), (150, 15, uniform, high), (300, 30, uniform, high), (100, 10, bimodal, high),
  (200, 10, bimodal, none), (120, 12, lognormal, high), (60, 12, uniform, low), (100, 20, lognormal, low).
* **Algorithms (equal budget).** Max-Min, Min-Min, GA, GA+CXM, MRFO, QI-MRFO, QI-MRFO+CXM, P-MRFO (linear twin),
  P-MRFO+CXM.
* **Metrics.** Makespan; gap to the old LB and to the tighter preemptive LB; ratio to Max-Min; runtime; evaluations;
  parent-identical and global duplicate rates; fraction of candidates touching the critical VM; improving fraction
  (all and late half); last global-best improvement time; move size; end diversity; end purity; exchange candidates and
  exchange improvements; improving swaps left at the end point; best-so-far curve at 20 checkpoints.
* **Statistics.** Paired by instance. Mean difference with a 10 000-resample percentile bootstrap CI; Wilcoxon
  signed-rank; matched-pairs rank-biserial correlation; Cliff's δ and A12 for continuity with §26. Holm correction
  within each comparison family across the 8 TEST families, plus one pre-registered pooled primary test (P1).
* **Immutability.** Each experiment writes to its own new directory under `results/` with a JSONL checkpoint, a
  `meta.json` (git commit, versions, configuration) and a `DONE` marker. The harness refuses to overwrite a finished
  experiment.

## 9. Amendment before the TEST stage (tie-break), 22 September 2026

The TUNE stage (`results/h5_tune/`, `results/h5_selection.json`) produced a **tie** in the pre-registered selection
criterion for QI-MRFO+CXM: p_x = 1.0 and p_x = 0.5 both have mean rank 2.1375 over the 40 development blocks. The
script's pick of 1.0 came from an implementation-defined sort order, not from a pre-registered rule. The tie-break is
fixed here, after seeing only development data and before any TEST run: **ties are broken by the lower mean gap2 on
the development set**. That gives p_x = 1.0 (0.816 % vs 0.930 %), so the frozen value stays 1.0. The GA+CXM choice
(p_x = 1.0, mean rank 2.05) was not tied.

To show that the conclusion does not hinge on this tie-break, the TEST stage adds one **sensitivity arm**,
QI-MRFO+CXM with p_x = 0.5, reported separately. It plays no part in the primary test P1.

## 10. H5 outcome (recorded after `results/h5_analysis.md`; details in the lab log and report §27)

| Prediction | Result | Verdict |
|---|---|---|
| P1 (primary) | −2.86 pp [−3.58, −2.21], 76/80 instances, p < 1e-4; 7/8 families Holm-significant, none worse | **confirmed → CXM retained** |
| P2 (absolute dose–response) | ρ = +0.17, p = 0.69 | not supported (post hoc: relative effect ρ = 0.71) |
| P3 (mechanism) | unused swaps 140 → 11 ✓, later last improvement ✓, late-half improving rate ✗ | partial |
| P4 (Born ≈ linear under CXM) | linear twin better on 68/80, Holm-significant on 4/8 families (small margins) | **falsified against the Born rule** |
| P5 (GA+CXM) | −0.81 pp pooled, no family after Holm; QI-MRFO+CXM beats GA+CXM on 73/80 | the gain is not generic |

New boundary: QI-MRFO+CXM beats Max-Min on 6/8 held-out families but loses on n100 m20 lognormal low. There Max-Min
is provably optimal, because it attains the preemptive bound L_max / S_max, and the swarm is stuck on a
makespan-neutral plateau.

## 11. H6 — dynamic re-optimisation: CXM under change × elite carry-over, with migration cost (pre-registered after the H5 analysis, before H6 was run)

**Observation basis.**
* The dynamic pilot (lab log, report §26 Part B) showed that carried registers beat restart and GA continuation, and
  that uniform decoherence shocks never help.
* Audit risk R4: QI-MRFO carries only its registers, never its best schedule, while the GA carries its elite.
* H5: CXM lowers the static held-out gap by 2.86 pp.
* Earlier dynamic experiments never counted **migrations**, i.e. the tasks the new schedule moves away from the previous
  deployed one, which is the real cost of re-optimising a running cloud. A per-epoch Max-Min recomputation was also
  never run as a competitor.

**Questions.**
1. Does CXM's static gain carry over to re-optimisation under change?
2. Does carrying the repaired previous best schedule speed up recovery?
3. How does the carried-state swarm compare with recomputing Max-Min every epoch once migrations are counted?

**Design** (`exp_h6_dynamic.py`).
* Six held-out dynamic scenarios, with instance seeds 101–110 (the dynamic pilot used 0–9) and 10 seeds each:
  n=100, m=10 with churn 20 %, drift, VM failure, VM addition, and mixed events; plus n=200, m=20 lognormal with mixed
  events.
* K = 8 changes, a 20 000-evaluation warm start, 4 000 evaluations per epoch, P = 30, c = 1, and p_x = 1 frozen from
  H5. Greedy repair of orphaned tasks for every carried-state strategy.
* Ten strategies:
  * Max-Min recomputed every epoch;
  * an incremental list heuristic (zero voluntary migrations);
  * GA continue and GA+CXM continue;
  * QI-MRFO continue, QI-MRFO+CXM continue, QI-MRFO continue+elite and QI-MRFO+CXM continue+elite (a 2×2 factorial);
  * P-MRFO+CXM continue+elite, the classical twin, added because of P4;
  * QI-MRFO+CXM restart.
* Unit: (scenario, seed). Holm correction across the 6 scenarios; the pooled test over all 60 pairs is the
  pre-registered one for each hypothesis.

**Predictions and acceptance.**
* **H6a (primary).** QI-MRFO+CXM continue has a lower mean post-change gap than QI-MRFO continue (pooled Wilcoxon
  p < 0.05, 95 % CI excluding 0). Retained if this holds and no scenario deteriorates with Holm p < 0.05.
* **H6b.** Elite carry-over lowers the recovery AUC of QI-MRFO+CXM continue (pooled, same criteria). If AUC does not
  improve, H6b is rejected, whatever the final gap does.
* **H6c (reported, direction not predicted).** QI-MRFO+CXM continue+elite vs GA+CXM continue, and the linear twin vs the
  Born version under change.
* **H6d (prediction).** Against Max-Min recomputed every epoch, QI-MRFO+CXM continue+elite has fewer voluntary
  migrations (pooled p < 0.05) and a post-change gap that is not higher (pooled 95 % CI upper bound ≤ +0.1 pp).
  Either failure is reported as a failure.

## 12. H7 — is the register swarm needed once CXM exists? And does Max-Min seeding remove the plateau failure? (pre-registered before H7 was run; H6 was running)

**Observation basis.**
* **Missing control.** Late in an H5 run every QI-MRFO+CXM candidate is "best schedule + per-task noise at rate c/n +
  critical exchange", which is exactly the mutation of a (1+1)-EA. H5 never ran that minimal classical control, so
  the contribution of the register swarm itself (population, MRFO dynamics, superposition) is untested once CXM exists.
* **Failure family.** On n100 m20 lognormal/low Max-Min is provably optimal and the swarm stalls on a plateau (report
  §27.7).

**Design** (`exp_h7_swarm_seed.py`).
* **A fresh held-out set:** the same 8 family shapes as H5 with **new instance seeds 201–210** (never used), 2 run
  seeds, 20 000 evaluations, P = 30. Re-using 101–110 would evaluate a remedy on the very instances that motivated it.
* **The (1+1)-EA+CXM control.** Each task is re-drawn uniformly with probability c/n, then the critical exchange is
  applied with probability p_x; strict acceptance. (c, p_x) is tuned on the development set over
  c ∈ {0.25, 1, 2} × p_x ∈ {0.5, 1}: 6 configurations, against 4 for QI-MRFO+CXM in H5. Selection is by mean rank,
  with ties broken by mean development gap.
* **Frozen from H5:** QI-MRFO+CXM and P-MRFO+CXM use c = 1, p_x = 1.
* **Seeding.** The Max-Min schedule is injected once at the start at the cost of one evaluation. It replaces the worst
  individual as a depolarised basis state (swarm), is the start point (1+1), or replaces individual 0 (GA).
* **Arms:** Max-Min; QI-MRFO+CXM ± seed; P-MRFO+CXM ± seed; (1+1)-EA+CXM ± seed; GA+CXM+seed.

**Hypotheses and acceptance.**
* **H7a (primary, directional).** QI-MRFO+CXM has a lower gap2 than (1+1)-EA+CXM, both unseeded, pooled over the
  80 instances (Wilcoxon p < 0.05, 95 % CI excluding 0). **If this fails**, the register swarm is declared unnecessary
  for static makespan once CXM is available, and the H5 gain is attributed to the exchange measurement, not to the
  swarm.
* **H7b.** Seeding improves QI-MRFO+CXM on the big-task family (Holm p < 0.05) and worsens no other family
  (no Holm-significant deterioration). Otherwise seeding is rejected or restricted.
* **H7c (reported).** Seeded QI-MRFO+CXM vs seeded (1+1)-EA+CXM, i.e. "Max-Min + stochastic local search", the
  control §21 of the report asked for.
* **Replications (reported).** H5's P4 (linear twin vs Born under CXM), and QI-MRFO+CXM vs Max-Min on fresh instances.

## 13. H6 outcome (recorded after `results/h6_analysis.md`)

| Hypothesis | Result | Verdict |
|---|---|---|
| H6a (primary) | CXM under change −2.98 pp [−3.79, −2.30], 60/60, 6/6 scenarios Holm | **confirmed → CXM retained under change** |
| H6b | elite AUC −0.06 pp, CI includes 0; helps churn and VM failure, hurts VM addition (gap +0.44 pp, 0/10) | **rejected** as a default; change-type-dependent option |
| H6c | swarm beats GA (both CXM) 60/60; CXM hurts the GA under change | reported |
| H6d | lower gap than Max-Min recompute (−0.33 pp, 48/60) with 41 % fewer migrations (60/60); worse on n200 lognormal mixed | **confirmed (pooled)** |

New observation: CXM triples voluntary migrations (19 → 58 per epoch at n = 100). This motivates H8, a
migration-aware objective.

## 14. H8 — migration-aware re-optimisation (pre-registered before H8 was run; H7 was running)

**Observation basis (H6).**
* Pooled over H6, CXM lowers the post-change makespan but roughly triples voluntary migrations (19 → 58 per epoch at
  n = 100).
* Recomputing Max-Min every epoch migrates 56–84 % of the persistent tasks.
* The zero-migration incremental heuristic collapses under drift and VM addition (gap up to 239 %).

No list heuristic can trade makespan against migrations, whereas a carried-state population method optimises
whatever objective it is given. H8 tests whether that advantage is real once migrations are priced.

**Objective** (`Objective(kind='makespan_migration')`). After the first epoch:
cost(a) = makespan(a) × (1 + λ · voluntary migrations(a) / eligible tasks), relative to the previous *deployed*
schedule. Eligible tasks are persistent tasks whose VM survived. λ is the relative makespan penalty for migrating
every eligible task.

**Design** (`exp_h8_migration.py`).
* The six H6 scenario types with **fresh seeds 201–210**. K = 8, a 20 000-evaluation warm start and 4 000 evaluations
  per epoch.
* **λ ∈ {0.05, 0.2, 1.0}**, pre-registered so that no favourable λ can be picked afterwards.
* Strategies:
  * Max-Min recomputed every epoch;
  * Incremental (zero voluntary migration);
  * **Chooser**: each epoch it deploys whichever of the two is cheaper under the true cost (a strong heuristic
    baseline at 2 evaluations per epoch);
  * GA continue, QI-MRFO+CXM continue and P-MRFO+CXM continue, all optimising the true cost, with c = 1, p_x = 1,
    greedy repair and no elite (H6b rejected it).

**Hypotheses and acceptance.**
* **H8a (primary, directional).** QI-MRFO+CXM continue has a lower post-change cost gap than the Chooser, pooled over
  the 60 (scenario, seed) pairs. Tested separately at each λ with Holm correction across the three λ values. It is
  retained for every λ at which pooled Holm p < 0.05 and the 95 % CI excludes 0. A λ at which the Chooser is better
  is reported as a boundary.
* **H8b (directional).** QI-MRFO+CXM continue beats GA continue on the same cost (same criteria).
* **Reported.** Linear twin vs Born rule. For each λ, the makespan-gap and migration components separately (the
  trade-off).

### 14.1 Amendment before any H8 run (H7 still running; its outcome unknown)

H8 lacked the dynamic counterpart of H7's minimal control. **(1+1)-EA+CXM continue** is therefore added: a (1+1)-EA
that carries its single deployed schedule across changes, with greedy repair after a VM failure and the development-set
values c = 1, p_x = 0.5 from `results/h7_selection.json`, optimising the same migration-aware cost. It is reported as
"register swarm vs (1+1)-EA carrying one schedule" at each λ. It does not change H8a or H8b. The addition was decided
before any H7 or H8 result was available.

## 15. H7 outcome (recorded after `results/h7_analysis.md`)

| Hypothesis | Result | Verdict |
|---|---|---|
| H7a (primary) | the (1+1)-EA with identical moves beats QI-MRFO+CXM on 58/80 fresh instances (p = 1e-4), Holm-better on n150 and n300 | **failed → register swarm unnecessary for static makespan; H5 gain attributed to CXM** |
| H7b | seeding −0.51 pp (67/11); plateau family 3.11 → 0.02 %; no family worse | **confirmed → seeding adopted for static runs** |
| H7c | seeded (1+1)-EA marginally better than the seeded swarm (51/19, +0.014 pp) | reported |

Updated recommendation for static makespan: Max-Min seed + (1+1)-EA with CXM moves, or the seeded classical twin.
The swarm's case rests on H8 (under change).

## 16. H8 outcome (recorded after `results/h8_analysis.md`)

| Test | λ = 0.05 | λ = 0.2 | λ = 1.0 |
|---|---|---|---|
| H8a swarm < Chooser (pooled) | not retained (CI includes 0; 39/21) | **retained** (−1.48 pp, Holm 0.048) | **retained** (−10.5 pp, Holm 0.005) |
| H8b swarm < GA | **retained** (−2.69 pp, 48/12) | not retained (25/35) | not retained (17/43) |
| swarm vs (1+1)-EA (amendment) | n.s. (24/36) | n.s. (20/40) | n.s. (24/36) |

The effect is heterogeneous by change type. The swarm wins on drift, mixed events and VM addition, and loses on churn
and VM failure, where zero-migration repair is near-optimal. The (1+1)-EA is stuck on VM addition behind a
single-move barrier (post hoc, `results/h8_posthoc_barrier.md`).

## 17. H10 — the deployed schedule as an elite anchor under migration pricing (pre-registered before H10 was run)

**Observation basis (H8).** Under migration pricing the swarm loses to zero-migration repair after churn and VM failure.
Its population is sampled *from* the carried registers and never contains the exact deployed schedule, so it pays
migrations it does not need, about 9 per epoch after churn even at λ = 1. It wins where change calls for coordinated
reconfiguration, including VM addition, thanks to its structural rule for new capacity. H6 rejected the elite only
under the makespan-only objective. Under a migration price the deployed schedule is the natural zero-cost anchor.

**Design** (`exp_h10_elite_migration.py`). The H8 harness, cost and six scenario types, with **fresh seeds 301–310**,
K = 8 and λ ∈ {0.05, 0.2, 1.0}; 900 runs. Strategies:
* Chooser;
* GA continue;
* (1+1)-EA+CXM continue;
* QI-MRFO+CXM continue (the H8 configuration);
* **QI-MRFO+CXM continue + elite**: the repaired previous deployed schedule is evaluated once and replaces the worst
  individual as a depolarised basis state.

**Hypotheses and acceptance** (pooled over 60 pairs per λ; Holm across the three λ; retained at a λ when Holm
p < 0.05 and the 95 % CI excludes 0).
* **H10a (primary).** Elite-anchored < QI-MRFO+CXM continue in cost gap, at each λ.
* **H10b.** Elite-anchored < Chooser at each λ; H8 failed at λ = 0.05.
* **H10c (reported, predicted favourable).** Elite-anchored vs (1+1)-EA+CXM continue, and vs GA continue.
* **Replication (reported).** H8a (QI-MRFO+CXM continue vs Chooser) on the fresh seeds.
* **Local changes (reported).** Per-scenario results on churn and VM failure. The prediction is no Holm-significant loss
  to the Chooser there.

## 18. H9 — purity-regulated decoherence, the original report's §21 item 2 (pre-registered before H9 was run)

**Origin.** The original report (§21, item 2, written before V5) proposed: "set γ_t so that the population's expected
move size stays in a target band (e.g. 1–3 tasks) instead of a fixed c/n". It predicted that this "removes the
residual 5–47 % wasted evaluations at small c without the quality loss seen at large c". The brief lists
feedback-controlled decoherence first. The band [1, 3] comes from that earlier text, so **nothing is tuned for H9**.
Context from H7: the swarm is not the best static method, so H9 tests the mechanism claim, not a practical
recommendation.

**Controller** (`run_qimrfo(move_band=(1, 3))`). After every iteration γ is multiplied by 1.25 when n(1 − mean purity)
< 1 task and divided by 1.25 when > 3, within [0.05/n, 8/n], starting from γ = 1/n.

**Design** (`exp_h9_purity_band.py`). The 8 static TEST family shapes with **fresh instance seeds 301–310**, 2 run
seeds, 20 000 evaluations; 640 runs. Arms: QI-MRFO (fixed c = 1), QI-MRFO + band, QI-MRFO+CXM (c = 1, p_x = 1),
QI-MRFO+CXM + band.

**Hypotheses and acceptance.**
* **H9a (primary; the report's own prediction, without CXM).** Both parts must hold:
  1. the band lowers the global duplicate-evaluation fraction (pooled Wilcoxon p < 0.05, CI excluding 0);
  2. it is non-inferior in gap2: the upper bound of the pooled 95 % CI of (band − fixed) is ≤ +0.10 pp.
* **H9b (under CXM).** The same two criteria.
* **Reported.** Two-sided gap tests per family (Holm), and the c trajectories (c_end, c_mean).

## 20. H10 outcome (recorded after `results/h10_analysis.md`)

| Test | λ = 0.05 | λ = 0.2 | λ = 1.0 |
|---|---|---|---|
| H10a elite < no elite (primary) | rejected (+1.43 pp) | rejected (+2.44 pp; 42/18 wins) | rejected (−0.29 pp; 42/18) |
| H10b elite-anchored < Chooser | n.s. | n.s. | **retained** (−10.8 pp) |
| H8a replication (no elite < Chooser) | **significant** (−0.63 pp) | CI excludes 0, p = 0.074 | **significant** (−10.6 pp) |

Heterogeneity again (the H6b mechanism): the elite wins 10/10 on churn and VM failure at every λ and loses 0–1/10 on
VM addition, where it suppresses the coordinated escape onto the new VM.

## 21. H11 — event-aware elite: carry the deployed schedule after every event except a VM addition (pre-registered before H11 was run)

**Origin (post hoc, therefore tested on fresh seeds).** The elite hurt after VM additions twice: in H6b under the
makespan-only objective, and in H10a under the migration price, where it lost 0–1/10 on VM addition at every λ.
Under the migration price it won 10/10 on churn and VM failure. The mechanism is the same both times. The carried
schedule leaves the new VM empty and, as the global-best attractor, suppresses the coordinated escape that the
register swarm's VM-addition rule produces. H11 tests the rule this suggests: `carry_elite="except_vm_add"`. It is
decided per event, so mixed scenarios receive the elite after every non-addition event.

**Design** (`exp_h11_event_elite.py`). The H8/H10 harness with **fresh seeds 401–410**, λ ∈ {0.05, 0.2, 1.0}; 720 runs.
Strategies: Chooser, QI-MRFO+CXM continue (no elite), + elite (always), + event-aware elite.

**Hypotheses and acceptance** (pooled over 60 pairs per λ; Holm across the three λ; retained at a λ when Holm
p < 0.05 and the 95 % CI excludes 0).
* **H11a (primary).** Event-aware elite < no elite in cost gap, at each λ.
* **H11b.** Event-aware elite < always-elite, at each λ (the VM-addition losses disappear).
* **H11c (reported).** Event-aware elite vs Chooser.
* **Replication (reported).** H10a (always-elite vs no elite) on fresh seeds.

## 22. H9 outcome (recorded after `results/h9_analysis.md`)

| Hypothesis | Result | Verdict |
|---|---|---|
| H9a (without CXM) | duplicates +19.0 pp (78/80 worse); gap2 +0.72 pp [0.20, 1.34] | **rejected (opposite direction)** |
| H9b (under CXM) | duplicates +6.9 pp (77/80 worse); gap2 +0.15 pp [0.04, 0.29] (non-inferiority margin +0.10 broken) | **rejected** |

Mechanism: the mean-purity signal is dominated by a few diffuse registers, so the controller lowers γ and starves the
collapsed registers that produce duplicates. The original report's §21 item 2 prediction is falsified for this
(untuned) controller.

## 23. H11 outcome (recorded after `results/h11_analysis.md`)

| Test | λ = 0.05 | λ = 0.2 | λ = 1.0 |
|---|---|---|---|
| H11a event-aware < no elite (primary) | **retained** (−0.41 pp, 41/9) | **retained** (−0.78 pp, 41/9) | **retained** (−2.19 pp, 40/10) |
| H11b event-aware < always-elite | **retained** (−1.76 pp) | **retained** (−3.45 pp) | **retained** (−2.52 pp) |
| H11c event-aware < Chooser | **−0.83 pp** (47/13) | **−2.27 pp** (45/15) | **−12.7 pp** (47/13) |
| H10a replication (always-elite vs no elite) | n.s. | n.s. | n.s. |

Remaining boundary: pure churn at λ ≥ 0.2, where zero-migration incremental repair stays best. Next (UNMEASURED): an
elite repaired by greedy placement of the new tasks.


## 24. Status of the brief's improvement list after V5 (what was tested, what was not)

| Brief item | V5 status | Evidence |
|---|---|---|
| Adaptive, feedback-controlled decoherence | **tested as H9 and falsified** (the purity-regulated band from the original report §21 raises duplicates). Follow-up observation (development set, descriptive): under CXM the static gap is flat for c ∈ [0, 2], while without CXM c = 0 costs +6.1 / +15.1 pp. An adaptive γ therefore has little static headroom once CXM exists; γ now mainly sets duplicate waste. **Under migration pricing an event-conditioned floor works (H13 ✓ at λ ≥ 0.2)**: no floor after local changes. The VM-addition exception is not needed (H13b ✗) | `results/h9_analysis.md`, `results/v5_c_sweep_paired.md`, `results/h13_analysis.md` |
| Event-aware adaptation (churn, VM failure/addition, drift) | **tested**: CXM under change (H6a ✓); unconditional elite (H6b ✗, H10 ✗); **event-aware elite (H11 ✓, every λ)**; **incremental elite (H12 ✓ at λ ≥ 0.2; it removes the churn boundary)**; structural rule for new VMs (H8 mechanism; H12c: the swarm's remaining advantage over a (1+1)-EA) | `results/h6_*`, `h8_*`, `h10_*`, `h11_*`, `h12_*` |
| Hybrid initialisation (Max-Min / Min-Min / HEFT) | **tested as H7b** (Max-Min seed ✓). Min-Min and HEFT not tested (HEFT does not apply to independent tasks) | `results/h7_analysis.md` |
| Discrete local search, critical-VM relocation, two-task swap | **CXM** (H5 ✓, H6a ✓). A (1+1)-EA with the same moves is the H7 control, and it wins for static makespan | `results/h5_*`, `h7_*` |
| Archive-based or multi-register diversity | **not tested** (UNMEASURED) | — |
| Stagnation detection + partial register resets | **not tested** (UNMEASURED). H5 moved stagnation from 54 % to 76 % of the budget | `results/h5_analysis.md` |
| Self-adaptive exploration parameters | partially: H9's controller. A self-adjusting mutation rate for the (1+1)-EA was not tested | — |
| Multi-objective (makespan, energy, SLA, cost, migration) | **migration tested** (H8, H10). Energy, SLA and monetary cost not tested in V5 (the V0–V4 energy objective is unchanged) | `results/h8_*`, `h10_*` |
| Larger and more diverse held-out families | done: 8 families up to n = 300, m = 30 with lognormal / bimodal / low-heterogeneity shapes; six disjoint fresh seed sets (101–110, 201–210, 301–310, 401–410, 501–510, 601–610) | `qi_experiment.py` |
| Vectorisation, caching, profiling, parallel execution | profiled (no micro-optimisation, since results must stay bit-identical); parallel checkpointed harness; duplicate diagnostics. No evaluation cache (the (1+1)-EA's 36 % duplicates make one a clear next step) | `research_plan_v5.md` §3 |
| Reproducibility, tests, configuration, checkpointing | done: 253 tests incl. golden fingerprints; JSON specs; write-once experiments with commit hashes; pinned requirements; deterministic notebook builds | `tests/`, `qi_experiment.py` |

## 25. H12 — incremental elite: place the new tasks of a churn event by list scheduling (pre-registered before H12 was run)

**Origin (observation on development seeds 11–15, `results/v5_churn_elite.md`, `observe_v5_churn_elite.py`).**
H11's remaining boundary is pure churn at λ ≥ 0.2, where the swarm loses to zero-migration incremental repair.
* **Why the elite is bad after churn.** With `repair="greedy"`, the carried elite repairs only VM failures. After churn,
  every new task keeps the VM of the departed task whose index it took ("slot inheritance"), whatever its length.
* **How large the gap is.** At the start of a churn epoch the slot-inherited elite's priced cost gap is **18–38 %**.
  The incremental schedule's is **1.8–3.0 %**, and both make zero voluntary migrations. New tasks are free to place.
* **What the swarm does with it.** It ends above the incremental schedule's cost on **73–100 %** of churn epochs. It
  spends 4–29 voluntary migrations per epoch repairing a bad start instead of placing the new tasks well.

**Change (one).** `repair="incremental"`: the carried elite is `incremental_list_schedule` of the previous deployed
schedule. Persistent tasks stay where they are; new and orphaned tasks go, longest first, to the VM that finishes them
earliest. Everything else is as in H11, including the event-aware rule (no elite after a VM addition).
* **Where it differs.** For VM failure the elite is identical to `"greedy"`, and for drift it is the previous schedule.
  After a VM addition there is no elite. The two swarm strategies therefore differ only after churn events, so the
  drift, VM-failure and VM-addition scenarios are **ties by construction** (30 of 60 pairs per λ). The effect can
  only come from the churn scenario and the two mixed scenarios.
* **Design guarantee (unit-tested).** The elite is evaluated first, so in every churn epoch the deployed priced cost is
  at most the incremental schedule's cost, relative to the swarm's own previous schedule. This bounds each epoch, not
  the sequence, because the previous schedules differ between strategies.

**Design** (`exp_h12_incremental_elite.py`). The H11 harness with **fresh seeds 501–510**; 6 scenarios ×
λ ∈ {0.05, 0.2, 1.0} × 4 strategies; 720 runs. The strategies are:
* the Chooser;
* the H11 swarm (QI-MRFO+CXM continue, event-aware elite, `repair="greedy"`);
* the H12 swarm (the same with `repair="incremental"`);
* a control: the (1+1)-EA+CXM carrying one schedule with `repair="incremental"`, i.e. incremental repair plus
  stochastic local search with the same moves (H8's tuned c = 1, p_x = 0.5).

**Hypotheses and acceptance** (post-change cost gap; unit = (scenario, seed); pooled over 60 pairs per λ; Holm across
the three λ; retained at a λ when the difference is negative, Holm p < 0.05 and the 95 % CI excludes 0).
* **H12a (primary).** H12 swarm < H11 swarm, at each λ. Prediction: retained at every λ, with the largest effect at
  λ ≥ 0.2.
* **H12b.** H12 swarm < Chooser, at each λ. Secondary, per scenario (Holm across the 6 scenarios within λ): on pure
  churn the H12 swarm is **better** than the Chooser at every λ, where H11 lost 0/10 at λ ≥ 0.2.
* **H12c (control).** H12 swarm < (1+1)-EA with incremental repair, at each λ. Predicted to be driven by VM addition
  (the single-move barrier, H8). On churn the two may not differ, since both start from the incremental schedule.
* **Replication (reported).** H11c (H11 swarm vs Chooser) on fresh seeds.

**What would falsify it.** H12a not retained at λ ≥ 0.2, or the H12 swarm significantly worse than the H11 swarm on a
mixed scenario. The latter would mean the incremental placement anchors the swarm in a worse basin, as the elite did
after VM additions.

**Decision rule.** If H12a is retained at every λ, the recommended configuration changes from `repair="greedy"` to
`repair="incremental"`, keeping `carry_elite="except_vm_add"`.


## 26. H12 outcome (recorded after `results/h12_analysis.md`)

| Test | λ = 0.05 | λ = 0.2 | λ = 1.0 |
|---|---|---|---|
| H12a incremental elite < H11 elite (primary) | **not retained**: −0.25 pp [−0.47, +0.04], 26/3, Holm p = 6e-5 (the CI includes 0) | **retained** (−1.18 pp, 29/0) | **retained** (−2.84 pp, 28/1) |
| H12b incremental elite < Chooser, pooled | **retained** (−0.90 pp, 57/3) | **retained** (−3.08 pp, 56/4) | **retained** (−14.17 pp, 54/6) |
| H12b secondary: better than the Chooser on pure churn | **yes** (10/0) | **yes** (9/1) | n.s. (8/2, −0.66 pp) |
| H12c incremental elite < (1+1)-EA with incremental repair | **retained** (−7.71 pp) | **retained** (−6.52 pp) | n.s. (−2.54 pp, 31/29) |
| Replication of H11c on fresh seeds | ✓ | ✓ | ✓ |

The decision rule required H12a at every λ, so the recommendation changes only for λ ≥ 0.2 (post hoc, labelled).
H12c locates the register swarm's remaining advantage over incremental repair + a (1+1)-EA in VM additions.


## 27. H13 — event-aware decoherence under change (pre-registered before H13 was run)

**Origin (development seeds 11–15, `results/v5_c_dynamic.md`).**
* **Effect of c after local changes.** With the H12 configuration, lower c after churn, drift and VM failure gives
  fewer voluntary migrations at a similar makespan. With a migration price, a random re-draw of a persistent task is a
  paid migration, and CXM already supplies the targeted moves.
* **Effect of c after VM additions.** Lower c hurts at λ ≥ 0.2, because filling new capacity needs exploration.
* **Rule chosen.** No floor after local changes (c = 0) and the default c = 1 after VM additions. Epoch 0 keeps c = 1.

The static result (§24, report §35) is consistent with this: once CXM exists, the floor is not needed for static
makespan.

**Change (one).** `decoherence_by_event={"churn": 0, "drift": 0, "vm_fail": 0}` (qi_dynamic.run_dynamic) on top of the
H12 configuration (QI-MRFO+CXM continue, event-aware incremental elite).
* **Ties by construction.** The rule changes nothing on the VM-addition scenario, so its 10 pairs per λ are ties with
  the c = 1 swarm.

**Design** (`exp_h13_event_gamma.py`). The H12 harness with **fresh seeds 601–610**; 6 scenarios ×
λ ∈ {0.05, 0.2, 1.0} × 4 strategies; 720 runs. The strategies are:
* the Chooser;
* the H12 swarm (c = 1);
* the H12 swarm with c = 0 after every change, including VM additions;
* the H12 swarm with event-aware γ.

**Hypotheses and acceptance** (post-change cost gap; unit = (scenario, seed); pooled over 60 pairs per λ; Holm across
the three λ; retained at a λ when the difference is negative, Holm p < 0.05 and the 95 % CI excludes 0).
* **H13a (primary).** Event-aware γ < c = 1, at each λ.
  * **Prediction:** retained at λ = 0.2 and λ = 1.0.
  * At λ = 0.05 the development-seed effect was about −0.1 pp on the pure scenarios, so it may miss the bar.
* **H13b.** Event-aware γ < c = 0 after every change, at each λ.
  * **Prediction:** retained at λ ≥ 0.2, driven by VM addition.
  * At λ = 0.05 no difference is expected; there, c = 0 was also better after VM additions.
* **H13c (reported).** Event-aware γ vs the Chooser.
* **Reported.** c = 0 after every change vs c = 1.

**What would falsify it.** H13a not retained at λ = 1.0, where the development-seed effect was largest, or the
event-aware swarm significantly worse than c = 1 on any scenario.

**Decision rule.** If H13a is retained at λ = 0.2 and λ = 1.0, the recommended configuration adds the event-aware γ
for λ ≥ 0.2. At λ = 0.05 it is added only if H13a is retained there too.


## 28. H13 outcome (recorded after `results/h13_analysis.md`)

| Test | λ = 0.05 | λ = 0.2 | λ = 1.0 |
|---|---|---|---|
| H13a event-aware γ < c = 1 (primary) | **not retained**: −0.10 pp [−0.24, +0.04], 36/14, Holm p = 0.006 (the CI includes 0) | **retained** (−0.26 pp, 34/16) | **retained** (−0.93 pp, 41/9) |
| H13b event-aware γ < c = 0 after every change | **falsified** (+0.04 pp, n.s.) | **falsified** (+0.06 pp, n.s.) | **falsified** (+0.09 pp, n.s.) |
| H13c event-aware γ vs Chooser | −1.26 pp (58/2) | −3.62 pp (57/3) | −18.34 pp (59/1) |

The decision rule is met for λ ≥ 0.2: the recommended configuration adds the event-aware γ there. H13b shows that the
VM-addition exception is not needed. The gain comes from removing the floor after local changes.

## 29. Scaling study: 500–5000 tasks (requested by the supervisor; descriptive; registered before it was run)

**Question.** How do the algorithms behave when the number of tasks grows to 500, 1000, 1500, 2000 and 5000? All
earlier static studies used n ≤ 300.

**Design** (`exp_scale_tasks.py`, write-once `results/scale_tasks/`).
* **Problems.** One problem per size on a pool of **50 heterogeneous VMs**: speeds 250–2000 MIPS, task lengths uniform
  1000–10000 MI, `make_instance(n, 50, seed=1, "uniform", "high")`. Only the number of tasks changes across sizes; the
  VM count is fixed at 50, so tasks per VM go from 10 to 100.
* **Runs.** 10 independent runs per algorithm and size (run seeds 0–9); the deterministic heuristics run once.
  20 000 evaluations per run, population 30, as in every earlier static study.
* **Algorithms.** Each uses its setting from the earlier studies, with no re-tuning:
  * DMO, QI-DMO (c = 0.25), MRFO, QI-MRFO (c = 1), PSO, GA and random search, as in the V4 baseline;
  * QI-MRFO + swap move (CXM, p_x = 1) and GA + swap move (p_x = 1), as in H5;
  * the (1+1)-EA + swap move (c = 1, p_x = 0.5) and the Max-Min-seeded QI-MRFO + swap and (1+1)-EA + swap, as in H7;
  * the Max-Min and Min-Min heuristics.
* **Measures.** Makespan (s): mean ± SD, best and worst of the 10 runs. Gap to the lower bound (%), runtime per run (s)
  and energy (Wh).

**Expectations (descriptive, not tests).**
* At a fixed budget of 20 000 evaluations, the gaps of the population methods grow with n, because the search space
  grows while the budget does not.
* The list heuristics stay close to the bound, because with many tasks per VM, balancing is easy for them.
* The Max-Min-seeded variants can only improve on Max-Min.
* The classical-rounding DMO / MRFO stay near random search.
* The runtime of the register methods grows about linearly with n: each task keeps a probability over 50 VMs.

**Threats.**
* One problem per size, so problem-to-problem variation is not sampled.
* A fixed budget disadvantages the population methods at large n; that is a property of the budget, not of the methods.
* Synthetic workload.
