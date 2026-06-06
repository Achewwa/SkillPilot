from __future__ import annotations

from pathlib import Path

from skillpilot.models import BuilderSession, SafetyReviewResult, SkillDraftResult, SkillSpec
from skillpilot.skills.builder.resource_generator import ResourceGenerator
from skillpilot.skills.builder.skill_md_writer import SkillMdWriter
from skillpilot.skills.builder.skill_structure_planner import SkillStructurePlanner
from skillpilot.skills.core import LLMProvider


class SkillBuilder:
    def __init__(
        self,
        generated_skills_dir: Path,
        llm: LLMProvider | None = None,
    ) -> None:
        self.generated_skills_dir = generated_skills_dir
        self.structure_planner = SkillStructurePlanner()
        self.skill_md_writer = SkillMdWriter()
        self.resource_generator = ResourceGenerator(llm)

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
