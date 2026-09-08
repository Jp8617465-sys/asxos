"""Immutable control pin. Live callers must use a 40-hex commit, never a branch."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from asxos_control.hashes import is_git_sha

_DEFAULT = Path(__file__).resolve().parents[1] / "fixtures" / "control-pin.json"


@dataclass(frozen=True)
class ControlPin:
    product_repo: str
    verifier_commit: str
    publisher_app_slug: str
    check_name: str
    state_controller_app_slug: str
    james_login: str

    @property
    def is_live(self) -> bool:
        return is_git_sha(self.verifier_commit)

    @classmethod
    def load(cls, path: Path | None = None) -> ControlPin:
        raw = json.loads((path or _DEFAULT).read_text(encoding="utf-8"))
        return cls(
            product_repo=raw["product_repo"],
            verifier_commit=raw["verifier_commit"],
            publisher_app_slug=raw["publisher_app_slug"],
            check_name=raw["check_name"],
            state_controller_app_slug=raw["state_controller_app_slug"],
            james_login=raw["james_login"],
        )


def require_live_pin(pin: ControlPin) -> ControlPin:
    if not pin.is_live:
        raise ValueError("control pin is not an immutable 40-hex commit")
    if pin.check_name != "risk-classify":
        raise ValueError("check name must be risk-classify")
    if pin.product_repo != "Jp8617465-sys/asxos":
        raise ValueError("wrong product repository")
    return pin
