from __future__ import annotations

from skillpilot.models import SafetyReviewResult, SkillSpec


class PackagingAdvisor:
    def notes(self, spec: SkillSpec, safety_review: SafetyReviewResult) -> list[str]:
        notes = [
            "Review `SKILL.md` before installing or sharing the generated draft.",
            "Keep examples generic until you have verified them against real course or project material.",
        ]
        if safety_review.risk_level != "low":
            notes.append("Because the safety review is not low risk, test this Skill in a limited scope first.")
        if spec.requires_scripts:
            notes.append("Do not run or distribute scripts until they pass manual security review.")
        return notes
