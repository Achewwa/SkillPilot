from __future__ import annotations

from skillpilot.config import AppConfig
from skillpilot.models import AgentRunResult
from skillpilot.pipeline import SkillPilotPipeline


class SkillPilotAgent:
    """Small orchestration facade for the skeleton implementation."""

    def __init__(self, config: AppConfig) -> None:
        self.pipeline = SkillPilotPipeline(config)

    def recommend(self, requirement: str) -> AgentRunResult:
        return self.pipeline.run(requirement)

    def build_skill(self, requirement: str) -> AgentRunResult:
        return self.pipeline.run(requirement, force_build_skill=True)
