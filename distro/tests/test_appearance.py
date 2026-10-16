# SPDX-License-Identifier: GPL-2.0-only
"""Exercise appearance failure handling with real, disposable child processes."""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    loader = importlib.machinery.SourceFileLoader(name.replace("-", "_"), str(ROOT / "scripts" / name))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture
def appearance(tmp_path, monkeypatch):
    tools = tmp_path / "bin"
    tools.mkdir()
    script = f"""#!{sys.executable}
import json, os, sys, time
from pathlib import Path
name = Path(sys.argv[0]).name
with open(os.environ['SPICY_TEST_LOG'], 'a') as log:
    log.write(json.dumps([name] + sys.argv[1:]) + '\\n')
if name == os.environ.get('SPICY_TEST_FAIL'):
    sys.exit(1)
if name == os.environ.get('SPICY_TEST_STALL'):
    time.sleep(60)
"""
    for name in ("kwriteconfig6", "plasma-apply-lookandfeel", "plasma-apply-colorscheme", "plasma-apply-cursortheme", "dbus-send"):
        path = tools / name
        path.write_text(script)
        path.chmod(0o755)
    log = tmp_path / "calls.jsonl"
    monkeypatch.setenv("PATH", str(tools) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("SPICY_TEST_LOG", str(log))
    return load_script("spicy-appearance"), log


def calls(log):
    return [json.loads(line) for line in log.read_text().splitlines()]


def test_theme_and_motion_complete_before_live_refresh(appearance):
    script, log = appearance
    assert script.apply(script.commands("night-prowl", True)) == 0
    actions = calls(log)
    first_refresh = next(i for i, action in enumerate(actions) if action[0] == "dbus-send")
    assert all(action[0] == "dbus-send" for action in actions[first_refresh:])
    assert any("AnimationDurationFactor" in action and action[-1] == "0" for action in actions[:first_refresh])
    assert all("--reply-timeout=3000" in action for action in actions[first_refresh:])
    assert not any("--resetLayout" in action for action in actions)


def test_busy_shell_preserves_saved_state_and_attempts_kwin_refresh(appearance, monkeypatch):
    script, log = appearance
    monkeypatch.setenv("SPICY_TEST_FAIL", "dbus-send")
    assert script.apply(script.commands("daylight")) == 2
    actions = calls(log)
    assert any("Theme" in action and action[-1] == "daylight" for action in actions if action[0] == "kwriteconfig6")
    refresh = [action for action in actions if action[0] == "dbus-send"]
    assert [next(arg for arg in action if arg.startswith("--dest=")) for action in refresh] == ["--dest=org.kde.plasmashell", "--dest=org.kde.KWin"]


def test_reduced_motion_refreshes_kwin_without_touching_wallpaper(appearance):
    script, log = appearance
    assert script.apply(script.commands(reduced=True)) == 0
    actions = calls(log)
    assert not any(action[0].startswith("plasma-apply-") for action in actions)
    refresh = [action for action in actions if action[0] == "dbus-send"]
    assert len(refresh) == 1 and "--dest=org.kde.KWin" in refresh[0]


def test_required_tool_failure_is_not_reported_as_saved(appearance, monkeypatch):
    script, log = appearance
    monkeypatch.setenv("SPICY_TEST_FAIL", "plasma-apply-colorscheme")
    assert script.apply(script.commands("night-prowl")) == 1
    assert not any(action[0] in ("kwriteconfig6", "dbus-send") for action in calls(log))


@pytest.mark.parametrize("program, expected", [("plasma-apply-lookandfeel", 1), ("dbus-send", 2)])
def test_stalled_tools_return_and_release_their_child_processes(appearance, monkeypatch, program, expected):
    script, _log = appearance
    children = []
    popen = script.subprocess.Popen

    def track_child(*args, **kwargs):
        child = popen(*args, **kwargs)
        children.append(child)
        return child

    # Record PIDs in the parent: interpreter startup can itself exceed the
    # short test timeout on a busy image builder, before a child writes a log.
    monkeypatch.setattr(script.subprocess, "Popen", track_child)
    monkeypatch.setenv("SPICY_TEST_STALL", program)
    if program == "plasma-apply-lookandfeel":
        monkeypatch.setattr(script, "COMMAND_TIMEOUT", .5)
    monkeypatch.setattr(script, "REFRESH_TIMEOUT", .5)
    start = time.monotonic()
    assert script.apply(script.commands("daylight")) == expected
    assert time.monotonic() - start < 15
    assert any(child.args[0] == program and child.returncode < 0 for child in children)
    for child in children:
        with pytest.raises(ProcessLookupError):
            os.kill(child.pid, 0)

