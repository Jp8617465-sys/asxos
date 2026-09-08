"""CODEOWNERS vs classifier-registry drift check."""

from __future__ import annotations

from asxos_control.registry import PathRegistry


def parse_codeowners(text: str) -> dict[str, tuple[str, ...]]:
    rules: dict[str, tuple[str, ...]] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        pattern, *owners = line.split()
        rules[pattern] = tuple(owners)
    return rules


def drift_errors(codeowners_text: str, registry: PathRegistry, owner: str = "@Jp8617465-sys") -> list[str]:
    rules = parse_codeowners(codeowners_text)
    errors: list[str] = []
    if "*" in rules:
        errors.append("catch_all_masks_risk_routing")
    for pattern in registry.codeowners_patterns:
        if pattern not in rules:
            errors.append(f"missing:{pattern}")
        elif owner not in rules[pattern]:
            errors.append(f"unowned:{pattern}")
    return errors
