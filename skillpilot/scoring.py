from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScoringWeights:
    capability: float = 0.45
    type_match: float = 0.15
    documentation: float = 0.20
    safety: float = 0.20

    def aggregate(
        self,
        *,
        capability_score: float,
        type_score: float,
        documentation_score: float,
        safety_score: float,
    ) -> float:
        return (
            capability_score * self.capability
            + type_score * self.type_match
            + documentation_score * self.documentation
            + safety_score * self.safety
        )


DEFAULT_SCORING_WEIGHTS = ScoringWeights()
