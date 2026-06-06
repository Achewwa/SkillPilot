from __future__ import annotations

from skillpilot.agents.core import PipelineContext
from skillpilot.skills.decision import DecisionGate


class DecisionAgent:
    def __init__(self, decision_gate: DecisionGate) -> None:
        self.decision_gate = decision_gate

    def run(self, context: PipelineContext) -> None:
        if context.force_build_skill:
            context.decision = self.decision_gate.build_custom(
                "用户显式请求构造 Skill，直接进入 SkillBuilder Agent。"
            )
            context.record(
                "DecisionAgent",
                "GuardrailDecisionSkill",
                summary="Forced custom Skill build by user request.",
            )
            return

        context.decision = self.decision_gate.decide(context.evaluations)
        context.record(
            "DecisionAgent",
            "GuardrailDecisionSkill",
            summary=f"Decision is `{context.decision.decision_type}`.",
            metadata={"reason": context.decision.reason},
        )
