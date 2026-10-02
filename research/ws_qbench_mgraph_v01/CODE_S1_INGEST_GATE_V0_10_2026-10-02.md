# WS-QBENCH-MGRAPH v0.10 — Code S1 acquisition and ingestion gate

## Status

`IMPLEMENTED IN SOFTWARE` / provenance gate. No Code S1 source has been executed.

Professor Sunkyu Yu confirmed in follow-up that the article and Supplementary Materials are open access and should be downloaded through a standard web browser. The current automated web environment continues to receive HTTP 403 from the Science article endpoint. Public search also does not expose the three MATLAB files individually.

The official paper is DOI `10.1126/sciadv.aee5566`.

## Required Code S1 files

The corresponding author identified:

1. `R003_Rabi_001_eig_Fock_data.m`
2. `R003_Rabi_001_eig_Fock_post.m`
3. `R003_Rabi_001_eig_Fock_post_plot.m`

v0.10 prepares a **non-executing** ingestion path for those files.

## What the gate does

When Code S1 is placed in one local directory, `code_s1_ingest_v10.py`:

- requires all three expected filenames;
- reads source as text only;
- computes SHA-256 for every file;
- records byte and line counts;
- counts source markers relevant to the unresolved numerical discrepancy;
- refuses a reviewed hash-lock transition if any file hash changes;
- does not invoke MATLAB, Octave, shell commands, or source-defined functions.

Markers include:

- `factorial`, `gamma`, `gammaln`;
- `laguerreL` / Laguerre evaluation;
- `prod` multiplication;
- `randperm`, `randi`, `datasample`;
- exact `==0` / `~=0` tests;
- `eps`, `realmin`;
- explicit `single`, `double`, `sym`, or `vpa` conversions.

These are the highest-value implementation details for explaining the v0.9 S1 discrepancy without inventing a threshold.

## Why source inspection is now decisive

The published arXiv supplementary figure visibly shows high-coupling `pConnect` plateaus below unity and strongly dependent on `q`, while the v0.9 stable-formula implementation approaches unity for q=2 and q=10.

Because the corresponding author specified **exact nonzero in double precision** and **no tolerance**, algebraically equivalent numerical implementations can still differ if they have different overflow, underflow, intermediate rounding, or product-order behavior.

The first comparison after acquisition is therefore:

`Code S1 hopping zero mask vs Worldshepherd hopping zero mask`

followed by:

`Code S1 W_q zero outcomes vs Worldshepherd W_q zero outcomes`.

Only after those match should Monte Carlo curve comparison be promoted.

## Retrieval boundary

Do not scrape around publisher access controls or fabricate a supplementary URL. If the automated endpoint remains blocked, obtain the open-access Supplementary Material through a normal browser and provide the Code S1 files to the controlled ingestion directory.

## Promotion gate

Exact S1 / Figure 4 promotion remains blocked until:

1. all three files are present;
2. SHA-256 hashes are recorded;
3. source markers are reviewed;
4. the floating-point zero path is understood;
5. the authors' MATLAB results and Worldshepherd results are compared on identical sampled inputs.
