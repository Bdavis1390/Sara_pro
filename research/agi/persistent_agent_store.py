from __future__ import annotations
from dataclasses import asdict
from hashlib import sha256
import json

from agent_state_capsule import AgentStateCapsule
from causal_world_model import CausalHypothesis, CausalHypothesisSet
from skill_memory import Skill, SkillLibrary, SkillState

SNAPSHOT_SCHEMA_VERSION = 1

def _skill_to_dict(skill: Skill) -> dict:
    return {
        "skill_id": skill.skill_id,
        "task_family": skill.task_family,
        "description": skill.description,
        "preconditions": skill.preconditions,
        "expected_effects": skill.expected_effects,
        "confidence": skill.confidence,
        "evidence_refs": skill.evidence_refs,
        "falsifiers": skill.falsifiers,
        "authorized_scopes": skill.authorized_scopes,
        "state": skill.state.value,
        "successes": skill.successes,
        "failures": skill.failures,
    }

def serialize_agent_state(
    state: AgentStateCapsule,
    skills: SkillLibrary,
    world_model: CausalHypothesisSet | None,
) -> str:
    state.validate()
    payload = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "state": asdict(state),
        "skills": [_skill_to_dict(s) for s in skills.skills.values()],
        "world_model": None,
    }
    if world_model is not None:
        world_model.validate()
        payload["world_model"] = {
            "hypotheses": {
                hid: {
                    "hypothesis_id": h.hypothesis_id,
                    "action_effects": {
                        action: dict(effects)
                        for action,effects in h.action_effects.items()
                    },
                    "evidence_refs": list(h.evidence_refs),
                }
                for hid,h in world_model.hypotheses.items()
            },
            "probabilities": world_model.probabilities,
            "update_history": world_model.update_history,
        }
    canonical = json.dumps(payload,sort_keys=True,separators=(",",":"))
    fingerprint = sha256(canonical.encode()).hexdigest()
    envelope = {"fingerprint":fingerprint,"payload":payload}
    return json.dumps(envelope,sort_keys=True)

def deserialize_agent_state(blob: str) -> tuple[
    AgentStateCapsule, SkillLibrary, CausalHypothesisSet | None
]:
    envelope = json.loads(blob)
    payload = envelope["payload"]
    canonical = json.dumps(payload,sort_keys=True,separators=(",",":"))
    actual = sha256(canonical.encode()).hexdigest()
    if actual != envelope["fingerprint"]:
        raise ValueError("snapshot fingerprint mismatch")
    if payload.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise ValueError("unsupported snapshot schema")

    state = AgentStateCapsule(**payload["state"])
    state.validate()

    library = SkillLibrary()
    for row in payload["skills"]:
        skill = Skill(
            skill_id=row["skill_id"],
            task_family=row["task_family"],
            description=row["description"],
            preconditions=dict(row["preconditions"]),
            expected_effects=dict(row["expected_effects"]),
            confidence=float(row["confidence"]),
            evidence_refs=list(row["evidence_refs"]),
            falsifiers=list(row["falsifiers"]),
            authorized_scopes=list(row["authorized_scopes"]),
            state=SkillState(row["state"]),
            successes=int(row["successes"]),
            failures=int(row["failures"]),
        )
        library.add(skill)

    wm = payload["world_model"]
    model = None
    if wm is not None:
        hypotheses = {
            hid:CausalHypothesis(
                hypothesis_id=row["hypothesis_id"],
                action_effects=row["action_effects"],
                evidence_refs=tuple(row["evidence_refs"]),
            )
            for hid,row in wm["hypotheses"].items()
        }
        model = CausalHypothesisSet(
            hypotheses=hypotheses,
            probabilities={
                k:float(v) for k,v in wm["probabilities"].items()
            },
            update_history=list(wm["update_history"]),
        )
        model.validate()

    return state,library,model
