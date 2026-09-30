from __future__ import annotations
from dataclasses import dataclass

from interactive_benchmark_runner import EpisodeResult, run_episode
from novel_skill_environments import (
    SwitchCausalityEnv,
    RelabeledSwitchEnv,
)

@dataclass(frozen=True)
class SuiteReport:
    results: tuple[EpisodeResult,...]

    @property
    def mean_score(self) -> float:
        return sum(r.score for r in self.results)/len(self.results) if self.results else 0.0

    @property
    def completion_rate(self) -> float:
        return sum(1 for r in self.results if r.completed)/len(self.results) if self.results else 0.0

def run_mechanics_suite(policy) -> SuiteReport:
    tasks = [
        ("switch_a",SwitchCausalityEnv(
            {"left":"red","right":"blue"},"blue"
        )),
        ("switch_b",SwitchCausalityEnv(
            {"left":"blue","right":"red"},"blue"
        )),
    ]
    results = tuple(
        run_episode(task_id,env,policy,6)
        for task_id,env in tasks
    )
    return SuiteReport(results)

def representation_shift_challenge(policy) -> EpisodeResult:
    env = RelabeledSwitchEnv(
        latent_rule={"left":"red","right":"blue"},
        surface_actions={
            "inspect_orbit":"probe_left",
            "inspect_nadir":"probe_right",
            "choose_orbit":"commit_left",
            "choose_nadir":"commit_right",
        },
        surface_signals={"red":"amber","blue":"violet"},
        target_latent_signal="blue",
    )
    return run_episode("representation_shift",env,policy,6)
