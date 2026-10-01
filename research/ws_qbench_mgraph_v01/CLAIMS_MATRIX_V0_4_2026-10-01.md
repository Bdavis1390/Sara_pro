# WS-QBENCH-MGRAPH v0.4 claims matrix

| Claim | Evidence | State | External wording allowed | Promotion gate |
|---|---|---|---|---|
| Generalized QRM maps to the published Floquet-Rabi magnetic graph | Source paper | `SUPPORTED BY LITERATURE` | Cite as authors' result | N/A |
| Worldshepherd implements finite displacement/hopping and normalized magnetic Laplacian | Repository code/tests | `IMPLEMENTED IN SOFTWARE` | Yes, as software implementation | CI + review |
| Weak-coupling `lambda1 ~ 2 eta` and reported crossover are independently reproduced numerically | Independent SciPy cross-check | `SIMULATED ONLY` + independent cross-check | Yes, with cutoff/method stated | External independent reproduction for stronger claim |
| Low Fock cutoffs can materially bias DSC `lambda1` | Cutoff sweep | `PROVEN INTERNALLY — NUMERICAL CONTROL ONLY` | Yes, for tested implementation/settings | Independent rerun |
| Raw Figure-4c-like `C_q(q)` trend is close to a complete-bipartite sampling null | v0.2 null control | `PROVEN INTERNALLY — NUMERICAL CONTROL ONLY` | Yes, explicitly as Worldshepherd adversarial finding | Larger ensemble + independent rerun |
| Raw conductance alone proves quasi-one-dimensional physical structure | Source interpretation challenged by null sufficiency | `NOT CURRENTLY CLAIMED` | Do not state as Worldshepherd conclusion | Show null-corrected incremental information |
| Detailed source sign topology changes `lambda1` beyond magnitudes/coarse phase classes | v0.3 Delta-sign permutation null | `PROVEN INTERNALLY — NUMERICAL CONTROL ONLY` | Yes, limited to tested finite model | Larger ensembles / alternative nulls |
| Detailed source sign topology universally increases physical-state localization | v0.4 IPR sensitivity contradicts universality | `NOT CURRENTLY CLAIMED` | Do not claim | Lock Figure 4e/f parameters and reproduce |
| Approximately half of formed loops are nontrivial | Source + threshold sensitivity cross-check | `SUPPORTED BY LITERATURE`; internally robust conditional split | Cite source; internal check as sensitivity result | Author/source-code lock for exact reproduction |
| Absolute `pConnect(eta,q)` is exactly reproduced | Threshold convention unresolved | `NOT CURRENTLY CLAIMED` | Do not claim | Obtain numerical zero/truncation convention |
| Figure 4e/f IPR/eigenenergy curves are exactly reproduced | Hamiltonian normalization unresolved | `NOT CURRENTLY CLAIMED` | Do not claim | Obtain `h_perp/omega0`, `h_parallel`, `h0` and rerun Nmax=200 |
| Magnetic-graph findings imply gate-speed, QEC, sensing, or hardware-performance gains for Worldshepherd | No hardware experiment | `REQUIRES PARTNER VALIDATION` | Do not infer performance | Partner/lab validation |

## Enforcement rule

External summaries must prefer the lowest defensible claim state when multiple rows interact. In particular, graph-level `lambda1` evidence must not be promoted into a localization or hardware-performance claim without the corresponding physical-Hamiltonian and experimental gates.
