# External reviewer outreach protocol

## Objective

Obtain a technically useful objection, reproduction result, or architecture critique from a high-signal systems reviewer without implying endorsement, creating social pressure, or wasting the reviewer's time.

The primary target may be Linus Torvalds, but this protocol applies equally to other senior open-source systems reviewers.

## Gate before any message

Do not send the review request unless:

1. the final review-branch head has passed the external-review CI gate;
2. existing repository-required checks on that head are green;
3. the root README is reviewer-first;
4. known security findings from the pre-outreach hostile review are either fixed or explicitly documented;
5. the message links directly to the narrow review surface;
6. no sentence implies that the reviewer is already associated with Worldshepherd.

## The first ask

The first ask is **criticism**, not partnership.

The useful questions are:

- Is the proposal/authorization/evidence/visibility separation a real systems boundary or unnecessary ceremony?
- Which abstraction should be deleted?
- Which trust boundary is false or bypassable?
- Is the evidence model useful, or does it create false assurance?
- What existing infrastructure should replace custom Worldshepherd code?

A negative answer can be a successful review result.

## Message constraints

The first contact should:

- fit comfortably on one screen;
- contain one repository URL;
- require no attachment;
- make no claim of certification, endorsement, relationship, or urgency;
- make the local-only/non-arbitrary-execution boundary clear;
- explicitly permit a one-sentence objection;
- state that no follow-up is expected if the recipient has no time.

Do not lead with a company biography, defense opportunity list, speculative research, funding ask, partnership economics, or a catalogue of Worldshepherd programs. Those are irrelevant until the technical artifact earns attention.

## Contact frequency

One unsolicited direct message is the default maximum.

Do not send repeated reminders merely because there is no response. Silence is not interest, rejection, approval, or validation.

A later contact is justified only by a material new event, such as:

- the reviewer explicitly invites follow-up;
- the project fixes a flaw the reviewer identified;
- Worldshepherd produces an upstream contribution directly relevant to the reviewer's maintained project;
- a mutual technical collaborator introduces the project;
- the recipient publicly asks for work in exactly this problem space.

## Partnership threshold

Do not introduce a partnership proposal until the reviewer independently signals technical interest.

A partnership discussion becomes reasonable only after at least one of these occurs:

- substantive code or architecture feedback;
- a request to continue the discussion;
- a suggestion that a component belongs upstream or in an existing foundation/project;
- an introduction to a maintainer/community where the work is relevant;
- an explicit request for a collaboration proposal.

Even then, describe the relationship only by what has actually happened.

## Parallel community route

Do not make the strategy dependent on one famous individual replying.

In parallel, seek review from communities working on open agent infrastructure, trust, identity, authorization, security, governance, and interoperability. The goal is to accumulate reproducible criticism and upstream-compatible improvements, not endorsements.

A strong outcome is that several independent maintainers can reproduce the narrow SARA target and identify the same useful boundary. That evidence is more durable than a name attached to a pitch.

## Response handling

If a reviewer replies:

1. preserve the exact technical objection;
2. convert it into a reproducible issue/test where appropriate;
3. label the claim or assumption affected;
4. fix the smallest correct layer;
5. rerun the complete review gate;
6. reply with the commit/test that addresses the objection rather than a narrative defense.

If the objection demonstrates that a Worldshepherd component is unnecessary, deletion or simplification is an acceptable resolution.

## Success criteria

Success is not "Linus likes Worldshepherd."

Success is one or more of:

- a falsified assumption;
- a reproducible defect;
- a simpler architecture;
- an upstream integration path;
- independent reproduction;
- a credible request for continued technical discussion.

Partnership is downstream of those outcomes, never a substitute for them.
