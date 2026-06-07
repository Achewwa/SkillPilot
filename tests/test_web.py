from __future__ import annotations

import time
from pathlib import Path

from typer.testing import CliRunner

from skillpilot.cli import app
from skillpilot.config import AppConfig, BuilderConfig, LLMConfig, SearchConfig
from skillpilot.web import SkillPilotWebApp


def web_config(tmp_path: Path, *, builder_interactive: bool = False) -> AppConfig:
    return AppConfig(
        project_root=tmp_path,
        data_dir=Path("/home/achewwa/Projects/SkillPilot/data"),
        outputs_dir=tmp_path / "outputs",
        generated_skills_dir=tmp_path / "generated_skills",
        llm=LLMConfig(provider="static_json", enable_evaluation=False),
        search=SearchConfig(enable_network_search=False),
        builder=BuilderConfig(interactive=builder_interactive),
    )


def test_web_app_loads_demo_cases(tmp_path: Path) -> None:
    web_app = SkillPilotWebApp(config_loader=lambda: web_config(tmp_path))

    cases = web_app.demo_cases()

    assert set(cases) == {"skill", "mcp", "build"}
    assert cases["skill"]


def test_web_app_runs_requirement_and_returns_report(tmp_path: Path) -> None:
    web_app = SkillPilotWebApp(config_loader=lambda: web_config(tmp_path))

    payload = web_app.run_requirement("我想让 Claude 帮我检查课程论文结构", "recommend")

    assert payload["summary"]["decision_type"] in {
        "recommend_existing",
        "recommend_with_custom_extension",
        "build_custom_skill",
    }
    assert payload["result"]["requirement"]["raw_text"] == "我想让 Claude 帮我检查课程论文结构"
    assert "SkillPilot运行报告" in payload["report_markdown"]
    assert "trace_events" in payload["trace_json"]


def test_web_app_direct_build_report_marks_search_skipped(tmp_path: Path) -> None:
    web_app = SkillPilotWebApp(config_loader=lambda: web_config(tmp_path))

    payload = web_app.run_requirement("帮我构造一个课程提示 Skill", "build")

    assert payload["result"]["search_plan"] is None
    assert payload["result"]["search_results"] == []
    assert payload["result"]["retrieved_contents"] == []
    assert "搜索与候选评估阶段已跳过" in payload["report_markdown"]
    assert "搜索源：" not in payload["report_markdown"]


def test_web_app_start_run_records_background_workflow(tmp_path: Path) -> None:
    web_app = SkillPilotWebApp(config_loader=lambda: web_config(tmp_path))

    snapshot = web_app.start_run("我想让 Claude 帮我检查课程论文结构", "recommend")

    assert snapshot["job_id"]
    final_snapshot = wait_for_job(web_app, snapshot["job_id"])
    assert final_snapshot["status"] == "complete"
    assert final_snapshot["result"]["summary"]["decision_type"] in {
        "recommend_existing",
        "recommend_with_custom_extension",
        "build_custom_skill",
    }
    skills = {event["skill"] for event in final_snapshot["events"]}
    assert "RunQueued" in skills
    assert "SourceSearchDispatchSkill" in skills
    assert "CandidateEvaluationDispatchSkill" in skills
    dispatch = next(
        event for event in final_snapshot["events"] if event["skill"] == "SourceSearchDispatchSkill"
    )
    assert dispatch["metadata"]["queries"]
    jobs = web_app.job_snapshots()["jobs"]
    assert jobs[0]["has_result"] is True
    assert jobs[0]["event_count"] == len(final_snapshot["events"])


def test_web_app_environment_snapshot_masks_sensitive_values(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "claude-secret")
    web_app = SkillPilotWebApp(config_loader=lambda: web_config(tmp_path))

    snapshot = web_app.env_snapshot()

    provider = next(item for item in snapshot["variables"] if item["name"] == "SKILLPILOT_LLM_PROVIDER")
    assert provider["value"] == "static_json"
    github_token = next(item for item in snapshot["variables"] if item["name"] == "GITHUB_TOKEN")
    assert github_token["value"] == "•" * len("secret-token")
    assert github_token["sensitive"] is True
    assert github_token["masked"] is True
    assert "ANTHROPIC_API_KEY" not in {item["name"] for item in snapshot["variables"]}


def test_web_app_updates_allowed_environment_values(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("SKILLPILOT_SEARCH_MAX_RESULTS", raising=False)
    web_app = SkillPilotWebApp(config_loader=lambda: web_config(tmp_path))

    snapshot = web_app.update_env({"SKILLPILOT_SEARCH_MAX_RESULTS": "7"})

    assert snapshot["variables"]
    assert next(
        item for item in snapshot["variables"] if item["name"] == "SKILLPILOT_SEARCH_MAX_RESULTS"
    )["value"] == "7"


def test_web_app_rejects_disallowed_environment_values(tmp_path: Path) -> None:
    web_app = SkillPilotWebApp(config_loader=lambda: web_config(tmp_path))

    try:
        web_app.update_env({"ANTHROPIC_API_KEY": "secret"})
    except ValueError as exc:
        assert "不允许" in str(exc)
    else:
        raise AssertionError("Expected disallowed env update to fail.")


def test_web_app_updates_sensitive_environment_values(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    web_app = SkillPilotWebApp(config_loader=lambda: web_config(tmp_path))

    snapshot = web_app.update_env({"GITHUB_TOKEN": "new-token"})

    github_token = next(item for item in snapshot["variables"] if item["name"] == "GITHUB_TOKEN")
    assert github_token["value"] == "•" * len("new-token")
    assert github_token["configured"] is True


def test_web_app_can_cancel_run(tmp_path: Path) -> None:
    web_app = SkillPilotWebApp(
        config_loader=lambda: web_config(tmp_path, builder_interactive=True)
    )
    snapshot = web_app.start_run("帮我构造一个课程提示 Skill", "build")

    cancelled = web_app.cancel_job(snapshot["job_id"])

    assert cancelled["status"] == "cancelled"
    assert cancelled["cancelled"] is True


def test_web_app_builder_waits_for_option_answers(tmp_path: Path) -> None:
    web_app = SkillPilotWebApp(
        config_loader=lambda: web_config(tmp_path, builder_interactive=True)
    )

    snapshot = web_app.start_run(
        "帮我构造一个根据课程课件给作业题提示知识点但不直接给答案的 Skill",
        "build",
    )
    job_id = snapshot["job_id"]

    for _ in range(3):
        waiting = wait_for_job_status(web_app, job_id, "waiting_for_builder_answer")
        question = waiting["pending_question"]
        assert question["options"]
        web_app.submit_answer(job_id, question["question_id"], question["options"][0]["option_id"])

    final_snapshot = wait_for_job(web_app, job_id)
    assert final_snapshot["status"] == "complete"
    skills = {event["skill"] for event in final_snapshot["events"]}
    assert "BuilderQuestionSkill" in skills
    assert "BuilderAnswerSkill" in skills


def test_cli_web_help() -> None:
    result = CliRunner().invoke(app, ["web", "--help"])

    assert result.exit_code == 0
    assert "Start the local SkillPilot web UI" in result.output


def wait_for_job(web_app: SkillPilotWebApp, job_id: str) -> dict:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        snapshot = web_app.job_snapshot(job_id)
        assert snapshot is not None
        if snapshot["status"] in {"complete", "failed"}:
            return snapshot
        time.sleep(0.05)
    raise AssertionError("Timed out waiting for web job.")


def wait_for_job_status(web_app: SkillPilotWebApp, job_id: str, status: str) -> dict:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        snapshot = web_app.job_snapshot(job_id)
        assert snapshot is not None
        if snapshot["status"] == status:
            return snapshot
        if snapshot["status"] == "failed":
            raise AssertionError(snapshot["error"])
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for web job status {status}.")
