# NVIDIA Runtime Evidence Packet — LAB-NV-01 / LAB-NV-02

This packet is the minimum evidence structure for executing WS-NV-01 against real NVIDIA runtimes or hardware.

It is intentionally stricter than a successful demo. A demo may prove that an interface works once; this packet is designed to establish configuration custody, reproducibility, degraded-state behavior, provenance, and explicit operator authorization.

## 1. Evidence package identity

Record:

- package ID;
- UTC campaign start/end;
- operator identity/role;
- reviewer identity/role;
- Worldshepherd/SARA commit SHA;
- WS-NV-01 contract digest;
- host identifier;
- operating system and version;
- evidence storage location;
- manifest digest;
- data classification/sensitivity marking.

Do not place passwords, API keys, bearer tokens, private keys, or confidential partner configuration in the package metadata.

## 2. Required evidence categories

Every surface must provide at least one valid evidence reference for each category before the package is eligible for human review:

1. `runtime_version_inventory`
2. `configuration_digest`
3. `bounded_interface_test`
4. `telemetry_and_provenance`
5. `failure_or_degraded_behavior`
6. `operator_authorization`

WS-NV-01G evaluates completeness only. It never grants VALIDATED status.

## 3. Omniverse Kit — LAB-NV-01A

Capture:

- Kit/runtime version;
- enabled extension/service versions relevant to the test;
- launch mode and headless/service configuration digest;
- Worldshepherd request correlation ID;
- exact WS-NV-01C request payload as an evidence object;
- exact captured service response as an evidence object;
- response status and latency;
- service/application logs covering the exchange;
- one controlled malformed/invalid request;
- one controlled service-unavailable or dependency-failure case when safe;
- recovery behavior;
- operator authorization reference.

Success criterion for interface evidence: an actual Omniverse-backed service accepts the bounded request contract and returns a correlation-preserving response that the offline Worldshepherd parser accepts.

This is **not** sufficient by itself for claim promotion.

## 4. Isaac Sim / ROS 2 — LAB-NV-01B

Capture:

- Isaac Sim version;
- `isaacsim.ros2.bridge` version;
- ROS distribution and middleware when relevant;
- simulation/scenario identifier and configuration digest;
- confirmation of playback state;
- observed ROS 2 topic names and message types;
- observed ROS 2 service names/types where practical;
- correlation strategy between SARA evidence and simulation event;
- timestamps and telemetry;
- one pause/stopped-state observation demonstrating bridge behavior changes as expected;
- one controlled invalid topic/service or unavailable dependency case when safe;
- recovery behavior;
- operator authorization reference.

Worldshepherd must not classify bridge activity as demonstrated unless the observation came from an actual Isaac Sim runtime.

## 5. Jetson Platform Services — LAB-NV-02A

Capture:

- exact Jetson model and module/carrier information when relevant;
- JetPack version;
- Jetson Platform Services version;
- container/runtime versions;
- service inventory;
- selected bounded Platform Service;
- API operation/method/path used for the test;
- request/response status and correlation ID;
- configuration digest;
- service logs/telemetry;
- resource telemetry appropriate to the workload;
- one unavailable/degraded-service test;
- recovery evidence;
- operator authorization reference.

Do not store bearer tokens, API keys, or credentials in request evidence. Redact sensitive headers before evidence capture.

## 6. CUDA — LAB-NV-02B

Capture:

- GPU model;
- NVIDIA driver version;
- CUDA Toolkit/runtime version;
- device compute capability;
- selected deterministic workload description;
- source/input/workload SHA-256 digest;
- configuration digest;
- execution command or bounded invocation metadata with secrets removed;
- result/output SHA-256 digest;
- runtime duration and relevant telemetry;
- second execution using the same frozen workload/configuration;
- repeatability comparison;
- one controlled failure or incompatible-input case;
- operator authorization reference.

The first workload should be non-sensitive, deterministic, small, and easy to independently reproduce. It should prove the evidence path before performance optimization is attempted.

## 7. Provenance requirements

For every evidence object record, where available:

- evidence ID;
- source system;
- producing process/tool;
- capture timestamp in UTC;
- correlation ID;
- configuration/contract digest;
- content digest;
- parent evidence references;
- operator/reviewer reference;
- claims status at time of capture.

Evidence should be immutable or append-only after sealing. Corrections should create a new version rather than silently rewriting a prior result.

## 8. Failure/degraded-state rule

A nominal success case is insufficient. Each surface must demonstrate at least one controlled failure, degraded, unavailable, paused, malformed, or incompatible condition appropriate to that runtime.

Required record:

- expected failure behavior;
- observed behavior;
- whether the Worldshepherd boundary failed closed, failed safe, or merely reported degradation;
- whether provenance remained intact;
- whether human intervention was required;
- recovery procedure and result.

## 9. Promotion review

When all six required evidence categories are populated, run the WS-NV-01G promotion-readiness assessment.

Expected software output for a complete packet:

- `ready_for_human_review: true`
- `auto_promotion_allowed: false`
- `decision: READY_FOR_HUMAN_REVIEW`

The human reviewer then determines whether evidence supports maintaining the current claim, requesting more evidence, or explicitly promoting the capability under Worldshepherd claims controls.

## 10. Non-negotiable boundary

No software function in WS-NV-01 is authorized to change an NVIDIA surface to VALIDATED solely because a packet is complete or a test returned success.

**Evidence completeness → human review.**

**Human review + sufficient reproducible evidence → possible claim promotion.**
