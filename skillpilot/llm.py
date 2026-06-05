from __future__ import annotations

import subprocess
from dataclasses import dataclass

from skillpilot.config import LLMConfig


@dataclass
class LLMResponse:
    text: str
    provider: str


class ClaudeCliLLM:
    """Thin wrapper around the WSL-local Claude CLI configuration."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def generate(self, prompt: str) -> LLMResponse:
        command = [self.config.claude_command, "-p"]
        if self.config.disable_tools:
            command.extend(["--tools", ""])
        if self.config.no_session_persistence:
            command.append("--no-session-persistence")
        command.extend(["--max-budget-usd", str(self.config.max_budget_usd), prompt])

        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
        return LLMResponse(text=result.stdout.strip(), provider=self.config.provider)


def create_llm(config: LLMConfig) -> ClaudeCliLLM:
    if config.provider != "claude_cli":
        raise ValueError(f"Unsupported LLM provider for skeleton: {config.provider}")
    return ClaudeCliLLM(config)
