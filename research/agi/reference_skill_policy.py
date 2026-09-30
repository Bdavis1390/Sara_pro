from __future__ import annotations

class MinimalSwitchPolicy:
    """Reference policy used only to validate benchmark mechanics.

    It deliberately contains task-family-specific logic and therefore must
    never be reported as evidence of general intelligence.
    """

    def __init__(self):
        self.goal = None
        self.seen = {}
        self.task_id = ""

    def reset(self, task_id: str) -> None:
        self.goal = None
        self.seen = {}
        self.task_id = task_id

    def act(self, observation: dict[str,str], actions: list[str]) -> str:
        self.goal = observation.get("goal",self.goal)
        signal = observation.get("last_signal")
        if signal and signal != "unknown" and "pending_probe" in self.seen:
            self.seen[self.seen["pending_probe"]] = signal
            self.seen.pop("pending_probe",None)

        for action in actions:
            if action.startswith("probe_") and action not in self.seen:
                self.seen["pending_probe"] = action
                return action

        for probe,signal in list(self.seen.items()):
            if not probe.startswith("probe_"):
                continue
            if signal == self.goal:
                suffix = probe.split("_",1)[1]
                candidate = f"commit_{suffix}"
                if candidate in actions:
                    return candidate

        # Surface-relabelled tasks are intentionally unsupported by this
        # family-specific baseline unless an external structural adapter maps them.
        return actions[0]

    def observe_result(
        self,
        action_id: str,
        observation: dict[str,str],
        terminal: bool,
    ) -> None:
        signal = observation.get("last_signal")
        if action_id.startswith("probe_") and signal is not None:
            self.seen[action_id] = signal
            self.seen.pop("pending_probe",None)
