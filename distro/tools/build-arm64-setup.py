#!/usr/bin/env python3
"""Bundle audited architecture-independent desktop packages for Debian ARM64."""
# SPDX-License-Identifier: GPL-2.0-only
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("spicy-artwork", "spicy-desktop")
COMPILED_MAGIC = (b"\x7fELF", b"MZ", b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe",
                  b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe", b"!<arch>\n")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def audit_package(path, name, version):
    fields = {}
    for key, expected in (("Package", name), ("Version", version), ("Architecture", "all")):
        value = subprocess.check_output(["dpkg-deb", "--field", str(path), key], text=True).strip()
        if value != expected:
            raise ValueError(f"{path.name}: {key} is {value!r}; expected {expected!r}")
        fields[key.lower()] = value
    count, compiled = 0, []
    # Inspect members without extracting package paths or executing their contents.
    with tempfile.TemporaryFile() as payload:
        subprocess.run(["dpkg-deb", "--fsys-tarfile", str(path)], stdout=payload, check=True)
        payload.seek(0)
        with tarfile.open(fileobj=payload, mode="r|") as archive:
            for member in archive:
                if member.isfile():
                    count += 1
                    with archive.extractfile(member) as stream:
                        prefix = stream.read(8)
                    if prefix.startswith(COMPILED_MAGIC) or Path(member.name).suffix in {".so", ".o", ".a", ".pyc", ".pyo"}:
                        compiled.append(member.name)
    if compiled:
        raise ValueError(f"{path.name}: compiled payload cannot be shipped as Architecture: all: {compiled}")
    return {**fields, "file": path.name, "sha256": digest(path),
            "regular_files": count, "compiled_payloads": compiled}


def build_bundle(packages, output, source_commit):
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("Record the full 40-character source commit SHA")
    version = (packages / "spicy-package-version").read_text().strip()
    audited = {name: audit_package(packages / f"{name}_{version}_all.deb", name, version)
               for name in PACKAGES}
    if output.exists():
        raise ValueError(f"Output already exists; preserve it or choose a new directory: {output}")
    output.mkdir(parents=True)
    for metadata in audited.values():
        shutil.copy2(packages / metadata["file"], output / metadata["file"])
    shutil.copy2(ROOT / "parallels/install.py", output / "install.py")
    shutil.copy2(ROOT / "parallels/README.md", output / "README.md")
    shutil.copy2(ROOT / "VM_VALIDATION.md", output / "VM_VALIDATION.md")
    manifest = {"target": {"distribution": "Debian 13", "architecture": "arm64"},
                "source_commit": source_commit, "version": version, "packages": audited,
                "native_dependencies": "Resolved by Debian ARM64 apt on the target; no native executables bundled",
                "runtime_validation": "Pending on the target Parallels VM"}
    (output / "bundle.json").write_text(json.dumps(manifest, indent=2) + "\n")
    sums = "".join(f"{digest(path)}  {path.name}\n" for path in sorted(output.iterdir()))
    (output / "SHA256SUMS").write_text(sums)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages", type=Path, default=ROOT / "dist")
    parser.add_argument("--output", type=Path, default=ROOT / "dist/spicy-debian-arm64-setup")
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    print(json.dumps(build_bundle(args.packages.resolve(), args.output.resolve(), args.source_commit), indent=2))


if __name__ == "__main__":
    main()
