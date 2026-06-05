from __future__ import annotations

import json
from pathlib import Path

from skillpilot.models import AgentRunResult, Decision, model_to_dict


class RecommendationWriter:
    def __init__(self, outputs_dir: Path) -> None:
        self.outputs_dir = outputs_dir

    def write_report(
        self,
        requirement_text: str,
        classification_reason: str,
        decision: Decision,
        report_path: Path | None = None,
    ) -> Path:
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        path = report_path or self.outputs_dir / "recommendation_report.md"
        lines = [
            "# SkillPilot 推荐报告",
            "",
            "## 用户需求理解",
            "",
            requirement_text,
            "",
            "## 扩展类型判断",
            "",
            classification_reason,
            "",
            "## 候选资源与评分",
            "",
        ]

        if decision.selected_candidates:
            for index, evaluation in enumerate(decision.selected_candidates, start=1):
                candidate = evaluation.candidate
                lines.extend(
                    [
                        f"{index}. {candidate.name}",
                        f"   - 类型：{candidate.extension_type}",
                        f"   - 匹配度：{evaluation.match_score}",
                        f"   - 风险等级：{evaluation.risk_level}",
                        f"   - 说明：{evaluation.reason}",
                        f"   - 来源：{candidate.source_url}",
                    ]
                )
        else:
            lines.append("暂无足够匹配的候选资源。")

        lines.extend(
            [
                "",
                "## 决策结果",
                "",
                f"- 决策：{decision.decision_type}",
                f"- 原因：{decision.reason}",
                "",
                "## 安全提示",
                "",
                "本报告由占位骨架生成，不会自动安装、运行或授权第三方扩展。后续实现应继续保留人工确认和风险提示。",
                "",
            ]
        )
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def write_trace(self, result: AgentRunResult, trace_path: Path | None = None) -> Path:
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        path = trace_path or self.outputs_dir / "decision_trace.json"
        path.write_text(
            json.dumps(model_to_dict(result), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path
