from __future__ import annotations

from skillpilot import config


def test_resolve_github_token_prefers_environment(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "env-token")
    monkeypatch.setattr(config, "_read_github_cli_token", lambda: "cli-token")

    assert config._resolve_github_token() == "env-token"


def test_resolve_github_token_falls_back_to_github_cli(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(config, "_read_github_cli_token", lambda: "cli-token")

    assert config._resolve_github_token() == "cli-token"
