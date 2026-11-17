# BAROS OpenKBP-Opt external planning benchmark gate

**Prepared:** 2026-11-17. **NONCLINICAL / DESK RESEARCH, NOT AN EXECUTED EXTERNAL BENCHMARK OR INSTITUTIONALLY APPROVED DATA STUDY.** This is a source-specific technical feasibility protocol for the remaining scientific novelty and TPS-objective questions raised by an academic radiotherapy-physics reviewer. No dataset has been downloaded, no third-party code/data imported or executed, and no clinical result claimed.

## Material discovery and its implications

Babier et al., *OpenKBP-Opt: an international and reproducible evaluation of 76 knowledge-based planning pipelines*, Physics in Medicine & Biology **67** (2022) 185012, DOI **10.1088/1361-6560/ac8044**, provides a more rigorous *planning-objective* reference than comparing BAROS solely with a trigger-only toy policy. Its open published method uses the OpenKBP challenge's 100 head-and-neck IMRT test cases, 21 models' dose predictions, a dose-influence matrix and **four dose-mimicking optimization formulations**. The paper evaluates 76 resulting KBP pipelines (after excluding two poorly performing predictor models from the main analysis) and reports that some dose-mimicking formulations can recover planning objective weights. It does not supply longitudinal FMISO/hypoxia truth, establish a new BAROS technology, or correspond to a commissioned TPS at a clinical institution.

**Crucial prior-art boundary:** A research mapping from a desired dose distribution to optimization objective weights **already exists**. Therefore BAROS's new synthetic `research_objective_intent.py` cannot be claimed to invent treatment-planning objective weights, inverse planning or dose mimicking. BAROS's only current *candidate contribution* is a jointly auditable, fail-closed **longitudinal biological-evidence qualification layer upstream of any objective translation**. Whether that joint layer creates meaningful value beyond established quality safeguards remains UNPROVEN.

## Reproducible external sources and technical inventory

- **Paper:** https://pmc.ncbi.nlm.nih.gov/articles/PMC10696540/ and https://doi.org/10.1088/1361-6560/ac8044
- **Author code and dataset description:** https://github.com/ababier/open-kbp-opt ; https://github.com/ababier/open-kbp-opt/blob/master/README.md
- **Code license reviewed:** repository `LICENSE` is MIT, © Aaron Babier (2022). MIT-covered source code may be reused subject to license obligations. **Do not presume that any associated patient-derived images, external downloadable data, or third-party code/dependencies grant the same rights solely because a root license is present.** Before patient-derived dataset ingestion, check exact file-specific usage, commercial permissions, data-sharing restrictions, privacy/ethics conditions and attribution.
- **Benchmark data described (100 cases):** reference dose, 21 predicted doses, dose-influence matrix, CT/structure masks, feasible-dose mask and voxel dimensions; downstream plan dose, fluence, optimization gap and weights are described. **These are research-model/data artifacts, not DICOM RTPLAN files from a qualified partner's clinical TPS.**
- **Implementation dependencies:** authors report Linux, Python 3.7.5, Gurobi 9.1.2 and optimization through OR-Tools. **Gurobi licensing applies independently of the MIT source license.** Main paper pipeline includes 7,600 optimization model executions; authors caution reproduction can take at least a month on typical machines. **Do not automatically run this full pipeline on WorldShepherd hardware or connected cloud accounts.**
- **Original benchmark partitions:** OpenKBP used 200 training, 40 validation and 100 testing head-and-neck cases; the OpenKBP-Opt paper focuses on the 100 test cases from that challenge and the same associated plan/data population. Avoid treating the 21 predictions for a given patient as 21 independent patients.
- **No biology:** OpenKBP-Opt does NOT contain a validated longitudinal PET hypoxia biomarker in the documented data inventory; do not label CT, target/OAR contours or dose outputs as hypoxia.

## Stage A — zero-download replicability/rights gate

1. Verify and archive exact paper DOI, repository URL, upstream version/commit, `LICENSE`, README, data download/redistribution terms, required citations, and solver licenses.
2. Have data governance confirm whether the actual patient-derived files may be accessed, processed, retained and used for **non-commercial research versus future commercial product development**. No identifying images in public PR/CI. Obtain written authorization when rights are ambiguous.
3. Obtain a qualified clinical physicist's assessment of whether the dose-prediction/fluence-optimization tasks are sufficiently related to the proposed biological-evidence prequalification problem. If they are not, use OpenKBP-Opt only as a *mathematical objective-interface reference*, NOT as a head-to-head BAROS comparator.
4. Pin a limited computing budget, deterministic environment and versioned solver; begin with a tiny permitted subset or aggregate published metrics. Run neither the entire author suite nor user-connected HPC/VM sessions automatically.
5. Preserve all author code license text when required, and explicitly distinguish literature claims from results actually reproduced locally.

## Stage B — independently predeclared planning-interface challenge (conditional)

**Independent party controls:** protocol ID, benchmark population, subject-level split, train/calibration/test separation, permission for data use, physically meaningful clinical reference criteria, and statistically valid case denominators.

**Comparator 1:** an independently reproduced OpenKBP-Opt model / documented mathematical dose mimicking method for objective-translation evaluation. If the computational/licensing cost makes faithful reproduction impractical, record it as such rather than substitute an unrelated weak baseline.

**Comparator 2:** existing clinical TPS + institutional medical-physics QA controls specified by the partner, under its legally approved environment. Public vendors' descriptions are *not* enough to establish exact local functionality.

**BAROS variant A:** identical planning interface with the biological evidence-eligibility contract disabled (but never changing clinical workflow). **BAROS variant B:** same permitted research planning interface with the evidence-eligibility contract enabled. Both must receive identically measured and calibrated biology-state inputs, with independent expert labels. OpenKBP-Opt by itself cannot provide this intervention because it has no longitudinal hypoxia measurements.

**Outputs:** case-matched acceptance/rejection, false-proceed/false-abstention, independent objective/plan quality and clinician-adjudicated constraint violations, with computation/people time, adverse outcomes, exact denominator, confidence intervals and nonconfidential source evidence digest. If any clinical dose is evaluated, an independent physicist establishes the commissioned TPS tolerances BEFORE testing.

**Decisive falsification:** if qualifying evidence fails to prevent new biologically disqualified proposals or merely replicates existing checks at greater cost, stop the product claim. If data rights or biological measurements are unavailable, **do not** claim that a positive OpenKBP numerical result satisfies BAROS's biological adaptation gate.

## Status versus doctors' unresolved criteria

| Requirement | Current evidence | Closure |
|---|---|---|
| Scientific objective translation specified | `baros/research_objective_intent.py` implements dimensionless synthetic priority, incapable of TPS export | **Partial; code boundary only** |
| Legitimate published plan-optimization comparator identified | OpenKBP-Opt paper + MIT author source, actual reported objective-weight/dose-influence methods | **Source identified; not independently executed** |
| External objective/biological comparator achieved | No licensed dataset ingestion, no external investigator, no biomarker, no commissioned TPS | **OPEN** |
| Real novelty beyond existing optimizer and QA | No independent head-to-head experiment, IP review or market evidence | **OPEN** |
| Commercializable product/site/biomarker/TPS and NIH workshare | Programmatic product drafts only; entity/partner/workshare unresolved | **OPEN** |

**Release conditions:** do not merge PR as clinical software, claim patient benefit, send patient data, infer a clinical TPS from academic KBP optimization, promise NIH award, or assert patent novelty. Independent results may be positive, negative or inconclusive and must be preserved.
