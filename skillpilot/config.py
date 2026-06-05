from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class LLMConfig:
    provider: str = "claude_cli"
    claude_command: str = "claude"
    max_budget_usd: float | None = None
    disable_tools: bool = True
    no_session_persistence: bool = True
    enable_evaluation: bool = True


@dataclass(frozen=True)
class SearchConfig:
    enable_network_search: bool = True
    timeout_seconds: float = 8.0
    max_results_per_query: int = 5
    github_token: str | None = None
    proxy_url: str | None = None
    user_agent: str = "SkillPilot/0.1"


@dataclass(frozen=True)
class AppConfig:
    project_root: Path
    data_dir: Path
    outputs_dir: Path
    generated_skills_dir: Path
    llm: LLMConfig
    search: SearchConfig


def load_config() -> AppConfig:
    """Load runtime configuration without duplicating secrets or endpoint settings."""
    max_budget = os.getenv("SKILLPILOT_CLAUDE_MAX_BUDGET_USD")
    llm = LLMConfig(
        provider=os.getenv("SKILLPILOT_LLM_PROVIDER", "claude_cli"),
        claude_command=os.getenv("SKILLPILOT_CLAUDE_COMMAND", "claude"),
        max_budget_usd=float(max_budget) if max_budget else None,
        disable_tools=os.getenv("SKILLPILOT_CLAUDE_DISABLE_TOOLS", "1") != "0",
        no_session_persistence=os.getenv("SKILLPILOT_CLAUDE_NO_SESSION", "1") != "0",
        enable_evaluation=os.getenv("SKILLPILOT_ENABLE_LLM_EVALUATION", "1") != "0",
    )
    search = SearchConfig(
        enable_network_search=os.getenv("SKILLPILOT_ENABLE_NETWORK_SEARCH", "1") == "1",
        timeout_seconds=float(os.getenv("SKILLPILOT_SEARCH_TIMEOUT_SECONDS", "8")),
        max_results_per_query=int(os.getenv("SKILLPILOT_SEARCH_MAX_RESULTS", "5")),
        github_token=os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN"),
        proxy_url=(
            os.getenv("SKILLPILOT_HTTP_PROXY")
            or os.getenv("SKILLPILOT_HTTPS_PROXY")
            or os.getenv("HTTPS_PROXY")
            or os.getenv("HTTP_PROXY")
            or os.getenv("ALL_PROXY")
        ),
        user_agent=os.getenv("SKILLPILOT_SEARCH_USER_AGENT", "SkillPilot/0.1"),
    )
    return AppConfig(
        project_root=PROJECT_ROOT,
        data_dir=PROJECT_ROOT / "data",
        outputs_dir=PROJECT_ROOT / "outputs",
        generated_skills_dir=PROJECT_ROOT / "generated_skills",
        llm=llm,
        search=search,
    )
