from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from skillpilot.config import PROJECT_ROOT


DEFAULT_SOURCE_ACCESS_GUIDE_PATH = PROJECT_ROOT / "docs" / "stage_2_3_source_access.json"


@dataclass(frozen=True)
class SourceAccessGuide:
    source_id: str
    extension_types: list[str]
    searcher_type: str
    reader_type: str
    entrypoint: dict[str, Any]
    content_format: str
    search_method: str
    query_parameters: dict[str, Any] = field(default_factory=dict)
    result_mapping: dict[str, str] = field(default_factory=dict)
    detail_reading: str = ""
    risk_notes: list[str] = field(default_factory=list)
    failure_handling: str = ""


class SourceAccessGuideLoader:
    """Read structured source search guidance from the project JSON guide."""

    def __init__(self, guide_path: Path = DEFAULT_SOURCE_ACCESS_GUIDE_PATH) -> None:
        self.guide_path = guide_path
        self._guides_by_source_id: dict[str, SourceAccessGuide] | None = None

    def get(self, source_id: str | None) -> SourceAccessGuide | None:
        if not source_id:
            return None
        return self._guides().get(source_id)

    def all(self) -> dict[str, SourceAccessGuide]:
        return dict(self._guides())

    def _guides(self) -> dict[str, SourceAccessGuide]:
        if self._guides_by_source_id is None:
            payload = json.loads(self.guide_path.read_text(encoding="utf-8"))
            guides: dict[str, SourceAccessGuide] = {}
            for item in payload.get("sources", []):
                guide = SourceAccessGuide(
                    source_id=str(item["source_id"]),
                    extension_types=[str(value) for value in item.get("extension_types", [])],
                    searcher_type=str(item["searcher_type"]),
                    reader_type=str(item["reader_type"]),
                    entrypoint=dict(item["entrypoint"]),
                    content_format=str(item["content_format"]),
                    search_method=str(item["search_method"]),
                    query_parameters=dict(item.get("query_parameters", {})),
                    result_mapping={
                        str(key): str(value)
                        for key, value in item.get("result_mapping", {}).items()
                    },
                    detail_reading=str(item.get("detail_reading", "")),
                    risk_notes=[str(value) for value in item.get("risk_notes", [])],
                    failure_handling=str(item.get("failure_handling", "")),
                )
                guides[guide.source_id] = guide
            self._guides_by_source_id = guides
        return self._guides_by_source_id
