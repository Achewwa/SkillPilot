# SkillPilot Project Info

This file is the project memory file for cross-window synchronization. Update it whenever project scope, progress, environment, or next actions change.

## Project Summary

SkillPilot is a Python-based lightweight agent for Claude extension discovery and construction. Given a user requirement, it should decide whether Skill, Plugin, MCP, or a mixed solution is appropriate, evaluate candidate resources, explain safety risks, and generate either a recommendation report or a custom Skill draft.

The project is for a course assignment on large language model agents. The current implementation direction is to build the agent workflow manually in Python rather than using mature agent frameworks.

## Important Constraints

- Use Python as the main implementation language.
- Do not rely on LangChain, CrewAI, AutoGPT, or other mature agent frameworks for the core workflow.
- Prioritize a complete, explainable, demonstrable agent loop over broad real-time search coverage.
- The MVP should be CLI-first.
- Do not automatically install third-party Claude Code plugins, MCP servers, or third-party scripts.
- Do not automatically execute untrusted shell commands from candidate resources.
- Prioritize real network search for candidate discovery. Cached data should not be the main implementation path.
- For classroom demos, record successful real-search runs in advance instead of relying on offline cache fixtures.
- The previous fixed schedule is invalid. Progress should follow the user's actual pace.

## Completed

- Connected to the WSL project directory: `/home/achewwa/Projects/SkillPilot`.
- Read the course requirement PDF: `info.pdf`.
- Read the original project draft: `project_draft.md`.
- Established the initial project direction: SkillPilot as a search, evaluation, recommendation, and custom Skill building agent.
- Created conda environment `skill_pilot` at `/home/achewwa/miniconda3/envs/skill_pilot`.
- Installed initial Python dependencies in `skill_pilot`:
  - `httpx`
  - `requests`
  - `beautifulsoup4`
  - `pydantic`
  - `typer`
  - `rich`
  - `python-dotenv`
  - `markdownify`
  - `pyyaml`
  - `openai`
  - `PyGithub`
  - `pypdf`
  - `pytest`
  - `pytest-cov`
- Verified the environment with Python `3.11.15` and successful imports.
- Updated WSL Claude Code settings to use the configured third-party endpoint.
- Verified WSL `claude -p` can return `OK` with the current configuration.
- Created `README.md` for project introduction.
- Created this `project_info.md` file for cross-window synchronization.
- Added the runnable Python skeleton:
  - `pyproject.toml`
  - `main.py`
  - `skillpilot/` package
  - CLI commands for `recommend`, `build-skill`, and `demo`
  - Pydantic models for requirements, candidates, evaluations, decisions, and traces
  - Stub pipeline for parsing, classification, source planning, cache loading, evaluation, and decision gating
  - Local demo cache under `data/`
  - Markdown report and JSON decision trace writers
  - Placeholder custom Skill draft builder
- Added a base LLM adapter that defaults to the WSL-local `claude` CLI, reusing the existing Claude Code configuration instead of hardcoding secrets or endpoints.
- Added smoke tests for CLI help, recommendation output, Skill draft generation, and demo cases.
- Added an interactive CLI session: running `python main.py` now accepts natural language directly, with `/build`, `/demo`, `/help`, and `/exit` shortcuts.
- Verified `conda run -n skill_pilot python -m pytest` passes with 9 tests.
- Verified the skeleton commands can generate `outputs/recommendation_report.md`, `outputs/decision_trace.json`, and `generated_skills/homework-knowledge-hint/`.
- Implemented Stage 2.1 and 2.2:
  - Added unified `SearchQuery` and `SearchResult` models.
  - Added `WebSearchTool`, `GitHubSearchTool`, and an environment-gated `SearchExecutor`.
  - Added explicit proxy support through `SKILLPILOT_HTTP_PROXY` / `SKILLPILOT_HTTPS_PROXY`.
  - Upgraded `SourcePlanner` to generate 3 to 5 targeted web/GitHub queries for Skill, MCP, Plugin, mixed, and unknown needs.
  - Search plans and search execution statuses are now saved in `outputs/decision_trace.json`, shown in the recommendation report, and summarized in CLI output.
  - Verified proxied network search for `阅读pdf的插件`, finding real web results such as `ZSHYC/pdf-master`.
- Created feature branch `feature/stage2-reading-extraction` for Stage 2.3 and 2.4 work.
- Implemented Stage 2.3 and 2.4:
  - Added structured `RetrievedContent` records for page/repository reads.
  - Added `PageReader` for ordinary documentation pages.
  - Added `RepoReader` for GitHub repositories, using the GitHub API for repository metadata, README content, and common files such as `SKILL.md`, `.mcp.json`, `package.json`, and `pyproject.toml`.
  - Added `ContentReader` to route search results to the correct reader, deduplicate URLs, preserve skipped/failed reads, and avoid breaking the whole pipeline when one read fails.
  - Added an initial rule-based `CandidateExtractor` to convert retrieved content into the shared `Candidate` model.
  - Later removed the rule-based `CandidateExtractor` from the main pipeline. The current pipeline sends successful `RetrievedContent` directly to the LLM evaluator, which reads the candidate raw content and returns candidate fields plus capability, documentation, and safety scores in one step.
  - Updated the pipeline to prefer real search/read content, falling back to the local demo cache only for offline/skipped runs.
  - Updated CLI/report/trace output to include page and repository read status.
- Verified Stage 2.3/2.4 with `conda run -n skill_pilot python -m pytest`: 12 tests passed.
- Verified a proxied real-search run for `阅读pdf的插件`; it found and read `https://github.com/ZSHYC/pdf-master`, extracted it as a plugin candidate, and wrote evidence into `outputs/recommendation_report.md`.
- Changed network search to be enabled by default. Set `SKILLPILOT_ENABLE_NETWORK_SEARCH=0` only when an offline run is needed.
- Re-verified with `conda run -n skill_pilot python -m pytest`: 13 tests passed.
- Created feature branch `feature/stage2-evaluation-decision-demo` for Stage 2.5, 2.6, and 2.7 work.
- Implemented Stage 2.5, 2.6, and 2.7:
  - Added weighted candidate evaluation with explicit component scores:
    - capability match: 45%
    - type match: 15%
    - documentation quality: 20%
    - safety risk: 20%
  - Switched candidate capability, documentation, and safety scoring to LLM-assisted structured JSON evaluation.
  - Kept type matching as a deterministic rule score.
  - Added high-risk decision gating: high match candidates with write, command execution, or token/API-key risks are not directly recommended for installation.
  - Expanded the Chinese recommendation report with component scores, matched/missing capabilities, risk reasons, failed queries/URLs, and safety alternatives.
  - Adjusted cache fallback so local demo cache is used for offline/skipped runs, while real-search runs with insufficient evidence clearly enter the custom Skill path.
  - Added focused tests for weighted evaluation, high-risk decisions, no-candidate custom Skill fallback, and report failure handling.
- Verified Stage 2.5/2.6/2.7 with `conda run -n skill_pilot python -m pytest`: 17 tests passed.
- Verified a proxied real-search run for `阅读pdf的插件`; it found and read real GitHub results including `https://github.com/ZSHYC/pdf-master`, recorded failed/no-result queries, scored candidates, and chose the safer custom Skill path because the best candidates had high-risk permission or token signals.
- Fixed an evaluation false positive where guide or marketplace overview pages could be treated as installable plugin candidates.
  - Candidate capability, dependency, permission, and type extraction no longer uses the search query text as candidate evidence.
  - Ordinary web guide/list/overview pages such as "Claude Code 插件完全指南" are skipped as non-candidate pages.
  - Added a regression test for skipping plugin guide pages.
- Re-verified with `conda run -n skill_pilot python -m pytest`: 18 tests passed.
- Refined Stage 2.1/2.2 source planning after source research:
  - Added structured `SearchSource` records and a curated `SourceCatalog`.
  - Current high-priority Skill sources: `anthropic_skills_repo`, `anthropic_agent_skills_docs`, `anthropic_skills_cookbook`, `skillsmp_directory`.
  - Current high-priority MCP sources: `official_mcp_registry`, `glama_mcp`, `smithery_mcp`.
  - Current high-priority Plugin sources: `anthropic_official_plugin_marketplace`, `anthropic_community_plugin_marketplace`, `anthropic_demo_plugin_marketplace`, `ccplugins_awesome_marketplace`.
  - `SearchPlan.sources` now records source id, kind, trust level, entry URLs, data format, reader type, and searcher type.
  - `SearchQuery`, `SearchResult`, and `RetrievedContent` can preserve `source_id` for source-level traceability.
  - CLI and reports now show planned sources in addition to queries/results.
  - Added `docs/stage_2_3_source_access.md` to guide Stage 2.3 source-specific readers for docs, marketplace JSON, GitHub trees, and MCP registry APIs.
- Re-verified source catalog planning with `conda run -n skill_pilot python -m pytest`: 18 tests passed.
- Added SkillsMP as a community Skill directory/API source:
  - Source id: `skillsmp_directory`.
  - Web search page: `https://skillsmp.com/search?q={query}`.
  - API docs: `https://skillsmp.com/docs/api`.
  - OpenAPI spec: `https://skillsmp.com/openapi.json`.
  - API endpoint: `https://skillsmp.com/api/v1/skills/search`.
  - Anonymous API limits documented by SkillsMP: 50 requests/day and 10 requests/min.
  - Search hits are treated as provisional GitHub-backed Skill discoveries and must be verified by reading the returned GitHub source before recommendation.
- Disabled the old broad DuckDuckGo-style web search path. Search planning now uses curated `source` queries from `SourceCatalog`; unsupported source-specific readers/searchers are recorded as skipped instead of falling back to generic web search.
- Re-verified with `conda run -n skill_pilot python -m pytest`: 19 tests passed.
- Verified a proxied source-specific Skill run for `阅读pdf的skill`; `skillsmp_directory` returned GitHub-backed Skill results, the pipeline read 3 successful repositories, and the run produced `recommend_existing`.
- Replaced keyword-rule requirement capability extraction with LLM structured extraction:
  - `RequirementParser` now calls the configured LLM and expects strict JSON for `task_domain`, `desired_capabilities`, operational booleans, and `risk_tolerance`.
  - The parser no longer uses keyword rules such as `pdf -> pdf_reading`; capabilities come from LLM output.
  - If the LLM is unavailable or returns invalid JSON, parsing falls back to a generic safe requirement with `general_guidance`, not rule-derived capabilities.
  - `SkillPilotPipeline` now injects the shared LLM adapter into `RequirementParser`.
  - Added `static_json` LLM provider for offline CLI smoke tests and deterministic test runs.
- Re-verified LLM parser changes with `conda run -n skill_pilot python -m pytest`: 22 tests passed.
- Re-read `docs/stage_2_3_source_access.md` and synchronized the Stage 2.1/2.2 understanding:
  - Source planning is now based on curated source pools rather than broad web/GitHub search pools.
  - Search execution now groups queries by `source_id`, dispatches one lightweight `SourceSearchAgent` per source, runs source agents concurrently, and aggregates results back in planned source order.
  - Source-agent results preserve `source_id` and `search_agent` metadata for traceability.
- Re-verified with `conda run -n skill_pilot python -m pytest`: 20 tests passed.
- Removed the rule-based `CandidateExtractor` from the main implementation:
  - Successful `RetrievedContent` now goes directly into `CandidateEvaluator`.
  - The LLM reads the retrieved raw content and returns candidate fields plus capability, documentation, safety, risk, and reason fields in one structured response.
  - The CLI now prints only the top recommendation summary; the full search/read/evaluation detail remains in `outputs/recommendation_report.md`.
  - `ClaudeCliLLM` now sends prompts through stdin and only passes a budget argument when `SKILLPILOT_CLAUDE_MAX_BUDGET_USD` is explicitly set.
- Re-verified with `conda run -n skill_pilot python -m pytest`: 25 tests passed.
- Verified a proxied real run for `制作海报的skill`; LLM direct raw-content scoring selected `canvas-design` and produced `recommend_existing`.
- Re-read project documentation after source-planning changes and refined Stage 2.5 scoring:
  - Candidate scoring no longer includes a trust/maintenance component because discovery now uses fixed curated sources.
  - LLM structured evaluation now scores capability match, documentation quality, and safety risk.
  - Type match remains a deterministic rule score because it is a direct comparison between classified target type and candidate type.
  - New scoring weights: capability 45%, type 15%, documentation 20%, safety 20%.
  - `SKILLPILOT_ENABLE_LLM_EVALUATION=0` can disable LLM scoring for deterministic tests; normal runtime defaults to enabled.

## Current Stage 2.1 / 2.2 Runtime Output Format

When running a recommendation command, the CLI now prints the final decision plus the search-stage intermediate results:

```text
Decision: <decision_type>
Planned sources: <count>
  - <source_id> (<source_kind>, <trust_level>)
Search queries: <count>
  1. [source source=<source_id>] <query text>
Search results: <count>
  - [source|github/<source_id>/success|no_results|failed|skipped] <title or query>
    <url or error message>
Report: outputs/recommendation_report.md
Trace: outputs/decision_trace.json
Skill draft: generated_skills/<skill-name>
```

`outputs/recommendation_report.md` now includes:

- 用户需求理解
- 扩展类型判断
- 搜索计划
- 搜索结果
- 候选资源与评分
- 决策结果
- 安全提示

`outputs/decision_trace.json` now includes structured `search_plan.queries` and `search_results` entries. Each search result preserves title, URL, snippet, source type, original query, status, error message, and metadata when available.

Network search is enabled by default. It can be controlled by environment variables:

```bash
SKILLPILOT_ENABLE_NETWORK_SEARCH=0  # optional: disable network search for offline tests
SKILLPILOT_HTTP_PROXY=http://172.22.0.1:7890
SKILLPILOT_SEARCH_TIMEOUT_SECONDS=8
SKILLPILOT_SEARCH_MAX_RESULTS=3
```

Example tested command:

```bash
SKILLPILOT_HTTP_PROXY=http://172.22.0.1:7890 \
SKILLPILOT_SEARCH_TIMEOUT_SECONDS=8 \
SKILLPILOT_SEARCH_MAX_RESULTS=3 \
conda run -n skill_pilot python main.py recommend "阅读pdf的插件"
```

## Not Started

- Replace placeholder requirement parsing with LLM-assisted structured extraction.
- Replace keyword-based Skill / Plugin / MCP classification with a stronger rule + LLM hybrid classifier.
- Further improve LLM scoring prompts and output validation for capability, documentation, and safety evaluation.
- Further improve risk analysis by separating read-only local file access from write, token, command execution, and network risks more precisely.
- Add broader tests beyond smoke coverage.
- Prepare demo cases, recorded real-search runs, and stable screenshots/video for classroom presentation.
- Prepare classroom PPT.
- Prepare final Chinese written report PDF.

## Proposed Next Steps

1. Run smoke tests and demo commands after skeleton changes.
2. Replace stubs one module at a time, starting with requirement parsing and extension type classification.
3. Implement real network search as the main second-stage path.
4. Record successful real-search demo runs for classroom presentation, including terminal output, reports, and screenshots.
5. Keep local demo data only as development fixtures or test inputs, not as the product's primary candidate source.

## Detailed Stage 2 Plan: Real Search MVP

Stage 2 should be split into small, testable steps. The goal is to replace the skeleton's placeholder candidate path with real web and GitHub discovery while preserving explainability and safety.

### 2.1 Search Interface Layer

- Define unified `SearchQuery` and `SearchResult` models.
- Implement a `WebSearchTool` for real web search results.
- Implement a `GitHubSearchTool` for repository search and metadata lookup.
- Preserve title, URL, snippet, source type, query string, and retrieval status for every result.
- Add timeout and error handling so failed searches are visible in the decision trace.

### 2.2 Search Planning

- Implement `SourcePlanner` so it expands a user requirement into 3 to 5 targeted search queries.
- Generate different query patterns for Skill, MCP, Plugin, and mixed needs.
- Include Claude-specific terms such as `Claude Skill`, `SKILL.md`, `Claude Code plugin`, `MCP server`, `GitHub`, and task-specific capability keywords.
- Store the generated query plan in `outputs/decision_trace.json`.

### 2.3 Page and Repository Reading

- Implement `PageReader` for ordinary documentation pages.
- Implement `RepoReader` for GitHub repositories, prioritizing README, description, license, stars, last update, and common config files.
- Prefer structured GitHub API responses where possible, and fall back to raw README content when needed.
- Record failed reads without dropping the whole pipeline.

### 2.4 Candidate Understanding

- Do not use a separate rule-based `CandidateExtractor` as the main path.
- Send successful retrieved content, especially `SKILL.md` and README text, directly to the LLM evaluator.
- Let the LLM return both candidate fields and scoring fields in one structured JSON response.
- Keep local fallback scoring only for offline tests or LLM failures.

### 2.5 Evaluation and Ranking

- Use LLM-assisted structured evaluation for candidate quality and safety.
- Keep type matching as a deterministic score.
- Use a weighted score for the MVP:
  - capability match: 45%
  - type match: 15%
  - documentation quality: 20%
  - safety risk: 20%
- Rank candidates and keep both numeric scores and natural-language reasons.

### 2.6 Decision and Report Generation

- Implement `DecisionGate` rules:
  - high match and low/medium risk -> recommend existing resource
  - medium match -> recommend existing resource plus custom Skill supplement
  - low match -> build custom Skill draft
  - high risk -> avoid direct installation recommendation and provide safer alternatives
- Generate a Chinese recommendation report with search queries, candidate evidence, scores, missing capabilities, risks, and final decision.
- Save a complete `decision_trace.json` for reproducibility.

### 2.7 Failure Handling and Demo Recording

- If search or reading fails, report the exact failed query or URL and continue with remaining results.
- If no sufficient candidate is found, clearly explain that real search did not find enough evidence and then enter the custom Skill path.
- Do not fabricate search results for classroom presentation.
- Prepare classroom demos by recording successful real-search runs in advance, including terminal commands, generated reports, and final artifacts.

## Environment Notes

Activate the environment from WSL:

```bash
conda activate skill_pilot
cd /home/achewwa/Projects/SkillPilot
```

Claude Code minimal verification command:

```bash
claude -p --tools '' --no-session-persistence --max-budget-usd 0.05 'Please only output OK'
```

Expected result:

```text
OK
```

## Source Documents

- `info.pdf`: course requirements.
- `project_draft.md`: original project draft, used as reference only. It can be modified or reduced as implementation proceeds.
