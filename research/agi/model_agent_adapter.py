from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

class ModelAgentBackend(Protocol):
    def reset(self, task_id: str) -> None: ...
    def propose_action(
        self,
        observation: dict[str,str],
        available_actions: list[str],
        explicit_state: dict,
    ) -> str: ...
    def observe(
        self,
        action_id: str,
        observation: dict[str,str],
        terminal: bool,
    ) -> None: ...
    def export_explicit_state(self) -> dict: ...

@dataclass
class BackendPolicyAdapter:
    backend: ModelAgentBackend

    def reset(self, task_id: str) -> None:
        self.backend.reset(task_id)

    def act(self, observation: dict[str,str], actions: list[str]) -> str:
        state = self.backend.export_explicit_state()
        action = self.backend.propose_action(observation,actions,state)
        if action not in actions:
            raise ValueError("backend proposed unavailable action")
        return action

    def observe_result(
        self,
        action_id: str,
        observation: dict[str,str],
        terminal: bool,
    ) -> None:
        self.backend.observe(action_id,observation,terminal)
