from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field, model_validator

from .qualification import CapabilityStatus, canonical_digest


ASTRA_PROFILE_ID = "WS-ASTRA-SOLVER-READ-ONLY"
DEFAULT_OPENAI_MODEL = "gpt-5.6-sol"


class AstraExecutionMode(str, Enum):
    SOLVER_READ_ONLY = "SOLVER_READ_ONLY"


class AstraRuntimeConfig(BaseModel):
    """Runtime configuration for the Worldshepherd Astra solver profile.

    `Astra` is a Worldshepherd profile/codename. It is deliberately separated
    from the provider model id so an undocumented model name cannot silently
    become an API dependency.
    """

    profile_id: str = ASTRA_PROFILE_ID
    provider: str = "openai"
    model_id: str = DEFAULT_OPENAI_MODEL
    mode: AstraExecutionMode = AstraExecutionMode.SOLVER_READ_ONLY
    network_enabled: bool = False
    allowed_tools: list[str] = Field(default_factory=list)
    store_remote_response: bool = False

    @model_validator(mode="after")
    def validate_read_only_boundary(self) -> "AstraRuntimeConfig":
        if self.mode != AstraExecutionMode.SOLVER_READ_ONLY:
            raise ValueError("only SOLVER_READ_ONLY is implemented")
        return self


class AstraInferenceAuthorization(BaseModel):
    authorization_id: str = Field(min_length=1)
    authorized_by: str = Field(min_length=1)
    allow_model_inference: bool = False
    allowed_model_ids: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    scope: str = "MODEL_INFERENCE_ONLY"


class AstraTask(BaseModel):
    task_id: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    requested_tools: list[str] = Field(default_factory=list)
    claims_control_labels: list[CapabilityStatus] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AstraPreparedRequest(BaseModel):
    profile_id: str
    task_id: str
    provider: str
    model_id: str
    mode: AstraExecutionMode
    input_digest: str
    evidence_refs: list[str]
    requested_tools: list[str]
    request_payload: dict[str, Any]
    prepared_utc: str
    network_call_performed: bool = False


class AstraResult(BaseModel):
    profile_id: str
    task_id: str
    provider: str
    model_id: str
    response_id: str | None = None
    input_digest: str
    output_digest: str
    output_text: str
    evidence_refs: list[str]
    claims_control_labels: list[CapabilityStatus]
    uncertainty_notes: list[str] = Field(default_factory=list)
    disconfirming_evidence: list[str] = Field(default_factory=list)
    recommended_follow_on: list[str] = Field(default_factory=list)
    authorization_id: str
    authorized_by: str
    network_call_performed: bool
    completed_utc: str


AstraTransport = Callable[[dict[str, Any]], dict[str, Any]]


class AstraSolver:
    """Policy-gated adapter for the Worldshepherd Astra solver profile.

    The adapter has no network implementation of its own. A transport must be
    injected explicitly, and inference remains blocked unless both runtime
    configuration and a SARA authorization allow it.
    """

    def __init__(
        self,
        config: AstraRuntimeConfig | None = None,
        *,
        transport: AstraTransport | None = None,
    ) -> None:
        self.config = config or AstraRuntimeConfig()
        self._transport = transport

    def _validate_requested_tools(
        self,
        task: AstraTask,
        authorization: AstraInferenceAuthorization | None = None,
    ) -> None:
        configured = set(self.config.allowed_tools)
        requested = set(task.requested_tools)
        outside_profile = requested - configured
        if outside_profile:
            raise PermissionError(
                "requested tools are outside the Astra profile allowlist: "
                + ", ".join(sorted(outside_profile))
            )
        if authorization is not None:
            outside_authorization = requested - set(authorization.allowed_tools)
            if outside_authorization:
                raise PermissionError(
                    "requested tools are outside the inference authorization: "
                    + ", ".join(sorted(outside_authorization))
                )

    def prepare(self, task: AstraTask) -> AstraPreparedRequest:
        self._validate_requested_tools(task)
        task_payload = task.model_dump(mode="json")
        input_digest = canonical_digest(task_payload)
        request_payload: dict[str, Any] = {
            "model": self.config.model_id,
            "instructions": (
                "Operate as the Worldshepherd Astra solver profile. "
                "Analyze and propose only. Preserve evidence references and claims-control "
                "labels. Do not claim that model output upgrades physical or operational "
                "maturity. Do not perform or request external actions."
            ),
            "input": task.prompt,
            "store": self.config.store_remote_response,
            "metadata": {
                "worldshepherd_profile": self.config.profile_id,
                "worldshepherd_task_id": task.task_id,
                "worldshepherd_input_digest": input_digest,
            },
        }
        return AstraPreparedRequest(
            profile_id=self.config.profile_id,
            task_id=task.task_id,
            provider=self.config.provider,
            model_id=self.config.model_id,
            mode=self.config.mode,
            input_digest=input_digest,
            evidence_refs=list(task.evidence_refs),
            requested_tools=list(task.requested_tools),
            request_payload=request_payload,
            prepared_utc=datetime.now(timezone.utc).isoformat(),
            network_call_performed=False,
        )

    def execute(
        self,
        task: AstraTask,
        authorization: AstraInferenceAuthorization | None,
    ) -> AstraResult:
        if not self.config.network_enabled:
            raise PermissionError("Astra network inference is disabled by runtime policy")
        if authorization is None or not authorization.allow_model_inference:
            raise PermissionError("explicit SARA model-inference authorization is required")
        if self.config.model_id not in set(authorization.allowed_model_ids):
            raise PermissionError("configured model is outside the inference authorization")
        if authorization.scope != "MODEL_INFERENCE_ONLY":
            raise PermissionError("authorization scope must be MODEL_INFERENCE_ONLY")
        self._validate_requested_tools(task, authorization)
        if self._transport is None:
            raise RuntimeError("no Astra transport is configured")

        prepared = self.prepare(task)
        raw_response = self._transport(prepared.request_payload)
        output_text = _extract_output_text(raw_response)
        output_digest = canonical_digest(
            {
                "task_id": task.task_id,
                "model_id": self.config.model_id,
                "output_text": output_text,
                "raw_response_digest": canonical_digest(raw_response),
            }
        )
        return AstraResult(
            profile_id=self.config.profile_id,
            task_id=task.task_id,
            provider=self.config.provider,
            model_id=self.config.model_id,
            response_id=(
                str(raw_response.get("id")) if raw_response.get("id") is not None else None
            ),
            input_digest=prepared.input_digest,
            output_digest=output_digest,
            output_text=output_text,
            evidence_refs=list(task.evidence_refs),
            claims_control_labels=list(task.claims_control_labels),
            authorization_id=authorization.authorization_id,
            authorized_by=authorization.authorized_by,
            network_call_performed=True,
            completed_utc=datetime.now(timezone.utc).isoformat(),
        )


def _extract_output_text(response: dict[str, Any]) -> str:
    direct = response.get("output_text")
    if isinstance(direct, str) and direct:
        return direct

    collected: list[str] = []
    output = response.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                text = part.get("text")
                if isinstance(text, str) and text:
                    collected.append(text)
    if not collected:
        raise ValueError("model response did not contain output text")
    return "\n".join(collected)
