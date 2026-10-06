# Curious NerdworX LLC — Federal Eligibility and Readiness Gates

**Status date:** 2026-10-05
**Scope:** operational gating only. This is not legal, tax, certification, or contracting advice and does not substitute for the applicable government system of record.

## Fail-closed status model

Use only these values:

- `VERIFIED` — documentary evidence exists and has been checked.
- `IN_PROGRESS` — action has been initiated but the gate is not yet closed.
- `PENDING_EXTERNAL` — waiting on an authority, registrar, counselor, assessor, partner, or system of record.
- `NOT_STARTED` — no verified initiation exists.
- `NOT_APPLICABLE` — documented reason the gate does not apply.

Unknown must never be upgraded to verified.

## Corporate and federal-registration gates

| Gate | Status | Evidence required before `VERIFIED` | Notes |
|---|---|---|---|
| Curious NerdworX LLC formation | IN_PROGRESS / documentary status must be checked | State formation record and governing records | Repository visibility does not establish legal formation |
| EIN | NOT VERIFIED HERE | IRS-issued EIN record | Do not commit EIN to public repository |
| Business banking | NOT VERIFIED HERE | Bank account under legal entity | Keep account data private |
| Accounting / payroll setup | NOT VERIFIED HERE | Selected system + documented treatment of owner and employees | Owner classification depends on tax election |
| SAM.gov entity registration | NOT VERIFIED HERE | Active SAM record | Registration/renewal evidence belongs in protected business records |
| UEI | NOT VERIFIED HERE | UEI from SAM record | Do not infer from outreach |
| CAGE | NOT VERIFIED HERE | Active CAGE record | Required for several DoD access paths |
| SBA small-business representations | NOT VERIFIED HERE | Current SAM/SBA representations | Verify NAICS-specific size status |
| DSIP / DoD SBIR portal access | NOT VERIFIED HERE | Account + entity mapping | Needed for applicable DoD SBIR/STTR submissions |
| Grants.gov | NOT VERIFIED HERE | Active organization registration / workspace access | Needed for applicable civilian grants |
| Research.gov / NSF account | NOT VERIFIED HERE | Account + organization role | NSF submission path |

## Cyber / CUI gates

| Gate | Status | What Worldshepherd can do internally | What remains external / authoritative |
|---|---|---|---|
| Defined NIST SP 800-171 system boundary | IN_PROGRESS | Architecture, control mapping, evidence collection, SSP precursor | Final boundary must reflect actual people/process/technology and contract context |
| NIST SP 800-171 Basic self-assessment | NOT VERIFIED HERE | Prepare evidence and calculate from verified control implementation | Score and submission must reflect actual environment |
| SPRS posting | NOT VERIFIED HERE | Prepare assessment package | Authorized submission to SPRS |
| CMMC Level 1/2 status | NOT VERIFIED HERE | Prepare controls/evidence | Certification/self-assessment status depends on current rule/contract requirement |
| CUI-capable environment | NOT VERIFIED HERE | Design isolated boundary, logging, access control, backups, evidence | Must actually be implemented and supportable before making the assertion |
| JCP / DD Form 2345 | NOT VERIFIED HERE | Prepare prerequisite checklist | DLA JCP approval is external |
| Data Custodian designation | NOT VERIFIED HERE | Draft role and responsibilities | Must be formally assigned where required |

## Opportunity-specific gates

### SCAR HQ0860-26-S-C008

**Can proceed now:**
- public / non-CUI solicitation analysis;
- non-CUI white-paper development;
- teaming discussions using public information;
- evidence packaging for Worldshepherd's bounded software contribution.

**Do not claim until verified:**
- eligibility to access EXPT/CUI Offeror Library material;
- active DD2345/JCP;
- CMMC/SPRS status;
- CUI-ready system;
- mature antenna/network-platform capability unless supplied by a qualified partner.

### Space Safari SYD89-26-RPO-RLSV

**Can proceed now:**
- bounded subsystem/RFI response using public material;
- partner-oriented mission-assurance / evidence proposal;
- non-CUI software demonstration.

**Do not claim until verified:**
- spacecraft-prime qualification;
- access to protected GFI;
- Handle compatibility;
- flight qualification;
- CUI handling capability.

### xTech / SBIR / STTR

Before submission verify:
- legal entity;
- U.S. small-business eligibility for the specific program;
- ownership/control requirements;
- principal-investigator / employment rules where applicable;
- SAM/UEI/CAGE/DSIP or other portal requirements by the relevant deadline.

### NSF SBIR/STTR

Before full proposal verify:
- Project Pitch invitation when required;
- organization and Research.gov roles;
- small-business eligibility;
- project scope is R&D with a credible commercialization path;
- budget and subaward rules.

## Worldshepherd evidence gate

A proposal may use a technical claim only when all fields below are populated:

```yaml
claim:
  statement: ""
  status: []
  evidence: []
  configuration: ""
  limitations: []
  next_gate: ""
```

Claims without evidence remain omitted or explicitly described as proposed work.

## Owner / employee compensation gate

Do not represent the owner as a W-2 employee unless the tax treatment and payroll structure actually support that classification. Compensation, payroll tax, benefits, and grant/contract charging must follow the legal/tax entity treatment in effect.

## Protected-record rule

Never commit the following to this public repository:

- EIN;
- bank/account numbers;
- SAM security information;
- CAGE/JCP portal credentials;
- CUI or export-controlled documents;
- private partner contact information;
- non-public solicitation attachments;
- tax returns;
- payroll PII;
- signatures;
- identity documents.

Public artifacts may record **status**, **requirements**, and **evidence references** without publishing protected data.
