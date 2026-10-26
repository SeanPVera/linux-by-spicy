# SPDX-License-Identifier: GPL-2.0-only
"""Keep failed/partial desktop probes distinct from visual acceptance."""
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import pytest


PATH = Path(__file__).resolve().parents[1] / "scripts/spicy-desktop-test"
LOADER = importlib.machinery.SourceFileLoader("desktop_test", str(PATH))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
TEST = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(TEST)


@pytest.fixture
def desktop(tmp_path, monkeypatch):
    helper = tmp_path / "candidate-helper"
    helper.write_text(f"#!{sys.executable}\nimport os,sys\nfrom pathlib import Path\nwith Path(os.environ['SPICY_TEST_THEMES']).open('a') as log: log.write(sys.argv[-1]+'\\n')\nsys.exit(int(os.environ.get('SPICY_TEST_APPLY_EXIT','0')))\n")
    helper.chmod(0o755)
    themes = tmp_path / "themes.txt"
    monkeypatch.setenv("SPICY_TEST_THEMES", str(themes))
    monkeypatch.setattr(TEST.os, "getuid", lambda: 1000)
    monkeypatch.setattr(TEST, "report_module", lambda: SimpleNamespace(__file__=str(PATH)))
    monkeypatch.setattr(TEST.time, "sleep", lambda _seconds: None)
    real_command = TEST.Run.command

    def command(run, label, argv, timeout=8):
        if argv[0] == str(helper):
            return real_command(run, label, argv, timeout)
        record = {"label": label, "argv": argv, "status": "returned", "returncode": 0}
        run.records.append(record)
        return record, ""

    monkeypatch.setattr(TEST.Run, "command", command)
    monkeypatch.setattr(TEST.Run, "snapshot", lambda *_args: True)
    return helper, themes


def test_blocked_desktop_access_never_changes_the_theme_or_captures(tmp_path, monkeypatch, desktop):
    helper, themes = desktop
    monkeypatch.setattr(TEST.Run, "snapshot", lambda *_args: False)
    monkeypatch.setattr(TEST.Run, "capture", lambda *_args: pytest.fail("capture after denied desktop access"))
    output = tmp_path / "blocked"
    assert TEST.main(["--output", str(output), "--cycle", "--capture", "--appearance", str(helper)]) == 2
    assert not themes.exists()
    report = json.loads((output / "report.json").read_text())
    assert report["outcome"] == "blocked_desktop_access_or_non_wayland_session"
    assert report["iso_identity"] is None
    assert report["visual_checks"] == "untested"


def test_cycle_records_real_helper_timing_and_never_claims_visual_pass(tmp_path, desktop):
    helper, themes = desktop
    output = tmp_path / "cycle"
    assert TEST.main(["--output", str(output), "--cycle", "--appearance", str(helper)]) == 0
    assert themes.read_text().splitlines() == ["daylight", "night-prowl", "daylight"]
    report = json.loads((output / "report.json").read_text())
    assert report["outcome"] == "cycle_commands_completed_visual_review_required"
    assert report["review_status"] == "unreviewed" and report["visual_checks"] == "untested"
    assert report["selected_appearance_helper"]["sha256"] == hashlib.sha256(helper.read_bytes()).hexdigest()
    calls = [r for r in report["commands"] if r["label"].endswith("-apply")]
    assert len(calls) == 3
    assert all(r["started_utc"] <= r["finished_utc"] and r["elapsed_seconds"] > 0 for r in calls)
    assert output.stat().st_mode & 0o777 == 0o700
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in output.iterdir())
    for evidence in report["evidence_files"]:
        assert evidence["sha256"] == hashlib.sha256((output / evidence["name"]).read_bytes()).hexdigest()
    with pytest.raises(SystemExit):
        TEST.main(["--output", str(output), "--cycle", "--appearance", str(helper)])
    assert themes.read_text().splitlines() == ["daylight", "night-prowl", "daylight"]


@pytest.mark.parametrize("exit_code", [1, 2])
def test_failed_or_partial_theme_request_stops_the_cycle(tmp_path, monkeypatch, desktop, exit_code):
    helper, themes = desktop
    monkeypatch.setenv("SPICY_TEST_APPLY_EXIT", str(exit_code))
    output = tmp_path / "partial"
    assert TEST.main(["--output", str(output), "--cycle", "--appearance", str(helper)]) == 1
    assert themes.read_text().splitlines() == ["daylight"]
    report = json.loads((output / "report.json").read_text())
    assert report["outcome"] == "cycle_incomplete" and report["visual_checks"] == "untested"


def test_probe_error_cannot_leave_a_successful_report(tmp_path, monkeypatch, desktop):
    def broken(*_args):
        raise ValueError("private input")

    monkeypatch.setattr(TEST.Run, "snapshot", broken)
    output = tmp_path / "error"
    assert TEST.main(["--output", str(output)]) == 1
    report = json.loads((output / "report.json").read_text())
    assert report["outcome"] == "execution_error" and report["exit_code"] == 1
    assert report["error_type"] == "ValueError"
    assert "private input" not in json.dumps(report)


def test_command_timeout_records_failure_and_releases_the_child(tmp_path):
    pidfile = tmp_path / "pid"
    output = tmp_path / "timing"
    output.mkdir()
    run = TEST.Run(output)
    original_handler = signal.getsignal(signal.SIGINT)
    record, _ = run.command("stall", [sys.executable, "-c",
                                     "import os,time; from pathlib import Path; "
                                     "Path('" + str(pidfile) + "').write_text(str(os.getpid())); time.sleep(60)"], timeout=0.5)
    assert record["status"] == "timeout"
    assert 0 < record["elapsed_seconds"] < 5
    assert record["started_utc"] <= record["finished_utc"]
    assert signal.getsignal(signal.SIGINT) is original_handler
    with pytest.raises(ProcessLookupError):
        os.kill(int(pidfile.read_text()), 0)


def test_fresh_window_capture_failure_cleans_up_only_its_own_process(tmp_path, monkeypatch):
    output = tmp_path / "window"
    output.mkdir()
    run = TEST.Run(output)
    real_popen = subprocess.Popen
    created = []

    def own_child(argv, **kwargs):
        child = real_popen([sys.executable, "-c", "import time; time.sleep(60)"], **kwargs)
        created.append(child)
        return child

    monkeypatch.setattr(TEST.subprocess, "Popen", own_child)
    monkeypatch.setattr(TEST.time, "sleep", lambda _seconds: None)

    def capture_failure(*_args):
        raise KeyboardInterrupt

    monkeypatch.setattr(run, "capture", capture_failure)
    with pytest.raises(KeyboardInterrupt):
        run.fresh_konsole("new-window")
    assert len(created) == 1 and created[0].returncode in (-signal.SIGTERM, -signal.SIGKILL)
    assert run.records[-1]["returncode_after_cleanup"] == created[0].returncode


def test_helper_fingerprint_rejects_special_files_without_opening_them(tmp_path):
    fifo = tmp_path / "helper-fifo"
    os.mkfifo(fifo)
    assert TEST.fingerprint(fifo)["status"] == "not_regular_file"


def test_exited_fresh_window_leader_does_not_leave_its_descendant(tmp_path, monkeypatch):
    output = tmp_path / "exited-window"
    output.mkdir()
    pidfile = tmp_path / "window-processes.json"
    real_popen = subprocess.Popen
    created = []
    script = ("import json,os,subprocess,sys; from pathlib import Path; "
              "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
              f"Path({str(pidfile)!r}).write_text(json.dumps(dict(leader=os.getpid(),descendant=child.pid)))")

    def owned_probe(_argv, **options):
        child = real_popen([sys.executable, "-c", script], **options)
        created.append(child)
        return child

    def wait_for_exit(_seconds):
        if _seconds < 1:
            threading.Event().wait(_seconds)
            return
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            try:
                leader = json.loads(pidfile.read_text())["leader"]
                if Path(f"/proc/{leader}/stat").read_text().split()[2] == "Z":
                    return
            except (OSError, ValueError, KeyError):
                pass
            threading.Event().wait(.01)
        pytest.fail("Fresh-window probe did not reach the exited-parent fixture")

    monkeypatch.setattr(TEST.subprocess, "Popen", owned_probe)
    monkeypatch.setattr(TEST.time, "sleep", wait_for_exit)
    run = TEST.Run(output)
    try:
        assert not run.fresh_konsole("exited-probe")
        assert created[0].returncode == 0
        descendant = json.loads(pidfile.read_text())["descendant"]
        status = Path(f"/proc/{descendant}/stat")
        assert not status.exists() or status.read_text().split()[2] == "Z"
    finally:
        if pidfile.exists():
            descendant = json.loads(pidfile.read_text())["descendant"]
            try:
                os.kill(descendant, signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_failed_capture_blocks_the_cycle_before_any_theme_write(tmp_path, monkeypatch, desktop):
    helper, themes = desktop
    monkeypatch.setattr(TEST.Run, "capture", lambda *_args: False)
    output = tmp_path / "no-capture"
    assert TEST.main(["--output", str(output), "--cycle", "--capture", "--appearance", str(helper)]) == 2
    assert not themes.exists()
    assert json.loads((output / "report.json").read_text())["outcome"] == "blocked_capture"


def test_failed_apply_skips_fresh_window_probe(tmp_path, monkeypatch, desktop):
    helper, _themes = desktop
    monkeypatch.setenv("SPICY_TEST_APPLY_EXIT", "2")
    monkeypatch.setattr(TEST.Run, "capture", lambda *_args: True)
    monkeypatch.setattr(TEST.Run, "fresh_konsole", lambda *_args: pytest.fail("fresh process after failed apply"))
    assert TEST.main(["--output", str(tmp_path / "no-fresh-window"), "--cycle", "--capture",
                      "--fresh-konsole", "--appearance", str(helper)]) == 1


def test_snapshot_does_not_accept_dbus_alone_when_display_access_failed(tmp_path, monkeypatch):
    output = tmp_path / "no-display"
    output.mkdir()
    run = TEST.Run(output)
    monkeypatch.setenv("WAYLAND_DISPLAY", "actual-session-display")
    report = TEST.report_module()
    monkeypatch.setattr(report, "appearance", lambda: {})

    def command(label, argv, timeout=8):
        if argv[0] == "kscreen-doctor":
            return {"returncode": 1}, ""
        return {"returncode": 0}, "Operation Mode: Wayland\n"

    monkeypatch.setattr(run, "command", command)
    assert not run.snapshot("probe", report, "qdbus6")


def test_timeout_releases_a_child_and_its_descendant(tmp_path):
    output = tmp_path / "descendants"
    output.mkdir()
    pidfile = tmp_path / "descendant.pid"
    script = ("import subprocess,sys,time; from pathlib import Path; "
              "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
              f"Path({str(pidfile)!r}).write_text(str(child.pid)); time.sleep(60)")
    record, _ = TEST.Run(output).command("tree", [sys.executable, "-c", script], timeout=1)
    assert record["status"] == "timeout"
    pid = int(pidfile.read_text())
    status = Path(f"/proc/{pid}/stat")
    # An orphan can remain a zombie until the container's init reaps it.
    assert not status.exists() or status.read_text().split()[2] == "Z"


def test_interrupted_command_is_recorded_and_reaped(tmp_path, monkeypatch):
    output = tmp_path / "interrupted"
    output.mkdir()
    real_popen = subprocess.Popen
    children = []

    def interruptible(argv, **kwargs):
        child = real_popen(argv, **kwargs)
        children.append(child)
        communicate = child.communicate
        calls = []

        def interrupted(*args, **options):
            if not calls:
                calls.append(True)
                raise KeyboardInterrupt
            return communicate(*args, **options)

        child.communicate = interrupted
        return child

    monkeypatch.setattr(TEST.subprocess, "Popen", interruptible)
    run = TEST.Run(output)
    with pytest.raises(KeyboardInterrupt):
        run.command("interrupt", [sys.executable, "-c", "import time; time.sleep(60)"])
    assert children[0].returncode is not None
    assert run.records[-1]["status"] == "interrupted"
    assert run.records[-1]["started_utc"] <= run.records[-1]["finished_utc"]


def test_real_sigint_cleans_descendant_after_its_leader_has_exited(tmp_path, monkeypatch):
    output = tmp_path / "real-interrupt"
    output.mkdir()
    pidfile = tmp_path / "processes.json"
    script = ("import json,os,subprocess,sys; from pathlib import Path; "
              "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
              f"Path({str(pidfile)!r}).write_text(json.dumps(dict(leader=os.getpid(),descendant=child.pid)))")
    original_handler = signal.getsignal(signal.SIGINT)
    real_popen = subprocess.Popen
    communicating = threading.Event()
    finished = threading.Event()
    sent = threading.Event()

    def observed_popen(argv, **options):
        child = real_popen(argv, **options)
        communicate = child.communicate

        def observed_communicate(*args, **kwargs):
            communicating.set()
            return communicate(*args, **kwargs)

        child.communicate = observed_communicate
        return child

    def interrupt_after_exit():
        deadline = time.monotonic() + 4
        while not finished.wait(0.01) and time.monotonic() < deadline:
            try:
                leader = json.loads(pidfile.read_text())["leader"]
                state = Path(f"/proc/{leader}/stat").read_text().split()[2]
            except (OSError, ValueError, KeyError):
                continue
            if communicating.is_set() and state == "Z":
                sent.set()
                os.kill(os.getpid(), signal.SIGINT)
                return

    monkeypatch.setattr(TEST.subprocess, "Popen", observed_popen)
    interrupter = threading.Thread(target=interrupt_after_exit, daemon=True)
    run = TEST.Run(output)
    interrupter.start()
    try:
        with pytest.raises(KeyboardInterrupt):
            run.command("interrupt-tree", [sys.executable, "-c", script], timeout=6)
        assert sent.is_set()
        assert signal.getsignal(signal.SIGINT) is original_handler
        assert run.records[-1]["status"] == "interrupted"
        assert run.records[-1]["returncode_after_cleanup"] == 0
        descendant = json.loads(pidfile.read_text())["descendant"]
        status = Path(f"/proc/{descendant}/stat")
        assert not status.exists() or status.read_text().split()[2] == "Z"
    finally:
        finished.set()
        interrupter.join(timeout=5)
        if pidfile.exists():
            descendant = json.loads(pidfile.read_text())["descendant"]
            try:
                os.kill(descendant, signal.SIGKILL)
            except ProcessLookupError:
                pass
