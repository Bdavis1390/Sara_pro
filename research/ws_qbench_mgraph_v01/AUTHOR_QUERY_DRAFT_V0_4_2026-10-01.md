# Draft author query — magnetic-graph reproduction details

Subject: Reproduction details for *Magnetic graphs for cavity quantum electrodynamics*

Dear Professors Yu, Piao, and Park,

I am independently reproducing the numerical magnetic-graph analysis in your 2026 *Science Advances* paper, *Magnetic graphs for cavity quantum electrodynamics* (eaee5566), as part of a bounded reproducibility workflow.

The normalized magnetic-Laplacian implementation reproduces the reported weak-coupling behavior and the qualitative-to-quantitative `lambda1(eta)` transition well at `Nmax=200`. I am now trying to reproduce Figure 4 and Supplementary Figure S1 without introducing undocumented numerical assumptions.

Could you please share the source code referenced in the paper, or clarify the following implementation details?

1. **Loop connection rule:** Supplementary Note S1 defines `pConnect`, `pNontrivial`, and `pTrivial`, and End Matter I treats a loop as disconnected when any constituent weight is zero. In the numerical implementation, was an explicit tolerance or maximum hopping-order cutoff used to treat very small nonzero displacement-matrix elements as zero? If so, what rule/value generated Figure 4d and Supplementary Figure S1?
2. **Random-subgraph sampling:** Were the `q` number states in each bipartition sampled without replacement, or were duplicate draws handled in another way?
3. **Figure 4e/f normalization:** What numerical values/units were used for `h0`, `|h_parallel|`, `|h_perp|`, and `hbar omega0` when computing the first 30 IPR/eigenenergy curves?
4. If available, a minimal script reproducing Figures 3b, 4c-f, and Supplementary Figure S1 would be particularly helpful.

For transparency, I am keeping independent cross-checks, adversarial null controls, cutoff sensitivity, and negative results separate from claims about your published implementation. I will not describe Figure 4/S1 as exactly reproduced until these conventions are source-locked.

Thank you for making the work available and for any clarification you can provide.
