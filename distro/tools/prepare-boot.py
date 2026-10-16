#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Render the firmware-menu background from the approved portrait and font."""
import base64
from pathlib import Path
import sys

import cairosvg

portrait = Path(__file__).resolve().parents[1] / "artwork/portrait.png"
encoded = base64.b64encode(portrait.read_bytes()).decode()
source = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="800" height="600" viewBox="0 0 800 600">
<rect width="800" height="600" fill="#151c20"/>
<image x="68" y="36" width="170" height="170" preserveAspectRatio="xMidYMid meet" xlink:href="data:image/png;base64,{encoded}"/>
<text x="268" y="104" font-family="Atkinson Hyperlegible" font-size="40" font-weight="bold" fill="#faf8f2">Spicy Linux</text>
<text x="270" y="144" font-family="Atkinson Hyperlegible" font-size="21" fill="#f3bb7a">Live desktop alpha</text>
<path d="M80 252 H720" stroke="#354247" stroke-width="1"/>
</svg>'''
target = Path(sys.argv[1])
target.parent.mkdir(parents=True, exist_ok=True)
cairosvg.svg2png(bytestring=source.encode(), write_to=str(target))
