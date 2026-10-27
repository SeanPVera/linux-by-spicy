# SPDX-License-Identifier: GPL-2.0-only
import importlib.util
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load("arm64_builder", ROOT / "tools/build-arm64-setup.py")
installer = load("arm64_installer", ROOT / "parallels/install.py")


def package(directory, name, version="0.1.0~alpha2", architecture="all", payload=b"portable artwork"):
    root = directory / f"root-{name}-{version}"
    (root / "DEBIAN").mkdir(parents=True)
    (root / "DEBIAN/control").write_text(
        f"Package: {name}\nVersion: {version}\nArchitecture: {architecture}\n"
        "Maintainer: Spicy tests <noreply@example.com>\nDescription: fixture\n")
    (root / "usr/share/spicy").mkdir(parents=True)
    (root / "usr/share/spicy/data").write_bytes(payload)
    target = directory / f"{name}_{version}_{architecture}.deb"
    subprocess.run(["dpkg-deb", "--build", str(root), str(target)], check=True, capture_output=True)
    return target


@pytest.mark.parametrize("payload", [b"\x7fELFwrong architecture", b"MZexecutable", b"!<arch>\nstatic library"])
def test_all_package_cannot_hide_compiled_payload(tmp_path, payload):
    target = package(tmp_path, "spicy-desktop", payload=payload)
    with pytest.raises(ValueError, match="compiled payload"):
        builder.audit_package(target, "spicy-desktop", "0.1.0~alpha2")


def test_architecture_specific_package_is_rejected(tmp_path):
    target = package(tmp_path, "spicy-desktop", architecture="amd64")
    with pytest.raises(ValueError, match="Architecture"):
        builder.audit_package(target, "spicy-desktop", "0.1.0~alpha2")


def test_bundle_pins_version_omits_identity_and_detects_corruption(tmp_path):
    for name in builder.PACKAGES:
        package(tmp_path, name)
        package(tmp_path, name, version="0.1.0~alpha1")
    package(tmp_path, "spicy-release")
    (tmp_path / "spicy-package-version").write_text("0.1.0~alpha2\n")
    output = tmp_path / "bundle"
    builder.build_bundle(tmp_path, output, "1" * 40)
    manifest, paths = installer.check_bundle(output)
    assert {Path(path).name for path in paths} == {
        "spicy-artwork_0.1.0~alpha2_all.deb", "spicy-desktop_0.1.0~alpha2_all.deb"}
    assert not list(output.glob("*alpha1*")) and not list(output.glob("spicy-release*"))
    assert manifest["target"]["architecture"] == "arm64"
    with pytest.raises(ValueError, match="already exists"):
        builder.build_bundle(tmp_path, output, "1" * 40)
    (output / "spicy-desktop_0.1.0~alpha2_all.deb").write_bytes(b"changed after download")
    with pytest.raises(ValueError, match="Checksum mismatch"):
        installer.check_bundle(output)


@pytest.mark.parametrize("architecture,release", [
    ("amd64", {"ID": "debian", "VERSION_ID": "13"}),
    ("arm64", {"ID": "debian", "VERSION_ID": "12"}),
    ("arm64", {"ID": "ubuntu", "VERSION_ID": "24.04"}),
])
def test_wrong_host_stops_before_bundle_or_apt(monkeypatch, architecture, release):
    monkeypatch.setattr(installer.subprocess, "check_output", lambda *a, **kw: architecture)
    monkeypatch.setattr(installer.platform, "freedesktop_os_release", lambda: release)
    monkeypatch.setattr(installer, "check_bundle", lambda *a: pytest.fail("bundle used on wrong host"))
    monkeypatch.setattr(installer.subprocess, "run", lambda *a, **kw: pytest.fail("apt invoked on wrong host"))
    assert installer.main(["--install"]) == 1


def test_arm64_debian_13_host_is_accepted(monkeypatch):
    monkeypatch.setattr(installer.subprocess, "check_output", lambda *a, **kw: "arm64\n")
    monkeypatch.setattr(installer.platform, "freedesktop_os_release", lambda: {
        "ID": "debian", "VERSION_ID": "13", "PRETTY_NAME": "Debian GNU/Linux 13 (trixie)"})
    assert installer.check_host()["architecture"] == "arm64"


def test_install_requires_guest_root_without_invoking_apt(monkeypatch):
    monkeypatch.setattr(installer, "check_host", lambda: {"architecture": "arm64"})
    monkeypatch.setattr(installer, "check_bundle", lambda *a: ({"source_commit": "1" * 40, "version": "0.1.0~alpha2"}, []))
    monkeypatch.setattr(installer.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(installer.subprocess, "run", lambda *a, **kw: pytest.fail("apt invoked without root"))
    assert installer.main(["--install"]) == 1


def test_install_uses_exact_paths_and_refuses_package_removals(monkeypatch):
    paths = ["/bundle/spicy-artwork_0.1.0~alpha2_all.deb", "/bundle/spicy-desktop_0.1.0~alpha2_all.deb"]
    monkeypatch.setattr(installer, "check_host", lambda: {"architecture": "arm64"})
    monkeypatch.setattr(installer, "check_bundle", lambda *a: ({"source_commit": "1" * 40, "version": "0.1.0~alpha2"}, paths))
    monkeypatch.setattr(installer.os, "geteuid", lambda: 0)
    calls = []
    monkeypatch.setattr(installer.subprocess, "run", lambda command, **kw: (calls.append(command) or subprocess.CompletedProcess(command, 0)))
    assert installer.main(["--check"]) == 0
    assert calls == []
    assert installer.main(["--install"]) == 0
    assert calls == [["apt-get", "install", "--no-remove", *paths]]
