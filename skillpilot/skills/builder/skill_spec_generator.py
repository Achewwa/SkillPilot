from __future__ import annotations

import json
import re
from typing import Any

from skillpilot.models import (
    BuilderSession,
    CandidateEvaluation,
    Decision,
    ParsedRequirement,
    SkillResourceSpec,
    SkillSpec,
    TypeClassification,
)
from skillpilot.skills.core import LLMProvider
from skillpilot.utils import extract_json_object


class SkillSpecGenerator:
    def __init__(self, llm: LLMProvider | None = None) -> None:
        self.llm = llm

    def generate(
        self,
        requirement: ParsedRequirement,
        classification: TypeClassification,
        decision: Decision,
        evaluations: list[CandidateEvaluation],
        session: BuilderSession,
    ) -> SkillSpec:
        if self.llm is not None:
            spec = self._generate_with_llm(
                requirement,
                classification,
                decision,
                evaluations,
                session,
            )
            if spec is not None:
                return spec
        return self._fallback_spec(requirement, decision, evaluations, session)

    def _generate_with_llm(
        self,
        requirement: ParsedRequirement,
        classification: TypeClassification,
        decision: Decision,
        evaluations: list[CandidateEvaluation],
        session: BuilderSession,
    ) -> SkillSpec | None:
        prompt = (
            "你是 SkillPilot 的 SkillSpecGenerator。请根据用户需求、澄清问答和候选缺口，"
            "生成一个安全、可执行、边界清楚的 Claude Skill 规格。返回严格 JSON，不要 Markdown。"
            "字段：name, slug, description, when_to_use, workflow, constraints, output_format, "
            "resources, examples, requires_scripts, script_notes, packaging_notes。"
            "resources/examples 每项包含 path, purpose, content_hint。slug 必须是小写英文短横线格式。\n"
            f"需求：{requirement.model_dump()}\n"
            f"类型判断：{classification.model_dump()}\n"
            f"决策：{decision.model_dump()}\n"
            f"候选缺口：{[item.missing_capabilities for item in evaluations[:3]]}\n"
            f"澄清会话：{session.model_dump()}"
        )
        try:
            response = self.llm.generate(prompt)
            payload = json.loads(_extract_json(getattr(response, "text", str(response))))
            return self._normalize_spec(payload, requirement)
        except Exception:  # noqa: BLE001 - builder must stay usable without LLM JSON.
            return None

    def _normalize_spec(self, payload: dict[str, Any], requirement: ParsedRequirement) -> SkillSpec:
        name = str(payload.get("name") or self._fallback_name(requirement)).strip()
        slug = _slugify(str(payload.get("slug") or name)) or self._fallback_slug(requirement)
        resources = self._resource_specs(payload.get("resources"))
        examples = self._resource_specs(payload.get("examples"))
        if not resources:
            resources = self._default_resources(requirement)
        if not examples:
            examples = self._default_examples(requirement)
        return SkillSpec(
            name=name,
            slug=slug,
            description=str(payload.get("description") or self._fallback_description(requirement)).strip(),
            when_to_use=_string_list(payload.get("when_to_use"))
            or self._default_when_to_use(requirement),
            workflow=_string_list(payload.get("workflow")) or self._default_workflow(requirement),
            constraints=_string_list(payload.get("constraints"))
            or self._default_constraints(requirement),
            output_format=str(payload.get("output_format") or self._default_output_format()).strip(),
            resources=resources,
            examples=examples,
            requires_scripts=bool(payload.get("requires_scripts", False)),
            script_notes=_string_list(payload.get("script_notes")),
            packaging_notes=_string_list(payload.get("packaging_notes")),
        )

    def _fallback_spec(
        self,
        requirement: ParsedRequirement,
        decision: Decision,
        evaluations: list[CandidateEvaluation],
        session: BuilderSession,
    ) -> SkillSpec:
        answers = _merged_answers(session)
        missing = _missing_capabilities(evaluations)
        name = self._fallback_name(requirement)
        if decision.decision_type == "recommend_with_custom_extension":
            name = f"{name} Supplement"
        return SkillSpec(
            name=name,
            slug=self._fallback_slug(requirement, decision),
            description=self._fallback_description(requirement, answers, missing),
            when_to_use=self._default_when_to_use(requirement, answers),
            workflow=self._default_workflow(requirement, answers, missing),
            constraints=self._default_constraints(requirement, answers),
            output_format=answers.get("output_format") or self._default_output_format(),
            resources=self._default_resources(requirement),
            examples=self._default_examples(requirement),
            requires_scripts=False,
            packaging_notes=[
                "Place this directory under a Claude-compatible skills directory before use.",
                "Review SKILL.md and resources before sharing it with others.",
            ],
        )

    def _fallback_name(self, requirement: ParsedRequirement) -> str:
        text = requirement.raw_text.lower()
        if "作业" in requirement.raw_text or "课件" in requirement.raw_text:
            return "Homework Knowledge Hint"
        if "海报" in requirement.raw_text or "poster" in text:
            return "Poster Design Coach"
        if "论文" in requirement.raw_text or "引用" in requirement.raw_text:
            return "Academic Writing Review"
        if "test" in text or "测试" in requirement.raw_text:
            return "Unit Test Guidance"
        domain = requirement.task_domain.replace("_", " ").title()
        return f"{domain} Skill" if domain != "General" else "Custom Guidance Skill"

    def _fallback_slug(
        self,
        requirement: ParsedRequirement,
        decision: Decision | None = None,
    ) -> str:
        base = self._fallback_name(requirement)
        if decision and decision.decision_type == "recommend_with_custom_extension":
            base = f"{base} Supplement"
        slug = _slugify(base)
        if slug:
            return slug
        capability = requirement.desired_capabilities[0] if requirement.desired_capabilities else "custom"
        return _slugify(f"{capability} skill") or "custom-guidance-skill"

    def _fallback_description(
        self,
        requirement: ParsedRequirement,
        answers: dict[str, str] | None = None,
        missing: list[str] | None = None,
    ) -> str:
        answers = answers or {}
        missing = missing or []
        parts = [
            f"Use this skill to help Claude handle: {requirement.raw_text}",
            "It turns the user's vague need into a structured workflow, safe boundaries, and reusable output templates.",
        ]
        if missing:
            parts.append(f"It especially covers missing capabilities: {', '.join(missing[:5])}.")
        if answers.get("use_case"):
            parts.append(f"Primary usage context: {answers['use_case']}")
        return " ".join(parts)

    def _default_when_to_use(
        self,
        requirement: ParsedRequirement,
        answers: dict[str, str] | None = None,
    ) -> list[str]:
        answers = answers or {}
        items = [
            "The user asks for a repeatable workflow rather than a one-off answer.",
            "The task benefits from clear constraints, examples, or output templates.",
        ]
        if answers.get("use_case"):
            items.insert(0, answers["use_case"])
        else:
            items.insert(0, f"The user request is related to {requirement.task_domain}.")
        return items

    def _default_workflow(
        self,
        requirement: ParsedRequirement,
        answers: dict[str, str] | None = None,
        missing: list[str] | None = None,
    ) -> list[str]:
        answers = answers or {}
        workflow = [
            "Restate the user's goal and identify the relevant task context.",
            "Ask for missing details only when the task cannot be handled safely from the current context.",
            "Apply the rules and templates in resources/ before producing the final response.",
            "Generate the response in the requested output format.",
            "Review the response against the constraints and remove unsafe or overreaching content.",
        ]
        if missing:
            workflow.insert(2, f"Pay special attention to these missing capabilities: {', '.join(missing[:5])}.")
        if answers.get("source_material"):
            workflow.insert(1, f"Use the expected source material policy: {answers['source_material']}")
        return workflow

    def _default_constraints(
        self,
        requirement: ParsedRequirement,
        answers: dict[str, str] | None = None,
    ) -> list[str]:
        answers = answers or {}
        constraints = [
            "Do not install third-party extensions, run shell commands, or request secrets.",
            "Do not invent source material that the user has not provided.",
            "Prefer safe guidance, checklists, templates, and examples over direct high-risk automation.",
        ]
        if "作业" in requirement.raw_text or "答案" in requirement.raw_text:
            constraints.insert(0, "Do not provide a complete homework answer; guide the user with concepts and steps.")
        if answers.get("boundaries"):
            constraints.insert(0, answers["boundaries"])
        return constraints

    def _default_output_format(self) -> str:
        return (
            "Use Markdown sections: Task Understanding, Key Guidance, Step-by-step Hints, "
            "Output Template, Safety or Boundary Notes."
        )

    def _default_resources(self, requirement: ParsedRequirement) -> list[SkillResourceSpec]:
        return [
            SkillResourceSpec(
                path="resources/guidance_rules.md",
                purpose="Rules and boundaries for this Skill.",
                content_hint="Summarize safe behavior, refusal boundaries, and workflow reminders.",
            ),
            SkillResourceSpec(
                path="resources/output_template.md",
                purpose="Reusable response template.",
                content_hint=f"Template for {requirement.task_domain} responses.",
            ),
        ]

    def _default_examples(self, requirement: ParsedRequirement) -> list[SkillResourceSpec]:
        return [
            SkillResourceSpec(
                path="examples/sample_output.md",
                purpose="Example response following the Skill workflow.",
                content_hint=f"Sample output for: {requirement.raw_text}",
            )
        ]

    def _resource_specs(self, value: Any) -> list[SkillResourceSpec]:
        if not isinstance(value, list):
            return []
        specs: list[SkillResourceSpec] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path") or "").strip()
            purpose = str(item.get("purpose") or "").strip()
            if not path or not purpose:
                continue
            specs.append(
                SkillResourceSpec(
                    path=path,
                    purpose=purpose,
                    content_hint=str(item.get("content_hint") or "").strip(),
                )
            )
        return specs


def _extract_json(text: str) -> str:
    return extract_json_object(text)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    normalized = re.sub(r"-{2,}", "-", normalized)
    return normalized[:60].strip("-")


def _merged_answers(session: BuilderSession) -> dict[str, str]:
    answers: dict[str, str] = {}
    for turn in session.turns:
        answers.update(turn.answers)
    return answers


def _missing_capabilities(evaluations: list[CandidateEvaluation]) -> list[str]:
    missing: list[str] = []
    for evaluation in evaluations[:3]:
        for capability in evaluation.missing_capabilities:
            if capability not in missing:
                missing.append(capability)
    return missing
