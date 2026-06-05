from __future__ import annotations

import json
from pathlib import Path

from skillpilot.models import (
    Candidate,
    CandidateEvaluation,
    Decision,
    ParsedRequirement,
    SearchPlan,
    TypeClassification,
)


class RequirementParser:
    def parse(self, text: str) -> ParsedRequirement:
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

        return ParsedRequirement(
            raw_text=text,
            task_domain=self._infer_domain(text),
            desired_capabilities=capabilities or ["general_guidance"],
            requires_codebase_access=("代码" in text or "code" in lower or "github" in lower),
            requires_command_execution=("运行" in text or "shell" in lower),
            requires_external_service=("github" in lower or "数据库" in text),
        )

    def _infer_domain(self, text: str) -> str:
        if "测试" in text or "代码" in text or "github" in text.lower():
            return "software_engineering"
        if "论文" in text or "引用" in text:
            return "academic_writing"
        if "课件" in text or "作业" in text:
            return "education"
        return "general"


class ExtensionTypeClassifier:
    def classify(self, requirement: ParsedRequirement) -> TypeClassification:
        text = requirement.raw_text.lower()
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
    def plan(self, requirement: ParsedRequirement, classification: TypeClassification) -> SearchPlan:
        source_map = {
            "skill": ["local_skill_cache", "anthropic_skill_docs", "github_skill_examples"],
            "mcp": ["local_mcp_cache", "mcp_server_directory", "github_mcp_repos"],
            "plugin": ["local_plugin_cache", "claude_code_plugin_docs", "github_plugin_repos"],
            "mixed": ["local_cache", "official_docs", "github"],
            "unknown": ["local_cache"],
        }
        return SearchPlan(
            extension_type=classification.recommended_type,
            sources=source_map[classification.recommended_type],
            queries=[requirement.raw_text],
        )


class LocalCandidateCache:
    def __init__(self, cache_path: Path) -> None:
        self.cache_path = cache_path

    def load(self) -> list[Candidate]:
        data = json.loads(self.cache_path.read_text(encoding="utf-8"))
        return [Candidate(**item) for item in data]


class CandidateEvaluator:
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

    def _evaluate_one(
        self,
        requirement: ParsedRequirement,
        classification: TypeClassification,
        candidate: Candidate,
    ) -> CandidateEvaluation:
        required = set(requirement.desired_capabilities)
        offered = set(candidate.capabilities)
        matched = sorted(required & offered)
        missing = sorted(required - offered)
        type_bonus = 0.2 if candidate.extension_type == classification.recommended_type else 0.0
        match_score = min(1.0, (len(matched) / max(len(required), 1)) * 0.75 + type_bonus)
        risk_reasons = self._risk_reasons(candidate)
        risk_level = "high" if any("write" in item for item in candidate.permissions) else "low"
        if "external_service" in candidate.permissions and risk_level != "high":
            risk_level = "medium"

        return CandidateEvaluation(
            candidate=candidate,
            match_score=round(match_score, 2),
            matched_capabilities=matched,
            missing_capabilities=missing,
            trust_level="medium",
            risk_level=risk_level,
            risk_reasons=risk_reasons,
            reason="占位评分：基于能力关键词重合、扩展类型一致性和权限风险生成。",
        )

    def _risk_reasons(self, candidate: Candidate) -> list[str]:
        reasons: list[str] = []
        if "write_repository" in candidate.permissions:
            reasons.append("候选涉及仓库写入权限，需要人工确认后再启用。")
        if "external_service" in candidate.permissions:
            reasons.append("候选需要连接外部服务，可能涉及账号或 token。")
        if not reasons:
            reasons.append("候选主要是说明型能力，当前占位评估未发现高风险权限。")
        return reasons


class DecisionGate:
    def decide(self, evaluations: list[CandidateEvaluation]) -> Decision:
        best = evaluations[0] if evaluations else None
        if best is None or best.match_score < 0.45:
            return Decision(
                decision_type="build_custom_skill",
                reason="没有足够匹配的候选资源，进入自定义 Skill 草案流程。",
                selected_candidates=[],
                custom_skill_name="homework-knowledge-hint",
            )
        if best.match_score >= 0.75 and best.risk_level != "high":
            return Decision(
                decision_type="recommend_existing",
                reason="存在匹配度较高且风险可解释的候选资源。",
                selected_candidates=evaluations[:3],
            )
        return Decision(
            decision_type="recommend_with_custom_extension",
            reason="候选资源有一定相关性，但仍建议用自定义 Skill 补齐缺口。",
            selected_candidates=evaluations[:3],
            custom_skill_name="homework-knowledge-hint",
        )
