from __future__ import annotations

import json
from pathlib import Path

from skillpilot.models import (
    AgentRunResult,
    Decision,
    ParsedRequirement,
    RetrievedContent,
    SearchPlan,
    SearchResult,
    model_to_dict,
)


class RecommendationWriter:
    def __init__(self, outputs_dir: Path) -> None:
        self.outputs_dir = outputs_dir

    def write_report(
        self,
        requirement_text: str,
        classification_reason: str,
        decision: Decision,
        requirement: ParsedRequirement | None = None,
        search_plan: SearchPlan | None = None,
        search_results: list[SearchResult] | None = None,
        retrieved_contents: list[RetrievedContent] | None = None,
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
            "## 搜索计划",
            "",
        ]

        if search_plan:
            lines.append(f"- 目标类型：{search_plan.extension_type}")
            if requirement:
                capabilities = self._join_or_none(requirement.desired_capabilities)
                lines.append(f"- 需求领域：{requirement.task_domain}")
                lines.append(f"- 需求能力：{capabilities}")
            if search_plan.sources:
                lines.append("- 搜索源：")
                for source in search_plan.sources:
                    lines.append(
                        "  - "
                        f"{source.source_id}：{source.name} "
                        f"({source.source_kind}, {source.trust_level})"
                    )
                    target_url = source.api_url or source.index_url or source.base_url
                    lines.append(f"    - 入口：{target_url}")
                    lines.append(
                        f"    - 读取方式：{source.reader_type}；搜索方式：{source.searcher_type}"
                    )
            else:
                lines.append("- 搜索源：暂无")
            for index, query in enumerate(search_plan.queries, start=1):
                source_label = f"，源：{query.source_id}" if query.source_id else ""
                lines.append(
                    f"{index}. [{query.source_type}] {query.text}（目的：{query.purpose}{source_label}）"
                )
        else:
            lines.append("暂无搜索计划。")

        lines.extend(
            [
                "",
                "## 搜索结果",
                "",
            ]
        )

        if search_results:
            for index, result in enumerate(search_results, start=1):
                status_detail = result.error_message or result.snippet or "无额外说明"
                title = result.title or result.query
                source_label = f"/{result.source_id}" if result.source_id else ""
                lines.append(f"{index}. [{result.source_type}{source_label}/{result.status}] {title}")
                if result.url:
                    lines.append(f"   - URL：{result.url}")
                lines.append(f"   - 查询：{result.query}")
                lines.append(f"   - 说明：{status_detail}")
        else:
            lines.append("暂无搜索结果。")

        lines.extend(
            [
                "",
                "## 页面与仓库读取",
                "",
            ]
        )

        if retrieved_contents:
            for index, content in enumerate(retrieved_contents, start=1):
                title = content.title or content.url or content.query
                detail = content.error_message or content.metadata.get("description") or "读取成功。"
                lines.append(f"{index}. [{content.source_type}/{content.status}] {title}")
                if content.url:
                    lines.append(f"   - URL：{content.url}")
                lines.append(f"   - 说明：{detail}")
        else:
            lines.append("暂无页面或仓库读取结果。")

        failure_lines = self._failure_lines(search_results or [], retrieved_contents or [])
        lines.extend(
            [
                "",
                "## 失败处理",
                "",
            ]
        )
        if failure_lines:
            lines.extend(failure_lines)
        else:
            lines.append("本次搜索和读取阶段未记录失败项。")

        lines.extend(
            [
                "",
                "## 候选资源与评分",
                "",
            ]
        )

        if decision.selected_candidates:
            for index, evaluation in enumerate(decision.selected_candidates, start=1):
                candidate = evaluation.candidate
                lines.extend(
                    [
                        f"{index}. {candidate.name}",
                        f"   - 类型：{candidate.extension_type}",
                        f"   - 描述：{candidate.description}",
                        f"   - 总分：{evaluation.match_score}",
                        (
                            "   - 分项："
                            f"能力 {evaluation.capability_score}，"
                            f"类型 {evaluation.type_score}，"
                            f"文档 {evaluation.documentation_score}，"
                            f"安全 {evaluation.safety_score}"
                        ),
                        f"   - 匹配能力：{self._join_or_none(evaluation.matched_capabilities)}",
                        f"   - 缺失能力：{self._join_or_none(evaluation.missing_capabilities)}",
                        f"   - 风险等级：{evaluation.risk_level}",
                        f"   - 说明：{evaluation.reason}",
                        f"   - 来源：{candidate.source_url}",
                    ]
                )
                if candidate.installation:
                    lines.append(f"   - 安装线索：{candidate.installation}")
                if evaluation.risk_reasons:
                    lines.append("   - 风险原因：")
                    for reason in evaluation.risk_reasons[:4]:
                        lines.append(f"     - {reason}")
                if candidate.evidence:
                    lines.append("   - 证据：")
                    for evidence in candidate.evidence[:3]:
                        lines.append(f"     - {evidence}")
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
                "## 使用建议与安全替代",
                "",
                self._usage_advice(decision),
                "",
                "## 安全提示",
                "",
                "SkillPilot 不会自动安装、运行或授权第三方扩展。涉及命令执行、写入、token、数据库或远程写操作的候选，必须先人工审查。",
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

    def _failure_lines(
        self,
        search_results: list[SearchResult],
        retrieved_contents: list[RetrievedContent],
    ) -> list[str]:
        lines: list[str] = []
        for result in search_results:
            if result.status == "success":
                continue
            detail = result.error_message or result.snippet or "未返回可用结果。"
            source_label = f"/{result.source_id}" if result.source_id else ""
            lines.append(
                f"- 搜索未完成：[{result.source_type}{source_label}/{result.status}] 查询 `{result.query}`；原因：{detail}"
            )
        for content in retrieved_contents:
            if content.status == "success":
                continue
            target = content.url or content.query
            detail = content.error_message or "未读取到足够内容。"
            source_label = f"/{content.source_id}" if content.source_id else ""
            lines.append(
                f"- 读取未完成：[{content.source_type}{source_label}/{content.status}] `{target}`；原因：{detail}"
            )
        return lines

    def _usage_advice(self, decision: Decision) -> str:
        if decision.decision_type == "recommend_existing":
            return "可优先人工审查排名靠前的候选文档与安装步骤，确认权限范围后再手动启用。"
        if decision.decision_type == "recommend_with_custom_extension":
            return "建议把现有候选作为参考资料，同时使用生成的自定义 Skill 补齐缺失能力。"
        if decision.selected_candidates:
            return "不建议直接安装高风险候选；可先采用自定义 Skill 草案，并把候选资源留作人工审查材料。"
        return "未找到足够证据支撑现成推荐时，应明确说明搜索不足，并优先生成可控的自定义 Skill 草案。"

    def _join_or_none(self, values: list[str]) -> str:
        return "、".join(values) if values else "无"
