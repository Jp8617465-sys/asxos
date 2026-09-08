"""CLI for turning a protected-main nightly JUnit report into Finding JSONL."""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

from asxos.control_plane.probe_adapters import (
    adapt_nightly_junit,
    context_from_github_environment,
    findings_jsonl,
)

_MAX_JUNIT_BYTES = 4 * 1024 * 1024


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Emit canonical Findings from one nightly pytest JUnit report"
    )
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--pytest-exit-code", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    environment: Mapping[str, str] | None = None,
    clock: Callable[[], datetime] | None = None,
) -> int:
    """Write one canonical JSONL artifact; return nonzero on invalid context."""

    args = _parser().parse_args(argv)
    if args.pytest_exit_code < 0 or args.pytest_exit_code > 5:
        raise ValueError("pytest exit code must be between 0 and 5")
    document = args.junit.read_bytes()
    if not document or len(document) > _MAX_JUNIT_BYTES:
        raise ValueError("nightly JUnit document is empty or too large")
    now = (clock or (lambda: datetime.now(UTC)))()
    context = context_from_github_environment(
        workflow="nightly_check",
        environment=os.environ if environment is None else environment,
        observed_at=now,
    )
    findings = adapt_nightly_junit(
        context=context,
        document=document,
        probe_failed=args.pytest_exit_code != 0,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(findings_jsonl(findings), encoding="utf-8")
    print(f"wrote {len(findings)} canonical Finding record(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
