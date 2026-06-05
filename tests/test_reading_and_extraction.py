from __future__ import annotations

from skillpilot.config import SearchConfig
from skillpilot.models import SearchResult
from skillpilot.modules.readers import ContentReader, RepoReader


def test_repo_reader_parses_github_repository_urls() -> None:
    reader = RepoReader()

    assert reader.parse_github_repo("https://github.com/modelcontextprotocol/servers") == (
        "modelcontextprotocol",
        "servers",
    )
    assert reader.parse_github_repo("https://github.com/owner/repo.git") == (
        "owner",
        "repo",
    )
    assert reader.parse_github_repo("https://example.com/owner/repo") is None


def test_repo_reader_reads_skill_md_from_github_tree_url(monkeypatch) -> None:
    reader = RepoReader()

    def fake_raw_file(_client, owner: str, repo: str, ref: str, path: str) -> str:
        assert (owner, repo, ref) == ("owner", "repo", "main")
        if path == "skills/poster/SKILL.md":
            return "# Poster Skill\nUse this skill to design posters and visual layouts."
        if path == "skills/poster/README.md":
            return "Poster design examples."
        return ""

    monkeypatch.setattr(reader, "_get_raw_github_file", fake_raw_file)
    result = SearchResult(
        title="poster",
        url="https://github.com/owner/repo/tree/main/skills/poster",
        snippet="Poster design skill.",
        source_type="github",
        query="poster design",
        status="success",
        source_id="skillsmp_directory",
        metadata={
            "author": "owner",
            "stars": 12,
            "updated_at": "2026-06-05T00:00:00Z",
            "skillsmp_url": "https://skillsmp.com/skills/poster",
        },
    )

    content = reader.read(result)

    assert content.status == "success"
    assert "Poster Skill" in content.content
    assert content.metadata["source_subpath"] == "skills/poster"
    assert content.metadata["common_files"] == ["SKILL.md"]
    assert content.metadata["last_updated"] == "2026-06-05T00:00:00Z"


def test_skillsmp_tree_result_requires_skill_md(monkeypatch) -> None:
    reader = RepoReader()

    def fake_raw_file(_client, _owner: str, _repo: str, _ref: str, path: str) -> str:
        if path.endswith("README.md"):
            return "Template examples but no Skill manifest."
        return ""

    monkeypatch.setattr(reader, "_get_raw_github_file", fake_raw_file)
    result = SearchResult(
        title="templates",
        url="https://github.com/owner/repo/tree/main/templates",
        snippet="Template examples.",
        source_type="github",
        query="poster design",
        status="success",
        source_id="skillsmp_directory",
    )

    content = reader.read(result)

    assert content.status == "failed"
    assert "No SKILL.md" in (content.error_message or "")


def test_content_reader_records_skipped_search_results() -> None:
    reader = ContentReader(SearchConfig(enable_network_search=False))
    contents = reader.read(
        [
            SearchResult(
                title="",
                url="",
                snippet="Network search is disabled.",
                source_type="web",
                query="PDF reading Claude Code plugin",
                status="skipped",
            )
        ]
    )

    assert len(contents) == 1
    assert contents[0].status == "skipped"
    assert "successful search results" in (contents[0].error_message or "")


