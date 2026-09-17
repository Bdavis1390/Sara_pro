#!/usr/bin/env python3
"""Explicit WS-QPHONON experiment lifecycle state machine."""

from __future__ import annotations

from dataclasses import dataclass

STATES = {
    "DRAFT",
    "CHARACTERIZE",
    "READY_FOR_PRIME",
    "READY_FOR_HUMAN_APPROVAL",
    "EXECUTION_ALLOWED",
    "RUNNING",
    "COMPLETED",
    "ABORTED",
}

ALLOWED = {
    "DRAFT": {"CHARACTERIZE", "ABORTED"},
    "CHARACTERIZE": {"READY_FOR_PRIME", "ABORTED"},
    "READY_FOR_PRIME": {"CHARACTERIZE", "READY_FOR_HUMAN_APPROVAL", "ABORTED"},
    "READY_FOR_HUMAN_APPROVAL": {"CHARACTERIZE", "EXECUTION_ALLOWED", "ABORTED"},
    "EXECUTION_ALLOWED": {"CHARACTERIZE", "RUNNING", "ABORTED"},
    "RUNNING": {"COMPLETED", "ABORTED"},
    "COMPLETED": set(),
    "ABORTED": set(),
}


@dataclass(frozen=True)
class TransitionDecision:
    allowed: bool
    current: str
    target: str
    reasons: list[str]


def transition(
    current: str,
    target: str,
    *,
    prime_passed: bool = False,
    human_approval_verified: bool = False,
) -> TransitionDecision:
    reasons: list[str] = []
    if current not in STATES:
        reasons.append("CURRENT_STATE_INVALID")
    if target not in STATES:
        reasons.append("TARGET_STATE_INVALID")
    if reasons:
        return TransitionDecision(False, current, target, reasons)

    if target not in ALLOWED[current]:
        reasons.append("TRANSITION_NOT_ALLOWED")

    if target == "READY_FOR_HUMAN_APPROVAL" and prime_passed is not True:
        reasons.append("PRIME_PASS_REQUIRED")

    if target == "EXECUTION_ALLOWED":
        if prime_passed is not True:
            reasons.append("PRIME_PASS_REQUIRED")
        if human_approval_verified is not True:
            reasons.append("HUMAN_APPROVAL_REQUIRED")

    return TransitionDecision(not reasons, current, target, reasons)
