from __future__ import annotations

import json

from skillpilot.io.report_writer import RecommendationWriter
from skillpilot.models import (
    Candidate,
    RetrievedContent,
    SearchPlan,
    SearchQuery,
    SearchResult,
    TypeClassification,
)
from skillpilot.modules.source_catalog import SourceCatalog
from skillpilot.modules.stubs import CandidateEvaluator, DecisionGate, RequirementParser


class FakeLLM:
    def __init__(self, text: str) -> None:
        self.text = text
        self.prompts: list[str] = []

    def generate(self, prompt: str):
        self.prompts.append(prompt)
        return type("FakeResponse", (), {"text": self.text})()


def parsed_requirement(text: str, **overrides):
    payload = {
        "task_domain": "general",
        "desired_capabilities": ["general_guidance"],
        "requires_codebase_access": False,
        "requires_command_execution": False,
        "requires_external_service": False,
        "risk_tolerance": "medium",
    }
    payload.update(overrides)
    return RequirementParser(FakeLLM(json.dumps(payload))).parse(text)


def test_llm_evaluation_recommends_strong_medium_risk_candidate() -> None:
    requirement = parsed_requirement(
        "阅读pdf的插件",
        task_domain="document_processing",
        desired_capabilities=["pdf_reading", "document_parsing"],
    )
    classification = TypeClassification(
        recommended_type="plugin",
        confidence=0.74,
        reason="用户明确提到插件。",
    )
    candidate = Candidate(
        name="owner/pdf-plugin",
        extension_type="plugin",
        source_url="https://github.com/owner/pdf-plugin",
        description="Claude Code plugin for PDF reading and document parsing.",
        capabilities=["pdf_reading", "document_parsing"],
        installation="Run npm install and configure the plugin manually.",
        dependencies=["node"],
        permissions=["read_documents"],
        maintainer="owner",
        last_updated="2026-06-01T00:00:00Z",
        evidence=[
            "The README says it reads PDF files.",
            "The plugin extracts document text for Claude.",
        ],
    )

    llm = FakeLLM(
        """
        {
          "capability_score": 1.0,
          "documentation_score": 0.9,
          "safety_score": 0.65,
          "matched_capabilities": ["pdf_reading", "document_parsing"],
          "missing_capabilities": [],
          "risk_level": "medium",
          "risk_reasons": ["候选会读取文档，需要确认文件范围。"],
          "reason": "LLM 结构化评分：候选明确覆盖 PDF 读取和文档解析。"
        }
        """
    )
    evaluation = CandidateEvaluator(llm).evaluate(requirement, classification, [candidate])[0]
    decision = DecisionGate().decide([evaluation])

    assert evaluation.match_score >= 0.75
    assert evaluation.capability_score == 1.0
    assert evaluation.type_score == 1.0
    assert evaluation.risk_level == "medium"
    assert "LLM 结构化评分" in evaluation.reason
    assert decision.decision_type == "recommend_existing"


def test_llm_evaluation_reads_retrieved_content_directly() -> None:
    requirement = parsed_requirement(
        "制作海报的skill",
        task_domain="visual_design",
        desired_capabilities=["poster_design", "visual_design"],
    )
    classification = TypeClassification(
        recommended_type="skill",
        confidence=0.86,
        reason="用户明确提到 Skill。",
    )
    content = RetrievedContent(
        title="poster-coach",
        url="https://github.com/owner/repo/tree/main/skills/poster-coach",
        source_type="github",
        query="poster design skill",
        status="success",
        content=(
            "# Poster Coach\n"
            "Use this skill to design posters from a campaign brief. "
            "It provides layout, visual hierarchy, typography, and copy guidance."
        ),
    )
    llm = FakeLLM(
        """
        {
          "candidate_name": "poster-coach",
          "extension_type": "skill",
          "description": "Skill for poster layout, typography, and visual design guidance.",
          "capabilities": ["poster_design", "visual_design"],
          "installation": null,
          "dependencies": [],
          "permissions": [],
          "maintainer": "owner",
          "last_updated": null,
          "evidence": ["Use this skill to design posters from a campaign brief."],
          "capability_score": 1.0,
          "documentation_score": 0.8,
          "safety_score": 1.0,
          "matched_capabilities": ["poster_design", "visual_design"],
          "missing_capabilities": [],
          "risk_level": "low",
          "risk_reasons": ["未发现明显高危权限。"],
          "reason": "LLM 结构化评分：原文明确支持海报设计指导。"
        }
        """
    )

    evaluation = CandidateEvaluator(llm).evaluate_retrieved(
        requirement,
        classification,
        [content],
    )[0]

    assert "Use this skill to design posters" in llm.prompts[0]
    assert evaluation.candidate.name == "poster-coach"
    assert evaluation.candidate.description.startswith("Skill for poster")
    assert evaluation.capability_score == 1.0
    assert evaluation.risk_level == "low"


def test_decision_gate_avoids_direct_recommendation_for_high_risk_candidate() -> None:
    requirement = parsed_requirement(
        "帮我读取 GitHub issue 并总结需要修改的代码位置",
        task_domain="software_engineering",
        desired_capabilities=["github_issue_read", "codebase_access"],
        requires_codebase_access=True,
        requires_external_service=True,
    )
    classification = TypeClassification(
        recommended_type="mcp",
        confidence=0.78,
        reason="需求涉及外部服务，适合 MCP。",
    )
    candidate = Candidate(
        name="owner/github-writer-mcp",
        extension_type="mcp",
        source_url="https://github.com/owner/github-writer-mcp",
        description="MCP server for GitHub issue triage and repository changes.",
        capabilities=["github_issue_read", "codebase_access"],
        installation="Configure a GitHub token before use.",
        dependencies=["github_token"],
        permissions=["external_service", "read_repository", "write_repository"],
        maintainer="owner",
        last_updated="2026-06-01T00:00:00Z",
        evidence=["The README describes GitHub issue reading and repository writes."],
    )

    llm = FakeLLM(
        """
        {
          "capability_score": 1.0,
          "documentation_score": 0.85,
          "safety_score": 0.0,
          "matched_capabilities": ["github_issue_read", "codebase_access"],
          "missing_capabilities": [],
          "risk_level": "high",
          "risk_reasons": ["候选需要 GitHub token 并包含仓库写入权限。"],
          "reason": "LLM 结构化评分：能力匹配但安全风险高。"
        }
        """
    )
    evaluation = CandidateEvaluator(llm).evaluate(requirement, classification, [candidate])[0]
    decision = DecisionGate().decide([evaluation])

    assert evaluation.risk_level == "high"
    assert evaluation.safety_score == 0.0
    assert decision.decision_type == "build_custom_skill"
    assert "不建议直接安装" in decision.reason
    assert decision.selected_candidates == [evaluation]


def test_decision_gate_builds_custom_skill_when_no_candidate_is_sufficient() -> None:
    decision = DecisionGate().decide([])

    assert decision.decision_type == "build_custom_skill"
    assert "没有提供足够证据" in decision.reason
    assert decision.custom_skill_name is None


def test_report_includes_scores_failures_and_safety_advice(tmp_path) -> None:
    requirement = parsed_requirement(
        "阅读pdf的插件",
        task_domain="document_processing",
        desired_capabilities=["pdf_reading", "document_parsing"],
    )
    classification = TypeClassification(
        recommended_type="plugin",
        confidence=0.74,
        reason="用户明确提到插件。",
    )
    candidate = Candidate(
        name="owner/pdf-plugin",
        extension_type="plugin",
        source_url="https://github.com/owner/pdf-plugin",
        description="Claude Code plugin for PDF reading.",
        capabilities=["pdf_reading"],
        permissions=["read_documents"],
        maintainer="owner",
        last_updated="2026-06-01T00:00:00Z",
        evidence=["README mentions PDF reading."],
    )
    llm = FakeLLM(
        """
        {
          "capability_score": 0.7,
          "documentation_score": 0.7,
          "safety_score": 0.55,
          "matched_capabilities": ["pdf_reading"],
          "missing_capabilities": ["document_parsing"],
          "risk_level": "medium",
          "risk_reasons": ["候选会读取文档，需要确认文件范围。"],
          "reason": "LLM 结构化评分：候选部分匹配 PDF 读取需求。"
        }
        """
    )
    evaluation = CandidateEvaluator(llm).evaluate(requirement, classification, [candidate])[0]
    decision = DecisionGate().decide([evaluation])
    source = SourceCatalog().by_id("anthropic_official_plugin_marketplace")
    assert source is not None
    search_plan = SearchPlan(
        extension_type="plugin",
        sources=[source],
        queries=[
            SearchQuery(
                text="PDF reading Claude Code plugin",
                source_type="web",
                extension_type="plugin",
                purpose="Find plugin candidates.",
                source_id="anthropic_official_plugin_marketplace",
            )
        ],
    )
    search_results = [
        SearchResult(
            title="",
            url="",
            snippet="Network search timed out.",
            source_type="web",
            query="PDF reading Claude Code plugin",
            status="failed",
            error_message="timeout",
        )
    ]
    retrieved_contents = [
        RetrievedContent(
            title="owner/pdf-plugin",
            url="https://github.com/owner/pdf-plugin",
            source_type="github",
            query="PDF reading Claude Code plugin",
            status="failed",
            error_message="404 Not Found",
        )
    ]

    report_path = RecommendationWriter(tmp_path).write_report(
        requirement_text=requirement.raw_text,
        classification_reason=classification.reason,
        decision=decision,
        requirement=requirement,
        search_plan=search_plan,
        search_results=search_results,
        retrieved_contents=retrieved_contents,
    )
    report = report_path.read_text(encoding="utf-8")

    assert "## 失败处理" in report
    assert "- 需求领域：document_processing" in report
    assert "- 需求能力：pdf_reading、document_parsing" in report
    assert "- 描述：Claude Code plugin for PDF reading." in report
    assert "查询 `PDF reading Claude Code plugin`" in report
    assert "分项：能力" in report
    assert "可信" not in report
    assert "## 使用建议与安全替代" in report
