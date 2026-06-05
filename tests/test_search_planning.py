from __future__ import annotations

from skillpilot.config import SearchConfig, load_config
from skillpilot.models import SearchPlan, SearchQuery, TypeClassification
from skillpilot.modules.search_tools import SearchExecutor
from skillpilot.modules.stubs import RequirementParser, SourcePlanner


def test_source_planner_generates_targeted_skill_queries() -> None:
    requirement = RequirementParser().parse("我想让 Claude 自动生成 Python 单元测试并分析失败原因")
    classification = TypeClassification(
        recommended_type="skill",
        confidence=0.82,
        reason="适合用 Skill 表达测试生成规范。",
    )

    plan = SourcePlanner().plan(requirement, classification)
    query_text = " ".join(query.text for query in plan.queries)

    assert plan.extension_type == "skill"
    assert 3 <= len(plan.queries) <= 5
    assert {query.source_type for query in plan.queries} == {"github", "web"}
    assert "Claude Skill" in query_text
    assert "SKILL.md" in query_text


def test_source_planner_generates_targeted_mcp_queries() -> None:
    requirement = RequirementParser().parse("帮我读取 GitHub issue 并总结需要修改的代码位置")
    classification = TypeClassification(
        recommended_type="mcp",
        confidence=0.78,
        reason="需求涉及外部服务，适合 MCP。",
    )

    plan = SourcePlanner().plan(requirement, classification)
    query_text = " ".join(query.text for query in plan.queries)

    assert plan.extension_type == "mcp"
    assert 3 <= len(plan.queries) <= 5
    assert "MCP server" in query_text
    assert "GitHub" in query_text


def test_pdf_plugin_requirement_generates_plugin_queries() -> None:
    requirement = RequirementParser().parse("阅读pdf的插件")
    classification = TypeClassification(
        recommended_type="plugin",
        confidence=0.74,
        reason="用户明确提到插件。",
    )

    plan = SourcePlanner().plan(requirement, classification)
    query_text = " ".join(query.text for query in plan.queries)

    assert requirement.task_domain == "document_processing"
    assert "pdf_reading" in requirement.desired_capabilities
    assert plan.extension_type == "plugin"
    assert "PDF reading" in query_text
    assert "Claude Code plugin" in query_text


def test_search_executor_records_skipped_results_when_network_disabled() -> None:
    plan = SearchPlan(
        extension_type="skill",
        sources=["web_search"],
        queries=[
            SearchQuery(
                text="Python unit test generation Claude Skill SKILL.md",
                source_type="web",
                extension_type="skill",
                purpose="test query",
                max_results=5,
            )
        ],
    )
    executor = SearchExecutor(
        SearchConfig(enable_network_search=False, max_results_per_query=2)
    )

    results = executor.run(plan)

    assert len(results) == 1
    assert results[0].status == "skipped"
    assert results[0].query == plan.queries[0].text
    assert results[0].source_type == "web"


def test_network_search_defaults_to_enabled(monkeypatch) -> None:
    monkeypatch.delenv("SKILLPILOT_ENABLE_NETWORK_SEARCH", raising=False)

    assert SearchConfig().enable_network_search is True
    assert load_config().search.enable_network_search is True
