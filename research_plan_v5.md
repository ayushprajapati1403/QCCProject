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
