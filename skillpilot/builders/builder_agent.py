from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from skillpilot.builders.packaging_advisor import PackagingAdvisor
from skillpilot.builders.question_planner import DetailOptionGenerator, QuestionPlanner
from skillpilot.builders.safety_reviewer import SafetyReviewer
from skillpilot.builders.skill_builder import SkillBuilder
from skillpilot.builders.skill_spec_generator import SkillSpecGenerator
from skillpilot.models import (
    BuilderSession,
    BuilderTurn,
    CandidateEvaluation,
    ClarificationQuestion,
    Decision,
    ParsedRequirement,
    SkillDraftResult,
    TypeClassification,
)

AnswerProvider = Callable[[ClarificationQuestion], str]


class BuilderLLM(Protocol):
    def generate(self, prompt: str) -> Any:
        ...


class SkillBuilderAgent:
    def __init__(
        self,
        generated_skills_dir: Path,
        llm: BuilderLLM | None = None,
        max_rounds: int = 3,
    ) -> None:
        option_generator = DetailOptionGenerator(llm)
        self.question_planner = QuestionPlanner(llm, option_generator)
        self.spec_generator = SkillSpecGenerator(llm)
        self.safety_reviewer = SafetyReviewer()
        self.packaging_advisor = PackagingAdvisor()
        self.builder = SkillBuilder(generated_skills_dir)
        self.max_rounds = max(1, max_rounds)

    def build(
        self,
        requirement: ParsedRequirement,
        classification: TypeClassification,
        decision: Decision,
        evaluations: list[CandidateEvaluation],
        *,
        interactive: bool = False,
        answer_provider: AnswerProvider | None = None,
    ) -> SkillDraftResult:
        session = BuilderSession(phase="intake")
        self._run_clarification_loop(
            requirement,
            session,
            interactive=interactive,
            answer_provider=answer_provider,
        )

        session.phase = "generate"
        spec = self.spec_generator.generate(
            requirement,
            classification,
            decision,
            evaluations,
            session,
        )
        session.spec = spec

        session.phase = "review"
        safety_review = self.safety_reviewer.review(requirement, spec)
        spec.packaging_notes = self.packaging_advisor.notes(spec, safety_review)
        session.safety_review = safety_review

        if not safety_review.allowed:
            session.phase = "blocked"
            return self.builder.write_safety_advice(spec, safety_review, session)

        session.phase = "complete"
        return self.builder.build_from_spec(spec, safety_review, session)

    def _run_clarification_loop(
        self,
        requirement: ParsedRequirement,
        session: BuilderSession,
        *,
        interactive: bool,
        answer_provider: AnswerProvider | None,
    ) -> None:
        session.phase = "clarify"
        for turn_index in range(1, self.max_rounds + 1):
            questions = self.question_planner.plan(requirement, session.turns)
            if not questions:
                session.information_sufficient = True
                session.reflection = "没有新的关键澄清问题，进入 Skill 规格生成。"
                break

            answers: dict[str, str] = {}
            for question in questions:
                raw_answer = (
                    answer_provider(question)
                    if interactive and answer_provider is not None
                    else self._default_answer(question)
                )
                answers[question.question_id] = self._normalize_answer(question, raw_answer)

            turn = BuilderTurn(
                turn_index=turn_index,
                questions=questions,
                answers=answers,
                reflection=self._reflect(answers, turn_index),
            )
            session.turns.append(turn)
            session.reflection = turn.reflection
            if self._is_sufficient(session) or not interactive:
                session.information_sufficient = True
                break

        if not session.information_sufficient:
            session.reflection = "达到最大澄清轮数，使用已收集信息保守生成 Skill。"
            session.information_sufficient = True

    def _default_answer(self, question: ClarificationQuestion) -> str:
        if question.options:
            option = question.options[0]
            return f"{option.label}：{option.detail}"
        return "未提供额外回答，按初始需求保守生成。"

    def _normalize_answer(self, question: ClarificationQuestion, answer: str) -> str:
        cleaned = answer.strip()
        if not cleaned:
            return self._default_answer(question)
        for option in question.options:
            if cleaned in {option.option_id, option.label}:
                return f"{option.label}：{option.detail}"
        return cleaned

    def _reflect(self, answers: dict[str, str], turn_index: int) -> str:
        answered = "、".join(answers) if answers else "无"
        return f"第 {turn_index} 轮已收集字段：{answered}。"

    def _is_sufficient(self, session: BuilderSession) -> bool:
        answered = {question_id for turn in session.turns for question_id in turn.answers}
        required = {"use_case", "boundaries", "output_format"}
        return required.issubset(answered)
