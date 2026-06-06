from __future__ import annotations

import json
from typing import Any

from skillpilot.models import (
    Candidate,
    CandidateEvaluation,
    ParsedRequirement,
    RetrievedContent,
    TypeClassification,
)
from skillpilot.safety import RiskPolicy
from skillpilot.scoring import DEFAULT_SCORING_WEIGHTS, ScoringWeights
from skillpilot.skills.core import LLMProvider
from skillpilot.utils import extract_json_object

EvaluationLLM = LLMProvider


class CandidateEvaluator:
    def __init__(
        self,
        llm: EvaluationLLM | None = None,
        weights: ScoringWeights = DEFAULT_SCORING_WEIGHTS,
        risk_policy: RiskPolicy | None = None,
    ) -> None:
        self.llm = llm
        self.weights = weights
        self.risk_policy = risk_policy or RiskPolicy()

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
        match_score = self.weights.aggregate(
            capability_score=llm_result["capability_score"],
            type_score=type_score,
            documentation_score=llm_result["documentation_score"],
            safety_score=llm_result["safety_score"],
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
        match_score = self.weights.aggregate(
            capability_score=llm_result["capability_score"],
            type_score=type_score,
            documentation_score=llm_result["documentation_score"],
            safety_score=llm_result["safety_score"],
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
        return extract_json_object(text)

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
        risk = self.risk_policy.assess_candidate(candidate)
        return {
            "capability_score": len(matched) / max(len(required), 1),
            "documentation_score": documentation_score,
            "safety_score": risk.safety_score,
            "matched_capabilities": matched,
            "missing_capabilities": missing,
            "risk_level": risk.risk_level,
            "risk_reasons": risk.risk_reasons,
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
