from __future__ import annotations

import json
from typing import Any

from skillpilot.models import (
    BuilderTurn,
    ClarificationOption,
    ClarificationQuestion,
    ParsedRequirement,
)
from skillpilot.skills.core import LLMProvider
from skillpilot.utils import extract_json_object


class DetailOptionGenerator:
    """Generate three concrete answer options while keeping free text available."""

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self.llm = llm

    def ensure_three_options(
        self,
        question: ClarificationQuestion,
        requirement: ParsedRequirement,
    ) -> ClarificationQuestion:
        options = [
            option
            for option in question.options
            if option.label.strip() and option.detail.strip()
        ][:3]
        if len(options) < 3 and self.llm is not None:
            generated = self._options_with_llm(question, requirement)
            seen = {option.label for option in options}
            options.extend(option for option in generated if option.label not in seen)
        if len(options) < 3:
            fallback = self._fallback_options(question, requirement)
            seen = {option.label for option in options}
            options.extend(option for option in fallback if option.label not in seen)
        question.options = options[:3]
        question.allow_free_text = True
        return question

    def _options_with_llm(
        self,
        question: ClarificationQuestion,
        requirement: ParsedRequirement,
    ) -> list[ClarificationOption]:
        prompt = (
            "你是 SkillPilot 的选项生成模块。请为澄清问题生成 3 个具体、互斥、可直接选择的细节选项。"
            "返回严格 JSON，不要 Markdown。字段：options，每项包含 option_id, label, detail。"
            "必须正好 3 个选项，同时不要剥夺用户自由输入自定义答案的可能。\n"
            f"用户需求：{requirement.raw_text}\n"
            f"问题：{question.prompt}"
        )
        try:
            response = self.llm.generate(prompt)
            payload = json.loads(_extract_json(getattr(response, "text", str(response))))
        except Exception:  # noqa: BLE001 - option generation falls back safely.
            return []
        return [
            ClarificationOption(
                option_id=str(item.get("option_id") or index),
                label=str(item.get("label") or "").strip(),
                detail=str(item.get("detail") or "").strip(),
            )
            for index, item in enumerate(payload.get("options") or [], start=1)
            if isinstance(item, dict)
        ][:3]

    def _fallback_options(
        self,
        question: ClarificationQuestion,
        requirement: ParsedRequirement,
    ) -> list[ClarificationOption]:
        question_id = question.question_id
        domain = requirement.task_domain
        if question_id == "use_case":
            return [
                ClarificationOption(
                    option_id="1",
                    label="学习辅助",
                    detail="面向学生理解资料、复习知识点或完成作业前的思考提示。",
                ),
                ClarificationOption(
                    option_id="2",
                    label="内容产出",
                    detail="面向写作、设计、总结或报告等可交付内容的生成流程。",
                ),
                ClarificationOption(
                    option_id="3",
                    label="检查改进",
                    detail="面向审查已有内容，指出问题并给出修改建议。",
                ),
            ]
        if question_id == "boundaries":
            return [
                ClarificationOption(
                    option_id="1",
                    label="只给建议",
                    detail="只输出解释、提示、检查清单或改进方向，不代替用户完成最终答案。",
                ),
                ClarificationOption(
                    option_id="2",
                    label="可给示例",
                    detail="允许提供小样例或模板，但样例不能等同于用户最终提交内容。",
                ),
                ClarificationOption(
                    option_id="3",
                    label="严格安全",
                    detail="不读取敏感文件，不使用 token，不执行命令，不连接外部写入服务。",
                ),
            ]
        if question_id == "output_format":
            return [
                ClarificationOption(
                    option_id="1",
                    label="分节 Markdown",
                    detail="按标题分成理解、步骤、注意事项、输出模板等 Markdown 小节。",
                ),
                ClarificationOption(
                    option_id="2",
                    label="检查清单",
                    detail="输出可逐项勾选的 checklist，适合审查和改进任务。",
                ),
                ClarificationOption(
                    option_id="3",
                    label="问答式提示",
                    detail="用连续问题引导用户思考，每一步都避免直接给最终答案。",
                ),
            ]
        if question_id == "source_material":
            return [
                ClarificationOption(
                    option_id="1",
                    label="用户粘贴资料",
                    detail="要求用户在对话中粘贴相关资料片段，Skill 只基于这些片段工作。",
                ),
                ClarificationOption(
                    option_id="2",
                    label="项目内资源",
                    detail="把规则、模板或示例放在 Skill 的 resources/ 目录中供 Claude 参考。",
                ),
                ClarificationOption(
                    option_id="3",
                    label="无固定资料",
                    detail="不依赖外部资料，只提供通用流程、检查项和安全边界。",
                ),
            ]
        return [
            ClarificationOption(
                option_id="1",
                label="保守默认",
                detail=f"按 {domain} 场景保守生成，优先安全和可解释。",
            ),
            ClarificationOption(
                option_id="2",
                label="更详细",
                detail="增加模板、示例和边界说明，让 Skill 更容易直接使用。",
            ),
            ClarificationOption(
                option_id="3",
                label="更简洁",
                detail="只保留核心流程和输出格式，减少额外文件。",
            ),
        ]


class QuestionPlanner:
    def __init__(
        self,
        llm: LLMProvider | None = None,
        option_generator: DetailOptionGenerator | None = None,
    ) -> None:
        self.llm = llm
        self.option_generator = option_generator or DetailOptionGenerator(llm)

    def plan(
        self,
        requirement: ParsedRequirement,
        turns: list[BuilderTurn],
    ) -> list[ClarificationQuestion]:
        if self.llm is not None:
            questions = self._plan_with_llm(requirement, turns)
            if questions:
                return [
                    self.option_generator.ensure_three_options(question, requirement)
                    for question in questions[:3]
                ]
        return self._fallback_questions(requirement, turns)

    def _plan_with_llm(
        self,
        requirement: ParsedRequirement,
        turns: list[BuilderTurn],
    ) -> list[ClarificationQuestion]:
        prompt = (
            "你是 SkillPilot 的问题生成模块。根据用户需求和已回答内容，生成下一轮澄清问题。"
            "返回严格 JSON，不要 Markdown。字段：questions，每项包含 question_id, prompt, reason, required, options。"
            "每个 question 必须一并生成 3 个 options，用于增进你对用户需求的了解。"
            "每个 option 包含 option_id, label, detail。"
            "问题应聚焦 Skill 的使用场景、边界、输出格式或资料来源；最多 3 个。"
            "不要为任何特例编写固定兜底选项；选项必须根据当前问题和当前用户需求生成。\n"
            f"用户需求：{requirement.raw_text}\n"
            f"已回答轮次：{json.dumps([turn.model_dump() for turn in turns], ensure_ascii=False)}"
        )
        try:
            response = self.llm.generate(prompt)
            payload = json.loads(_extract_json(getattr(response, "text", str(response))))
        except Exception:  # noqa: BLE001 - question generation falls back safely.
            return []
        questions: list[ClarificationQuestion] = []
        for index, item in enumerate(payload.get("questions") or [], start=1):
            if not isinstance(item, dict):
                continue
            prompt_text = str(item.get("prompt") or "").strip()
            if not prompt_text:
                continue
            questions.append(
                ClarificationQuestion(
                    question_id=str(item.get("question_id") or f"q{index}"),
                    prompt=prompt_text,
                    reason=str(item.get("reason") or "补齐 Skill 规格。").strip(),
                    required=bool(item.get("required", True)),
                    options=[
                        ClarificationOption(**option)
                        for option in item.get("options", [])
                        if isinstance(option, dict)
                    ],
                )
            )
        return questions

    def _fallback_questions(
        self,
        requirement: ParsedRequirement,
        turns: list[BuilderTurn],
    ) -> list[ClarificationQuestion]:
        answered = {question_id for turn in turns for question_id in turn.answers}
        candidates = [
            ClarificationQuestion(
                question_id="use_case",
                prompt="这个 Skill 最主要服务于哪类使用场景？",
                reason="明确使用场景后，SKILL.md 的触发条件会更准确。",
            ),
            ClarificationQuestion(
                question_id="boundaries",
                prompt="这个 Skill 必须避免哪些行为或越界输出？",
                reason="明确边界可以降低直接给答案、执行命令或访问敏感信息的风险。",
            ),
            ClarificationQuestion(
                question_id="output_format",
                prompt="你希望这个 Skill 的最终输出采用什么格式？",
                reason="输出格式会决定模板文件和示例文件的结构。",
            ),
            ClarificationQuestion(
                question_id="source_material",
                prompt="这个 Skill 需要依赖哪些资料来源？",
                reason="资料来源决定 resources/ 目录中是否需要放置规则、模板或示例。",
            ),
        ]
        planned = [question for question in candidates if question.question_id not in answered]
        if not planned:
            return []
        return [
            self.option_generator.ensure_three_options(question, requirement)
            for question in planned[:3]
        ]


def _extract_json(text: str) -> str:
    return extract_json_object(text)
