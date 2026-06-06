from __future__ import annotations

import json
from typing import Any

from skillpilot.models import ParsedRequirement, TypeClassification
from skillpilot.skills.core import LLMProvider
from skillpilot.utils import extract_json_object


class ExtensionTypeClassifier:
    def __init__(self, llm: LLMProvider | None = None) -> None:
        self.llm = llm

    def classify(self, requirement: ParsedRequirement) -> TypeClassification:
        if self.llm is not None:
            classification = self._classify_with_llm(requirement)
            if classification is not None:
                return classification
        return self._fallback_classify(requirement)

    def _classify_with_llm(
        self,
        requirement: ParsedRequirement,
    ) -> TypeClassification | None:
        prompt = (
            "你是 SkillPilot 的扩展类型判断 skill。请根据结构化需求判断最适合 Claude Skill、"
            "Claude Code Plugin、MCP Server、mixed 还是 unknown。返回严格 JSON，不要 Markdown。"
            "字段：recommended_type, confidence, reason。recommended_type 只能是 "
            "skill/mcp/plugin/mixed/unknown；confidence 为 0-1；reason 用中文说明语义依据。"
            "不要只靠关键词，优先判断任务需要的是说明型能力、代码工作流、外部服务连接，还是组合方案。\n"
            f"需求：{requirement.model_dump()}"
        )
        try:
            response = self.llm.generate(prompt)
            payload = json.loads(extract_json_object(getattr(response, "text", str(response))))
        except Exception:  # noqa: BLE001 - classifier should fall back to deterministic rules.
            return None

        recommended_type = payload.get("recommended_type")
        if recommended_type not in {"skill", "mcp", "plugin", "mixed", "unknown"}:
            return None
        confidence = self._clamp_confidence(payload.get("confidence"))
        reason = str(payload.get("reason") or "").strip()
        if not reason:
            reason = "LLM 根据需求语义完成扩展类型判断。"
        return TypeClassification(
            recommended_type=recommended_type,
            confidence=confidence,
            reason=f"LLM 类型判断：{reason}",
        )

    def _fallback_classify(self, requirement: ParsedRequirement) -> TypeClassification:
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

    def _clamp_confidence(self, value: Any) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return 0.5
        return max(0.0, min(1.0, confidence))
