from __future__ import annotations
from dataclasses import dataclass

from interactive_benchmark_runner import TaskStep

@dataclass
class SwitchCausalityEnv:
    rule: dict[str,str]
    target_signal: str
    max_steps: int = 6

    def __post_init__(self):
        self._steps = 0
        self._score = 0.0
        self._last_signal = "unknown"

    def reset(self) -> TaskStep:
        self._steps = 0
        self._score = 0.0
        self._last_signal = "unknown"
        return TaskStep(
            {"last_signal":"unknown","goal":self.target_signal},
            False,
        )

    def actions(self) -> list[str]:
        return ["probe_left","probe_right","commit_left","commit_right"]

    def step(self, action_id: str) -> TaskStep:
        self._steps += 1
        if action_id.startswith("probe_"):
            side = action_id.split("_",1)[1]
            self._last_signal = self.rule[side]
        elif action_id.startswith("commit_"):
            side = action_id.split("_",1)[1]
            signal = self.rule[side]
            self._last_signal = signal
            if signal == self.target_signal:
                self._score = 1.0
                return TaskStep(
                    {"last_signal":signal,"goal":self.target_signal},
                    True,
                )
            return TaskStep(
                {"last_signal":signal,"goal":self.target_signal},
                True,
            )

        terminal = self._steps >= self.max_steps
        return TaskStep(
            {"last_signal":self._last_signal,"goal":self.target_signal},
            terminal,
        )

    def score(self) -> float:
        return self._score

@dataclass
class RelabeledSwitchEnv:
    latent_rule: dict[str,str]
    surface_actions: dict[str,str]
    surface_signals: dict[str,str]
    target_latent_signal: str

    def __post_init__(self):
        self._score = 0.0
        self._last = "unknown"

    def reset(self) -> TaskStep:
        self._score = 0.0
        self._last = "unknown"
        return TaskStep({
            "last_signal":"unknown",
            "goal":self.surface_signals[self.target_latent_signal],
        },False)

    def actions(self) -> list[str]:
        return list(self.surface_actions)

    def step(self, action_id: str) -> TaskStep:
        latent_action = self.surface_actions[action_id]
        kind,side = latent_action.split("_",1)
        latent_signal = self.latent_rule[side]
        surface_signal = self.surface_signals[latent_signal]
        self._last = surface_signal
        if kind == "commit":
            if latent_signal == self.target_latent_signal:
                self._score = 1.0
            return TaskStep({
                "last_signal":surface_signal,
                "goal":self.surface_signals[self.target_latent_signal],
            },True)
        return TaskStep({
            "last_signal":surface_signal,
            "goal":self.surface_signals[self.target_latent_signal],
        },False)

    def score(self) -> float:
        return self._score

@dataclass
class RuleChangeSwitchEnv:
    initial_rule: dict[str,str]
    changed_rule: dict[str,str]
    change_after_probes: int
    target_signal: str

    def __post_init__(self):
        self._probes = 0
        self._changed = False
        self._score = 0.0

    def reset(self) -> TaskStep:
        self._probes = 0
        self._changed = False
        self._score = 0.0
        return TaskStep({
            "last_signal":"unknown",
            "goal":self.target_signal,
            "regime":"initial",
        },False)

    def actions(self) -> list[str]:
        return ["probe_left","probe_right","commit_left","commit_right"]

    def _rule(self):
        return self.changed_rule if self._changed else self.initial_rule

    def step(self, action_id: str) -> TaskStep:
        kind,side = action_id.split("_",1)
        if kind == "probe":
            self._probes += 1
            if self._probes > self.change_after_probes:
                self._changed = True
        signal = self._rule()[side]
        if kind == "commit":
            if signal == self.target_signal:
                self._score = 1.0
            return TaskStep({
                "last_signal":signal,
                "goal":self.target_signal,
                "regime":"changed" if self._changed else "initial",
            },True)
        return TaskStep({
            "last_signal":signal,
            "goal":self.target_signal,
            "regime":"changed" if self._changed else "initial",
        },False)

    def score(self) -> float:
        return self._score
