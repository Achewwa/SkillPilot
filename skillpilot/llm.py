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
        command.extend(["--model", self.config.claude_model])
        if self.config.disable_tools:
            command.extend(["--tools", ""])
        if self.config.no_session_persistence:
            command.append("--no-session-persistence")
        if self.config.max_budget_usd is not None:
            command.extend(["--max-budget-usd", str(self.config.max_budget_usd)])

        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            input=prompt,
        )
        return LLMResponse(text=result.stdout.strip(), provider=self.config.provider)


class StaticJsonLLM:
    """Deterministic JSON provider for offline tests and smoke runs."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def generate(self, prompt: str) -> LLMResponse:
        return LLMResponse(
            text=(
                '{"task_domain":"general","desired_capabilities":["general_guidance"],'
                '"requires_codebase_access":false,"requires_command_execution":false,'
                '"requires_external_service":false,"risk_tolerance":"medium"}'
            ),
            provider=self.config.provider,
        )


def create_llm(config: LLMConfig) -> ClaudeCliLLM | StaticJsonLLM:
    if config.provider != "claude_cli":
        if config.provider == "static_json":
            return StaticJsonLLM(config)
        raise ValueError(f"Unsupported LLM provider for skeleton: {config.provider}")
    return ClaudeCliLLM(config)
