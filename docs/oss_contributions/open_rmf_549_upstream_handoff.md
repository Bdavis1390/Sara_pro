# Open-RMF #549 — upstream handoff package

Upstream issue: `open-rmf/rmf_ros2#549`
Reviewed upstream main: `c16cfee2a80065972e191ecad6ad13c29e156baf`
Maintainer signal: **explicitly welcomed contribution**
Claims state: **MAINTAINER-WELCOMED PATCH DRAFT / REQUIRES UPSTREAM BUILD + CONTENTION VALIDATION**

## Current contribution

Canonical current-main patch:

`docs/oss/patches/open-rmf-549-gil-release-minimal-current-main.patch`

The patch is intentionally narrower than the earlier Worldshepherd audit. It touches only the minimum surfaces explicitly named in issue #549:

- `RobotUpdateHandle.replan`
- `update_current_waypoint`
- `update_current_lanes`
- `update_off_grid_position`
- `update_lost_position`
- `set_charger_waypoint`
- `update_battery_soc`
- `cancel_task`
- `create_issue`
- `FleetUpdateHandle.set_task_planner_params`
- `schedule.Participant.set_itinerary`

It does **not** add GIL-release guards to every binding merely because the binding calls C++. Additional surfaces should be added only when blocking/contended behavior is demonstrated.

## Why the binding boundary is the correct first intervention

The reported deadlock requires a Python→C++ call to retain the GIL while waiting for RMF state and a C++ worker to require the GIL while calling a Python `RobotCommandHandle` method.

`py::call_guard<py::gil_scoped_release>()` moves the GIL release to the binding boundary:

```text
Python argument conversion       GIL held
        ↓
construct call_guard             GIL released
        ↓
blocking/native RMF call         GIL released
        ↓
destroy call_guard              GIL reacquired
        ↓
Python return conversion         GIL held
```

This does not alter RMF's internal mutex ordering or scheduling semantics.

## Python callback safety gate

`cancel_task()` carries a Python callback converted to `std::function<void(bool)>`. Before upstream submission, the build/stress validation must prove that the pybind11 callback trampoline reacquires the GIL when RMF invokes it after the outer call released the caller's GIL.

Acceptance condition:

```text
cancel_task() returns or waits without pinning the caller's GIL
AND
on_cancellation executes in Python normally when invoked by RMF
```

If this fails, remove the guard from that binding or provide an explicit trampoline that acquires `py::gil_scoped_acquire` only around the Python callback invocation.

## Existing upstream test scaffolding to reuse

Do not create a parallel simulator. Current upstream already provides:

- `rmf_fleet_adapter_python/scripts/test_loop.py`
- `rmf_fleet_adapter_python/scripts/test_reporting.py`
- `rmf_fleet_adapter_python/scripts/test_interrupt.py`
- `rmf_fleet_adapter_python/scripts/test_utils.py::MockRobotCommand`
- Python binding to `agv::test::MockAdapter`

`MockRobotCommand._timer_cb()` already enters Python repeatedly and calls `RobotUpdateHandle.update_current_waypoint()`. That gives a natural callback/update progress signal.

## Stress reproducer extension

Create a stress variant of `test_loop.py` with two concurrent activity classes:

### Callback/progress thread

Run normal patrol execution through `MockRobotCommand`. Record monotonic counters/timestamps for:

```text
follow_new_path callback
stop callback
MockRobotCommand._timer_cb
update_current_waypoint return
```

### Contending Python thread

After `updater_inserter` exposes the `RobotUpdateHandle`, repeatedly invoke a rotating set of implicated APIs:

```python
updater.replan()
updater.update_battery_soc(0.95)
updater.set_charger_waypoint(charger_index)
issue = updater.create_issue(...)
```

Exercise `cancel_task()` in a separate scenario with a Python completion callback and an existing/controlled task so the callback path is actually executed.

Do not make the test pass merely because calls raise expected task-state errors; it must verify the GIL/progress behavior around the native call.

## Semantic watchdog

Process liveness is explicitly insufficient. Sample every 100 ms and fail a run when either callback or updater progress is silent for more than 3 seconds while work is expected.

Track:

```text
last_python_robot_callback
last_update_call_return
last_robot_timer_callback
last_fleet_state_or_task_progress
process_alive
```

A passing run requires the first four to continue advancing, not only `process_alive=true`.

## Validation tiers

### Tier A — build/API

- build `rmf_fleet_adapter_python` on the target branch/toolchain;
- run existing Python adapter tests;
- confirm the patch applies cleanly to current target SHA;
- verify no binding signature/API change.

### Tier B — short contention

- >=20 repetitions;
- 30–45 seconds each;
- overlapping patrol/callback traffic;
- repeated implicated API calls;
- no >3 s semantic stall.

### Tier C — sustained

- six simulated robots or the largest practical local equivalent;
- >=10 minutes;
- continuous dispatch/callback traffic;
- telemetry/update timestamps remain fresh.

### Tier D — callback-bearing binding

Explicitly validate `cancel_task()` and any other callback-bearing API before keeping its GIL release in the upstream patch.

## What would falsify the patch hypothesis

Do not defend the patch if evidence shows any of the following:

- unpatched code does not reproduce even under the reporter-equivalent stress regime;
- patched code still stalls with the same GIL/mutex signature;
- released calls access Python objects without reacquiring the GIL;
- sanitizer/test failures expose a native lifetime assumption that had previously been serialized by the GIL;
- the actual block is in a different binding or lower layer.

If so, narrow or relocate the fix and preserve the reproduction evidence.

## Submission checklist

Before external PR creation:

1. Re-check #549 for a newly opened reporter/contributor PR.
2. Rebase patch on the actual target branch requested by the maintainer (`humble` versus current `main`).
3. Read current Open-RMF contribution and AI-assistance requirements.
4. Build and run the validation tiers available locally/CI.
5. State exactly what was run; do not imply six-robot sustained validation if only a local short test ran.
6. Reference #549 and the maintainer invitation.

Worldshepherd may currently claim: **current-source-reviewed, maintainer-welcomed minimal patch draft with a defined semantic-progress validation gate.** It may not yet claim the deadlock is fixed upstream.
