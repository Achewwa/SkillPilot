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
- Use cached candidate data for stable classroom demos; live search can be an optional enhancement.
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
- Implement real candidate search and reading.
- Implement robust candidate extraction from README / SKILL.md / docs.
- Implement production-quality capability matching and scoring.
- Implement richer trust evaluation.
- Implement richer risk analysis.
- Add broader tests beyond smoke coverage.
- Prepare demo cases and stable demo outputs.
- Prepare classroom PPT.
- Prepare final Chinese written report PDF.

## Proposed Next Steps

1. Run smoke tests and demo commands after skeleton changes.
2. Expand local candidate cache so classroom demos have richer evidence.
3. Replace stubs one module at a time, starting with requirement parsing and extension type classification.
4. Implement candidate extraction from cached README / SKILL.md text before adding live search.
5. Keep live GitHub or web search optional until the offline demo path is stable.

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
