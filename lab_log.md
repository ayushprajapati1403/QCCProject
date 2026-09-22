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
