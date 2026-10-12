# WS-QX Evidence Classes

WS-QX uses explicit evidence classes to prevent ambiguous readiness language.

- SOURCE_THESIS: requirement, paper, theory, partner statement, or other source proposition; not implementation evidence.
- GOVERNED_REPO_INTAKE: source has been recorded with provenance and claims boundary.
- IMPLEMENTED_IN_SOFTWARE: code/configuration exists; does not imply tested performance.
- INTERNAL_REPRODUCIBLE_TEST: a bounded internal test is repeatable with retained evidence.
- CONTROLLED_SIMULATION_BENCH: controlled simulation/emulation/bench evidence; physical scope must be stated.
- PHYSICAL_COUPON_HARDWARE: bounded physical evidence on identified hardware/configuration.
- EXTERNAL_BLIND_TEST: externally executed or independently controlled test with acceptable provenance.
- INDEPENDENT_REPLICATION: independent reproduction under declared conditions.

Separate claim-control labels such as SUPPORTED_BY_LITERATURE, SIMULATED_ONLY, REQUIRES_LAB_VALIDATION, REQUIRES_PARTNER_VALIDATION, and NOT_CURRENTLY_CLAIMED may coexist with these evidence classes. Evidence class describes what evidence exists; claim labels describe what Worldshepherd is allowed to say about capability.
