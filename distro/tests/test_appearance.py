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
if name == 'dbus-send' and '--type=signal' in sys.argv and os.environ.get('SPICY_TEST_FAIL_SIGNAL'):
    sys.exit(1)
if name == os.environ.get('SPICY_TEST_STALL'):
    time.sleep(60)
if name == 'kwriteconfig6' and sys.argv[2] == 'Kvantum/kvantum.kvconfig':
    Path(os.environ['SPICY_TEST_KVANTUM']).write_text(sys.argv[-1])
if name == 'plasma-apply-lookandfeel':
    # KDE's StyleChanged handler recreates the Qt style during application of
    # look-and-feel. Kvantum reads the currently saved selection at that point.
    selection = Path(os.environ['SPICY_TEST_KVANTUM'])
    with open(os.environ['SPICY_TEST_STYLE_LOG'], 'a') as style_log:
        style_log.write(json.dumps(selection.read_text() if selection.exists() else None) + '\\n')
"""
    for name in ("kwriteconfig6", "plasma-apply-lookandfeel", "plasma-apply-colorscheme", "plasma-apply-cursortheme", "dbus-send"):
        path = tools / name
        path.write_text(script)
        path.chmod(0o755)
    log = tmp_path / "calls.jsonl"
    monkeypatch.setenv("PATH", str(tools) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("SPICY_TEST_LOG", str(log))
    monkeypatch.setenv("SPICY_TEST_KVANTUM", str(tmp_path / "kvantum-theme"))
    monkeypatch.setenv("SPICY_TEST_STYLE_LOG", str(tmp_path / "style-reloads.jsonl"))
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
    assert all("--reply-timeout=3000" in action for action in actions[first_refresh:] if "--type=signal" not in action)
    assert not any("--resetLayout" in action for action in actions)


def test_busy_shell_preserves_saved_state_and_attempts_kwin_refresh(appearance, monkeypatch):
    script, log = appearance
    monkeypatch.setenv("SPICY_TEST_FAIL", "dbus-send")
    assert script.apply(script.commands("daylight")) == 2
    actions = calls(log)
    assert any("Theme" in action and action[-1] == "daylight" for action in actions if action[0] == "kwriteconfig6")
    refresh = [action for action in actions if action[0] == "dbus-send"]
    assert [next(arg for arg in action if arg.startswith("--dest=")) for action in refresh if "--type=signal" not in action] == ["--dest=org.kde.plasmashell", "--dest=org.kde.KWin"]
    assert any("org.kde.KGlobalSettings.notifyChange" in action for action in refresh)


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
    assert not any(action[0] == "dbus-send" or "spicyrc" in action for action in calls(log))


def test_style_reload_observes_each_new_kvantum_selection(appearance):
    script, _log = appearance
    for theme in ("daylight", "night-prowl", "daylight"):
        assert script.apply(script.commands(theme)) == 0
    observed = Path(os.environ["SPICY_TEST_STYLE_LOG"]).read_text().splitlines()
    assert [json.loads(value) for value in observed] == ["SpicyDaylight", "SpicyNightProwl", "SpicyDaylight"]


def test_failed_kvantum_selection_stops_before_broadcasting_or_saving_preferences(appearance, monkeypatch):
    script, log = appearance
    monkeypatch.setenv("SPICY_TEST_FAIL", "kwriteconfig6")
    assert script.apply(script.commands("daylight")) == 1
    assert len(calls(log)) == 1
    assert calls(log)[0][2] == "Kvantum/kvantum.kvconfig"


def test_cursor_change_is_broadcast_after_saved_configuration_even_when_tools_succeed(appearance):
    script, log = appearance
    # The real cursor helper can exit zero without emitting CursorChanged when
    # look-and-feel has already saved the requested theme.
    assert script.apply(script.commands("daylight")) == 0
    actions = calls(log)
    signal = ["dbus-send", "--session", "--type=signal", "/KGlobalSettings",
              "org.kde.KGlobalSettings.notifyChange", "int32:5", "int32:0"]
    assert actions.count(signal) == 1
    cursor_apply = next(i for i, action in enumerate(actions) if action[0] == "plasma-apply-cursortheme")
    saved_theme = next(i for i, action in enumerate(actions) if "spicyrc" in action and "Theme" in action)
    assert cursor_apply < saved_theme < actions.index(signal)


def test_cursor_notification_failure_reports_saved_state_and_still_refreshes_shell_and_kwin(appearance, monkeypatch):
    script, log = appearance
    monkeypatch.setenv("SPICY_TEST_FAIL_SIGNAL", "1")
    assert script.apply(script.commands("daylight")) == 2
    actions = calls(log)
    assert any("spicyrc" in action and "Theme" in action and action[-1] == "daylight" for action in actions)
    assert [next(arg for arg in action if arg.startswith("--dest=")) for action in actions if action[0] == "dbus-send" and "--type=signal" not in action] == ["--dest=org.kde.plasmashell", "--dest=org.kde.KWin"]


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


def test_commands_rejects_unsupported_theme(appearance):
    script, _log = appearance
    with pytest.raises(ValueError, match="Unsupported theme"):
        script.commands("invalid-theme")


