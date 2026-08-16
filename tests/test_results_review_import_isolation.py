"""Step 0 proof (mission P2-04): results-review imports execute no config.

`asxos/domain/results_review/contracts.py:49` imports `derive_knowledge_date`
from `asxos/ingestion/financial_statements.py`. Before P2-04's Step 0 that
module's top imported `EODHDClient` (`asxos/ingestion/eodhd.py`), whose module
top imports `asxos.config`, whose line 108 executes `CoreSettings()` — reading
the secrets env file (`$HOME/Projects/asxos-secrets/.env.production`) and
hard-failing without `DATABASE_URL`. That chained a secrets requirement onto a
pure-contract import path.

The proof runs in a SUBPROCESS with `HOME` pointed at an empty temp dir and a
scrubbed environment (no `DATABASE_URL`), so any config execution on import
fails loudly instead of being masked by the developer machine's secrets file.
The subprocess also asserts `asxos.config` and `asxos.ingestion.eodhd` never
enter `sys.modules` — import success alone is not the claim; *no config
execution* is.

Mutation observation (recorded in the P2-04 report): restoring the module-top
`from asxos.ingestion.eodhd import EODHDClient` in `financial_statements.py`
makes this test fail (the subprocess import raises pydantic ValidationError
for the missing DATABASE_URL); reverting restores the pass.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import asxos

_REPO_ROOT = Path(asxos.__file__).resolve().parents[1]

_PROOF_SCRIPT = """
import sys

import asxos.domain.results_review.adapter
import asxos.domain.results_review.contracts
import asxos.domain.results_review.fixtures
import asxos.ingestion.financial_statements

assert "asxos.config" not in sys.modules, "asxos.config executed on import"
assert "asxos.ingestion.eodhd" not in sys.modules, "eodhd client imported"
print("IMPORT-ISOLATION-OK")
"""


def test_results_review_imports_without_secrets_or_config_execution(
    tmp_path: Path,
) -> None:
    empty_home = tmp_path / "empty-home"
    empty_home.mkdir()
    env = {
        "HOME": str(empty_home),
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(_REPO_ROOT),
        # Explicitly no DATABASE_URL / EODHD_API_KEY: config execution would
        # hard-fail here, which is exactly what makes the proof observable.
    }
    result = subprocess.run(  # noqa: S603 — fixed argv, test-controlled input
        [sys.executable, "-c", _PROOF_SCRIPT],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, (
        "results_review import executed config or failed without secrets:\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "IMPORT-ISOLATION-OK" in result.stdout
