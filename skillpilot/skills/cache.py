from __future__ import annotations

import json
from pathlib import Path

from skillpilot.models import Candidate


class LocalCandidateCache:
    def __init__(self, cache_path: Path) -> None:
        self.cache_path = cache_path

    def load(self) -> list[Candidate]:
        data = json.loads(self.cache_path.read_text(encoding="utf-8"))
        return [Candidate(**item) for item in data]
