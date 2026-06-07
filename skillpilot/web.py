from __future__ import annotations

import json
import mimetypes
import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote

from skillpilot.agent import SkillPilotAgent
from skillpilot.agents.core import TraceObserver
from skillpilot.config import AppConfig, load_config
from skillpilot.models import AgentRunResult, model_to_dict


ASSETS_DIR = Path(__file__).resolve().parent / "web_assets"
ENV_KEYS = [
    "SKILLPILOT_LLM_PROVIDER",
    "SKILLPILOT_ENABLE_NETWORK_SEARCH",
    "SKILLPILOT_ENABLE_LLM_EVALUATION",
    "SKILLPILOT_SEARCH_TIMEOUT_SECONDS",
    "SKILLPILOT_SEARCH_MAX_RESULTS",
    "SKILLPILOT_CLAUDE_MODEL",
    "SKILLPILOT_OUTPUTS_DIR",
    "SKILLPILOT_GENERATED_SKILLS_DIR",
]
SENSITIVE_ENV_KEYS = ["GITHUB_TOKEN"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RunJob:
    job_id: str
    requirement: str
    mode: str
    status: str = "queued"
    events: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: str | None = None
    cancelled: bool = False
    pending_question: dict[str, Any] | None = None
    pending_answer: dict[str, str] | None = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    lock: threading.RLock = field(default_factory=threading.RLock)
    answer_condition: threading.Condition = field(init=False)

    def __post_init__(self) -> None:
        self.answer_condition = threading.Condition(self.lock)

    def add_event(
        self,
        agent: str,
        skill: str,
        *,
        status: str = "success",
        summary: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self.lock:
            self.events.append(
                {
                    "agent": agent,
                    "skill": skill,
                    "status": status,
                    "summary": summary,
                    "metadata": metadata or {},
                    "created_at": _now(),
                }
            )
            self.updated_at = _now()

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "job_id": self.job_id,
                "requirement": self.requirement,
                "mode": self.mode,
                "status": self.status,
                "events": list(self.events),
                "result": self.result,
                "error": self.error,
                "cancelled": self.cancelled,
                "pending_question": self.pending_question,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
            }

    def mark_running(self) -> None:
        with self.lock:
            if self.cancelled:
                return
            self.status = "running"
            self.updated_at = _now()

    def mark_complete(self, result: dict[str, Any]) -> None:
        with self.lock:
            if self.cancelled:
                return
            self.status = "complete"
            self.result = result
            self.updated_at = _now()

    def mark_failed(self, error: str) -> None:
        with self.lock:
            if self.cancelled:
                return
            self.status = "failed"
            self.error = error
            self.updated_at = _now()

    def cancel(self) -> None:
        with self.answer_condition:
            self.cancelled = True
            self.status = "cancelled"
            self.pending_question = None
            self.pending_answer = None
            self.updated_at = _now()
            self.add_event(
                "WebServer",
                "RunCancelled",
                status="skipped",
                summary="用户确认 New，当前运行状态已取消并清空。",
            )
            self.answer_condition.notify_all()

    def set_pending_question(self, question: dict[str, Any]) -> None:
        with self.answer_condition:
            if self.cancelled:
                raise RuntimeError("Run cancelled.")
            self.status = "waiting_for_builder_answer"
            self.pending_question = question
            self.pending_answer = None
            self.updated_at = _now()
            self.add_event(
                "SkillBuilderAgent",
                "BuilderQuestionSkill",
                status="skipped",
                summary=question.get("prompt", "等待用户选择 Builder 选项。"),
                metadata={"question": question},
            )

    def submit_answer(self, question_id: str, answer: str) -> None:
        with self.answer_condition:
            if self.cancelled:
                raise ValueError("Run cancelled.")
            if not self.pending_question:
                raise ValueError("当前没有等待回答的问题。")
            if self.pending_question.get("question_id") != question_id:
                raise ValueError("问题 ID 与当前等待问题不匹配。")
            cleaned = answer.strip()
            if not cleaned:
                raise ValueError("回答不能为空。")
            self.pending_answer = {"question_id": question_id, "answer": cleaned}
            self.status = "running"
            self.updated_at = _now()
            self.add_event(
                "SkillBuilderAgent",
                "BuilderAnswerSkill",
                summary=f"已收到 `{question_id}` 的回答。",
                metadata={"question_id": question_id, "answer": cleaned},
            )
            self.answer_condition.notify_all()

    def wait_for_answer(self, question_id: str) -> str:
        with self.answer_condition:
            while (
                self.pending_answer is None
                or self.pending_answer.get("question_id") != question_id
            ):
                if self.cancelled:
                    raise RuntimeError("Run cancelled.")
                self.answer_condition.wait()
            answer = self.pending_answer["answer"]
            self.pending_answer = None
            self.pending_question = None
            self.status = "running"
            self.updated_at = _now()
            return answer


class SkillPilotWebApp:
    """HTTP-facing wrapper that keeps the web layer thin and pipeline-driven."""

    def __init__(
        self,
        config_loader: Callable[[], AppConfig] = load_config,
        agent_factory: Callable[[AppConfig], SkillPilotAgent] = SkillPilotAgent,
    ) -> None:
        self.config_loader = config_loader
        self.agent_factory = agent_factory
        self.jobs: dict[str, RunJob] = {}
        self.jobs_lock = threading.Lock()

    def demo_cases(self) -> dict[str, str]:
        config = self.config_loader()
        cases_path = config.data_dir / "demo_cases.json"
        if not cases_path.exists():
            return {}
        return json.loads(cases_path.read_text(encoding="utf-8"))

    def env_snapshot(self) -> dict[str, Any]:
        config = self.config_loader()
        effective_values = {
            "SKILLPILOT_LLM_PROVIDER": config.llm.provider,
            "SKILLPILOT_ENABLE_NETWORK_SEARCH": "1" if config.search.enable_network_search else "0",
            "SKILLPILOT_ENABLE_LLM_EVALUATION": "1" if config.llm.enable_evaluation else "0",
            "SKILLPILOT_SEARCH_TIMEOUT_SECONDS": str(config.search.timeout_seconds),
            "SKILLPILOT_SEARCH_MAX_RESULTS": str(config.search.max_results_per_query),
            "SKILLPILOT_CLAUDE_MODEL": config.llm.claude_model,
            "SKILLPILOT_OUTPUTS_DIR": str(config.outputs_dir),
            "SKILLPILOT_GENERATED_SKILLS_DIR": str(config.generated_skills_dir),
        }
        values = [
            {
                "name": key,
                "value": os.getenv(key) if key in os.environ else effective_values.get(key, ""),
                "sensitive": False,
                "configured": key in os.environ,
            }
            for key in ENV_KEYS
        ]
        values.extend(self._sensitive_env_items())
        return {"variables": values}

    def update_env(self, updates: dict[str, Any]) -> dict[str, Any]:
        for key, value in updates.items():
            if key not in {*ENV_KEYS, *SENSITIVE_ENV_KEYS}:
                raise ValueError(f"不允许通过 Web UI 设置 {key}。")
            cleaned = str(value).strip()
            if cleaned:
                os.environ[key] = cleaned
            elif key in SENSITIVE_ENV_KEYS:
                continue
            else:
                os.environ.pop(key, None)
        return self.env_snapshot()

    def _sensitive_env_items(self) -> list[dict[str, Any]]:
        github_key = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or ""
        return [
            {
                "name": "GITHUB_TOKEN",
                "value": "•" * len(github_key) if github_key else "",
                "sensitive": True,
                "configured": bool(github_key),
                "masked": bool(github_key),
            },
        ]

    def start_run(self, requirement: str, mode: str) -> dict[str, Any]:
        cleaned = self._validate_run(requirement, mode)
        job = RunJob(job_id=uuid.uuid4().hex, requirement=cleaned, mode=mode)
        job.add_event(
            "WebServer",
            "RunQueued",
            summary="已提交运行任务，等待后台 agent 启动。",
            metadata={"mode": mode},
        )
        with self.jobs_lock:
            self.jobs[job.job_id] = job
        thread = threading.Thread(target=self._execute_job, args=(job,), daemon=True)
        thread.start()
        return job.snapshot()

    def job_snapshot(self, job_id: str) -> dict[str, Any] | None:
        with self.jobs_lock:
            job = self.jobs.get(job_id)
        return job.snapshot() if job else None

    def job_snapshots(self) -> dict[str, Any]:
        with self.jobs_lock:
            jobs = list(self.jobs.values())
        snapshots = []
        for job in jobs:
            snapshot = job.snapshot()
            snapshots.append(
                {
                    "job_id": snapshot["job_id"],
                    "requirement": snapshot["requirement"],
                    "mode": snapshot["mode"],
                    "status": snapshot["status"],
                    "error": snapshot["error"],
                    "cancelled": snapshot["cancelled"],
                    "pending_question": snapshot["pending_question"],
                    "created_at": snapshot["created_at"],
                    "updated_at": snapshot["updated_at"],
                    "event_count": len(snapshot["events"]),
                    "events": snapshot["events"][-5:],
                    "has_result": snapshot["result"] is not None,
                }
            )
        return {"jobs": snapshots}

    def submit_answer(self, job_id: str, question_id: str, answer: str) -> dict[str, Any]:
        with self.jobs_lock:
            job = self.jobs.get(job_id)
        if job is None:
            raise ValueError("Run not found.")
        job.submit_answer(question_id, answer)
        return job.snapshot()

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        with self.jobs_lock:
            job = self.jobs.get(job_id)
        if job is None:
            return {"job_id": job_id, "status": "cancelled"}
        job.cancel()
        return job.snapshot()

    def run_requirement(
        self,
        requirement: str,
        mode: str,
        trace_observer: TraceObserver | None = None,
        answer_provider: Callable[[Any], str] | None = None,
    ) -> dict[str, Any]:
        cleaned = self._validate_run(requirement, mode)
        agent = self.agent_factory(self.config_loader())
        result = (
            agent.build_skill(
                cleaned,
                interactive_builder=answer_provider is not None,
                answer_provider=answer_provider,
                trace_observer=trace_observer,
            )
            if mode == "build"
            else agent.recommend(
                cleaned,
                interactive_builder=answer_provider is not None,
                answer_provider=answer_provider,
                trace_observer=trace_observer,
            )
        )
        return result_payload(result)

    def _validate_run(self, requirement: str, mode: str) -> str:
        cleaned = requirement.strip()
        if not cleaned:
            raise ValueError("请输入一段需求。")
        if mode not in {"recommend", "build"}:
            raise ValueError("mode 必须是 recommend 或 build。")
        return cleaned

    def _execute_job(self, job: RunJob) -> None:
        job.mark_running()
        job.add_event(
            "WebServer",
            "RunStarted",
            summary="后台 agent 已启动，开始执行 SkillPilot pipeline。",
            metadata={"mode": job.mode},
        )

        def observe(event) -> None:
            if job.cancelled:
                raise RuntimeError("Run cancelled.")
            payload = model_to_dict(event)
            job.add_event(
                payload["agent"],
                payload["skill"],
                status=payload["status"],
                summary=payload.get("summary", ""),
                metadata=payload.get("metadata") or {},
            )

        def answer_provider(question) -> str:
            payload = model_to_dict(question)
            job.set_pending_question(payload)
            return job.wait_for_answer(payload["question_id"])

        try:
            result = self.run_requirement(
                job.requirement,
                job.mode,
                trace_observer=observe,
                answer_provider=answer_provider,
            )
        except Exception as exc:  # noqa: BLE001 - local UI should show agent failures.
            if job.cancelled:
                return
            job.mark_failed(str(exc))
            job.add_event(
                "WebServer",
                "RunFailed",
                status="failed",
                summary=str(exc),
            )
            return

        if not job.cancelled:
            job.mark_complete(result)
            job.add_event(
                "WebServer",
                "RunCompleted",
                summary="运行完成，结果和报告已写入页面。",
            )


def result_payload(result: AgentRunResult) -> dict[str, Any]:
    return {
        "summary": result_summary(result),
        "result": model_to_dict(result),
        "report_markdown": _read_text(result.report_path),
        "trace_json": _read_text(result.trace_path),
    }


def result_summary(result: AgentRunResult) -> dict[str, Any]:
    decision = result.decision
    top = decision.selected_candidates[0] if decision.selected_candidates else None
    skill_draft = result.skill_draft
    return {
        "decision_type": decision.decision_type,
        "decision_reason": decision.reason,
        "recommended_type": result.classification.recommended_type,
        "classification_confidence": result.classification.confidence,
        "candidate_count": len(result.evaluations),
        "search_count": len(result.search_results),
        "successful_reads": sum(1 for item in result.retrieved_contents if item.status == "success"),
        "read_count": len(result.retrieved_contents),
        "trace_event_count": len(result.trace_events),
        "top_candidate": top.candidate.name if top else None,
        "top_score": top.match_score if top else None,
        "top_risk": top.risk_level if top else None,
        "report_path": result.report_path,
        "trace_path": result.trace_path,
        "skill_draft_path": skill_draft.path if skill_draft else None,
        "skill_draft_name": skill_draft.name if skill_draft else None,
    }


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    app = SkillPilotWebApp()
    server = ThreadingHTTPServer((host, port), _handler_for(app))
    url = f"http://{host}:{port}"
    print(f"SkillPilot Web UI running at {url}")  # noqa: T201 - CLI entrypoint feedback.
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSkillPilot Web UI stopped.")  # noqa: T201
    finally:
        server.server_close()


def _handler_for(app: SkillPilotWebApp) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API.
            path = _clean_path(self.path)
            if path in {"", "/", "/index.html"}:
                self._send_asset("index.html", "text/html; charset=utf-8")
                return
            if path == "/api/health":
                self._send_json({"status": "ok"})
                return
            if path == "/api/demo-cases":
                self._send_json({"cases": app.demo_cases()})
                return
            if path == "/api/env":
                self._send_json(app.env_snapshot())
                return
            if path == "/api/jobs":
                self._send_json(app.job_snapshots())
                return
            if path.startswith("/api/runs/"):
                snapshot = app.job_snapshot(path.removeprefix("/api/runs/"))
                if snapshot is None:
                    self._send_json({"error": "Run not found"}, HTTPStatus.NOT_FOUND)
                    return
                self._send_json(snapshot)
                return
            if path.startswith("/assets/"):
                self._send_asset(path.removeprefix("/assets/"))
                return
            self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API.
            path = _clean_path(self.path)
            if path == "/api/runs":
                try:
                    payload = self._read_json_body()
                    response = app.start_run(
                        str(payload.get("requirement") or ""),
                        str(payload.get("mode") or "recommend"),
                    )
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                    return
                except Exception as exc:  # noqa: BLE001 - surface runtime failure to local UI.
                    self._send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
                    return
                self._send_json(response)
                return
            if path == "/api/env":
                try:
                    payload = self._read_json_body()
                    response = app.update_env(payload.get("updates") or {})
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                    return
                except Exception as exc:  # noqa: BLE001 - surface runtime failure to local UI.
                    self._send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
                    return
                self._send_json(response)
                return
            if path.startswith("/api/runs/") and path.endswith("/answers"):
                job_id = path.removeprefix("/api/runs/").removesuffix("/answers")
                try:
                    payload = self._read_json_body()
                    response = app.submit_answer(
                        job_id,
                        str(payload.get("question_id") or ""),
                        str(payload.get("answer") or ""),
                    )
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                    return
                except Exception as exc:  # noqa: BLE001 - surface runtime failure to local UI.
                    self._send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
                    return
                self._send_json(response)
                return
            if path.startswith("/api/runs/") and path.endswith("/cancel"):
                job_id = path.removeprefix("/api/runs/").removesuffix("/cancel")
                try:
                    response = app.cancel_job(job_id)
                except Exception as exc:  # noqa: BLE001 - surface runtime failure to local UI.
                    self._send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
                    return
                self._send_json(response)
                return
            else:
                self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
                return

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _read_json_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length") or 0)
            if length > 128_000:
                raise ValueError("请求内容过长。")
            raw = self.rfile.read(length).decode("utf-8")
            if not raw:
                return {}
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError("请求体必须是合法 JSON。") from exc
            if not isinstance(parsed, dict):
                raise ValueError("请求体必须是 JSON object。")
            return parsed

        def _send_asset(self, name: str, content_type: str | None = None) -> None:
            asset_path = (ASSETS_DIR / name).resolve()
            if ASSETS_DIR not in asset_path.parents and asset_path != ASSETS_DIR:
                self._send_json({"error": "Invalid asset path"}, HTTPStatus.BAD_REQUEST)
                return
            if not asset_path.exists() or not asset_path.is_file():
                self._send_json({"error": "Asset not found"}, HTTPStatus.NOT_FOUND)
                return
            body = asset_path.read_bytes()
            guessed = content_type or mimetypes.guess_type(asset_path.name)[0] or "text/plain"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", guessed)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_json(
            self,
            payload: dict[str, Any],
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def _clean_path(raw_path: str) -> str:
    return unquote(raw_path.split("?", 1)[0])


def _read_text(path: str) -> str:
    target = Path(path)
    if not target.exists() or not target.is_file():
        return ""
    return target.read_text(encoding="utf-8")
