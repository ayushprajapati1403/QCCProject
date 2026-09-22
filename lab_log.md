# Lab log — quantum-inspired DMO for cloud scheduling (Senku loop)

All numbers below were actually measured on this machine (Python 3.13, NumPy 2.3; 5 seeds; 20,000 evaluations per run; prototype scripts `observe_v0.py`, `observe_v1.py`). Anything not measured is labelled UNMEASURED.

## V0 — OBSERVE (classical PSO / DMO / MRFO / GA / random, floor-rounding encoding)

Instances: (n=30,m=5 uniform tasks, heterogeneous VMs), (n=50,m=10 bimodal, hetero), (n=100,m=10 uniform, hetero), (n=50,m=10 uniform, homogeneous VMs). LB = max(total work / total speed, largest task / fastest VM).

| Instance | LB | Max-Min | PSO | DMO | MRFO | GA | Random |
|---|---|---|---|---|---|---|---|
| n30 m5 uni | 44.53 | 45.46 | 45.71 (2.7%) | 45.73 (2.7%) | 47.64 (7.0%) | 44.87 (0.8%) | 47.03 (5.6%) |
| n50 m10 bimodal | 25.11 | 27.06 | 28.75 (14.5%) | 36.50 (45.4%) | 35.45 (41.2%) | 28.74 (14.5%) | 34.41 (37.1%) |
| n100 m10 uni | 47.06 | 47.45 | 56.86 (20.8%) | 82.62 (75.6%) | 93.39 (98.5%) | 47.72 (1.4%) | 90.22 (91.7%) |
| n50 m10 homog | 28.39 | 28.98 | 30.47 (7.3%) | 33.04 (16.4%) | 33.26 (17.2%) | 29.37 (3.5%) | 32.90 (15.9%) |

(percent = gap to LB)

Mechanism diagnostics (n=100, m=10): mean number of tasks changed per candidate — DMO 48.9, MRFO 43.9, PSO 13.8, GA 5.4. Fraction of improving candidates: MRFO 1.4%, PSO 2.8%; MRFO end-diversity (mean pairwise Hamming / n) 0.022, PSO 0.124, DMO 0.565, GA 0.089. MRFO wasted (candidate identical to parent) 14.5%; PSO on n=30: 35.8% wasted.

Landscape probe (1-move local optima from 20 random starts): neutral 1-move neighbours 2–5% (uniform tasks) but 43% (bimodal); 90–100% of 1-move local optima are improvable by a 2-task swap; median relative barrier of the swap's intermediate state 1–5% (uniform), 38% (bimodal).

**What happened?** DMO and MRFO perform at or below random search for n >= 50. **Why?** Their moves are proportional to inter-individual distances in the continuous box [0,m)^n; after floor-decoding these change ~half of all task assignments (a random re-draw), while improvements on the assignment landscape require changing 1–5 tasks. **Evidence:** mean move size 25–49 tasks with <=2% improving candidates vs GA's 4–6 tasks with 16–25% improving. **Alternative explanation:** poor parameters (peep, S) rather than the encoding — partially, but PSO with the same encoding also degrades sharply with n, and the GA with the same budget does not; the encoding is the common factor. **Change:** replace the floor-rounding encoding with a superposition (amplitude) encoding whose measurement produces schedules; move size then becomes a function of register purity. **Prediction:** move size decays smoothly, improving fraction rises, gain grows with n and m; a linear-probability twin captures most of the gain if the benefit is representational.

## V1 — QI-DMO (amplitude registers, Born rule, alpha peeps its measured schedule, gamma=1 babysitter reset)

| Instance | DMO | QI-DMO signed | QI-DMO abs | P-DMO linear (classical twin) | GA |
|---|---|---|---|---|---|
| n30 m5 uni | 45.73 (2.7%) | 45.40 (2.0%) | 45.58 (2.4%) | 45.48 (2.1%) | 44.87 (0.8%) |
| n50 m10 bimodal | 36.50 (45.4%) | 30.54 (21.6%) | 30.18 (20.2%) | 30.26 (20.5%) | 28.74 (14.5%) |
| n100 m10 uni | 82.62 (75.6%) | 49.36 (4.9%) | 48.79 (3.7%) | 48.97 (4.0%) | 47.72 (1.4%) |
| n50 m10 homog | 33.04 (16.4%) | 30.75 (8.3%) | 30.79 (8.5%) | 30.74 (8.3%) | 29.37 (3.5%) |

Mechanism diagnostics (n=100): move size QI-DMO 11.3 (was 48.9); improving 17%; purity at mid-run 0.99 (signed/abs) vs 0.72 (linear); best at 25% budget 51.9 (signed) vs 60.4 (linear) vs 101.9 (DMO). Wasted candidates: 26–76% for Born variants (population collapsed: end diversity 0.001–0.07), 6–40% for linear.

**What happened?** The encoding change removed the pathology: gap to LB at n=100 fell from 76% to 4–5%; gain grows with n as predicted. Signed vs unsigned amplitudes: indistinguishable (interference has no measurable effect at 5 seeds). Born vs linear: same final quality, but Born concentrates faster (purity 0.99 vs 0.72 at mid-run) and reaches good solutions 2x earlier in evaluations; it then collapses and wastes 26–76% of evaluations re-measuring the same schedule. **Why?** Born rule squares amplitudes, so a register slightly biased toward one VM becomes strongly biased after renormalisation: a "collapse accelerator". Once purity -> 1 the only diversity source left is the babysitter reset. **Alternative explanation:** the alpha step always rebuilds candidates from a pure basis state E(b_alpha), which is itself a collapse force independent of the Born rule; the linear twin shares this step, so the difference between the two is attributable to the squaring. **Change (V2):** add a per-candidate depolarising channel (decoherence) with strength gamma = c/n to bound purity and guarantee an expected move of ~2c tasks per measurement. **Prediction:** wasted fraction drops toward 0, final makespan improves most where collapse was earliest (n=30, m=5) and QI-DMO approaches the GA; too large gamma (c >= 2) should hurt by turning the search into random re-sampling. Effect size UNMEASURED.

## V2 — decoherence floor (per-candidate depolarising channel, gamma = c/n) + transfer test on MRFO

QI-DMO, gap to LB (5 seeds, 20k evals): c = 0 / 0.25 / 0.5 / 1 / 2

| Instance | DMO | c=0 | c=0.25 | c=0.5 | c=1 | c=2 | GA |
|---|---|---|---|---|---|---|---|
| n30 m5 uni | 2.7% | 2.0% | 1.6% | 2.1% | 2.1% | 2.7% | 0.8% |
| n50 m10 bimodal | 45.4% | 21.6% | 15.9% | 15.9% | 18.5% | 21.3% | 14.5% |
| n100 m10 uni | 75.6% | 4.9% | 3.9% | 5.5% | 8.1% | 11.2% | 1.4% |
| n50 m10 homog | 16.4% | 8.3% | 6.6% | 10.4% | 12.6% | 14.8% | 3.5% |

Wasted candidates: c=0: 14–76%; c>=0.25: <=1.3%. End purity falls monotonically with c (0.999 -> 0.57). Dose-response: an optimum at c ~ 0.25 (expected ~0.2–0.5 random reassignments per candidate); larger c degrades monotonically on every instance.

Transfer test — the same mechanism on MRFO (QI-MRFO), c = 0.5:

| Instance | MRFO | QI-MRFO c=0 | QI-MRFO c=0.5 | GA | Max-Min |
|---|---|---|---|---|---|
| n30 m5 uni | 47.64 (7.0%) | 45.70 (2.6%) | 45.08 (1.2%) | 44.87 (0.8%) | 45.46 |
| n50 m10 bimodal | 35.45 (41.2%) | 30.18 (20.2%) | 28.10 (11.9%) | 28.74 (14.5%) | 27.06 |
| n100 m10 uni | 93.39 (98.5%) | 53.93 (14.6%) | 47.54 (1.0%) | 47.72 (1.4%) | 47.45 |
| n50 m10 homog | 33.26 (17.2%) | 30.60 (7.8%) | 29.38 (3.5%) | 29.37 (3.5%) | 28.98 |

**What happened?** The decoherence floor helps both hosts, with a clear optimum at weak decoherence. The mechanism transfers: on MRFO it converts the worst classical optimizer into the best population optimizer tested (ties or beats the discrete GA on all four instances; 1.0% from the lower bound at n=100). QI-MRFO > QI-DMO on every instance. **Why?** MRFO uses greedy replacement in all phases and best-centred moves, so on amplitude registers every move is a controlled perturbation of the best schedule; DMO spends one third of its budget on an unconditional noise step (faithful to the MATLAB code) that destroys accepted solutions. **Evidence:** gb-improvement counts and wasted fractions; DMO's high 'improving' fraction is an artefact of the unconditional degradation. **Alternative explanation:** parameter luck (c=0.5 for MRFO vs 0.25 for DMO); V3 sweeps c for MRFO and tests DMO with a greedy next-position step and with the alpha's superposition as attractor. **Open failure:** the Max-Min list heuristic still beats every metaheuristic on the bimodal instance (27.06 vs 28.10) — a makespan-only static batch is heuristic-friendly; the mechanism must be tested where heuristics do not apply (dynamic re-optimisation, energy-aware objective).

## V3 — ablations (5 seeds, 20k evals)

| Variant | n30 m5 | n50 bimodal | n100 m10 | n50 homog |
|---|---|---|---|---|
| DMO greedy-next (classical, MEALPY-dev style) | 2.3% | 17.9% | 30.7% | 12.4% |
| QI-DMO c=0.25 greedy-next | 1.1% | 12.0% | 1.4% | 3.2% |
| QI-DMO c=0.25 attractor = alpha's superposition | 7.1% | 34.2% | 87.8% | 14.2% |
| QI-MRFO c=0.25 / 0.5 / 1 / 2 | 1.8 / 1.2 / 0.9 / 0.9 | 15.0 / 11.9 / 9.7 / 11.3 | 1.3 / 1.0 / 1.0 / 1.2 | 3.3 / 3.5 / 2.9 / 3.5 |
| P-MRFO linear twin c=0.5 | 0.9% | 9.7% | (n/a) | 3.2% |
| QI-MRFO unsigned c=0.5 | 0.9% | (n/a) | (n/a) | (n/a) |
| QI-MRFO c=0.5, P=15 / P=60 | 1.6 / 1.5 | 13.0 / 12.0 | 1.4 / 1.2 | 2.9 / 3.5 |

**What happened?** (1) DMO's unconditional next-position move explains most of the QI-DMO vs QI-MRFO difference: with a greedy version QI-DMO reaches 1.1 / 12.0 / 1.4 / 3.2 %, on par with QI-MRFO. (2) Using the alpha's superposition instead of its measured schedule as attractor collapses the search into random sampling (purity stays 0.1–0.2, 24–90 tasks changed per candidate): collapse-conditioned attraction is a necessary design element. (3) QI-MRFO's decoherence optimum is c ≈ 1 with a broad plateau 0.5–2 (MRFO is greedy in every phase and filters the noise); QI-DMO's is c ≈ 0.25. (4) The classical linear-probability twin and the unsigned-amplitude variant match the signed Born-rule version: the effect is representational, not "quantum" in the sense of interference or amplitude squaring. (5) Population size 15–60 changes results by < 1 percentage point.

## Dynamic-workload pilot (n=50, m=10; 15k-evaluation warm start, then 6 changes with 4k evaluations each; 5 seeds; QI-MRFO c=0.5)

Mean post-change gap to LB (%) and area under the gap curve (AUC %, recovery speed):

| Strategy | churn 20% | drift (x lognormal 0.3) | VM failure | VM addition |
|---|---|---|---|---|
| QI-MRFO restart | 4.76 / 16.8 | 6.09 / 22.1 | 1.95 / 7.8 | 11.0 / 29.4 |
| QI-MRFO continue (state carried, structural rules) | 4.47 / 6.9 | 4.30 / 10.1 | 1.92 / 2.8 | 6.73 / 8.2 |
| QI-MRFO shock 0.25 | 4.81 / 9.2 | 4.51 / 8.6 | 1.91 / 3.5 | 7.26 / 12.8 |
| QI-MRFO shock 0.5 | 3.92 / 10.4 | 4.13 / 10.6 | 2.32 / 4.6 | 9.15 / 18.5 |
| QI-MRFO shock 0.75 | 4.84 / 15.0 | 6.56 / 18.5 | 2.14 / 7.0 | 8.20 / 22.8 |
| MRFO restart / continue | 53 / 55 | 69 / 67 | 27 / 15 | 84 / 96 |
| GA restart | 6.22 / 17.5 | 6.19 / 20.8 | 2.29 / 8.0 | 10.96 / 27.0 |
| GA continue | 4.73 / 6.8 | 5.62 / 9.8 | 2.57 / 4.6 | 9.57 / 12.7 |
| GA hypermutation (x10 for 20% of the epoch) | 5.67 / 11.4 | 6.70 / 16.1 | 2.53 / 7.5 | 11.42 / 15.3 |

**What happened?** Carrying the register state beats restarting on every change type (AUC 2–4x lower) and beats the GA's carried population on drift, VM failure and VM addition; the representation's structural rules (column deletion, uniform share for a new VM, uniform registers for new tasks) do the work. The decoherence shock helps only marginally (final gap on churn/drift at gamma_shock = 0.5, at the cost of recovery speed) and hurts on structural changes; gamma_shock = 0.75 behaves like a restart. GA hypermutation — the classical analogue of the shock — hurts everywhere. **Why?** At 20 % churn or mild drift the old optimum's basin is still good; forgetting discards useful structure. **Alternative explanation:** the shock is applied to every register uniformly, including the unchanged tasks; a change-aware (task-selective) or severity-scaled shock might behave differently. **Next test:** churn-severity sweep rho in {0.1, 0.5, 0.8} to see whether an optimal gamma_shock > 0 appears above a severity threshold. **Status of the controlled-forgetting hypothesis:** not supported at mild change severity; boundary UNMEASURED (sweep running).

## Churn-severity sweep (n=50, m=10, K=6, 15k warm start + 4k per epoch, 5 seeds, QI-MRFO c=1)

Mean post-change gap (%) / AUC (%):

| Strategy | rho=0.1 | rho=0.2 (pilot above, c=0.5) | rho=0.5 | rho=0.8 |
|---|---|---|---|---|
| QI-MRFO restart | 4.22 / 16.0 | 4.76 / 16.8 | 5.11 / 15.6 | 4.59 / 15.3 |
| QI-MRFO continue (structural rules) | 3.65 / 5.7 | 4.70 / 8.3 | 4.31 / 10.1 | 4.79 / 13.6 |
| QI-MRFO shock 0.25 | 4.07 / 8.2 | 4.81 / 9.2 | 4.31 / 11.5 | 4.67 / 13.5 |
| QI-MRFO shock 0.5 | 4.99 / 10.1 | 3.92 / 10.4 | 4.65 / 12.1 | 5.39 / 15.2 |
| QI-MRFO shock 0.75 | 4.74 / 12.7 | 4.84 / 15.0 | 4.83 / 12.7 | 4.72 / 14.3 |
| GA continue | 4.35 / 6.2 | 4.73 / 6.8 | 5.64 / 8.8 | 5.40 / 9.2 |
| GA hypermutation | 5.50 / 8.7 | 5.67 / 11.4 | 6.14 / 13.0 | 6.11 / 15.7 |

**What happened?** The value of the carried state decays with change severity: at 10 % churn continuation is far better than restart (AUC 5.7 vs 16.0); at 80 % churn restart, continuation and every shock level are statistically indistinguishable (all 4.6–5.4 % gap). At no severity does a decoherence shock beat plain continuation with structural rules on both metrics (the rho=0.2, shock 0.5 final-gap advantage of the first pilot does not reappear at 0.1, 0.5 or 0.8 and is within seed noise). GA hypermutation is worse than GA continuation at every severity. **Conclusion:** the strong form of the controlled-forgetting hypothesis (an interior optimum gamma_shock > 0 that rises with severity) is falsified for uniform, task-agnostic shocks on this problem. **Alternative explanation:** shocks that are selective (only registers of tasks whose ET rows changed) or scaled per task by the size of its change were not tested; also the epoch budget (4000 evaluations) may be too short for a shocked population to re-converge. **What the data does support:** the register representation's structural adaptation rules (new tasks -> uniform registers; VM removal -> column deletion; VM addition -> uniform share) give a warm-start advantage that the floor-encoded swarm cannot have and that exceeds the GA's carried population on drift, VM failure and VM addition. This becomes the dynamic-optimisation research question of the proposal: severity-aware, task-selective decoherence.

## V4 — neutral acceptance (accept equal-fitness candidates) for QI-MRFO, c=1, 5 seeds

| Instance | greedy (default) | accept_equal=True |
|---|---|---|
| n40 m8 identical tasks, homogeneous VMs (pure plateau; optimum 25.0), 10k evals | 29.00 ± 2.00 (16.0 %) | 27.00 ± 2.45 (8.0 %) |
| n100 m10 uniform, 20k | 47.51 (0.96 %) | 47.54 (1.02 %) |
| n50 m10 bimodal, 20k | 27.54 ± 1.39 (9.7 %) | 28.31 ± 1.49 (12.7 %) |
| n30 m5 uniform, 20k | 44.93 (0.91 %) | 45.01 (1.09 %) |

**What happened?** Accepting neutral moves halves the plateau gap but does not reach the optimum in every seed (GA, Max-Min and QI-DMO do); it is neutral on the uniform instances and possibly harmful on the bimodal one (within one standard deviation). **Why?** On the plateau the population is fully collapsed on one schedule and a neutral move only relocates that single point; reaching the 5-per-VM optimum needs a specific two-step exchange that neutral drift finds slowly with 10k evaluations; QI-DMO's unconditional move and the GA's crossover supply larger neutral steps. **Decision:** keep greedy acceptance as the default; the plateau boundary is real and is a population-collapse problem, not just an acceptance-rule problem — which points back to purity-regulated decoherence (V2 plan, item 2) rather than to acceptance rules.

## Full notebook run (QI_MODE=full: 30 seeds, 7 instances, 20k evaluations; dynamic pilot 10 seeds) — executed in Docker, zero cell errors

Outputs: results/executed_full.ipynb, baseline_full.csv, stats_full.csv, ablation_full.csv, sensitivity_full.csv, failure_cases_full.csv, dynamic_full.csv, fig_*_full.png. The numbers are reported in section 26 of quantum_inspired_research_report.md. Summary of what changed relative to the 5-seed pilot: (1) encoding effect confirmed on all 7 instances incl. three held-out shapes (Holm p < 1e-4, Cliff's delta ~ -1); (2) Born rule and sign irrelevant (no instance separates QI-MRFO from the linear twin after Holm); (3) "ties or beats the GA" softens to "GA-class, significantly better on 1 of 7"; (4) Max-Min beats QI-MRFO on 6 of 7 static instances by 0.3–4.7 pp (the pilot's n=100 tie and the fast-mode bimodal win were small-sample artefacts); (5) the decoherence floor is essential for MRFO (13.1 -> 1.1 % at n=100) but marginal for DMO (4.3 -> 4.0 %), whose unconditional step is already a noise floor; (6) dynamic re-optimisation with 10 seeds: carried register state beats GA-continue on all four change types (0.7–2.0 pp, recovery area 20–45 % lower); shocks never beat continuation by more than 0.15 pp.

---

# V5 — research loop continued (22 September 2026, Python 3.11 / NumPy 2.2.6, 4 cores)

Protocol changes introduced in V5, following the audit in `research_plan_v5.md`:

* **Tests.** 190+ unit tests, plus bit-exact golden fingerprints of the V0–V4 code (`tests/golden_v0.json`). Every V5
  feature is opt-in, and the fingerprints stay identical.
* **Development/held-out split.** Parameters are chosen only on the 4 pilot instances (TUNE, `inst_seed` 1), and those
  numbers are labelled selection-biased. Claims are made only on held-out families: 8 families × 10 new instance seeds
  (101–110) × 2 run seeds.
* **Inference unit.** The instance is the unit, not the run seed.
* **Bound.** Gaps are reported against the tighter preemptive bound (`lower_bound_pmtn`, "gap2"). The old `lower_bound`
  is kept for comparability.
* **Immutability.** Results go to write-once experiment directories (`results/<name>/` with `jobs.json`, `meta.json`,
  a JSONL checkpoint and a `DONE` marker).
* **Reproducibility.** The unchanged smoke notebook was re-executed and matches the committed `results/*_smoke.csv`
  to 1.1e-16.

## V5 OBSERVE — where do QI-MRFO's evaluations go? (`observe_v5_diagnostics.py`, `observe_v5_localopt.py`; 5 seeds, 20k evaluations, c = 1, pilot instances)

| Instance | final gap | global duplicate evals | parent-identical | candidates touching the critical VM | last global-best improvement | improving swaps left at the end point |
|---|---|---|---|---|---|---|
| n30 m5 uniform | 0.91 % | 45.8 % | 20.6 % | 44.8 % | 94 % of budget | 4.8 |
| n50 m10 bimodal | 9.68 % | 38.8 % | 11.7 % | 19.8 % | 16 % | 1.0 |
| n100 m10 uniform | 0.96 % | 30.6 % | 16.5 % | 36.9 % | 54 % | 50.0 |
| n50 m10 homogeneous | 2.95 % | 38.3 % | 18.2 % | 33.5 % | 47 % | 22.8 |

**What happened?**
* A third to a half of all evaluations re-evaluate a schedule seen before; the old "wasted" metric counted half of them.
* 100 % of improving candidates move a task off the critical VM, which is a necessary condition, but only 20–45 % of
  candidates do.
* The global best stops improving at 16–54 % of the budget on three of four instances.
* Every end point is relocation-optimal, yet 1–50 strictly improving critical swaps remain. Max-Min is also
  relocation-optimal and never swap-optimal.

**Why?** The measurement samples tasks independently (a product state). At a relocation-optimal schedule the next
improvement needs a *correlated* change of two tasks: t leaves the critical VM and u takes its place. Independent
resampling almost never produces this. A back-of-envelope estimate is about 1e-4 per candidate at n=100 (HYPOTHETICAL
arithmetic).

**Alternative explanations.** (a) Too little noise: adaptive decoherence would fix it. Against this: the pilot's c=2
and c=4 are not better, and noise only raises independent per-task changes. (b) Budget too small. Against this: the
search stalls long before the budget ends.

**Change (H5, one controlled change).** *Critical exchange measurement* (CXM). With probability p_x a measured
candidate also swaps a task t from its critical VM with a shorter task u on another VM, or relocates t when no shorter
task exists. The pair's registers collapse onto the outcome, so accepted registers remember the exchange. The GA gets
the identical operator as the control.

**Prediction (pre-registered, `research_plan_v5.md` §7).** Lower held-out gap (P1). A larger gain where more swaps
were left unused (P2). End points closer to swap-optimal and later stagnation (P3). The linear twin is still equivalent
(P4).

## V5 / H5 — critical exchange measurement: results (`results/h5_tune/`, `results/h5_test/`, `results/h5_analysis.md`, `results/h5_posthoc.md`)

**Development set (selection-biased; used only to choose p_x).** Mean gap2 over the 4 pilot instances (10 seeds):

| Algorithm | Mean gap2 |
|---|---|
| QI-MRFO | 3.73 % |
| QI-MRFO+CXM, p_x = 0.1 / 0.25 / 0.5 / 1.0 | 0.97 / 1.19 / 0.93 / 0.82 % |
| GA | 4.98 % |
| GA+CXM, p_x = 1.0 | 1.88 % |

p_x = 1.0 and 0.5 tied on the pre-registered mean-rank criterion. The tie-break was fixed and committed before the
held-out stage (plan §9).

**Held-out set** (8 new families × 10 new instances × 2 seeds, 20 000 evaluations, 1 440 runs; unit = instance;
gap2 = gap to the preemptive bound):

| Family | Max-Min | GA | GA+CXM | P-MRFO | P-MRFO+CXM | QI-MRFO | QI-MRFO+CXM |
|---|---|---|---|---|---|---|---|
| n80 m8 uniform high | 1.009 | 1.232 | 0.922 | 0.989 | **0.043** | 1.046 | 0.061 |
| n150 m15 uniform high | 0.955 | 2.157 | 2.158 | 1.721 | **0.063** | 1.790 | 0.134 |
| n300 m30 uniform high | 0.815 | 5.819 | 5.163 | 9.123 | **0.169** | 9.075 | 0.329 |
| n100 m10 bimodal high | 0.267 | 3.225 | 0.844 | 4.008 | **0.039** | 3.660 | 0.144 |
| n200 m10 bimodal none | 0.137 | 0.389 | 0.269 | 0.347 | **0.004** | 0.527 | 0.006 |
| n120 m12 lognormal high | 0.286 | 1.563 | 1.536 | 1.052 | **0.045** | 1.300 | 0.075 |
| n60 m12 uniform low | 1.609 | 4.039 | 3.226 | 3.611 | **0.208** | 4.146 | 0.274 |
| n100 m20 lognormal low | **0.000** | 4.457 | 2.251 | 5.855 | 3.458 | 5.628 | 3.307 |

Mean rank over 160 blocks: P-MRFO+CXM 1.57, QI-MRFO+CXM 2.16, Max-Min 3.20, GA+CXM 5.01, P-MRFO 5.38, GA 5.47,
QI-MRFO 5.49, Min-Min 8.18, MRFO 8.55.

**What happened?**
* **P1 confirmed (primary).** QI-MRFO+CXM − QI-MRFO = −2.86 pp (95 % CI [−3.58, −2.21]), better on 76/80 instances,
  Wilcoxon p < 1e-4, rank-biserial −0.96. Seven families are Holm-significant, each with 10/10 wins. The eighth
  (lognormal low) points the same way but is not significant (6/4). No family deteriorates.
* **The p_x = 0.5 sensitivity arm** gives −2.81 pp (78/80): the conclusion does not depend on the tie-break.
* **Max-Min reversal.** Unchanged QI-MRFO loses to Max-Min on 73/80 held-out instances, Holm-significantly on 6/8 families
  (n200 bimodal-none: Holm p = 0.055; n80: 5/5), so the §26 finding generalises beyond single instances. QI-MRFO+CXM **beats Max-Min on 6/8 families** (Holm p = 0.016, 9–10/10
  wins each), ties on bimodal-high (8/2, n.s.), and **loses on n100 m20 lognormal low** (0 wins, 2 ties, 8 losses; Holm p = 0.016).
* **P5.** CXM helps the GA far less: −0.81 pp pooled, 50/28, not significant in any family after Holm. QI-MRFO+CXM beats
  GA+CXM on 73/80 (−1.50 pp; 7/8 families). The gain therefore comes from the combination of the register swarm with
  the exchange, not from the exchange alone.
* **P4 falsified, against the quantum part.** Under CXM the classical linear-probability twin is slightly but
  significantly better than the Born-rule version: 68/80 instances, pooled Wilcoxon p < 1e-4, Holm-significant on
  4 families, margins 0.002–0.16 pp. Without CXM the two remain indistinguishable (38/41, p = 0.64). The best algorithm
  on the held-out set is the classical twin with CXM (P-MRFO+CXM).
* **P3 partially supported.**
  * Improving swaps left at the end point: 139.7 → 10.9 ✓.
  * Last global-best improvement: 54 % → 76 % of the budget ✓.
  * Late-half improving fraction: 1.45 % → 0.44 % ✗, predicted to rise. CXM converges so fast that fewer late
    candidates can still improve: gap2 at 10 % of the budget is 3.8 % against 25.6 %.
  * Global duplicate evaluations: 27.9 % → 2.5 %.
* **P2 not supported as pre-registered.** Spearman(baseline unused swaps, CXM effect in pp) = +0.17, p = 0.69. POST HOC
  (`results/h5_posthoc.md`): the pp effect is capped by each family's baseline gap. The *relative* reduction is
  92–98 % on 7 families and 22 % on the family with 0.4 unused swaps, and it correlates with unused swaps
  (families ρ = 0.71, p = 0.047; instances ρ = 0.35, p = 0.002). This is exploratory only.

**Why?** A relocation-optimal schedule needs a correlated two-task change, and CXM supplies it at one evaluation per
candidate. Greedy acceptance around a collapsed best, together with back-action onto the exchanged registers, turns it
into an efficient stochastic swap-descent around the best-known schedule. In the GA, crossover and generational
replacement dilute it.

**Failure boundary (new).** On n100 m20 lognormal low the preemptive bound equals L_max / S_max on every instance: the
largest task alone on the fastest VM. Max-Min attains it, so it is provably optimal. The swarm reaches it on only 2/10
instances, because emptying the fastest VM needs makespan-neutral moves that strict acceptance rejects: a plateau, as
in the V4 identical-task case.

**Alternative explanations.**
* *CXM only adds exploration budget.* Against this: GA+CXM also has zero parent duplicates, yet gains little.
* *Tuning bias.* Against this: p_x was chosen on disjoint instances, and p_x = 0.5 gives the same result.

**Decision.** RETAIN CXM (p_x = 1) as the recommended option for makespan. Defaults stay unchanged for backward
compatibility. The Born rule is not recommended.

**Next.**
* **H6.** Does CXM carry over to re-optimisation under change, does the elite carry-over (fixing audit risk R4) speed
  up recovery, and how does the carried-state swarm compare with recomputing Max-Min once migrations are counted?
* **Later.** Heuristic seeding and plateau-aware acceptance for the big-task failure family.

## V5 / H6 — re-optimisation under change: CXM × elite carry-over, with migrations (`results/h6_dynamic/`, `results/h6_analysis.md`)

Six held-out scenarios, 10 seeds (instance seeds 101–110), K = 8 changes, a 20 000-evaluation warm start, then 4 000
evaluations per epoch; 600 runs. Means over the post-change epochs, pooled over the 60 (scenario, seed) pairs:

| Strategy | Post-change gap (%) | Recovery AUC (%) | Voluntary migrations per epoch |
|---|---|---|---|
| Max-Min recomputed every epoch | 0.80 | 0.80 | 87.5 |
| Incremental list heuristic (no voluntary migration) | 1.3–239 (collapses under drift / VM addition) | same | 0 |
| GA continue | 4.08 | 7.4 | 20.6 |
| GA+CXM continue | 4.48 | 6.6 | 40.0 |
| QI-MRFO continue (registers + structural rules) | 3.38 | 6.9 | 19.4 |
| QI-MRFO+CXM continue | 0.41 | 1.86 | 58.3 |
| QI-MRFO+CXM continue + elite | 0.47 | 1.80 | 51.6 |
| P-MRFO+CXM continue + elite (classical twin) | **0.29** | **1.58** | 56.1 |
| QI-MRFO+CXM restart | 0.85 | 12.8 | 93.9 |

**What happened?**
* **H6a confirmed (primary).** CXM under change: −2.98 pp [−3.79, −2.30], better on 60/60 pairs; every scenario is
  Holm-significant at 10/10.
* **H6b rejected as pre-registered.** Elite carry-over changes the recovery AUC by −0.06 pp, CI [−0.19, +0.08] (43/17,
  p = 0.034). It helps after churn and VM failure (AUC, Holm p = 0.012). After a **VM addition it hurts**: the
  post-change gap is +0.44 pp, 0/10, Holm p = 0.012. Without CXM the elite helps more clearly (AUC −0.74 pp, 47/13,
  p < 1e-4).
* **H6c.** The register swarm beats the GA, both with CXM, on 60/60 (−4.0 pp). CXM makes the GA *worse* under change
  (+0.40 pp, 16/44, p = 0.0002). Carried state is worth an 11-pp lower recovery AUC than a restart with CXM (60/60).
* **H6d confirmed (pooled).** QI-MRFO+CXM+elite has a lower post-change gap than recomputing Max-Min every epoch
  (−0.33 pp, 48/60, p = 1e-4) with 41 % fewer voluntary migrations (51.6 vs 87.5, 60/60). It is better on 4 scenarios,
  tied on VM addition, and **worse on n200 m20 lognormal mixed** (+0.57 pp, 0/10), where the 4 000-evaluation epochs
  are short for n = 200 and heavy-tailed tasks favour Max-Min.
* **Replication of H5's P4.** Under change as well, the classical linear twin beats the Born rule (−0.17 pp, 55/60;
  Holm-significant on 4/6 scenarios).

**Why?**
* CXM repairs a disturbed schedule with exactly the correlated moves needed, and carried registers start the repair
  next to the old optimum.
* The elite fails after a VM addition because the carried schedule leaves the new VM empty. As the global-best
  attractor it pulls every register toward a solution that ignores the new capacity, while an exchange can never move
  a task onto an empty VM (there is no task there to swap with).

**Alternative explanation for the elite result.** The per-epoch budget (4 000) is too short for the swarm to leave
the elite's basin. Not tested.

**New observation.** CXM roughly **triples voluntary migrations** (19 → 58 per epoch at n = 100). The unconstrained
objective has no reason to keep tasks where they are, and many exchanges shuffle tasks between near-equivalent
schedules. Migration cost therefore has to enter the objective. That is a problem list heuristics cannot address and
the carried-state swarm naturally can.

**Decision.**
* CXM is retained for re-optimisation.
* Elite carry-over is **not** adopted as a default. It is kept as an option with a documented, change-type-dependent
  effect: helps after churn and VM failure, hurts after VM addition. An event-aware variant (no elite after VM
  addition) is a post hoc idea and needs its own pre-registered test.
* **Next:** H7 (already pre-registered: is the swarm needed; seeding), then a migration-aware objective (H8).

## V5 / H7 — is the register swarm needed once CXM exists? Max-Min seeding (`results/h7_tune/`, `results/h7_test/`, `results/h7_analysis.md`)

**Why this test.** Late in an H5 run every QI-MRFO+CXM candidate is "best schedule + per-task noise at rate c/n +
critical exchange", which is exactly the mutation of a (1+1)-EA. H5 never ran that minimal control. H7 runs it, tuned
with comparable effort on the development set (6 configurations; c = 1, p_x = 0.5 selected), on **fresh** held-out
instances (seeds 201–210) so that the seeding remedy is not evaluated on the instances that motivated it.

Mean gap2 (%) on the fresh held-out set (8 families × 10 instances × 2 seeds, 20 000 evaluations):

| Family | Max-Min | GA+CXM+seed | (1+1)-EA+CXM | (1+1)-EA+CXM+seed | P-MRFO+CXM | P-MRFO+CXM+seed | QI-MRFO+CXM | QI-MRFO+CXM+seed |
|---|---|---|---|---|---|---|---|---|
| n80 m8 uniform high | 0.765 | 0.411 | 0.043 | 0.050 | 0.044 | 0.046 | 0.052 | 0.051 |
| n150 m15 uniform high | 0.842 | 0.601 | **0.042** | 0.046 | 0.069 | 0.068 | 0.118 | 0.087 |
| n300 m30 uniform high | 0.857 | 0.597 | 0.075 | **0.065** | 0.136 | 0.110 | 0.413 | 0.166 |
| n100 m10 bimodal high | 0.282 | 0.162 | 0.304 | 0.028 | 0.325 | **0.022** | 0.503 | 0.025 |
| n200 m10 bimodal none | 0.165 | 0.081 | 0.015 | **0.002** | 0.003 | 0.003 | 0.006 | 0.004 |
| n120 m12 lognormal high | 0.246 | 0.171 | 0.186 | **0.036** | 0.331 | **0.036** | 0.203 | 0.040 |
| n60 m12 uniform low | 1.903 | 1.305 | 0.245 | 0.242 | 0.208 | **0.172** | 0.252 | 0.209 |
| n100 m20 lognormal low | 0.145 | 0.094 | 2.330 | 0.020 | 2.115 | 0.025 | 3.107 | **0.019** |

Mean rank over 160 blocks: (1+1)-EA+CXM+seed 2.70, P-MRFO+CXM+seed 3.10, (1+1)-EA+CXM 3.39, QI-MRFO+CXM+seed 3.85,
P-MRFO+CXM 3.98, QI-MRFO+CXM 5.31, GA+CXM+seed 6.40, Max-Min 7.27.

**What happened?**
* **H7a (primary) FAILED.** QI-MRFO+CXM − (1+1)-EA+CXM = +0.18 pp [−0.11, +0.53]. The (1+1)-EA is better on
  **58/80** instances (21 swarm wins, 1 tie), pooled Wilcoxon p = 1e-4 in the (1+1)-EA's favour. It is Holm-significantly
  better on n150 (10/10) and n300 (10/10), and no family favours the swarm. The classical twin P-MRFO+CXM is not
  significantly different pooled (26 vs 54 wins, p = 0.12) but also loses on n150 and n300. **By the pre-registered rule the register swarm is
  declared unnecessary for static makespan once CXM is available, and H5's static gain is attributed to the exchange
  measurement.**
* **H7b confirmed.** Max-Min seeding improves QI-MRFO+CXM by 0.51 pp [−0.88, −0.22], on 67/80 instances (2 ties,
  11 worse). It removes the plateau failure: lognormal-low 3.11 % → 0.02 %, 8/2/0, Holm p = 0.047. It is
  Holm-significant on 3 more families and worsens none.
* **H7c.** The seeded (1+1)-EA ("Max-Min + stochastic CXM local search", the control report §21 asked for) is slightly
  better than the seeded swarm: +0.014 pp [0.004, 0.025], 51/10/19, p = 0.001. It is Holm-better on n150, n200 and
  n300; the swarm is better on none.
* **By construction and measured.** The seeded swarm is never worse than Max-Min and strictly better on 70/80
  instances. It beats the seeded GA+CXM on 70/80.
* **Replications on fresh instances.**
  * QI-MRFO+CXM vs Max-Min: 63/2/15, p = 3e-4. Better on 5 families (Holm), worse again on lognormal-low.
  * Linear twin vs Born rule (seeded): the twin is better on 54/10/16, p < 1e-4.

**Why?** Mechanism diagnostics:
* The (1+1)-EA spends 36 % of its evaluations on duplicates and makes 1.9-task moves, yet it converges faster: gap2
  5.7 % at 5 % of the budget against 10.0 % for QI-MRFO+CXM, and 0.41 % against 0.58 % at the end.
* Once CXM supplies the right correlated move, a single trajectory uses the budget better than 30 individuals that
  share it. The MRFO dynamics add no exploration benefit measurable at 20 000 evaluations.

**Alternative explanations.** (a) The population would pay off at larger budgets or on more rugged landscapes;
UNMEASURED. (b) The swarm's parameters (c = 1) were not re-tuned under CXM, whereas the (1+1)-EA's were; partly
answered by the flat (1+1) grid, and P-MRFO+CXM (same c) is not significantly different from it pooled.

**Decision.**
* For static makespan the recommended method is **Max-Min seeding + (1+1)-EA with CXM moves**, or equivalently the
  seeded classical twin.
* QI-MRFO's remaining claim rests on **re-optimisation under change**. H8, whose (1+1)-EA arm was fixed before these
  results, tests exactly that.
* Seeding is adopted for static runs.
