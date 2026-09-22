# Quantum-Inspired Manta Ray Foraging Optimization for Cloud Task Scheduling
## An implementation-first research investigation (report, 22 September 2026)

**Scope.** Quantum-*inspired* classical optimization for cloud computing. Every experiment in this report ran on an ordinary laptop CPU (Windows 11, Python 3.13 / NumPy 2.3 for the pilots; a Docker image with Python 3.12 for the notebook). No quantum hardware, quantum circuits, QPU or annealer was used or is required.

**Rules.** Every number labelled *measured* was produced by the code in this folder (`observe_v0.py … observe_v3.py`, `observe_dyn*.py`, the notebook). Anything not measured is labelled UNMEASURED; illustrative numbers are labelled HYPOTHETICAL. All literature statements come from pages opened by live web search on 22 September 2026 (see `literature/`), never from memory.

**Deliverables.** `quantum_inspired_cloud_scheduler.ipynb` (18 sections, runs top-to-bottom), this report, `README.md`, `lab_log.md`, `phd_research_proposal.md`, `literature/*.md`, `results/`.

---

## 1. Selected algorithm

**MRFO (Manta Ray Foraging Optimization; Zhao, Zhang & Wang, 2020)** is the primary host of the quantum-inspired mechanism (QI-MRFO). **DMO (Dwarf Mongoose Optimization; Agushaka, Ezugwu & Abualigah, 2022)** is implemented as a second host (QI-DMO) because the mechanism is host-agnostic and DMO is the algorithm of the candidate's prior project; showing the transfer is part of the evidence. PSO was not selected.

## 2. Why it was selected (Phase 3)

The choice was made *after* the literature mapping and *after* the first pilot, on the criteria requested:

| Criterion | PSO | DMO | MRFO |
|---|---|---|---|
| Weakness of the original optimizer on cloud scheduling (measured, §17–18) | degrades with n (gap 21 % at n=100) | random-search level for n ≥ 50 (gap 76 %) | random-search level for n ≥ 50 (gap 98 %); collapses diversity |
| Literature gap for a quantum-inspired version | saturated: ≥ 20 QPSO/QI-PSO papers incl. cloud (`literature/qpso_literature_map.md`) | 5 quantum-labelled papers, all binary Q-bit feature selection or a relabelled Gaussian jump; none for scheduling | 6 quantum-labelled items, all continuous, none discrete, none for scheduling; the two MRFO surveys each index a single one |
| Suitability for the amplitude representation | fine, but already done (Balicki 2022, Jeong 2010) | natural mapping (babysitter reset = full decoherence) | natural mapping (best-centred moves become perturbations of the best basis state; somersault = reflection about it) |
| Cloud-scheduling relevance | high | growing (Abraham/Ngadi line 2025–26) | ~10 papers, mostly regional; one 2025 study shows hybrid MRFO losing to PSO-GA |
| Discrete compatibility | needs transfer functions | needs transfer functions | needs transfer functions (Yıldızdan 2023; Bouaita 2026) |
| Implementation feasibility | done | done (MATLAB/MEALPY-faithful) | done (MEALPY-faithful) |
| Measured improvement from the mechanism (pilot) | UNMEASURED (not implemented) | 76 % → 3.9 % gap at n=100; 1.4 % with a greedy next-position step | 98 % → 1.0 % gap at n=100; ties/beats the discrete GA on all four pilot instances |
| Identity preservation | — | preserved, but the original's unconditional "next position" move is a handicap | preserved; greedy replacement in every phase makes the mechanism most effective |

MRFO is primary because the measured effect is largest and cleanest and the literature gap is documented by a 2025 survey; DMO is secondary because the candidate's background is DMO and because the transfer result strengthens the science (the mechanism is representational, not host-specific). PSO was excluded because quantum-inspired PSO is the most crowded corner of the literature and a Q-bit PSO for VM placement already exists (Balicki, Entropy 2022).

## 3. Existing quantum-inspired versions (Phase 1)

Full tables with URLs: `literature/qpso_literature_map.md` (23 papers), `literature/dmo_literature_map.md` (5 quantum DMO papers + 9 cloud DMO papers), `literature/mrfo_literature_map.md` (6 quantum MRFO items + 12 cloud MRFO papers), `literature/qi_cloud_and_classical_equivalents.md` (19 quantum-inspired cloud schedulers + the mechanism-without-the-word-quantum analysis). Highlights:

* **QPSO** (Sun, Feng & Xu 2004; Sun et al. 2011/2012): $x = p \pm \alpha |mbest - x| \ln(1/u)$. Its authors state it is a bare-bones PSO sampling a double-exponential distribution; Mikki & Kishk (2006) show the delta well *is* a Laplace kernel. Cloud uses (Yu et al. 2021 HWQPSO; Wang et al. 2023 DE3C; Elsedimy 2025; Aminu 2026) round the continuous position to a VM index and evaluate static batches; the Naik/Bey group replaces the sampler by Q-bits + hashing (an EDA). No verified QPSO cloud paper tests dynamic workloads.
* **Quantum DMO**: DMOAQ (Abd Elaziz et al., Mathematics 2022: binary Q-bit, Han–Kim rotation table, threshold measurement, DMO operators on the angle vector); three papers copy its equations into deep-learning pipelines (Almutairi 2023; Deepa 2024; Sivakumaran 2025); EDMO (arXiv 2511.09020, Nov 2025) relabels a fitness-scaled Gaussian jump as "quantum tunnelling". None is multi-valued, none is for scheduling.
* **Quantum MRFO**: Gupta & Kumar (IJCSE 2024, Bloch-phase encoding, 20 continuous benchmarks); Turgut et al. (Sci Rep 2025, QPSO delta-well move on the worst third of the population); Wang et al. (Biomimetics 2023, Bloch-coded initialization only); QFLN-QIMRO (J. Supercomputing, 20 Sep 2026, quantum-behaved MRFO for 6G MEC orchestration; equations paywalled); two unreadable items (Ramadan 2021; CRC 2022 chapter). None discrete, none for cloud task/workflow/VM scheduling, none with code.
* **Quantum-inspired cloud schedulers on other hosts** (2021–2026): QIGA/QIEA with Q-bit chromosomes and rotation gates (Hussain 2022/2024; Lilhore 2025 QHRMOF; Hammouda 2026 FOG-QIEA; Chauhan & Alam 2024; Galavani 2025), Q-bit PSO for VM placement (Balicki 2022), Q-bit DE (Priyanka 2024), RQWOA (Divya 2026), and two "quantum" heuristics with no probabilistic structure at all (QBDS 2026, QIARM 2025). A 2026 arXiv benchmark of QUBO/quantum-inspired HPC workflow mapping (Sharma et al.) finds classical solvers preferable.

## 4. Literature comparison (the quantum-innovation map, condensed)

| Family | Quantum mechanism | Classical equivalent | Representation for scheduling | Genuinely different mechanism? | What it does NOT solve |
|---|---|---|---|---|---|
| QPSO (delta well) | wave-function sampling around an attractor | Laplace mutation with population-spread scale (authors' own statement) | continuous + rounding | No (kernel choice) | attractor collapse; lossy discretisation; dynamics untested |
| Q-bit QIEA/QIGA/QI-PSO/QI-DE | qubit amplitudes + rotation gate + measurement | PBIL/cGA/UMDA with a self-damping learning rate (Platel, Schliebs & Kasabov 2007/2009) | binary Q-bits, hashing/random keys | No (univariate EDA) | needs a decoder; no theory; no dynamics |
| "Quantum tunnelling" variants | jump probability from a pseudo-potential | Cauchy/Lévy mutation (Yao 1999; Lee & Yao 2004) | continuous | No | discrete problems |
| Quantum-behaved MRFO/DMO (Turgut 2025; QFLN-QIMRO 2026; EDMO 2025) | QPSO move or tunnelling jump inside the host | Laplace/Gaussian jumps | continuous | No | scheduling; discrete encodings |
| Bloch-phase MRFO (Gupta & Kumar 2024) | phase-angle encoding, three real points per individual | reparameterised continuous search | continuous | Partial (representation) | discrete; applications |
| Simulated quantum annealing / quantum walks (physics literature) | transverse-field replica coupling; ballistic spreading | parallel tempering; random walk | binary/QUBO | Partial (different classical dynamics) | not used by any cloud paper; QUBO mapping loses feasibility beyond ~15 tasks (Sharma 2026) |
| **This work** | m-ary amplitude registers per task, Born measurement, basis-state attractors, depolarising channel, swarm difference-vector updates | probability-vector swarm with a mutation floor (classical twin implemented and tested) | native task→VM registers, no decoder | Partial: the *representation* is what matters; squaring and sign are measurably irrelevant (§19) | static heavy-tailed batches (Max-Min wins); very severe change |

## 5. Existing classical equivalents (Phase 1B, mandatory)

For every quantum mechanism the same idea was searched without the word "quantum" (`literature/qi_cloud_and_classical_equivalents.md`, Part 2):

| Quantum mechanism | Classical equivalent | Who showed it | Mathematical difference |
|---|---|---|---|
| Q-bit rotation gate | PBIL probability-vector update, $p' = \sin^2(\theta+\Delta\theta) \approx p + 2\sqrt{p(1-p)}\,\Delta\theta$ | Platel, Schliebs & Kasabov 2007, 2009 ("QEA is an EDA"); da Silva & Schirru 2014 ("quantum PBIL") | none for sampling; a self-damping learning-rate schedule |
| Tunnelling | Cauchy / Lévy mutation, restarts | Yao, Liu & Lin 1999; Lee & Yao 2004 | none in metaheuristics; partial for path-integral SQA (Santoro 2002; Isakov 2016) |
| Quantum walk | random walk; classical wave simulation | Knight, Roldán & Sipe 2003; Xue & Sanders 2013 | ballistic vs diffusive spreading is a classical interference effect; decoherence restores the random walk |
| Decoherence / depolarising channel | Baluja's mutation shift $p \leftarrow (1-\lambda)p + \lambda\,\text{rand}$; Yang & Yao's central-vector mixing; Cobb's hypermutation; Branke's memory | Baluja 1994; Cobb 1990; Branke 1999; Yang & Yao 2005/2008 | none on product states (diagonal of $\rho$ is all that sampling sees) |
| Superposition + measurement | sampling a product distribution: UMDA/PBIL/cGA; EDAs already used for cloud (Chen 2014) and fog (Wu, Li, Wang & Zomaya 2018) | — | none |
| Born rule | squared reparameterisation of a probability vector | Glasser et al. 2019 (separations only for entangled Born machines) | none for product states |
| Purity floor | cGA margins $[1/n, 1-1/n]$; Han & Kim's Hε gate | Doerr & Zheng 2020; Han & Kim 2004 | none |

Conclusion of Phase 1B: in the cloud-scheduling corpus every quantum-inspired operator is a relabelled EDA/PBIL, Lévy mutation or mutation shift. The genuinely distinct physics-derived algorithms (SQA, quantum walks, entangled Born machines) are not used by any cloud paper — and our own experiments (§19) confirm the same verdict for our mechanism: the useful content is representational.

## 6. The weakness we target (OBSERVATION)

Measured in the V0 pilot (`observe_v0.py`, 5 seeds, 20 000 evaluations, floor encoding $a_i = \lfloor x_i \rfloor$):

| Instance | LB | Max-Min | PSO | DMO | MRFO | GA (discrete) | Random |
|---|---|---|---|---|---|---|---|
| n=30, m=5, uniform tasks, heterogeneous VMs | 44.53 | 45.46 | 45.71 (2.7 %) | 45.73 (2.7 %) | 47.64 (7.0 %) | 44.87 (0.8 %) | 47.03 (5.6 %) |
| n=50, m=10, bimodal (heavy-tailed) tasks | 25.11 | 27.06 | 28.75 (14.5 %) | 36.50 (45.4 %) | 35.45 (41.2 %) | 28.74 (14.5 %) | 34.41 (37.1 %) |
| n=100, m=10, uniform | 47.06 | 47.45 | 56.86 (20.8 %) | 82.62 (75.6 %) | 93.39 (98.5 %) | 47.72 (1.4 %) | 90.22 (91.7 %) |
| n=50, m=10, homogeneous VMs | 28.39 | 28.98 | 30.47 (7.3 %) | 33.04 (16.4 %) | 33.26 (17.2 %) | 29.37 (3.5 %) | 32.90 (15.9 %) |

(makespan in seconds; brackets = gap to the lower bound.) The instrumentation shows why: at n=100 a DMO candidate changes on average **48.9** task assignments, an MRFO candidate **43.9**, a PSO candidate 13.8, a GA child 5.4; only 1.4 % (MRFO) and 2.8 % (PSO) of candidates improve; MRFO's population diversity (mean pairwise Hamming distance / n) collapses to 0.02 while 15 % of its evaluations are spent on candidates identical to the parent. The landscape probe shows that improving moves on this landscape change 1–5 tasks (90–100 % of 1-move local optima are improvable by a 2-task swap). **The floor encoding gives the swarm no controllable notion of move size**: steps are proportional to inter-individual distances in $[0,m)^n$ and become random re-draws after rounding. This is not a parameter problem (PSO shares the trend) and not a metaphor problem (the same algorithms are competent on continuous functions); it is the representation.

## 7. Our quantum-inspired mechanism (MECHANISM)

1. **Representation.** Individual $i$ holds $\Psi_i \in \mathbb{R}^{n \times m}$: one *m*-level real amplitude register (a "rebit" generalised to $m$ outcomes) per task, rows on the unit sphere $\sum_j \Psi_i[t,j]^2 = 1$. Initial state: the uniform superposition $m^{-1/2}\mathbf{1}$.
2. **Measurement (Born rule).** $\Pr(a_t = j) = \Psi[t,j]^2$, tasks sampled independently; one measurement = one evaluation; a measured schedule $b$ is encoded back as the basis state $E(b)$ (one-hot rows).
3. **Host dynamics unchanged.** Every MRFO (or DMO) equation is applied to the amplitude matrices, followed by the projection $\Pi$ (row renormalisation). Attractors are basis states: $E(b_{best})$ for MRFO, $E(b_\alpha)$ for DMO ("the alpha peeps its measured food position").
4. **Decoherence.** Each candidate register passes through the depolarising channel $\mathcal{D}_\gamma(p) = (1-\gamma)p + \gamma/m$ (amplitudes $\leftarrow \operatorname{sign}(\Psi)\sqrt{\mathcal{D}_\gamma(\Psi^2)}$), $\gamma = c/n$. It bounds purity away from 1 and therefore guarantees a floor on the expected number of reassigned tasks per measurement. With $\gamma = 1$ it is the classical random reset (DMO's babysitter exchange); intermediate $\gamma$ is *controlled forgetting*.
5. **Purity as the move-size dial.** $\pi_t = \sum_j p_{tj}^2$; the expected number of tasks that differ between two measurements of the same register set is $n - \sum_t \pi_t$. The host's own dynamics move purity continuously: attraction to a basis state raises it (exploitation), mixing with a diffuse register or a random basis state lowers it (exploration).
6. **Structural rules for dynamic environments.** VM removal = delete the column and renormalise (a projective measurement onto the surviving VMs); VM addition = a new column with the uniform share $1/(m+1)$; a replaced task = its register reset to the uniform superposition.

## 8. Original equations

**MRFO** ($r, r_1, r_2, r_3 \sim U(0,1)$; $t$ = iteration, $T$ = iteration budget; greedy replacement after each phase; $i=1$ uses $x_{best}$ as predecessor):
* Chain: $x_i^{t+1} = x_i^t + r(x_{i-1}^t - x_i^t) + \alpha(x_{best} - x_i^t)$, $\alpha = 2r\sqrt{|\log r|}$.
* Cyclone: $x_i^{t+1} = x_{best} + r(x_{i-1}^t - x_i^t) + \beta(x_{best} - x_i^t)$, $\beta = 2e^{r_1(T-t+1)/T}\sin(2\pi r_1)$; while $t/T < \mathrm{rand}$, a uniformly random $x_{rand}$ replaces $x_{best}$.
* Somersault: $x_i^{t+1} = x_i^t + S(r_2 x_{best} - r_3 x_i^t)$, $S = 2$.

**DMO** (MATLAB/MEALPY form, which is what the field actually runs; the paper-vs-code discrepancies are documented in `literature/dmo_literature_map.md`): alpha selection by roulette on $e^{-f_i/\bar f}$; alpha-group candidate $X_\alpha + \varphi \odot (X_\alpha - X_k)$, $\varphi \sim \tfrac{peep}{2}U(-1,1)^n$; scout candidate $X_i + \varphi \odot (X_i - X_k)$ with sleeping mound $sm_i = (f_{cand} - f_i)/\max(f_{cand}, f_i)$; babysitter exchange (uniform re-initialisation of the first $B$ mongooses when $C_i \ge L = 0.6nB$); next position $X_i \mp CF\,\varphi\,r\,(X_i - sm_i)$, $CF = (1-t/T)^{2t/T}$, applied unconditionally.

Symbols: $x_i$ position of individual $i$ (one coordinate per task); $x_{best}$ best position; $r$-type factors are uniform random scalars; $\alpha, \beta, S, \varphi, CF$ are the step-size coefficients defined by the respective papers.

## 9. Modified equations (what changed and why)

Replace every position by a register matrix and every attractor by a basis state; wrap each update in $\mathcal{D}_\gamma \Pi[\cdot]$; measure the candidate to obtain the schedule that is evaluated:

* Chain: $\Psi_{cand} = \mathcal{D}_\gamma\Pi\big[\Psi_i + r(\Psi_{i-1} - \Psi_i) + \alpha(E(b_{best}) - \Psi_i)\big]$.
* Cyclone: $\Psi_{cand} = \mathcal{D}_\gamma\Pi\big[E(b_{best}) + r(\Psi_{i-1} - \Psi_i) + \beta(E(b_{best}) - \Psi_i)\big]$ (exploration: $E(b_{rand})$, the basis state of a uniformly random schedule).
* Somersault: $\Psi_{cand} = \mathcal{D}_\gamma\Pi\big[\Psi_i + S(r_2 E(b_{best}) - r_3\Psi_i)\big]$.
* Acceptance: measure $a_{cand} \sim \Psi_{cand}$; if $f(a_{cand}) < f_i$ adopt $(\Psi_{cand}, a_{cand}, f(a_{cand}))$.
* DMO: alpha group $\mathcal{D}_\gamma\Pi[E(b_\alpha) + \varphi \odot (E(b_\alpha) - \Psi_k)]$; scouts $\mathcal{D}_\gamma\Pi[\Psi_i + \varphi \odot (\Psi_i - \Psi_k)]$; babysitter exchange $\Psi_i \leftarrow \mathcal{D}_{\gamma_{reset}}(\Psi_i)$; next position $\mathcal{D}_\gamma\Pi[\Psi_i \mp CF\,\varphi\,r\,(\Psi_i - sm_i)]$; $\varphi$ drawn per task (per row).

What changed: (i) the state space ($[0,m)^n \to$ product of $n$ unit spheres in $\mathbb{R}^m$); (ii) attractors are collapsed schedules, not raw states; (iii) a projection and a noise channel after every update; (iv) schedules are sampled, not decoded. What did *not* change: the operators, the control flow, the number of evaluations per iteration, the greedy acceptance — the algorithm is still recognisably MRFO/DMO. Complexity: $O(nm)$ per candidate (update + measurement) instead of $O(n)$; memory $Pnm$ floats.

State-transition process: $(\Psi_i, b_i, f_i) \xrightarrow{\text{operator}} \tilde\Psi \xrightarrow{\Pi,\ \mathcal{D}_\gamma} \Psi_{cand} \xrightarrow{\text{measure}} a_{cand} \xrightarrow{f} f_{cand} \xrightarrow{\text{greedy}} (\Psi_i', b_i', f_i')$.

## 10. Why the mechanism is genuinely quantum-inspired

The three ingredients are the textbook objects of quantum measurement theory: a normalised amplitude vector per subsystem (a product state over $n$ subsystems), the Born rule that turns amplitudes into outcome probabilities by squaring, and the depolarising channel $\rho \to (1-\gamma)\rho + \gamma I/m$, the standard model of decoherence. Purity $\operatorname{Tr}\rho^2$ is the standard measure of how mixed a state is, and the observation that *purity controls the expected Hamming distance between two measurements* is the quantum-information reading of the move-size problem. Signed amplitudes admit cancellation when registers are mixed (interference). The mapping is complete and teachable, and it is *not* decoration: it produced a testable prediction (move size follows purity; a decoherence floor is needed; the optimal $\gamma$ is small) that the experiments confirmed. What we also report honestly is that the quantum-specific parts (squaring, sign) turned out to be measurably irrelevant (§19), which is exactly the kind of result Phase 1B predicts for product states.

## 11. Why this is NOT quantum computing

No joint state of $n$ qubits is ever formed (that would need $m^n$ amplitudes); the registers are independent, real, $m$-dimensional unit vectors updated by ordinary arithmetic; no unitary evolution, no entanglement, no interference across subsystems is simulated; "measurement" is `numpy` sampling. The whole optimizer is $O(Pnm)$ memory and runs in seconds on a laptop. Nothing here would run faster on a quantum computer, and nothing here requires one.

## 12. Scientific hypothesis (stated before the experiments, Phase 4/5)

* **Observation.** Floor-encoded DMO/MRFO change ~n/2 tasks per candidate and perform at random-search level for n ≥ 50 (§6).
* **Mechanism.** Amplitude registers + Born measurement + basis-state attractors + decoherence floor (§7).
* **Causal reasoning.** With registers, the number of tasks changed per candidate is $n - \sum_t \pi_t$, a continuous function of the state that the host's attraction/repulsion dynamics move; therefore the host's exploration–exploitation schedule (which is meaningless after rounding) becomes an effective move-size schedule on the assignment lattice.
* **H1 (encoding).** QI-X reaches lower makespans than X at equal evaluation budgets, with the gain increasing with n and m; QI-X approaches the discrete GA.
* **H2 (decoherence).** Without the channel the registers collapse (purity → 1) and evaluations are wasted re-measuring the same schedule; a weak channel ($c \approx 0.25$–1) removes the waste and improves results; strong decoherence ($c \ge 2$) degrades monotonically (dose–response).
* **H3 (classical twin).** If the benefit is representational, the linear-probability twin captures it; if the Born rule matters, the twin is worse.
* **H4 (dynamic).** After a workload change, carrying the register state beats a restart; a decoherence shock $\gamma_{shock} \in (0,1)$ ("controlled forgetting") beats both naive continuation and restart, and the optimal $\gamma_{shock}$ grows with change severity.
* **Falsification.** H1 fails if QI-X does not beat X on n ≥ 50 or is dominated by the GA by a wide margin; H2 fails if $c = 0$ is best or if performance is flat in $c$; H3 is decided either way; H4 fails if no $\gamma_{shock} \in (0,1)$ beats plain continuation.
* **Anticipated effect size (HYPOTHETICAL, written before the run):** 20–40 % lower makespan than classical DMO/MRFO at n = 100 and a gap to the GA below 5 %; 5–15 % better post-change quality for the shock strategy on moderate churn.

## 13. Expected behaviour BEFORE the experiments

Move size decays smoothly from ~n/2 to a few tasks as purity rises; improving-candidate fraction rises from ~1 % to ≥ 10 %; diversity collapses *unless* the channel is on; QI-MRFO and QI-DMO converge to within a few percent of the lower bound; the linear twin close behind; the register attractor variant (using the alpha's superposition instead of its measured schedule) expected to be worse because nothing concentrates the registers.

## 14. What result would support the hypothesis

Consistent improvement over the classical host on all instances with the gain growing with n; a U-shaped or monotone dose–response in $c$ with an interior optimum; wasted-evaluation fraction dropping to ~0 with the channel; and, for H4, a strategy with $0 < \gamma_{shock} < 1$ dominating both restart and continuation with the optimum shifting with severity.

## 15. What result would falsify it

No gain at n ≥ 50; a flat response in $c$; the twin performing differently in the direction that contradicts H3; no interior optimum in $\gamma_{shock}$; or the discrete GA / Max-Min dominating everywhere (which would make the contribution "fixing a broken baseline" rather than a competitive scheduler).

---

## 16. First implementation (V1 → V3, what exists and how it was built)

All code is pure NumPy/SciPy and lives in three modules that the notebook embeds verbatim (`build_notebook.py` slices them by section markers, so notebook and modules cannot drift):

* `qi_core.py` — instance model (`CloudInstance`, `make_instance`), objective with evaluation counting (`Objective`), the floor decoder, instrumentation (`Tracker`: best-so-far, diversity, per-candidate move size, wasted/neutral/improving/worse classification, global-best improvements), Min-Min/Max-Min heuristics, a 1-move hill climber for landscape probes, and the classical optimizers PSO, DMO (faithful to the authors' MATLAB code as ported by MEALPY, including the unconditional next-position move; `greedy_next=True` gives the MEALPY-developed variant), MRFO (faithful to MEALPY's `OriginalMRFO`), a discrete GA and random search. Every optimizer accepts and returns a `state` for warm-started re-optimisation.
* `qi_quantum.py` — the mechanism (`born_probs`, `measure`, `basis_state`, `project`, `purity`, `depolarise`, structural-change operators `remove_vm_state`, `add_vm_state`, `add_tasks_state`, `shock_state`) and the two hosts `run_qimrfo`, `run_qidmo` with `mode ∈ {born_signed, born_abs, linear}`, `decoherence` ($\gamma$), `attractor ∈ {basis, register}`, `gamma_reset`, `greedy_next`.
* `qi_dynamic.py` — dynamic environments (task churn, VM failure, VM addition, speed drift) and the strategies restart / continue / continue_struct / shock / hypermutation.

Version history (each version has one evidence-driven change; see `lab_log.md`):

| Version | Change | Reason (evidence) |
|---|---|---|
| V0 | classical PSO/DMO/MRFO/GA with floor encoding + instrumentation | OBSERVE |
| V1 | amplitude registers, Born measurement, basis-state attractor, $\gamma_{reset}=1$ | move size uncontrollable (V0) |
| V2 | per-candidate depolarising channel $\gamma = c/n$; transfer to MRFO | 26–76 % wasted evaluations after collapse (V1) |
| V3 | ablations: greedy next-position for DMO, register attractor, $c$ sweep for MRFO, linear twin, unsigned, population size | QI-DMO < QI-MRFO (V2): is it the host's unconditional move?; is the Born rule doing anything? |
| Dyn | warm-start harness, structural rules, shock, severity sweep | H4 |

The notebook's Section 10 runs 18 validation tests (objective vs brute force, decoder bounds, chi-square test that measurement follows the Born rule, channel normalisation and monotone purity, strict evaluation-budget accounting for every optimizer, determinism, $\gamma = 1$ reduces to uniform sampling, valid schedules in all modes). One bug was found by these tests and fixed: DMO/QI-DMO exceeded the budget by the babysitter re-initialisation evaluations (about 0.1 % in the pilots; the pilot numbers below are therefore, for DMO/QI-DMO, a few evaluations above budget — immaterial, but recorded).

## 17. Pilot methodology (Phase 9)

* Instances (generator seed 1): (n=30, m=5, uniform tasks U(1000, 10000) MI, heterogeneous VMs 250–2000 MIPS), (50, 10, bimodal heavy-tailed tasks, heterogeneous), (100, 10, uniform, heterogeneous), (50, 10, uniform, homogeneous VMs). Same instance for every algorithm and seed.
* Budget: 20 000 objective evaluations per run for every algorithm (each measurement = one evaluation); population 30; 5 run seeds (0–4); objective = makespan; results reported as mean makespan and gap to the Q||Cmax lower bound; Max-Min and Min-Min as heuristic references; random search as the floor.
* Controlled initial conditions: all population methods start from the uniform distribution over schedules (uniform positions / uniform superposition / uniform integers).
* Mechanism metrics: per-candidate move size (tasks changed vs parent), wasted/neutral/improving/worse fractions, global-best improvements per 1 000 evaluations, population diversity (mean pairwise Hamming/n), register purity, runtime.
* Notebook `full` mode repeats everything with 30 seeds and adds held-out instance shapes (n=200 m=20; lognormal tasks with low heterogeneity; bimodal on homogeneous VMs).

## 18. Experimental results (measured; pilot = 5 seeds, 20 000 evaluations)

**V1 — the encoding (H1).** Gap to LB, mean over seeds:

| Instance | DMO | QI-DMO (V1, no channel) | P-DMO linear twin (V1) | GA |
|---|---|---|---|---|
| n30 m5 | 2.7 % | 2.0 % | 2.1 % | 0.8 % |
| n50 m10 bimodal | 45.4 % | 21.6 % | 20.5 % | 14.5 % |
| n100 m10 | 75.6 % | 4.9 % | 4.0 % | 1.4 % |
| n50 m10 homogeneous | 16.4 % | 8.3 % | 8.3 % | 3.5 % |

At n=100 the mean move size fell from 48.9 to 11.3 tasks and the population reached 51.9 s at 25 % of the budget (DMO: 101.9 s). The gain grows with n as predicted. But the Born-rule registers collapsed (end purity 0.996–0.999, end diversity 0.001–0.07) and 26–76 % of evaluations re-measured the parent's schedule.

**V2 — decoherence dose–response (H2) and transfer (H1 on MRFO).** Gap to LB for QI-DMO with $\gamma = c/n$:

| Instance | c=0 | c=0.25 | c=0.5 | c=1 | c=2 | wasted (c=0 → c≥0.25) |
|---|---|---|---|---|---|---|
| n30 m5 | 2.0 % | **1.6 %** | 2.1 % | 2.1 % | 2.7 % | 76 % → 1 % |
| n50 bimodal | 21.6 % | **15.9 %** | 15.9 % | 18.5 % | 21.3 % | 14 % → 0 % |
| n100 m10 | 4.9 % | **3.9 %** | 5.5 % | 8.1 % | 11.2 % | 26 % → 0 % |
| n50 homog | 8.3 % | **6.6 %** | 10.4 % | 12.6 % | 14.8 % | 38 % → 0 % |

QI-MRFO (mean makespan, gap in brackets):

| Instance | MRFO | QI-MRFO c=0 | QI-MRFO c=0.5 | QI-MRFO c=1 | GA | Max-Min |
|---|---|---|---|---|---|---|
| n30 m5 | 47.64 (7.0 %) | 45.70 (2.6 %) | 45.08 (1.2 %) | 44.93 (0.9 %) | 44.87 (0.8 %) | 45.46 |
| n50 bimodal | 35.45 (41.2 %) | 30.18 (20.2 %) | 28.10 (11.9 %) | 27.54 (9.7 %) | 28.74 (14.5 %) | 27.06 |
| n100 m10 | 93.39 (98.5 %) | 53.93 (14.6 %) | 47.54 (1.0 %) | 47.51 (1.0 %) | 47.72 (1.4 %) | 47.45 |
| n50 homog | 33.26 (17.2 %) | 30.60 (7.8 %) | 29.38 (3.5 %) | 29.22 (2.9 %) | 29.37 (3.5 %) | 28.98 |

Effect sizes actually observed versus the HYPOTHETICAL prediction (20–40 % lower makespan at n=100): measured **49 %** lower makespan than MRFO (93.4 → 47.5) and **41 %** lower than DMO (82.6 → 48.9); the gap to the GA is not "below 5 %" but zero or negative (QI-MRFO ties or beats the GA on all four instances). The prediction was too conservative on the first part and right on the second.

**V3 — mechanism tests.** (a) DMO's unconditional next-position move explains QI-DMO's deficit: with a greedy version QI-DMO reaches 1.1 / 12.0 / 1.4 / 3.2 %, on par with QI-MRFO (classical DMO with the same change: 2.3 / 17.9 / 30.7 / 12.4 %). (b) Register attractor (alpha's superposition instead of its measured schedule): 7.1 / 34.2 / 87.8 / 14.2 % — purity stays at 0.1–0.2 and 24–90 tasks change per candidate: the search never concentrates. (c) Linear twin of QI-MRFO: 0.9 / 9.7 / — / 3.2 % versus Born 0.9 / 9.7 / 1.0 / 2.9 %: identical within seed noise. (d) Unsigned amplitudes: 0.9 % on n30 (= signed). (e) Population size 15/30/60: differences below one percentage point. (f) Runtime: QI-MRFO about 14 s versus MRFO about 3 s per 20 000 evaluations at n=100, m=10 in pure Python/NumPy (the objective is cheap; in a CloudSim-class simulator evaluation cost dominates and the overhead disappears).

**What the mechanism changed (Phase 10).** It changed one measurable search property, the distribution of move sizes (from about n/2 tasks per candidate to a purity-controlled few), which raised the improving-candidate fraction and the number of global-best improvements per 1 000 evaluations (n=100: 2.7 for QI-MRFO c=1 while MRFO improves on 1.4 % of candidates), and the decoherence channel changed a second property, the floor of that distribution (wasted fraction from 63 % to 5–17 %). Diversity is *not* what it improved: QI-MRFO's end diversity is about 0.001 (the population sits on the best schedule and explores by measurement noise), lower than MRFO's 0.02 and the GA's 0.09.

## 19. Ablation (Phase 11): did the quantum-inspired component cause the effect?

| Ladder (n100 m10 unless noted) | gap to LB | verdict |
|---|---|---|
| MRFO (classical, floor encoding) | 98.5 % | baseline failure |
| + registers, Born measurement, basis-state attractor (QI-MRFO c=0) | 14.6 % | the representation causes most of the gain |
| + depolarising floor c=1 (QI-MRFO) | 1.0 % | the floor causes the rest |
| Born rule replaced by linear mixing (P-MRFO twin, c=0.5; n50 bimodal / n30 / homog) | 9.7 / 0.9 / 3.2 % versus 9.7–11.9 / 0.9–1.2 / 2.9–3.5 % | **no measurable effect of the Born rule** |
| signed → unsigned amplitudes (n30) | 0.9 % versus 0.9 % | **no measurable effect of interference** |
| basis-state attractor → superposition attractor (QI-DMO) | 87.8 % | collapse-conditioned attraction is necessary |
| DMO's unconditional move → greedy (QI-DMO) | 1.4 % (from 3.9 %) | host quirk, not mechanism |

Answer: the effect is caused by (i) the superposition-and-measurement representation and (ii) the decoherence floor; the specifically quantum parts (amplitude squaring, sign/interference) contribute nothing measurable at this sample size. The mechanism is best described as a *measurement-based register representation with a purity-calibrated noise floor*; "quantum-inspired" is an accurate description of where it came from, not of why it works.

## 20. Failure analysis (Phase 12, adversarial; measured where stated)

* **Heavy-tailed static batches:** on the bimodal instance the Max-Min list heuristic (27.06) beats every metaheuristic (best QI-MRFO 27.54, GA 28.74). The landscape probe explains it: 43 % neutral 1-move neighbours and 38 % median barriers; a list heuristic that places big tasks first is structurally right. A population method must be seeded with Max-Min or given an objective a list heuristic cannot optimise (energy/cost/deadlines) to be worth its cost there.
* **Dynamic workloads (H4, the "big-result" hypothesis):** carrying the register state beats a restart on all four change types (AUC 2–4× lower) and beats the GA's carried population on drift, VM failure and VM addition; but the decoherence shock does **not** beat plain continuation at any churn severity between 10 % and 80 % (`lab_log.md`, severity table), and GA hypermutation — the classical analogue — is worse than GA continuation everywhere. At 80 % churn restart and continuation are indistinguishable. H4's strong form is falsified for uniform shocks; the boundary is measured.
* **Population collapse:** even with the floor, QI-MRFO's end diversity is about 0.001 and 5–47 % of candidates are wasted for small c; the search relies on measurement noise around one schedule. This is a documented weakness, not hidden by the good makespans.
* **Overhead:** about 4–5× wall time and $m$× memory relative to the floor encoding in pure Python (measured); irrelevant in a simulator, relevant for embedded/edge use.
* **Adversarial cases from the notebook (fast mode: 3 seeds, 10 000 evaluations; `results/failure_cases_fast.csv`; 30-seed update in §26).**
  * *17a tiny (n=10, m=3):* every method within 0.1–0.5 % of the lower bound, random search included (0.15 %); Max-Min is the worst (1.8 %). The mechanism is unnecessary here, as predicted.
  * *17b two VMs (n=40, m=2):* all population methods identical (≤ 0.02 % gap); the floor encoding is lossless when $m=2$, so the representational advantage vanishes, as predicted.
  * *17c identical tasks on homogeneous VMs (n=40, m=8; optimum = 5 tasks per VM):* GA, Max-Min and QI-DMO reach the optimum (25.0) in every seed; **QI-MRFO reaches it in one seed of three** (28.3 ± 2.9), MRFO and DMO never (30.0). This landscape is a pure plateau: an improvement requires moving one task from a 6-task VM to a 4-task VM and *every* other move is neutral. QI-MRFO's strict greedy acceptance rejects neutral moves, and its collapsed population cannot drift; QI-DMO's unconditional next-position move — the very quirk that hurts it elsewhere — provides neutral drift and solves the instance. **A new, unpredicted boundary: when neutrality dominates, the decoherence floor is not a substitute for accepting neutral moves.** The obvious classical fix (accept equal-fitness candidates) was tested immediately (V4, 5 seeds, `lab_log.md`): it halves the plateau gap (16 % → 8 %) but does not reach the optimum in every seed, is neutral on the uniform instances and possibly harmful on the bimodal one (within one standard deviation). Greedy acceptance therefore stays the default; the plateau failure is a *population-collapse* problem (one point relocating on a plateau cannot find a two-step exchange quickly), which points to purity-regulated decoherence rather than to acceptance rules.
  * *17d makespan + energy (n=100, m=10, additive objective):* QI-MRFO 0.212 = GA 0.212 ≈ Max-Min 0.211 (combined objective), QI-DMO 0.219, MRFO/DMO 0.37, random 0.40. The mechanism keeps its advantage over the classical hosts on the smooth objective, but so does the list heuristic: the energy term here is dominated by idle power during the makespan, so Max-Min remains hard to beat.
  * *17e many VMs (n=40, m=20):* Max-Min 3.2 % ≪ QI-MRFO 12.7 % < GA 18.1 % < QI-DMO 33.7 % ≪ MRFO/DMO 80–91 %. With two tasks per VM the problem is heuristic-friendly and the population methods' 10 000 evaluations are far from enough; QI-MRFO still beats the GA. **Boundary: large $m/n$ favours list heuristics.**
  * *17f bimodal tall barriers (n=50, m=10, 10 000 evaluations, c=1):* QI-MRFO 26.41 (5.2 %) versus Max-Min 27.06 (7.8 %) and GA 29.25 (16.5 %) — the opposite of the 5-seed pilot at c=0.5 (28.10). The bimodal instance has the largest seed variance of the suite (sd 0.8–3.7); the 30-seed run decides this comparison (§26).

## 21. Version 2 improvement plan (what to change next, evidence-driven)

1. **Task-selective, severity-scaled decoherence** for dynamic environments: shock only the registers of tasks whose execution-time row changed, with $\gamma$ proportional to the relative change (predicted to recover the churn/drift gains without harming structural changes) — the uniform shock is the proven-wrong version.
2. **Purity-regulated $\gamma$** (V3 of the static algorithm): set $\gamma_t$ so that the population's expected move size stays in a target band (e.g. 1–3 tasks) instead of a fixed $c/n$; prediction: removes the residual 5–47 % wasted evaluations at small $c$ without the quality loss seen at large $c$.
3. **Max-Min seeding** (one individual initialised as $E(b_{MaxMin})$): predicted to close the heavy-tailed gap; must be tested against Max-Min + local search to avoid a trivial win.
4. **Objective where heuristics do not apply:** the energy-aware objective (Section 17d), then deadlines/cost, evaluated in CloudSim-class simulation.
5. **Drop the quantum-specific parts that do nothing** (sign, squaring) from the *default* configuration and keep the honest name: measurement-based register swarm with decoherence floor; keep the Born variant as an option with its documented convergence-speed difference.

## 22. Prior-art recheck after implementation (Phase 15; `literature/prior_art_recheck.md`)

Searched with our own terminology, the classical equivalents, quantum, cloud and optimisation terms. **(a) Already published:** the classical twin is essentially ICPSO (Strasser, Goodman, Sheppard & Butcher, GECCO 2016: one probability distribution per variable, unchanged PSO equations, renormalisation, one sample per evaluation, best-distributions shifted toward the sampled state — $\varepsilon = 0$ is exactly our basis-state attractor), with Pugh & Martinoli (2006) and Kennedy & Eberhart (1997) as precursors; Born-rule measurement of unit-vector registers is Han & Kim (2002) in the binary case and appears m-ary in QIEDA (Soloviev et al. 2021) and qudit imaginary-time evolution (Åsgrim & Awan 2025); a floor against full collapse exists as the Hε gate (Han & Kim 2004), EDA margins (Krejca & Witt 2018), Baluja's mutation shift and PBIL's pull-to-centre (Yang & Richter 2009); controlled forgetting at a change exists as PBIL hypermutation/hyper-learning and ACO pheromone equalisation after city deletion (Guntsch & Middendorf 2001). **(b) Separately published, never combined:** amplitude registers with swarm difference-vector updates; m-ary registers + floor + change-triggered shock. **(c) Not found:** a per-candidate depolarising channel in any EA/swarm; purity used to calibrate expected reassignments; a decoherence shock of strength $\gamma_{shock}$; VM removal as projective column deletion with warm re-optimisation; any of this in a cloud scheduler. The defensible novelty is therefore narrow and must be stated as such: the purity-calibrated floor and its dose–response, the amplitude-versus-probability comparison (negative), the structural-change rules and the failure-mode analysis of rounding encodings — positioned against ICPSO and QIEA, not as a new probabilistic-register swarm.

## 23. Possible research contribution (Phase 16/17)

In the requested form: *We identify the condition — task-to-VM scheduling with $n \gtrsim 50$ tasks under the floor encoding used by most swarm-scheduling papers — under which the classical optimizers DMO and MRFO exhibit the failure mode "move size ≈ n/2, ≤ 2 % improving candidates, random-search-level makespan", and show that a measurement-based register representation with a purity-calibrated decoherence floor changes the property "expected number of reassigned tasks per candidate" (from ≈ n/2 to a controllable few, with a measured dose–response in the floor strength) and therefore improves the outcome "makespan at equal evaluation budget" from a 76–98 % gap to ≈ 1 %, matching a discrete GA. We further show (negative result) that the quantum-specific ingredients — amplitude squaring and signed interference — are measurably irrelevant, and that uniform decoherence shocks do not improve re-optimisation after workload changes at any tested severity, whereas the representation's structural adaptation rules do.*

Outcome type by the Phase 16 taxonomy: **B (works under a characterised regime: n large, heuristics inapplicable, warm re-optimisation) plus a clean negative for the "quantum" part and for uniform forgetting.** It is not outcome D (no advantage): the advantage over the algorithms the field actually uses (floor-encoded swarms) is large and reproducible (30 seeds, 7 instances, Holm-corrected p < 10⁻⁴, Cliff's δ ≈ −1); the advantage over a proper discrete baseline is small or zero on static batches (GA-class; significantly better on one of seven instances) and real on dynamic ones; and a two-pass list heuristic beats it on six of seven static heterogeneous batches at this budget (§26). The contribution is therefore a *representation result with a measured boundary*, not a new best static scheduler.

## 24. Two-year extension (Phase 20)

* 0–3 months — literature + fundamentals: this report's maps; ICPSO/QIEA/EDA theory (genetic drift with r-valued variables, Ben Jedidia, Doerr & Krejca 2024); CloudSim 7G/iFogSim familiarisation.
* 3–6 months — algorithm + pilot: the notebook's `full` study on a held-out instance family and real traces (GoCJ, HPC2N, Google), Max-Min-seeded variants, energy/cost/deadline objectives; first workshop paper: "Why rounding breaks swarm schedulers and what a measurement-based representation fixes".
* 6–10 months — mechanism refinement: purity-regulated $\gamma$, task-selective severity-scaled shocks, structural rules for VM heterogeneity changes; dynamic benchmark suite with change generators; second paper (dynamic re-optimisation).
* 10–14 months — theoretical analysis: expected-move-size and drift analysis of the register swarm with a floor (runtime analysis in the style of Neumann's chance-constrained makespan work; margins/drift results from EDA theory transfer directly because the twin is a univariate model).
* 14–18 months — large-scale experiments: CloudSim/WorkflowSim with DAG workflows, 30+ seeds, DRL and list-scheduling baselines, statistical protocol as in Section 14 of the notebook.
* 18–21 months — prototype: a Kubernetes scheduler plugin/descheduler using the warm-started register swarm for pod placement under node churn (iContinuum/GreenK8s-style testbed).
* 21–24 months — publication + thesis.

Minimum viable thesis: the failure-mode analysis + representation fix + dose–response + dynamic structural rules, all reproducible (already in hand as a pilot). Main contribution: severity-aware re-optimisation with a measurement-based representation, with theory. Optional extension: Kubernetes prototype. Negative-result contribution (already obtained, publishable as a short paper): quantum-specific ingredients and uniform decoherence shocks add nothing measurable — a caution to the growing "quantum-inspired scheduler" literature.

## 25. Exact next experiment

*Task-selective decoherence under churn.* Same harness as `observe_dyn_severity.py` (n=50, m=10, 15 000-evaluation warm start, 6 changes × 4 000 evaluations, 10 seeds), churn $\rho \in \{0.1, 0.2, 0.5\}$; strategies: continue_struct (control), uniform shock $\gamma \in \{0.25, 0.5\}$ (known-negative control), **selective shock** (registers of tasks sharing a VM with a replaced task receive $\gamma_{sel}$), and **severity-scaled shock** $\gamma_t = \kappa \cdot |ET'_t - ET_t|_1 / |ET_t|_1$ for drift. Metrics: post-change gap and AUC. Prediction (falsifiable): selective/scaled shocks reduce AUC below continue_struct by at least 10 % at $\rho = 0.5$ and are neutral at $\rho = 0.1$; if they do not, the forgetting line is closed and the programme concentrates on structural rules, purity regulation and the theory.

## 26. 30-seed confirmation (notebook `full` mode, executed in Docker; measured)

**Part A — baseline (2 100 runs: 7 instances × 10 algorithms × 30 seeds; 20 000 evaluations each; `results/baseline_full.csv`, `results/stats_full.csv`).** Three instance shapes are new relative to the pilot (held-out): n=200 m=20; n=100 m=10 lognormal tasks on low-heterogeneity VMs; n=60 m=8 bimodal tasks on homogeneous VMs.

Mean gap to the lower bound (%), 30 seeds:

| Instance | Max-Min | Random | PSO | DMO | MRFO | GA | QI-MRFO | QI-DMO | P-MRFO (linear twin) |
|---|---|---|---|---|---|---|---|---|---|
| n30 m5 uniform, hetero | 2.10 | 6.76 | 3.01 | 2.89 | 6.52 | 0.87 | **1.06** | 1.65 | 0.93 |
| n50 m10 bimodal, hetero | 7.77 | 34.50 | 14.06 | 40.85 | 42.15 | 13.55 | **11.99** | 18.04 | 13.27 |
| n100 m10 uniform, hetero | 0.83 | 95.34 | 33.84 | 75.39 | 83.94 | 1.44 | **1.12** | 3.96 | 1.25 |
| n50 m10 uniform, homogeneous | 2.10 | 15.23 | 6.44 | 16.05 | 17.70 | 3.55 | **3.14** | 7.17 | 3.17 |
| n200 m20 uniform, hetero (held-out) | 0.82 | 160.41 | 78.16 | 246.16 | 150.00 | 3.25 | **2.79** | 9.02 | 2.61 |
| n100 m10 lognormal, low hetero (held-out) | 0.79 | 14.82 | 4.40 | 15.79 | 13.67 | 1.07 | **1.07** | 3.16 | 0.92 |
| n60 m8 bimodal, homogeneous (held-out) | 3.96 | 19.83 | 11.65 | 18.46 | 21.64 | 8.04 | **8.68** | 9.23 | 10.34 |

Paired statistics (Wilcoxon signed-rank by seed, Holm-corrected across the 7 instances; Cliff's δ; 95 % bootstrap CI of the mean difference in percentage points):

| Comparison | Result over the 7 instances |
|---|---|
| QI-MRFO vs MRFO | QI-MRFO better on all 7: Holm p < 10⁻⁴ everywhere, δ = −0.97 … −1.00; differences −5.5 pp (n30) to −147 pp (n200) |
| QI-DMO vs DMO | QI-DMO better on all 7: Holm p < 10⁻⁴, δ = −0.82 … −1.00; −1.2 pp (n30) to −237 pp (n200) |
| QI-MRFO vs GA | equal or slightly better: significantly better only at n100 (−0.32 pp, CI [−0.54, −0.08], Holm p = 0.011, δ = −0.55); raw p < 0.05 but not after Holm at n50-homogeneous (−0.41 pp) and n200 (−0.46 pp); no difference on the other four (|diff| ≤ 0.64 pp, CIs include 0) |
| QI-MRFO vs P-MRFO (linear twin) | **no significant difference on any instance after Holm** (smallest Holm p = 0.34; |diff| ≤ 1.7 pp; δ between −0.33 and +0.24) — the Born rule contributes nothing measurable at 30 seeds |
| QI-MRFO vs Max-Min | Max-Min significantly better on 6 of 7 (Holm p ≤ 0.013; by 0.3 pp at n100 and lognormal, 1.0 pp homogeneous, 2.0 pp n200, 4.2 pp bimodal-hetero, 4.7 pp bimodal-homogeneous); QI-MRFO better only at n30 (−1.05 pp, Holm p < 10⁻⁴) |
| QI-MRFO vs QI-DMO | QI-MRFO better on 6 of 7 (Holm p ≤ 0.002), tie on bimodal-homogeneous |
| QI-DMO vs GA | GA better on 6 of 7 (Holm p ≤ 0.014); tie on bimodal-homogeneous |

Mechanism metrics (means over 30 seeds; largest instances): tasks changed per candidate — MRFO 126, DMO 121, QI-MRFO 19, linear twin 27, GA 7.6 (n200 m20); MRFO 46, QI-MRFO 10, GA 5.4 (n100). Global-best improvements per 1 000 evaluations at n200: QI-MRFO 5.1, GA 3.4, MRFO 0.48. Wasted candidates QI-MRFO 9–21 % (c = 1), end diversity 0.001–0.02, end purity 0.92–0.99. Runtime per 20 000 evaluations: QI-MRFO 2.5–4.6× MRFO (16–41 s vs 4–12 s in the Docker container with 18 concurrent processes); QI-DMO 2–3× DMO.

**What the 30 seeds change relative to the pilot.** (i) The encoding effect and its growth with $n$ are confirmed with overwhelming evidence, including on the three held-out shapes (n=200, m=20: MRFO 150 % → QI-MRFO 2.8 %). (ii) The Born-rule irrelevance is confirmed: no instance separates QI-MRFO from its linear-probability twin. (iii) The pilot's "ties or beats the GA on all four instances" softens to "equal or slightly better, significant on one instance": QI-MRFO is a GA-class optimizer, not a better one. (iv) The pilot's suggestion that QI-MRFO matches Max-Min at n=100 (47.54 vs 47.45) does not survive: with 30 seeds Max-Min is significantly better on 6 of 7 static instances by 0.3–4.7 pp; QI-MRFO beats it only on the smallest instance. The boundary stated in §20 therefore widens: **on static independent-task makespan batches with heterogeneous VMs, a two-pass list heuristic is the right tool, and the population method's case rests on objectives and dynamics the heuristic does not handle** — which is exactly the direction the proposal takes.

**Part B — ablation, sensitivity, adversarial and dynamic sections of the `full` run (measured; `results/ablation_full.csv`, `sensitivity_full.csv`, `failure_cases_full.csv`, `dynamic_full.csv`; the executed notebook is `results/executed_full.ipynb`, zero cell errors).**

*Ablation (30 seeds, 20 000 evaluations, 4 instances; mean gap to LB in %):*

| Variant | n30 m5 | n50 bimodal | n100 m10 | n50 homogeneous |
|---|---|---|---|---|
| MRFO (classical) | 6.52 | 42.15 | 83.94 | 17.70 |
| QI-MRFO no-decoherence (registers + measurement only) | 2.46 | 17.74 | 13.12 | 7.84 |
| **QI-MRFO** (c = 1) | 1.06 | 11.99 | 1.12 | 3.14 |
| QI-MRFO unsigned amplitudes | 1.24 | 13.91 | 1.16 | 3.65 |
| P-MRFO linear twin (no Born rule) | 0.93 | 13.27 | 1.25 | 3.17 |
| DMO (classical) | 2.89 | 40.85 | 75.39 | 16.05 |
| DMO greedy-next | 2.26 | 17.65 | 30.03 | 12.58 |
| QI-DMO no-decoherence | 2.43 | 23.30 | 4.33 | 8.02 |
| **QI-DMO** (c = 0.25) | 1.65 | 18.04 | 3.96 | 7.17 |
| QI-DMO greedy-next | 1.33 | 10.12 | 1.46 | 3.69 |
| P-DMO linear twin | 1.71 | 16.25 | 4.72 | 7.53 |
| QI-DMO register-attractor (negative control) | 6.70 | 32.87 | 91.16 | 15.12 |
| GA | 0.87 | 13.55 | 1.44 | 3.55 |

The ladder holds at 30 seeds: representation first (84 % → 13 % at n100), decoherence floor second (13 % → 1.1 %); unsigned and linear-twin variants are within one standard deviation of QI-MRFO on every instance (SD 0.4–0.5 pp on the uniform instances, 7 pp on bimodal); the superposition attractor destroys the search; DMO's unconditional move explains the QI-DMO deficit (greedy-next QI-DMO: 1.46 % at n100, 10.1 % on bimodal — the best population result on that instance). One nuance the pilot missed: for QI-DMO the decoherence floor matters little (4.33 → 3.96 at n100) because DMO's own unconditional noise step already acts as a floor; for QI-MRFO, which is greedy in every phase, the floor is essential (13.1 → 1.1).

*Sensitivity (30 seeds; n100 m10, n200 m20, n50 bimodal; gap %):*

| c in γ = c/n | 0 | 0.25 | 0.5 | 1 | 2 | 4 |
|---|---|---|---|---|---|---|
| QI-MRFO n100 | 13.12 | 1.43 | 1.34 | **1.12** | 1.35 | 1.65 |
| QI-MRFO n200 m20 | 75.04 | 5.64 | 3.36 | **2.79** | 3.37 | 5.05 |
| QI-MRFO bimodal | 17.74 | 12.32 | 12.19 | 11.99 | 11.78 | 11.32 |
| QI-DMO n100 | 4.33 | **3.96** | 5.49 | 7.66 | 10.66 | 22.22 |
| QI-DMO n200 m20 | 12.76 | **9.02** | 11.55 | 17.38 | 29.73 | 55.60 |
| QI-DMO bimodal | 23.30 | 18.04 | **16.63** | 18.17 | 22.22 | 25.48 |

QI-MRFO's wasted-candidate fraction falls monotonically with c (0.62 → 0.44 → 0.31 → 0.17 → 0.05 → 0.002 at n100) while quality is flat between c = 0.5 and 2: a broad, forgiving optimum. QI-DMO's optimum is sharp (c = 0.25) and large c is destructive (55.6 % at n200 for c = 4): the host's own noise compounds the channel. Population size 15/30/60 and somersault factor 1/2/3 change QI-MRFO by ≤ 0.4 pp at n100 (P = 15 is slightly better at n200: 2.42 vs 2.79 vs 3.22 for P = 60, i.e. more iterations help when the budget is tight).

*Adversarial cases (30 seeds, 10 000 evaluations; gap % unless stated):*

| Case | Max-Min | Random | MRFO | QI-MRFO | GA | DMO | QI-DMO |
|---|---|---|---|---|---|---|---|
| 17a tiny (n10 m3) | 1.77 | **0.17** | 0.85 | 0.33 | 0.21 | 0.22 | 0.33 |
| 17b two VMs (n40 m2) | 0.35 | 0.004 | 0.02 | 0.005 | 0.003 | 0.002 | 0.001 |
| 17c identical tasks, homogeneous VMs (n40 m8) | **0.00** | 17.3 | 18.7 | 11.3 (27.83 ± 2.5) | **0.00** | 17.3 | 3.3 |
| 17d makespan + energy (combined objective, lower is better) | **0.211** | 0.400 | 0.375 | 0.212 | 0.213 | 0.375 | 0.218 |
| 17e many VMs (n40 m20) | **3.19** | 96.6 | 96.6 | 15.4 | 18.6 | 90.7 | 33.2 |
| 17f bimodal tall barriers (n50 m10, 10k) | **7.77** | 36.8 | 44.5 | 13.2 | 14.7 | 53.0 | 19.6 |

All four predicted boundaries are confirmed: tiny and two-VM instances need no mechanism (random search is within 0.2 %); the pure plateau defeats QI-MRFO (11.3 %) while the GA and Max-Min solve it exactly and QI-DMO nearly does (3.3 %, its unconditional move supplies neutral drift); many VMs per task and heavy-tailed batches belong to the list heuristic (Max-Min 3.2 % and 7.8 % versus QI-MRFO 15.4 % and 13.2 %); the fast-mode hint that QI-MRFO beats Max-Min on the bimodal instance was a 3-seed artefact. On the smooth makespan + energy objective QI-MRFO (0.212) equals the GA (0.213) and Max-Min (0.211) and beats its classical host (0.375) by 43 %.

*Dynamic workloads (10 seeds; n50 m10; 15 000-evaluation warm start, then 5 changes × 4 000 evaluations; QI-MRFO c = 1; mean post-change gap % / area under the gap curve %):*

| Strategy | churn 20 % | drift | VM addition | VM failure |
|---|---|---|---|---|
| QI-MRFO restart | 4.73 / 14.2 | 5.62 / 20.6 | 8.82 / 24.6 | 2.16 / 8.3 |
| **QI-MRFO continue** (carried registers + structural rules) | **4.12 / 5.6** | 4.40 / **8.8** | **6.96 / 8.8** | 2.13 / **3.2** |
| QI-MRFO shock γ = 0.25 | 4.23 / 8.2 | 4.27 / 9.0 | 7.73 / 12.5 | 2.10 / 3.8 |
| QI-MRFO shock γ = 0.5 | 4.66 / 10.3 | 4.25 / 12.0 | 7.34 / 15.3 | 2.07 / 4.8 |
| QI-MRFO shock γ = 0.75 | 4.75 / 13.4 | 5.03 / 17.7 | 8.18 / 19.8 | 2.20 / 6.2 |
| MRFO restart / continue | 51 / 50 | 79 / 72 | 76 / 72 | 34 / 15 |
| GA restart | 5.93 / 16.0 | 6.21 / 22.9 | 9.92 / 25.5 | 2.53 / 9.3 |
| GA continue | 5.00 / 7.2 | 5.51 / 10.0 | 8.92 / 11.5 | 2.81 / 5.1 |
| GA hypermutation | 5.79 / 11.2 | 6.37 / 15.9 | 10.50 / 14.2 | 2.82 / 8.6 |

With 10 seeds the picture of the 5-seed pilot is unchanged and sharper: carrying the register state is the best or within noise of the best strategy on every change type, with recovery areas 2.5–3× smaller than a restart; **QI-MRFO-continue beats GA-continue on all four change types** (by 0.7–2.0 pp in final gap and 20–45 % in recovery area; seed SDs 0.4–1.1 pp); the decoherence shock never improves on continuation by more than 0.15 pp (drift, γ ≤ 0.5) and always slows recovery; GA hypermutation is worse than GA continuation everywhere. The value of the mechanism for cloud resource management is therefore not "quantum forgetting" but the warm-startable, structurally adaptable state that a measurement-based representation provides.

## Final decision

**PROCEED — with the revised framing.** The implementation works, the effect is large and reproducible against the baselines the field uses (2 100-run, 30-seed confirmation on seven instances including three held-out shapes), the mechanism is understood (move size via purity, floor via decoherence), the boundary is measured (a list heuristic wins static heterogeneous batches at this budget; neutrality-dominated plateaus defeat greedy acceptance; uniform forgetting does not help under change), and the honest negative results (Born rule and interference irrelevant; uniform shocks useless) are themselves publishable. The research question for the PhD is not "does quantum inspiration beat classical?" but "which properties of a measurement-based schedule representation matter for re-scheduling under change, and how should its noise floor adapt to change severity?"
