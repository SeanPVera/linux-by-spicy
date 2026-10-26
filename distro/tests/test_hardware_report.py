# SPDX-License-Identifier: GPL-2.0-only
"""Exercise evidence integrity, privacy boundaries and degraded tool availability."""
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/spicy-hardware-report"
LOADER = importlib.machinery.SourceFileLoader("hardware_report", str(SCRIPT))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
REPORT = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(REPORT)


class HardwareReportTests(unittest.TestCase):
    def invoke(self, *args):
        # Executing with no ancillary commands models a minimal/unready live session.
        env = os.environ.copy()
        env["PATH"] = ""
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], env=env, capture_output=True, text=True, check=False)

    def test_computed_image_and_missing_commands_never_claim_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            iso = root / "exact-image.iso"
            iso.write_bytes(b"test-only image; not a bootable ISO")
            digest = hashlib.sha256(iso.read_bytes()).hexdigest()
            result = self.invoke("--iso", iso, "--expected-sha256", digest, "--kind", "vm", "--label", "test-run", "--output", root / "report")
            self.assertEqual(result.returncode, 0, result.stderr)
            observations = json.loads((root / "report/observations.json").read_text())
            matrix = json.loads((root / "report/results.json").read_text())
            self.assertEqual(observations["image"]["sha256"], digest)
            self.assertTrue(observations["image"]["expected_digest_matches"])
            self.assertFalse(observations["image"]["boot_origin_confirmed"])
            self.assertEqual(observations["diagnostics"]["graphics"]["kwin"]["status"], "missing_command")
            self.assertEqual(observations["diagnostics"]["graphics"]["kwin_process_environment"]["status"], "missing_command")
            self.assertEqual(observations["diagnostics"]["graphics"]["kwin"]["cursor"]["status"], "missing_command")
            self.assertEqual(observations["diagnostics"]["appearance"]["settings"]["kvantum_theme"]["status"], "missing_command")
            self.assertEqual(observations["diagnostics"]["peripherals"]["network_manager"]["status"], "missing_command")
            self.assertEqual(len(matrix["scaling"]), 80)
            self.assertIn([3840, 2160], [case["resolution"] for case in matrix["scaling"]])
            self.assertEqual({case["status"] for case in matrix["tests"] + matrix["scaling"]}, {"untested"})
            self.assertEqual((root / "report").stat().st_mode & 0o777, 0o700)
            self.assertEqual((root / "report/results.json").stat().st_mode & 0o777, 0o600)
            # A repeat run cannot replace evidence or reset recorded outcomes.
            repeat = self.invoke("--iso", iso, "--kind", "vm", "--label", "replacement", "--output", root / "report")
            self.assertEqual(repeat.returncode, 2)
            self.assertEqual(json.loads((root / "report/results.json").read_text())["run_label"], "test-run")

    def test_checksum_mismatch_stops_before_collecting_or_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            iso = root / "image.iso"
            iso.write_bytes(b"unexpected image")
            result = self.invoke("--iso", iso, "--expected-sha256", "0" * 64, "--kind", "physical", "--label", "test", "--output", root / "report")
            self.assertEqual(result.returncode, 2)
            self.assertIn("differs", result.stderr)
            self.assertFalse((root / "report").exists())

    def test_supplied_digest_is_distinct_from_computed_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.invoke("--iso-sha256", "A" * 64, "--image-name", "exact-image.iso", "--kind", "vm", "--label", "guest", "--output", Path(directory) / "report")
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads((Path(directory) / "report/observations.json").read_text())
            self.assertEqual(data["image"]["digest_source"], "supplied_by_tester")
            self.assertIsNone(data["image"]["expected_digest_matches"])
            self.assertFalse(data["image"]["boot_origin_confirmed"])

    def test_empty_or_invalid_digest_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for digest in ("", "xyz", "f" * 63):
                result = self.invoke("--iso-sha256", digest, "--image-name", "image.iso", "--kind", "vm", "--label", "guest", "--output", Path(directory) / "report")
                self.assertEqual(result.returncode, 2)

    def test_failed_command_and_timeout_do_not_leak_raw_error_output(self):
        with patch.object(REPORT.shutil, "which", return_value=sys.executable):
            probe, output = REPORT.command(["python3", "-c", "import sys; print('private-network'); sys.stderr.write('/home/private-user'); sys.exit(4)"])
            self.assertEqual(probe["status"], "failed")
            self.assertIsNone(output)
            self.assertNotIn("private", json.dumps(probe))
            probe, output = REPORT.command(["python3", "-c", "import time; time.sleep(1)"], timeout=0.01)
            self.assertEqual(probe["status"], "timeout")
            self.assertIsNone(output)

    def test_display_diagnostics_drop_edid_and_serials(self):
        raw = {"outputs": [{"id": 1, "name": "DP-1", "scale": 1.25, "connected": True, "enabled": True, "edid": "private-edid", "serial": "private-serial", "hash": "private-hash", "currentModeId": "0", "modes": [{"id": "0", "name": "private-display-name", "size": {"width": 3840, "height": 2160}, "refreshRate": 60}]}]}
        with patch.object(REPORT, "command", return_value=({"status": "ok"}, json.dumps(raw))):
            data = REPORT.displays()
        self.assertEqual(data["outputs"][0]["scale"], 1.25)
        self.assertEqual(data["outputs"][0]["modes"][0]["size"]["width"], 3840)
        self.assertNotIn("private", json.dumps(data))

    def test_kwin_diagnostics_only_keep_renderer_allowlist(self):
        source = "OpenGL renderer string: llvmpipe\nCompositing Type: OpenGL\nHostname: private-host\nUser: private-user\nEDID: private-edid\n"
        fields = REPORT.selected_lines(source, REPORT.KWIN_FIELDS)
        self.assertEqual(fields["OpenGL renderer string"], "llvmpipe")
        self.assertNotIn("private", json.dumps(fields))

    def test_appearance_queries_keep_only_typed_allowlisted_values(self):
        values = ("SpicyDaylight\n", "kvantum\n", "SpicyDaylight\n", "SpicyLittleTip\n", "24\n", "\n", "night-prowl\n", "true\n")
        replies = [({"status": "ok", "command": "kreadconfig6", "returncode": 0}, value) for value in values]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private-source-path"
            path.write_bytes(b"installed helper bytes")
            with patch.object(REPORT, "command", side_effect=replies) as probe, \
                    patch.object(REPORT, "INSTALLED_APPEARANCE_FILES", {"appearance_helper": path}):
                data = REPORT.appearance()
        settings = data["settings"]
        self.assertEqual(settings["kvantum_theme"]["value"], "SpicyDaylight")
        self.assertEqual(settings["widget_style"]["value"], "kvantum")
        self.assertEqual(settings["cursor_theme"]["value"], "SpicyLittleTip")
        self.assertEqual(settings["cursor_size"]["value"], 24)
        self.assertEqual(settings["konsole_color_scheme"]["status"], "not_configured")
        self.assertEqual(settings["spicy_theme"]["value"], "night-prowl")
        self.assertIs(settings["reduced_motion"]["value"], True)
        self.assertEqual(data["installed_files"]["appearance_helper"]["sha256"], hashlib.sha256(b"installed helper bytes").hexdigest())
        self.assertEqual(len(probe.call_args_list), 8)
        for call, (_, filename, group, key) in zip(probe.call_args_list, REPORT.APPEARANCE_QUERIES):
            self.assertEqual(call.args[0], ["kreadconfig6", "--file", filename, "--group", group, "--key", key])
            self.assertEqual(call.kwargs["accepted"], (0, 1))
        self.assertNotIn("private", json.dumps(data))

    def test_appearance_failed_probes_and_invalid_values_cannot_leak_config(self):
        replies = [
            ({"status": "missing_command"}, None),
            ({"status": "timeout", "timeout_seconds": 8}, None),
            ({"status": "failed", "returncode": 2}, None),
            ({"status": "partial", "returncode": 1}, ""),
            ({"status": "ok", "returncode": 0}, "999"),
            ({"status": "ok", "returncode": 0}, "/home/private-user/scheme"),
            ({"status": "partial", "returncode": 1}, ""),
            ({"status": "ok", "returncode": 0}, "private-user"),
        ]
        with patch.object(REPORT, "command", side_effect=replies), \
                patch.object(REPORT, "INSTALLED_APPEARANCE_FILES", {}):
            data = REPORT.appearance()
        self.assertEqual([probe["status"] for probe in data["settings"].values()],
                         ["missing_command", "timeout", "failed", "not_configured", "invalid_output", "invalid_output", "not_configured", "invalid_output"])
        self.assertNotIn("private", json.dumps(data))
        for value in ("private-user\nOtherKey=secret", "x" * 129, "invalid/secret", "nonascii-\u2603"):
            with self.subTest(value=value), \
                    patch.object(REPORT, "command", return_value=({"status": "ok", "returncode": 0}, value)), \
                    patch.object(REPORT, "INSTALLED_APPEARANCE_FILES", {}):
                data = REPORT.appearance()
            self.assertEqual({p["status"] for p in data["settings"].values()}, {"invalid_output"})
            self.assertFalse(any("value" in p for p in data["settings"].values()))
        with patch.object(REPORT, "command", return_value=({"status": "partial", "returncode": 1}, "private-user")), \
                patch.object(REPORT, "INSTALLED_APPEARANCE_FILES", {}):
            data = REPORT.appearance()
        self.assertEqual({p["status"] for p in data["settings"].values()}, {"invalid_output"})
        self.assertNotIn("private", json.dumps(data))

    def test_cursor_section_must_be_present_and_not_spoofed_by_other_sections(self):
        source = "Effects\n=======\nthemeName: private-name\nthemeSize: 999\n\nCursor\n======\nthemeName: SpicyLittleTip\nthemeSize: 24\n\nOther\n=====\nthemeName: private-name\nthemeSize: 999\n"
        data = REPORT.kwin_cursor(source)
        self.assertEqual(data, {"status": "ok", "themeName": "SpicyLittleTip", "themeSize": 24, "omitted_invalid_fields": []})
        self.assertEqual(REPORT.kwin_cursor("Effects\n=======\nthemeName: SpicyLittleTip\n"), {"status": "not_reported"})
        data = REPORT.kwin_cursor("Cursor\n======\nthemeName: /home/private-user\nthemeSize: 999\n")
        self.assertEqual(data["status"], "partial")
        self.assertEqual(data["omitted_invalid_fields"], ["themeName", "themeSize"])
        self.assertNotIn("private", json.dumps(data))
        self.assertEqual(REPORT.kwin_cursor("Cursor\n======\nthemeName: breeze_cursors\n")["status"], "partial")

    def test_installed_hashes_preserve_bytes_and_refuse_links_or_special_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            regular = root / "helper"
            regular.write_bytes(b"installed bytes")
            data = REPORT.installed_file_hash(regular)
            self.assertEqual(data, {"status": "ok", "size_bytes": 15, "sha256": hashlib.sha256(b"installed bytes").hexdigest()})
            link = root / "link"
            link.symlink_to(regular)
            fifo = root / "fifo"
            os.mkfifo(fifo)
            for path in (link, fifo, root):
                with self.subTest(path=path), patch.object(REPORT.os, "open") as opened:
                    self.assertEqual(REPORT.installed_file_hash(path), {"status": "not_regular_file"})
                    opened.assert_not_called()

    def test_installed_hash_limits_access_and_changes_stay_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private-path"
            self.assertEqual(REPORT.installed_file_hash(path), {"status": "missing_file"})
            path.write_bytes(b"oversized")
            self.assertEqual(REPORT.installed_file_hash(path, limit=2), {"status": "too_large"})
            with patch.object(REPORT.os, "open", side_effect=PermissionError("private-error")):
                data = REPORT.installed_file_hash(path)
            self.assertEqual(data, {"status": "unreadable"})
            self.assertNotIn("private", json.dumps(data))
            before = path.stat()
            after = SimpleNamespace(st_size=before.st_size, st_mtime_ns=before.st_mtime_ns + 1)
            with patch.object(REPORT.os, "fstat", side_effect=[before, after]):
                self.assertEqual(REPORT.installed_file_hash(path), {"status": "changed_during_read"})

    def test_collector_overrides_are_distinct_from_kwin_process_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            process = Path(directory) / "123"
            process.mkdir()
            (process / "comm").write_text("kwin_wayland\n")
            (process / "environ").write_bytes(b"KWIN_COMPOSE=Q\0USER=private-user\0HOME=/home/private-user\0QT_QUICK_BACKEND=/home/private-value\0")

            def probe(argv, **kwargs):
                output = ("123\n" if "org.freedesktop.DBus.GetConnectionUnixProcessID" in argv
                          else "OpenGL renderer string: llvmpipe\n" if argv[0] != "kscreen-doctor"
                          else '{"outputs": []}')
                return {"status": "ok", "command": argv[0]}, output

            process_probe = REPORT.kwin_process_environment
            with patch.object(REPORT, "command", side_effect=probe), \
                    patch.object(REPORT.shutil, "which", side_effect=lambda name: name), \
                    patch.object(REPORT, "kwin_process_environment", side_effect=lambda qdbus: process_probe(qdbus, Path(directory))), \
                    patch.dict(REPORT.os.environ, {"LIBGL_ALWAYS_SOFTWARE": "1", "USER": "private-user"}, clear=True):
                data = REPORT.graphics()
            self.assertEqual(data["renderer_overrides"], {"LIBGL_ALWAYS_SOFTWARE": "1"})
            self.assertIn("Collector process", data["renderer_overrides_scope"])
            kwin = data["kwin_process_environment"]
            self.assertEqual(kwin["status"], "partial")
            self.assertEqual(kwin["variables"], {"KWIN_COMPOSE": "Q"})
            self.assertEqual(kwin["omitted_invalid_values"], ["QT_QUICK_BACKEND"])
            self.assertNotIn("private", json.dumps(data))

    def test_kwin_environment_unavailable_pid_probes_stay_explicit(self):
        for status in ("missing_command", "failed", "timeout"):
            with self.subTest(status=status), patch.object(REPORT, "command", return_value=({"status": status}, None)):
                data = REPORT.kwin_process_environment("qdbus6")
            self.assertEqual(data["status"], status)
            self.assertEqual(data["variables"], {})
        with patch.object(REPORT, "command", return_value=({"status": "ok"}, "/home/private-user")):
            data = REPORT.kwin_process_environment("qdbus6")
        self.assertEqual(data["status"], "invalid_pid")
        self.assertNotIn("private", json.dumps(data))

    def test_kwin_environment_missing_or_unreadable_process_is_not_an_empty_success(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(REPORT, "command", return_value=({"status": "ok"}, "123")):
            root = Path(directory)
            self.assertEqual(REPORT.kwin_process_environment("qdbus6", root)["status"], "process_unavailable")
            process = root / "123"
            process.mkdir()
            (process / "comm").write_text("kwin_wayland\n")
            with patch.object(REPORT.Path, "open", side_effect=PermissionError("/home/private-user/environ")):
                data = REPORT.kwin_process_environment("qdbus6", root)
            self.assertEqual(data["status"], "unreadable")
            self.assertEqual(data["variables"], {})
            self.assertNotIn("private", json.dumps(data))

    def test_kwin_environment_refuses_another_user_or_unexpected_process(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(REPORT, "command", return_value=({"status": "ok"}, "123")):
            root = Path(directory)
            process = root / "123"
            process.mkdir()
            (process / "comm").write_text("private-process\n")
            (process / "environ").write_bytes(b"KWIN_COMPOSE=Q\0")
            uid = os.getuid()
            with patch.object(REPORT.os, "getuid", return_value=uid + 1):
                self.assertEqual(REPORT.kwin_process_environment("qdbus6", root)["status"], "different_user")
            data = REPORT.kwin_process_environment("qdbus6", root)
            self.assertEqual(data["status"], "unexpected_process")
            self.assertEqual(data["variables"], {})
            self.assertNotIn("private", json.dumps(data))

    def test_kwin_environment_bounded_reads_and_absent_overrides(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(REPORT, "command", return_value=({"status": "ok"}, "123")):
            root = Path(directory)
            process = root / "123"
            process.mkdir()
            (process / "comm").write_text("kwin_x11\n")
            (process / "environ").write_bytes(b"USER=private-user\0")
            data = REPORT.kwin_process_environment("qdbus6", root)
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["variables"], {})
            (process / "environ").write_bytes(b"KWIN_COMPOSE=Q\0" + b"x" * 131072)
            data = REPORT.kwin_process_environment("qdbus6", root)
            self.assertEqual(data["status"], "too_large")
            self.assertEqual(data["variables"], {})

    def test_firmware_variable_format_and_access_failure_remain_explicit(self):
        with patch.object(REPORT.Path, "read_bytes", return_value=b"\x07\x00\x00\x00\x01"):
            self.assertEqual(REPORT.read_efi_variable("SecureBoot"), {"status": "ok", "value": 1})
        with patch.object(REPORT.Path, "read_bytes", return_value=b"\x01"):
            self.assertEqual(REPORT.read_efi_variable("SecureBoot")["status"], "invalid_data")
        with patch.object(REPORT.Path, "read_bytes", side_effect=PermissionError):
            self.assertEqual(REPORT.read_efi_variable("SecureBoot")["status"], "unreadable")

    def test_vm_profile_rejects_private_extra_fields_and_invalid_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            path.write_text(json.dumps({"hypervisor": "QEMU", "memory_mib": 4096}))
            self.assertEqual(REPORT.vm_profile(path)["memory_mib"], 4096)
            for value in ({"qemu_args": "-drive file=/home/private/iso"}, {"memory_mib": True}, {"memory_mib": 0}):
                path.write_text(json.dumps(value))
                with self.assertRaises(ValueError):
                    REPORT.vm_profile(path)


if __name__ == "__main__":
    unittest.main()
