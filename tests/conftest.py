"""Shared fixtures for Amazing Irrigation tests."""

from __future__ import annotations

import sys

import pytest
import pytest_socket

pytest_plugins = "pytest_homeassistant_custom_component"

# On Windows, asyncio's ProactorEventLoop self-pipe uses an AF_INET
# ``socket.socketpair()``. The Home Assistant test harness disables sockets for
# every test (``disable_socket(allow_unix_socket=True)``), which blocks that
# AF_INET pair and prevents the event loop fixture from being created. On Linux
# the unix socketpair is allowed, so the network guard is left fully intact
# there; we only neutralise it on Windows so local development can run tests.
if sys.platform == "win32":
    pytest_socket.disable_socket = lambda *args, **kwargs: None  # type: ignore[assignment]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of the custom integration in every test."""
    yield
