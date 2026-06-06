from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from skillpilot.config import SearchConfig
from skillpilot.models import SearchPlan, SearchQuery, SearchResult, model_to_dict
from skillpilot.skills.discovery.source_access_guide import (
    SourceAccessGuide,
    SourceAccessGuideLoader,
)


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
        guide_loader: SourceAccessGuideLoader | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self.proxy_url = proxy_url
        self.guide_loader = guide_loader or SourceAccessGuideLoader()

    def search(self, query: SearchQuery) -> list[SearchResult]:
        guide = self.guide_loader.get(query.source_id)
        if guide is None:
            return [
                self._source_status_result(
                    query,
                    "skipped",
                    "No source access guide entry exists for this source.",
                )
            ]

        searcher_type = guide.searcher_type
        if searcher_type == "skillsmp_api_searcher":
            return self._search_skillsmp(query, guide)
        if searcher_type == "marketplace_json_searcher":
            return self._search_marketplace_json(query, guide)
        if searcher_type in {
            "mcp_registry_api_searcher",
            "glama_api_searcher",
            "smithery_api_searcher",
        }:
            return self._search_registry_api(query, guide)
        if searcher_type == "docs_keyword_searcher":
            return self._search_markdown_docs(query, guide)
        if searcher_type == "github_contents_searcher":
            return self._search_github_contents(query, guide)
        return [
            self._source_status_result(
                query,
                "skipped",
                f"Unsupported source-specific searcher type: {searcher_type}.",
            )
        ]

    def _search_skillsmp(
        self,
        query: SearchQuery,
        guide: SourceAccessGuide | None = None,
    ) -> list[SearchResult]:
        url = (
            guide.entrypoint.get("url")
            if guide is not None
            else "https://skillsmp.com/api/v1/skills/search"
        )
        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                follow_redirects=True,
                headers={"User-Agent": self.user_agent},
                proxy=self.proxy_url,
            ) as client:
                response = client.get(
                    str(url),
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

    def _search_marketplace_json(
        self,
        query: SearchQuery,
        guide: SourceAccessGuide,
    ) -> list[SearchResult]:
        try:
            payload = self._fetch_json(str(guide.entrypoint["url"]))
            results = self._parse_marketplace_results(query, guide, payload)
        except Exception as exc:  # noqa: BLE001 - source failures stay structured.
            return [self._source_failure_result(query, "Marketplace JSON search failed.", exc)]
        return results or [
            self._source_status_result(query, "no_results", "Marketplace JSON contained no matching entries.")
        ]

    def _parse_marketplace_results(
        self,
        query: SearchQuery,
        guide: SourceAccessGuide,
        payload: dict[str, Any],
    ) -> list[SearchResult]:
        entries = payload.get("plugins")
        if not isinstance(entries, list):
            return []

        terms = self._query_terms(query.text)
        ranked_results: list[tuple[int, SearchResult]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            nested_skill_paths = entry.get("skills") if isinstance(entry.get("skills"), list) else []
            if nested_skill_paths:
                for skill_path in nested_skill_paths:
                    title = str(skill_path).rstrip("/").rsplit("/", 1)[-1]
                    text = self._marketplace_match_text(entry, extra=str(skill_path))
                    score = self._match_score(terms, text)
                    if score <= 0:
                        continue
                    ranked_results.append(
                        (
                            score,
                            SearchResult(
                                title=title,
                                url=self._resolve_source_url(guide, str(skill_path)),
                                snippet=str(entry.get("description") or ""),
                                source_type="github",
                                query=query.text,
                                status="success",
                                source_id=query.source_id,
                                metadata=self._marketplace_metadata(entry, guide, skill_path=str(skill_path)),
                            ),
                        )
                    )
                continue

            text = self._marketplace_match_text(entry)
            score = self._match_score(terms, text)
            if score <= 0:
                continue
            title = str(entry.get("name") or "").strip()
            url = self._entry_url(entry, guide)
            ranked_results.append(
                (
                    score,
                    SearchResult(
                        title=title,
                        url=url,
                        snippet=str(entry.get("description") or ""),
                        source_type="github" if "github.com" in url else "source",
                        query=query.text,
                        status="success",
                        source_id=query.source_id,
                        metadata=self._marketplace_metadata(entry, guide),
                    ),
                )
            )

        return self._top_ranked_results(ranked_results, query.max_results)

    def _search_registry_api(
        self,
        query: SearchQuery,
        guide: SourceAccessGuide,
    ) -> list[SearchResult]:
        try:
            payload = self._fetch_json(str(guide.entrypoint["url"]))
            results = self._parse_registry_results(query, guide, payload)
        except Exception as exc:  # noqa: BLE001 - source failures stay structured.
            return [self._source_failure_result(query, "Registry API search failed.", exc)]
        return results or [
            self._source_status_result(query, "no_results", "Registry API contained no matching entries.")
        ]

    def _parse_registry_results(
        self,
        query: SearchQuery,
        guide: SourceAccessGuide,
        payload: dict[str, Any],
    ) -> list[SearchResult]:
        entries = payload.get("servers")
        if not isinstance(entries, list):
            return []

        terms = self._query_terms(query.text)
        ranked_results: list[tuple[int, SearchResult]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            server = entry.get("server") if isinstance(entry.get("server"), dict) else entry
            text = self._stringify_for_match(server)
            score = self._match_score(terms, text)
            if score <= 0:
                continue
            title = str(
                server.get("displayName")
                or server.get("title")
                or server.get("name")
                or server.get("qualifiedName")
                or ""
            ).strip()
            url = self._registry_url(server)
            ranked_results.append(
                (
                    score,
                    SearchResult(
                        title=title,
                        url=url,
                        snippet=str(server.get("description") or ""),
                        source_type="github" if "github.com" in url else "source",
                        query=query.text,
                        status="success",
                        source_id=query.source_id,
                        metadata={
                            "searcher_type": guide.searcher_type,
                            "reader_type": guide.reader_type,
                            "content_format": guide.content_format,
                            "qualified_name": server.get("qualifiedName") or server.get("name"),
                            "namespace": server.get("namespace"),
                            "verified": server.get("verified"),
                            "remote": server.get("remote"),
                            "is_deployed": server.get("isDeployed"),
                            "use_count": server.get("useCount"),
                        },
                    ),
                )
            )
        return self._top_ranked_results(ranked_results, query.max_results)

    def _search_markdown_docs(
        self,
        query: SearchQuery,
        guide: SourceAccessGuide,
    ) -> list[SearchResult]:
        try:
            markdown = self._fetch_text(str(guide.entrypoint["url"]))
            results = self._parse_markdown_results(query, guide, markdown)
        except Exception as exc:  # noqa: BLE001 - source failures stay structured.
            return [self._source_failure_result(query, "Markdown docs search failed.", exc)]
        return results or [
            self._source_status_result(query, "no_results", "Markdown source contained no matching sections.")
        ]

    def _parse_markdown_results(
        self,
        query: SearchQuery,
        guide: SourceAccessGuide,
        markdown: str,
    ) -> list[SearchResult]:
        terms = self._query_terms(query.text)
        sections = self._markdown_sections(markdown)
        ranked_results: list[tuple[int, SearchResult]] = []
        for title, body in sections:
            text = f"{title}\n{body}"
            score = self._match_score(terms, text)
            if score <= 0:
                continue
            ranked_results.append(
                (
                    score,
                    SearchResult(
                        title=title or "Documentation match",
                        url=str(guide.entrypoint["url"]),
                        snippet=self._truncate_snippet(body or text),
                        source_type="source",
                        query=query.text,
                        status="success",
                        source_id=query.source_id,
                        metadata={
                            "searcher_type": guide.searcher_type,
                            "reader_type": guide.reader_type,
                            "content_format": guide.content_format,
                        },
                    ),
                )
            )
        return self._top_ranked_results(ranked_results, query.max_results)

    def _search_github_contents(
        self,
        query: SearchQuery,
        guide: SourceAccessGuide,
    ) -> list[SearchResult]:
        try:
            payload = self._fetch_json(str(guide.entrypoint["url"]))
            results = self._parse_github_contents_results(query, guide, payload)
        except Exception as exc:  # noqa: BLE001 - source failures stay structured.
            return [self._source_failure_result(query, "GitHub contents search failed.", exc)]
        return results or [
            self._source_status_result(query, "no_results", "GitHub contents source contained no matching entries.")
        ]

    def _parse_github_contents_results(
        self,
        query: SearchQuery,
        guide: SourceAccessGuide,
        payload: Any,
    ) -> list[SearchResult]:
        if not isinstance(payload, list):
            return []
        terms = self._query_terms(query.text)
        ranked_results: list[tuple[int, SearchResult]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            text = " ".join(
                str(item.get(key) or "")
                for key in ("name", "path", "type", "html_url", "download_url")
            )
            score = self._match_score(terms, text)
            if score <= 0:
                continue
            url = str(item.get("html_url") or item.get("download_url") or "")
            ranked_results.append(
                (
                    score,
                    SearchResult(
                        title=str(item.get("name") or item.get("path") or ""),
                        url=url,
                        snippet=f"GitHub {item.get('type') or 'content'} entry: {item.get('path') or item.get('name')}",
                        source_type="github" if "github.com" in url else "source",
                        query=query.text,
                        status="success",
                        source_id=query.source_id,
                        metadata={
                            "searcher_type": guide.searcher_type,
                            "reader_type": guide.reader_type,
                            "content_format": guide.content_format,
                            "path": item.get("path"),
                            "type": item.get("type"),
                        },
                    ),
                )
            )
        return self._top_ranked_results(ranked_results, query.max_results)

    def _fetch_json(self, url: str) -> Any:
        with httpx.Client(
            timeout=self.timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": self.user_agent},
            proxy=self.proxy_url,
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()

    def _fetch_text(self, url: str) -> str:
        with httpx.Client(
            timeout=self.timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": self.user_agent},
            proxy=self.proxy_url,
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.text

    def _query_terms(self, text: str) -> list[str]:
        stop_words = {
            "and",
            "the",
            "with",
            "for",
            "inside",
            "source",
            "claude",
            "code",
            "plugin",
            "plugins",
            "skill",
            "skills",
            "mcp",
            "server",
            "github",
            "official",
            "community",
            "marketplace",
            "json",
            "repo",
            "repository",
        }
        terms = [
            term.lower()
            for term in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*|[\u4e00-\u9fff]+", text)
        ]
        return [
            term
            for term in terms
            if len(term) > 2 and term not in stop_words
        ]

    def _match_score(self, terms: list[str], text: str) -> int:
        if not terms:
            return 1
        haystack = text.lower()
        return sum(1 for term in terms if term in haystack)

    def _top_ranked_results(
        self,
        ranked_results: list[tuple[int, SearchResult]],
        max_results: int,
    ) -> list[SearchResult]:
        ranked_results.sort(key=lambda item: item[0], reverse=True)
        results: list[SearchResult] = []
        seen_urls: set[str] = set()
        seen_titles: set[str] = set()
        for _, result in ranked_results:
            title_key = result.title.lower()
            url_key = result.url.rstrip("/")
            if url_key and url_key in seen_urls:
                continue
            if title_key and title_key in seen_titles:
                continue
            if url_key:
                seen_urls.add(url_key)
            if title_key:
                seen_titles.add(title_key)
            results.append(result)
            if len(results) >= max_results:
                break
        return results

    def _marketplace_match_text(self, entry: dict[str, Any], extra: str = "") -> str:
        source = entry.get("source")
        fields = [
            entry.get("name"),
            entry.get("description"),
            entry.get("category"),
            entry.get("homepage"),
            extra,
            json.dumps(entry.get("keywords", []), ensure_ascii=False),
            json.dumps(source, ensure_ascii=False),
        ]
        return " ".join(str(field or "") for field in fields)

    def _marketplace_metadata(
        self,
        entry: dict[str, Any],
        guide: SourceAccessGuide,
        *,
        skill_path: str | None = None,
    ) -> dict[str, Any]:
        return {
            "searcher_type": guide.searcher_type,
            "reader_type": guide.reader_type,
            "content_format": guide.content_format,
            "entry_name": entry.get("name"),
            "category": entry.get("category"),
            "author": entry.get("author"),
            "source": entry.get("source"),
            "skill_path": skill_path,
        }

    def _entry_url(self, entry: dict[str, Any], guide: SourceAccessGuide) -> str:
        homepage = str(entry.get("homepage") or "").strip()
        if homepage:
            return homepage
        return self._resolve_source_url(guide, entry.get("source"))

    def _resolve_source_url(self, guide: SourceAccessGuide, source: Any) -> str:
        if isinstance(source, dict):
            source_kind = str(source.get("source") or "")
            url = str(source.get("url") or "")
            path = str(source.get("path") or "").strip("/")
            ref = str(source.get("ref") or "main")
            if "github.com" in url and path:
                return f"{url.rstrip('/')}/tree/{ref}/{path}"
            return url
        if not isinstance(source, str):
            return str(guide.entrypoint.get("url") or "")
        if source.startswith(("http://", "https://")):
            return source
        raw_url = str(guide.entrypoint.get("url") or "")
        github_base = self._raw_github_base_url(raw_url)
        if github_base:
            clean_source = source.strip("./")
            if clean_source:
                return f"{github_base.rstrip('/')}/tree/main/{clean_source}"
            return github_base
        return urljoin(raw_url, source)

    def _raw_github_base_url(self, raw_url: str) -> str:
        parsed = urlparse(raw_url)
        if parsed.netloc != "raw.githubusercontent.com":
            return ""
        parts = [part for part in parsed.path.strip("/").split("/") if part]
        if len(parts) < 3:
            return ""
        owner, repo = parts[0], parts[1]
        return f"https://github.com/{owner}/{repo}"

    def _registry_url(self, server: dict[str, Any]) -> str:
        repository = server.get("repository")
        if isinstance(repository, dict) and repository.get("url"):
            return str(repository["url"])
        for key in ("homepage", "homepageUrl", "websiteUrl", "url"):
            if server.get(key):
                return str(server[key])
        remotes = server.get("remotes")
        if isinstance(remotes, list) and remotes:
            first_remote = remotes[0]
            if isinstance(first_remote, dict) and first_remote.get("url"):
                return str(first_remote["url"])
        qualified_name = server.get("qualifiedName") or server.get("name") or ""
        if qualified_name:
            return f"https://smithery.ai/server/{qualified_name}"
        return ""

    def _stringify_for_match(self, value: Any) -> str:
        if isinstance(value, dict):
            return " ".join(self._stringify_for_match(item) for item in value.values())
        if isinstance(value, list):
            return " ".join(self._stringify_for_match(item) for item in value)
        return str(value or "")

    def _markdown_sections(self, markdown: str) -> list[tuple[str, str]]:
        sections: list[tuple[str, list[str]]] = []
        current_title = "Documentation"
        current_lines: list[str] = []
        for line in markdown.splitlines():
            if line.startswith("#"):
                if current_lines:
                    sections.append((current_title, current_lines))
                current_title = line.lstrip("#").strip() or "Documentation"
                current_lines = []
            else:
                current_lines.append(line)
        if current_lines:
            sections.append((current_title, current_lines))
        return [
            (title, "\n".join(lines).strip())
            for title, lines in sections
            if title or any(line.strip() for line in lines)
        ]

    def _truncate_snippet(self, text: str, max_length: int = 300) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= max_length:
            return normalized
        return normalized[:max_length].rstrip() + "..."

    def _source_status_result(
        self,
        query: SearchQuery,
        status: str,
        message: str,
    ) -> SearchResult:
        return SearchResult(
            title="",
            url="",
            snippet=message,
            source_type="source",
            query=query.text,
            status=status,  # type: ignore[arg-type]
            source_id=query.source_id,
        )

    def _source_failure_result(
        self,
        query: SearchQuery,
        message: str,
        error: Exception,
    ) -> SearchResult:
        return SearchResult(
            title="",
            url="",
            snippet=message,
            source_type="source",
            query=query.text,
            status="failed",
            source_id=query.source_id,
            error_message=str(error),
        )


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
