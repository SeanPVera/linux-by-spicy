# SPDX-License-Identifier: GPL-2.0-only
import configparser
import importlib.util
import json
from pathlib import Path
import struct

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/"build"
STAGE=BUILD/"packages"


def components(image):
    alpha=image.getchannel("A")
    pixels=alpha.load()
    remaining={(x,y) for y in range(image.height) for x in range(image.width) if pixels[x,y]>32}
    groups=[]
    while remaining:
        start=remaining.pop()
        group={start}; work=[start]
        while work:
            x,y=work.pop()
            for n in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if n in remaining:
                    remaining.remove(n);group.add(n);work.append(n)
        if len(group)>2:
            groups.append(group)
    return groups


def test_cursor_tip_and_paw_are_disconnected_at_every_size():
    for path in (BUILD/"cursors").glob("left_ptr-*-0.png"):
        with Image.open(path) as image:
            groups=components(image)
            assert len(groups)==2,(path,len(groups))
            size=image.width
            hotspot=round(size*3/64)
            assert image.getchannel("A").getpixel((hotspot,hotspot))>32
    assert len(list((BUILD/"cursors").glob("left_ptr-*-0.png")))==10


def test_compiled_cursor_contains_all_sizes_and_valid_hotspots():
    path=STAGE/"spicy-desktop/usr/share/icons/SpicyLittleTip/cursors/left_ptr"
    data=path.read_bytes()
    assert data[:4]==b"Xcur"
    _magic,_header,_version,count=struct.unpack_from("<4I",data)
    assert count==10
    sizes=[]
    for i in range(count):
        kind,size,offset=struct.unpack_from("<3I",data,16+i*12)
        assert kind==0xfffd0002
        header,itype,subtype,version,width,height,xhot,yhot,delay=struct.unpack_from("<9I",data,offset)
        assert width==height==size
        assert 0<=xhot<width and 0<=yhot<height
        sizes.append(size)
    assert sorted(sizes)==[24,28,32,36,40,48,64,72,96,128]


def test_wallpapers_are_real_exports_for_lower_resolutions_and_4k():
    roots=STAGE/"spicy-artwork/usr/share/wallpapers"
    for theme in ("SpicyDaylight","SpicyNightProwl","SpicySleeping"):
        images=roots/theme/"contents/images"
        for width,height in ((1280,720),(1366,768),(1280,800),(1920,1080),(1920,1200),(2560,1440),(2560,1600),(3440,1440),(3840,2160)):
            with Image.open(images/f"{width}x{height}.png") as image:
                assert image.size==(width,height)
                assert image.mode in ("RGB","RGBA")
        with Image.open(images/"3840x2160.png") as image:
            pixel=image.getpixel((20,20))[:3]
            assert pixel==((250,248,242) if theme=="SpicyDaylight" else (21,28,32))


def luminance(rgb):
    values=[x/255 for x in rgb]
    linear=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in values]
    return sum(x*y for x,y in zip(linear,(.2126,.7152,.0722)))


def test_normal_text_and_selection_contrast():
    for name in ("SpicyDaylight","SpicyNightProwl"):
        cfg=configparser.ConfigParser()
        cfg.read(STAGE/f"spicy-desktop/usr/share/color-schemes/{name}.colors")
        for group in ("View","Window","Button","Tooltip","Selection","Complementary"):
            section=cfg["Colors:"+group]
            a,b=[luminance(tuple(map(int,section[key].split(",")))) for key in ("BackgroundNormal","ForegroundNormal")]
            ratio=(max(a,b)+.05)/(min(a,b)+.05)
            assert ratio>=4.5,(name,group,ratio)
            if group=="Complementary":
                assert a < .08 and b > .8, "The lock screen needs light text over its dark wallpaper"


def test_selected_screen_sequence_and_font_are_preserved():
    direction=json.loads((ROOT/"artwork/direction.json").read_text())
    screens=direction["choices"]["screens"]
    assert [screens[k]["code"] for k in ("boot","sign_in","locked")]==["7A","7C","7B"]
    assert direction["choices"]["typography"]["font"]=="Atkinson Hyperlegible"
    greeter=(ROOT/"theme/files/usr/share/sddm/themes/spicy/Main.qml").read_text()
    assert "sddm.login(" in greeter
    assert "onLoginFailed" in greeter and "password.clear()" in greeter
