from __future__ import annotations

from skillpilot.config import SearchConfig
from skillpilot.models import RetrievedContent, SearchResult, TypeClassification
from skillpilot.modules.candidate_extractor import CandidateExtractor
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


def test_candidate_extractor_uses_retrieved_repo_content() -> None:
    search_result = SearchResult(
        title="owner/pdf-mcp",
        url="https://github.com/owner/pdf-mcp",
        snippet="An MCP server for PDF document reading.",
        source_type="github",
        query="PDF reading MCP server GitHub",
        status="success",
    )
    retrieved = RetrievedContent(
        title="owner/pdf-mcp",
        url="https://github.com/owner/pdf-mcp",
        source_type="github",
        query=search_result.query,
        status="success",
        content=(
            "# owner/pdf-mcp\n"
            "A Model Context Protocol server that lets Claude read PDF documents.\n"
            "## Installation\n"
            "Run npm install and configure a GitHub token only if repository access is needed.\n"
            "The server extracts text from PDF files for document parsing workflows."
        ),
        metadata={
            "full_name": "owner/pdf-mcp",
            "description": "MCP server for PDF document reading.",
            "last_updated": "2026-06-05T00:00:00Z",
            "common_files": ["package.json"],
        },
    )
    classification = TypeClassification(
        recommended_type="mcp",
        confidence=0.78,
        reason="需求适合 MCP。",
    )

    candidates = CandidateExtractor().extract([search_result], [retrieved], classification)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.name == "owner/pdf-mcp"
    assert candidate.extension_type == "mcp"
    assert "pdf_reading" in candidate.capabilities
    assert "document_parsing" in candidate.capabilities
    assert candidate.installation is not None
    assert "node" in candidate.dependencies
    assert "read_documents" in candidate.permissions
    assert candidate.maintainer == "owner"
    assert candidate.last_updated == "2026-06-05T00:00:00Z"
    assert candidate.evidence
