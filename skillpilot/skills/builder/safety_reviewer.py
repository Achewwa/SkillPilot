from __future__ import annotations

import json
from typing import Any

from skillpilot.models import ParsedRequirement, SafetyReviewResult, SkillSpec
from skillpilot.safety import RiskPolicy
from skillpilot.skills.core import LLMProvider
from skillpilot.utils import extract_json_object


class SafetyReviewer:
    def __init__(
        self,
        llm: LLMProvider | None = None,
        risk_policy: RiskPolicy | None = None,
    ) -> None:
        self.llm = llm
        self.risk_policy = risk_policy or RiskPolicy()

    def review(self, requirement: ParsedRequirement, spec: SkillSpec) -> SafetyReviewResult:
        rule_review = self._review_with_policy(requirement, spec)
        llm_review = self._review_with_llm(requirement, spec)
        if llm_review is None:
            return rule_review
        if not rule_review.allowed:
            return rule_review
        if rule_review.risk_level == "medium" and llm_review.risk_level == "low":
            return SafetyReviewResult(
                allowed=True,
                risk_level="medium",
                risk_reasons=rule_review.risk_reasons,
                safe_alternatives=rule_review.safe_alternatives,
            )
        return llm_review

    def _review_with_policy(
        self,
        requirement: ParsedRequirement,
        spec: SkillSpec,
    ) -> SafetyReviewResult:
        assessment = self.risk_policy.assess_skill_request(requirement, spec)
        return SafetyReviewResult(
            allowed=assessment.allowed,
            risk_level=assessment.risk_level,
            risk_reasons=assessment.risk_reasons,
            safe_alternatives=assessment.safe_alternatives,
        )

    def _review_with_llm(
        self,
        requirement: ParsedRequirement,
        spec: SkillSpec,
    ) -> SafetyReviewResult | None:
        if self.llm is None:
            return None
        prompt = (
            "你是 SkillPilot 的 Skill 构建安全审查 skill。请从语义上审查这个 Skill 规格是否可以生成。"
            "返回严格 JSON，不要 Markdown。字段：allowed, risk_level, risk_reasons, safe_alternatives。"
            "risk_level 只能是 low/medium/high。遇到命令执行、批量删除、写数据库、收集密钥或 token "
            "等高风险能力时 allowed 必须为 false。\n"
            f"需求：{requirement.model_dump()}\n"
            f"Skill 规格：{spec.model_dump()}"
        )
        try:
            response = self.llm.generate(prompt)
            payload = json.loads(extract_json_object(getattr(response, "text", str(response))))
            return self._normalize_llm_review(payload)
        except Exception:  # noqa: BLE001 - rule guardrail remains authoritative.
            return None

    def _normalize_llm_review(self, payload: dict[str, Any]) -> SafetyReviewResult | None:
        if "allowed" not in payload:
            return None
        risk_level = payload.get("risk_level")
        if risk_level not in {"low", "medium", "high"}:
            risk_level = "medium"
        risk_reasons = _string_list(payload.get("risk_reasons"))
        if not risk_reasons:
            risk_reasons = ["LLM 安全审查未给出具体原因，需要人工复核。"]
        return SafetyReviewResult(
            allowed=bool(payload.get("allowed")),
            risk_level=risk_level,
            risk_reasons=risk_reasons,
            safe_alternatives=_string_list(payload.get("safe_alternatives")),
        )


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
