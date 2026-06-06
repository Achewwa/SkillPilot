from __future__ import annotations

from skillpilot.models import ParsedRequirement, SafetyReviewResult, SkillSpec


class SafetyReviewer:
    HIGH_RISK_TERMS = {
        "token": "需求涉及 token 或 API 凭据，不能生成会收集或暴露凭据的 Skill。",
        "api key": "需求涉及 API key，必须避免把密钥写入模板或示例。",
        "密钥": "需求涉及密钥，必须避免收集或保存敏感凭据。",
        "登录": "需求涉及账号登录，需要人工审查认证和权限边界。",
        "数据库": "需求涉及数据库操作，不能生成自动写库流程。",
        "批量删除": "需求涉及批量删除，存在不可逆数据风险。",
        "shell": "需求涉及 shell 命令，不能自动生成可执行命令流程。",
        "命令执行": "需求涉及命令执行，必须避免运行不可信命令。",
        "自动执行": "需求涉及自动执行，必须人工确认触发条件和权限。",
        "写入": "需求涉及写入操作，需要明确范围并避免自动修改关键数据。",
    }

    def review(self, requirement: ParsedRequirement, spec: SkillSpec) -> SafetyReviewResult:
        text = " ".join(
            [
                requirement.raw_text,
                spec.description,
                " ".join(spec.workflow),
                " ".join(spec.script_notes),
            ]
        ).lower()
        risk_reasons: list[str] = []
        for term, reason in self.HIGH_RISK_TERMS.items():
            if term.lower() in text:
                risk_reasons.append(reason)

        if requirement.requires_command_execution:
            risk_reasons.append("结构化需求标记为需要命令执行，SkillPilot 不应直接生成自动执行命令的 Skill。")
        if spec.requires_scripts:
            risk_reasons.append("规格要求生成辅助脚本，必须在人工审查后才可启用。")

        if any("命令" in reason or "删除" in reason or "数据库" in reason for reason in risk_reasons):
            return SafetyReviewResult(
                allowed=False,
                risk_level="high",
                risk_reasons=_dedupe(risk_reasons),
                safe_alternatives=[
                    "改为生成只读检查清单和人工执行步骤，不包含可执行脚本。",
                    "把所有写入、删除、登录或命令执行动作交给人工确认。",
                    "如确实需要工具能力，先单独设计 MCP 或 Plugin，并进行权限审计。",
                ],
            )

        if risk_reasons or requirement.requires_codebase_access or requirement.requires_external_service:
            if requirement.requires_codebase_access:
                risk_reasons.append("需求可能读取代码库，应限制读取范围并避免自动写入。")
            if requirement.requires_external_service:
                risk_reasons.append("需求可能连接外部服务，应人工检查账号和网络权限。")
            return SafetyReviewResult(
                allowed=True,
                risk_level="medium",
                risk_reasons=_dedupe(risk_reasons),
                safe_alternatives=[
                    "保持 Skill 为说明、模板和检查清单，不自动连接外部系统。",
                    "需要外部工具时，只给出人工配置建议。",
                ],
            )

        return SafetyReviewResult(
            allowed=True,
            risk_level="low",
            risk_reasons=["未发现明显的高危权限、敏感凭据或不可逆操作。"],
            safe_alternatives=[],
        )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped
