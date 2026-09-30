# Worldshepherd V23 — GitHub Action Pin No-Regression Gate

## State

**IMPLEMENTED IN SOFTWARE / REVIEW CANDIDATE**

V23 begins the repository-wide GitHub Actions reference hardening program without converting the existing floating-reference backlog into an all-or-nothing migration.

## Policy

For pull requests, V23 fails closed when the proposed head:

1. introduces a new external `uses:` reference that is not pinned to an immutable 40-hex Git commit SHA;
2. changes a previously exact-pinned GitHub Action target in the same workflow back to a floating reference; or
3. introduces a Docker action reference that is not digest-pinned with `@sha256:`.

Local repository actions such as `./.github/actions/...` are not external supply-chain fetches and are accepted as local.

Pre-existing floating references remain explicit remediation backlog. Their existence does not make a PR fail unless the PR expands that backlog.

## Why staged enforcement

The repository contains multiple historical workflows that use floating major tags such as `actions/checkout@v4`, `actions/checkout@v7`, `actions/setup-python@v5`, and `actions/setup-python@v7`.

Rewriting all of them in one change would combine unrelated workflow behavior changes, complicate rollback, and make failures harder to attribute. V23 therefore establishes a monotonic **no-regression boundary** first. Subsequent batches can pin existing workflows to reviewed commit SHAs while this gate prevents backsliding.

## Claims boundary

A V23 PASS means only that the evaluated change did not add a new floating external Action reference or downgrade an exact pin. It does **not** prove that every historical workflow is immutable, that the referenced third-party code is trustworthy, or that the repository has achieved supply-chain certification.

Existing backlog must be reduced in controlled review units.
