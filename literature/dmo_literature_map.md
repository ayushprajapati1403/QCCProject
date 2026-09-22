# Literature map B — DMO, quantum-inspired DMO variants, DMO in cloud scheduling

Compiled 2026-09-22 by live web search (Crossref/OpenAlex/Semantic Scholar sweeps, Europe PMC full texts, MEALPY source). The original CMAME paper is closed access; equations are taken from restatements by the original authors (BDMO, PLOS One 2022; BDMSAO, Sci Rep 2022; ADMO, PLOS One 2022) cross-checked against three independent restatements (DMOAQ 2022; CDMO 2024; MDMOSA 2025). Unconfirmed items are marked UNVERIFIED.

## 1. Original DMO equations (Agushaka, Ezugwu, Abualigah, CMAME 391:114570, 2022; DOI 10.1016/j.cma.2022.114570; ~870 citations)

| Component | Equation (paper, as restated) | Sources |
|---|---|---|
| Initialisation | X is an n×d matrix, x_ij ~ U(LB, UB) | DMOAQ Eq. 1–2 |
| Population split | n_alpha = n − bs (bs = number of babysitters) | DMOAQ Eq. 4; BDMO; EDMO §3.1 |
| Alpha selection probability | α = fit_i / Σ_i fit_i | BDMO Eq. 3; BDMSAO Eq. 3; ADMO Eq. 1; DMOAQ Eq. 3; CDMO Eq. 3; MDMOSA Eq. 10 |
| Candidate food position | X_{i+1} = X_i + phi · peep, phi ~ U[−1,1] (peep = alpha vocalisation; default 2) | BDMO Eq. 4; BDMSAO Eq. 4; ADMO Eq. 2; DMOAQ Eq. 5; MDMOSA Eq. 12 |
| Sleeping mound | sm_i = (fit_{i+1} − fit_i) / max{|fit_{i+1}|, |fit_i|} | BDMO Eq. 5; ADMO Eq. 3; DMOAQ Eq. 6; CDMO Eq. 5; MDMOSA Eq. 13 |
| Average sleeping mound | φ = Σ_i sm_i / n | BDMO Eq. 6; ADMO Eq. 4; DMOAQ Eq. 7; CDMO Eq. 6 |
| Scout movement | X_{i+1} = X_i − CF·phi·rand·[X_i − M] if φ_{i+1} > φ_i (exploration); X_{i+1} = X_i + CF·phi·rand·[X_i − M] otherwise | BDMO Eq. 7; DMOAQ Eq. 8; MDMOSA Eq. 11 |
| Control factor | CF = (1 − iter/Max_iter)^(2·iter/Max_iter) | BDMO; DMOAQ Eq. 10; CDMO |
| Movement vector | M = Σ_i X_i × sm_i / X_i | BDMO; DMOAQ Eq. 9; CDMO |
| Babysitter exchange | scout phase if C < L, babysitting if C ≥ L; babysitters re-initialised and C reset to 0 | DMOAQ Eq. 11; BDMSAO; EDMO §3.3 |

### Paper vs MATLAB code (MEALPY `OriginalDMOA` follows the MATLAB File Exchange 105125 code)
MEALPY's docstring: "The Matlab code differs slightly from the original paper; there are some parameters and equations in the Matlab code that don't seem to have any meaningful purpose; the algorithm seems to be weak on solving several problems."

| Paper says | Code does | Corroboration |
|---|---|---|
| α = fit_i/Σfit_i | roulette over fi = exp(−fit/mean) (ABC-style) | EL-DMOA (Sci Rep 2025); IDMO (JBE 2022, original authors): the probability "is just a computational overhead and contributes nothing" |
| X_{i+1} = X_i + phi·peep | phi = (peep/2)·U(−1,1)^d; new = X_alpha + phi·(X_alpha − X_k), random partner k (difference vector) | UAV-3D IDMO (Sci Rep 2025); EDMO (arXiv 2511.09020) |
| scout uses CF, M | scout loop = second difference-vector move; SM = (f_new − f_old)/max(f_new, f_old) | — |
| M = ΣX_i·sm_i/X_i | M = SM[idx]·X_i/X_i = SM[idx] (scalar; the "no meaningful purpose" equation) | DevDMOA: "Removed the meaningless variable tau" |
| condition φ_{i+1} > φ_i | new_tau = mean(SM) compared with the previous iteration's mean (init −inf) | — |
| final move accepted if better | "Next Mongoose position" overwrites every agent UNCONDITIONALLY | explains "weak on several problems" |
| L unspecified | L = round(0.6 · n_dims · n_baby_sitter); only the first n_baby_sitter indices are ever checked | — |
| babysitters exchanged | re-initialised from scratch | IDMO (JBE 2022): "instead of initializing them afresh as done in DMO" |

## 2. Quantum-inspired DMO variants — all found

| Title | Authors | Year | Venue | URL | Quantum mechanism | Classical equivalent | Problem | Representation | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| Feature Selection for High Dimensional Datasets Based on Quantum-Based Dwarf Mongoose Optimization (DMOAQ) | Abd Elaziz, Ewees, Al-qaness, Alshathri, Ibrahim | 2022 | Mathematics 10(23):4565 | https://mdpi-res.com/d_attachment/mathematics/mathematics-10-04565/article_deploy/mathematics-10-04565.pdf | Q-bit q = e^{iθ}; rotation q(t+1) = q(t)·R(Δθ), Δθ ∈ {0, ±0.01} from a lookup table keyed on (X_ij, X_b, f(X_i) vs f(X_b)); solution = θ vector; measurement BX_ij = 1 if rand < |β|²; DMO operators act on θ | Han–Kim QIEA rotation gate + threshold binarisation | wrapper feature selection (18 UCI + 8 high-dim sets) | binary, one qubit per feature | GENUINELY DIFFERENT (binary only) — standard QIEA bolt-on |
| Quantum Dwarf Mongoose Optimization With Ensemble Deep Learning Based Intrusion Detection in CPS (QDMO-EDLID) | Almutairi et al. | 2023 | IEEE Access 11:66828 | https://ieeexplore.ieee.org/document/10156784/ | full text unreachable; per the QIEA-FSS survey (arXiv 2407.17946 §6.13): rotation gate with angle from a reference table | rotation gate | feature selection for intrusion detection | binary Q-bit (UNVERIFIED) | QUANTUM TERMINOLOGY ON A CLASSICAL METHOD (as far as verifiable) |
| Explainable deep learning for glaucoma detection: … quantum-based Dwarf Mongoose optimization (QDMOA) | Deepa et al. | 2024 | Edelweiss Appl. Sci. Technol. 8(6) | https://learning-gate.com/index.php/2576-8484/article/download/2140/817 | reproduces DMOAQ verbatim; applied to a continuous hyper-parameter (internally inconsistent) | rotation gate | DenseNet tuning | nominal binary Q-bit | TERMINOLOGY — copied formulation |
| Mitigating Air Pollution Risks … Quantum-Optimized Approach for NO2 Prediction (QDMOA) | Sivakumaran et al. | 2025 | J. Machine and Computing 5(2) | https://anapub.co.ke/journals/jmc/jmc_pdf/2025/jmc_volume_5-issue_2/JMC202505056.pdf | restates DMO + DMOAQ's Q-bit equations; used for hyper-parameter tuning | rotation gate | ConvLSTM tuning | nominal binary | TERMINOLOGY — template reuse |
| A Quantum Tunneling and Bio-Phototactic Driven Enhanced Dwarf Mongoose Optimizer (EDMO / DQTOS) | Yu, Yang, An, Wei, Xu, Xu | 2025 | arXiv 2511.09020 | https://arxiv.org/abs/2511.09020 | "quantum potential" V(X_i) = |f(X_i) − f_best|/(f_max − f_min)·V0; WKB-style tunnelling probability P = exp(−2√2·V/Ē − κ); if rand < P: X_new = X_i + ξ·T(t)·δ(t), ξ ~ N(0,1) | fitness-scaled Gaussian perturbation with annealed step | CEC2017/2020, engineering design, UAV path planning | continuous | TERMINOLOGY — a Boltzmann-flavoured perturbation on classical positions |

No QPSO-style (delta-potential-well) DMO exists. No quantum DMO is applied to cloud/fog/edge scheduling or VM placement. No multi-valued (K-ary) amplitude representation exists for DMO.

## 3. DMO in cloud / fog / edge scheduling

| Title | Year | URL | Problem | Representation | Baselines | Result | Weakness |
|---|---|---|---|---|---|---|---|
| Task Scheduling in Cloud Computing Environment Based on DMO (Abraham, Ngadi, Sharif, Sidik, Kolawole) | 2025 | https://thesai.org/Downloads/Volume16No12/Paper_73-Task_Scheduling_in_Cloud_Computing_Environment.pdf | independent tasks, makespan | discrete task→VM mapping via ETC (mechanism unspecified) | MALPSO, EMPA, GWOEM; CloudSim; GoCJ 100–1000 tasks | 1000 tasks: 491.2 vs 527.9–543.0 | single objective; limited baselines |
| MDMOSA: Multi-Objective DMO for Cloud Task Scheduling (Abraham et al.) | 2025 | https://file.techscience.com/files/onlinefirst/2025/12.23/TSP_CMC_72279/TSP_CMC_72279.pdf | makespan + cost, Pareto archive | task-to-instance tuples; SA local search | SMOACO, MOTSGWO, MFPAGWO; CloudSim | 1000 tasks/50 VMs: 342.26 vs 352–361 | plain DMO "may converge prematurely" |
| Chaotic local search-based DMO for multi-objective cloud scheduling (CLSDMO; Abraham et al.) | 2025 | https://link.springer.com/article/10.1186/s13677-025-00837-7 | makespan, cost, utilisation | integer array (task → VM) + logistic-map local search | MOTSWAO, MOTSGWO, MOTSACO; CloudSim; GoCJ + HPC2N | makespan 314.37 vs 322–326; cost −45–50% | static tasks; no code |
| MABFDMO: adaptive DMO for multi-objective cloud scheduling (Abraham et al.) | 2026 | https://www.sciencedirect.com/science/article/abs/pii/S2210537926001034 | multi-objective | adaptive babysitter foraging (UNVERIFIED) | GCWOAS, HGHHC, DPPA | makespan improvements 10–21% (snippet) | closed access |
| Chaos opposition-based DMO for workflow scheduling in cloud (CO-DWO; Talha, Bouayad, Cherkaoui Malki) | 2023 | https://api.crossref.org/works/10.1002/ett.4744 | workflow scheduling; time, cost, resource use | chaos + OBL initialisation | not visible | "better convergence rate" | paywalled |
| Hybrid Prairie Dog and DMO for fog application placement (Baskar et al.) | 2025 | https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11707010/fullTextXML | IoT placement on fog nodes; energy, cost, makespan | application-to-device mapping | GWO, GA, NSGA, WOA variants | −22% energy, −25% makespan | says DMOA limited in exploration |
| SADMO: scheduling + data replication (Rambabu, Govardhan) | 2023 | https://api.semanticscholar.org/graph/v1/paper/DOI:10.1080/1206212X.2023.2267840 | joint scheduling + replication | self-adaptive DMO | not visible | fitness 0.324 | paywalled |
| Strategy-proof DMO mechanism for vehicular task offloading (Liu, Liu) | 2026 | https://www.sciencedirect.com/science/article/abs/pii/S0167739X2500322X | auction-based offloading | seeded allocations | not visible | strategy-proofness | closed access |
| Discrete DMO for task assignment on smart farms (Xu, Li, Zhang, Su) | 2024 | https://link.springer.com/article/10.1007/s10586-024-04271-3 | cloud–edge unsplittable assignment | discrete DMO seeded by an approximation algorithm | not visible | not visible | abstract only |

VM placement/consolidation with DMO: none found.

## 4. Reported weaknesses of DMO (with the stating paper)
1. Slow convergence: ADMO (PLOS One 2022); DMOAQ (2022); IDMO (ESWA 2023); EDMO (JBUAA 2025); UAV-3D IDMO (Sci Rep 2025).
2. Restricted exploitation: BDMSAO (Sci Rep 2022). 3. Limited exploration: Baskar et al. (Sci Rep 2025).
4. Alpha-probability computation is overhead: IDMO (JBE 2022, original authors); BDMO (PLOS One 2022).
5. Roulette alpha selection loses diversity rapidly: EL-DMOA (Sci Rep 2025). 6. Babysitters re-initialised afresh, discarding information: IDMO (JBE 2022).
7. No mutation/escape operator: EDMO (arXiv 2511.09020). 8. Premature convergence in high-dimensional scheduling spaces: CLSDMO, MDMOSA (2025).
9. Continuous-only: needs thresholds or transfer functions (BDMO, CDMO, BinDMO NCA 2024). 10. Code ≠ paper, meaningless equations: MEALPY docstring.

## 5. Gap
Every quantum DMO uses either the binary Han–Kim template (four papers, three of them copies of Elaziz 2022) or a relabelled Gaussian jump. No work combines a multi-valued (K-ary) probability-amplitude representation (a per-task amplitude vector over VMs collapsed by measurement) with DMO's alpha/scout/babysitter dynamics for cloud, fog or edge scheduling; DMO cloud scheduling (Abraham/Ngadi line 2025–2026, CO-DWO, Baskar) uses integer or rounded-continuous encodings in CloudSim with GoCJ/HPC2N and repairs premature convergence with SA, chaos, OBL or adaptive parameters. A credible contribution must confront the paper-vs-code discrepancies above, since most reimplementations follow the MATLAB variant.

## Sources
https://api.crossref.org/works/10.1016/j.cma.2022.114570 ; https://raw.githubusercontent.com/thieu1995/mealpy/master/mealpy/swarm_based/DMOA.py ; https://www.mathworks.com/matlabcentral/fileexchange/105125-dwarf-mongoose-optimization-algorithm ; https://pmc.ncbi.nlm.nih.gov/articles/PMC9536540/ (BDMO) ; https://www.ebi.ac.uk/europepmc/webservices/rest/PMC9629639/fullTextXML (ADMO) ; https://www.ebi.ac.uk/europepmc/webservices/rest/PMC9440036/fullTextXML (BDMSAO) ; https://www.ebi.ac.uk/europepmc/webservices/rest/PMC10771514/fullTextXML (CDMO) ; https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12217916/fullTextXML (EL-DMOA) ; https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12290074/fullTextXML (UAV-3D IDMO) ; https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11707010/fullTextXML ; https://mdpi-res.com/d_attachment/mathematics/mathematics-10-04565/article_deploy/mathematics-10-04565.pdf ; https://ieeexplore.ieee.org/document/10156784/ ; https://arxiv.org/abs/2407.17946 ; https://learning-gate.com/index.php/2576-8484/article/download/2140/817 ; https://anapub.co.ke/journals/jmc/jmc_pdf/2025/jmc_volume_5-issue_2/JMC202505056.pdf ; https://arxiv.org/abs/2511.09020 ; https://thesai.org/Downloads/Volume16No12/Paper_73-Task_Scheduling_in_Cloud_Computing_Environment.pdf ; https://file.techscience.com/files/onlinefirst/2025/12.23/TSP_CMC_72279/TSP_CMC_72279.pdf ; https://link.springer.com/article/10.1186/s13677-025-00837-7 ; https://api.crossref.org/works/10.1016/j.suscom.2026.101393 ; https://api.crossref.org/works/10.1002/ett.4744 ; https://api.crossref.org/works/10.1016/j.future.2025.108027 ; https://link.springer.com/article/10.1007/s10586-024-04271-3 ; https://api.semanticscholar.org/graph/v1/paper/DOI:10.1007/s42235-022-00316-8 (IDMO) ; https://api.semanticscholar.org/graph/v1/paper/DOI:10.1007/s00521-024-09436-0 (BinDMO)
