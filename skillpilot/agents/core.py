from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from skillpilot.models import (
    AgentSkillTraceEvent,
    CandidateEvaluation,
    Decision,
    ParsedRequirement,
    RetrievedContent,
    SearchPlan,
    SearchResult,
    SkillDraftResult,
    TypeClassification,
)


TraceObserver = Callable[[AgentSkillTraceEvent], None]


@dataclass
class PipelineContext:
    requirement_text: str
    force_build_skill: bool = False
    requirement: ParsedRequirement | None = None
    classification: TypeClassification | None = None
    search_plan: SearchPlan | None = None
    search_results: list[SearchResult] = field(default_factory=list)
    retrieved_contents: list[RetrievedContent] = field(default_factory=list)
    evaluations: list[CandidateEvaluation] = field(default_factory=list)
    decision: Decision | None = None
    skill_draft: SkillDraftResult | None = None
    report_path: Path | None = None
    trace_path: Path | None = None
    trace_events: list[AgentSkillTraceEvent] = field(default_factory=list)
    trace_observer: TraceObserver | None = None

    def require_requirement(self) -> ParsedRequirement:
        if self.requirement is None:
            raise RuntimeError("Requirement has not been parsed yet.")
        return self.requirement

    def require_classification(self) -> TypeClassification:
        if self.classification is None:
            raise RuntimeError("Extension type has not been classified yet.")
        return self.classification

    def require_search_plan(self) -> SearchPlan:
        if self.search_plan is None:
            raise RuntimeError("Search plan has not been created yet.")
        return self.search_plan

    def require_decision(self) -> Decision:
        if self.decision is None:
            raise RuntimeError("Decision has not been created yet.")
        return self.decision

    def record(
        self,
        agent: str,
        skill: str,
        *,
        status: str = "success",
        summary: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        event = AgentSkillTraceEvent(
            agent=agent,
            skill=skill,
            status=status,  # type: ignore[arg-type]
            summary=summary,
            metadata=metadata or {},
        )
        self.trace_events.append(event)
        if self.trace_observer is not None:
            self.trace_observer(event)
