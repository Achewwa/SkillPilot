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
- Read the course requirement PDF: `课程项目.pdf`.
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
- Created this `projects_info.md` file for cross-window synchronization.

## Not Started

- Initialize the Python project structure.
- Implement CLI entrypoint.
- Define core data models and schemas.
- Build the agent state and orchestration loop.
- Implement requirement parsing.
- Implement Skill / Plugin / MCP classification.
- Prepare local candidate cache.
- Implement candidate search and reading.
- Implement candidate extraction.
- Implement capability matching and scoring.
- Implement trust evaluation.
- Implement risk analysis.
- Implement decision gate.
- Implement recommendation report generation.
- Implement custom Skill generation.
- Add tests.
- Prepare demo cases and stable demo outputs.
- Prepare classroom PPT.
- Prepare final Chinese written report PDF.

## Proposed Next Steps

1. Initialize git and connect the repository to `Achewwa/SkillPilot`.
2. Create the Python project skeleton.
3. Add `requirements.txt` or `pyproject.toml`.
4. Implement core models first, because every later module depends on them.
5. Build a small offline candidate cache before implementing live search.
6. Implement the three demo cases early so the project remains demonstrable throughout development.

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

- `课程项目.pdf`: course requirements.
- `project_draft.md`: original project draft, used as reference only. It can be modified or reduced as implementation proceeds.
