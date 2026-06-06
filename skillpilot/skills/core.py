from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, Literal, Protocol, TypeVar


class LLMProvider(Protocol):
    def generate(self, prompt: str) -> Any:
        ...


T = TypeVar("T")


@dataclass(frozen=True)
class SkillResult(Generic[T]):
    value: T
    status: Literal["success", "fallback", "skipped", "failed"] = "success"
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
