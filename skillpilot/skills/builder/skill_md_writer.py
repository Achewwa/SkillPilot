from __future__ import annotations

from skillpilot.models import SkillSpec


class SkillMdWriter:
    def render(self, spec: SkillSpec) -> str:
        lines = [
            f"# {spec.name}",
            "",
            "## Description",
            "",
            spec.description,
            "",
            "## When To Use",
            "",
        ]
        lines.extend(f"- {item}" for item in spec.when_to_use)
        lines.extend(["", "## Workflow", ""])
        lines.extend(f"{index}. {step}" for index, step in enumerate(spec.workflow, start=1))
        lines.extend(["", "## Constraints", ""])
        lines.extend(f"- {item}" for item in spec.constraints)
        lines.extend(["", "## Output Format", "", spec.output_format])
        if spec.resources:
            lines.extend(["", "## Resources", ""])
            lines.extend(f"- `{item.path}`: {item.purpose}" for item in spec.resources)
        if spec.examples:
            lines.extend(["", "## Examples", ""])
            lines.extend(f"- `{item.path}`: {item.purpose}" for item in spec.examples)
        if spec.script_notes:
            lines.extend(["", "## Script Notes", ""])
            lines.extend(f"- {item}" for item in spec.script_notes)
        return "\n".join(lines).rstrip() + "\n"
