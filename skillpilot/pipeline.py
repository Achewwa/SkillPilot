from __future__ import annotations

from pathlib import Path

from skillpilot.builders.skill_builder import SkillBuilder
from skillpilot.config import AppConfig
from skillpilot.io.report_writer import RecommendationWriter
from skillpilot.models import AgentRunResult
from skillpilot.modules.stubs import (
    CandidateEvaluator,
    DecisionGate,
    ExtensionTypeClassifier,
    LocalCandidateCache,
    RequirementParser,
    SourcePlanner,
)
from skillpilot.modules.search_tools import SearchExecutor


class SkillPilotPipeline:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.parser = RequirementParser()
        self.classifier = ExtensionTypeClassifier()
        self.planner = SourcePlanner()
        self.search_executor = SearchExecutor(config.search)
        self.cache = LocalCandidateCache(config.data_dir / "candidate_cache.json")
        self.evaluator = CandidateEvaluator()
        self.decision_gate = DecisionGate()
        self.writer = RecommendationWriter(config.outputs_dir)
        self.skill_builder = SkillBuilder(config.generated_skills_dir)

    def run(self, requirement_text: str, force_build_skill: bool = False) -> AgentRunResult:
        requirement = self.parser.parse(requirement_text)
        classification = self.classifier.classify(requirement)
        search_plan = self.planner.plan(requirement, classification)
        search_results = self.search_executor.run(search_plan)
        candidates = self.cache.load()
        evaluations = self.evaluator.evaluate(requirement, classification, candidates)
        decision = self.decision_gate.decide(evaluations)

        if force_build_skill:
            decision.decision_type = "build_custom_skill"
            decision.custom_skill_name = "homework-knowledge-hint"
            decision.reason = "用户显式请求构造 Skill，骨架直接进入 SkillBuilder。"

        skill_draft = None
        if decision.decision_type in {
            "build_custom_skill",
            "recommend_with_custom_extension",
        }:
            skill_draft = self.skill_builder.build_homework_hint_skill()

        report_path = self.config.outputs_dir / "recommendation_report.md"
        trace_path = self.config.outputs_dir / "decision_trace.json"
        self.writer.write_report(
            requirement_text=requirement.raw_text,
            classification_reason=classification.reason,
            decision=decision,
            search_plan=search_plan,
            search_results=search_results,
            report_path=report_path,
        )

        result = AgentRunResult(
            requirement=requirement,
            classification=classification,
            search_plan=search_plan,
            search_results=search_results,
            evaluations=evaluations,
            decision=decision,
            report_path=str(report_path),
            trace_path=str(trace_path),
            skill_draft=skill_draft,
        )
        self.writer.write_trace(result, trace_path=Path(result.trace_path))
        return result
