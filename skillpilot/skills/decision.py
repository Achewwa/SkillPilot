from __future__ import annotations

import json

from skillpilot.models import CandidateEvaluation, Decision
from skillpilot.skills.core import LLMProvider
from skillpilot.utils import extract_json_object


class DecisionGate:
    def __init__(self, llm: LLMProvider | None = None) -> None:
        self.llm = llm

    def build_custom(self, reason: str) -> Decision:
        return Decision(
            decision_type="build_custom_skill",
            reason=reason,
            selected_candidates=[],
        )

    def decide(self, evaluations: list[CandidateEvaluation]) -> Decision:
        best = evaluations[0] if evaluations else None
        if best is None or best.match_score < 0.45:
            return self._with_llm_reason(
                Decision(
                    decision_type="build_custom_skill",
                    reason=(
                        "实时搜索或可用候选没有提供足够证据支撑直接推荐，"
                        "进入自定义 Skill 草案流程。"
                    ),
                    selected_candidates=[],
                ),
                evaluations,
            )
        if best.risk_level == "high":
            return self._with_llm_reason(
                Decision(
                    decision_type="build_custom_skill",
                    reason=(
                        "最高匹配候选包含高风险权限或敏感凭据依赖，"
                        "不建议直接安装；优先生成更小权限的自定义 Skill，并把候选作为人工审查参考。"
                    ),
                    selected_candidates=evaluations[:3],
                ),
                evaluations,
            )
        if best.match_score >= 0.75 and best.risk_level != "high":
            return self._with_llm_reason(
                Decision(
                    decision_type="recommend_existing",
                    reason="存在匹配度较高且风险为低或中的候选资源，可作为现成资源推荐。",
                    selected_candidates=evaluations[:3],
                ),
                evaluations,
            )
        return self._with_llm_reason(
            Decision(
                decision_type="recommend_with_custom_extension",
                reason="候选资源有中等相关性，建议参考现有资源并用自定义 Skill 补齐缺失能力。",
                selected_candidates=evaluations[:3],
            ),
            evaluations,
        )

    def _with_llm_reason(
        self,
        decision: Decision,
        evaluations: list[CandidateEvaluation],
    ) -> Decision:
        if self.llm is None:
            return decision
        payload = {
            "guardrail_decision": {
                "decision_type": decision.decision_type,
                "reason": decision.reason,
            },
            "candidates": [
                {
                    "name": evaluation.candidate.name,
                    "match_score": evaluation.match_score,
                    "risk_level": evaluation.risk_level,
                    "matched_capabilities": evaluation.matched_capabilities,
                    "missing_capabilities": evaluation.missing_capabilities,
                    "risk_reasons": evaluation.risk_reasons,
                }
                for evaluation in evaluations[:3]
            ],
        }
        prompt = (
            "你是 SkillPilot 的决策解释 skill。确定性 guardrail 已经给出 decision_type，"
            "你只能为同一个 decision_type 生成更清晰的中文 reason，不得改变决策类型。"
            "返回严格 JSON，不要 Markdown。字段：decision_type, reason。\n"
            f"数据：{json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}"
        )
        try:
            response = self.llm.generate(prompt)
            data = json.loads(extract_json_object(getattr(response, "text", str(response))))
        except Exception:  # noqa: BLE001 - deterministic decision is authoritative.
            return decision
        if data.get("decision_type") != decision.decision_type:
            return decision
        reason = str(data.get("reason") or "").strip()
        if not reason:
            return decision
        return Decision(
            decision_type=decision.decision_type,
            reason=f"LLM 决策解释：{reason}",
            selected_candidates=decision.selected_candidates,
            custom_skill_name=decision.custom_skill_name,
        )
