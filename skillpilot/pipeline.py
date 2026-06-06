from __future__ import annotations

from collections.abc import Callable

from skillpilot.agents.core import PipelineContext
from skillpilot.agents.builder import AnswerProvider, SkillBuilderAgent
from skillpilot.agents.decision import DecisionAgent
from skillpilot.agents.discovery import SourceDiscoveryAgent
from skillpilot.agents.evaluation import CandidateEvaluationAgent
from skillpilot.agents.report import ReportAgent
from skillpilot.agents.requirement import RequirementAnalysisAgent
from skillpilot.config import AppConfig
from skillpilot.llm import create_llm
from skillpilot.models import AgentRunResult
from skillpilot.skills.cache import LocalCandidateCache
from skillpilot.skills.classification import ExtensionTypeClassifier
from skillpilot.skills.decision import DecisionGate
from skillpilot.skills.discovery.readers import ContentReader
from skillpilot.skills.discovery.search_tools import SearchExecutor
from skillpilot.skills.evaluation import CandidateEvaluator
from skillpilot.skills.planning import SourcePlanner
from skillpilot.skills.report import RecommendationWriter
from skillpilot.skills.requirement import RequirementParser

DecisionObserver = Callable[[PipelineContext], None]


class SkillPilotPipeline:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        llm = create_llm(config.llm)
        self.parser = RequirementParser(llm)
        self.classifier = ExtensionTypeClassifier(llm)
        self.planner = SourcePlanner(llm)
        self.search_executor = SearchExecutor(config.search)
        self.content_reader = ContentReader(config.search)
        self.cache = LocalCandidateCache(config.data_dir / "candidate_cache.json")
        self.evaluator = CandidateEvaluator(llm if config.llm.enable_evaluation else None)
        self.decision_gate = DecisionGate(llm)
        self.writer = RecommendationWriter(config.outputs_dir)
        self.skill_builder = SkillBuilderAgent(
            config.generated_skills_dir,
            llm,
            config.builder.max_clarification_rounds,
        )
        self.requirement_agent = RequirementAnalysisAgent(
            self.parser,
            self.classifier,
            self.planner,
        )
        self.discovery_agent = SourceDiscoveryAgent(
            self.search_executor,
            self.content_reader,
        )
        self.evaluation_agent = CandidateEvaluationAgent(
            self.evaluator,
            self.cache,
        )
        self.decision_agent = DecisionAgent(self.decision_gate)
        self.report_agent = ReportAgent(self.writer, config.outputs_dir)

    def run(
        self,
        requirement_text: str,
        force_build_skill: bool = False,
        *,
        interactive_builder: bool = False,
        answer_provider: AnswerProvider | None = None,
        decision_observer: DecisionObserver | None = None,
    ) -> AgentRunResult:
        context = PipelineContext(
            requirement_text=requirement_text,
            force_build_skill=force_build_skill,
        )
        self.requirement_agent.run(context)
        if not force_build_skill:
            self.discovery_agent.run(context)
            self.evaluation_agent.run(context)
        self.decision_agent.run(context)

        decision = context.require_decision()
        requires_skill_builder = decision.decision_type in {
            "build_custom_skill",
            "recommend_with_custom_extension",
        }
        if requires_skill_builder:
            self.report_agent.write_report(context)
        if decision_observer is not None:
            decision_observer(context)

        if requires_skill_builder:
            context.skill_draft = self.skill_builder.build(
                context.require_requirement(),
                context.require_classification(),
                decision,
                context.evaluations,
                interactive=interactive_builder and self.config.builder.interactive,
                answer_provider=answer_provider,
            )
            context.record(
                "SkillBuilderAgent",
                "SkillDraftBuildSkill",
                summary=f"Skill draft result: `{context.skill_draft.name}`.",
                metadata={"files": context.skill_draft.files},
            )
            if context.skill_draft.builder_session and context.skill_draft.builder_session.spec:
                decision.custom_skill_name = context.skill_draft.builder_session.spec.slug

        self.report_agent.write_report(context)
        context.record(
            "ReportAgent",
            "TraceWriterSkill",
            summary=f"Wrote trace to `{context.trace_path}`.",
        )

        result = AgentRunResult(
            requirement=context.require_requirement(),
            classification=context.require_classification(),
            search_plan=context.require_search_plan(),
            search_results=context.search_results,
            retrieved_contents=context.retrieved_contents,
            evaluations=context.evaluations,
            decision=decision,
            report_path=str(context.report_path),
            trace_path=str(context.trace_path),
            skill_draft=context.skill_draft,
            builder_session=context.skill_draft.builder_session if context.skill_draft else None,
            trace_events=context.trace_events,
        )
        self.writer.write_trace(result)
        return result
