"""Content-addressed identity helpers. Stdlib only."""

from __future__ import annotations

import hashlib
import re

_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_git_sha(value: str) -> bool:
    return bool(_GIT_SHA.fullmatch(value))


def is_sha256(value: str) -> bool:
    return bool(_SHA256.fullmatch(value))


def require_git_sha(value: str, *, what: str) -> str:
    if not is_git_sha(value):
        raise ValueError(f"{what} must be a 40-hex git SHA, got {value!r}")
    return value
