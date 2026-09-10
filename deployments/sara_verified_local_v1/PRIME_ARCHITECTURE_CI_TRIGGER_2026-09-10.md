# PRIME architecture CI trigger

Purpose: ensure the protected-branch `test-and-build` verification job executes for Worldshepherd PRIME architecture/configuration changes in PR #142.

This file intentionally lives under `deployments/sara_verified_local_v1/**`, the path currently configured to trigger the SARA Verified Local v1 Gate. It does not alter runtime behavior, branch protection, physical capability claims, or deployment configuration.

Claims boundary: passing this software/CI gate establishes only repository-level build/test/evidence behavior. It does not establish physical PRIME, PUMI, PSDM, AERO, HADAL, SUBSPACE, carrier, launch, or SPACE performance.
