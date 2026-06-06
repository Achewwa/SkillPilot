from __future__ import annotations

import json
from typing import Any

from skillpilot.models import ParsedRequirement
from skillpilot.skills.core import LLMProvider
from skillpilot.utils import dedupe_preserve_order, extract_json_object

ParserLLM = LLMProvider


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
        return dedupe_preserve_order(values)

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
        return extract_json_object(text)
