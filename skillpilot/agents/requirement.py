from __future__ import annotations

from skillpilot.agents.core import PipelineContext
from skillpilot.skills.classification import ExtensionTypeClassifier
from skillpilot.skills.planning import SourcePlanner
from skillpilot.skills.requirement import RequirementParser


class RequirementAnalysisAgent:
    def __init__(
        self,
        parser: RequirementParser,
        classifier: ExtensionTypeClassifier,
        planner: SourcePlanner,
    ) -> None:
        self.parser = parser
        self.classifier = classifier
        self.planner = planner

    def run(self, context: PipelineContext, *, plan_search: bool = True) -> None:
        context.requirement = self.parser.parse(context.requirement_text)
        context.record(
            "RequirementAnalysisAgent",
            "RequirementExtractionSkill",
            summary=f"Parsed requirement domain `{context.requirement.task_domain}`.",
            metadata={"capabilities": context.requirement.desired_capabilities},
        )

        context.classification = self.classifier.classify(context.requirement)
        context.record(
            "RequirementAnalysisAgent",
            "ExtensionTypeDecisionSkill",
            summary=f"Selected `{context.classification.recommended_type}`.",
            metadata={
                "confidence": context.classification.confidence,
                "reason": context.classification.reason,
            },
        )

        if not plan_search:
            context.record(
                "RequirementAnalysisAgent",
                "QueryPlanningSkill",
                status="skipped",
                summary="Skipped search planning because custom Skill build was requested directly.",
            )
            return

        context.search_plan = self.planner.plan(context.requirement, context.classification)
        context.record(
            "RequirementAnalysisAgent",
            "QueryPlanningSkill",
            summary=f"Planned {len(context.search_plan.queries)} source queries.",
            metadata={
                "sources": [source.source_id for source in context.search_plan.sources],
                "queries": [query.text for query in context.search_plan.queries],
            },
        )
