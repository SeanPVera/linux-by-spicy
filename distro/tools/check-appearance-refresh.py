#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Check actual Kvantum palettes at the helper's style-reload boundary."""
import argparse
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def probe(source):
    # Run in a separate process: Qt and Kvantum cache XDG paths on first use.
    with tempfile.TemporaryDirectory(prefix="spicy-kvantum-order-") as directory:
        config = Path(directory)
        os.environ["XDG_CONFIG_HOME"] = str(config)
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtCore import qVersion
        from PySide6.QtWidgets import QApplication, QStyleFactory

        app = QApplication([])
        app.setApplicationName("konsole")
        try:
            if "kvantum" not in [name.lower() for name in QStyleFactory.keys()]:
                raise RuntimeError("The native Qt 6 Kvantum style is unavailable")
            chooser = config / "Kvantum/kvantum.kvconfig"
            chooser.parent.mkdir()
            themes = ROOT / "build/packages/spicy-desktop/usr/share/Kvantum"
            for name in ("SpicyDaylight", "SpicyNightProwl"):
                shutil.copytree(themes / name, chooser.parent / name)
            loader = importlib.machinery.SourceFileLoader("appearance_probe", str(source))
            spec = importlib.util.spec_from_loader(loader.name, loader)
            appearance = importlib.util.module_from_spec(spec)
            loader.exec_module(appearance)
            chooser.write_text("[General]\ntheme=SpicyNightProwl\n")
            observations = []
            for theme in ("daylight", "night-prowl", "daylight"):
                for action in appearance.commands(theme):
                    if action[0] == "kwriteconfig6" and action[2] == "Kvantum/kvantum.kvconfig":
                        chooser.write_text("[General]\ntheme=" + action[-1] + "\n")
                    elif action[0] == "plasma-apply-lookandfeel":
                        # KDE's StyleChanged handler recreates the style here.
                        # Use Qt's string overload so Qt owns the native style.
                        app.setStyle("kvantum")
                        app.processEvents()
                expected = "#151c20" if theme == "night-prowl" else "#faf8f2"
                actual = app.style().standardPalette().window().color().name()
                observations.append({
                    "requested": theme, "expected_window_color": expected,
                    "native_kvantum_window_color": actual, "matches": actual == expected,
                })
            return {
                "qt_version": qVersion(), "source": str(source),
                "scope": "Actual Qt/Kvantum style recreation at the helper's look-and-feel step. "
                         "This is not a Plasma session, Konsole process or visual acceptance result.",
                "observations": observations,
                "passed": all(item["matches"] for item in observations),
            }
        finally:
            # Destroy Kvantum while its temporary configuration still exists;
            # require ordinary Qt teardown and a normal process exit.
            app.setStyle("Fusion")
            app.processEvents()
            app.quit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "scripts/spicy-appearance")
    parser.add_argument("--output", type=Path, default=ROOT / "build/previews/appearance-refresh.json")
    args = parser.parse_args()
    result = probe(args.source.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
