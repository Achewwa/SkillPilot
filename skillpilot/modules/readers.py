from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from skillpilot.config import SearchConfig
from skillpilot.models import RetrievedContent, SearchResult


class PageReader:
    """Read ordinary documentation pages without executing page scripts."""

    def __init__(
        self,
        timeout_seconds: float = 8.0,
        user_agent: str = "SkillPilot/0.1",
        proxy_url: str | None = None,
        max_chars: int = 12000,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self.proxy_url = proxy_url
        self.max_chars = max_chars

    def read(self, result: SearchResult) -> RetrievedContent:
        if result.status != "success" or not result.url:
            return self._skipped(result, "Search result has no readable URL.")

        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                follow_redirects=True,
                headers={"User-Agent": self.user_agent},
                proxy=self.proxy_url,
            ) as client:
                response = client.get(result.url)
                response.raise_for_status()
            return self._parse_response(result, response)
        except Exception as exc:  # noqa: BLE001 - read failures should stay in the trace.
            return self._failed(result, exc)

    def _parse_response(
        self,
        result: SearchResult,
        response: httpx.Response,
    ) -> RetrievedContent:
        content_type = response.headers.get("content-type", "")
        metadata = {
            "content_type": content_type,
            "final_url": str(response.url),
        }
        if "html" in content_type or "<html" in response.text[:500].lower():
            title, text, description = self._extract_html(response.text, result.title)
            metadata["description"] = description
        elif "text" in content_type or "json" in content_type or "xml" in content_type:
            title = result.title
            text = response.text
        else:
            return RetrievedContent(
                title=result.title,
                url=result.url,
                source_type=result.source_type,
                query=result.query,
                status="failed",
                error_message=f"Unsupported content type: {content_type or 'unknown'}",
                metadata=metadata,
            )

        return RetrievedContent(
            title=title or result.title,
            url=result.url,
            source_type=result.source_type,
            query=result.query,
            status="success",
            content=self._truncate(text),
            metadata=metadata,
        )

    def _extract_html(self, html: str, fallback_title: str) -> tuple[str, str, str]:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()

        title = soup.title.get_text(" ", strip=True) if soup.title else fallback_title
        description_node = soup.select_one('meta[name="description"]')
        description = ""
        if description_node:
            description = description_node.get("content", "").strip()

        text_parts = []
        if description:
            text_parts.append(description)
        text_parts.append(soup.get_text("\n", strip=True))
        return title, self._normalize_text("\n".join(text_parts)), description

    def _normalize_text(self, text: str) -> str:
        lines = [" ".join(line.split()) for line in text.splitlines()]
        return "\n".join(line for line in lines if line)

    def _truncate(self, text: str) -> str:
        normalized = self._normalize_text(text)
        if len(normalized) <= self.max_chars:
            return normalized
        return normalized[: self.max_chars].rstrip() + "\n...[truncated]"

    def _skipped(self, result: SearchResult, message: str) -> RetrievedContent:
        return RetrievedContent(
            title=result.title,
            url=result.url,
            source_type=result.source_type,
            query=result.query,
            status="skipped",
            error_message=message,
        )

    def _failed(self, result: SearchResult, error: Exception) -> RetrievedContent:
        return RetrievedContent(
            title=result.title,
            url=result.url,
            source_type=result.source_type,
            query=result.query,
            status="failed",
            error_message=str(error),
        )


class RepoReader:
    """Read GitHub repository metadata and high-value documentation files."""

    COMMON_FILES = (
        "SKILL.md",
        ".mcp.json",
        "package.json",
        "pyproject.toml",
        "README.md",
    )

    def __init__(
        self,
        timeout_seconds: float = 8.0,
        user_agent: str = "SkillPilot/0.1",
        github_token: str | None = None,
        proxy_url: str | None = None,
        max_chars: int = 20000,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self.github_token = github_token
        self.proxy_url = proxy_url
        self.max_chars = max_chars

    def read(self, result: SearchResult) -> RetrievedContent:
        if result.status != "success" or not result.url:
            return self._skipped(result, "Search result has no readable repository URL.")

        repo_ref = self.parse_github_repo(result.url)
        if repo_ref is None:
            return self._failed_message(result, "URL is not a GitHub repository URL.")
        owner, repo = repo_ref

        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                follow_redirects=True,
                proxy=self.proxy_url,
            ) as client:
                repo_data = self._get_repo_metadata(client, owner, repo)
                readme = self._get_readme(client, owner, repo)
                config_files = self._get_common_files(client, owner, repo)
        except Exception as exc:  # noqa: BLE001 - read failures should stay in the trace.
            return self._failed(result, exc)

        metadata = self._metadata_from_repo(repo_data, config_files)
        content = self._build_repo_content(repo_data, readme, config_files)
        return RetrievedContent(
            title=repo_data.get("full_name") or result.title,
            url=repo_data.get("html_url") or result.url,
            source_type="github",
            query=result.query,
            status="success",
            content=self._truncate(content),
            metadata=metadata,
        )

    def parse_github_repo(self, url: str) -> tuple[str, str] | None:
        parsed = urlparse(url)
        if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
            return None
        parts = [part for part in parsed.path.strip("/").split("/") if part]
        if len(parts) < 2:
            return None
        owner = parts[0]
        repo = parts[1].removesuffix(".git")
        if not owner or not repo:
            return None
        return owner, repo

    def _headers(self, accept: str) -> dict[str, str]:
        headers = {
            "Accept": accept,
            "User-Agent": self.user_agent,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        return headers

    def _get_repo_metadata(
        self,
        client: httpx.Client,
        owner: str,
        repo: str,
    ) -> dict[str, Any]:
        response = client.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers=self._headers("application/vnd.github+json"),
        )
        response.raise_for_status()
        return response.json()

    def _get_readme(self, client: httpx.Client, owner: str, repo: str) -> str:
        response = client.get(
            f"https://api.github.com/repos/{owner}/{repo}/readme",
            headers=self._headers("application/vnd.github.raw"),
        )
        if response.status_code == 404:
            return ""
        response.raise_for_status()
        return response.text

    def _get_common_files(
        self,
        client: httpx.Client,
        owner: str,
        repo: str,
    ) -> dict[str, str]:
        files: dict[str, str] = {}
        for path in self.COMMON_FILES:
            if path == "README.md":
                continue
            response = client.get(
                f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
                headers=self._headers("application/vnd.github.raw"),
            )
            if response.status_code == 404:
                continue
            response.raise_for_status()
            files[path] = response.text
        return files

    def _metadata_from_repo(
        self,
        repo_data: dict[str, Any],
        config_files: dict[str, str],
    ) -> dict[str, Any]:
        license_info = repo_data.get("license") or {}
        return {
            "full_name": repo_data.get("full_name"),
            "description": repo_data.get("description"),
            "stars": repo_data.get("stargazers_count"),
            "forks": repo_data.get("forks_count"),
            "open_issues": repo_data.get("open_issues_count"),
            "language": repo_data.get("language"),
            "license": license_info.get("spdx_id"),
            "last_updated": repo_data.get("updated_at"),
            "homepage": repo_data.get("homepage"),
            "topics": repo_data.get("topics") or [],
            "common_files": sorted(config_files),
        }

    def _build_repo_content(
        self,
        repo_data: dict[str, Any],
        readme: str,
        config_files: dict[str, str],
    ) -> str:
        license_info = repo_data.get("license") or {}
        sections = [
            f"# {repo_data.get('full_name') or repo_data.get('name') or 'GitHub repository'}",
            f"Description: {repo_data.get('description') or 'unknown'}",
            f"License: {license_info.get('spdx_id') or 'unknown'}",
            f"Stars: {repo_data.get('stargazers_count') or 0}",
            f"Last updated: {repo_data.get('updated_at') or 'unknown'}",
        ]
        if readme:
            sections.extend(["", "## README", readme])
        for path, text in config_files.items():
            sections.extend(["", f"## {path}", text])
        return "\n".join(sections)

    def _truncate(self, text: str) -> str:
        normalized = "\n".join(line.rstrip() for line in text.splitlines() if line.strip())
        if len(normalized) <= self.max_chars:
            return normalized
        return normalized[: self.max_chars].rstrip() + "\n...[truncated]"

    def _skipped(self, result: SearchResult, message: str) -> RetrievedContent:
        return RetrievedContent(
            title=result.title,
            url=result.url,
            source_type=result.source_type,
            query=result.query,
            status="skipped",
            error_message=message,
        )

    def _failed(self, result: SearchResult, error: Exception) -> RetrievedContent:
        return self._failed_message(result, str(error))

    def _failed_message(self, result: SearchResult, message: str) -> RetrievedContent:
        return RetrievedContent(
            title=result.title,
            url=result.url,
            source_type=result.source_type,
            query=result.query,
            status="failed",
            error_message=message,
        )


class ContentReader:
    def __init__(self, config: SearchConfig, max_results_to_read: int = 10) -> None:
        self.max_results_to_read = max_results_to_read
        self.page_reader = PageReader(
            timeout_seconds=config.timeout_seconds,
            user_agent=config.user_agent,
            proxy_url=config.proxy_url,
        )
        self.repo_reader = RepoReader(
            timeout_seconds=config.timeout_seconds,
            user_agent=config.user_agent,
            github_token=config.github_token,
            proxy_url=config.proxy_url,
        )

    def read(self, search_results: list[SearchResult]) -> list[RetrievedContent]:
        contents: list[RetrievedContent] = []
        seen_urls: set[str] = set()
        readable_count = 0

        for result in search_results:
            if result.status != "success" or not result.url:
                contents.append(
                    RetrievedContent(
                        title=result.title,
                        url=result.url,
                        source_type=result.source_type,
                        query=result.query,
                        status="skipped",
                        error_message="Only successful search results with URLs are read.",
                    )
                )
                continue

            normalized_url = result.url.rstrip("/")
            if normalized_url in seen_urls:
                contents.append(
                    RetrievedContent(
                        title=result.title,
                        url=result.url,
                        source_type=result.source_type,
                        query=result.query,
                        status="skipped",
                        error_message="Duplicate URL already read.",
                    )
                )
                continue

            if readable_count >= self.max_results_to_read:
                contents.append(
                    RetrievedContent(
                        title=result.title,
                        url=result.url,
                        source_type=result.source_type,
                        query=result.query,
                        status="skipped",
                        error_message="Read limit reached for this run.",
                    )
                )
                continue

            seen_urls.add(normalized_url)
            readable_count += 1
            if self._is_github_repository_result(result):
                contents.append(self.repo_reader.read(result))
            else:
                contents.append(self.page_reader.read(result))

        return contents

    def _is_github_repository_result(self, result: SearchResult) -> bool:
        if result.source_type == "github":
            return True
        return self.repo_reader.parse_github_repo(result.url) is not None
