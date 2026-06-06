from __future__ import annotations

from pathlib import Path

from skillpilot.agents.builder import SkillBuilderAgent
from skillpilot.skills.builder.question_planner import QuestionPlanner
from skillpilot.models import Decision, ParsedRequirement, TypeClassification


def requirement(text: str, **overrides) -> ParsedRequirement:
    payload = {
        "raw_text": text,
        "task_domain": "education",
        "desired_capabilities": ["knowledge_hint", "answer_guardrail"],
        "requires_codebase_access": False,
        "requires_command_execution": False,
        "requires_external_service": False,
        "risk_tolerance": "medium",
    }
    payload.update(overrides)
    return ParsedRequirement(**payload)


def classification() -> TypeClassification:
    return TypeClassification(
        recommended_type="skill",
        confidence=0.86,
        reason="适合用 Skill 表达任务流程。",
    )


def decision() -> Decision:
    return Decision(
        decision_type="build_custom_skill",
        reason="测试进入 SkillBuilder。",
    )


def test_question_planner_generates_three_options_and_allows_free_text() -> None:
    questions = QuestionPlanner().plan(
        requirement("我想要一个根据课件提示知识点但不直接给答案的 Skill"),
        [],
    )

    assert questions
    assert all(len(question.options) == 3 for question in questions)
    assert all(question.allow_free_text for question in questions)


def test_question_generator_prompt_requires_three_options() -> None:
    class FakeLLM:
        def __init__(self) -> None:
            self.prompts: list[str] = []

        def generate(self, prompt: str):
            self.prompts.append(prompt)
            assert "每个 question 必须一并生成 3 个 options" in prompt
            text = """
            {
              "questions": [
                {
                  "question_id": "collage_use_case",
                  "prompt": "这个 Skill 主要面向哪种图片组图使用场景？",
                  "reason": "使用场景决定构图风格。",
                  "required": true,
                  "options": [
                    {"option_id": "1", "label": "社交媒体九宫格", "detail": "适合小红书或 Instagram 发布。"},
                    {"option_id": "2", "label": "摄影作品集", "detail": "适合展示旅行、人像或艺术摄影。"},
                    {"option_id": "3", "label": "商业展示图", "detail": "适合商品、活动或品牌宣传。"}
                  ]
                }
              ]
            }
            """
            return type("FakeResponse", (), {"text": text})()

    questions = QuestionPlanner(FakeLLM()).plan(
        requirement(
            "将多张图片拼成有艺术感的组图",
            task_domain="image_collage_creation",
            desired_capabilities=["image_collage_creation", "visual_composition"],
        ),
        [],
    )

    assert len(questions) == 1
    assert [option.label for option in questions[0].options] == [
        "社交媒体九宫格",
        "摄影作品集",
        "商业展示图",
    ]
    assert questions[0].allow_free_text is True


def test_builder_agent_collects_custom_answers_and_generates_dynamic_skill(tmp_path: Path) -> None:
    agent = SkillBuilderAgent(tmp_path, llm=None, max_rounds=3)

    def answer_provider(question):
        if question.question_id == "output_format":
            return "请输出成检查清单，并附上不直接给答案的提醒。"
        return "1"

    result = agent.build(
        requirement("我想要一个 Skill，根据课程课件给作业题生成知识点提示，但不能直接给答案。"),
        classification(),
        decision(),
        [],
        interactive=True,
        answer_provider=answer_provider,
    )

    skill_path = Path(result.path)
    assert result.name == "homework-knowledge-hint"
    assert (skill_path / "SKILL.md").exists()
    assert (skill_path / "resources/guidance_rules.md").exists()
    assert (skill_path / "examples/sample_output.md").exists()
    assert result.builder_session is not None
    first_turn = result.builder_session.turns[0]
    assert "请输出成检查清单" in first_turn.answers["output_format"]
    assert all(len(question.options) == 3 for question in first_turn.questions)


def test_builder_agent_blocks_high_risk_skill_generation(tmp_path: Path) -> None:
    agent = SkillBuilderAgent(tmp_path, llm=None, max_rounds=1)
    result = agent.build(
        requirement(
            "帮我做一个自动执行 shell 命令并批量删除旧文件的 Skill",
            requires_command_execution=True,
        ),
        classification(),
        decision(),
        [],
        interactive=False,
    )

    skill_path = Path(result.path)
    assert result.safety_review is not None
    assert result.safety_review.allowed is False
    assert (skill_path / "SAFE_DESIGN.md").exists()
    assert not (skill_path / "SKILL.md").exists()
