# WS-QX 0.1 PR Review Checklist

Reviewer should verify:

- code and docs agree on claim-promotion semantics;
- no requested claim state self-authorizes promotion;
- internal, physical, external, standards, and program claims remain distinct;
- tests include negative/adversarial paths;
- semantic data reduction and mission utility remain independent;
- schema/manifest defaults do not claim unearned validation;
- historical PR #266 is treated as historical evidence, not current-main physical qualification;
- exact-head required CI is green before merge;
- merge does not bypass protected-main requirements.
