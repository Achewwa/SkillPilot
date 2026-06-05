from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


ExtensionType = Literal["skill", "mcp", "plugin", "mixed", "unknown"]
RiskLevel = Literal["low", "medium", "high"]
SearchSourceType = Literal["source", "web", "github"]
SearchSourceKind = Literal[
    "official_docs",
    "official_registry_api",
    "community_registry_api",
    "community_skill_directory_api",
    "commercial_hosted_registry_api",
    "official_github_marketplace_repo",
    "community_github_marketplace_repo",
    "official_example_repo",
    "community_awesome_list",
    "web_directory",
    "github_search",
]
SourceTrustLevel = Literal["official", "partner", "community", "commercial", "discovery"]
SearchStatus = Literal["success", "no_results", "failed", "skipped"]
ReadStatus = Literal["success", "failed", "skipped"]
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


class SearchSource(BaseModel):
    source_id: str
    name: str
    extension_types: list[ExtensionType]
    source_kind: SearchSourceKind
    trust_level: SourceTrustLevel
    reader_type: str
    searcher_type: str
    base_url: str
    index_url: str | None = None
    api_url: str | None = None
    data_format: str
    notes: str = ""


class SearchQuery(BaseModel):
    text: str
    source_type: SearchSourceType
    extension_type: ExtensionType
    purpose: str
    source_id: str | None = None
    max_results: int = 5


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    source_type: SearchSourceType
    query: str
    status: SearchStatus
    source_id: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievedContent(BaseModel):
    title: str
    url: str
    source_type: SearchSourceType
    query: str
    status: ReadStatus
    source_id: str | None = None
    content: str = ""
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchPlan(BaseModel):
    extension_type: ExtensionType
    sources: list[SearchSource]
    queries: list[SearchQuery]


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
    capability_score: float = 0.0
    type_score: float = 0.0
    documentation_score: float = 0.0
    safety_score: float = 0.0
    matched_capabilities: list[str] = Field(default_factory=list)
    missing_capabilities: list[str] = Field(default_factory=list)
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
    search_results: list[SearchResult] = Field(default_factory=list)
    retrieved_contents: list[RetrievedContent] = Field(default_factory=list)
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
