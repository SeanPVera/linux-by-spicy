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
