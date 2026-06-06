from __future__ import annotations

from skillpilot.models import SkillResourceSpec, SkillSpec
from skillpilot.utils import dedupe_preserve_order


class SkillStructurePlanner:
    def plan_files(self, spec: SkillSpec) -> list[SkillResourceSpec]:
        files = [
            SkillResourceSpec(
                path="SKILL.md",
                purpose="Main Claude Skill manifest and workflow.",
                content_hint=spec.description,
            )
        ]
        files.extend(self._dedupe_specs(spec.resources))
        files.extend(self._dedupe_specs(spec.examples))
        files.append(
            SkillResourceSpec(
                path="README.md",
                purpose="Packaging and local review notes for the generated draft.",
                content_hint="Explain generated files and manual review steps.",
            )
        )
        if spec.requires_scripts:
            files.append(
                SkillResourceSpec(
                    path="scripts/README.md",
                    purpose="Placeholder guidance for scripts that require manual review.",
                    content_hint="Do not run generated scripts without human review.",
                )
            )
        return files

    def _dedupe_specs(self, specs: list[SkillResourceSpec]) -> list[SkillResourceSpec]:
        return dedupe_preserve_order(specs, key=lambda spec: spec.path)
