"""Path registry: Green is an explicit allowlist; unknown work is Amber."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Tier = Literal["green", "amber", "red"]

_DEFAULT_REGISTRY = Path(__file__).resolve().parents[1] / "registries" / "classifier-paths.json"


@dataclass(frozen=True)
class PathRegistry:
    green_prefixes: tuple[str, ...]
    green_exact: tuple[str, ...]
    amber_prefixes: tuple[str, ...]
    amber_exact: tuple[str, ...]
    red_prefixes: tuple[str, ...]
    red_exact: tuple[str, ...]
    investment_output_prefixes: tuple[str, ...]
    codeowners_patterns: tuple[str, ...]

    @classmethod
    def load(cls, path: Path | None = None) -> PathRegistry:
        raw = json.loads((path or _DEFAULT_REGISTRY).read_text(encoding="utf-8"))
        return cls(
            green_prefixes=tuple(raw["green_prefixes"]),
            green_exact=tuple(raw["green_exact"]),
            amber_prefixes=tuple(raw["amber_prefixes"]),
            amber_exact=tuple(raw["amber_exact"]),
            red_prefixes=tuple(raw["red_prefixes"]),
            red_exact=tuple(raw["red_exact"]),
            investment_output_prefixes=tuple(raw["investment_output_prefixes"]),
            codeowners_patterns=tuple(raw["codeowners_patterns"]),
        )


def normalize_path(path: str) -> str:
    text = path.replace("\\", "/").strip()
    while text.startswith("./"):
        text = text[2:]
    return text.lstrip("/")


def _matches_prefix(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in prefixes)


def path_tier(path: str, registry: PathRegistry) -> Tier:
    norm = normalize_path(path)
    if norm in registry.red_exact or _matches_prefix(norm, registry.red_prefixes):
        return "red"
    if norm in registry.amber_exact or _matches_prefix(norm, registry.amber_prefixes):
        return "amber"
    if norm in registry.green_exact or _matches_prefix(norm, registry.green_prefixes):
        return "green"
    return "amber"


def highest_tier(paths: tuple[str, ...], registry: PathRegistry) -> Tier:
    order = {"green": 0, "amber": 1, "red": 2}
    highest: Tier = "green"
    if not paths:
        return "amber"
    for path in paths:
        tier = path_tier(path, registry)
        if order[tier] > order[highest]:
            highest = tier
    return highest


def touches_investment_output(paths: tuple[str, ...], registry: PathRegistry) -> bool:
    return any(
        _matches_prefix(normalize_path(path), registry.investment_output_prefixes)
        for path in paths
    )
