# BAROS EvidenceGate — competitive and novelty challenge matrix

**2026-11-16 | Public-safe pre-commercial research.** This is an adversarial prior-art screen, NOT a freedom-to-operate opinion, patent search certification, regulatory determination, independent technical comparison, or evidence of market demand.

## Why this screen matters

Dr. Ming Zhao's 2026-11-13 NCI feedback explicitly requests a product that addresses an unmet customer need and shows technical advantage over existing uncertainty, quality and planning safeguards. **A product consisting only of uncertainty thresholds, basic OOD checks, automated QA or auditable logs is not differentiated enough.** The burden is to demonstrate incremental value against meaningful existing methods under independently defined cases.

## Existing methods BAROS must not rebrand as novel

| State of the art | Established result/capability | Risk to a BAROS novelty claim | Falsifiable next evidence |
|---|---|---|---|
| RayStation robust optimization/evaluation | Robust scenario evaluation of setup/density uncertainties, dose–volume goals and detailed plan review | Claiming generic uncertainty-aware planning or robust optimization as innovation is indefensible | Scope different biological-evidence provenance/input quality, show no bypass of TPS safety checks and quantify added *detectable* failures |
| Varian Ethos online adaptive practice | CBCT/synthetic CT, OAR segmentation, adaptive replanning and physical/dosimetric QA; existing safety checks can block unusable plans | Basic triggering/replanning and safety checks already exist | Show an explicitly *external, pre-proposal biological evidence* gate addresses a distinct failure category; independent TPS partner validates usefulness |
| 2026 online ART uncertainty/OOD segmentation research (PMCID PMC12846928) | Uses prediction uncertainty and OOD indicators to identify unreliable segmentation | OOD and uncertainty screening alone are prior art | Test whether **joint, provenance-bound biologic state identifiability + reference validity + abstention** detects cases that uncertainty-only segmentation screening misses |
| Adaptive RT safety ASTRO white paper (2025) | Specifies multidisciplinary governance, QA, credentialed specialists and safety accountability | Human QA and authorization not original inventions | Show complete coverage of explicit evidence-to-decision trace and safe fallback without implying authority to treat |
| Multicentre prospective automation risk analysis (2025) | FMEA/risk analysis highlights low-generalizability models, human handoff and failure points | Generic risk controls/education cannot be patented merely by renaming them | Pre-register error/failure modes in a study with independent clinical physicist adjudication |
| Software chart checking and upstream physics review (2025–26) | Real deployed or evaluated automated chart checks and plan review workflows | Basic pre-treatment automated approval checks are not differentiated | Examine whether biology-specific longitudinal state and uncertainty dependencies make the proposed tool nonredundant |
| Abstention/selective prediction literature | Risk–coverage and false-rejection trade-offs are established | Saying 'abstain on uncertainty' is not technical novelty | Report BOTH critical false-proceed and unnecessary abstention, with cost/workflow burden, across independently authored cases |

## Honest candidate differentiator, to attempt to falsify

A versioned *evidence contract* that binds sequential biological inputs to validated registration/reference identity, quantitative model identifiability, uncertainty calibration, explicit event-time ordering, data provenance, and a reversible abstention/fallback action before TPS proposal. It cannot transfer treatment authority; partner-controlled QA remains required. Novelty must be shown by **incremental failures detected over named baselines**, not by addition of a novel acronym.

## Bounded comparator protocol

For a fixed disease site, single chosen biomarker and TPS workflow:

1. **Method A: trigger-only research proposal.** Declares adaptation on predeclared biological/anatomical trigger even when evidence is poor. Negative straw baseline only; NOT a vendor's clinical decision algorithm.
2. **Method B: uncertainty/OOD-only rejection**, with independently chosen thresholds. A realistic scientific baseline; to be implemented only after tracing literature controls.
3. **Method C: full EvidenceGate**, adding reference/provenance, identifiability, quality gates and explicit proposal/hold decisions.
4. **Method D: abstain-all**, a negative-utility floor. This prevents inflating 'safety' by prohibiting all useful adaptation.
5. **External clinical workflow comparator**, as defined by a qualified partner; not implementable without access to the system, trained staff, and a permitted protocol.

**Primary outcome:** zero safety-disqualified proposals among predeclared independent challenge cases is a *software stop rule*; not a statistically proven clinical reliability rate. Also report proposal coverage, false abstentions, case-level failure attribution, calibration (where applicable), execution cost and workflow burden with actual denominators, uncertainty intervals and independent adjudication.

### Current software-only evidence / limitations

- The repository CI currently exercises 125+ bounded synthetic software tests (including all 32 combinations of five quality-control flags) on the first product-scope candidate.
- A comparator utility and tests (`baros/phase1_evaluation.py`) score a frozen developer-authored 12-case suite against trigger-only and abstain-all policies, reporting Wilson intervals. Results describe *synthetic contract agreement*, not measured patient safety or product superiority.
- **Missing:** method B implemented from a peer-reviewed baseline; independent labels/challenge design; end-user acceptance/utility data; installed and externally governed TPS, external measured dose; evidence of legal commercial dataset use; medical physicist and radiation oncologist support; claim chart and counsel review.

## Decision rule

**DO NOT** call BAROS a new clinical safety system or assert a competitive advantage until independent evaluation establishes (1) measured failure categories not adequately addressed by alternatives, (2) acceptable false-abstention/effort tradeoffs, (3) a real licensed data path, and (4) a buyer who would fund the product. If those fail, re-scope the commercial proposal to a different nonclinical application with distinct market evidence or stop the NCI route.

## Public source bibliography

- https://www.raysearchlabs.com/robustness-in-treatment-planning/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC12005670/ (Ethos end-to-end QA)
- https://pmc.ncbi.nlm.nih.gov/articles/PMC12846928/ (uncertainty/OOD in online ART)
- https://pubmed.ncbi.nlm.nih.gov/39424080/ (ASTRO ART white paper)
- https://pmc.ncbi.nlm.nih.gov/articles/PMC12005333/ (multicentre prospective risk analysis)
- https://pmc.ncbi.nlm.nih.gov/articles/PMC13341639/ (automated chart checking)
- https://pubmed.ncbi.nlm.nih.gov/40164354/ (upstream physics review)
- https://www.nature.com/articles/s41746-026-02882-1 (healthcare abstention review)

No external clinical data, patient identifiers, or security-sensitive information has been committed.
