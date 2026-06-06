# Pipeline-Agent-Skill Mapping

This document maps the current SkillPilot implementation to the refactored
pipeline-agent-skill structure. It is intended as a behavior-preservation
checklist: every existing workflow step remains represented after the
refactor.

## Pipeline

| Current code | Refactored role | Notes |
| --- | --- | --- |
| `skillpilot.pipeline.SkillPilotPipeline.run` | `SkillPilotPipeline` orchestration loop | Keeps the single public run entrypoint, but delegates each stage to role agents. |
| `skillpilot.agent.SkillPilotAgent.recommend` | User-facing facade | Continues to call the pipeline for recommendation runs. |
| `skillpilot.agent.SkillPilotAgent.build_skill` | User-facing facade | Continues to call the pipeline with `force_build_skill=True`. |

## Agents and Skills

| Agent path | Skills path | Existing implementation mapped |
| --- | --- | --- |
| `skillpilot.agents.requirement.RequirementAnalysisAgent` | `skillpilot.skills.requirement.RequirementParser`, `skillpilot.skills.classification.ExtensionTypeClassifier`, `skillpilot.skills.planning.SourcePlanner` | `RequirementParser.parse`, `ExtensionTypeClassifier.classify`, `SourcePlanner.plan` |
| `skillpilot.agents.discovery.SourceDiscoveryAgent` | `skillpilot.skills.discovery.search_tools`, `skillpilot.skills.discovery.readers` | `SearchExecutor.run`, `SourceSearchAgent.search`, `ContentReader.read` |
| `skillpilot.agents.evaluation.CandidateEvaluationAgent` | `skillpilot.skills.evaluation.CandidateEvaluator`, `skillpilot.skills.cache.LocalCandidateCache` | `CandidateEvaluator.evaluate_retrieved`, `CandidateEvaluator.evaluate`, `CandidateEvaluator._fallback_score` |
| `skillpilot.agents.decision.DecisionAgent` | `skillpilot.skills.decision.DecisionGate` | `DecisionGate.decide`, `DecisionGate.build_custom` |
| `skillpilot.agents.builder.SkillBuilderAgent` | `skillpilot.skills.builder.*` | `QuestionPlanner`, `SkillSpecGenerator`, `ResourceGenerator`, `SafetyReviewer`, `SkillBuilder` |
| `skillpilot.agents.report.ReportAgent` | `skillpilot.skills.report.RecommendationWriter` | `RecommendationWriter.write_report`, `RecommendationWriter.write_trace` |

## Removed Legacy Paths

The old `skillpilot.builders`, `skillpilot.modules`, and `skillpilot.io.report_writer`
shim paths have been removed after the physical migration. Production code and
tests now import directly from `skillpilot.agents.*` and `skillpilot.skills.*`.

## Guardrails Kept Deterministic

- URL parsing, GitHub repository path parsing, read limits, and duplicate URL handling remain deterministic I/O skills.
- Score clamping, enum validation, type-score calculation, and weighted score aggregation remain deterministic guardrails.
- Installation, command execution, and third-party script execution are still not performed by the system.
- Rule fallbacks remain available for offline tests and LLM failures, but primary semantic choices can be made through LLM-backed skills.
