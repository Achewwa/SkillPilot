from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from skillpilot.cli import app


runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "SkillPilot CLI skeleton" in result.output


def test_interactive_session_accepts_natural_language() -> None:
    result = runner.invoke(
        app,
        input="我想让 Claude 自动生成 Python 单元测试并分析失败原因\n/exit\n",
    )

    assert result.exit_code == 0
    assert "SkillPilot interactive session" in result.output
    assert "Decision:" in result.output


def test_recommend_generates_report_and_trace() -> None:
    result = runner.invoke(
        app,
        ["recommend", "我想让 Claude 自动生成 Python 单元测试并分析失败原因"],
    )

    assert result.exit_code == 0
    assert Path("outputs/recommendation_report.md").exists()
    assert Path("outputs/decision_trace.json").exists()

    trace = json.loads(Path("outputs/decision_trace.json").read_text(encoding="utf-8"))
    assert trace["classification"]["recommended_type"] in {
        "skill",
        "mcp",
        "plugin",
        "mixed",
    }


def test_build_skill_generates_draft() -> None:
    result = runner.invoke(
        app,
        ["build-skill", "帮我构造一个根据课程课件给作业题提示知识点但不直接给答案的 Skill"],
    )

    assert result.exit_code == 0
    assert Path("generated_skills/homework-knowledge-hint/SKILL.md").exists()
    assert Path("generated_skills/homework-knowledge-hint/resources/hint_policy.md").exists()


def test_demo_cases_run() -> None:
    for case in ("skill", "mcp", "build"):
        result = runner.invoke(app, ["demo", "--case", case])
        assert result.exit_code == 0
        assert f"Demo case: {case}" in result.output
