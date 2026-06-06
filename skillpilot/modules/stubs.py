from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from skillpilot.models import (
    Candidate,
    CandidateEvaluation,
    Decision,
    ParsedRequirement,
    RetrievedContent,
    SearchPlan,
    SearchQuery,
    SearchSource,
    TypeClassification,
)
from skillpilot.modules.source_catalog import SourceCatalog


class ParserLLM(Protocol):
    def generate(self, prompt: str) -> Any:
        ...


class RequirementParser:
    def __init__(self, llm: ParserLLM | None = None) -> None:
        self.llm = llm

    def parse(self, text: str) -> ParsedRequirement:
        if self.llm is None:
            return self._fallback(text, "LLM parser is not configured.")

        prompt = self._build_prompt(text)
        try:
            response = self.llm.generate(prompt)
            response_text = getattr(response, "text", str(response))
            payload = json.loads(self._extract_json(response_text))
            return self._from_payload(text, payload)
        except Exception as exc:  # noqa: BLE001 - parsing should continue with traceable fallback.
            return self._fallback(text, f"LLM parser failed: {exc}")

    def _from_payload(self, text: str, payload: dict[str, Any]) -> ParsedRequirement:
        capabilities = payload.get("desired_capabilities")
        if not isinstance(capabilities, list):
            capabilities = []
        normalized_capabilities = [
            str(capability).strip().lower().replace(" ", "_").replace("-", "_")
            for capability in capabilities
            if str(capability).strip()
        ]
        return ParsedRequirement(
            raw_text=text,
            task_domain=str(payload.get("task_domain") or "general").strip() or "general",
            desired_capabilities=normalized_capabilities or ["general_guidance"],
            requires_codebase_access=bool(payload.get("requires_codebase_access", False)),
            requires_command_execution=bool(payload.get("requires_command_execution", False)),
            requires_external_service=bool(payload.get("requires_external_service", False)),
            risk_tolerance=str(payload.get("risk_tolerance") or "medium").strip() or "medium",
        )

    def _fallback(self, text: str, reason: str) -> ParsedRequirement:
        lower = text.lower()
        capabilities: list[str] = []

        if "测试" in text or "test" in lower:
            capabilities.extend(["generate_tests", "analyze_test_failures"])
        if "github" in lower or "issue" in lower:
            capabilities.extend(["github_issue_read", "codebase_access"])
        if "论文" in text or "引用" in text:
            capabilities.extend(["writing_review", "citation_check"])
        if "课件" in text or "作业" in text or "知识点" in text:
            capabilities.extend(["knowledge_hint", "answer_guardrail"])
        if "pdf" in lower or "文档" in text or "文件" in text:
            capabilities.extend(["pdf_reading", "document_parsing"])
        if any(term in lower for term in ("poster", "design", "image")) or any(
            term in text for term in ("海报", "设计", "图片", "图像", "视觉")
        ):
            capabilities.extend(["poster_design", "visual_design"])

        return ParsedRequirement(
            raw_text=text,
            task_domain=self._infer_domain(text),
            desired_capabilities=self._dedupe_values(capabilities) or ["general_guidance"],
            risk_tolerance="medium",
        )

    def _infer_domain(self, text: str) -> str:
        lower = text.lower()
        if "测试" in text or "代码" in text or "github" in lower:
            return "software_engineering"
        if "pdf" in lower or "文档" in text or "文件" in text:
            return "document_processing"
        if "论文" in text or "引用" in text:
            return "academic_writing"
        if "课件" in text or "作业" in text:
            return "education"
        if any(term in lower for term in ("poster", "design", "image")) or any(
            term in text for term in ("海报", "设计", "图片", "图像", "视觉")
        ):
            return "visual_design"
        return "general"

    def _dedupe_values(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        deduped: list[str] = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            deduped.append(value)
        return deduped

    def _build_prompt(self, text: str) -> str:
        return f"""You are the requirement extraction module for SkillPilot.

Extract a structured requirement from the user's request. Return ONLY valid JSON.
Do not wrap the JSON in markdown. Do not include explanations.

Schema:
{{
  "task_domain": "short_snake_case_domain",
  "desired_capabilities": ["short_snake_case_capability"],
  "requires_codebase_access": false,
  "requires_command_execution": false,
  "requires_external_service": false,
  "risk_tolerance": "low|medium|high"
}}

Guidance:
- Capabilities should be specific and search-friendly, e.g. "pdf_reading", "document_parsing", "github_issue_read", "unit_test_generation", "citation_check", "homework_hinting".
- Infer capabilities from meaning, not only from exact keywords.
- Use boolean fields to describe operational needs.
- If the request is ambiguous, still infer the most likely capabilities conservatively.

User request:
{text}
"""

    def _extract_json(self, text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return stripped
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("LLM response did not contain a JSON object.")
        return stripped[start : end + 1]


class ExtensionTypeClassifier:
    def classify(self, requirement: ParsedRequirement) -> TypeClassification:
        text = requirement.raw_text.lower()
        if "skill" in text or "技能" in requirement.raw_text:
            return TypeClassification(
                recommended_type="skill",
                confidence=0.86,
                reason="用户明确提到 Skill，优先规划 Claude Skill 方向。",
            )
        if "插件" in requirement.raw_text or "plugin" in text:
            return TypeClassification(
                recommended_type="plugin",
                confidence=0.74,
                reason="用户明确提到插件，优先规划 Claude Code Plugin 方向，同时保留后续安全评估。",
            )
        if requirement.requires_external_service:
            return TypeClassification(
                recommended_type="mcp",
                confidence=0.78,
                reason="需求涉及外部服务或仓库访问，MCP 更适合作为工具连接层。",
            )
        if "一整套" in requirement.raw_text or "workflow" in text:
            return TypeClassification(
                recommended_type="plugin",
                confidence=0.7,
                reason="需求像完整工作流，后续可扩展为 Plugin 方案。",
            )
        return TypeClassification(
            recommended_type="skill",
            confidence=0.82,
            reason="需求主要是规范 Claude 如何完成任务，适合先以 Skill 表达。",
        )


class SourcePlanner:
    def __init__(self) -> None:
        self.catalog = SourceCatalog()

    def plan(self, requirement: ParsedRequirement, classification: TypeClassification) -> SearchPlan:
        sources = self.catalog.sources_for(classification.recommended_type)
        queries = self._build_queries(requirement, classification, sources)
        return SearchPlan(
            extension_type=classification.recommended_type,
            sources=sources,
            queries=queries,
        )

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


class LocalCandidateCache:
    def __init__(self, cache_path: Path) -> None:
        self.cache_path = cache_path

    def load(self) -> list[Candidate]:
        data = json.loads(self.cache_path.read_text(encoding="utf-8"))
        return [Candidate(**item) for item in data]


class EvaluationLLM(Protocol):
    def generate(self, prompt: str) -> Any:
        ...


class CandidateEvaluator:
    def __init__(self, llm: EvaluationLLM | None = None) -> None:
        self.llm = llm

    def evaluate(
        self,
        requirement: ParsedRequirement,
        classification: TypeClassification,
        candidates: list[Candidate],
    ) -> list[CandidateEvaluation]:
        evaluations = [
            self._evaluate_one(requirement, classification, candidate)
            for candidate in candidates
        ]
        return sorted(evaluations, key=lambda item: item.match_score, reverse=True)

    def evaluate_retrieved(
        self,
        requirement: ParsedRequirement,
        classification: TypeClassification,
        retrieved_contents: list[RetrievedContent],
    ) -> list[CandidateEvaluation]:
        evaluations = [
            self._evaluate_content(requirement, classification, content)
            for content in retrieved_contents
            if content.status == "success" and content.url and content.content.strip()
        ]
        return sorted(evaluations, key=lambda item: item.match_score, reverse=True)

    def _evaluate_content(
        self,
        requirement: ParsedRequirement,
        classification: TypeClassification,
        content: RetrievedContent,
    ) -> CandidateEvaluation:
        llm_result = self._score_content_with_llm(requirement, classification, content)
        candidate = llm_result["candidate"]
        type_score = self._type_score(classification, candidate)
        match_score = (
            llm_result["capability_score"] * 0.45
            + type_score * 0.15
            + llm_result["documentation_score"] * 0.20
            + llm_result["safety_score"] * 0.20
        )

        return CandidateEvaluation(
            candidate=candidate,
            match_score=round(match_score, 2),
            capability_score=round(llm_result["capability_score"], 2),
            type_score=round(type_score, 2),
            documentation_score=round(llm_result["documentation_score"], 2),
            safety_score=round(llm_result["safety_score"], 2),
            matched_capabilities=llm_result["matched_capabilities"],
            missing_capabilities=llm_result["missing_capabilities"],
            risk_level=llm_result["risk_level"],
            risk_reasons=llm_result["risk_reasons"],
            reason=llm_result["reason"],
        )

    def _score_content_with_llm(
        self,
        requirement: ParsedRequirement,
        classification: TypeClassification,
        content: RetrievedContent,
    ) -> dict[str, Any]:
        if self.llm is None:
            candidate = self._fallback_candidate(content, classification)
            result = self._fallback_score(requirement, candidate)
            result["candidate"] = candidate
            result["reason"] = (
                "LLM 评分未启用，使用本地兜底规则；正常运行应由 LLM 直接阅读原文评分。"
            )
            return result

        prompt = self._build_content_evaluation_prompt(requirement, classification, content)
        try:
            response = self.llm.generate(prompt)
            text = getattr(response, "text", str(response))
            return self._normalize_content_llm_result(
                json.loads(self._extract_json(text)),
                requirement,
                classification,
                content,
            )
        except Exception:  # noqa: BLE001 - evaluation should continue with traceable fallback.
            candidate = self._fallback_candidate(content, classification)
            result = self._fallback_score(requirement, candidate)
            result["candidate"] = candidate
            result["reason"] = "LLM 评分未完成，使用本地兜底规则。"
            return result

    def _build_content_evaluation_prompt(
        self,
        requirement: ParsedRequirement,
        classification: TypeClassification,
        content: RetrievedContent,
    ) -> str:
        payload = {
            "requirement": {
                "raw_text": requirement.raw_text,
                "task_domain": requirement.task_domain,
                "desired_capabilities": requirement.desired_capabilities,
            },
            "classification": {
                "recommended_type": classification.recommended_type,
            },
            "retrieved_content": {
                "title": content.title,
                "url": content.url,
                "source_type": content.source_type,
                "source_id": content.source_id,
                "metadata": content.metadata,
                "content": content.content,
            },
        }
        return (
            "你是 SkillPilot 的候选资源理解与评分模块。请直接阅读 retrieved_content.content 原文，"
            "判断它是否是一个具体可用候选，并评估是否满足用户需求。\n"
            "返回严格 JSON，不要 Markdown。字段：candidate_name, extension_type, description, "
            "capabilities, installation, dependencies, permissions, maintainer, last_updated, evidence, "
            "capability_score, documentation_score, safety_score, matched_capabilities, "
            "missing_capabilities, risk_level, risk_reasons, reason。\n"
            "extension_type 只能是 skill/mcp/plugin/mixed/unknown；risk_level 只能是 low/medium/high；"
            "分数范围 0-1。reason 必须是中文，并包含“LLM 结构化评分”。\n"
            "不要因为搜索词或目录名相关就给高分，必须以原文证据为准。"
            "如果原文只是列表、市场页、模板目录或教程而不是具体候选，capability_score 应较低并说明原因。\n"
            f"数据：{json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}"
        )

    def _normalize_content_llm_result(
        self,
        data: dict[str, Any],
        requirement: ParsedRequirement,
        classification: TypeClassification,
        content: RetrievedContent,
    ) -> dict[str, Any]:
        candidate = Candidate(
            name=str(data.get("candidate_name") or content.title or content.url).strip(),
            extension_type=self._extension_type(data.get("extension_type"), classification),
            source_url=content.url,
            description=str(data.get("description") or self._fallback_description(content)).strip(),
            capabilities=self._string_list(data.get("capabilities")),
            installation=self._optional_string(data.get("installation")),
            dependencies=self._string_list(data.get("dependencies")),
            permissions=self._string_list(data.get("permissions")),
            maintainer=self._optional_string(data.get("maintainer"))
            or self._optional_string(content.metadata.get("author")),
            last_updated=self._optional_string(data.get("last_updated"))
            or self._optional_string(content.metadata.get("last_updated"))
            or self._optional_string(content.metadata.get("updated_at")),
            evidence=self._string_list(data.get("evidence")),
        )
        normalized = self._normalize_llm_result(data, requirement)
        normalized["candidate"] = candidate
        return normalized

    def _fallback_candidate(
        self,
        content: RetrievedContent,
        classification: TypeClassification,
    ) -> Candidate:
        return Candidate(
            name=str(content.metadata.get("full_name") or content.title or content.url).strip(),
            extension_type=classification.recommended_type
            if classification.recommended_type in {"skill", "mcp", "plugin"}
            else "unknown",
            source_url=content.url,
            description=self._fallback_description(content),
            capabilities=[],
            installation=None,
            dependencies=[],
            permissions=[],
            maintainer=self._optional_string(content.metadata.get("author")),
            last_updated=self._optional_string(content.metadata.get("last_updated"))
            or self._optional_string(content.metadata.get("updated_at")),
            evidence=self._fallback_evidence(content),
        )

    def _fallback_description(self, content: RetrievedContent) -> str:
        metadata_description = content.metadata.get("description")
        if isinstance(metadata_description, str) and metadata_description.strip():
            return metadata_description.strip()
        for line in content.content.splitlines():
            cleaned = " ".join(line.split()).strip(" -`*_#\t")
            if len(cleaned) >= 30:
                return cleaned
        return "No clear description found in retrieved content."

    def _fallback_evidence(self, content: RetrievedContent) -> list[str]:
        evidence: list[str] = []
        for line in content.content.splitlines():
            cleaned = " ".join(line.split()).strip(" -`*_#\t")
            if len(cleaned) < 20:
                continue
            evidence.append(cleaned)
            if len(evidence) >= 4:
                break
        return evidence

    def _extension_type(self, value: Any, classification: TypeClassification) -> str:
        if value in {"skill", "mcp", "plugin", "mixed", "unknown"}:
            return str(value)
        if classification.recommended_type in {"skill", "mcp", "plugin", "mixed"}:
            return classification.recommended_type
        return "unknown"

    def _optional_string(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _evaluate_one(
        self,
        requirement: ParsedRequirement,
        classification: TypeClassification,
        candidate: Candidate,
    ) -> CandidateEvaluation:
        llm_result = self._score_with_llm(requirement, classification, candidate)
        type_score = self._type_score(classification, candidate)
        match_score = (
            llm_result["capability_score"] * 0.45
            + type_score * 0.15
            + llm_result["documentation_score"] * 0.20
            + llm_result["safety_score"] * 0.20
        )

        return CandidateEvaluation(
            candidate=candidate,
            match_score=round(match_score, 2),
            capability_score=round(llm_result["capability_score"], 2),
            type_score=round(type_score, 2),
            documentation_score=round(llm_result["documentation_score"], 2),
            safety_score=round(llm_result["safety_score"], 2),
            matched_capabilities=llm_result["matched_capabilities"],
            missing_capabilities=llm_result["missing_capabilities"],
            risk_level=llm_result["risk_level"],
            risk_reasons=llm_result["risk_reasons"],
            reason=llm_result["reason"],
        )

    def _score_with_llm(
        self,
        requirement: ParsedRequirement,
        classification: TypeClassification,
        candidate: Candidate,
    ) -> dict[str, Any]:
        if self.llm is None:
            result = self._fallback_score(requirement, candidate)
            result["reason"] = (
                "LLM 评分未启用，使用本地兜底规则生成能力、文档和安全分；"
                "正常运行应启用 LLM 结构化评分。"
            )
            return result

        prompt = self._build_evaluation_prompt(requirement, classification, candidate)
        try:
            response = self.llm.generate(prompt)
            text = getattr(response, "text", str(response))
            return self._normalize_llm_result(json.loads(self._extract_json(text)), requirement)
        except Exception:  # noqa: BLE001 - evaluation should continue with traceable fallback.
            result = self._fallback_score(requirement, candidate)
            result["reason"] = "LLM 评分未完成，使用本地兜底规则。"
            return result

    def _build_evaluation_prompt(
        self,
        requirement: ParsedRequirement,
        classification: TypeClassification,
        candidate: Candidate,
    ) -> str:
        payload = {
            "requirement": {
                "raw_text": requirement.raw_text,
                "task_domain": requirement.task_domain,
                "desired_capabilities": requirement.desired_capabilities,
            },
            "classification": {
                "recommended_type": classification.recommended_type,
            },
            "candidate": {
                "name": candidate.name,
                "extension_type": candidate.extension_type,
                "source_url": candidate.source_url,
                "description": self._truncate_text(candidate.description, 700),
                "capabilities": candidate.capabilities,
                "installation": self._truncate_text(candidate.installation or "", 220),
                "dependencies": candidate.dependencies,
                "permissions": candidate.permissions,
                "evidence": [
                    self._truncate_text(item, 260)
                    for item in candidate.evidence[:4]
                ],
            },
        }
        return (
            "你是 SkillPilot 候选评分器。只根据给定候选判断是否满足用户需求。\n"
            "返回严格 JSON，不要 Markdown。字段：capability_score, documentation_score, "
            "safety_score, matched_capabilities, missing_capabilities, risk_level, "
            "risk_reasons, reason。\n"
            "分数范围 0-1。risk_level 只能是 low/medium/high。reason 必须是中文，并包含“LLM 结构化评分”。\n"
            "能力分只看候选真实能力；安全分重点看 token/API key、命令执行、hook、写文件/写仓库、外部服务风险。\n"
            f"数据：{json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}"
        )

    def _truncate_text(self, text: str, max_length: int) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= max_length:
            return normalized
        return normalized[:max_length].rstrip() + "..."

    def _extract_json(self, text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = stripped.strip("`").strip()
            if stripped.startswith("json"):
                stripped = stripped.removeprefix("json").strip()
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError("LLM response did not contain a JSON object.")
        return stripped[start : end + 1]

    def _normalize_llm_result(
        self,
        data: dict[str, Any],
        requirement: ParsedRequirement,
    ) -> dict[str, Any]:
        risk_level = data.get("risk_level")
        if risk_level not in {"low", "medium", "high"}:
            risk_level = "medium"
        matched = self._string_list(data.get("matched_capabilities"))
        missing = self._string_list(data.get("missing_capabilities"))
        if not matched and not missing:
            missing = list(requirement.desired_capabilities)
        risk_reasons = self._string_list(data.get("risk_reasons"))
        if not risk_reasons:
            risk_reasons = ["LLM 未给出具体风险原因，需人工复核。"]
        reason = str(data.get("reason") or "LLM 结构化评分。").strip()
        return {
            "capability_score": self._clamp_score(data.get("capability_score")),
            "documentation_score": self._clamp_score(data.get("documentation_score")),
            "safety_score": self._clamp_score(data.get("safety_score")),
            "matched_capabilities": matched,
            "missing_capabilities": missing,
            "risk_level": risk_level,
            "risk_reasons": risk_reasons,
            "reason": reason,
        }

    def _fallback_score(
        self,
        requirement: ParsedRequirement,
        candidate: Candidate,
    ) -> dict[str, Any]:
        required = requirement.desired_capabilities or ["general_guidance"]
        offered = set(candidate.capabilities) | set(candidate.permissions)
        aliases = {
            "pdf_reading": {"pdf_reading", "read_documents"},
            "document_parsing": {"document_parsing", "read_documents"},
            "poster_design": {"poster_design", "visual_design", "image_generation"},
            "visual_design": {"visual_design", "poster_design", "image_generation"},
            "general_guidance": {"general_guidance"},
        }
        matched = sorted(
            capability
            for capability in required
            if aliases.get(capability, {capability}) & offered
        )
        missing = sorted(
            capability
            for capability in required
            if not aliases.get(capability, {capability}) & offered
        )
        documentation_score = min(
            1.0,
            (0.25 if candidate.description else 0.0)
            + min(0.40, 0.12 * len(candidate.evidence))
            + (0.20 if candidate.installation else 0.0)
            + (0.15 if candidate.dependencies or candidate.permissions else 0.0),
        )
        permissions = set(candidate.permissions)
        dependencies = set(candidate.dependencies)
        risk_reasons: list[str] = []
        high_risk = bool({"write_repository", "command_execution"} & permissions) or bool(
            {"api_token", "github_token"} & dependencies
        )
        medium_risk = bool({"external_service", "read_repository", "read_documents"} & permissions)
        if "write_repository" in permissions:
            risk_reasons.append("候选涉及仓库写入权限，可能修改代码、提交或创建 PR。")
        if "command_execution" in permissions:
            risk_reasons.append("候选涉及命令执行，需要避免自动运行不可信脚本。")
        if {"api_token", "github_token"} & dependencies:
            risk_reasons.append("候选需要 token 或 API 凭据，应避免在未审计配置中暴露。")
        if "external_service" in permissions:
            risk_reasons.append("候选需要连接外部服务，可能涉及账号、网络请求或远程数据。")
        if "read_repository" in permissions:
            risk_reasons.append("候选会读取仓库或代码库，需要确认访问范围。")
        if "read_documents" in permissions:
            risk_reasons.append("候选会读取本地或上传文档，需要确认文件范围和隐私。")
        if high_risk:
            risk_level = "high"
            safety_score = 0.0
        elif medium_risk:
            risk_level = "medium"
            safety_score = 0.55
        else:
            risk_level = "low"
            safety_score = 1.0
            risk_reasons.append("未发现明显的高危权限或敏感依赖。")
        return {
            "capability_score": len(matched) / max(len(required), 1),
            "documentation_score": documentation_score,
            "safety_score": safety_score,
            "matched_capabilities": matched,
            "missing_capabilities": missing,
            "risk_level": risk_level,
            "risk_reasons": risk_reasons,
            "reason": "",
        }

    def _clamp_score(self, value: Any) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, score))

    def _string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def _type_score(
        self,
        classification: TypeClassification,
        candidate: Candidate,
    ) -> float:
        if candidate.extension_type == classification.recommended_type:
            return 1.0
        if classification.recommended_type == "mixed" and candidate.extension_type in {
            "skill",
            "mcp",
            "plugin",
        }:
            return 0.8
        if classification.recommended_type == "unknown":
            return 0.5
        if candidate.extension_type == "unknown":
            return 0.2
        return 0.25


class DecisionGate:
    def build_custom(self, reason: str) -> Decision:
        return Decision(
            decision_type="build_custom_skill",
            reason=reason,
            selected_candidates=[],
        )

    def decide(self, evaluations: list[CandidateEvaluation]) -> Decision:
        best = evaluations[0] if evaluations else None
        if best is None or best.match_score < 0.45:
            return Decision(
                decision_type="build_custom_skill",
                reason=(
                    "实时搜索或可用候选没有提供足够证据支撑直接推荐，"
                    "进入自定义 Skill 草案流程。"
                ),
                selected_candidates=[],
            )
        if best.risk_level == "high":
            return Decision(
                decision_type="build_custom_skill",
                reason=(
                    "最高匹配候选包含高风险权限或敏感凭据依赖，"
                    "不建议直接安装；优先生成更小权限的自定义 Skill，并把候选作为人工审查参考。"
                ),
                selected_candidates=evaluations[:3],
            )
        if best.match_score >= 0.75 and best.risk_level != "high":
            return Decision(
                decision_type="recommend_existing",
                reason="存在匹配度较高且风险为低或中的候选资源，可作为现成资源推荐。",
                selected_candidates=evaluations[:3],
            )
        return Decision(
            decision_type="recommend_with_custom_extension",
            reason="候选资源有中等相关性，建议参考现有资源并用自定义 Skill 补齐缺失能力。",
            selected_candidates=evaluations[:3],
        )
