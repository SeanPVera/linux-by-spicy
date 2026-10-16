// SPDX-License-Identifier: GPL-2.0-only
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../spicy/qml" as Spicy

Rectangle {
    id: root
    color: "#151c20"
    property bool compact: width < 760
    property real contentWidth: Math.min(width * .84, 1180)
    property real contentX: (width - contentWidth) / 2
    property url artworkRoot: typeof spicyArtwork !== "undefined" ? spicyArtwork : "file:///usr/share/spicy/artwork/"
    property string failure: ""
    Image {
        source: root.artworkRoot + "portrait.png"
        width: root.compact ? Math.min(root.width * .22, root.height * .24) : root.contentWidth * .46
        height: root.compact ? width : Math.min(root.height * .7, 600)
        x: root.compact ? (root.width - width) / 2 : root.contentX
        y: root.compact ? root.height * .035 : (root.height - height) / 2
        fillMode: Image.PreserveAspectFit
    }
    ScrollView {
        width: root.compact ? root.width * .86 : root.contentWidth * .40
        height: root.compact ? root.height * .67 : Math.min(root.height * .8, 640)
        x: root.compact ? (root.width - width) / 2 : root.contentX + root.contentWidth * .56
        y: root.compact ? root.height * .29 : (root.height - height) / 2
        contentWidth: availableWidth
        clip: true
        ColumnLayout {
            width: parent.width
            spacing: 16
            Label { text: "Welcome back"; color: "#faf8f2"; font.family: "Atkinson Hyperlegible"; font.pixelSize: root.compact ? 26 : 36; font.bold: true }
            Label { text: "Spicy Linux"; color: "#c6cbc6"; font.family: "Atkinson Hyperlegible"; font.pixelSize: 18 }
            TextField {
                id: user; objectName: "username"; Layout.fillWidth: true; implicitHeight: 48
                placeholderText: "Username"; text: userModel.lastUser; color: "#f4efe7"; placeholderTextColor: "#adb8b4"
                font.family: "Atkinson Hyperlegible"; font.pixelSize: 18; leftPadding: 14
                background: Rectangle { radius: 11; color: "#d9263136"; border.width: user.activeFocus ? 2 : 1; border.color: user.activeFocus ? "#f3bb7a" : "#536166" }
                onAccepted: password.forceActiveFocus()
            }
            TextField {
                id: password; objectName: "password"; Layout.fillWidth: true; implicitHeight: 48
                placeholderText: "Password"; echoMode: TextInput.Password; focus: true; color: "#f4efe7"; placeholderTextColor: "#adb8b4"
                font.family: "Atkinson Hyperlegible"; font.pixelSize: 18; leftPadding: 14
                background: Rectangle { radius: 11; color: "#d9263136"; border.width: password.activeFocus ? 2 : 1; border.color: password.activeFocus ? "#f3bb7a" : "#536166" }
                onAccepted: login.clicked()
            }
            ComboBox {
                id: session; objectName: "session"; Layout.fillWidth: true; implicitHeight: 44
                model: sessionModel; textRole: "name"; currentIndex: sessionModel.lastIndex; font.family: "Atkinson Hyperlegible"
                contentItem: Text { text: session.displayText; color: "#f4efe7"; leftPadding: 14; font.family: "Atkinson Hyperlegible"; font.pixelSize: 16; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { radius: 11; color: "#d9263136"; border.color: "#536166" }
            }
            Spicy.SpicyButton { id: login; objectName: "signIn"; night: true; primary: true; Layout.fillWidth: true; implicitHeight: 48; text: "Sign in"; font.pixelSize: 18; onClicked: sddm.login(user.text, password.text, session.currentIndex) }
            Label { text: root.failure; visible: text.length > 0; color: "#f297a3"; wrapMode: Text.Wrap; Layout.fillWidth: true; font.family: "Atkinson Hyperlegible" }
            RowLayout {
                Spicy.SpicyButton { text: "Restart"; night: true; visible: sddm.canReboot; onClicked: sddm.reboot() }
                Spicy.SpicyButton { text: "Power off"; night: true; visible: sddm.canPowerOff; onClicked: sddm.powerOff() }
            }
        }
    }
    Connections {
        target: sddm
        function onLoginFailed() { root.failure = "Sign-in failed. Check your username and password."; password.clear(); password.forceActiveFocus() }
    }
    Component.onCompleted: password.forceActiveFocus()
}
