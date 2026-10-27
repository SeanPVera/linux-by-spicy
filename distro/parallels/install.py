#!/usr/bin/env python3
"""Check or install this Spicy desktop bundle inside a Debian 13 ARM64 guest."""
# SPDX-License-Identifier: GPL-2.0-only
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

PACKAGES = {"spicy-artwork", "spicy-desktop"}


def check_host():
    architecture = subprocess.check_output(["dpkg", "--print-architecture"], text=True).strip()
    release = platform.freedesktop_os_release()
    if architecture != "arm64":
        raise ValueError(f"Run inside the Debian ARM64 VM; dpkg reports {architecture!r}")
    if release.get("ID") != "debian" or release.get("VERSION_ID", "").split(".")[0] != "13":
        raise ValueError("This setup requires Debian 13 (trixie); no system changes were made")
    return {"architecture": architecture, "distribution": release.get("PRETTY_NAME")}


def check_bundle(directory):
    entries = {}
    for line in (directory / "SHA256SUMS").read_text().splitlines():
        sha, name = line.split("  ", 1)
        if len(sha) != 64 or Path(name).name != name or name in entries:
            raise ValueError("Invalid bundle checksum entry")
        entries[name] = sha
        with (directory / name).open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != sha:
            raise ValueError(f"Checksum mismatch: {name}")
    required = {"bundle.json", "install.py", "README.md"}
    if not required <= entries.keys():
        raise ValueError("Incomplete bundle checksum file")
    manifest = json.loads((directory / "bundle.json").read_text())
    if manifest["target"] != {"distribution": "Debian 13", "architecture": "arm64"}:
        raise ValueError("Unexpected bundle target")
    if set(manifest["packages"]) != PACKAGES:
        raise ValueError("The setup must contain only the artwork and desktop packages")
    paths = []
    for name, metadata in sorted(manifest["packages"].items()):
        filename = metadata["file"]
        if Path(filename).name != filename or filename not in entries:
            raise ValueError(f"Package missing from checksums: {name}")
        path = directory / filename
        for field, expected in (("Package", name), ("Version", manifest["version"]), ("Architecture", "all")):
            actual = subprocess.check_output(["dpkg-deb", "--field", str(path), field], text=True).strip()
            if actual != expected:
                raise ValueError(f"Unexpected {field} in {filename}: {actual!r}")
        if metadata["sha256"] != entries[filename] or metadata["compiled_payloads"]:
            raise ValueError(f"Package audit does not match: {name}")
        paths.append(str(path.resolve()))
    return manifest, paths


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="Check host and files without installing (default)")
    action.add_argument("--install", action="store_true", help="Install the two desktop packages using apt-get")
    args = parser.parse_args(argv)
    try:
        host = check_host()
        manifest, paths = check_bundle(Path(__file__).resolve().parent)
        print(json.dumps({"host": host, "source_commit": manifest["source_commit"],
                          "version": manifest["version"], "checksums": "passed"}, indent=2), flush=True)
        if args.install:
            if os.geteuid() != 0:
                raise ValueError("Install inside the guest with: sudo python3 install.py --install")
            # Refuse an apt solution that would remove existing packages.
            return subprocess.run(["apt-get", "install", "--no-remove", *paths], check=False).returncode
        return 0
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"Setup stopped: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
