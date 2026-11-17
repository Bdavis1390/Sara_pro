# BAROS EvidenceGate — Product-Oriented NCI Phase I Specific Aims v3

**Draft, November 17, 2026. Nonconfidential; not submitted, funded, clinically validated, or supported by a committed institution.**

### Product and commercial problem

BAROS EvidenceGate is a **research-only, pre-treatment-planning-system (pre-TPS) evidence-qualification module**. It checks whether longitudinal biological observations are sufficiently reliable to justify a **research replanning proposal** or require abstention and preservation of the governed plan identity. Its potential buyer is an academic radiation-oncology/medical-physics research team or TPS technology provider. Whether existing systems leave a real commercial gap is **unproven**.

**Candidate first use:** head-and-neck research photon IMRT, one institution-selected TPS and a single biological measurement. Serial 18F-FMISO PET hypoxia is a **candidate**, not an available or calibrated dataset; the clinical partner must confirm or reject it. A 2024 specialist-reader study found material interreader variability before training, and baseline-to-on-treatment change is not the same experiment as test–retest reproducibility. BAROS now screens declared mock reader concordance and acquisition protocol integrity and holds FMISO-specific proposals on a current negative interpretation or absent positive synthetic priority. These conservative developer-defined checks are **not clinical FMISO validity or a treatment rule**. FDG PET must not be presented as an equivalent hypoxia measurement.

**Differentiator to test:** a versioned *longitudinal evidence contract* binding prior/current measurement quality, identifiability, uncertainty, geometry, source provenance, reasoned abstention, replayable decisions and bounded, **abstract research objective intent**. The software does **not** invent adaptive planning, QA, uncertainty assessment or radiobiological dose-response models and cannot generate a clinical prescription, a deliverable RTPLAN, a TPS command or treatment authorization. Novelty requires independent comparisons.

### Aim 1 — Prototype engineering and independent software feasibility

Develop a frozen, auditable API from qualified biological inputs to **propose/hold/fallback/no adaptation**, evidence record and, only for synthetic research cases, explicit dimensionless region-priority changes. Current internal background evidence: **286 passing bounded software tests and two warnings** at GitHub commit `832060f0d79754d9b490f627d17f044dd18698b4`; no external or clinical validity is inferred.

**Proposed go/no-go criteria:** an evaluator independently freezes a minimum of **100 new synthetic/phantom challenge cases** (provisional count), with disqualifying and eligible conditions and reference labels withheld until predictions are committed. **Zero permitted proposals on prespecified critical-disqualification cases**, **zero treatment-authority grants**, and complete case-denominator, false-abstention, qualified-proposal recall, decision latency and risk–coverage reporting. Any critical bypass is STOP. Include a **fair, published-method uncertainty/OOD comparator**, plus trigger-only and always-abstain controls. Developer toy comparisons are not independent clinical evidence; no target safety rate is claimed.

### Aim 2 — Conditional partner-controlled planning/physics feasibility

A qualified radiation-oncology/medical-physics team must first select and authorize **one site–biomarker–TPS/version–machine workflow**, legally permitted mock/biological data, physics criteria and institutional scope. The partner independently specifies DICOM-RT geometry/reference checks, objective translation, TPS dose recalculation and any mock-phantom measurement and deliverability thresholds. BAROS remains upstream; physical dose calculation and all clinical authority remain external. **Any material silent dose/geometry, identity or clinical hard-constraint failure is STOP.** No real-patient adaptation, intervention or outcome claim is proposed.

### Phase I readiness and commercialization milestones

Before claiming product demand: conduct **five structured independent buyer/user interviews** and document existing solutions, failures, integration burden, budget owner, willingness to evaluate/pay, and negative findings. An acknowledgment is not a sales commitment.

An eligible applicant and realistic research workshare are also required. The contemplated LLC is **not formed**, but NIH recognizes qualifying **sole proprietorships** as possible small-business legal forms; eligibility, ownership/control, registration and PI terms must be checked, not assumed. Explore **STTR PA-27-102** if a nonprofit research partner must perform substantial work (≥40% business and ≥30% institution), versus **SBIR PA-27-100** if the business can perform at least two-thirds of Phase I R&D and satisfy PI employment. Document IP rights, budget, a signed institutional scope and a qualified FDA/intended-use review before claiming a clinically commercializable device. No application, filing, expenditure or rights transfer is authorized.

**External hard dependencies:** willing independent physician/physicist, legally accessible biomarker/planning data, versioned TPS, physical QA, fair comparative result, buyer evidence and eligible business structure. The listed next standard receipt date is **January 5, 2027**; BAROS is **not ready to submit** until these gates are evidenced.

**References:** [NIH program structure](https://seed.nih.gov/small-business-funding/small-business-program-basics/understanding-sbir-sttr); [NIH eligibility policy, revised March 2026](https://www.grants.nih.gov/grants/policy/nihgps/HTML5/section_18/18.5.2_eligibility.htm); [NCI current parent announcements](https://sbir.cancer.gov/small-business-funding/grants/omnibus-solicitation); [Research PR #565](https://github.com/Bdavis1390/Sara_pro/pull/565).

*Pre-existing WorldShepherd IP remains with its owner. This draft confers no license, clinical authority, grant eligibility determination or institutional participation.*
