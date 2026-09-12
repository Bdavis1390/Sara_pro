# Open-RMF #549 — Python binding GIL boundary audit

Upstream: `open-rmf/rmf_ros2#549`
Target: `rmf_fleet_adapter_python` on ROS 2 Humble
Claims state: **PATCH DRAFT REVIEW / REQUIRES UPSTREAM BUILD + CONTENTION VALIDATION**

## Maintainer signal

The upstream maintainer explicitly welcomed a contribution on issue #549. No competing GIL-release PR was found in the current repository scan.

## Failure mechanism under review

The reported inversion is:

```text
Python caller owns GIL
  -> enters bound RMF method
  -> waits on RMF worker/mutex

RMF worker owns/needs RMF state
  -> invokes Python RobotCommandHandle callback
  -> waits on GIL
```

The required property is not merely process survival. Callback progress, updater-call progress, and fleet telemetry must continue advancing.

## Canonical patch surface

The canonical draft is `docs/oss_contributions/open_rmf_549_gil_release.patch` because it includes the schedule participant path in addition to the `RobotUpdateHandle` methods.

### Guard in first patch

| Binding | Reason | Validation emphasis |
|---|---|---|
| `interrupted` / `replan` | Explicitly implicated by #549; may wait on worker state | concurrent Python callback progress |
| `update_current_waypoint` | Position update can contend with RMF state | timer-driven callback + updater loop |
| `update_current_lanes` | Same update path family | lane update under callback saturation |
| `update_off_grid_position` | Same update path family | off-grid update under callback saturation |
| `update_lost_position` | Same update path family | lost-position update under callback saturation |
| `update_position(StartSet)` | Same update path family | start-set update under callback saturation |
| `set_charger_waypoint` | Explicitly listed by issue | repeated setter under active fleet |
| `update_battery_soc` | Explicitly listed by issue | high-rate battery update |
| `create_issue` | Explicitly implicated by report | create/resolve tickets while callbacks fire |
| `cancel_task` | Explicitly listed; carries Python callback | prove callback trampoline reacquires GIL |
| `set_task_planner_params` | Explicitly listed by issue | build-time/runtime safety; no Python work inside released region |
| `Participant.set_itinerary` | Explicitly listed by issue | itinerary update under schedule contention |

## Do not expand without evidence

The first upstream PR should remain narrow. These bindings may deserve later audit, but they should not be changed in the first patch unless profiling/reproduction shows the same blocking property:

```text
override_status
log_info / log_warning / log_error
interrupt
kill_task
submit_direct_request
unstable_* accessors
FleetUpdateHandle add/open/close-lane helpers
```

Adding `gil_scoped_release` everywhere increases review surface and can expose lifetime assumptions unnecessarily.

## Python-object safety review

`py::call_guard<py::gil_scoped_release>()` is suitable only when the underlying C++ call does not directly use Python APIs during the released region.

Required checks:

1. pybind argument conversion completes before the guard releases the GIL.
2. return-value conversion occurs after the guard has reacquired the GIL.
3. Python callbacks carried as `std::function` reacquire the GIL when invoked.
4. no borrowed Python object/reference is dereferenced by C++ while the GIL is released.
5. object lifetime is retained for the duration of the native call.

`cancel_task()` therefore needs an explicit regression case: its `on_cancellation` Python callable must execute correctly while the outer bound method has released the caller's GIL.

## Regression acceptance matrix

| Scenario | Unpatched expectation | Patched requirement |
|---|---|---|
| patrol callbacks + repeated `replan()` | possible GIL/RMF inversion | no semantic stall |
| callbacks + `create_issue()` | possible contention | callback and update counters advance |
| callbacks + waypoint/battery updates | possible contention | telemetry timestamps remain fresh |
| `cancel_task()` Python callback | may participate in inversion | callback executes and returns normally |
| six robots, sustained load | issue reports fleet-wide freeze | no simultaneous callback/update stall |
| process/PID check only | can remain green falsely | insufficient to pass |

## Watchdog signals

A run is passing only while all active signals stay within threshold:

```text
last_robot_command_callback
last_update_call_return
last_fleet_state_timestamp
process_alive
```

Suggested CI thresholds from the regression plan:

```text
sample interval: 100 ms
callback silence threshold: 3 s
updater-call silence threshold: 3 s
overall short test: 30-45 s
repetitions: >= 20
sustained validation: >= 10 min
```

## Submission gate

Move from `PATCH DRAFT` to `UPSTREAM_READY` only after:

- Humble build succeeds;
- existing adapter tests pass;
- unpatched branch reproduces the semantic stall at least once under the defined harness;
- patched branch survives repeated short runs and one sustained run;
- callback-bearing bindings are explicitly exercised;
- patch is rebased on the upstream target branch and formatting/lint checks pass.

Until those conditions are met, Worldshepherd may claim a **maintainer-welcomed patch draft and regression design**, not a proven fix.
