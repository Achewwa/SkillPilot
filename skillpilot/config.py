from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class LLMConfig:
    provider: str = "claude_cli"
    claude_command: str = "claude"
    max_budget_usd: float = 0.05
    disable_tools: bool = True
    no_session_persistence: bool = True


@dataclass(frozen=True)
class AppConfig:
    project_root: Path
    data_dir: Path
    outputs_dir: Path
    generated_skills_dir: Path
    llm: LLMConfig


def load_config() -> AppConfig:
    """Load runtime configuration without duplicating secrets or endpoint settings."""
    llm = LLMConfig(
        provider=os.getenv("SKILLPILOT_LLM_PROVIDER", "claude_cli"),
        claude_command=os.getenv("SKILLPILOT_CLAUDE_COMMAND", "claude"),
        max_budget_usd=float(os.getenv("SKILLPILOT_CLAUDE_MAX_BUDGET_USD", "0.05")),
        disable_tools=os.getenv("SKILLPILOT_CLAUDE_DISABLE_TOOLS", "1") != "0",
        no_session_persistence=os.getenv("SKILLPILOT_CLAUDE_NO_SESSION", "1") != "0",
    )
    return AppConfig(
        project_root=PROJECT_ROOT,
        data_dir=PROJECT_ROOT / "data",
        outputs_dir=PROJECT_ROOT / "outputs",
        generated_skills_dir=PROJECT_ROOT / "generated_skills",
        llm=llm,
    )
