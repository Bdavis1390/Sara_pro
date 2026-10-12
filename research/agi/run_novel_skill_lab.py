from __future__ import annotations
import json

from reference_skill_policy import MinimalSwitchPolicy
from novel_skill_suite import run_mechanics_suite, representation_shift_challenge

def main() -> int:
    policy = MinimalSwitchPolicy()
    base = run_mechanics_suite(policy)
    shifted = representation_shift_challenge(policy)
    report = {
        "warning": (
            "Reference policy is family-specific and validates benchmark mechanics only. "
            "It is not AGI evidence."
        ),
        "base_mean_score":base.mean_score,
        "base_completion_rate":base.completion_rate,
        "representation_shift_score":shifted.score,
        "representation_shift_completed":shifted.completed,
    }
    print(json.dumps(report,indent=2,sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
