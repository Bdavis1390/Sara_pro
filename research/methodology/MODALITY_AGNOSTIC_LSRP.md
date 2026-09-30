# Modality-Agnostic Layered Systems Reasoning Protocol

## The original lesson generalized

The same correction that improved analysis of a symbolic image applies to every information-bearing object:

**Surface content is only one layer of evidence.**

A high-quality analysis must preserve and inspect the relationships that make the object part of a system.

## Universal evidence envelope

For any object E:

E = {
  content,
  structure,
  relations,
  sequence,
  state,
  provenance,
  transformations,
  context,
  interfaces,
  scale,
  measurements,
  uncertainties,
  dependencies,
  hypotheses,
  falsifiers
}

No single field is assumed sufficient.

## Examples by modality

### Text

Do not analyze only words.

Also inspect:
- paragraph/discourse structure;
- reference chains;
- chronology;
- source lineage;
- omitted/supplied material;
- version changes;
- contradictions;
- rhetorical role;
- translation/transcription dependencies.

### Software

Do not analyze only source files.

Also inspect:
- import/dependency graph;
- runtime state;
- configuration;
- API/schema version;
- permissions;
- data flow;
- deployment topology;
- failure propagation;
- observability evidence;
- security boundary assumptions.

### Scientific data

Do not analyze only values.

Also inspect:
- units;
- calibration;
- instrument;
- sampling design;
- missingness;
- preprocessing;
- annotation/version;
- temporal order;
- batch effects;
- causal model;
- uncertainty;
- null distribution.

### Biology

Do not analyze only sequence identity.

Also inspect:
- annotation;
- structure;
- regulation;
- tissue/context;
- interaction networks;
- temporal expression;
- evolutionary constraint;
- phenotype linkage;
- assay limitations.

### Medicine

Do not analyze only an isolated classification.

Also inspect:
- source/version;
- review status;
- evidence strength;
- population;
- date;
- patient context when legitimately available;
- conflicting submissions;
- guidelines;
- downstream decision dependency.

### Law

Do not analyze only quoted text.

Also inspect:
- jurisdiction;
- authority;
- publication/revision state;
- procedural posture;
- holding vs dicta;
- later treatment;
- statutory/regulatory dependencies;
- exact version of controlling language.

### Intelligence

Do not analyze only conclusions.

Also inspect:
- source quality;
- source independence;
- assumptions;
- confidence;
- alternative hypotheses;
- indicators;
- chronology;
- deception possibilities;
- dependency graph;
- what would change the judgment.

### Security telemetry

Do not analyze only alerts.

Also inspect:
- event sequence;
- host/user/service relationships;
- baseline behavior;
- network graph;
- privilege transitions;
- process ancestry;
- timing;
- provenance;
- sensor blind spots;
- adversary alternatives.

### Finance / operations

Do not analyze only totals.

Also inspect:
- transaction provenance;
- timing;
- recurrence;
- category uncertainty;
- transfers vs income/outflow;
- account coverage;
- partial-period state;
- dependencies and commitments.

### Audio / speech

Do not analyze only transcript.

Also inspect:
- timing;
- prosody;
- acoustic spectrum;
- speaker turn structure;
- confidence/noise;
- channel effects;
- linguistic context.

### Geospatial

Do not analyze only coordinates.

Also inspect:
- network connectivity;
- travel constraints;
- terrain;
- temporal accessibility;
- jurisdiction;
- proximity vs reachability;
- uncertainty/resolution.

## Discovery and validation remain separate

Discovery engine:
- broad;
- relational;
- cross-domain;
- hypothesis-generating.

Validation engine:
- provenance-first;
- chronology-aware;
- quantitative;
- null-controlled;
- falsification-driven.

The system should maximize discovery **subject to a strict claim-promotion ceiling**.

## Universal non-conflation rule

correspondence
!= intent
!= provenance
!= mechanism
!= causation
!= quantitative relationship
!= validated capability
!= proof

## Operational rule

When a task arrives, the first representation chosen by the interface is not automatically the correct representation for reasoning.

The system should ask:

**What information was lost when this object was rendered into the form I am currently seeing?**

That question is now mandatory across Worldshepherd.
