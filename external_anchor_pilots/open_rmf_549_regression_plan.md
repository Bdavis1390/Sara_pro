# Open-RMF #549 — deterministic regression plan

Upstream: `open-rmf/rmf_ros2#549`
Target: `rmf_fleet_adapter_python` (`humble`)
Status: contribution-ready test design; requires ROS 2 / RMF execution environment

## Failure contract

The regression is not simply "the process did not crash." The reported failure mode leaves the process and DDS/C++ threads alive while Python robot-update activity and callback execution freeze. The test therefore needs independent progress signals.

A passing run MUST demonstrate all of the following for the entire stress interval:

1. Python `RobotCommandHandle` callbacks continue to execute.
2. Python-side robot update loops continue to advance.
3. `RobotUpdateHandle.replan()` and the other guarded calls return within a bounded interval.
4. Fleet state timestamps continue to advance.
5. No watchdog interval contains a simultaneous callback-progress and telemetry-progress stall.

## Workload shape

Use the existing `MockAdapter`, graph, battery, and `MockRobotCommand` patterns from `scripts/test_loop.py` and `scripts/test_utils.py` to minimize new test scaffolding.

Create six robots. Dispatch a long-running patrol/loop workload so RMF workers repeatedly call into Python `follow_new_path()` / `stop()` while a Python stress thread concurrently invokes the affected update-handle APIs.

Pseudo-flow:

```python
adapter = adpt.MockAdapter("GilReleaseRegression")
fleet = build_existing_test_fleet(adapter)
robots = [add_robot(f"T{i}") for i in range(6)]
adapter.start()

dispatch_long_patrols(robots)

stop_event = threading.Event()
progress = ProgressCounters()

threading.Thread(target=stress_update_handles,
                 args=(robots, progress, stop_event),
                 daemon=True).start()

run_rclpy_executor_and_watchdog(progress, stop_event, duration=30.0)
```

The stress worker should rotate through operations that are explicitly guarded by the patch:

```python
while not stop_event.is_set():
    for robot in robots:
        updater = robot.updater
        updater.replan()
        updater.update_battery_soc(0.95)
        updater.update_current_waypoint(robot.current_waypoint, 0.0)
        ticket = updater.create_issue(
            adpt.robot_update_handle.Tier.Info,
            "gil-regression",
            {"sequence": progress.calls},
        )
        ticket.resolve({"reason": "test"})
        progress.calls += 1
```

Instrument the command handle callbacks:

```python
class ProgressRobotCommand(MockRobotCommand):
    def follow_new_path(self, *args):
        self.progress.callback_count += 1
        self.progress.last_callback = time.monotonic()
        return super().follow_new_path(*args)

    def stop(self):
        self.progress.stop_count += 1
        self.progress.last_callback = time.monotonic()
        return super().stop()
```

Track the last successful Python-side updater operation as well:

```python
progress.last_update_return = time.monotonic()
```

## Watchdog

A watchdog must run independently from the stress worker. Recommended thresholds for CI:

- sample interval: 100 ms
- maximum callback silence while patrols are active: 3 s
- maximum updater-call return silence: 3 s
- overall test timeout: 45 s

Failure message should distinguish:

- `CALLBACK_STALL`
- `UPDATE_CALL_STALL`
- `TELEMETRY_STALE`
- `PROCESS_EXIT`

The test should fail on semantic progress loss even if the process is alive.

## Before/after expectation

### Before GIL-release patch

Under sufficient callback/update contention, the reproducer is expected to eventually reach the reported inversion:

```text
Python thread owns GIL -> enters bound RMF call -> waits on RMF worker/mutex
RMF worker owns/needs RMF state -> invokes Python callback -> waits on GIL
```

The watchdog should report simultaneous callback/update stagnation without requiring a process crash.

### After patch

The Python caller releases the GIL while executing the selected C++ binding. An RMF worker that needs to execute a Python callback can therefore acquire the GIL and make progress.

## Upstream acceptance sequence

1. Confirm the unpatched branch can reproduce the watchdog failure under repeated runs.
2. Apply `open_rmf_549_gil_release.patch`.
3. Run existing `rmf_fleet_adapter_python` pytest suite.
4. Run this stress harness repeatedly (recommended >= 20 CI/local repetitions).
5. Run one sustained >= 10-minute six-robot test.
6. Confirm callback-bearing methods such as `cancel_task()` correctly reacquire the GIL through the `std::function` trampoline.
7. Submit patch and regression evidence to #549.

## Claims boundary

This document defines the regression criteria and workload. It does not claim that the deadlock has been reproduced or eliminated in the Worldshepherd CI environment, because that environment does not currently execute a ROS 2 Humble/RMF integration stack.
