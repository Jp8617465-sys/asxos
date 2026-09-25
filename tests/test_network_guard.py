"""Proof that the outbound-network guard works, and that offline tests still do.

A guard nobody has watched fail is not a guard — it reads as coverage while
protecting nothing. ``tests/test_no_bare_date_today.py`` makes the same point
about its AST visitor and pins it with explicit "this detects" cases; this module
follows that shape for ``tests/_netguard.py``.

Nothing here performs real egress. Every denial is asserted through
``pytest.raises``, so the guard raises before a packet exists; the opt-in case
asserts the guard is *disarmed* rather than calling out.
"""
from __future__ import annotations

import socket
from pathlib import Path

import httpx
import pytest

from tests import _netguard
from tests._netguard import NetworkAccessDenied

_REPO_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# The guard denies outbound access
# ---------------------------------------------------------------------------


def test_create_connection_is_blocked() -> None:
    with pytest.raises(NetworkAccessDenied):
        socket.create_connection(("example.com", 443), timeout=1)


def test_socket_connect_is_blocked() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(NetworkAccessDenied):
            sock.connect(("example.com", 443))
    finally:
        sock.close()


def test_socket_connect_ex_is_blocked() -> None:
    """connect_ex returns an errno instead of raising, so it needs its own patch.

    Without it, a caller using connect_ex would silently reach the network and
    this suite would report a green offline run.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(NetworkAccessDenied):
            sock.connect_ex(("example.com", 443))
    finally:
        sock.close()


def test_dns_resolution_is_blocked() -> None:
    """DNS is denied so failure names the host, before any packet is sent."""
    with pytest.raises(NetworkAccessDenied):
        socket.getaddrinfo("example.com", 443)


def test_loopback_is_blocked() -> None:
    """Loopback is denied too — the verifier has no Postgres unless it starts one.

    A test quietly reaching localhost:5432 is exactly the class of failure this
    guard exists to catch, so loopback is not carved out.
    """
    with pytest.raises(NetworkAccessDenied):
        socket.create_connection(("127.0.0.1", 5432), timeout=1)


def test_real_http_client_call_is_blocked() -> None:
    """The end-to-end shape: a real client, through httpcore, hits the guard."""
    with pytest.raises(NetworkAccessDenied):
        httpx.get("https://example.invalid", timeout=1)


def test_psycopg2_connect_is_blocked() -> None:
    """psycopg2 opens its socket in C, below every patch above.

    libpq bypasses the Python socket module entirely, so without this separate
    patch a psycopg2 connection would sail straight past the guard.
    """
    psycopg2 = pytest.importorskip("psycopg2")
    with pytest.raises(NetworkAccessDenied):
        psycopg2.connect("postgresql://u:p@localhost:5432/db")


# ---------------------------------------------------------------------------
# The guard does not deny things that are not outbound access
# ---------------------------------------------------------------------------


def test_af_unix_socketpair_still_works() -> None:
    """asyncio's self-pipe uses AF_UNIX socketpair; blocking it would break
    every pytest-asyncio test for no security gain."""
    left, right = socket.socketpair()
    try:
        left.sendall(b"ping")
        assert right.recv(4) == b"ping"
    finally:
        left.close()
        right.close()


async def test_asyncio_still_runs_under_the_guard() -> None:
    """Direct evidence for the AF_UNIX carve-out: this test is itself async."""
    import asyncio

    await asyncio.sleep(0)
    assert _netguard.is_enabled() is True


def test_httpx_mock_transport_still_works() -> None:
    """In-memory transports are not network access and must keep working."""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"ok": True})
    )
    with httpx.Client(transport=transport) as client:
        response = client.get("https://example.invalid/data")
    assert response.json() == {"ok": True}


async def test_asgi_transport_still_works() -> None:
    """The idiom used by tests/test_decision_engine_prototype.py:595 — ASGI
    dispatch in-process, base_url never resolved."""

    async def app(scope, receive, send):  # type: ignore[no-untyped-def]
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"text/plain")],
        })
        await send({"type": "http.response.body", "body": b"offline"})

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
    assert response.text == "offline"


# ---------------------------------------------------------------------------
# The opt-in marker, and that it does not leak
# ---------------------------------------------------------------------------


@pytest.mark.network
def test_network_marker_lifts_the_guard() -> None:
    """Asserted without egress: the marked test checks the guard is disarmed."""
    assert _netguard.is_enabled() is False


def test_guard_is_rearmed_after_a_marked_test() -> None:
    """The lift is per-test. An opted-in test must not leak permission to the
    tests that follow it — the autouse fixture re-arms in a finally block."""
    assert _netguard.is_enabled() is True
    with pytest.raises(NetworkAccessDenied):
        socket.create_connection(("example.com", 443), timeout=1)


def test_network_marker_is_registered() -> None:
    """--strict-markers makes an unregistered marker a collection error, so this
    would already fail loudly; pinning it keeps the registration deliberate."""
    import tomllib

    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as handle:
        config = tomllib.load(handle)
    markers = config["tool"]["pytest"]["ini_options"]["markers"]
    assert any(marker.startswith("network:") for marker in markers)


# ---------------------------------------------------------------------------
# Secretless: no credential reaches the settings objects
# ---------------------------------------------------------------------------


def test_production_secrets_file_is_unreachable() -> None:
    """conftest points HOME at an empty temp dir before any asxos import.

    asxos/settings_base.py resolves ENV_FILE at import time from Path.home(), so this
    asserts the file pydantic-settings was pointed at does not exist. On a
    developer machine the real path DOES exist, which is what made every local
    run load production credentials before this guard landed.
    """
    from asxos.settings_base import ENV_FILE as _ENV_FILE

    assert not Path(_ENV_FILE).exists(), (
        f"the settings env file is reachable during tests: {_ENV_FILE}. "
        "The suite must not be able to load production credentials."
    )


def test_no_production_credentials_loaded() -> None:
    """The direct statement of the secretless property.

    Every credential-bearing field on the module-level CoreSettings() instance
    must be empty. This fails on any machine where the secrets file leaks into
    the test process — which was the case for every local run before this
    change.
    """
    from asxos.config import core_settings

    leaked = [
        name
        for name in (
            "eodhd_api_key",
            "fred_api_key",
            "asxos_api_token",
            "backup_github_token",
            "backup_repo",
            "healthchecks_write_key",
        )
        if getattr(core_settings, name) != ""
    ]
    leaked += [
        name
        for name in dir(core_settings)
        if name.startswith("healthcheck_url_") and getattr(core_settings, name) != ""
    ]
    assert not leaked, (
        "production credentials reached the test process via "
        f"{Path(__file__).parents[1]}/asxos/config.py: {sorted(leaked)}"
    )


def test_database_url_is_the_deterministic_dummy() -> None:
    """The one credential the suite does need is pinned, not inherited."""
    from asxos.config import core_settings

    assert str(core_settings.database_url) == "postgresql://test:test@localhost/test"


def test_marker_lifts_the_guard_during_module_scoped_fixture_setup(
    tmp_path: Path,
) -> None:
    """Regression: the lift must cover module-scoped fixture setup.

    tests/test_price_revision_migration_integration.py opens its connection in a
    ``scope="module"`` fixture. An autouse function-scoped fixture runs *after*
    module-scoped setup, so a fixture-based lift would leave the guard armed
    exactly where the marked test needs it lifted — breaking the
    migration-integration CI lane while every offline run stayed green. This
    runs a nested pytest to prove the hookwrapper covers that phase.

    No socket is opened: the probe records ``is_enabled()`` rather than
    connecting.
    """
    import subprocess
    import sys

    (tmp_path / "conftest.py").write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(_REPO_ROOT)!r})\n"
        "from tests.conftest import pytest_runtest_protocol  # noqa: F401\n"
        "from tests import _netguard\n"
        "_netguard.install()\n"
        "_netguard.enable()\n",
        encoding="utf-8",
    )
    (tmp_path / "test_probe.py").write_text(
        "import pytest\n"
        "from tests import _netguard\n"
        "pytestmark = pytest.mark.network\n"
        "\n"
        "@pytest.fixture(scope='module')\n"
        "def armed_during_setup():\n"
        "    return _netguard.is_enabled()\n"
        "\n"
        "def test_guard_was_lifted_for_module_scope(armed_during_setup):\n"
        "    assert armed_during_setup is False\n",
        encoding="utf-8",
    )
    (tmp_path / "pytest.ini").write_text(
        "[pytest]\nmarkers =\n    network: opt-in outbound network access\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(tmp_path / "test_probe.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, (
        "the network marker did not lift the guard during module-scoped fixture "
        f"setup:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
