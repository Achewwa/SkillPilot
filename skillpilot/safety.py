from __future__ import annotations

from dataclasses import dataclass, field

from skillpilot.models import Candidate, ParsedRequirement, RiskLevel, SkillSpec
from skillpilot.utils import dedupe_preserve_order


@dataclass(frozen=True)
class RiskAssessment:
    risk_level: RiskLevel
    safety_score: float
    risk_reasons: list[str] = field(default_factory=list)
    allowed: bool = True
    safe_alternatives: list[str] = field(default_factory=list)


class RiskPolicy:
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

    def assess_candidate(self, candidate: Candidate) -> RiskAssessment:
        permissions = set(candidate.permissions)
        dependencies = set(candidate.dependencies)
        risk_reasons: list[str] = []
        high_risk = bool({"write_repository", "command_execution"} & permissions) or bool(
            {"api_token", "github_token"} & dependencies
        )
        medium_risk = bool({"external_service", "read_repository", "read_documents"} & permissions)
        if "write_repository" in permissions:
            risk_reasons.append("候选涉及仓库写入权限，可能修改代码、提交或创建 PR。")
        if "command_execution" in permissions:
            risk_reasons.append("候选涉及命令执行，需要避免自动运行不可信脚本。")
        if {"api_token", "github_token"} & dependencies:
            risk_reasons.append("候选需要 token 或 API 凭据，应避免在未审计配置中暴露。")
        if "external_service" in permissions:
            risk_reasons.append("候选需要连接外部服务，可能涉及账号、网络请求或远程数据。")
        if "read_repository" in permissions:
            risk_reasons.append("候选会读取仓库或代码库，需要确认访问范围。")
        if "read_documents" in permissions:
            risk_reasons.append("候选会读取本地或上传文档，需要确认文件范围和隐私。")
        if high_risk:
            return RiskAssessment("high", 0.0, risk_reasons)
        if medium_risk:
            return RiskAssessment("medium", 0.55, risk_reasons)
        risk_reasons.append("未发现明显的高危权限或敏感依赖。")
        return RiskAssessment("low", 1.0, risk_reasons)

    def assess_skill_request(
        self,
        requirement: ParsedRequirement,
        spec: SkillSpec,
    ) -> RiskAssessment:
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

        risk_reasons = dedupe_preserve_order(risk_reasons)
        if any("命令" in reason or "删除" in reason or "数据库" in reason for reason in risk_reasons):
            return RiskAssessment(
                risk_level="high",
                safety_score=0.0,
                risk_reasons=risk_reasons,
                allowed=False,
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
            return RiskAssessment(
                risk_level="medium",
                safety_score=0.55,
                risk_reasons=dedupe_preserve_order(risk_reasons),
                allowed=True,
                safe_alternatives=[
                    "保持 Skill 为说明、模板和检查清单，不自动连接外部系统。",
                    "需要外部工具时，只给出人工配置建议。",
                ],
            )

        return RiskAssessment(
            risk_level="low",
            safety_score=1.0,
            risk_reasons=["未发现明显的高危权限、敏感凭据或不可逆操作。"],
            allowed=True,
            safe_alternatives=[],
        )
