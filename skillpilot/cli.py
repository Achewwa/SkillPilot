from __future__ import annotations

import json
from enum import Enum

import typer
from rich.console import Console

from skillpilot.agent import SkillPilotAgent
from skillpilot.agents.core import PipelineContext
from skillpilot.config import load_config
from skillpilot.models import ClarificationQuestion


app = typer.Typer(
    help="SkillPilot CLI skeleton.",
    invoke_without_command=True,
    no_args_is_help=False,
)
console = Console()
_last_previewed_decision: str | None = None


class DemoCase(str, Enum):
    skill = "skill"
    mcp = "mcp"
    build = "build"


def _agent() -> SkillPilotAgent:
    return SkillPilotAgent(load_config())


def _print_result(result) -> None:
    console.print(f"[bold]Decision:[/bold] {result.decision.decision_type}")
    if result.decision.selected_candidates:
        evaluation = result.decision.selected_candidates[0]
        candidate = evaluation.candidate
        console.print(f"[bold]Top candidate:[/bold] {candidate.name}")
        console.print(f"  Score: {evaluation.match_score}", markup=False)
        console.print(f"  Type: {candidate.extension_type}", markup=False)
        console.print(f"  Risk: {evaluation.risk_level}", markup=False)
        console.print(f"  Description: {candidate.description}", markup=False)
        console.print(f"  Source: {candidate.source_url}", markup=False)
        console.print(f"  Reason: {evaluation.reason}", markup=False)
    else:
        console.print("[bold]Top candidate:[/bold] none")
        console.print(f"  Reason: {result.decision.reason}", markup=False)
    if result.retrieved_contents:
        successful_reads = sum(1 for item in result.retrieved_contents if item.status == "success")
        console.print(
            f"[bold]Read results:[/bold] {successful_reads}/{len(result.retrieved_contents)} succeeded"
        )
    console.print(f"[bold]Report:[/bold] {result.report_path}")
    console.print(f"[bold]Trace:[/bold] {result.trace_path}")
    if result.skill_draft:
        console.print(f"[bold]Skill draft:[/bold] {result.skill_draft.path}")
        if result.skill_draft.safety_review:
            console.print(
                f"[bold]Skill safety:[/bold] {result.skill_draft.safety_review.risk_level}"
            )
        if result.skill_draft.warnings:
            console.print(f"  Warning: {result.skill_draft.warnings[0]}", markup=False)


def _print_decision_preview(context: PipelineContext) -> None:
    global _last_previewed_decision

    decision = context.require_decision()
    if decision.decision_type == "recommend_existing":
        _last_previewed_decision = None
        return

    signature = f"{id(context)}:{decision.decision_type}:{decision.reason}"
    if signature == _last_previewed_decision:
        return
    _last_previewed_decision = signature

    console.print("\n[bold]Decision stage completed[/bold]")
    console.print(f"Decision: {decision.decision_type}", markup=False)
    console.print(f"Reason: {decision.reason}", markup=False)
    console.print(
        f"Evaluated candidates: {len(context.evaluations)}",
        markup=False,
    )
    if context.evaluations:
        best = context.evaluations[0]
        console.print(
            (
                "Best candidate: "
                f"{best.candidate.name} "
                f"(score={best.match_score}, risk={best.risk_level})"
            ),
            markup=False,
        )
        if best.missing_capabilities:
            console.print(
                f"Missing capabilities: {'、'.join(best.missing_capabilities)}",
                markup=False,
            )
        if best.risk_reasons:
            console.print(f"Risk reason: {best.risk_reasons[0]}", markup=False)
    successful_reads = sum(1 for item in context.retrieved_contents if item.status == "success")
    if context.retrieved_contents:
        console.print(
            f"Read results: {successful_reads}/{len(context.retrieved_contents)} succeeded",
            markup=False,
        )
    if context.report_path:
        console.print(f"Interim report: {context.report_path}", markup=False)
    console.print("Entering SkillBuilder because the decision requires a custom Skill draft.")


def _answer_builder_question(question: ClarificationQuestion) -> str:
    console.print(f"\n[bold]Builder question:[/bold] {question.prompt}")
    console.print(f"Reason: {question.reason}", markup=False)
    if question.options:
        console.print("Options:")
        for option in question.options:
            console.print(
                f"  {option.option_id}. {option.label} - {option.detail}",
                markup=False,
            )
    return typer.prompt("Choose 1/2/3 or type your own answer").strip()


def _run_demo_case(agent: SkillPilotAgent, case: DemoCase) -> None:
    config = load_config()
    cases_path = config.data_dir / "demo_cases.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    requirement = cases[case.value]
    console.print(f"[bold]Demo case:[/bold] {case.value}")
    console.print(f"[bold]Requirement:[/bold] {requirement}")
    result = agent.build_skill(requirement) if case == DemoCase.build else agent.recommend(requirement)
    _print_result(result)


def _print_session_help() -> None:
    console.print("直接输入自然语言需求，SkillPilot 会自动尝试推荐或构造 Skill。")
    console.print("可用指令：")
    console.print("  /build <需求>      直接生成自定义 Skill 草案")
    console.print("  /demo skill|mcp|build")
    console.print("  /help")
    console.print("  /exit")


def _interactive_session() -> None:
    agent = _agent()
    console.print("[bold]SkillPilot[/bold] interactive session")
    _print_session_help()

    while True:
        try:
            user_input = typer.prompt("skillpilot").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nBye.")
            raise typer.Exit()

        if not user_input:
            continue
        if user_input in {"/exit", "exit", "quit", ":q"}:
            console.print("Bye.")
            raise typer.Exit()
        if user_input == "/help":
            _print_session_help()
            continue
        if user_input.startswith("/build "):
            result = agent.build_skill(
                user_input.removeprefix("/build ").strip(),
                interactive_builder=True,
                answer_provider=_answer_builder_question,
                decision_observer=_print_decision_preview,
            )
            _print_result(result)
            continue
        if user_input.startswith("/demo "):
            case_name = user_input.removeprefix("/demo ").strip()
            try:
                _run_demo_case(agent, DemoCase(case_name))
            except ValueError:
                console.print("Unknown demo case. Use: skill, mcp, or build.")
            continue

        result = agent.recommend(
            user_input,
            interactive_builder=True,
            answer_provider=_answer_builder_question,
            decision_observer=_print_decision_preview,
        )
        _print_result(result)


@app.callback()
def main(ctx: typer.Context) -> None:
    """Start an interactive session when no subcommand is provided."""
    if ctx.invoked_subcommand is None:
        _interactive_session()


@app.command()
def recommend(requirement: str) -> None:
    """Recommend a Claude Skill, Plugin, MCP, or mixed extension plan."""
    result = _agent().recommend(requirement)
    _print_result(result)


@app.command("build-skill")
def build_skill(requirement: str) -> None:
    """Build a custom Skill draft, asking clarifying questions when enabled."""
    result = _agent().build_skill(
        requirement,
        interactive_builder=True,
        answer_provider=_answer_builder_question,
        decision_observer=_print_decision_preview,
    )
    _print_result(result)


@app.command()
def demo(case: DemoCase = typer.Option(..., "--case", "-c")) -> None:
    """Run one of the stable classroom demo cases."""
    _run_demo_case(_agent(), case)


@app.command()
def web(
    host: str = typer.Option("127.0.0.1", "--host", help="Host for the local web UI."),
    port: int = typer.Option(8000, "--port", "-p", help="Port for the local web UI."),
) -> None:
    """Start the local SkillPilot web UI."""
    from skillpilot.web import serve

    serve(host=host, port=port)
