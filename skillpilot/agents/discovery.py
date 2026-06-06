from __future__ import annotations

from skillpilot.agents.core import PipelineContext
from skillpilot.skills.discovery.readers import ContentReader
from skillpilot.skills.discovery.search_tools import SearchExecutor


class SourceDiscoveryAgent:
    def __init__(
        self,
        search_executor: SearchExecutor,
        content_reader: ContentReader,
    ) -> None:
        self.search_executor = search_executor
        self.content_reader = content_reader

    def run(self, context: PipelineContext) -> None:
        search_plan = context.require_search_plan()
        context.search_results = self.search_executor.run(search_plan)
        context.record(
            "SourceDiscoveryAgent",
            "SourceSearchSkill",
            summary=f"Search returned {len(context.search_results)} result records.",
            metadata={
                "statuses": [result.status for result in context.search_results],
            },
        )

        context.retrieved_contents = self.content_reader.read(context.search_results)
        context.record(
            "SourceDiscoveryAgent",
            "ContentReadSkill",
            summary=f"Read stage returned {len(context.retrieved_contents)} content records.",
            metadata={
                "statuses": [content.status for content in context.retrieved_contents],
            },
        )
