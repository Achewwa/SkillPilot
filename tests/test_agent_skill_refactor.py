from __future__ import annotations

import json
from pathlib import Path

from skillpilot.config import AppConfig, BuilderConfig, LLMConfig, SearchConfig
from skillpilot.models import (
    Candidate,
    CandidateEvaluation,
    Decision,
    ParsedRequirement,
    SafetyReviewResult,
    SkillSpec,
    TypeClassification,
)
from skillpilot.pipeline import SkillPilotPipeline
from skillpilot.skills.classification import ExtensionTypeClassifier
from skillpilot.skills.decision import DecisionGate
from skillpilot.skills.planning import SourcePlanner
from skillpilot.skills.builder.safety_reviewer import SafetyReviewer


class FakeLLM:
    def __init__(self, payload: dict | list[dict]) -> None:
        self.payload = payload
        self.prompts: list[str] = []

    def generate(self, prompt: str):
        self.prompts.append(prompt)
        if isinstance(self.payload, list):
            payload = self.payload[min(len(self.prompts) - 1, len(self.payload) - 1)]
        else:
            payload = self.payload
        return type("FakeResponse", (), {"text": json.dumps(payload, ensure_ascii=False)})()


def requirement(text: str = "帮我连接 GitHub issue 并读取仓库上下文") -> ParsedRequirement:
    return ParsedRequirement(
        raw_text=text,
        task_domain="software_engineering",
        desired_capabilities=["github_issue_read", "codebase_access"],
        requires_codebase_access=True,
        requires_external_service=True,
        risk_tolerance="medium",
    )


def classification(extension_type: str = "mcp") -> TypeClassification:
    return TypeClassification(
        recommended_type=extension_type,  # type: ignore[arg-type]
        confidence=0.8,
        reason="测试分类。",
    )


def evaluation(score: float, risk_level: str = "low") -> CandidateEvaluation:
    return CandidateEvaluation(
        candidate=Candidate(
            name=f"candidate-{score}",
            extension_type="skill",
            source_url="https://example.com/candidate",
            description="A test candidate.",
        ),
        match_score=score,
        capability_score=score,
        type_score=1.0,
        documentation_score=score,
        safety_score=1.0 if risk_level != "high" else 0.0,
        risk_level=risk_level,  # type: ignore[arg-type]
        risk_reasons=["test risk"],
        reason="test evaluation",
    )


def test_extension_type_classifier_uses_llm_main_path() -> None:
    llm = FakeLLM(
        {
            "recommended_type": "mcp",
            "confidence": 0.91,
            "reason": "需要连接 GitHub 外部服务并读取 issue。",
        }
    )

    result = ExtensionTypeClassifier(llm).classify(requirement())

    assert result.recommended_type == "mcp"
    assert result.confidence == 0.91
    assert result.reason.startswith("LLM 类型判断")
    assert "扩展类型判断 skill" in llm.prompts[0]


def test_source_planner_uses_llm_queries_with_catalog_guardrail() -> None:
    llm = FakeLLM(
        {
            "queries": [
                {
                    "source_id": "official_mcp_registry",
                    "text": "GitHub issue reader MCP server official registry",
                    "purpose": "Find official MCP servers for GitHub issue reading.",
                },
                {
                    "source_id": "not_in_catalog",
                    "text": "should be ignored",
                    "purpose": "Invalid source.",
                },
            ]
        }
    )

    plan = SourcePlanner(llm).plan(requirement(), classification("mcp"))

    assert [query.source_id for query in plan.queries] == ["official_mcp_registry"]
    assert plan.queries[0].source_type == "source"
    assert "source-aware 查询规划 skill" in llm.prompts[0]


def test_safety_reviewer_lets_policy_redline_override_llm() -> None:
    llm = FakeLLM(
        {
            "allowed": True,
            "risk_level": "low",
            "risk_reasons": ["LLM did not notice the shell risk."],
            "safe_alternatives": [],
        }
    )
    spec = SkillSpec(
        name="Dangerous Skill",
        slug="dangerous-skill",
        description="自动执行 shell 命令并批量删除旧文件。",
        workflow=["运行命令执行清理流程。"],
    )

    review = SafetyReviewer(llm).review(
        requirement(
            "帮我做一个自动执行 shell 命令并批量删除旧文件的 Skill",
        ).model_copy(update={"requires_command_execution": True}),
        spec,
    )

    assert review.allowed is False
    assert review.risk_level == "high"
    assert any("命令" in reason for reason in review.risk_reasons)


def test_decision_gate_score_matrix_and_llm_reason_guardrail() -> None:
    gate = DecisionGate(
        FakeLLM(
            {
                "decision_type": "recommend_existing",
                "reason": "分数高且风险可控。",
            }
        )
    )

    strong = gate.decide([evaluation(0.8, "low")])
    medium = DecisionGate().decide([evaluation(0.6, "low")])
    weak = DecisionGate().decide([evaluation(0.3, "low")])
    high_risk = DecisionGate().decide([evaluation(0.9, "high")])

    assert strong.decision_type == "recommend_existing"
    assert strong.reason.startswith("LLM 决策解释")
    assert medium.decision_type == "recommend_with_custom_extension"
    assert weak.decision_type == "build_custom_skill"
    assert high_risk.decision_type == "build_custom_skill"


def test_pipeline_records_agent_skill_trace_events(tmp_path: Path) -> None:
    config = AppConfig(
        project_root=tmp_path,
        data_dir=Path("/home/achewwa/Projects/SkillPilot/data"),
        outputs_dir=tmp_path / "outputs",
        generated_skills_dir=tmp_path / "generated_skills",
        llm=LLMConfig(provider="static_json", enable_evaluation=False),
        search=SearchConfig(enable_network_search=False),
        builder=BuilderConfig(interactive=False),
    )

    result = SkillPilotPipeline(config).run("阅读pdf的skill")

    skills = {event.skill for event in result.trace_events}
    assert "RequirementExtractionSkill" in skills
    assert "ExtensionTypeDecisionSkill" in skills
    assert "QueryPlanningSkill" in skills
    assert "SourceSearchSkill" in skills
    assert "ContentReadSkill" in skills
    assert "OfflineCandidateCacheSkill" in skills
    assert "GuardrailDecisionSkill" in skills
    assert result.trace_path.endswith("decision_trace.json")
