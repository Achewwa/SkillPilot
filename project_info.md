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
- Verified `conda run -n skill_pilot python -m pytest` passes with 5 tests.
- Verified the skeleton commands can generate `outputs/recommendation_report.md`, `outputs/decision_trace.json`, and `generated_skills/homework-knowledge-hint/`.

## Not Started

- Replace placeholder requirement parsing with LLM-assisted structured extraction.
- Replace keyword-based Skill / Plugin / MCP classification with a stronger rule + LLM hybrid classifier.
- Implement real web and GitHub candidate search.
- Implement robust candidate extraction from README / SKILL.md / docs.
- Implement production-quality capability matching and scoring.
- Implement richer trust evaluation.
- Implement richer risk analysis.
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

### 2.4 Candidate Extraction

- Implement `CandidateExtractor` to convert search results and retrieved content into the shared `Candidate` model.
- Extract name, extension type, description, capabilities, installation notes, dependencies, permissions, maintainer signals, and evidence quotes.
- Detect evidence from README / `SKILL.md` / docs instead of relying only on search snippets.
- Keep extraction conservative: unknown fields should stay unknown rather than being guessed.

### 2.5 Evaluation and Ranking

- Upgrade `CapabilityMatcher`, `TrustEvaluator`, and `RiskAnalyzer`.
- Use a simple weighted score for the MVP:
  - capability match: 40%
  - type match: 15%
  - documentation quality: 15%
  - maintenance / trust signals: 15%
  - safety risk: 15%
- Rank candidates and keep both numeric scores and natural-language reasons.

### 2.6 Decision and Report Generation

- Implement `DecisionGate` rules:
  - high match and low/medium risk -> recommend existing resource
  - medium match -> recommend existing resource plus custom Skill supplement
  - low match -> build custom Skill draft
  - high risk -> avoid direct installation recommendation and provide safer alternatives
- Generate a Chinese recommendation report with search queries, candidate evidence, scores, missing capabilities, trust signals, risks, and final decision.
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
