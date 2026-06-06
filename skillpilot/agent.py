from __future__ import annotations

from skillpilot.agents.core import TraceObserver
from skillpilot.agents.builder import AnswerProvider
from skillpilot.config import AppConfig
from skillpilot.models import AgentRunResult
from skillpilot.pipeline import DecisionObserver, SkillPilotPipeline


class SkillPilotAgent:
    """Small orchestration facade for the skeleton implementation."""

    def __init__(self, config: AppConfig) -> None:
        self.pipeline = SkillPilotPipeline(config)

    def recommend(
        self,
        requirement: str,
        *,
        interactive_builder: bool = False,
        answer_provider: AnswerProvider | None = None,
        decision_observer: DecisionObserver | None = None,
        trace_observer: TraceObserver | None = None,
    ) -> AgentRunResult:
        return self.pipeline.run(
            requirement,
            interactive_builder=interactive_builder,
            answer_provider=answer_provider,
            decision_observer=decision_observer,
            trace_observer=trace_observer,
        )

    def build_skill(
        self,
        requirement: str,
        *,
        interactive_builder: bool = False,
        answer_provider: AnswerProvider | None = None,
        decision_observer: DecisionObserver | None = None,
        trace_observer: TraceObserver | None = None,
    ) -> AgentRunResult:
        return self.pipeline.run(
            requirement,
            force_build_skill=True,
            interactive_builder=interactive_builder,
            answer_provider=answer_provider,
            decision_observer=decision_observer,
            trace_observer=trace_observer,
        )
