# SPDX-License-Identifier: GPL-2.0-only
"""Check the real Qt process lifecycle, including retries after failures."""
import importlib.machinery
import importlib.util
from pathlib import Path
import sys
import time

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QProcess

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def app():
    return QCoreApplication.instance() or QCoreApplication([])


@pytest.fixture
def welcome(tmp_path, monkeypatch, app):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    tools = tmp_path / "bin"
    tools.mkdir()
    monkeypatch.setenv("PATH", str(tools))
    path = tools / "spicy-appearance"
    loader = importlib.machinery.SourceFileLoader("spicy_welcome_process_test", str(ROOT / "scripts/spicy-welcome"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    backend = module.Backend()
    yield backend, path
    if backend.process is not None:
        backend.process.kill()
        backend.process.waitForFinished(1000)
    backend.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def tool(path, code=0, crash=False):
    body = "import os, signal; os.kill(os.getpid(), signal.SIGKILL)" if crash else f"import sys; sys.exit({code})"
    path.write_text(f"#!{sys.executable}\n{body}\n")
    path.chmod(0o755)


def finish(app, backend):
    deadline = time.monotonic() + 3
    while backend.busy and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.005)
    assert not backend.busy, "Welcome remained busy after the child process ended"
    assert backend.process is None
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    assert not backend.findChildren(QProcess), "A completed request retained its process"


def test_saved_preference_is_shown_when_desktop_refresh_is_pending(welcome, app):
    backend, path = welcome
    tool(path, code=2)
    backend.setTheme("night-prowl")
    finish(app, backend)
    assert backend.currentTheme == "night-prowl"
    assert "Try again when the desktop is responding" in backend.status
    backend.setReducedMotion(True)
    finish(app, backend)
    assert backend.reducedMotion
    tool(path)
    backend.setTheme("daylight")
    finish(app, backend)
    assert backend.currentTheme == "daylight"
    assert backend.status == "Your desktop is ready."


@pytest.mark.parametrize("failure", ["exit", "crash", "missing"])
def test_failure_releases_busy_state_and_allows_a_successful_retry(welcome, app, failure):
    backend, path = welcome
    if failure != "missing":
        tool(path, code=1, crash=failure == "crash")
    backend.setTheme("night-prowl")
    finish(app, backend)
    assert backend.currentTheme == "daylight"
    assert "Couldn't" in backend.status
    tool(path)
    backend.setTheme("night-prowl")
    finish(app, backend)
    assert backend.currentTheme == "night-prowl"
    assert backend.status == "Your desktop is ready."
