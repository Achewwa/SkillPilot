from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from skillpilot.cli import app


runner = CliRunner()
BASE_TEST_ENV = {
    "SKILLPILOT_ENABLE_NETWORK_SEARCH": "0",
    "SKILLPILOT_ENABLE_LLM_EVALUATION": "0",
    "SKILLPILOT_LLM_PROVIDER": "static_json",
    "SKILLPILOT_BUILDER_INTERACTIVE": "0",
}


def env_for_test(tmp_path: Path) -> dict[str, str]:
    return {
        **BASE_TEST_ENV,
        "SKILLPILOT_OUTPUTS_DIR": str(tmp_path / "outputs"),
        "SKILLPILOT_GENERATED_SKILLS_DIR": str(tmp_path / "generated_skills"),
    }


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "SkillPilot CLI skeleton" in result.output


def test_interactive_session_accepts_natural_language(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        input="我想让 Claude 自动生成 Python 单元测试并分析失败原因\n/exit\n",
        env=env_for_test(tmp_path),
    )

    assert result.exit_code == 0
    assert "SkillPilot interactive session" in result.output
    assert "Decision:" in result.output


def test_recommend_generates_report_and_trace(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["recommend", "我想让 Claude 自动生成 Python 单元测试并分析失败原因"],
        env=env_for_test(tmp_path),
    )

    assert result.exit_code == 0
    trace_path = tmp_path / "outputs" / "decision_trace.json"
    assert (tmp_path / "outputs" / "recommendation_report.md").exists()
    assert trace_path.exists()

    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["classification"]["recommended_type"] in {
        "skill",
        "mcp",
        "plugin",
        "mixed",
    }
    assert 3 <= len(trace["search_plan"]["queries"]) <= 5
    assert trace["search_plan"]["queries"][0]["text"]
    assert trace["search_results"][0]["status"] == "skipped"
    assert trace["retrieved_contents"][0]["status"] == "skipped"


def test_build_skill_generates_draft(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["build-skill", "帮我构造一个根据课程课件给作业题提示知识点但不直接给答案的 Skill"],
        env=env_for_test(tmp_path),
    )

    assert result.exit_code == 0
    trace = json.loads(
        (tmp_path / "outputs" / "decision_trace.json").read_text(encoding="utf-8")
    )
    skill_path = Path(trace["skill_draft"]["path"])
    assert (skill_path / "SKILL.md").exists()
    assert (skill_path / "resources/guidance_rules.md").exists()
    assert (skill_path / "examples/sample_output.md").exists()
    assert trace["builder_session"]["turns"][0]["questions"][0]["options"]


def test_demo_cases_run(tmp_path: Path) -> None:
    for case in ("skill", "mcp", "build"):
        result = runner.invoke(
            app,
            ["demo", "--case", case],
            env=env_for_test(tmp_path),
        )
        assert result.exit_code == 0
        assert f"Demo case: {case}" in result.output
