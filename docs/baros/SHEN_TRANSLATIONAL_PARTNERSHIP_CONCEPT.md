# BAROS Translational Partnership Concept — Dr. Chenyang Shen / UT Southwestern

Status: **PROPOSED COLLABORATION — NOT YET AGREED**

## Purpose

Establish an academic–industrial translational partnership to determine, through independent medical-physics and clinical evidence, whether BAROS can progress from a bounded research-software framework toward a clinically credible radiotherapy technology.

This document is not an endorsement request. It is a proposed division of scientific responsibility, validation authority, and sponsored-project work.

## Why this partnership is technically well matched

BAROS requires expertise in intelligent treatment planning, numerical optimization, adaptive radiotherapy workflows, physical dosimetry, clinical workflow integration, and independent validation. Dr. Chenyang Shen's published research interests and clinical medical-physics background overlap directly with those needs.

## Proposed roles

### Worldshepherd / BAROS side

- maintain and harden the executable BAROS research architecture;
- maintain requirements traceability, software verification, provenance, failure logging, and claims-control gates;
- implement research interfaces for DICOM-RT/TPS exchange and external dose-engine comparison;
- provide solver, optimization, robustness, and audit tooling;
- prepare reproducible study builds and analysis pipelines;
- support sponsor, regulatory, commercialization, and engineering documentation;
- preserve a strict separation between research results and clinical claims.

### UT Southwestern / academic medical-physics side — proposed

- determine whether the initial intended use is clinically meaningful and sufficiently narrow;
- independently review and, where needed, reject or revise BAROS mathematical/biological assumptions;
- define the reference TPS, delivery system, commissioning measurements, and clinical-physics acceptance criteria;
- design or co-design retrospective and prospective validation protocols;
- independently adjudicate dose-accuracy and clinically material failure criteria;
- lead or co-lead institutional IRB / research-governance interactions as applicable;
- participate in publications, conference presentations, and grant submissions according to actual contribution;
- retain scientific independence to publish negative or limiting findings.

## Initial Specific Aims concept

### Aim 1 — Technical and dosimetric validation

Lock one intended-use configuration and compare BAROS-generated research plans against a validated TPS/dose-calculation workflow using independent measured-dose and end-to-end tests. Quantify absolute dose error, spatial dose agreement, clinically relevant DVH differences, hard-constraint violations, failure localization, and robustness under realistic perturbations.

**Promotion condition:** technical/dosimetric claims remain blocked until independent measurements satisfy predeclared acceptance criteria.

### Aim 2 — Retrospective clinical-planning evaluation

On held-out, appropriately governed retrospective cases, compare BAROS with the clinical planning comparator using predeclared target-coverage, OAR, deliverability, robustness, planning-time, and physician/physicist review endpoints.

**Promotion condition:** clinical-effectiveness language remains indication-specific and comparative. No universal treatment-success claim is permitted.

### Aim 3 — Prospective translational validation

If Aims 1–2 justify continuation, execute prospective shadow-mode evaluation and then, only with required regulatory/IRB authorization, an interventional clinical study designed around patient-relevant endpoints, safety monitoring, and predefined stopping rules.

**Promotion condition:** prospective clinical claims require the applicable study, statistical, regulatory, and independent-replication evidence.

## 98.7% evidence objective

The program target is not a single blended score. Safety, physical dose accuracy, clinical effectiveness, and successful treatment-process use must each be separately demonstrated for a locked intended-use population and configuration.

For genuinely binary independent endpoints with zero failures, an exact one-sided binomial lower bound above 0.987 requires at least:

- 229/229 successes at 95% confidence;
- 282/282 at 97.5% confidence;
- 352/352 at 99% confidence;
- 528/528 at 99.9% confidence.

These counts do **not** replace disease-specific power calculations or comparative-effectiveness design.

## Funding concept

### Primary near-term candidate

**NIH/NCI PAR-25-337 — Academic-Industrial Partnerships for Translation of Technologies for Diagnosis and Treatment (R01; Clinical Trial Optional).**

The mechanism requires at least one academic and one industrial organization, supports translation and validation, permits clinical trials when translational validation is the purpose, allows up to $499,000 in direct costs per year for up to five years, and permits investigators to apportion effort and budget according to project requirements. The next new-application receipt date is October 5, 2026.

### Parallel / alternate routes

- NCI SBIR/STTR investigator-initiated mechanisms;
- NCI radiation-research / SBIR opportunities involving AI-assisted treatment planning;
- institutional pilot or translational research funding;
- foundation or cancer-center innovation funding;
- later-stage commercialization and regulatory-development mechanisms if preliminary external evidence is favorable.

## Workshare and financial principles

Any award or sponsored-project funds should be divided between participating organizations according to an agreed statement of work, personnel effort, facilities, indirect-cost requirements, milestones, and sponsor rules. No personal side-payment or informal revenue-sharing arrangement is proposed.

Intellectual property, inventorship, licensing, publication rights, data rights, commercialization rights, and background-IP boundaries should be handled separately through written institutional agreements and should reflect actual contributions and applicable law/policy.

## Independence / credibility safeguards

- UT Southwestern investigators must remain free to report negative findings.
- BAROS claims cannot be promoted solely because a partner participates.
- Independent measurement and blinded/held-out evaluation should be used where practical.
- Protocols, endpoints, acceptance criteria, and statistical analysis should be predeclared before outcome evaluation.
- Any financial conflict of interest must be disclosed and managed under institutional and sponsor rules.
- Clinical care remains governed by validated clinical systems until all applicable external gates are satisfied.

## First decision meeting

The first collaboration discussion should resolve only three decisions:

1. **Initial intended use:** Which disease site / planning problem / delivery platform is the most scientifically defensible first target?
2. **Minimum credibility experiment:** What independent TPS + measurement experiment would Dr. Shen require before BAROS merits retrospective clinical testing?
3. **Funding structure:** Is PAR-25-337, SBIR/STTR, or another institutional mechanism the best first joint submission route?

A positive answer to those three questions would justify a jointly authored validation protocol, workshare, budget, and specific-aims page. A negative answer should be documented as actionable technical evidence and used to revise or stop the corresponding BAROS claim.
