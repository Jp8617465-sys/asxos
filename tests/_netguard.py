"""Test-only outbound-network boundary.

The ACP verifier (`docs/proposals/arbi-chief-of-staff-and-feature-control-plane-plan-2026-09-03.md`
§5.4) runs the product suite under `docker run --network none` with no secret,
model key, deadman URL, or GitHub write token. Before a suite can be trusted to
that environment, an outbound call has to be a *loud failure here*, not a
surprise inside the container.

Every isolation guarantee in this suite currently rests on per-test
``unittest.mock`` discipline, and 14 modules assert "no network calls" in prose
with nothing mechanising the claim. This module mechanises it.

What this is NOT
----------------
This is a tripwire, not a sandbox. It patches Python-level entry points, so a
client that opens its socket from C bypasses it entirely — ``psycopg2`` reaches
the network through libpq, which is why ``psycopg2.connect`` is patched
separately below rather than being caught by the socket patches. Any future
C-extension client would need the same treatment. Containment remains the
verifier's ``--network none``; this guard exists to fail fast, in-process, with
a message that names the test.

Scope
-----
- ``AF_INET``/``AF_INET6`` connects are denied, **loopback included**. A test
  quietly reaching ``localhost:5432`` is precisely the failure this exists to
  catch: the verifier has no Postgres unless it starts one.
- ``AF_UNIX`` is deliberately untouched. ``socket.socketpair()`` on Unix uses the
  AF_UNIX socketpair syscall and never calls ``connect()``, but asyncio's
  self-pipe depends on the family working; blocking it would break every
  ``pytest-asyncio`` test for no security gain.
- DNS (``getaddrinfo``) is denied too, so resolution fails before any packet and
  the error names the host rather than surfacing as a connect timeout.

Production runtime is unaffected: this module lives under ``tests/``, is imported
only by ``tests/conftest.py``, and ``[tool.setuptools.packages.find]`` excludes
``tests*`` from the installed package.

Opt out for a genuinely external test with ``@pytest.mark.network`` (registered
in ``pyproject.toml``); ``tests/conftest.py`` lifts the guard for exactly that
test and re-arms afterwards.
"""
from __future__ import annotations

import socket
from typing import Any

__all__ = [
    "NetworkAccessDenied",
    "disable",
    "enable",
    "install",
    "is_enabled",
    "set_current_test",
]


class NetworkAccessDenied(RuntimeError):
    """A test attempted outbound network access."""


# Families that may connect freely. AF_UNIX only — see the module docstring.
_ALLOWED_FAMILIES: frozenset[int] = frozenset(
    f for f in (getattr(socket, "AF_UNIX", None),) if f is not None
)

_enabled = False
_installed = False
_current_test: str | None = None

# Captured before any patching so the originals survive re-entry.
_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex
_real_create_connection = socket.create_connection
_real_getaddrinfo = socket.getaddrinfo


def _describe(address: Any) -> str:
    if isinstance(address, tuple) and len(address) >= 2:
        return f"{address[0]}:{address[1]}"
    return repr(address)


def _deny(entry_point: str, target: str) -> NetworkAccessDenied:
    where = f"\n  test: {_current_test}" if _current_test else ""
    return NetworkAccessDenied(
        f"outbound network access is blocked in the test suite.\n"
        f"  attempted: {entry_point} -> {target}{where}\n"
        "  The product suite must run offline and secretless so the ACP verifier "
        "can execute it under `docker run --network none`.\n"
        "  Fix by faking the collaborator (see tests/test_security_master.py for "
        "the recorder-fake idiom) or by patching the client at the consuming "
        "module path (see tests/test_job_monitor.py).\n"
        "  A genuinely external, opt-in test must be marked @pytest.mark.network "
        "and recorded in docs/ops/offline-test-inventory.json."
    )


def _guarded_connect(self: socket.socket, address: Any, *args: Any, **kwargs: Any) -> Any:
    if _enabled and self.family not in _ALLOWED_FAMILIES:
        raise _deny("socket.connect", _describe(address))
    return _real_connect(self, address, *args, **kwargs)


def _guarded_connect_ex(self: socket.socket, address: Any, *args: Any, **kwargs: Any) -> Any:
    if _enabled and self.family not in _ALLOWED_FAMILIES:
        raise _deny("socket.connect_ex", _describe(address))
    return _real_connect_ex(self, address, *args, **kwargs)


def _guarded_create_connection(address: Any, *args: Any, **kwargs: Any) -> Any:
    if _enabled:
        raise _deny("socket.create_connection", _describe(address))
    return _real_create_connection(address, *args, **kwargs)


def _guarded_getaddrinfo(host: Any, port: Any, *args: Any, **kwargs: Any) -> Any:
    if _enabled:
        raise _deny("socket.getaddrinfo", f"{host}:{port}")
    return _real_getaddrinfo(host, port, *args, **kwargs)


def _install_psycopg2() -> None:
    """Patch ``psycopg2.connect``, which the socket patches cannot reach.

    libpq opens its socket in C, below the Python ``socket`` module, so a
    psycopg2 connection would sail straight past every patch above. Absence is
    tolerated: psycopg2 is a core dependency today, but the guard should not be
    the reason a slimmer install fails to collect.
    """
    try:
        import psycopg2
    except ImportError:  # pragma: no cover - psycopg2 is a core dependency
        return

    real_connect = psycopg2.connect

    def guarded(*args: Any, **kwargs: Any) -> Any:
        if _enabled:
            dsn = args[0] if args else kwargs.get("dsn", "<kwargs>")
            raise _deny("psycopg2.connect", str(dsn))
        return real_connect(*args, **kwargs)

    psycopg2.connect = guarded  # type: ignore[assignment]


def install() -> None:
    """Patch the outbound entry points. Idempotent; does not arm the guard."""
    global _installed
    if _installed:
        return
    socket.socket.connect = _guarded_connect  # type: ignore[method-assign]
    socket.socket.connect_ex = _guarded_connect_ex  # type: ignore[method-assign]
    socket.create_connection = _guarded_create_connection  # type: ignore[assignment]
    socket.getaddrinfo = _guarded_getaddrinfo  # type: ignore[assignment]
    _install_psycopg2()
    _installed = True


def enable() -> None:
    global _enabled
    _enabled = True


def disable() -> None:
    global _enabled
    _enabled = False


def is_enabled() -> bool:
    return _enabled


def set_current_test(nodeid: str | None) -> None:
    """Record the running test so a denial message can name it."""
    global _current_test
    _current_test = nodeid
