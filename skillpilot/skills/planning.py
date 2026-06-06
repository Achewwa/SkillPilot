from __future__ import annotations

import json

from skillpilot.models import (
    ParsedRequirement,
    SearchPlan,
    SearchQuery,
    SearchSource,
    TypeClassification,
)
from skillpilot.skills.discovery.source_catalog import SourceCatalog
from skillpilot.skills.core import LLMProvider
from skillpilot.utils import extract_json_object


class SourcePlanner:
    def __init__(self, llm: LLMProvider | None = None) -> None:
        self.llm = llm
        self.catalog = SourceCatalog()

    def plan(self, requirement: ParsedRequirement, classification: TypeClassification) -> SearchPlan:
        sources = self.catalog.sources_for(classification.recommended_type)
        queries = self._build_queries_with_llm(requirement, classification, sources)
        if not queries:
            queries = self._build_queries(requirement, classification, sources)
        return SearchPlan(
            extension_type=classification.recommended_type,
            sources=sources,
            queries=queries,
        )

    def _build_queries_with_llm(
        self,
        requirement: ParsedRequirement,
        classification: TypeClassification,
        sources: list[SearchSource],
    ) -> list[SearchQuery]:
        if self.llm is None:
            return []
        source_payload = [
            {
                "source_id": source.source_id,
                "name": source.name,
                "source_kind": source.source_kind,
                "extension_types": source.extension_types,
                "searcher_type": source.searcher_type,
                "reader_type": source.reader_type,
                "notes": source.notes,
            }
            for source in sources
        ]
        prompt = (
            "你是 SkillPilot 的 source-aware 查询规划 skill。请只基于给定 sources 为用户需求生成搜索查询。"
            "返回严格 JSON，不要 Markdown。字段：queries，每项包含 source_id, text, purpose。"
            "要求：1) 只能使用给定 source_id；2) 每个查询都应适配该 source 的生态和 searcher；"
            "3) 最多 5 条；4) text 应包含任务能力和 Claude Skill/MCP/plugin 等必要生态词；"
            "5) 不要编造新的 source。\n"
            f"需求：{requirement.model_dump()}\n"
            f"类型判断：{classification.model_dump()}\n"
            f"sources：{json.dumps(source_payload, ensure_ascii=False)}"
        )
        try:
            response = self.llm.generate(prompt)
            payload = json.loads(extract_json_object(getattr(response, "text", str(response))))
        except Exception:  # noqa: BLE001 - query planning should fall back to deterministic templates.
            return []

        by_id = {source.source_id: source for source in sources}
        patterns: list[tuple[str, str, str, str | None]] = []
        for item in payload.get("queries") or []:
            if not isinstance(item, dict):
                continue
            source_id = str(item.get("source_id") or "").strip()
            text = str(item.get("text") or "").strip()
            purpose = str(item.get("purpose") or "").strip()
            if source_id not in by_id or not text:
                continue
            patterns.append(
                (
                    "source",
                    text,
                    purpose or f"Search inside the curated source `{source_id}`.",
                    source_id,
                )
            )
        return self._dedupe_queries(patterns, classification.recommended_type)

    def _build_queries(
        self,
        requirement: ParsedRequirement,
        classification: TypeClassification,
        sources: list[SearchSource],
    ) -> list[SearchQuery]:
        extension_type = classification.recommended_type
        capability_text = self._capability_terms(requirement)
        raw_text = requirement.raw_text.strip()

        patterns = [
            (
                "source",
                self._source_query_text(source, capability_text, raw_text),
                f"Search inside the curated source `{source.source_id}`.",
                source.source_id,
            )
            for source in sources
        ]
        return self._dedupe_queries(patterns, extension_type)

    def _source_query_text(self, source: SearchSource, capability_text: str, raw_text: str) -> str:
        ecosystem_terms = self._source_ecosystem_terms(source)
        terms_by_kind = {
            "official_docs": "official docs",
            "official_registry_api": "official registry",
            "community_registry_api": "registry API",
            "commercial_hosted_registry_api": "hosted registry",
            "official_github_marketplace_repo": "marketplace.json",
            "community_github_marketplace_repo": "marketplace.json",
            "official_example_repo": "examples README",
            "community_awesome_list": "awesome list",
            "web_directory": "web directory",
            "github_search": "GitHub",
        }
        source_terms = terms_by_kind.get(source.source_kind, source.source_kind)
        if source.source_id == "skillsmp_directory":
            return f"{capability_text} {raw_text}".strip()
        if source.source_kind in {
            "official_github_marketplace_repo",
            "community_github_marketplace_repo",
        }:
            return f'{capability_text} {ecosystem_terms} {source.name} ".claude-plugin" marketplace.json'
        if source.source_kind.endswith("registry_api"):
            return f"{capability_text} {ecosystem_terms} {source.name} {source_terms}"
        return f"{capability_text} {ecosystem_terms} {source.name} {source_terms} {raw_text}"

    def _source_ecosystem_terms(self, source: SearchSource) -> str:
        if "plugin" in source.extension_types:
            return "Claude Code plugin"
        if "mcp" in source.extension_types:
            return "MCP server"
        if "skill" in source.extension_types:
            return "Claude Skill SKILL.md"
        return "Claude extension"

    def _capability_terms(self, requirement: ParsedRequirement) -> str:
        capability_labels = {
            "unit_test_generation": "Python unit test generation",
            "test_failure_analysis": "test failure analysis",
            "generate_tests": "Python unit test generation",
            "analyze_test_failures": "test failure analysis",
            "github_issue_read": "GitHub issue reader",
            "codebase_access": "codebase access",
            "writing_review": "academic writing review",
            "citation_check": "citation check",
            "knowledge_hint": "homework knowledge hint",
            "answer_guardrail": "avoid direct answers",
            "pdf_reading": "PDF reading",
            "document_parsing": "document parsing",
            "poster_design": "poster design",
            "visual_design": "visual design",
            "general_guidance": "general assistant guidance",
        }
        terms = [
            capability_labels.get(capability, capability.replace("_", " "))
            for capability in requirement.desired_capabilities
        ]
        if not terms:
            terms.append(requirement.task_domain.replace("_", " "))
        if terms == ["general assistant guidance"]:
            return requirement.raw_text.strip() or "general assistant guidance"
        return " ".join(terms[:3])

    def _dedupe_queries(
        self,
        patterns: list[tuple[str, str, str, str | None]],
        extension_type: str,
    ) -> list[SearchQuery]:
        queries: list[SearchQuery] = []
        seen: set[tuple[str | None, str, str]] = set()
        for source_type, text, purpose, source_id in patterns:
            normalized = " ".join(text.split())
            key = (source_id, source_type, normalized.lower())
            if key in seen:
                continue
            seen.add(key)
            queries.append(
                SearchQuery(
                    text=normalized,
                    source_type=source_type,  # type: ignore[arg-type]
                    extension_type=extension_type,  # type: ignore[arg-type]
                    purpose=purpose,
                    source_id=source_id,
                )
            )
            if len(queries) >= 5:
                break
        return queries
