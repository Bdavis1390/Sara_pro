# Open-RMF #549 — upstream regression scaffold

Status: **TEST DESIGN READY / REQUIRES ROS 2 HUMBLE EXECUTION**

Use existing upstream scaffolding rather than a new simulator:

- `rmf_fleet_adapter_python/scripts/test_loop.py` for graph, fleet, patrol dispatch, and `MockAdapter` setup.
- `rmf_fleet_adapter_python/scripts/test_utils.py` for `MockRobotCommand.follow_new_path()`, `stop()`, and updater behavior.
- `rmf_fleet_adapter_python/scripts/test_reporting.py` for fleet-state observation and `create_issue()`/`IssueTicket.resolve()` usage.

## Required progress signals

Instrument four independent signals:

```text
robot_command_callback_count
last_robot_command_callback_time
update_call_return_count
last_update_call_return_time
fleet_state_update_count
last_fleet_state_update_time
latest_fleet_unix_millis_time
```

A run fails if callbacks or update-call returns remain silent for more than 3 seconds after warm-up, or if fleet telemetry stops advancing while the process remains alive.

## Contention workload

Run six simulated robots with overlapping patrols. In a separate Python thread, repeatedly rotate through the guarded API set:

```text
replan()
update_battery_soc()
update_current_waypoint()
create_issue() -> resolve()
```

Add a separate test for callback-bearing `cancel_task()` so its Python callback is proven to reacquire the GIL correctly.

## Before/after protocol

1. Run the harness on unpatched Humble repeatedly until the reported semantic stall is reproduced or a documented reproduction limit is reached.
2. Apply `docs/oss_contributions/open_rmf_549_gil_release.patch`.
3. Run existing Python/fleet-adapter tests.
4. Run at least 20 short contention repetitions.
5. Run one sustained test of at least 10 minutes.
6. Pass only if callbacks, updater returns, and telemetry all continue progressing.

## Claims rule

Process survival alone is not evidence of success. Until the ROS/RMF execution matrix passes, the contribution remains **PATCH DRAFT / REQUIRES UPSTREAM BUILD+STRESS VALIDATION**.
