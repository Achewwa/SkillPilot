from __future__ import annotations

from pathlib import Path

from skillpilot.agents.core import PipelineContext
from skillpilot.skills.report import RecommendationWriter


class ReportAgent:
    def __init__(self, writer: RecommendationWriter, outputs_dir: Path) -> None:
        self.writer = writer
        self.outputs_dir = outputs_dir

    def write_report(self, context: PipelineContext) -> None:
        report_path = self.outputs_dir / "recommendation_report.md"
        trace_path = self.outputs_dir / "decision_trace.json"
        decision = context.require_decision()
        requirement = context.require_requirement()
        classification = context.require_classification()
        self.writer.write_report(
            requirement_text=requirement.raw_text,
            classification_reason=classification.reason,
            decision=decision,
            requirement=requirement,
            search_plan=context.search_plan,
            search_results=context.search_results,
            retrieved_contents=context.retrieved_contents,
            skill_draft=context.skill_draft,
            report_path=report_path,
        )
        context.report_path = report_path
        context.trace_path = trace_path
        context.record(
            "ReportAgent",
            "ReportWriterSkill",
            summary=f"Wrote report to `{report_path}`.",
        )

    def write_trace(self, context: PipelineContext, result) -> None:
        trace_path = context.trace_path or self.outputs_dir / "decision_trace.json"
        self.writer.write_trace(result, trace_path=Path(trace_path))
        context.record(
            "ReportAgent",
            "TraceWriterSkill",
            summary=f"Wrote trace to `{trace_path}`.",
        )
