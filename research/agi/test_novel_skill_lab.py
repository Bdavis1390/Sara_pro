import unittest

from interactive_benchmark_runner import run_episode
from novel_skill_environments import SwitchCausalityEnv, RelabeledSwitchEnv
from novel_skill_suite import run_mechanics_suite, representation_shift_challenge
from reference_skill_policy import MinimalSwitchPolicy

class NovelSkillLabTests(unittest.TestCase):
    def test_family_specific_reference_solves_base_mechanics(self):
        report = run_mechanics_suite(MinimalSwitchPolicy())
        self.assertEqual(report.mean_score,1.0)

    def test_surface_shift_defeats_family_specific_reference(self):
        result = representation_shift_challenge(MinimalSwitchPolicy())
        self.assertLess(result.score,1.0)

    def test_episode_rejects_unavailable_action(self):
        class Bad:
            def reset(self,task_id): pass
            def act(self,observation,actions): return "not_available"
            def observe_result(self,*args): pass
        env = SwitchCausalityEnv(
            {"left":"red","right":"blue"},"blue"
        )
        with self.assertRaises(ValueError):
            run_episode("bad",env,Bad(),3)

    def test_relabelled_environment_preserves_latent_rule(self):
        env = RelabeledSwitchEnv(
            {"left":"red","right":"blue"},
            {
                "look_a":"probe_left",
                "look_b":"probe_right",
                "take_a":"commit_left",
                "take_b":"commit_right",
            },
            {"red":"x","blue":"y"},
            "blue",
        )
        step = env.reset()
        self.assertEqual(step.observation["goal"],"y")
        step = env.step("look_b")
        self.assertEqual(step.observation["last_signal"],"y")
        step = env.step("take_b")
        self.assertEqual(env.score(),1.0)

if __name__ == "__main__":
    unittest.main()
