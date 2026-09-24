# Lab log — quantum-inspired DMO for cloud scheduling (Senku loop)

> **Where the files are (23 September 2026).** The repository was reorganised into folders; file names are unchanged. Modules are in `src/`, experiments in `experiments/`, pilot and observation scripts in `scripts/observe/`, report and figure scripts in `scripts/reports/`, notebooks in `notebooks/`, documents in `docs/`, and raw results still in `results/`. See the README (*Repository layout*).

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

## V5 / H8 — migration-aware re-optimisation (`results/h8_migration/`, `results/h8_analysis.md`, `results/h8_posthoc_barrier.md`)

**Setup.** After the first epoch the cost is makespan × (1 + λ · voluntary migrations / eligible tasks). Six scenario
types, fresh seeds 201–210, K = 8, λ ∈ {0.05, 0.2, 1.0}; 1 260 runs. Every optimizer optimises the true cost. The
(1+1)-EA arm was added by amendment §14.1, before any H7 or H8 result existed.

Pooled means (60 scenario-seed pairs per λ): cost gap % / makespan gap % / voluntary migrations per epoch

| Strategy | λ = 0.05 | λ = 0.2 | λ = 1.0 |
|---|---|---|---|
| Max-Min recomputed every epoch | 4.69 / 0.71 / 86.3 | 16.63 / 0.71 / 86.3 | 80.31 / 0.71 / 86.3 |
| Incremental (no voluntary migration) | 77.76 / 77.76 / 0 | 77.76 / 77.76 / 0 | 77.76 / 77.76 / 0 |
| Chooser (cheaper of the two, each epoch) | 3.40 / 1.29 / 51.3 | 8.96 / 3.34 / 32.6 | 29.99 / 19.36 / 12.9 |
| GA continue | 5.89 / 5.15 / 15.5 | 8.71 / 6.58 / 11.1 | **19.30** / 14.92 / 4.4 |
| (1+1)-EA+CXM continue | 9.31 / 8.05 / 28.4 | 11.61 / 8.31 / 18.8 | 19.36 / 12.60 / 7.2 |
| QI-MRFO+CXM continue | **3.19** / 1.24 / 42.2 | 7.48 / 2.14 / 28.7 | 19.48 / 7.69 / 12.0 |
| P-MRFO+CXM continue (classical twin) | 3.28 / 1.30 / 42.6 | **7.43** / 2.17 / 28.2 | 19.72 / 8.15 / 12.0 |

**What happened (pre-registered tests, pooled over 60 pairs, Holm across the three λ).**
* **H8a (swarm vs Chooser).** Retained at **λ = 0.2** (−1.48 pp [−2.62, −0.30], 34/26, Holm p = 0.048) and
  **λ = 1.0** (−10.5 pp [−15.6, −5.5], 37/23, Holm p = 0.005). **Not retained at λ = 0.05**: 39/21 and p = 1e-4, but the
  CI [−0.84, +0.81] includes 0.
  * **Heterogeneity is the main finding.** At every λ the swarm wins on drift, mixed events and VM addition, Holm p ≤ 0.016
    at λ = 1.0. At λ = 0.2 the VM-addition win (7/3) is not Holm-significant (p = 0.098).
  * It **loses on churn and VM failure** (Holm p = 0.012 at λ = 0.2 and 1.0). There the zero-migration incremental
    heuristic is already near-optimal, and the swarm pays migration penalties it does not need.
* **H8b (swarm vs GA).** Retained only at λ = 0.05 (−2.69 pp, 48/12). At λ = 0.2 and 1.0 the GA wins more pairs, though
  not significantly (35/25, 43/17). The GA migrates least of the population methods.
* **Amendment (swarm vs (1+1)-EA carrying one schedule).** Not significant at any λ. The (1+1)-EA wins more pairs
  (36/24, 40/20, 36/24) but fails catastrophically on VM addition: 40.8 % cost gap and zero migrations at every λ.
* **Linear twin vs Born rule.** Not significant at any λ.

**Why? The VM-addition barrier** (post hoc check, `results/h8_posthoc_barrier.md`, exploratory).
* On a well-balanced deployed schedule every *single-task* move onto a new VM is uphill under the migration price in
  100 % of the 30 cases checked. The makespan gain of relieving one VM is tiny, because the next VM is almost as loaded,
  while one migration costs λ/n of the makespan. A strict (1+1)-EA therefore never leaves the deployed schedule.
* The register swarm's VM-addition rule gives the new VM a uniform share in every register, so its candidates move
  many tasks at once (about 39 per epoch at λ = 0.05) and do escape.
* A naive coordinated move (the shortest task of every old VM) is downhill in only 20 % of cases, since it can
  overload a slow new VM. Which structure makes the swarm's multi-task candidates downhill is therefore not isolated
  (UNMEASURED).

**Why the swarm loses on churn and VM failure.** Its population is *measured from* the carried registers and never
contains the exact deployed schedule, so even at λ = 1 it deploys schedules with about 9 unnecessary migrations per
epoch after churn. The (1+1)-EA and the incremental heuristic start *at* the deployed schedule.

**Decision / next.**
* Under migration pricing no single method dominates: the swarm is best when change calls for coordinated
  reconfiguration, and deployed-schedule-anchored methods are best when change is local.
* The evidence points to one combination: the swarm plus the deployed schedule as an elite (a zero-migration anchor),
  keeping the structural rules that produce coordinated moves after a VM addition. H6 rejected the elite only for the
  makespan-only objective.
* This becomes H10 (pre-registered next).

## V5 / H10 — the deployed schedule as an elite anchor under migration pricing (`results/h10_elite_migration/`, `results/h10_analysis.md`)

**Setup.** The H8 harness with fresh seeds 301–310, λ ∈ {0.05, 0.2, 1.0}; 900 runs. Pooled cost gap % (voluntary
migrations per epoch):

| Strategy | λ = 0.05 | λ = 0.2 | λ = 1.0 |
|---|---|---|---|
| Chooser | 3.41 (49.3) | 8.72 (31.6) | 30.19 (11.3) |
| GA continue | 5.02 (15.6) | 8.33 (11.5) | **18.95** (4.3) |
| (1+1)-EA+CXM continue | 9.36 (27.6) | 11.86 (18.9) | 19.21 (7.6) |
| QI-MRFO+CXM continue | **2.79** (42.2) | **7.35** (28.2) | 19.64 (12.1) |
| QI-MRFO+CXM continue + elite | 4.21 (30.2) | 9.79 (18.9) | 19.35 (7.6) |

**What happened?**
* **H10a (primary) rejected at every λ.** Elite − no elite: +1.43 pp [0.43, 2.70] (33/27, p = 0.76), +2.44 pp
  [0.28, 5.05] (42/18, p = 0.07) and −0.29 pp [−2.23, 1.81] (42/18, p = 0.08). The mean is worse even though the elite
  wins most pairs at λ ≥ 0.2.
  * **Churn and VM failure:** the elite wins 10/10 at every λ (Holm p = 0.012), and at λ ≥ 0.2 it also wins on drift
    and mixed events. Migrations fall sharply, e.g. VM failure 17.0 → 5.3 per epoch at λ = 0.05.
  * **VM addition:** it **loses badly** by +9.1, +19.3 and +12.2 pp with 0–1/10 wins. Migrations after VM addition fall
    from 8.2 to 0.0 at λ = 1.0: the swarm stops using the new capacity.
* **H10b.** Elite-anchored vs Chooser is retained only at λ = 1.0 (−10.8 pp, Holm p = 0.007).
* **H10c.** Against the (1+1)-EA: n.s. at every λ. Against the GA: better at λ = 0.05 (50/10), n.s. at higher λ.
* **Replication of H8a on fresh seeds** (swarm without elite vs Chooser): significant at λ = 0.05 (−0.63 pp, 43/17,
  Holm p = 1e-4) and λ = 1.0 (−10.6 pp, Holm p = 0.013). At λ = 0.2 it is −1.37 pp with the CI excluding 0 but
  Wilcoxon p = 0.074. Across H8 and H10 the swarm without elite has the lower mean cost than the Chooser at every λ,
  but significance varies by seed set.

**Why?** The same mechanism appears for the second time (H6b, now H10a).
* The elite is the global-best attractor. After local changes it is exactly the right anchor, because it costs zero
  migrations.
* After a VM addition it leaves the new VM empty and pulls every register onto a schedule from which every
  single-task move is uphill (the H8 barrier).
* The anchor thereby suppresses the coordinated escape that the VM-addition rule would otherwise produce.

**Decision.**
* The elite is not adopted unconditionally.
* **Post hoc suggestion:** carry the elite after every event **except** VM addition. Derived from H6b + H10a, it is
  pre-registered as H11 and tested on fresh seeds 401–410.

## V5 / H9 — purity-regulated decoherence, the original report's §21 item 2 (`results/h9_test/`, `results/h9_analysis.md`)

**Setup.** The controller multiplies γ by 1.25 when n(1 − mean purity) < 1 task and divides it by 1.25 when > 3, with
the band [1, 3] taken from the original report, so nothing was tuned. It runs on the 8 static family shapes with fresh
seeds 301–310, with and without CXM; 640 runs.

| Pooled | QI-MRFO (c = 1) | QI-MRFO + band | QI-MRFO+CXM (c = 1) | QI-MRFO+CXM + band |
|---|---|---|---|---|
| global duplicate evaluations | 27.4 % | **46.4 %** | 2.5 % | **9.4 %** |
| gap2 | 3.39 % | 4.12 % | 0.34 % | 0.49 % |
| mean c over the run (c = γ·n) | 1.00 | 0.33–1.22 by family | 1.00 | 0.06–0.82 by family |

**What happened?**
* **H9a (primary, without CXM) rejected, in the opposite direction.** The band *raises* duplicate evaluations by
  +19.0 pp (78/80 worse) and *worsens* gap2 by +0.72 pp [0.20, 1.34] (48/26, p = 0.003). Both pre-registered criteria
  fail.
* **H9b (under CXM) rejected.** Duplicates rise by +6.9 pp (77/80 worse). The gap2 difference is +0.15 pp
  [0.04, 0.29]: the band wins 52/26 instances, but the upper CI bound breaks the +0.10 pp non-inferiority margin,
  driven by large losses on lognormal-low (+1.0 pp) and n300 (+0.32 pp).

**Why?** The feedback variable is wrong.
* The controller drove γ *down*, because n(1 − mean purity) sat above 3 tasks: mean c was 0.33–0.64 on 7 of 8
  families without CXM (1.22 on n60) and 0.06–0.82 on all 8 families with CXM, instead of 1.
* The population-mean purity is dominated by a few diffuse registers.
* The duplicates come from the many collapsed ones.
* Lowering γ therefore starves exactly the registers that produce duplicates. Duplicates rise, reproducing V2's
  low-c waste, and the search degrades.
* The report's proxy "expected move size = n − Σ purity" is correct in expectation but is a poor *control* signal,
  because the move-size distribution is bimodal: many zero moves plus some large ones.

**Alternative explanation.** A different band (e.g. scaled with n) could work. That would be a new, tuned
hypothesis. The pre-registered, untuned version from the original report is falsified.

**Decision.** Not adopted. Fixed c = 1 stays the default. A future controller should use a direct signal, such as the
per-register duplicate rate or the parent-identical rate. That is UNMEASURED.

## V5 / H11 — event-aware elite: no elite after a VM addition (`results/h11_event_elite/`, `results/h11_analysis.md`)

**Origin.** The elite hurt after VM additions twice: in H6b and in H10a. There the carried schedule leaves the new VM
empty and, as the attractor, blocks the coordinated escape. It helped after every other event. The post hoc rule "no
elite after a VM addition" was pre-registered (plan §21) and tested on **fresh seeds 401–410**; 720 runs.

Pooled cost gap % (makespan gap %, voluntary migrations per epoch):

| Strategy | λ = 0.05 | λ = 0.2 | λ = 1.0 |
|---|---|---|---|
| Chooser | 3.44 (1.39, 49.2) | 8.72 (3.24, 32.1) | 29.78 (20.08, 11.8) |
| QI-MRFO+CXM continue (no elite) | 3.02 (1.09, 41.0) | 7.23 (2.11, 27.3) | 19.26 (7.79, 11.6) |
| + elite (always) | 4.37 (2.99, 29.8) | 9.90 (6.46, 18.6) | 19.59 (12.66, 7.3) |
| **+ event-aware elite** | **2.61** (0.93, 36.8) | **6.45** (2.23, 23.1) | **17.07** (7.64, 9.8) |

**What happened?**
* **H11a (primary) retained at every λ.** Event-aware elite − no elite: −0.41 pp [−0.63, −0.22], −0.78 pp
  [−1.15, −0.37] and −2.19 pp [−3.09, −1.32]; 41/9, 41/9 and 40/10 wins; Holm p < 1e-4 each. The 10 ties per λ are the
  VM-addition pairs, identical by construction.
* **H11b retained at every λ.** Event-aware − always-elite: −1.76, −3.45 and −2.52 pp (Holm p ≤ 0.018). The
  VM-addition losses disappear.
* **H11c.** The event-aware swarm **beats the Chooser at every λ**: −0.83, −2.27 and −12.7 pp; 47/13, 45/15, 47/13;
  Holm p ≤ 1.4e-4.
  * By scenario (Holm p = 0.012 unless stated) it is better on drift and mixed events at every λ, on VM failure at
    every λ (Holm p = 0.039 at λ = 1.0), on VM addition at λ ≥ 0.2 (8/2 at λ = 0.05, n.s.), and on heavy-tailed n200
    at λ = 1.0 (Holm p = 0.039).
  * It is still **worse on pure churn** at λ ≥ 0.2 (0/10; +2.5 and +6.8 pp). There, zero-migration incremental
    repair is best.
* **Replication.** H10a's rejection of the unconditional elite replicates on the fresh seeds (n.s. at every λ).

**Why?** The event-aware rule keeps the two mechanisms where each helps:
* after local events, the deployed schedule is a zero-migration anchor;
* after a VM addition, no anchor, so the register swarm's uniform-share rule for the new VM can produce the coordinated
  multi-task moves that single moves cannot (the H8 barrier).

**Remaining boundary / next.**
* **Churn.** The carried elite keeps each new task's slot from the old schedule. The incremental heuristic instead
  places new tasks greedily, and that stays cheaper at λ ≥ 0.2. Repairing the elite by greedy placement of new tasks
  (an "incremental-repaired elite") is the obvious next hypothesis. UNMEASURED.

**Decision.** Adopt the event-aware elite (`carry_elite="except_vm_add"`) as the recommended configuration for
migration-priced re-optimisation.

## V5 OBSERVE — the decoherence floor once CXM exists (`results/v5_c_under_cxm.md`, `results/v5_c_without_cxm.md`, `results/v5_c_sweep_paired.md`)

**Question.** Before designing any adaptive-decoherence hypothesis: once CXM exists, does the fixed floor γ = c/n still
matter? If the gap does not respond to c, a controller has nothing to adapt.

**Design.** Development set only: 4 pilot instances, 10 seeds, 20 000 evaluations, P = 30.
* QI-MRFO+CXM and P-MRFO+CXM (p_x = 1) at c ∈ {0, 0.25, 0.5, 1, 2, 4}; 480 runs.
* The control, committed before it ran: the same c = 0 vs c = 1 contrast without CXM on the same instances and seeds;
  160 runs.
* Pairs are run-level on 4 instances. This is descriptive, not a held-out test.

| Mean gap2 % (global duplicate evaluations %) | c = 0 | c = 1 | c = 0 − c = 1 [95 % CI], c = 0 better / c = 1 better |
|---|---|---|---|
| QI-MRFO, no CXM | 9.85 (83.4) | 3.73 (38.2) | +6.12 pp [+4.42, +7.93], 2/38 |
| P-MRFO (linear twin), no CXM | 19.68 (84.7) | 4.56 (47.5) | +15.12 pp [+10.34, +20.52], 2/38 |
| QI-MRFO+CXM | 0.63 (28.7) | 0.82 (7.3) | −0.19 pp [−0.81, +0.44], 24/14 |
| P-MRFO+CXM | 0.72 (36.3) | 0.68 (12.0) | +0.04 pp [−0.22, +0.36], 21/19 |

**What happened?**
* **Without CXM the floor is essential.** Removing it multiplies the gap by 2.6 (QI-MRFO) and 4.3 (linear twin), as in
  V2–V4.
* **With CXM the gap is flat for c ∈ [0, 2].** Every paired difference against c = 1 has a bootstrap CI containing 0,
  for both hosts. Two run-level p values fall just below 0.05, in inconsistent directions (0.045 and 0.043), and
  neither survives Holm within its host. Only c = 4 hurts: +0.55 pp (4/35) and +0.89 pp (3/37).
* **The floor still sets evaluation waste.** Under CXM, duplicate evaluations fall monotonically with c: QI-MRFO+CXM
  is at 28.7 % for c = 0, 7.3 % for c = 1 and 0.1 % for c = 4. At this budget the waste does not change the gap.
* **Side note (descriptive).** Without the floor the Born-rule host degrades less than its linear twin (9.8 vs 19.7 %).
  In every held-out V5 comparison with a working floor (H5, H6, H7, H8), the twin was as good or better.

**Why?** In V2–V4 the floor kept single-task moves available after the registers collapse. Without it, collapsed
registers re-sample the same schedule (83–85 % duplicates) and the search stalls. With p_x = 1, every measured schedule
also receives a critical exchange or relocation, whatever the register purity. Collapsed registers therefore still
move: duplicates drop from 83 % to 29 % at c = 0, and the gap no longer depends on the floor. That is consistent with
CXM taking over the floor's role.

**Consequences for the backlog.**
* **Static makespan under CXM.** Adaptive decoherence has little headroom here: on the development set, any γ with
  c ∈ [0, 2] matches fixed c = 1 within noise.
* **Evaluation waste.** This is the floor's remaining static role. An evaluation cache would remove the cost of
  duplicates without changing the search, so it is the better lever. UNMEASURED.
* **Under change.** γ might still matter as a recovery lever, but the dose-response under change with CXM is
  UNMEASURED.

**Decision.** No adaptive-decoherence hypothesis is pre-registered for static makespan; fixed c = 1 stays the default.

## V5 / H12 — incremental elite: new churn tasks placed by list scheduling (`results/h12_incremental_elite/`, `results/h12_analysis.md`)

**Origin.** On development seeds 11–15 (`results/v5_churn_elite.md`), the carried elite after churn leaves every new
task on the VM of the departed task it replaced.
* **Start cost.** It starts 18–38 % above the bound, against 1.8–3.0 % for the incremental schedule. Both make zero
  voluntary migrations.
* **End cost.** The swarm then ends above the incremental schedule's cost on 73–100 % of churn epochs.

H12 was pre-registered in plan §25 and tested on **fresh seeds 501–510**; 720 runs.

Pooled cost gap % (makespan gap %, voluntary migrations per epoch):

| Strategy | λ = 0.05 | λ = 0.2 | λ = 1.0 |
|---|---|---|---|
| Chooser | 3.40 (1.27, 52.9) | 8.62 (3.25, 31.4) | 29.70 (19.66, 12.7) |
| (1+1)-EA+CXM, incremental repair | 10.21 (9.32, 20.8) | 12.06 (9.81, 13.5) | 18.07 (13.32, 5.2) |
| H11 swarm (event-aware elite, slot inheritance) | 2.76 (1.06, 37.1) | 6.72 (2.49, 22.9) | 18.37 (9.05, 9.6) |
| **H12 swarm (event-aware incremental elite)** | **2.50** (1.19, 29.6) | **5.54** (2.38, 17.6) | **15.53** (8.21, 7.7) |

**What happened?**
* **H12a (primary): retained at λ = 0.2 and 1.0, not at λ = 0.05.**
  * λ = 0.2: −1.18 pp [−1.55, −0.83], 29/0.
  * λ = 1.0: −2.84 pp [−3.79, −1.94], 28/1.
  * Both have Holm p < 1e-5.
  * λ = 0.05: −0.25 pp [−0.47, +0.04], 26/3, Holm p = 6e-5. The rank test is significant, but the bootstrap CI of the
    mean includes 0, so the pre-registered rule (all three conditions) is not met.
    * The three losses are all on heavy-tailed n200 mixed (+0.11 pp, 7/3, n.s.).
    * Churn (−1.20 pp, 10/0) and n100 mixed (−0.43 pp, 9/0) improve.
  * The 30 drift, VM-failure and VM-addition pairs per λ are ties by construction.
  * No scenario is significantly worse, so the pre-registered falsification criterion is not met either.
* **The mechanism on held-out seeds (pure churn, λ = 0.05 / 0.2 / 1.0).**
  * Voluntary migrations per epoch fall from 27.0 / 15.3 / 5.0 to 6.5 / 1.6 / 0.2.
  * The makespan gap changes little at λ ≤ 0.2 (0.48 → 0.57 and 0.92 → 0.92 %) and halves at λ = 1.0
    (2.80 → 1.40 %).
  * The cost gap falls from 2.17 / 4.77 / 9.24 % to 0.97 / 1.32 / 1.69 %.
* **H12b: retained pooled at every λ.** H12 swarm − Chooser: −0.90, −3.08 and −14.17 pp; 57/3, 56/4 and 54/6;
  Holm p < 1e-8.
  * **H11's churn boundary is gone.** On pure churn the swarm is better at λ = 0.05 (10/0) and at λ = 0.2 (9/1,
    Holm p = 0.016). At λ = 1.0 it is 8/2 but n.s. (−0.66 pp, Holm p = 0.084). H11 lost this scenario 0/10 at λ ≥ 0.2.
    The pre-registered secondary prediction (better on churn at every λ) therefore holds only at λ ≤ 0.2.
  * The only scenario not won at λ = 0.05 is heavy-tailed n200 mixed (+0.50 pp, 8/2, n.s.).
* **H12c: the swarm vs incremental repair + a (1+1)-EA with the same moves.**
  * Retained at λ = 0.05 (−7.71 pp, Holm p = 0.006) and λ = 0.2 (−6.52 pp, Holm p = 0.010).
  * n.s. at λ = 1.0 (−2.54 pp, 31/29, p = 0.082).
  * The advantage is concentrated in **VM addition**: −44.6 / −38.6 / −12.2 pp; 10/0, 10/0, 9/1. It also appears in
    n100 mixed at λ = 0.05, a scenario that contains VM additions.
  * On churn, drift and VM failure the (1+1)-EA with incremental repair is as good. On churn it is even slightly
    better in the mean (+0.05 to +0.21 pp, n.s.).
* **Replication.** H11c (H11 swarm vs Chooser) replicates on fresh seeds at every λ: −0.64 / −1.90 / −11.33 pp.

**Why?** New tasks are free to place.
* The slot-inherited elite wastes that freedom, and the swarm then pays migrations to repair it.
* With the incremental elite, the swarm starts at the zero-migration heuristic's cost (guaranteed by construction) and
  migrates only when that pays.
* What remains specific to the register swarm is VM addition. The (1+1)-EA with the same moves and the same repair
  cannot fill a new VM with single moves (the H8 barrier).

**Decision.**
* **Formal.** The pre-registered rule ("retained at every λ") is not met, so the default does not switch
  unconditionally.
* **Post hoc reading, labelled.** For migration prices λ ≥ 0.2 the incremental elite is adopted: `repair="incremental"`
  with `carry_elite="except_vm_add"`. At λ = 0.05 it wins 26 of the 29 non-tied pairs, but its mean advantage is not
  established, so either configuration is defensible there.

**Next (UNMEASURED).** Against incremental repair + a (1+1)-EA, the swarm's value is confined to VM additions.
* **Candidate design.** A hybrid: run the (1+1)-EA after local events (4× cheaper per run: 2.9 s vs 11.6 s) and the
  register swarm only after VM additions.
* **Open problem.** It needs a register state that survives the (1+1)-EA epochs.

## V5 OBSERVE — decoherence under change, and a Max-Min recompute as the elite (`results/v5_c_dynamic.md`, `results/v5_chooser_elite.md`)

Both observations use development seeds 11–15 and the H12 configuration. They are descriptive.

**Decoherence under change** (`observe_v5_c_dynamic.py`; c ∈ {0, 0.5, 1, 2, 4}, six scenarios, three λ; 450 runs).
* **High c hurts at every λ.** Against c = 1, pooled: c = 2 adds +0.29 / +0.48 / +0.76 pp and c = 4 adds
  +1.15 / +1.76 / +2.65 pp (λ = 0.05 / 0.2 / 1.0).
* **c = 0 against c = 1, pooled.**
  * λ = 0.05: −0.24 pp [−0.37, −0.11], 24/6.
  * λ = 0.2: +0.07 pp, 19/11, n.s.
  * λ = 1.0: −0.85 pp, 22/8, n.s. after Holm.
* **The pooled numbers hide a split by event type.**
  * After local changes (churn, drift, VM failure), lower c gives fewer voluntary migrations at a similar makespan.
    For example, on drift at λ = 0.2: 32.6 vs 38.1 migrations per epoch; cost gap 7.34 vs 8.34 %.
  * After a VM addition, lower c hurts at λ ≥ 0.2: a cost gap of 11.4 vs 9.4 % at λ = 0.2. At λ = 1.0 the makespan gap is
    29.8 % at c = 0, 24.5 % at c = 1 and 14.3 % at c = 4. Filling new capacity needs exploration.
* **Mechanism.** Under a migration price, every random re-draw of a persistent task that survives selection is a paid
  migration. CXM already supplies the targeted moves, so after local changes the floor mostly adds priced noise.
* **Consequence.** An event-aware γ (c = 0 after local changes, c = 1 after VM additions) is worth a pre-registered test:
  H13, plan §27. The values come from these development seeds, so the test uses fresh seeds.

**Max-Min recompute as the elite** (`observe_v5_chooser_elite.py`; drift, n100 mixed and n200 mixed; non-VM-addition
epochs).
* **How often the recompute is cheaper.** Measured from the swarm's own previous schedule, the recompute is the cheaper
  heuristic in 9–100 % of epochs.
* **Whether that matters.** The swarm already ends below the recompute in 94–100 % of epochs. The one exception is n200
  mixed at λ = 0.05, where it ends above it in 6 % of epochs.
* **Verdict.** A "Chooser elite" would almost never change the deployed schedule, so it is not pursued. This is a
  negative observation.
* **Why the Chooser still wins n200 mixed at λ = 0.05 (H12 held-out records).** It is not because it migrates little:
  it migrates 136 tasks per epoch, against 51 for the swarm. It wins on makespan, 0.60 vs 3.34 %. Max-Min is
  near-optimal on heavy-tailed tasks, and at λ = 0.05 a full recompute is cheap. The swarm's 4 000 evaluations per
  epoch at n = 200 do not reach that makespan.

## V5 / H13 — event-aware decoherence under change (`results/h13_event_gamma/`, `results/h13_analysis.md`)

**Origin.** On development seeds (`results/v5_c_dynamic.md`), lowering c after local changes removed paid noise
migrations, and lowering it after VM additions hurt at λ ≥ 0.2. H13 was pre-registered in plan §27 and tested on
**fresh seeds 601–610** (720 runs). All swarms use the H12 configuration.

Pooled cost gap % (makespan gap %, voluntary migrations per epoch):

| Strategy | λ = 0.05 | λ = 0.2 | λ = 1.0 |
|---|---|---|---|
| Chooser | 3.52 (1.23, 55.9) | 9.19 (3.28, 35.3) | 33.90 (22.41, 13.9) |
| H12 swarm, c = 1 | 2.36 (0.95, 32.2) | 5.83 (2.25, 20.5) | 16.49 (8.49, 8.6) |
| H12 swarm, c = 0 after every change | 2.22 (0.90, 30.1) | 5.51 (2.46, 17.3) | 15.47 (9.07, 6.9) |
| **H12 swarm, event-aware γ** | **2.25** (0.89, 30.9) | **5.57** (2.37, 18.1) | **15.56** (8.71, 7.2) |

**What happened?**
* **H13a (primary): retained at λ = 0.2 and 1.0, not at λ = 0.05, as the pre-registration anticipated.**
  * Event-aware γ − c = 1: −0.26 pp [−0.45, −0.07] (34/16, Holm p = 0.007) at λ = 0.2 and −0.93 pp [−1.67, −0.17]
    (41/9, Holm p = 0.001) at λ = 1.0.
  * At λ = 0.05: −0.10 pp [−0.24, +0.04], 36/14, Holm p = 0.006. The CI includes 0, so the rule is not met.
  * **Where the gain comes from.** Mostly drift (−0.23 / −1.05 / −3.02 pp), with small, consistent gains on churn and VM
    failure.
  * **Mechanism, as on development seeds.** There are fewer voluntary migrations (for example 20.5 → 18.1 per epoch at
    λ = 0.2) at a similar makespan.
  * No scenario is significantly worse, so the falsification criterion is not met.
* **H13b: falsified.** Event-aware γ − (c = 0 after every change) is +0.04 / +0.06 / +0.09 pp, n.s. at every λ.
  * The VM-addition exception from the development seeds did not replicate: on VM addition, c = 1 vs c = 0 is 3/7, 5/5
    and 5/5.
  * The gain comes from dropping the floor after local changes. What happens after VM additions made no measurable
    difference.
  * **Statistical subtlety.** "c = 0 after every change" vs c = 1 wins the rank test at every λ (47/13, 41/19, 47/13;
    Holm p ≤ 0.002), but its mean CIs all include 0. The event-aware rule passes at λ ≥ 0.2 because it is identical to
    c = 1 on VM addition, which removes that scenario's variance.
* **H13c: the final configuration beats the Chooser at every λ.** −1.26 / −3.62 / −18.34 pp; 58/2, 57/3 and 59/1;
  Holm p < 1e-9.
  * Per scenario, 16 of the 18 scenario × λ cells are Holm-significant wins.
  * The other two (n200 mixed at λ = 0.05, VM addition at λ = 0.2) are 8/2 in its favour but n.s.
  * Pure churn is won at every λ on these seeds: 10/0, 10/0 and 9/1.
* **Replication.** The H12 swarm (c = 1) again beats the Chooser at every λ on these fresh seeds: 2.36 vs 3.52,
  5.83 vs 9.19 and 16.49 vs 33.90 %.

**Why?** Under a migration price, the decoherence floor's random re-draws of persistent tasks are paid moves, and CXM
already supplies the targeted ones. After local changes the floor is therefore priced noise; removing it lowers
migrations without costing makespan. The static observation (report §35) is consistent: once CXM exists the floor is
not needed for makespan.

**Decision (pre-registered rule met at λ ≥ 0.2).** For λ ≥ 0.2 the recommended configuration adds
`decoherence_by_event={"churn": 0, "drift": 0, "vm_fail": 0}`. H13b shows that dropping the floor after VM additions as
well is statistically indistinguishable, but that variant did not pass the pre-registered bar. At λ = 0.05 neither H12
nor H13 met the bar: both win the rank test, but the mean CI includes 0. Every swarm variant beats the Chooser there.

## V5 — scaling study: 500–5000 tasks (supervisor request; `results/scale_tasks/`, `results/scale_tasks_analysis.md`, `docs/summaries/results_scale_tasks.pdf`)

**Design (plan §29, registered before the run).** 500, 1000, 1500, 2000 and 5000 tasks on 50 heterogeneous VMs, one
problem per size. 10 runs per algorithm (the heuristics run once), 20 000 evaluations, population 30, and the settings of
the earlier studies without re-tuning; 610 runs in total. Descriptive.

Mean makespan (s) over 10 runs (lower bound in the last row):

| Algorithm | 500 | 1000 | 1500 | 2000 | 5000 |
|---|---|---|---|---|---|
| DMO (original) | 200.61 | 377.84 | 707.12 | 995.60 | 2140.14 |
| QI-DMO | 90.73 | 143.55 | 324.00 | 478.84 | 1402.89 |
| MRFO (original) | 169.84 | 317.91 | 571.56 | 837.58 | 1917.67 |
| QI-MRFO | 76.89 | 138.95 | 336.44 | 510.95 | 1698.02 |
| **QI-MRFO + swap** | **54.10** | **102.60** | **171.27** | **255.97** | **693.00** |
| **QI-MRFO + swap + Max-Min seed** | **53.49** | **101.47** | **164.93** | **231.69** | **528.30** |
| GA | 66.65 | 123.90 | 290.29 | 460.46 | 1532.38 |
| GA + swap | 59.87 | 108.86 | 185.05 | 286.70 | 861.06 |
| (1+1)-EA + swap | 53.46 | 101.46 | 165.10 | 232.64 | 589.93 |
| (1+1)-EA + swap + Max-Min seed | 53.43 | 101.42 | 164.83 | 231.59 | 528.22 |
| Max-Min heuristic | 53.67 | 101.71 | 165.33 | 231.96 | 528.61 |
| Lower bound | 53.38 | 101.38 | 164.78 | 231.55 | 528.17 |

**What happened?** Unless a bullet says "on average", the comparison holds in every run at every size: every run of the
better method beats every run of the other (Mann–Whitney, Holm p = 0.0009).
* **Quantum-inspired vs original.** QI-DMO beats DMO and QI-MRFO beats MRFO at every size. The advantage shrinks at
  5000 tasks, where the fixed budget is small for the problem (MRFO 1917.67 → QI-MRFO 1698.02 s).
* **The swap move.** With it, QI-MRFO beats the GA at every size (693.00 vs 1532.38 s at 5000 tasks). It also beats the
  GA with the same swap move (861.06 s).
* **Seeded with Max-Min.** QI-MRFO + swap is within 0.03–0.22 % of the lower bound and beats the Max-Min heuristic in
  every run.
* **Negative findings.**
  * Without the swap move, QI-MRFO is behind the GA on average at all five sizes (in every run at 1000, 1500 and 5000
    tasks).
  * The unseeded QI-MRFO + swap drifts from the bound as n grows: 1.36 % at 500 tasks, 31.2 % at 5000.
  * The simple (1+1)-EA with the same swap move is better than the unseeded swarm at every size: 589.93 vs 693.00 s at
    5000 tasks.
  * Seeded, every run of the (1+1)-EA is still slightly better, by less than 0.1 s. The (1+1)-EA is about 16× faster at 5000 tasks:
    8.5 vs 138.9 s per run.
* **Side observation.** QI-DMO is ahead of QI-MRFO on average from 1500 tasks on, and in every run at 5000 tasks
  (1402.89 vs 1698.02 s). UNMEASURED why.

**Why?**
* **The budget.** A fixed budget of 20 000 evaluations is small for thousands of tasks. The single-trajectory (1+1)-EA
  spends every evaluation improving one schedule, while a population of 30 spreads them.
* **Seeding.** Max-Min is already within 0.1–0.6 % of the bound at these sizes, so a seeded method only needs to polish.
* **Runtime.** The register methods cost O(n · m) per evaluation, which is why their runtime grows with tasks × VMs.

**Consequence.** For one-time batches at scale the recommendation from H7 holds: Max-Min seed plus a local search with
the swap move. At thousands of tasks the swarm needs either a seed or a larger budget. The swarm's own case remains the
changing cloud (H11–H13).

## One-file Colab notebook for sharing (supervisor request)

**What happened?** `build_colab_notebook.py` assembles `QI_MRFO_DMO_Colab.ipynb`. It is one self-contained notebook with:
* the tested module code, copied verbatim;
* four commented experiments:
  * A = the V4 baseline;
  * B = the H5 held-out test, plus the (1+1)-EA + swap on the same problems;
  * C = the 500–5000 task scaling study;
  * D = H6c (vs the GA) and H13 (with a migration price);
* saving to a Google Drive folder: every finished run is written at once, and a re-run skips saved runs.

`MODE = "full"` uses the settings of those studies. `MODE = "quick"` is a subset of the same runs: same budgets and
seeds, fewer problems, runs and sizes.

**Evidence.**
* **Quick mode end to end.** Executed with `jupyter nbconvert`: 2 processes, 5.4 min, no errors, 26 files written
  (run CSVs, tables, `all_tables.xlsx`, 4 figures, `summary.txt`).
* **Quick runs vs the committed records.** All 208 quick runs that have a committed counterpart are bit-identical:
  320 of 320 values (makespan, energy, gap, cost gap, migrations). The 6 (1+1)-EA runs of B have no H5 counterpart.
* **Full-mode spot checks.** A further 76 values across A–D match exactly.
  * pandas' default CSV parser drops the last bit of some values (6 of the 76 at first).
  * The notebook therefore reads its own files with `float_precision="round_trip"`.
* **Tests.** `tests/test_colab_notebook.py` keeps the notebook in sync with the modules and re-checks two committed
  records.

**Not tested here.** No Colab runtime is available in this environment, so two things are UNMEASURED:
* the Google Drive mount itself (standard `google.colab.drive` calls, with a guard that stops if Drive is not mounted);
* run times on Colab. Full mode is about 5 CPU-hours here (A 0.5, B 0.7, C 3.4, D 0.8 h); the notebook's "roughly 3–5
  hours on free Colab" is an estimate from that.

## V5 / H14 — the swap move transferred to QI-DMO (`results/h14_test/`, `results/h14_scale/`, `results/h14_analysis.md`)

**Origin.** The standalone QI-DMO notebook requested by the supervisor should show how the swap move improves
QI-DMO, but the move existed only for QI-MRFO, the GA and the (1+1)-EA. It was added to `run_qidmo` as an opt-in
option: the QI-MRFO operator unchanged, in all three search phases, p_x = 1 fixed a priori. H14 was pre-registered in
plan §31 and tested on **fresh instance seeds 701–710** (480 runs) plus the 5 scaling problems (50 runs). Before the
pre-registration was committed, one job was dry-run to validate the code; that result was not used.

Mean gap2 (%) on the 80 fresh problems: DMO 74.37, **QI-DMO 7.39**, QI-DMO+CXM 9.72.

**What happened?**
* **P1 fails; the move makes QI-DMO worse.** QI-DMO+CXM − QI-DMO = +2.33 pp [+1.44, +3.18]. It is better on only 15
  of 80 problems; Wilcoxon p = 9e-8.
* **P2 fails.** 6 of 8 families are Holm-significantly worse. On the other two (n300 m30 uniform, n100 m20 lognormal
  low) the difference is not significant.
* **P3 (descriptive): the opposite on the scaling problems.** The move is better at every size: 77.16 vs 90.73 s at
  500 tasks, 129.87 vs 143.55 s at 1000, 261.84 vs 324.00 s at 1500, 426.72 vs 478.84 s at 2000 and 1198.89 vs
  1402.89 s at 5000. Every run is better at 1500, 2000 and 5000 tasks; Holm p = 0.0009 at every size.
* **Mechanism.** With the move, QI-DMO converges less: end purity 0.95 → 0.83, move size 33 → 53 tasks, more
  improving swaps left unused (371 → 525), and the last global-best improvement comes earlier (85 % → 75 % of the
  budget).
* **Reference.** QI-DMO beats the original DMO on all 80 problems (−67 pp).

**Why? (post hoc, plan §32).** Every QI-MRFO candidate is kept only if it improves, so a bad swap is discarded. QI-DMO's
third phase (next position) keeps every candidate. There, at p_x = 1, every candidate carries a swap, and a worsening
swap is kept too. Far from convergence (the large problems, gaps of 40–166 %), most swaps on the critical VM improve,
which fits the gains there.

**Decision (pre-registered rule).** REJECT for the 30–300-task range. The explanation became H15 (plan §33): the swap
only in the two phases that keep improvements, with p_x chosen on the development set and tested on fresh seeds.

## V5 / H15 — the swap move only in QI-DMO's greedy phases (`results/h15_tune/`, `results/h15_selection.json`, `results/h15_test/`, `results/h15_scale/`, `results/h15_analysis.md`)

**Origin.** H14's post-hoc explanation: a worsening swap is harmless where a candidate is kept only if it improves,
and harmful in QI-DMO's next-position phase, which keeps every candidate. `run_qidmo(..., exchange_phases="greedy")`
applies the move only in the alpha-group and scout phases. H15 was pre-registered in plan §33 with H5's protocol:
* tune phases × p_x on the 4 pilot instances (360 runs);
* freeze the choice;
* test once on **fresh instance seeds 801–810** (480 runs), plus the scaling problems (50 runs).

**Selection (development set, selection bias applies).** Phases = greedy, p_x = 0.1 (mean rank 3.45 of 8). All 8
configurations had a lower dev-set mean gap2 than QI-DMO (7.43 %): 5.64–7.39 %.

Mean gap2 (%) on the 80 fresh problems: QI-DMO 6.89, **greedy p_x = 0.1: 6.08**, H14 configuration 8.78.

**What happened?**
* **P1 fails narrowly.** Greedy p_x = 0.1 − QI-DMO = −0.81 pp [−1.43, −0.25]: the mean is better and the CI excludes 0.
  It is better on 47 of 80 problems, but the pre-registered Wilcoxon test gives p = 0.067.
* **P2 holds.** No family is significantly worse. The largest gains are on n300 m30 uniform (−3.57 pp, 9/10, Holm
  p = 0.11) and n100 m20 lognormal low (−2.72 pp, 8/10).
* **The phase explanation holds.** Greedy p_x = 0.1 beats the H14 configuration on 71 of 80 problems (−2.70 pp,
  p < 1e-4), and the H14 configuration is again worse than QI-DMO (65/80 worse) on these fresh seeds.
* **Mechanism.** 6.7 % of candidates carry a swap, and 42 % of those improve their parent. End purity is 0.93 vs 0.94,
  improving swaps left fall 401 → 365, and the last global-best improvement comes later (80 % → 84 % of the budget).
* **P3 (scaling, descriptive).** Better on average at every size: −9.0 s at 500 tasks … −33.1 s at 5000. Not
  significant after Holm (p 0.13–0.24). The H14 configuration's gains there are much larger (−13.6 … −204.0 s).

**Why?** Far from convergence (large problems), almost any swap on the critical VM helps, so a high swap rate in every
phase pays. Near convergence (30–300 tasks), a swap is often worse and must be filtered by greedy acceptance; then only
a low rate is safe, and its gain is small.

**Decision (pre-registered rule).** REJECT. QI-DMO keeps no swap move by default. The standalone QI-DMO notebook shows
both versions with their measured results; these negative and inconclusive outcomes are reported as they are.
Untested: making the next-position phase greedy (`greedy_next=True`) together with the move.

## Standalone QI-DMO and QI-MRFO notebooks (supervisor request; `notebooks/colab/QI_DMO_Colab.ipynb`, `notebooks/colab/QI_MRFO_Colab.ipynb`, `results/notebook_runs/`)

**What happened?** `notebooks/build/build_algorithm_notebooks.py` builds one notebook per algorithm. Each holds only
the code that algorithm needs, copied verbatim from `src/`, and saves every run, table, figure and a summary to
Google Drive.
* **Part 1:** the algorithm on its own: 7 benchmark problems × 30 runs and 500–5 000 tasks × 10 runs.
* **Part 2:** how it was improved, version by version, on the benchmark, on 80 unseen problems (QI-DMO: the H15 test
  set; QI-MRFO: the H5 test set) and on the large problems.
* **Part 3 (QI-MRFO only):** the changing-cloud improvements (H6–H13) step by step, at the migration price λ = 0.2.

**Evidence.**
* **Full mode, executed end to end** with `jupyter nbconvert` (4 processes): no errors. The executed copies and every
  file they wrote are in `results/notebook_runs/`. The container restarted twice during the runs; the notebooks
  resumed from their saved runs. The executed copies come from a last pass on the final notebook text, which read
  every run back and recomputed the tables and figures.
* **Runs vs the committed records.** Every run with a committed counterpart is bit-identical:
  * **QI-DMO:** 1 100 of 1 100 runs (benchmark vs `baseline_full.csv`, unseen vs `h15_test`, large vs `scale_tasks`,
    `h14_scale` and `h15_scale`). 580 runs are new: the two swap versions on the benchmark, and DMO on the unseen
    problems.
  * **QI-MRFO:** 1 220 runs, 1 340 of 1 340 values (benchmark, unseen vs `h5_test`, large vs `scale_tasks`, and Part 3
    steps 5–6 vs `h13_event_gamma`, cost gap and migrations). 820 runs are new: the two swap versions on the
    benchmark, the Max-Min start on the unseen problems, and Part 3 steps 1–4.
* **Quick mode is a subset of full mode.** In a clean quick run (2 processes, 2.8 GHz Xeon), all 76 QI-DMO runs and
  all 100 QI-MRFO runs (24 of them changing-cloud runs) were bit-identical to the same runs in full mode.
* **Run time, measured here.** The sum of all run times is 3.25 h for QI-DMO (1 680 runs) and 4.35 h for QI-MRFO
  (2 040 runs). Quick mode end to end, 2 processes on a 2.8 GHz Xeon, nothing else running: QI-DMO 3.6 min,
  QI-MRFO 5.2 min. Run times on Colab are UNMEASURED; the notebooks' ranges are estimates from these.

**What the new runs show** (full mode, the notebooks' own runs):
* **QI-DMO.** QI-DMO beats DMO on 76 of the 80 unseen problems (Wilcoxon p = 1.3e-14). DMO wins 4, all of the type
  n100 m20 lognormal low (seeds 801, 803, 806 and 810). On the benchmark, the improving-phase swap is better on only 2
  of 7 problems (the two bimodal ones, by about 2 s) and slightly worse on 5.
* **QI-MRFO.** MRFO → QI-MRFO is better on 78 of 80 unseen problems (p = 9.1e-15). The Max-Min start is better on 65
  and worse on 13 (p = 9.4e-10), and slightly worse on the 30-task benchmark problem.
* **QI-MRFO Part 3** (λ = 0.2, 6 scenarios × 10 runs). Cost gap over the six steps: 23.18 → 10.33 → 7.43 → 9.23 →
  5.83 → 5.57 %.
  * **Step 3 (swap move) vs step 2:** better in only 31 of 60 runs (p = 0.051). It moves more tasks (10.2 → 28.3 per
    change). It helps after a VM addition (18.43 → 11.16 %), after speed drift and on 200 tasks, and hurts after
    churn, VM failures and mixed events. H6 measured the swap move without a migration price (60 of 60 better), so
    the notebook text now says so.
  * **Step 4 vs step 3:** worse on average (9.23 vs 7.43 %), because of the VM addition (11.16 → 24.25 %). This is
    the H6b mechanism; step 5 removes it.
  * **Steps 5 and 6** reproduce H13 exactly.
