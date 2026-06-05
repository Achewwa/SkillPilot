# SkillPilot Subject Info

This file records the current subject-facing behavior, output format, and newly added project capabilities for synchronization and report writing.

## Current Stage

Stage 2.1 and 2.2 are implemented on branch `feature/stage2-search-interface-planning`.

- 2.1 Search Interface Layer:
  - Added unified `SearchQuery` and `SearchResult` models.
  - Added `WebSearchTool` for ordinary web search.
  - Added `GitHubSearchTool` for GitHub repository search and metadata lookup.
  - Added `SearchExecutor` to run planned queries and preserve success, no-result, skipped, and failed statuses.
  - Added timeout and structured error handling so failed searches are visible in the trace.
- 2.2 Search Planning:
  - Upgraded `SourcePlanner` to generate 3 to 5 targeted queries.
  - Query patterns now vary by Skill, MCP, Plugin, mixed, and unknown extension needs.
  - Query terms include Claude ecosystem keywords such as `Claude Skill`, `SKILL.md`, `Claude Code plugin`, `MCP server`, and `GitHub`.
  - Search plans are saved in `outputs/decision_trace.json`, the recommendation report, and CLI output.

## Network Search Configuration

Network search is disabled by default for stable local tests.

```bash
SKILLPILOT_ENABLE_NETWORK_SEARCH=1 \
SKILLPILOT_HTTP_PROXY=http://172.22.0.1:7890 \
conda run -n skill_pilot python main.py recommend "阅读pdf的插件"
```

Useful environment variables:

- `SKILLPILOT_ENABLE_NETWORK_SEARCH=1`: enable real Web/GitHub search.
- `SKILLPILOT_HTTP_PROXY`: explicit proxy URL for WSL-to-Windows proxy access.
- `SKILLPILOT_HTTPS_PROXY`: optional HTTPS proxy override.
- `SKILLPILOT_SEARCH_TIMEOUT_SECONDS`: per-query timeout, default `8`.
- `SKILLPILOT_SEARCH_MAX_RESULTS`: max results per query, default `5`.
- `GITHUB_TOKEN` or `GH_TOKEN`: optional GitHub API token.

## CLI Return Format

The CLI now prints the final decision plus search middle states:

```text
Decision: <decision_type>
Search queries: <query_count>
  1. [<source_type>] <query_text>
Search results: <result_count>
  - [<source_type>/<status>] <title_or_query>
    <url_or_error_message>
Report: <outputs/recommendation_report.md>
Trace: <outputs/decision_trace.json>
Skill draft: <generated_skill_path>
```

`source_type` is `web` or `github`.

`status` can be:

- `success`: returned a usable result.
- `no_results`: search executed but returned no visible results.
- `failed`: search failed and the error is recorded.
- `skipped`: network search is disabled.

## Report And Trace Additions

`outputs/recommendation_report.md` now includes:

- Search plan: extension type, sources, query text, and query purpose.
- Search results: source, status, title, URL, original query, snippet, or error message.

`outputs/decision_trace.json` now includes:

- `search_plan.queries`: structured `SearchQuery` objects.
- `search_results`: structured `SearchResult` objects with retrieval status and metadata.

## Verified Network Test

Test requirement:

```text
阅读pdf的插件
```

Observed behavior:

- Requirement parser identifies PDF/document processing capabilities.
- Classifier chooses `plugin` because the user explicitly asks for a plugin.
- Query planner generates Claude Code plugin search queries.
- Proxied web search returns real results, including:
  - `https://github.com/ZSHYC/pdf-master`
  - `https://zshyc.github.io/pdf-master/`

The final decision is still `build_custom_skill` because Stage 2.3 and 2.4 have not yet wired search results into candidate reading, extraction, and ranking.

## Verification

```bash
conda run -n skill_pilot python -m pytest
```

Latest result:

```text
9 passed
```
