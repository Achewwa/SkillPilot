from __future__ import annotations

from pathlib import Path

from skillpilot.builders.builder_agent import AnswerProvider, SkillBuilderAgent
from skillpilot.config import AppConfig
from skillpilot.io.report_writer import RecommendationWriter
from skillpilot.llm import create_llm
from skillpilot.models import AgentRunResult, SearchResult
from skillpilot.modules.readers import ContentReader
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
        llm = create_llm(config.llm)
        self.parser = RequirementParser(llm)
        self.classifier = ExtensionTypeClassifier()
        self.planner = SourcePlanner()
        self.search_executor = SearchExecutor(config.search)
        self.content_reader = ContentReader(config.search)
        self.cache = LocalCandidateCache(config.data_dir / "candidate_cache.json")
        self.evaluator = CandidateEvaluator(llm if config.llm.enable_evaluation else None)
        self.decision_gate = DecisionGate()
        self.writer = RecommendationWriter(config.outputs_dir)
        self.skill_builder = SkillBuilderAgent(
            config.generated_skills_dir,
            llm,
            config.builder.max_clarification_rounds,
        )

    def run(
        self,
        requirement_text: str,
        force_build_skill: bool = False,
        *,
        interactive_builder: bool = False,
        answer_provider: AnswerProvider | None = None,
    ) -> AgentRunResult:
        requirement = self.parser.parse(requirement_text)
        classification = self.classifier.classify(requirement)
        search_plan = self.planner.plan(requirement, classification)
        if force_build_skill:
            search_results = []
            retrieved_contents = []
            evaluations = []
            decision = self.decision_gate.build_custom(
                "用户显式请求构造 Skill，直接进入 SkillBuilder Agent。"
            )
        else:
            search_results = self.search_executor.run(search_plan)
            retrieved_contents = self.content_reader.read(search_results)
            evaluations = self.evaluator.evaluate_retrieved(
                requirement,
                classification,
                retrieved_contents,
            )
            if not evaluations and self._should_use_offline_cache(search_results):
                evaluations = self.evaluator.evaluate(
                    requirement,
                    classification,
                    self.cache.load(),
                )
            decision = self.decision_gate.decide(evaluations)

        skill_draft = None
        if decision.decision_type in {
            "build_custom_skill",
            "recommend_with_custom_extension",
        }:
            skill_draft = self.skill_builder.build(
                requirement,
                classification,
                decision,
                evaluations,
                interactive=interactive_builder and self.config.builder.interactive,
                answer_provider=answer_provider,
            )
            if skill_draft.builder_session and skill_draft.builder_session.spec:
                decision.custom_skill_name = skill_draft.builder_session.spec.slug

        report_path = self.config.outputs_dir / "recommendation_report.md"
        trace_path = self.config.outputs_dir / "decision_trace.json"
        self.writer.write_report(
            requirement_text=requirement.raw_text,
            classification_reason=classification.reason,
            decision=decision,
            requirement=requirement,
            search_plan=search_plan,
            search_results=search_results,
            retrieved_contents=retrieved_contents,
            skill_draft=skill_draft,
            report_path=report_path,
        )

        result = AgentRunResult(
            requirement=requirement,
            classification=classification,
            search_plan=search_plan,
            search_results=search_results,
            retrieved_contents=retrieved_contents,
            evaluations=evaluations,
            decision=decision,
            report_path=str(report_path),
            trace_path=str(trace_path),
            skill_draft=skill_draft,
            builder_session=skill_draft.builder_session if skill_draft else None,
        )
        self.writer.write_trace(result, trace_path=Path(result.trace_path))
        return result

    def _should_use_offline_cache(self, search_results: list[SearchResult]) -> bool:
        if not search_results:
            return True
        return all(result.status == "skipped" for result in search_results)
