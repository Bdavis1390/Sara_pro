#!/usr/bin/env python3
"""Bounded experience memory populated only from independently adjudicated runs.

The store keeps both successes and failures. Only independently passed, integrity-clean
records are eligible as positive planner exemplars. Failed and blocked experiences are
retained for avoidance context rather than discarded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Sequence, Set


@dataclass(frozen=True)
class ExperienceRecord:
    experience_id: str
    task_family: str
    tags: Set[str]
    strategy_summary: str
    independently_passed: bool
    integrity_clean: bool
    final_evaluator_identity: str
    evidence_hash: str
    failure_summary: str = ""

    def __post_init__(self) -> None:
        if not self.experience_id or not self.task_family or not self.strategy_summary:
            raise ValueError("experience_id, task_family, and strategy_summary are required")
        if not self.final_evaluator_identity or not self.evidence_hash:
            raise ValueError("independent evaluator identity and evidence hash are required")
        if not self.independently_passed and not self.failure_summary:
            raise ValueError("failed experiences require failure_summary")

    @property
    def positive_exemplar(self) -> bool:
        return self.independently_passed and self.integrity_clean


@dataclass
class VerifiedExperienceStore:
    _records: Dict[str, ExperienceRecord] = field(default_factory=dict)

    def add(self, record: ExperienceRecord) -> None:
        existing = self._records.get(record.experience_id)
        if existing is not None and existing != record:
            raise ValueError(f"experience_id conflict: {record.experience_id}")
        self._records[record.experience_id] = record

    def extend(self, records: Iterable[ExperienceRecord]) -> None:
        for record in records:
            self.add(record)

    def query(
        self,
        *,
        task_family: str,
        tags: Sequence[str],
        limit: int = 5,
    ) -> List[ExperienceRecord]:
        if limit <= 0:
            return []
        query_tags = set(tags)

        def score(record: ExperienceRecord):
            family = 1 if record.task_family == task_family else 0
            overlap = len(query_tags.intersection(record.tags))
            positive = 1 if record.positive_exemplar else 0
            # Prefer same-family and overlapping records, then independently clean successes.
            return (family, overlap, positive, record.experience_id)

        candidates = [
            record
            for record in self._records.values()
            if record.task_family == task_family or query_tags.intersection(record.tags)
        ]
        candidates.sort(key=score, reverse=True)
        return candidates[:limit]

    def planner_context(
        self,
        *,
        task_family: str,
        tags: Sequence[str],
        limit: int = 5,
    ) -> List[dict]:
        context = []
        for record in self.query(task_family=task_family, tags=tags, limit=limit):
            context.append(
                {
                    "experience_id": record.experience_id,
                    "task_family": record.task_family,
                    "tags": sorted(record.tags),
                    "strategy_summary": record.strategy_summary,
                    "independently_passed": record.independently_passed,
                    "integrity_clean": record.integrity_clean,
                    "failure_summary": record.failure_summary,
                    "evidence_hash": record.evidence_hash,
                }
            )
        return context
