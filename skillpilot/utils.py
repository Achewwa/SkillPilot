from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TypeVar

T = TypeVar("T")
K = TypeVar("K")


def extract_json_object(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`").strip()
        if stripped.startswith("json"):
            stripped = stripped.removeprefix("json").strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("LLM response did not contain a JSON object.")
    return stripped[start : end + 1]


def dedupe_preserve_order(
    values: Iterable[T],
    key: Callable[[T], K] | None = None,
) -> list[T]:
    seen: set[K | T] = set()
    deduped: list[T] = []
    for value in values:
        marker = key(value) if key else value
        if marker in seen:
            continue
        seen.add(marker)
        deduped.append(value)
    return deduped
