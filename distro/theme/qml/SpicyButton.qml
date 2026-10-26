// SPDX-License-Identifier: GPL-2.0-only
import QtQuick
import QtQuick.Controls

Button {
    id: control
    property bool night: false
    property bool primary: false
    implicitHeight: 44
    implicitWidth: Math.max(100, label.implicitWidth + 32)
    leftPadding: 16; rightPadding: 16; topPadding: 10; bottomPadding: 10
    font.family: "Atkinson Hyperlegible"
    font.pixelSize: 16
    contentItem: Text {
        id: label
        text: control.text
        font: control.font
        color: control.primary ? (control.night ? "#30383d" : "#ffffff") : (control.night ? "#f4efe7" : "#30383d")
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        opacity: control.enabled ? 1 : .55
    }
    background: Rectangle {
        radius: 11
        gradient: Gradient {
            GradientStop { position: 0; color: control.primary ? (control.night ? "#f7c68f" : control.down ? "#813b14" : "#a9551f") : (control.night ? "#344147" : "#fffdf8") }
            GradientStop { position: 1; color: control.primary ? (control.night ? "#f3bb7a" : "#954614") : (control.night ? "#293438" : "#f4eee5") }
        }
        border.width: control.visualFocus ? 2 : 1
        border.color: control.visualFocus ? "#c56724" : control.night ? "#536166" : "#d6cdc0"
        opacity: control.enabled ? 1 : .6
    }
}
