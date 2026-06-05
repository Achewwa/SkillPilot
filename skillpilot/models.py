from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


ExtensionType = Literal["skill", "mcp", "plugin", "mixed", "unknown"]
RiskLevel = Literal["low", "medium", "high"]
DecisionType = Literal[
    "recommend_existing",
    "recommend_with_custom_extension",
    "build_custom_skill",
]


class ParsedRequirement(BaseModel):
    raw_text: str
    task_domain: str = "unknown"
    desired_capabilities: list[str] = Field(default_factory=list)
    requires_codebase_access: bool = False
    requires_command_execution: bool = False
    requires_external_service: bool = False
    risk_tolerance: str = "medium"


class TypeClassification(BaseModel):
    recommended_type: ExtensionType
    confidence: float
    reason: str


class SearchPlan(BaseModel):
    extension_type: ExtensionType
    sources: list[str]
    queries: list[str]


class Candidate(BaseModel):
    name: str
    extension_type: ExtensionType
    source_url: str
    description: str
    capabilities: list[str] = Field(default_factory=list)
    installation: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    maintainer: str | None = None
    last_updated: str | None = None
    evidence: list[str] = Field(default_factory=list)


class CandidateEvaluation(BaseModel):
    candidate: Candidate
    match_score: float
    matched_capabilities: list[str] = Field(default_factory=list)
    missing_capabilities: list[str] = Field(default_factory=list)
    trust_level: str = "medium"
    risk_level: RiskLevel = "low"
    risk_reasons: list[str] = Field(default_factory=list)
    reason: str


class Decision(BaseModel):
    decision_type: DecisionType
    reason: str
    selected_candidates: list[CandidateEvaluation] = Field(default_factory=list)
    custom_skill_name: str | None = None


class SkillDraftResult(BaseModel):
    name: str
    path: str
    files: list[str]


class AgentRunResult(BaseModel):
    requirement: ParsedRequirement
    classification: TypeClassification
    search_plan: SearchPlan
    evaluations: list[CandidateEvaluation]
    decision: Decision
    report_path: str
    trace_path: str
    skill_draft: SkillDraftResult | None = None
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


def model_to_dict(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()
