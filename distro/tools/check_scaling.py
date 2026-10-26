#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Load the real QML with Qt, check layout bounds and capture native previews."""
import argparse
import importlib.machinery
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time

from PySide6.QtCore import QAbstractListModel, QCoreApplication, QEvent, QModelIndex, QObject, Property, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QFont, QFontDatabase, QFontInfo, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "build/packages"


class SessionModel(QAbstractListModel):
    @Property(int, constant=True)
    def lastIndex(self):
        return 0

    def rowCount(self, parent=QModelIndex()):
        return 1 if not parent.isValid() else 0

    def roleNames(self):
        return {Qt.UserRole + 1:b"name"}

    def data(self, index, role=Qt.DisplayRole):
        return "Plasma" if index.isValid() and role in (Qt.DisplayRole, Qt.UserRole + 1) else None


class UserModel(QObject):
    @Property(str, constant=True)
    def lastUser(self):
        return "spicy"


class Greeter(QObject):
    loginFailed = Signal()
    @Property(bool, constant=True)
    def canReboot(self):
        return True

    @Property(bool, constant=True)
    def canPowerOff(self):
        return True

    @Slot(str, str, int)
    def login(self, _user, _password, _session):
        self.loginFailed.emit()

    @Slot()
    def reboot(self):
        pass

    @Slot()
    def powerOff(self):
        pass


def settle(app, duration=.25):
    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)


def load_backend():
    loader = importlib.machinery.SourceFileLoader("spicy_welcome", str(ROOT / "scripts/spicy-welcome"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module.Backend(preview=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale",type=float,default=1)
    parser.add_argument("--output",type=Path,default=ROOT/"build/previews")
    args=parser.parse_args()
    os.environ["QT_SCALE_FACTOR"] = str(args.scale)
    os.environ.setdefault("QT_QUICK_BACKEND","software")
    os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
    app=QGuiApplication(sys.argv)
    app.setFont(QFont("Atkinson Hyperlegible",11))
    assert "Atkinson Hyperlegible" in QFontDatabase.families(), "The actual selected font must be installed"
    assert QFontInfo(app.font()).family() == "Atkinson Hyperlegible"
    backend=load_backend()
    art=STAGE/"spicy-artwork/usr/share/spicy/artwork"
    engine=QQmlApplicationEngine()
    warnings=[]
    engine.warnings.connect(lambda items:warnings.extend(str(x) for x in items))
    engine.rootContext().setContextProperty("backend",backend)
    engine.rootContext().setContextProperty("spicyArtwork",QUrl.fromLocalFile(str(art)+"/").toString())
    engine.load(QUrl.fromLocalFile(str(STAGE/"spicy-desktop/usr/share/spicy/qml/Welcome.qml")))
    assert engine.rootObjects(), "Welcome QML did not load"
    window=engine.rootObjects()[0]
    args.output.mkdir(parents=True,exist_ok=True)
    cases=((1024,768),(1280,720),(1280,800),(1366,768),(1920,1080),(1920,1200),(2560,1440),(2560,1600),(3440,1440),(3840,2160))
    checked=[]
    for physical_w,physical_h in cases:
        logical_w,logical_h=math.floor(physical_w/args.scale),math.floor(physical_h/args.scale)
        window.setMinimumWidth(min(440,logical_w))
        window.setMinimumHeight(min(320,logical_h))
        window.setWidth(logical_w)
        window.setHeight(logical_h)
        for theme in ("daylight","night-prowl"):
            backend.setTheme(theme)
            settle(app)
            assert window.width()==logical_w and window.height()==logical_h
            scroll=window.findChild(QObject,"welcomeScroll")
            assert scroll is not None
            assert scroll.property("contentWidth") <= scroll.property("width")+1, "Horizontal clipping"
            portrait=window.findChild(QObject,"brandPortrait")
            assert portrait and abs(portrait.property("width")-portrait.property("height"))<1, "Distorted portrait"
            # Real Qt renders, not resized concept images. Capture the common
            # laptop layout and native 4K at each tested scaling factor.
            if (physical_w,physical_h) in ((1280,720),(1920,1080),(3840,2160)):
                shot=window.grabWindow()
                assert not shot.isNull(), "Qt did not render the window"
                target=args.output/f"welcome-{theme}-{physical_w}x{physical_h}-{args.scale:g}x.png"
                assert shot.save(str(target))
            checked.append({"resolution":[physical_w,physical_h],"scale":args.scale,"logical_size":[logical_w,logical_h],"theme":theme})
    backend.setReducedMotion(True)
    settle(app)
    assert backend.reducedMotion
    window.close()
    # Load the real sign-in form with harmless model objects; authentication
    # itself is supplied by SDDM in the live image.
    greeter_engine=QQmlApplicationEngine()
    greeter_engine.warnings.connect(lambda items:warnings.extend(str(x) for x in items))
    greeter=Greeter(); users=UserModel(); sessions=SessionModel()
    for key,value in (("sddm",greeter),("userModel",users),("sessionModel",sessions)):
        greeter_engine.rootContext().setContextProperty(key,value)
    greeter_engine.rootContext().setContextProperty("spicyArtwork",QUrl.fromLocalFile(str(art)+"/").toString())
    greeter_engine.load(QUrl.fromLocalFile(str(STAGE/"spicy-desktop/usr/share/sddm/themes/spicy/Main.qml")))
    assert greeter_engine.rootObjects(), "Sign-in QML did not load"
    greeter_item=greeter_engine.rootObjects()[0]
    greeter_window=QQuickWindow()
    greeter_item.setParentItem(greeter_window.contentItem())
    for physical_w,physical_h in cases:
        logical_w,logical_h=math.floor(physical_w/args.scale),math.floor(physical_h/args.scale)
        greeter_window.setWidth(logical_w); greeter_window.setHeight(logical_h)
        greeter_item.setWidth(logical_w); greeter_item.setHeight(logical_h)
        greeter_window.show()
        settle(app)
        if (physical_w,physical_h) in ((1280,720),(3840,2160)):
            shot=greeter_window.grabWindow()
            assert not shot.isNull()
            assert shot.save(str(args.output/f"sign-in-{physical_w}x{physical_h}-{args.scale:g}x.png"))
    password=greeter_item.findChild(QObject,"password")
    password.setProperty("text","preview-test")
    greeter.loginFailed.emit()
    settle(app)
    assert password.property("text")=="", "A failed sign-in must clear the password field"
    greeter_window.close()
    for instance in (greeter_window, greeter_engine, engine):
        instance.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    serious=[x for x in warnings if any(s in x for s in ("ReferenceError","TypeError","is not a type","is not installed","Binding loop","Error decoding","Cannot open:"))]
    assert not serious,"\n".join(serious)
    report={"font":QFontInfo(app.font()).family(),"cases":checked,"qml_warnings":warnings,"sign_in_qml_loaded":True}
    (args.output/f"scaling-{args.scale:g}x.json").write_text(json.dumps(report,indent=2))
    print(f"Qt scaling: {len(checked)} layouts passed at {args.scale:g}x; actual Atkinson Hyperlegible loaded")


if __name__=="__main__":
    main()
