from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Protocol

@dataclass(frozen=True)
class TaskStep:
    observation: dict[str,str]
    terminal: bool

class InteractiveEnvironment(Protocol):
    def reset(self) -> TaskStep: ...
    def actions(self) -> list[str]: ...
    def step(self, action_id: str) -> TaskStep: ...
    def score(self) -> float: ...

class AgentPolicy(Protocol):
    def reset(self, task_id: str) -> None: ...
    def act(self, observation: dict[str,str], actions: list[str]) -> str: ...
    def observe_result(
        self,
        action_id: str,
        observation: dict[str,str],
        terminal: bool,
    ) -> None: ...

@dataclass(frozen=True)
class EpisodeResult:
    task_id: str
    score: float
    actions_taken: int
    completed: bool

def run_episode(
    task_id: str,
    env: InteractiveEnvironment,
    policy: AgentPolicy,
    action_budget: int,
) -> EpisodeResult:
    if action_budget <= 0:
        raise ValueError("action_budget must be positive")
    policy.reset(task_id)
    step = env.reset()
    if step.terminal:
        return EpisodeResult(task_id,env.score(),0,True)

    taken = 0
    while taken < action_budget:
        available = env.actions()
        action = policy.act(step.observation,available)
        if action not in available:
            raise ValueError("agent selected unavailable action")
        step = env.step(action)
        taken += 1
        policy.observe_result(action,step.observation,step.terminal)
        if step.terminal:
            return EpisodeResult(task_id,env.score(),taken,True)

    return EpisodeResult(task_id,env.score(),taken,False)
