#!/usr/bin/env python3
"""Build the Spicy desktop packages from source artwork and native theme files."""
# SPDX-License-Identifier: GPL-2.0-only
import argparse
import base64
import configparser
import json
import math
import os
from pathlib import Path
import shutil
import subprocess

import cairosvg
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0~alpha2"
PALETTE = json.loads((ROOT / "artwork/direction.json").read_text())["palette"]
SIZES = (24, 28, 32, 36, 40, 48, 64, 72, 96, 128)
WALLPAPER_SIZES = ((1280, 720), (1366, 768), (1280, 800), (1920, 1080),
                   (1920, 1200), (2560, 1440), (2560, 1600), (3440, 1440),
                   (3840, 2160))


def write(path, text, executable=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    if executable:
        path.chmod(0o755)


def svg(body, width=64, height=64):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">{body}</svg>')


def png(data, target, width=None, height=None):
    target.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(bytestring=data.encode(), write_to=str(target),
                    output_width=width, output_height=height)


def embedded_image(path):
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def progress_svg():
    # Match the viewport to the exported strip; a square viewport letterboxes
    # the rectangle and leaves most of the progress track transparent.
    return svg('<rect width="64" height="8" rx="2" fill="#C56724"/>', 64, 8)


def wallpaper(kind, size):
    """Compose within a shared safe area; never stretch the cat for an aspect ratio."""
    width, height = size
    dark = kind != "daylight"
    asset = "sitting.png" if kind == "daylight" else "sleeping.png" if kind == "sleeping" else "reclining.png"
    source = ROOT / "artwork" / asset
    with Image.open(source) as image:
        sw, sh = image.size
    # Normalized 16:9 master. The cat stays inside the central 5:4 safe area and
    # the vertical safe area shared with 21:9. Workspace on the left stays clear.
    scale = min(1150 / sw, 1250 / sh, 1.0)
    cw, ch = sw * scale, sh * scale
    x, y = 3200 - cw, 1830 - ch
    background = "#151C20" if dark else "#FAF8F2"
    arcs = ('<path d="M1600 2160 Q2300 750 3840 180 L3840 2160Z" fill="#202A2E"/>'
            '<path d="M1900 2160 Q2800 900 3840 300" fill="none" stroke="#8E592F" stroke-width="5"/>') if dark else (
            '<path d="M1800 2160 Q2200 850 3840 300 L3840 2160Z" fill="#F9D8AD"/>'
            '<path d="M1500 2160 Q2300 1250 3840 850 L3840 2160Z" fill="#F3BB7A" opacity=".35"/>')
    master = f'<rect width="3840" height="2160" fill="{background}"/>{arcs}'
    master += f'<image x="{x:.3f}" y="{y:.3f}" width="{cw:.3f}" height="{ch:.3f}" preserveAspectRatio="xMidYMid meet" xlink:href="{embedded_image(source)}"/>'
    # Render the composition for each ratio rather than asking Plasma to crop a
    # single bitmap. Uniform scaling protects the portrait and white sock paws.
    fit = max(width / 3840, height / 2160)
    tx, ty = (width - 3840 * fit) / 2, (height - 2160 * fit) / 2
    return svg(f'<g transform="translate({tx:.6f} {ty:.6f}) scale({fit:.9f})">{master}</g>', width, height)


def paw_svg(frame=0, hover=False, include_tip=True):
    pulse = .92 + .08 * math.cos(frame * math.pi / 4)
    tip = "#C56724" if hover else "#30383D"
    defs = '<defs><linearGradient id="fur" x2="0" y2="1"><stop stop-color="#FFFFFF"/><stop offset="1" stop-color="#EDE3D6"/></linearGradient><linearGradient id="beans" x2="0" y2="1"><stop stop-color="#F0B2BB"/><stop offset="1" stop-color="#D78294"/></linearGradient><linearGradient id="cuff" x2="0" y2="1"><stop stop-color="#E5A25E"/><stop offset="1" stop-color="#BC6B2B"/></linearGradient></defs>'
    # The triangle and paw are deliberately disconnected. Hotspot is (3, 3)
    # in this 64-unit source, independent of paw shape or animation frame.
    tip_path = f'<path d="M3 3 L21 12 L11 19 Z" fill="{tip}" stroke="#FAF8F2" stroke-width="2.2" stroke-linejoin="round"/>'
    outline = 'M29 29 C27 24 32 21 35 25 C35 19 41 18 44 24 C48 21 53 24 52 29 C57 27 61 32 57 37 C63 43 62 51 55 59 L36 59 C28 53 25 43 29 37 C24 35 25 31 29 29Z'
    paw = f'<path d="{outline}" fill="url(#fur)" stroke="#FAF8F2" stroke-width="3"/><path d="{outline}" fill="url(#fur)" stroke="#30383D" stroke-width=".9"/>'
    paw += '<path d="M32 54 Q43 58 58 52 L55 59 L36 59Z" fill="url(#cuff)"/>'
    pads = '<ellipse cx="32" cy="31" rx="2.8" ry="3.7" transform="rotate(-24 32 31)"/><ellipse cx="40" cy="27" rx="2.8" ry="3.9"/><ellipse cx="48" cy="30" rx="2.7" ry="3.8" transform="rotate(20 48 30)"/><ellipse cx="54" cy="36" rx="2.6" ry="3.4" transform="rotate(35 54 36)"/><path d="M35 43 C34 39 39 37 42 40 C46 37 51 40 50 44 C52 48 48 51 44 49 C40 53 34 50 35 46Z"/>'
    return svg(defs + (tip_path if include_tip else "") + paw + f'<g fill="url(#beans)" opacity="{pulse:.4f}">{pads}</g>')


def build_cursors(dest, scratch):
    cursor = dest / "usr/share/icons/SpicyLittleTip"
    write(cursor / "index.theme", "[Icon Theme]\nName=Spicy Little Tip\nComment=Separate precision tip and Spicy paw with pink toe beans\nInherits=breeze_cursors\n")
    (cursor / "cursors").mkdir(parents=True)
    for name, frames, hover in (("left_ptr", 1, False), ("hand2", 1, True), ("watch", 8, False)):
        entries = []
        for size in SIZES:
            for frame in range(frames):
                target = scratch / f"{name}-{size}-{frame}.png"
                png(paw_svg(frame, hover), target, size, size)
                hotspot = round(size * 3 / 64)
                entries.append(f"{size} {hotspot} {hotspot} {target} 90")
        cfg = scratch / f"{name}.cursor"
        write(cfg, "\n".join(entries) + "\n")
        subprocess.run(["xcursorgen", str(cfg), str(cursor / "cursors" / name)], check=True)
    aliases = {"default":"left_ptr", "arrow":"left_ptr", "top_left_arrow":"left_ptr",
               "pointer":"hand2", "hand1":"hand2", "wait":"watch", "progress":"watch", "left_ptr_watch":"watch",
               "08e8e1c95fe2fc01f976f1e063a24ccd":"watch", "e29285e634086352946a0e7090d73106":"hand2"}
    for alias, target in aliases.items():
        (cursor / "cursors" / alias).symlink_to(target)
    write(scratch / "cursor-metadata.json", json.dumps({"sizes":SIZES,"hotspot_source":[3,3],"source_canvas":[64,64],"separate_tip_and_paw":True}, indent=2))
    write(scratch / "little-tip.svg", paw_svg())


def utility_icon(name):
    defs = '<defs><linearGradient id="ginger" x2="0" y2="1"><stop stop-color="#F3BB7A"/><stop offset="1" stop-color="#C56724"/></linearGradient><linearGradient id="ivory" x2="0" y2="1"><stop stop-color="#FFFFFF"/><stop offset="1" stop-color="#E8DED0"/></linearGradient><linearGradient id="slate" x2="0" y2="1"><stop stop-color="#53616B"/><stop offset="1" stop-color="#30383D"/></linearGradient></defs>'
    if name in ("folder", "user-home", "folder-documents", "folder-pictures"):
        body = '<path d="M7 17 Q7 11 13 11 H26 L32 17 H51 Q57 17 57 23 V50 Q57 55 51 55 H13 Q7 55 7 49Z" fill="url(#ginger)" stroke="#B56A30"/><rect x="7" y="23" width="50" height="31" rx="5" fill="url(#ginger)"/><path d="M36 51 Q39 38 49 33 M45 52 Q47 43 54 39" fill="none" stroke="#B76B30" stroke-width="3" opacity=".55"/>'
    elif name in ("preferences-system", "systemsettings", "applications-system"):
        points = []
        for i in range(48):
            radius = 25 if i % 6 in (1,2,3,4) else 20
            a = i * math.pi / 24
            points.append(f"{32+radius*math.cos(a):.2f},{32+radius*math.sin(a):.2f}")
        body = f'<polygon points="{" ".join(points)}" fill="url(#slate)"/><circle cx="32" cy="32" r="13" fill="url(#ivory)"/><circle cx="32" cy="32" r="8" fill="url(#ginger)"/>'
    elif name in ("utilities-terminal", "org.kde.konsole"):
        body = '<rect x="7" y="10" width="50" height="45" rx="7" fill="url(#slate)"/><path d="M7 19 H57" stroke="#E7A160" stroke-width="7"/><path d="M18 29 L26 36 L18 43 M32 44 H44" fill="none" stroke="#FAF8F2" stroke-width="3" stroke-linecap="round"/>'
    elif name in ("system-software-install", "plasmadiscover", "applications-other"):
        body = '<rect x="10" y="19" width="44" height="37" rx="6" fill="url(#ginger)"/><path d="M22 23 V15 Q22 5 32 5 Q42 5 42 15 V23" fill="none" stroke="#C9B9A5" stroke-width="5"/><path d="M37 31 C30 25 27 36 39 43 C51 35 46 25 40 31Z" fill="#B93645"/>'
    elif name in ("user-trash", "user-trash-full"):
        body = '<path d="M15 19 H49 L46 55 H18Z" fill="url(#ivory)" stroke="#BEB4A5"/><rect x="11" y="14" width="42" height="8" rx="3" fill="url(#ginger)"/><path d="M25 13 V8 H39 V13 M25 29 V47 M33 29 V47 M41 29 V47" fill="none" stroke="#AAA18F" stroke-width="3" stroke-linecap="round"/>'
    elif name in ("network-wireless", "internet-web-browser"):
        body = '<path d="M8 25 Q32 4 56 25 M16 34 Q32 20 48 34 M24 43 Q32 36 40 43" fill="none" stroke="#8C9C83" stroke-width="7" stroke-linecap="round"/><circle cx="32" cy="53" r="5" fill="url(#ginger)"/>'
    else:
        body = '<path d="M15 8 H38 L50 20 V55 H15Z" fill="url(#ivory)" stroke="#D6CDBF"/><path d="M38 8 V20 H50" fill="url(#ginger)"/><path d="M23 29 H42 M23 36 H39 M23 43 H34" stroke="#B7AA98" stroke-width="3" stroke-linecap="round"/><path d="M39 44 C34 39 31 46 40 51 C49 45 44 39 40 44Z" fill="#B93645"/>'
    return svg(defs + '<ellipse cx="32" cy="57" rx="23" ry="2" fill="#30383D" opacity=".08"/>' + body)


def build_icons(dest):
    root = dest / "usr/share/icons/SpicySoft"
    contexts = {"places":["folder","user-home","folder-documents","folder-pictures","user-trash","user-trash-full"],
                "apps":["preferences-system","systemsettings","applications-system","utilities-terminal","org.kde.konsole","system-software-install","plasmadiscover","internet-web-browser","applications-other"],
                "mimetypes":["text-x-generic","document-new"], "status":["network-wireless"]}
    dirs = ["scalable/" + x for x in contexts]
    metadata = "[Icon Theme]\nName=Spicy Soft\nComment=Soft illustrative ginger, ivory and slate utility icons\nInherits=breeze,hicolor\nDirectories=" + ",".join(dirs) + "\n"
    for context, names in contexts.items():
        metadata += f"\n[scalable/{context}]\nSize=64\nType=Scalable\nMinSize=16\nMaxSize=256\nContext={context.capitalize()}\n"
        for name in names:
            write(root / "scalable" / context / (name + ".svg"), utility_icon(name))
    write(root / "index.theme", metadata)


def build_artwork(dest):
    art = dest / "usr/share/spicy/artwork"
    art.mkdir(parents=True)
    for name in ("portrait.png", "sitting.png", "reclining.png", "sleeping.png"):
        shutil.copy2(ROOT / "artwork" / name, art / name)
    write(art / "beans.svg", paw_svg(include_tip=False))
    write(art / "heart.svg", svg('<path d="M32 54 C-6 30 8 2 29 17 L32 20 L35 17 C56 2 70 30 32 54Z" fill="#B93645"/><circle cx="32" cy="18" r="2" fill="#DCD8CF"/>'))
    portrait = svg(f'<image x="7" y="7" width="86" height="86" preserveAspectRatio="xMidYMid meet" xlink:href="{embedded_image(ROOT / "artwork/portrait.png")}"/>', 100, 100)
    for size in (16,22,24,32,48,64,96,128,256,512):
        png(portrait, dest / f"usr/share/icons/hicolor/{size}x{size}/apps/spicy-linux.png", size, size)
    write(dest / "usr/share/icons/hicolor/scalable/apps/spicy-linux.svg", portrait)
    for kind, title in (("daylight","Spicy Daylight"),("night-prowl","Spicy Night Prowl"),("sleeping","Spicy Sleeping")):
        folder = dest / "usr/share/wallpapers" / ("Spicy" + "".join(x.title() for x in kind.split("-")))
        write(folder / "metadata.json", json.dumps({"KPlugin":{"Id":folder.name,"Name":title,"License":"GPL-2.0-only","Authors":[{"Name":"Spicy Linux"}]},"KPackageStructure":"Wallpaper/Images"}, indent=2))
        for width, height in WALLPAPER_SIZES:
            png(wallpaper(kind, (width,height)), folder / f"contents/images/{width}x{height}.png")
    png(progress_svg(), art / "progress.png", 64, 8)


def color_scheme(dark):
    bg, view, fg, alt = ("21,28,32","31,40,45","244,239,231","37,47,52") if dark else ("250,248,242","255,253,248","48,56,61","244,238,229")
    accent, selected = ("243,187,122","48,56,61") if dark else ("149,70,20","255,255,255")
    title = "Spicy Night Prowl" if dark else "Spicy Daylight"
    text = f"[General]\nName={title}\nColorScheme={title.replace(' ','')}\n\n[KDE]\ncontrast=4\n\n"
    for group, surface in (("View",view),("Window",bg),("Button",alt),("Tooltip",view),("Complementary",bg),("Header",bg)):
        # Breeze's lock screen uses Complementary text over a darkened
        # wallpaper, including when the desktop itself uses Daylight.
        surface_dark = dark or group == "Complementary"
        group_fg = "244,239,231" if group == "Complementary" else fg
        group_alt = "37,47,52" if group == "Complementary" else alt
        group_accent = "243,187,122" if group == "Complementary" else accent
        if group == "Complementary":
            surface = "21,28,32"
        text += f"[Colors:{group}]\nBackgroundNormal={surface}\nBackgroundAlternate={group_alt}\nForegroundNormal={group_fg}\nForegroundInactive={'182,185,180' if surface_dark else '93,100,100'}\nForegroundLink={group_accent}\nForegroundVisited=128,92,136\nForegroundNegative={'242,151,163' if surface_dark else '170,42,60'}\nForegroundNeutral={'243,187,122' if surface_dark else '129,88,26'}\nForegroundPositive={'172,196,154' if surface_dark else '55,105,65'}\nDecorationFocus={group_accent}\nDecorationHover={group_accent}\n\n"
    text += f"[Colors:Selection]\nBackgroundNormal={accent}\nBackgroundAlternate={accent}\nForegroundNormal={selected}\nForegroundInactive={selected}\n\n[WM]\nactiveBackground={bg}\nactiveForeground={fg}\ninactiveBackground={bg}\ninactiveForeground={'182,185,180' if dark else '93,100,100'}\n"
    text += "\n[ColorEffects:Disabled]\nColor=112,111,108\nColorAmount=0\nColorEffect=0\nContrastAmount=0.65\nContrastEffect=1\nIntensityAmount=0.1\nIntensityEffect=2\n\n[ColorEffects:Inactive]\nEnable=false\n"
    return text


def build_kvantum(dest):
    """Derive from the installed upstream geometry; retain its upstream license."""
    roots = (Path("/usr/share/Kvantum"),Path("/usr/share/qt5ct/Kvantum"))
    for suffix, candidates in (("Daylight",("KvGnome","KvMojave","KvRoughGlass")),("NightProwl",("KvGnomeDark","KvMojaveDark","KvRoughGlassDark"))):
        base = next((r / c for r in roots for c in candidates if (r/c/(c+".kvconfig")).exists()), None)
        if base is None:
            raise RuntimeError("Install the upstream Kvantum theme data before building")
        name = "Spicy" + suffix
        out = dest / "usr/share/Kvantum" / name
        cfg = configparser.ConfigParser(interpolation=None, strict=False)
        cfg.optionxform = str
        cfg.read(base / (base.name + ".kvconfig"))
        for section in ("%General","General"):
            if not cfg.has_section(section):
                continue
            for key, value in {"author":"Spicy Linux; upstream geometry by Tsu Jan","comment":"Spicy Soft Glass","translucent_windows":"true","blurring":"true","blur_translucent":"true","reduce_window_opacity":"10","reduce_menu_opacity":"8"}.items():
                cfg.set(section,key,value)
        if not cfg.has_section("%General"):
            cfg.add_section("%General")
        dark = suffix == "NightProwl"
        palette = {"window.color":"#151c20" if dark else "#faf8f2", "base.color":"#202a2e" if dark else "#fffdf8", "alt.base.color":"#293438" if dark else "#f4eee5", "text.color":"#f4efe7" if dark else "#30383d", "window.text.color":"#f4efe7" if dark else "#30383d", "button.color":"#293438" if dark else "#f4eee5", "button.text.color":"#f4efe7" if dark else "#30383d", "highlight.color":"#f3bb7a" if dark else "#954614", "highlight.text.color":"#30383d" if dark else "#ffffff", "link.color":"#f3bb7a" if dark else "#954614"}
        if not cfg.has_section("GeneralColors"):
            cfg.add_section("GeneralColors")
        for key, value in palette.items():
            cfg.set("GeneralColors",key,value)
        out.mkdir(parents=True)
        with (out / (name + ".kvconfig")).open("w") as handle:
            cfg.write(handle, space_around_delimiters=False)
        shutil.copy2(base / (base.name + ".svg"), out / (name + ".svg"))
        write(out / "UPSTREAM", f"Geometry derived from {base.name}, by Tsu Jan.\nSource: https://github.com/tsujan/Kvantum\nLicense: GPL-3.0-or-later, as distributed by Debian's Kvantum package.\n")


def build_desktop(dest, scratch):
    for dark in (False, True):
        suffix, key = ("NightProwl","night-prowl") if dark else ("Daylight","daylight")
        name = "Spicy" + suffix
        write(dest / f"usr/share/color-schemes/{name}.colors", color_scheme(dark))
        package = dest / f"usr/share/plasma/look-and-feel/org.spicy.{key}.desktop"
        write(package / "metadata.json", json.dumps({"KPackageStructure":"Plasma/LookAndFeel","KPlugin":{"Id":f"org.spicy.{key}.desktop","Name":"Spicy " + ("Night Prowl" if dark else "Daylight"),"Description":"Spicy's faithful portrait, soft glass and pink toe beans","Version":"0.1.0","License":"GPL-2.0-only","Authors":[{"Name":"Spicy Linux"}]}} , indent=2))
        write(package / "contents/defaults", f"[kdeglobals][General]\nColorScheme={name}\nfont=Atkinson Hyperlegible,10,-1,5,50,0,0,0,0,0\nsmallestReadableFont=Atkinson Hyperlegible,9,-1,5,50,0,0,0,0,0\n\n[kdeglobals][KDE]\nwidgetStyle=kvantum\n\n[kdeglobals][Icons]\nTheme=SpicySoft\n\n[plasmarc][Theme]\nname={'breeze-dark' if dark else 'default'}\n\n[kcminputrc][Mouse]\ncursorTheme=SpicyLittleTip\n\n[kwinrc][org.kde.kdecoration2]\nlibrary=org.kde.breeze\n\n[Wallpaper]\nImage={name}\n\n[ksplashrc][KSplash]\nTheme=org.spicy.{key}.desktop\nEngine=KSplashQML\n")
        splash = package / "contents/splash/Splash.qml"
        splash.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "theme/qml/Splash.qml", splash)
        layout = package / "contents/layouts/org.kde.plasma.desktop-layout.js"
        layout.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "theme/desktop-layout.js", layout)
        # Keep the stock, maintained authentication implementation.
        for component in ("lockscreen", "components"):
            (package / "contents" / component).symlink_to(f"/usr/share/plasma/look-and-feel/org.kde.breeze.desktop/contents/{component}")
    build_icons(dest)
    build_cursors(dest, scratch)
    build_kvantum(dest)
    for file in (ROOT / "theme/files").rglob("*"):
        if file.is_file():
            target = dest / file.relative_to(ROOT / "theme/files")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file,target)
    # Debian's Plymouth initramfs hook preserves assets inside the theme's own
    # directory. An external ImageDir is copied to a different path, leaving
    # early boot unable to find the portrait. Keep only the boot assets here.
    boot_art = dest / "usr/share/plymouth/themes/spicy"
    shutil.copy2(ROOT / "artwork/portrait.png", boot_art / "portrait.png")
    png(progress_svg(), boot_art / "progress.png", 64, 8)
    qml = dest / "usr/share/spicy/qml"
    shutil.copytree(ROOT / "theme/qml",qml,dirs_exist_ok=True)
    shutil.copytree(ROOT / "hardware", dest / "usr/share/spicy/hardware", dirs_exist_ok=True)
    for script in (ROOT / "scripts").iterdir():
        if script.name.startswith("spicy-"):
            target = dest / "usr/bin" / script.name
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(script,target)
            target.chmod(0o755)
    write(dest / "usr/share/doc/spicy-desktop/art-direction.json", (ROOT / "artwork/direction.json").read_text())


def package(root, name, depends, summary, output, recommends=""):
    dependency = f"Depends: {depends}\n" if depends else ""
    recommendation = f"Recommends: {recommends}\n" if recommends else ""
    write(root / "DEBIAN/control", f"Package: {name}\nVersion: {VERSION}\nSection: x11\nPriority: optional\nArchitecture: all\nMaintainer: Spicy Linux <noreply@github.com>\n{dependency}{recommendation}Homepage: https://github.com/SeanPVera/linux-by-spicy\nDescription: {summary}\n A first Spicy Linux desktop alpha for Debian 13 and Plasma 6.\n")
    copyright = "Spicy Linux distribution assets and code\nLicense: GPL-2.0-only\nSee /usr/share/common-licenses/GPL-2.\n\nKvantum-derived theme geometry: Tsu Jan, GPL-3.0-or-later.\nSee /usr/share/common-licenses/GPL-3 and each theme's UPSTREAM file.\n"
    write(root / f"usr/share/doc/{name}/copyright",copyright)
    # Source artwork can originate in private upload directories. Installed
    # assets must be readable by the greeter and every desktop user.
    root.chmod(0o755)
    for item in root.rglob("*"):
        if item.is_symlink():
            continue
        if item.is_dir():
            item.chmod(0o755)
        else:
            item.chmod(0o755 if item.stat().st_mode & 0o111 else 0o644)
    output.mkdir(parents=True,exist_ok=True)
    subprocess.run(["dpkg-deb","--root-owner-group","--build",str(root),str(output / f"{name}_{VERSION}_all.deb")],check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=ROOT/"dist")
    args = parser.parse_args()
    staging = ROOT / "build/packages"
    if staging.exists():
        shutil.rmtree(staging)
    scratch = ROOT / "build/cursors"
    scratch.mkdir(parents=True,exist_ok=True)
    art, desktop, release = [staging/x for x in ("spicy-artwork","spicy-desktop","spicy-release")]
    build_artwork(art)
    build_desktop(desktop,scratch)
    for file in (ROOT / "release").rglob("*"):
        if file.is_file():
            target = release / file.relative_to(ROOT / "release")
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(file,target)
    package(art,"spicy-artwork","", "Spicy the Cat artwork and wallpapers",args.output)
    deps = f"spicy-artwork (= {VERSION}), fonts-atkinson-hyperlegible, fonts-noto-core, breeze-icon-theme, breeze-cursor-theme, plasma-workspace (>= 4:6.0), kde-cli-tools, dbus-bin, qt6-style-kvantum, libqt6svg6, qt6-svg-plugins, libkscreen-bin, qdbus-qt6, python3, python3-pyside6.qtquick, python3-pyside6.qtqml, qml6-module-qtquick-controls, qml6-module-qtquick-layouts, qml6-module-qt5compat-graphicaleffects, plymouth, sddm"
    package(desktop,"spicy-desktop",deps,"Spicy Daylight and Night Prowl Plasma desktop",args.output,recommends="konsole, kde-spectacle")
    package(release,"spicy-release","base-files, dpkg", "Spicy Linux alpha system identity",args.output)
    write(args.output / "spicy-package-version", VERSION + "\n")


if __name__ == "__main__":
    main()
