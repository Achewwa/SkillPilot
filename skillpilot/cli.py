from __future__ import annotations

import json
from enum import Enum

import typer
from rich.console import Console

from skillpilot.agent import SkillPilotAgent
from skillpilot.config import load_config


app = typer.Typer(
    help="SkillPilot CLI skeleton.",
    invoke_without_command=True,
    no_args_is_help=False,
)
console = Console()


class DemoCase(str, Enum):
    skill = "skill"
    mcp = "mcp"
    build = "build"


def _agent() -> SkillPilotAgent:
    return SkillPilotAgent(load_config())


def _print_result(result) -> None:
    console.print(f"[bold]Decision:[/bold] {result.decision.decision_type}")
    console.print(f"[bold]Search queries:[/bold] {len(result.search_plan.queries)}")
    for index, query in enumerate(result.search_plan.queries, start=1):
        console.print(f"  {index}. [{query.source_type}] {query.text}", markup=False)
    if result.search_results:
        console.print(f"[bold]Search results:[/bold] {len(result.search_results)}")
        for item in result.search_results[:10]:
            label = f"[{item.source_type}/{item.status}]"
            target = item.title or item.query
            console.print(f"  - {label} {target}", markup=False)
            if item.url:
                console.print(f"    {item.url}", markup=False)
            elif item.error_message:
                console.print(f"    {item.error_message}", markup=False)
        if len(result.search_results) > 10:
            console.print(f"  ... {len(result.search_results) - 10} more results in trace")
    if result.retrieved_contents:
        successful_reads = sum(1 for item in result.retrieved_contents if item.status == "success")
        console.print(
            f"[bold]Read results:[/bold] {successful_reads}/{len(result.retrieved_contents)} succeeded"
        )
    console.print(f"[bold]Report:[/bold] {result.report_path}")
    console.print(f"[bold]Trace:[/bold] {result.trace_path}")
    if result.skill_draft:
        console.print(f"[bold]Skill draft:[/bold] {result.skill_draft.path}")


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
            result = agent.build_skill(user_input.removeprefix("/build ").strip())
            _print_result(result)
            continue
        if user_input.startswith("/demo "):
            case_name = user_input.removeprefix("/demo ").strip()
            try:
                _run_demo_case(agent, DemoCase(case_name))
            except ValueError:
                console.print("Unknown demo case. Use: skill, mcp, or build.")
            continue

        result = agent.recommend(user_input)
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
    """Build a placeholder custom Skill draft."""
    result = _agent().build_skill(requirement)
    _print_result(result)


@app.command()
def demo(case: DemoCase = typer.Option(..., "--case", "-c")) -> None:
    """Run one of the stable classroom demo cases."""
    _run_demo_case(_agent(), case)
