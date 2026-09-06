"""Shared pytest configuration.

Three jobs, in this order, and the order is load-bearing:

1. **Make the environment secretless.** ``asxos/config.py`` instantiates
   ``CoreSettings()`` at module level, and its ``_ENV_FILE`` resolves
   ``Path.home() / "Projects" / "asxos-secrets" / ".env.production"`` at import
   time. On a developer machine that file exists, so before this block the suite
   ran with **real production credentials** loaded into ``core_settings`` —
   ``eodhd_api_key``, ``fred_api_key``, ``resend_api_key`` and all 22
   ``healthcheck_url_*`` fields. That also disarmed the empty-key guards in
   ``asxos/ingestion/eodhd.py`` and ``asxos/clients/fred.py``, turning "a test
   forgot to patch" from a loud ``RuntimeError`` into a successful authenticated
   call to a live vendor. Pointing ``HOME`` at an empty temp dir makes the
   secrets file *unreachable* rather than merely outranked: environment
   variables beat ``env_file`` in pydantic-settings, so scrubbing alone would
   still read the file and would leak any field not on the scrub list.

2. **Add the project root to ``sys.path``** so tests can import from ``jobs/``,
   which is not part of the ``asxos`` package.

3. **Arm the outbound-network guard** (``tests/_netguard.py``) so any test that
   reaches the network fails loudly and names itself. Opt out with
   ``@pytest.mark.network``.

Every test that touches the DB still mocks asyncpg/acquire directly.
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# 1. Secretless environment — must precede any asxos import.
# ---------------------------------------------------------------------------

# Not cleaned up: the interpreter is about to exit anyway, and removing it while
# a late fixture still resolves Path.home() would reintroduce the very lookup
# this is here to prevent.
_TEST_HOME = tempfile.mkdtemp(prefix="asxos-test-home-")
os.environ["HOME"] = _TEST_HOME

_CREDENTIAL_SUFFIXES = ("_API_KEY", "_TOKEN", "_SECRET", "_PASSWORD", "_WRITE_KEY")
_CREDENTIAL_PREFIXES = ("SUPABASE_", "HEALTHCHECK_URL_", "HEALTHCHECKS_")
_CREDENTIAL_EXACT = frozenset({"DATABASE_URL"})

# MIGRATION_TEST_DATABASE_URL is deliberately NOT scrubbed. It is the documented
# opt-in for tests/test_price_revision_migration_integration.py and is set by
# .github/workflows/migration-integration.yml against a throwaway postgres:17
# service container. Scrubbing it here would silently disable that CI lane,
# which is weakening a test, not hardening one.
_PRESERVED = frozenset({"MIGRATION_TEST_DATABASE_URL"})


def _is_credential(name: str) -> bool:
    if name in _PRESERVED:
        return False
    return (
        name in _CREDENTIAL_EXACT
        or name.endswith(_CREDENTIAL_SUFFIXES)
        or name.startswith(_CREDENTIAL_PREFIXES)
    )


for _name in [k for k in os.environ if _is_credential(k)]:
    del os.environ[_name]

# Deterministic dummies for the settings objects instantiated at import time:
# CoreSettings() (asxos/config.py) and BriefSettings() (asxos/api/main.py).
# These values are the ones tests/test_api_main.py used to seed itself; that
# block is now redundant and has been removed, along with the ordering hazard
# every future importer of asxos.api.main would otherwise have had to repeat.
for _key, _value in {
    "DATABASE_URL": "postgresql://test:test@localhost/test",
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_ANON_KEY": "test-anon",
    "RESEND_API_KEY": "test-resend",
    "BRIEF_FROM_EMAIL": "from@example.com",
    "BRIEF_TO_EMAIL": "to@example.com",
}.items():
    os.environ[_key] = _value

# ---------------------------------------------------------------------------
# 2. Allow `import jobs.ingest_news` etc. in test files.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

# ---------------------------------------------------------------------------
# 3. Outbound-network guard.
# ---------------------------------------------------------------------------
from tests import _netguard  # noqa: E402

_netguard.install()
_netguard.enable()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item: pytest.Item, nextitem: pytest.Item | None):
    """Arm the guard for every test; lift it only for @pytest.mark.network.

    This is a protocol hookwrapper rather than an autouse fixture, and that
    choice is load-bearing. An autouse *function-scoped* fixture runs after any
    module- or session-scoped fixture the test depends on, so the guard would
    still have been armed during their setup. That is not hypothetical:
    ``tests/test_price_revision_migration_integration.py`` opens its connection
    in a ``scope="module"`` fixture, so a fixture-based lift would have blocked
    the one test the marker exists to permit — silently breaking the
    migration-integration CI lane while every offline run stayed green.

    ``pytest_runtest_protocol`` wraps the item's whole setup/call/teardown, so
    the lift covers fixture setup and finalisation too. It is still strictly
    per-item and always re-arms in the ``finally``, so an opted-in test cannot
    leak permission to the tests that follow it.
    """
    if item.get_closest_marker("network") is not None:
        _netguard.disable()
    else:
        _netguard.set_current_test(item.nodeid)
    try:
        yield
    finally:
        _netguard.enable()
        _netguard.set_current_test(None)
