# BAROS — Direct Technical Responses to Radiation-Physics Review Questions

**2026-11-17 | Nonconfidential technical clarification | Research-stage, no clinical or TPS validation.** This document addresses the three specific questions raised by the academic radiation-physics reviewer in September. It does **not** claim that the reviewer has accepted the responses or agreed to collaborate.

## 1. What is new versus existing adaptive, automated and biology-guided RT?

**Already established in the field:** clinical adaptive radiotherapy, biology-guided planning, LQ/TCP/NTCP concepts, robust optimization, DICOM-RT handling, uncertainty/OOD screening, selective abstention, human QA and commercial TPS safeguards. BAROS does not claim ownership, invention or physical discovery of any of these.

**Testable candidate engineering contribution:** a *single longitudinal evidence-to-research-objective eligibility contract* that requires both timepoints to be qualified, binds data/model/trigger decisions to a replayable digest, rejects unidentifiable, high-uncertainty, OOD, low-quality or geometrically unqualified observations, and prevents those observations from issuing a planning-intent output while preserving the last-governed research plan identity. An abstract synthetic priority-intent mapper is downstream of the decision gate. This is a specific architectural/implementation hypothesis; **it is NOT yet proved novel or superior to vendor/institutional workflows**.

**Falsification:** if a fair, faithfully implemented uncertainty/OOD and clinical-physics comparator detects the same meaningful errors at equal or better eligible-proposal coverage, usability, throughput and cost, BAROS cannot claim a material technical advantage. Independent published-method comparison, user interviews and independent clinical-physics evaluation remain OPEN.

## 2. What exactly is biological adaptation, what inputs exist, what triggers it, and how do outputs change?

**The present input is caller-supplied estimated research state**, not a PET-to-hypoxia inference product. `baros/closed_loop.py` defines prior/current `BiologicalState` arrays for research alpha (per Gy), beta (per Gy squared), dimensionless hypoxia/resistance indices, uncertainty, measurement quality, geometry qualification, model identifiability and OOD flag, plus anatomy/motion metadata. Array values in verified tests are **synthetic**. No validated FMISO acquisition, tracer normalization, dose-response calibration, image-registration accuracy or clinically identified voxel-state model exists.

**Trigger semantics:** strictly advancing integer phase index, equal state dimensions and finite values are required. Relative comparison uses the maximum **absolute** difference for hypoxia, resistance and uncertainty arrays; anatomy and motion use configured thresholds. A numerically zero change does not trigger solely because a threshold is set to zero. Manual-force requests still cannot bypass qualification.

**Qualification:** both old and new states must individually pass geometry/identifiability/OOD, measurement quality and maximum uncertainty tests. If either fails, BAROS returns HOLD_LAST_VALID or FALLBACK_STANDARD without a research adaptation proposal. Passing permits only PROPOSE_REOPTIMIZATION as **software status**; all treatment authority remains false.

**Current executable planning intent, not a therapy plan:** `baros/research_objective_intent.py` demonstrates for **synthetic region identifiers only** a dimensionless positive-priority increment:

`Δpriority_i = min(cap, gain × max(0, hypoxia_index_i(t) − hypoxia_index_i(t−1)))`.

Both `gain` and `cap` are configurable unvalidated toy research constants in [0,1]. The calculation is made only if the prior/current biological observations pass qualification and a hypoxia-change trigger exists; other triggers alone do not imply a biological priority increase. The returned record explicitly has `dose_or_prescription_defined=False`, `tps_export_allowed=False`, and `treatment_authority=False`. It has **no Gy units** and does not specify a clinical objective weight, optimization constraint, organ-at-risk dose, target dose, machine field, fractionation or a medical directive. Its only value today is to make a possible transfer contract examinable and falsifiable.

**What is NOT implemented:** a biological observation/measurement model, patient-level prior distribution, prospective outcome prediction, biologically valid objective-to-dose translation, commissioned TPS optimization API, actual dose accumulation/registration or a clinically deliverable plan. These require an investigator-selected use case and real assay/physics evidence; claims that they are already present would be false.

## 3. Which TPS, machines, images and delivery platforms are supported?

**Current support: NONE for a commissioned clinical TPS or delivery machine.** BAROS has self-authored synthetic DICOM-RT geometry/reference parsing tests but **no vendor-specific plan adapter, commissioned TPS integration, approved photon/proton technique, human patient model, or clinical RTPLAN output**. RayStation/Ethos are referenced as established competitive platforms, not as BAROS integrations.

**Current boundary:** `synthetic observations -> validate phase and measurement -> assess research trigger -> qualify both states -> propose/hold research status -> optional abstract synthetic priority intent -> STOP`. Future, separately authorized clinical-physics and hospital-owned workflow would be `specified biomarker and plan context -> qualified clinician/physicist -> version-locked TPS reoptimization and independent calculation -> medical-physics QA/phantom acceptance -> human clinical decision`. BAROS presently implements NONE of those clinical steps.

**First experiment required to progress:** an independent academic physics team selects exactly one indication/biomarker/TPS/version/machine and legally permitted data/phantom fixtures, freezes actual objective semantics and acceptance tolerances, then runs independent challenge and dosimetry comparisons. HNSCC + serial FMISO PET is a discussion candidate; usable paired data and repeatability are unknown. An unsuitable signal should be **rejected**, not substituted with a different PET tracer without protocol revision.

## Evidence and remaining scientific decisions

- Frozen internal engineering snapshot: GitHub commit `d1dfd1f7936991c506f5904fa9b56fabc5d06926` passed **258 bounded tests, two warnings**, including the first research-only objective-intent regression tests. Developer-controlled synthetic verification is not a clinical sample.
- The short conventional methods manuscript is a separate draft and requires scientific, references and IP review before external publication.
- Original +5% synthetic dose perturbation constraint failure remains disclosed.
- Independent model validity, meaningful competitor advantage, licensed data, commissionable TPS workflow, physical dosimetry, regulatory categorization and medical authority remain external **STOP** gates.

**Bottom line:** The reviewer can now inspect explicit code and finite input/output semantics for what is *present*. A scientifically compelling treatment-planning result **still requires independent experimental evidence**. No claim of peer-review acceptance, institutional collaboration, FDA exemption or grant approval is made.

**Evidence:** https://github.com/Bdavis1390/Sara_pro/pull/565 ; `docs/baros/BAROS_INDEPENDENT_EVALUATION_PREREGISTRATION_TEMPLATE_2026-11-17.md` ; `docs/baros/BAROS_NCI_COMPETITOR_PRIOR_ART_CHALLENGE_2026-11-16.md`.
