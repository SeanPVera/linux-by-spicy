# SPDX-License-Identifier: GPL-2.0-only
"""Keep VM profiles explicit and host prerequisites distinct from certification."""
import argparse
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "tools/run-vm"
LOADER = importlib.machinery.SourceFileLoader("run_vm", str(SCRIPT))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
VM = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(VM)


def device(path, usable=True):
    return {"path": str(path), "exists": usable, "character_device": usable,
            "readable": usable, "writable": usable}


def capabilities(display="headless", usable=True):
    return {
        "display": display,
        "qemu": {"executable": "/test/qemu", "version": "QEMU test",
                 "advertised": {"accelerators": ["tcg", "kvm"],
                                "graphics_devices": {"virtio-vga": True, "virtio-vga-gl": True},
                                "displays": ["none", "gtk", "egl-headless"]}},
        "devices": {"kvm": device("/dev/kvm", usable),
                    "render_nodes": [device("/dev/dri/renderD128", usable)],
                    "selected_render_node": device("/dev/dri/renderD128", usable)},
    }


class RunVMTests(unittest.TestCase):
    def args(self, root, **overrides):
        for name in ("image.iso", "code.fd", "vars.fd"):
            (root / name).write_bytes(b"test bytes; not bootable")
        values = dict(iso=root / "image.iso", output=root / "run", firmware=root / "code.fd",
                      variables=root / "vars.fd", profile="software", accel=None, graphics=None,
                      display="headless", render_node=None, resolution=(1920, 1080), qemu="qemu",
                      cpus=2, memory=4096, network="none", dry_run=True,
                      expected_sha256=None, max_seconds=1)
        values.update(overrides)
        return argparse.Namespace(**values)

    def plan(self, args):
        with patch("builtins.print") as output:
            self.assertEqual(VM.launch(args), 0)
        return json.loads(output.call_args.args[0])

    def test_profiles_and_independent_controls_choose_exact_devices(self):
        cases = [
            ({}, "tcg", "max", "virtio-vga", "none"),
            ({"profile": "accelerated"}, "kvm", "host", "virtio-vga-gl", "egl-headless"),
            ({"accel": "kvm"}, "kvm", "host", "virtio-vga", "none"),
            ({"graphics": "virgl"}, "tcg", "max", "virtio-vga-gl", "egl-headless"),
            ({"profile": "accelerated", "accel": "tcg", "graphics": "software"},
             "tcg", "max", "virtio-vga", "none"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for overrides, accel, cpu, gpu, display in cases:
                with self.subTest(overrides=overrides):
                    plan = self.plan(self.args(root, **overrides))
                    command = plan["command"]
                    self.assertEqual(command[command.index("-accel") + 1], accel)
                    self.assertEqual(command[command.index("-cpu") + 1], cpu)
                    self.assertIn(f"{gpu},xres=1920,yres=1080", command)
                    self.assertEqual(command[command.index("-display") + 1].split(",")[0], display)
                    self.assertIn(accel.upper(), plan["vm_profile"]["acceleration"])
                    self.assertFalse((root / "run").exists())

    def test_gtk_graphics_mode_is_independent_of_cpu_acceleration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for graphics, expected in (("software", "gtk,gl=off"), ("virgl", "gtk,gl=on")):
                command = self.plan(self.args(root, display="gtk", accel="kvm", graphics=graphics))["command"]
                self.assertEqual(command[command.index("-display") + 1], expected)

    def test_render_node_is_only_valid_for_headless_virgl_and_commas_are_escaped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for overrides in ({}, {"graphics": "virgl", "display": "gtk"}):
                with self.assertRaisesRegex(ValueError, "VirGL and headless"):
                    VM.launch(self.args(root, render_node=Path("/dev/dri/renderD128"), **overrides))
            command = self.plan(self.args(root, graphics="virgl", render_node=Path("/dev/dri/a,b")))["command"]
            self.assertIn("egl-headless,rendernode=/dev/dri/a,,b", command)

    def test_missing_devices_block_acceleration_but_allow_software(self):
        evidence = capabilities(usable=False)
        self.assertEqual(VM.prerequisites(evidence, "tcg", "software"), ([], []))
        for accel, graphics in (("kvm", "software"), ("tcg", "virgl"), ("kvm", "virgl")):
            with self.subTest(accel=accel, graphics=graphics):
                blocked, unknown = VM.prerequisites(evidence, accel, graphics)
                self.assertTrue(blocked)
                self.assertFalse(unknown)

    def test_device_presence_alone_and_help_support_alone_do_not_establish_usability(self):
        evidence = capabilities()
        self.assertEqual(VM.prerequisites(evidence, "kvm", "virgl"), ([], []))
        evidence["devices"]["kvm"]["character_device"] = False
        self.assertTrue(VM.prerequisites(evidence, "kvm", "software")[0])
        evidence = capabilities()
        evidence["qemu"]["advertised"]["graphics_devices"]["virtio-vga-gl"] = False
        self.assertIn("QEMU does not advertise virtio-vga-gl", VM.prerequisites(evidence, "tcg", "virgl")[0])
        evidence["qemu"]["advertised"]["graphics_devices"] = None
        self.assertEqual(VM.prerequisites(evidence, "tcg", "virgl"), ([], ["graphics_devices"]))

    def test_inspection_parses_help_and_never_claims_a_pass(self):
        replies = [
            ({"status": "ok"}, "QEMU test version\nCopyright test\n"),
            ({"status": "ok"}, "Accelerators supported in QEMU binary:\ntcg\nkvm\n"),
            ({"status": "ok"}, 'Display devices:\nname "virtio-vga"\nname "virtio-vga-gl"\n'),
            ({"status": "ok"}, "Available display backend types:\nnone\ngtk\negl-headless\n"),
        ]
        with patch.object(VM.shutil, "which", return_value="/test/qemu"), \
             patch.object(VM, "help_probe", side_effect=replies), \
             patch.object(VM, "device_evidence", side_effect=device):
            report = VM.host_capabilities("qemu", "headless", Path("/dev/dri/renderD128"))
        self.assertEqual(report["qemu"]["version"], "QEMU test version")
        self.assertTrue(report["qemu"]["advertised"]["graphics_devices"]["virtio-vga-gl"])
        self.assertEqual({entry["status"] for entry in report["combinations"].values()}, {"unverified"})
        self.assertIn("remain unverified", report["limits"])

    def test_missing_qemu_inspection_stays_explicit_and_preserves_prior_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "host.json"
            args = argparse.Namespace(qemu="nonexistent", display="headless", render_node=None, output=output)
            with patch.object(VM.shutil, "which", return_value=None), patch("builtins.print"):
                self.assertEqual(VM.inspect(args), 0)
            report = json.loads(output.read_text())
            self.assertIsNone(report["qemu"]["version"])
            self.assertEqual(report["qemu"]["probes"]["devices"]["status"], "missing_command")
            self.assertEqual({entry["status"] for entry in report["combinations"].values()}, {"blocked"})
            original = output.read_bytes()
            with self.assertRaisesRegex(ValueError, "already exists"):
                VM.inspect(args)
            self.assertEqual(output.read_bytes(), original)

    def test_help_probes_are_bounded_and_keep_failed_output_out_of_report(self):
        self.assertEqual(VM.help_probe(None, ["--version"]), ({"status": "missing_command"}, None))
        with patch.object(VM.subprocess, "run", side_effect=subprocess.TimeoutExpired("qemu", 10)) as run:
            self.assertEqual(VM.help_probe("qemu", ["-device", "help"]), ({"status": "timeout"}, None))
            self.assertEqual(run.call_args.kwargs["timeout"], 10)
        result = subprocess.CompletedProcess(["qemu"], 7, stdout="untrusted output", stderr="private error")
        with patch.object(VM.subprocess, "run", return_value=result):
            self.assertEqual(VM.help_probe("qemu", ["-device", "help"]), ({"status": "failed", "exit_code": 7}, None))

    def test_launch_refuses_missing_kvm_without_creating_a_run_or_falling_back(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(VM, "host_capabilities", return_value=capabilities(usable=False)), \
                 patch.object(VM.subprocess, "Popen") as process:
                with self.assertRaisesRegex(ValueError, "/dev/kvm"):
                    VM.launch(self.args(root, dry_run=False, accel="kvm"))
            process.assert_not_called()
            self.assertFalse((root / "run").exists())

    def test_launch_retains_capabilities_and_resolved_override_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = capabilities()
            with patch.object(VM, "host_capabilities", return_value=evidence), \
                 patch.object(VM.subprocess, "Popen") as spawn, patch("builtins.print"):
                spawn.return_value.wait.return_value = 0
                spawn.return_value.returncode = 0
                self.assertEqual(VM.launch(self.args(root, dry_run=False, accel="kvm")), 0)
            recorded = json.loads((root / "run/run.json").read_text())
            self.assertEqual(recorded["profile"], "software")
            self.assertEqual(recorded["cpu_acceleration"], "kvm")
            self.assertEqual(recorded["graphics"], "software")
            self.assertEqual(recorded["status"], "exited")
            self.assertEqual(json.loads((root / "run/host-capabilities.json").read_text()), evidence)
            profile = json.loads((root / "run/vm-profile.json").read_text())
            self.assertEqual(profile["hypervisor_version"], "QEMU test")
            self.assertIn("KVM", profile["acceleration"])
            command = spawn.call_args.args[0]
            self.assertEqual(command[command.index("-accel") + 1], "kvm")

    def test_existing_run_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "run").mkdir()
            (root / "run/run.json").write_text("prior evidence")
            with self.assertRaisesRegex(ValueError, "already exists"):
                VM.launch(self.args(root))
            self.assertEqual((root / "run/run.json").read_text(), "prior evidence")

    def test_cli_accepts_the_inspect_action_without_iso_or_firmware(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "inspect", "--qemu", "/no/such/qemu"],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["qemu"]["probes"]["version"]["status"], "missing_command")


if __name__ == "__main__":
    unittest.main()
