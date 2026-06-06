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
        context.record(
            "SourceDiscoveryAgent",
            "SourceSearchDispatchSkill",
            summary=f"Searching {len(search_plan.queries)} planned source queries.",
            metadata={
                "sources": [
                    {
                        "source_id": source.source_id,
                        "name": source.name,
                        "entrypoint": source.api_url or source.index_url or source.base_url,
                    }
                    for source in search_plan.sources
                ],
                "queries": [
                    {
                        "source_id": query.source_id,
                        "text": query.text,
                        "purpose": query.purpose,
                    }
                    for query in search_plan.queries
                ],
            },
        )
        context.search_results = self.search_executor.run(search_plan)
        context.record(
            "SourceDiscoveryAgent",
            "SourceSearchSkill",
            summary=f"Search returned {len(context.search_results)} result records.",
            metadata={
                "statuses": [result.status for result in context.search_results],
                "results": [
                    {
                        "title": result.title,
                        "url": result.url,
                        "status": result.status,
                        "source_id": result.source_id,
                    }
                    for result in context.search_results
                ],
            },
        )

        context.record(
            "SourceDiscoveryAgent",
            "ContentReadDispatchSkill",
            summary="Reading returned pages and repositories.",
            metadata={
                "targets": [
                    {
                        "title": result.title,
                        "url": result.url,
                        "status": result.status,
                        "source_id": result.source_id,
                    }
                    for result in context.search_results
                    if result.url
                ],
            },
        )
        context.retrieved_contents = self.content_reader.read(context.search_results)
        context.record(
            "SourceDiscoveryAgent",
            "ContentReadSkill",
            summary=f"Read stage returned {len(context.retrieved_contents)} content records.",
            metadata={
                "statuses": [content.status for content in context.retrieved_contents],
                "contents": [
                    {
                        "title": content.title,
                        "url": content.url,
                        "status": content.status,
                        "source_id": content.source_id,
                    }
                    for content in context.retrieved_contents
                ],
            },
        )
