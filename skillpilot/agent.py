from __future__ import annotations

from skillpilot.builders.builder_agent import AnswerProvider
from skillpilot.config import AppConfig
from skillpilot.models import AgentRunResult
from skillpilot.pipeline import SkillPilotPipeline


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
    ) -> AgentRunResult:
        return self.pipeline.run(
            requirement,
            interactive_builder=interactive_builder,
            answer_provider=answer_provider,
        )

    def build_skill(
        self,
        requirement: str,
        *,
        interactive_builder: bool = False,
        answer_provider: AnswerProvider | None = None,
    ) -> AgentRunResult:
        return self.pipeline.run(
            requirement,
            force_build_skill=True,
            interactive_builder=interactive_builder,
            answer_provider=answer_provider,
        )
