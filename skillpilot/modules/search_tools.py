from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from bs4 import BeautifulSoup

from skillpilot.config import SearchConfig
from skillpilot.models import SearchPlan, SearchQuery, SearchResult, model_to_dict


class WebSearchTool:
    """Small web search adapter that keeps failures as structured results."""

    def __init__(
        self,
        timeout_seconds: float = 8.0,
        user_agent: str = "SkillPilot/0.1",
        proxy_url: str | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self.proxy_url = proxy_url

    def search(self, query: SearchQuery) -> list[SearchResult]:
        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                follow_redirects=True,
                headers={"User-Agent": self.user_agent},
                proxy=self.proxy_url,
            ) as client:
                response = client.get(
                    "https://duckduckgo.com/html/",
                    params={"q": query.text},
                )
                response.raise_for_status()
            results = self._parse_duckduckgo_html(query, response.text)
            if not results:
                return [self._status_result(query, "no_results", "Web search returned no visible results.")]
            return results
        except Exception as exc:  # noqa: BLE001 - search failures should stay in the trace.
            return [self._failure_result(query, exc)]

    def _parse_duckduckgo_html(self, query: SearchQuery, html: str) -> list[SearchResult]:
        soup = BeautifulSoup(html, "html.parser")
        results: list[SearchResult] = []

        for item in soup.select(".result"):
            link = item.select_one(".result__a") or item.select_one("a.result-link")
            if link is None:
                continue
            title = link.get_text(" ", strip=True)
            url = self._normalize_result_url(link.get("href") or "")
            snippet_node = item.select_one(".result__snippet")
            snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""
            if not title or not url:
                continue
            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source_type="web",
                    query=query.text,
                    status="success",
                    source_id=query.source_id,
                )
            )
            if len(results) >= query.max_results:
                break

        return results

    def _normalize_result_url(self, url: str) -> str:
        if url.startswith("//"):
            url = f"https:{url}"
        parsed = urlparse(url)
        if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
            target = parse_qs(parsed.query).get("uddg", [])
            if target:
                return target[0]
        return url

    def _status_result(self, query: SearchQuery, status: str, message: str) -> SearchResult:
        return SearchResult(
            title="",
            url="",
            snippet=message,
            source_type="web",
            query=query.text,
            status=status,  # type: ignore[arg-type]
            source_id=query.source_id,
        )

    def _failure_result(self, query: SearchQuery, error: Exception) -> SearchResult:
        return SearchResult(
            title="",
            url="",
            snippet="Web search failed before candidate extraction.",
            source_type="web",
            query=query.text,
            status="failed",
            source_id=query.source_id,
            error_message=str(error),
        )


class GitHubSearchTool:
    """Search GitHub repositories and preserve repository metadata for later scoring."""

    def __init__(
        self,
        timeout_seconds: float = 8.0,
        user_agent: str = "SkillPilot/0.1",
        github_token: str | None = None,
        proxy_url: str | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self.github_token = github_token
        self.proxy_url = proxy_url

    def search(self, query: SearchQuery) -> list[SearchResult]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": self.user_agent,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"

        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                headers=headers,
                proxy=self.proxy_url,
            ) as client:
                response = client.get(
                    "https://api.github.com/search/repositories",
                    params={
                        "q": query.text,
                        "sort": "stars",
                        "order": "desc",
                        "per_page": query.max_results,
                    },
                )
                response.raise_for_status()
            results = self._parse_repository_results(query, response.json())
            if not results:
                return [self._status_result(query, "no_results", "GitHub search returned no repositories.")]
            return results
        except Exception as exc:  # noqa: BLE001 - search failures should stay in the trace.
            return [self._failure_result(query, exc)]

    def _parse_repository_results(self, query: SearchQuery, payload: dict[str, Any]) -> list[SearchResult]:
        results: list[SearchResult] = []
        for item in payload.get("items", [])[: query.max_results]:
            license_info = item.get("license") or {}
            results.append(
                SearchResult(
                    title=item.get("full_name") or item.get("name") or "",
                    url=item.get("html_url") or "",
                    snippet=item.get("description") or "",
                    source_type="github",
                    query=query.text,
                    status="success",
                    source_id=query.source_id,
                    metadata={
                        "stars": item.get("stargazers_count"),
                        "forks": item.get("forks_count"),
                        "open_issues": item.get("open_issues_count"),
                        "language": item.get("language"),
                        "last_updated": item.get("updated_at"),
                        "license": license_info.get("spdx_id"),
                    },
                )
            )
        return [result for result in results if result.title and result.url]

    def _status_result(self, query: SearchQuery, status: str, message: str) -> SearchResult:
        return SearchResult(
            title="",
            url="",
            snippet=message,
            source_type="github",
            query=query.text,
            status=status,  # type: ignore[arg-type]
            source_id=query.source_id,
        )

    def _failure_result(self, query: SearchQuery, error: Exception) -> SearchResult:
        return SearchResult(
            title="",
            url="",
            snippet="GitHub search failed before repository reading.",
            source_type="github",
            query=query.text,
            status="failed",
            source_id=query.source_id,
            error_message=str(error),
        )


class SourceSearchTool:
    """Run source-specific searches without using broad web search."""

    def __init__(
        self,
        timeout_seconds: float = 8.0,
        user_agent: str = "SkillPilot/0.1",
        proxy_url: str | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self.proxy_url = proxy_url

    def search(self, query: SearchQuery) -> list[SearchResult]:
        if query.source_id == "skillsmp_directory":
            return self._search_skillsmp(query)
        return [
            SearchResult(
                title="",
                url="",
                snippet=(
                    "Source-specific search is planned, but its reader/searcher is not implemented yet. "
                    "See docs/stage_2_3_source_access.md."
                ),
                source_type="source",
                query=query.text,
                status="skipped",
                source_id=query.source_id,
            )
        ]

    def _search_skillsmp(self, query: SearchQuery) -> list[SearchResult]:
        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                follow_redirects=True,
                headers={"User-Agent": self.user_agent},
                proxy=self.proxy_url,
            ) as client:
                response = client.get(
                    "https://skillsmp.com/api/v1/skills/search",
                    params={
                        "q": query.text,
                        "limit": query.max_results,
                        "sortBy": "stars",
                    },
                )
                response.raise_for_status()
            results = self._parse_skillsmp_results(query, response.json())
            if not results:
                return [
                    SearchResult(
                        title="",
                        url="",
                        snippet="SkillsMP API returned no matching skills.",
                        source_type="source",
                        query=query.text,
                        status="no_results",
                        source_id=query.source_id,
                    )
                ]
            return results
        except Exception as exc:  # noqa: BLE001 - search failures should stay in the trace.
            return [
                SearchResult(
                    title="",
                    url="",
                    snippet="SkillsMP source search failed before source verification.",
                    source_type="source",
                    query=query.text,
                    status="failed",
                    source_id=query.source_id,
                    error_message=str(exc),
                )
            ]

    def _parse_skillsmp_results(self, query: SearchQuery, payload: dict[str, Any]) -> list[SearchResult]:
        skills = payload.get("data", {}).get("skills", [])
        results: list[SearchResult] = []
        for skill in skills[: query.max_results]:
            github_url = skill.get("githubUrl") or ""
            skill_url = skill.get("skillUrl") or ""
            title = skill.get("name") or skill.get("id") or ""
            if not title:
                continue
            results.append(
                SearchResult(
                    title=title,
                    url=github_url or skill_url,
                    snippet=skill.get("description") or "",
                    source_type="github" if github_url else "source",
                    query=query.text,
                    status="success",
                    source_id=query.source_id,
                    metadata={
                        "skillsmp_id": skill.get("id"),
                        "skillsmp_url": skill_url,
                        "author": skill.get("author"),
                        "stars": skill.get("stars"),
                        "updated_at": skill.get("updatedAt"),
                    },
                )
            )
        return [result for result in results if result.url]


class SourceSearchAgent:
    """Run all queries planned for one curated source."""

    def __init__(self, source_id: str, search_tool: SourceSearchTool) -> None:
        self.source_id = source_id
        self.search_tool = search_tool

    def search(self, queries: list[SearchQuery]) -> list[SearchResult]:
        results: list[SearchResult] = []
        for query in queries:
            query_results = self.search_tool.search(query)
            for result in query_results:
                result.metadata.setdefault("search_agent", self.source_id)
            results.extend(query_results)
        return results


class SearchExecutor:
    def __init__(self, config: SearchConfig) -> None:
        self.config = config
        self.source_search = SourceSearchTool(
            timeout_seconds=config.timeout_seconds,
            user_agent=config.user_agent,
            proxy_url=config.proxy_url,
        )
        self.web_search = WebSearchTool(
            timeout_seconds=config.timeout_seconds,
            user_agent=config.user_agent,
            proxy_url=config.proxy_url,
        )
        self.github_search = GitHubSearchTool(
            timeout_seconds=config.timeout_seconds,
            user_agent=config.user_agent,
            github_token=config.github_token,
            proxy_url=config.proxy_url,
        )

    def run(self, plan: SearchPlan) -> list[SearchResult]:
        results: list[SearchResult] = []
        limited_queries = [self._with_configured_limit(query) for query in plan.queries]

        if not self.config.enable_network_search:
            return [self._skipped_result(query) for query in limited_queries]

        source_queries = [query for query in limited_queries if query.source_type == "source"]
        results.extend(self._run_source_agents(source_queries))

        for query in limited_queries:
            if query.source_type == "source":
                continue
            if query.source_type == "github":
                results.extend(self.github_search.search(query))
            elif query.source_type == "web":
                results.append(self._disabled_web_result(query))
        return results

    def _run_source_agents(self, queries: list[SearchQuery]) -> list[SearchResult]:
        if not queries:
            return []

        grouped_queries = self._group_queries_by_source(queries)
        results_by_source: dict[str, list[SearchResult]] = {}
        max_workers = min(len(grouped_queries), 5)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_source = {
                executor.submit(SourceSearchAgent(source_id, self.source_search).search, source_queries): source_id
                for source_id, source_queries in grouped_queries.items()
            }
            for future in as_completed(future_to_source):
                source_id = future_to_source[future]
                try:
                    results_by_source[source_id] = future.result()
                except Exception as exc:  # noqa: BLE001 - source-agent failures should stay in the trace.
                    results_by_source[source_id] = [
                        self._source_agent_failure_result(
                            grouped_queries[source_id][0],
                            source_id,
                            exc,
                        )
                    ]

        results: list[SearchResult] = []
        for source_id in grouped_queries:
            results.extend(results_by_source.get(source_id, []))
        return results

    def _group_queries_by_source(self, queries: list[SearchQuery]) -> dict[str, list[SearchQuery]]:
        grouped: dict[str, list[SearchQuery]] = {}
        for query in queries:
            source_id = query.source_id or "unknown_source"
            grouped.setdefault(source_id, []).append(query)
        return grouped

    def _source_agent_failure_result(
        self,
        query: SearchQuery,
        source_id: str,
        error: Exception,
    ) -> SearchResult:
        return SearchResult(
            title="",
            url="",
            snippet="Source search agent failed before returning source-specific results.",
            source_type="source",
            query=query.text,
            status="failed",
            source_id=source_id,
            error_message=str(error),
            metadata={"search_agent": source_id},
        )

    def _with_configured_limit(self, query: SearchQuery) -> SearchQuery:
        data = model_to_dict(query)
        data["max_results"] = min(query.max_results, self.config.max_results_per_query)
        return SearchQuery(**data)

    def _skipped_result(self, query: SearchQuery) -> SearchResult:
        return SearchResult(
            title="",
            url="",
            snippet="Network search is disabled. Set SKILLPILOT_ENABLE_NETWORK_SEARCH=1 to execute this query.",
            source_type=query.source_type,
            query=query.text,
            status="skipped",
            source_id=query.source_id,
        )

    def _disabled_web_result(self, query: SearchQuery) -> SearchResult:
        return SearchResult(
            title="",
            url="",
            snippet=(
                "Broad web search is disabled. Use curated source readers/searchers "
                "instead of DuckDuckGo fallback search."
            ),
            source_type="web",
            query=query.text,
            status="skipped",
            source_id=query.source_id,
        )
