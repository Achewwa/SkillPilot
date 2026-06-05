from __future__ import annotations

import re

from skillpilot.models import (
    Candidate,
    ExtensionType,
    RetrievedContent,
    SearchResult,
    TypeClassification,
)


class CandidateExtractor:
    """Convert read search results into conservative Candidate records."""

    CAPABILITY_PATTERNS = (
        ("generate_tests", ("unit test", "pytest", "test generation", "generate tests", "testing")),
        ("analyze_test_failures", ("test failure", "failing test", "debug test", "failure analysis")),
        ("github_issue_read", ("github issue", "issues", "pull request", "repository issue")),
        ("codebase_access", ("codebase", "repository", "source code", "read code")),
        ("writing_review", ("paper", "academic", "review", "writing")),
        ("citation_check", ("citation", "reference", "bibliography")),
        ("knowledge_hint", ("homework", "course", "lesson", "knowledge point", "hint")),
        ("answer_guardrail", ("avoid direct answer", "guardrail", "do not reveal", "hint only")),
        ("pdf_reading", ("pdf", "document reader", "extract text")),
        ("document_parsing", ("document", "parse", "markdown", "text extraction")),
    )
    INSTALL_KEYWORDS = (
        "install",
        "installation",
        "setup",
        "usage",
        "npm install",
        "pip install",
        "uvx",
        "npx",
        "claude mcp",
    )
    EVIDENCE_KEYWORDS = (
        "claude",
        "skill",
        "skill.md",
        "mcp",
        "model context protocol",
        "plugin",
        "install",
        "pdf",
        "github",
        "test",
    )

    def extract(
        self,
        search_results: list[SearchResult],
        retrieved_contents: list[RetrievedContent],
        classification: TypeClassification,
    ) -> list[Candidate]:
        result_by_url = {
            self._normalize_url(result.url): result
            for result in search_results
            if result.url
        }
        candidates: list[Candidate] = []
        seen_urls: set[str] = set()

        for content in retrieved_contents:
            if content.status != "success" or not content.url or not content.content.strip():
                continue
            normalized_url = self._normalize_url(content.url)
            if normalized_url in seen_urls:
                continue
            result = result_by_url.get(normalized_url)
            candidate = self._extract_one(content, result, classification)
            if candidate:
                candidates.append(candidate)
                seen_urls.add(normalized_url)

        return candidates

    def _extract_one(
        self,
        content: RetrievedContent,
        result: SearchResult | None,
        classification: TypeClassification,
    ) -> Candidate | None:
        name = self._extract_name(content, result)
        description = self._extract_description(content, result)
        evidence = self._extract_evidence(content, result)
        if not name or not (description or evidence):
            return None

        return Candidate(
            name=name,
            extension_type=self._infer_extension_type(content, result, classification),
            source_url=content.url,
            description=description or "No clear description found in retrieved content.",
            capabilities=self._extract_capabilities(content, result),
            installation=self._extract_installation(content),
            dependencies=self._extract_dependencies(content),
            permissions=self._extract_permissions(content),
            maintainer=self._extract_maintainer(content),
            last_updated=content.metadata.get("last_updated"),
            evidence=evidence,
        )

    def _extract_name(
        self,
        content: RetrievedContent,
        result: SearchResult | None,
    ) -> str:
        full_name = content.metadata.get("full_name")
        if isinstance(full_name, str) and full_name.strip():
            return full_name.strip()
        title = content.title or (result.title if result else "")
        return self._clean_text(title, max_length=120)

    def _infer_extension_type(
        self,
        content: RetrievedContent,
        result: SearchResult | None,
        classification: TypeClassification,
    ) -> ExtensionType:
        haystack = self._haystack(content, result)
        scores = {
            "skill": self._score(haystack, ("skill.md", "claude skill", "/skills/", "skill template")),
            "mcp": self._score(haystack, ("model context protocol", "mcp server", "claude mcp", "mcp-server")),
            "plugin": self._score(haystack, ("claude code plugin", "plugin", "claude-code-plugin")),
        }
        best_type, best_score = max(scores.items(), key=lambda item: item[1])
        if best_score > 0:
            return best_type  # type: ignore[return-value]
        if classification.recommended_type in {"skill", "mcp", "plugin"}:
            return classification.recommended_type
        return "unknown"

    def _score(self, haystack: str, needles: tuple[str, ...]) -> int:
        return sum(1 for needle in needles if needle in haystack)

    def _extract_description(
        self,
        content: RetrievedContent,
        result: SearchResult | None,
    ) -> str:
        metadata_description = content.metadata.get("description")
        if isinstance(metadata_description, str) and metadata_description.strip():
            return self._clean_text(metadata_description, max_length=300)
        if result and result.snippet.strip():
            return self._clean_text(result.snippet, max_length=300)

        for line in content.content.splitlines():
            cleaned = self._clean_text(line, max_length=300)
            if not cleaned or cleaned.startswith(("#", "Description:", "License:", "Stars:")):
                continue
            if len(cleaned) >= 35:
                return cleaned
        return ""

    def _extract_capabilities(
        self,
        content: RetrievedContent,
        result: SearchResult | None,
    ) -> list[str]:
        haystack = self._haystack(content, result)
        capabilities = [
            capability
            for capability, keywords in self.CAPABILITY_PATTERNS
            if any(keyword in haystack for keyword in keywords)
        ]
        return self._dedupe(capabilities)

    def _extract_installation(self, content: RetrievedContent) -> str | None:
        for line in content.content.splitlines():
            lowered = line.lower()
            if any(keyword in lowered for keyword in self.INSTALL_KEYWORDS):
                return self._clean_text(line, max_length=260)
        return None

    def _extract_dependencies(self, content: RetrievedContent) -> list[str]:
        haystack = self._haystack(content, None)
        dependencies: list[str] = []
        if "package.json" in content.metadata.get("common_files", []) or "npm install" in haystack or "npx " in haystack:
            dependencies.append("node")
        if "pyproject.toml" in content.metadata.get("common_files", []) or "pip install" in haystack or "python" in haystack:
            dependencies.append("python")
        if "docker" in haystack:
            dependencies.append("docker")
        if "github_token" in haystack or "github token" in haystack or "gh_token" in haystack:
            dependencies.append("github_token")
        if "api key" in haystack or "api_key" in haystack or "access token" in haystack:
            dependencies.append("api_token")
        return self._dedupe(dependencies)

    def _extract_permissions(self, content: RetrievedContent) -> list[str]:
        haystack = self._haystack(content, None)
        permissions: list[str] = []
        if any(term in haystack for term in ("github", "api key", "token", "http", "server")):
            permissions.append("external_service")
        if any(term in haystack for term in ("repository", "codebase", "read code", "github issue")):
            permissions.append("read_repository")
        if any(term in haystack for term in ("write access", "push", "commit", "create pull request", "delete branch")):
            permissions.append("write_repository")
        if any(term in haystack for term in ("read file", "local file", "pdf", "document")):
            permissions.append("read_documents")
        if any(term in haystack for term in ("shell", "subprocess", "execute command", "run command")):
            permissions.append("command_execution")
        return self._dedupe(permissions)

    def _extract_maintainer(self, content: RetrievedContent) -> str | None:
        full_name = content.metadata.get("full_name")
        if isinstance(full_name, str) and "/" in full_name:
            return full_name.split("/", 1)[0]
        return None

    def _extract_evidence(
        self,
        content: RetrievedContent,
        result: SearchResult | None,
    ) -> list[str]:
        evidence: list[str] = []
        for line in content.content.splitlines():
            cleaned = self._clean_text(line, max_length=260)
            lowered = cleaned.lower()
            if len(cleaned) < 20:
                continue
            if any(keyword in lowered for keyword in self.EVIDENCE_KEYWORDS):
                evidence.append(cleaned)
            if len(evidence) >= 4:
                break

        if result and result.snippet and len(evidence) < 4:
            evidence.append(f"Search snippet: {self._clean_text(result.snippet, max_length=220)}")
        return self._dedupe(evidence)

    def _haystack(
        self,
        content: RetrievedContent,
        result: SearchResult | None,
    ) -> str:
        parts = [
            content.title,
            content.query,
            content.content,
            str(content.metadata.get("description") or ""),
            " ".join(content.metadata.get("topics") or []),
        ]
        if result:
            parts.extend([result.title, result.snippet, result.query])
        return "\n".join(parts).lower()

    def _clean_text(self, text: str, max_length: int) -> str:
        cleaned = re.sub(r"\s+", " ", text).strip(" -`*_#\t")
        if len(cleaned) <= max_length:
            return cleaned
        return cleaned[:max_length].rstrip() + "..."

    def _normalize_url(self, url: str) -> str:
        return url.rstrip("/")

    def _dedupe(self, items: list[str]) -> list[str]:
        seen: set[str] = set()
        deduped: list[str] = []
        for item in items:
            if not item or item in seen:
                continue
            seen.add(item)
            deduped.append(item)
        return deduped
