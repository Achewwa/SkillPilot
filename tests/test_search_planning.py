from __future__ import annotations

import json

from skillpilot.config import SearchConfig, load_config
from skillpilot.models import SearchPlan, SearchQuery, SearchResult, TypeClassification
from skillpilot.skills.classification import ExtensionTypeClassifier
from skillpilot.skills.discovery.source_access_guide import SourceAccessGuideLoader
from skillpilot.skills.discovery.search_tools import SearchExecutor, SourceSearchTool
from skillpilot.skills.discovery.source_catalog import SourceCatalog
from skillpilot.skills.planning import SourcePlanner
from skillpilot.skills.requirement import RequirementParser


class FakeLLM:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def generate(self, prompt: str):
        return type("Response", (), {"text": json.dumps(self.payload)})()


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
    return RequirementParser(FakeLLM(payload)).parse(text)


def test_requirement_parser_uses_llm_extraction_without_keyword_rules() -> None:
    requirement = parsed_requirement(
        "帮我处理这个材料",
        task_domain="document_processing",
        desired_capabilities=["pdf_reading", "table_extraction"],
    )

    assert requirement.task_domain == "document_processing"
    assert requirement.desired_capabilities == ["pdf_reading", "table_extraction"]


def test_requirement_parser_without_llm_uses_keyword_fallback() -> None:
    requirement = RequirementParser().parse("阅读pdf的skill")

    assert requirement.task_domain == "document_processing"
    assert requirement.desired_capabilities == ["pdf_reading", "document_parsing"]


def test_source_planner_generates_targeted_skill_queries() -> None:
    requirement = parsed_requirement(
        "我想让 Claude 自动生成 Python 单元测试并分析失败原因",
        task_domain="software_engineering",
        desired_capabilities=["unit_test_generation", "test_failure_analysis"],
    )
    classification = TypeClassification(
        recommended_type="skill",
        confidence=0.82,
        reason="适合用 Skill 表达测试生成规范。",
    )

    plan = SourcePlanner().plan(requirement, classification)
    query_text = " ".join(query.text for query in plan.queries)

    assert plan.extension_type == "skill"
    assert 3 <= len(plan.queries) <= 5
    assert {source.source_id for source in plan.sources} >= {
        "anthropic_skills_repo",
        "anthropic_agent_skills_docs",
        "anthropic_skills_cookbook",
        "skillsmp_directory",
    }
    assert any(query.source_id == "anthropic_skills_repo" for query in plan.queries)
    assert {query.source_type for query in plan.queries} == {"source"}
    assert "Claude Skill" in query_text
    assert "SKILL.md" in query_text


def test_source_access_guide_covers_source_catalog() -> None:
    catalog = SourceCatalog()
    catalog_source_ids = {
        source.source_id
        for extension_type in ("skill", "mcp", "plugin")
        for source in catalog.sources_for(extension_type)  # type: ignore[arg-type]
    }
    guide_source_ids = set(SourceAccessGuideLoader().all())

    assert guide_source_ids == catalog_source_ids


def test_poster_skill_requirement_generates_visual_design_query() -> None:
    requirement = RequirementParser().parse("制作海报的skill")
    classification = TypeClassification(
        recommended_type="skill",
        confidence=0.82,
        reason="适合用 Skill 表达设计流程。",
    )

    plan = SourcePlanner().plan(requirement, classification)
    query_text = " ".join(query.text for query in plan.queries)

    assert requirement.task_domain == "visual_design"
    assert "poster_design" in requirement.desired_capabilities
    assert "visual_design" in requirement.desired_capabilities
    assert "poster design" in query_text
    assert "general assistant guidance" not in query_text


def test_explicit_skill_word_overrides_external_service_signal() -> None:
    requirement = parsed_requirement(
        "制作海报的skill",
        task_domain="visual_design",
        desired_capabilities=["poster_design", "visual_design"],
        requires_external_service=True,
    )

    classification = ExtensionTypeClassifier().classify(requirement)

    assert classification.recommended_type == "skill"


def test_source_planner_generates_targeted_mcp_queries() -> None:
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

    plan = SourcePlanner().plan(requirement, classification)
    query_text = " ".join(query.text for query in plan.queries)

    assert plan.extension_type == "mcp"
    assert 3 <= len(plan.queries) <= 5
    assert {source.source_id for source in plan.sources} >= {
        "official_mcp_registry",
        "glama_mcp",
        "smithery_mcp",
    }
    assert any(query.source_id == "official_mcp_registry" for query in plan.queries)
    assert "MCP server" in query_text
    assert all(query.source_type == "source" for query in plan.queries)


def test_pdf_plugin_requirement_generates_plugin_queries() -> None:
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

    plan = SourcePlanner().plan(requirement, classification)
    query_text = " ".join(query.text for query in plan.queries)

    assert requirement.task_domain == "document_processing"
    assert "pdf_reading" in requirement.desired_capabilities
    assert plan.extension_type == "plugin"
    assert {source.source_id for source in plan.sources} >= {
        "anthropic_official_plugin_marketplace",
        "anthropic_community_plugin_marketplace",
        "anthropic_demo_plugin_marketplace",
        "ccplugins_awesome_marketplace",
    }
    assert any(query.source_id == "ccplugins_awesome_marketplace" for query in plan.queries)
    assert "PDF reading" in query_text
    assert "Claude Code plugin" in query_text
    assert all(query.source_type == "source" for query in plan.queries)


def test_search_executor_records_skipped_results_when_network_disabled() -> None:
    source = SourceCatalog().by_id("anthropic_agent_skills_docs")
    assert source is not None
    plan = SearchPlan(
        extension_type="skill",
        sources=[source],
        queries=[
            SearchQuery(
                text="Python unit test generation Claude Skill SKILL.md",
                source_type="source",
                extension_type="skill",
                purpose="test query",
                source_id="anthropic_agent_skills_docs",
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
    assert results[0].source_type == "source"
    assert results[0].source_id == "anthropic_agent_skills_docs"


def test_skillsmp_response_parser_returns_github_results() -> None:
    query = SearchQuery(
        text="pdf",
        source_type="source",
        extension_type="skill",
        purpose="Search SkillsMP.",
        source_id="skillsmp_directory",
        max_results=5,
    )
    payload = {
        "success": True,
        "data": {
            "skills": [
                {
                    "id": "owner-repo-pdf-md",
                    "name": "pdf.md",
                    "author": "owner",
                    "description": "Read and extract PDF documents.",
                    "githubUrl": "https://github.com/owner/repo",
                    "skillUrl": "https://skillsmp.com/skills/owner-repo-pdf-md",
                    "stars": 42,
                    "updatedAt": 1775714881,
                }
            ]
        },
    }

    results = SourceSearchTool()._parse_skillsmp_results(query, payload)

    assert len(results) == 1
    assert results[0].source_type == "github"
    assert results[0].source_id == "skillsmp_directory"
    assert results[0].url == "https://github.com/owner/repo"
    assert results[0].metadata["skillsmp_url"] == "https://skillsmp.com/skills/owner-repo-pdf-md"


def test_marketplace_json_searcher_matches_plugin_fixture() -> None:
    guide = SourceAccessGuideLoader().get("anthropic_demo_plugin_marketplace")
    assert guide is not None
    query = SearchQuery(
        text="GitHub pull request review Claude Code plugin",
        source_type="source",
        extension_type="plugin",
        purpose="Search demo plugin marketplace.",
        source_id=guide.source_id,
        max_results=5,
    )
    payload = {
        "plugins": [
            {
                "name": "code-review",
                "description": "Automated code review for pull requests using specialized agents.",
                "source": "./plugins/code-review",
                "category": "productivity",
            },
            {
                "name": "frontend-design",
                "description": "Create production-grade frontend interfaces.",
                "source": "./plugins/frontend-design",
                "category": "development",
            },
        ]
    }

    results = SourceSearchTool()._parse_marketplace_results(query, guide, payload)

    assert [result.title for result in results] == ["code-review"]
    assert results[0].status == "success"
    assert results[0].source_id == "anthropic_demo_plugin_marketplace"
    assert results[0].url.endswith("/tree/main/plugins/code-review")


def test_registry_api_searcher_matches_mcp_fixture() -> None:
    guide = SourceAccessGuideLoader().get("official_mcp_registry")
    assert guide is not None
    query = SearchQuery(
        text="GitHub issue pull request MCP server",
        source_type="source",
        extension_type="mcp",
        purpose="Search official MCP registry.",
        source_id=guide.source_id,
        max_results=5,
    )
    payload = {
        "servers": [
            {
                "server": {
                    "name": "io.github.github-mcp",
                    "title": "GitHub MCP Server",
                    "description": "Manage GitHub issues, pull requests, and repositories.",
                    "repository": {"url": "https://github.com/github/github-mcp-server"},
                }
            },
            {
                "server": {
                    "name": "docs-mcp",
                    "description": "Search documentation pages.",
                }
            },
        ]
    }

    results = SourceSearchTool()._parse_registry_results(query, guide, payload)

    assert [result.title for result in results] == ["GitHub MCP Server"]
    assert results[0].source_type == "github"
    assert results[0].url == "https://github.com/github/github-mcp-server"


def test_source_search_tool_dispatches_by_json_guide(monkeypatch) -> None:
    tool = SourceSearchTool()

    def fake_fetch_json(url: str):
        assert url.endswith("/marketplace.json")
        return {
            "plugins": [
                {
                    "name": "pr-review-toolkit",
                    "description": "Comprehensive PR review agents for pull requests and tests.",
                    "source": "./plugins/pr-review-toolkit",
                }
            ]
        }

    monkeypatch.setattr(tool, "_fetch_json", fake_fetch_json)
    query = SearchQuery(
        text="pull request review agents",
        source_type="source",
        extension_type="plugin",
        purpose="Search demo marketplace.",
        source_id="anthropic_demo_plugin_marketplace",
        max_results=5,
    )

    results = tool.search(query)

    assert len(results) == 1
    assert results[0].status == "success"
    assert results[0].title == "pr-review-toolkit"
    assert results[0].metadata["searcher_type"] == "marketplace_json_searcher"


def test_search_executor_runs_one_agent_per_source() -> None:
    class FakeSourceSearchTool:
        def search(self, query: SearchQuery) -> list[SearchResult]:
            return [
                SearchResult(
                    title=f"result from {query.source_id}",
                    url=f"https://example.com/{query.source_id}",
                    snippet="fake source result",
                    source_type="source",
                    query=query.text,
                    status="success",
                    source_id=query.source_id,
                )
            ]

    source_a = SourceCatalog().by_id("anthropic_agent_skills_docs")
    source_b = SourceCatalog().by_id("skillsmp_directory")
    assert source_a is not None
    assert source_b is not None
    plan = SearchPlan(
        extension_type="skill",
        sources=[source_a, source_b],
        queries=[
            SearchQuery(
                text="query a",
                source_type="source",
                extension_type="skill",
                purpose="Search source A.",
                source_id=source_a.source_id,
            ),
            SearchQuery(
                text="query b",
                source_type="source",
                extension_type="skill",
                purpose="Search source B.",
                source_id=source_b.source_id,
            ),
        ],
    )
    executor = SearchExecutor(SearchConfig(enable_network_search=True))
    executor.source_search = FakeSourceSearchTool()  # type: ignore[assignment]

    results = executor.run(plan)

    assert [result.source_id for result in results] == [
        "anthropic_agent_skills_docs",
        "skillsmp_directory",
    ]
    assert [result.metadata["search_agent"] for result in results] == [
        "anthropic_agent_skills_docs",
        "skillsmp_directory",
    ]


def test_network_search_defaults_to_enabled(monkeypatch) -> None:
    monkeypatch.delenv("SKILLPILOT_ENABLE_NETWORK_SEARCH", raising=False)

    assert SearchConfig().enable_network_search is True
    assert load_config().search.enable_network_search is True
