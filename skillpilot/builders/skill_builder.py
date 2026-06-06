from __future__ import annotations

from pathlib import Path

from skillpilot.builders.resource_generator import ResourceGenerator
from skillpilot.builders.skill_md_writer import SkillMdWriter
from skillpilot.builders.skill_structure_planner import SkillStructurePlanner
from skillpilot.models import BuilderSession, SafetyReviewResult, SkillDraftResult, SkillSpec


class SkillBuilder:
    def __init__(self, generated_skills_dir: Path) -> None:
        self.generated_skills_dir = generated_skills_dir
        self.structure_planner = SkillStructurePlanner()
        self.skill_md_writer = SkillMdWriter()
        self.resource_generator = ResourceGenerator()

    def build_from_spec(
        self,
        spec: SkillSpec,
        safety_review: SafetyReviewResult,
        session: BuilderSession,
    ) -> SkillDraftResult:
        skill_dir = self.generated_skills_dir / spec.slug
        skill_dir.mkdir(parents=True, exist_ok=True)

        files: dict[Path, str] = {}
        for file_spec in self.structure_planner.plan_files(spec):
            path = skill_dir / file_spec.path
            if file_spec.path == "SKILL.md":
                files[path] = self.skill_md_writer.render(spec)
            else:
                files[path] = self.resource_generator.render(file_spec, spec)

        for path, content in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

        return SkillDraftResult(
            name=spec.slug,
            path=str(skill_dir),
            files=[str(path) for path in files],
            spec_summary=spec.description,
            safety_review=safety_review,
            builder_session=session,
        )

    def write_safety_advice(
        self,
        spec: SkillSpec,
        safety_review: SafetyReviewResult,
        session: BuilderSession,
    ) -> SkillDraftResult:
        skill_dir = self.generated_skills_dir / spec.slug
        skill_dir.mkdir(parents=True, exist_ok=True)
        advice_path = skill_dir / "SAFE_DESIGN.md"
        lines = [
            f"# {spec.name} Safety Review",
            "",
            "SkillPilot did not generate an executable Skill draft because the request crossed a safety boundary.",
            "",
            "## Risk Reasons",
            "",
        ]
        lines.extend(f"- {reason}" for reason in safety_review.risk_reasons)
        lines.extend(["", "## Safer Alternatives", ""])
        lines.extend(f"- {item}" for item in safety_review.safe_alternatives)
        advice_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

        return SkillDraftResult(
            name=spec.slug,
            path=str(skill_dir),
            files=[str(advice_path)],
            spec_summary=spec.description,
            safety_review=safety_review,
            builder_session=session,
            warnings=["Safety review blocked full Skill generation."],
        )

    def build_homework_hint_skill(self) -> SkillDraftResult:
        skill_name = "homework-knowledge-hint"
        skill_dir = self.generated_skills_dir / skill_name
        resources_dir = skill_dir / "resources"
        examples_dir = skill_dir / "examples"
        resources_dir.mkdir(parents=True, exist_ok=True)
        examples_dir.mkdir(parents=True, exist_ok=True)

        files = {
            skill_dir / "SKILL.md": self._skill_md(),
            resources_dir / "hint_policy.md": self._hint_policy(),
            resources_dir / "output_template.md": self._output_template(),
            examples_dir / "sample_output.md": self._sample_output(),
        }
        for path, content in files.items():
            path.write_text(content, encoding="utf-8")

        return SkillDraftResult(
            name=skill_name,
            path=str(skill_dir),
            files=[str(path) for path in files],
        )

    def _skill_md(self) -> str:
        return """# Homework Knowledge Hint

## Description

占位 Skill 草案：根据课程资料为书面作业题提供知识点提示，但不直接给出答案。

## When To Use

- 用户希望理解题目涉及的知识点。
- 用户需要解题方向、概念提醒或阅读建议。
- 用户明确要求不要直接输出完整答案。

## Workflow

1. 识别题目主题和课程知识点。
2. 给出相关概念、公式或阅读范围。
3. 提供分步骤思考提示。
4. 检查输出中是否包含直接答案，并在必要时改写为提示。

## Constraints

- 不直接给最终答案。
- 不替用户完成完整作业。
- 不编造课程资料中不存在的要求。

## Output Format

参考 `resources/output_template.md`。
"""

    def _hint_policy(self) -> str:
        return """# Hint Policy

- 优先提示知识点和思考路径。
- 可以给出例子，但例子不应等同于题目答案。
- 如果用户要求直接答案，应提醒学习边界并改为提示。
"""

    def _output_template(self) -> str:
        return """# Output Template

## 题目理解

## 相关知识点

## 思考步骤提示

## 需要回看课程资料的位置

## 不直接给答案的说明
"""

    def _sample_output(self) -> str:
        return """# Sample Output

## 题目理解

这道题看起来考查某个概念与实际场景之间的关系。

## 相关知识点

- 核心概念 A
- 判断条件 B

## 思考步骤提示

1. 先确认题目给出的条件。
2. 再判断这些条件对应课程中的哪条规则。
3. 最后用自己的话组织答案。
"""
