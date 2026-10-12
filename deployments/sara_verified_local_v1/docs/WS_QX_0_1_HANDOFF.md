# WS-QX 0.1 Protected-Main Handoff

Candidate branch: `ws-qx-evidence-01`.

Handoff sequence:
1. open pull request against protected `main`;
2. capture exact head SHA;
3. wait for required CI on that exact head;
4. inspect failures and make only corrective changes;
5. after any correction, repeat exact-head CI verification;
6. review claims matrix and release attestation;
7. merge only through normal branch protection; never bypass required checks;
8. after merge, verify resulting main commit and update publication state from release candidate to repository-published software only.

A merge does not change physical/external/program claim states.
