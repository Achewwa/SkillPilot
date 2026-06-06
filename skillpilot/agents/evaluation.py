from __future__ import annotations

from skillpilot.agents.core import PipelineContext
from skillpilot.models import SearchResult
from skillpilot.skills.cache import LocalCandidateCache
from skillpilot.skills.evaluation import CandidateEvaluator


class CandidateEvaluationAgent:
    def __init__(
        self,
        evaluator: CandidateEvaluator,
        cache: LocalCandidateCache,
    ) -> None:
        self.evaluator = evaluator
        self.cache = cache

    def run(self, context: PipelineContext) -> None:
        requirement = context.require_requirement()
        classification = context.require_classification()
        successful_contents = [
            content
            for content in context.retrieved_contents
            if content.status == "success" and content.url and content.content.strip()
        ]
        context.record(
            "CandidateEvaluationAgent",
            "CandidateEvaluationDispatchSkill",
            summary=(
                f"Evaluating {len(successful_contents)} retrieved contents with LLM."
                if successful_contents
                else "No retrieved contents are eligible for LLM evaluation; fallback may be used."
            ),
            metadata={
                "contents": [
                    {
                        "title": content.title,
                        "url": content.url,
                        "source_id": content.source_id,
                    }
                    for content in successful_contents
                ]
            },
        )
        context.evaluations = self.evaluator.evaluate_retrieved(
            requirement,
            classification,
            context.retrieved_contents,
        )
        context.record(
            "CandidateEvaluationAgent",
            "CandidateUnderstandingSkill",
            status="success" if context.evaluations else "skipped",
            summary=f"Evaluated {len(context.evaluations)} retrieved candidates.",
        )

        if not context.evaluations and self.should_use_offline_cache(context.search_results):
            context.evaluations = self.evaluator.evaluate(
                requirement,
                classification,
                self.cache.load(),
            )
            context.record(
                "CandidateEvaluationAgent",
                "OfflineCandidateCacheSkill",
                status="fallback",
                summary=f"Loaded and evaluated {len(context.evaluations)} cached candidates.",
            )

    def should_use_offline_cache(self, search_results: list[SearchResult]) -> bool:
        if not search_results:
            return True
        return all(result.status == "skipped" for result in search_results)
