// SPDX-License-Identifier: GPL-2.0-only
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: root
    objectName: "spicyWelcome"
    width: Math.min(1120, Screen.width * .9)
    height: Math.min(760, Screen.height * .88)
    minimumWidth: Math.min(440, Screen.width)
    minimumHeight: Math.min(320, Screen.height)
    visible: true
    title: "Welcome to Spicy Linux"
    font.family: "Atkinson Hyperlegible"
    font.pixelSize: 16
    property bool night: backend.currentTheme === "night-prowl"
    property color ink: night ? "#f4efe7" : "#30383d"
    property color muted: night ? "#bac0bc" : "#5d6464"
    property bool compact: width < 760
    color: night ? "#151c20" : "#faf8f2"
    palette.windowText: ink
    palette.text: ink
    palette.buttonText: ink
    palette.button: night ? "#293438" : "#f4eee5"
    palette.highlight: night ? "#f3bb7a" : "#954614"
    palette.highlightedText: night ? "#30383d" : "#ffffff"

    SpicyBackdrop { anchors.fill: parent; night: root.night; opacity: .34 }
    ScrollView {
        id: scroll
        objectName: "welcomeScroll"
        anchors.fill: parent
        anchors.margins: root.compact ? 16 : 32
        contentWidth: availableWidth
        clip: true
        ColumnLayout {
            width: scroll.availableWidth
            spacing: 20
            RowLayout {
                Layout.fillWidth: true
                spacing: 16
                Item {
                    objectName: "brandPortrait"
                    Layout.preferredWidth: root.compact ? 64 : 96
                    Layout.preferredHeight: width
                    clip: true
                    Image {
                        id: peekImage
                        source: spicyArtwork + "portrait.png"
                        width: parent.width; height: parent.height
                        fillMode: Image.PreserveAspectFit
                        sourceSize: Qt.size(width * Screen.devicePixelRatio, height * Screen.devicePixelRatio)
                        NumberAnimation { id: peekAnimation; target: peekImage; property: "y"; from: peekImage.height; to: 0; duration: 500 }
                        Component.onCompleted: Qt.callLater(function() { if (!backend.reducedMotion) peekAnimation.start() })
                        Connections { target: backend; function onChanged() { if (backend.reducedMotion) { peekAnimation.stop(); peekImage.y = 0 } } }
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    Label { text: "Spicy Linux"; color: root.ink; font.pixelSize: root.compact ? 28 : 36; font.bold: true }
                    Label { text: "A desktop with personality"; color: root.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                }
            }
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: intro.implicitHeight + 32
                radius: 18
                color: root.night ? "#de202a2e" : "#e6fffdf8"
                border.color: root.night ? "#445054" : "#ded8ce"
                ColumnLayout {
                    id: intro
                    anchors.fill: parent; anchors.margins: 16
                    spacing: 8
                    Label { text: "Welcome home"; font.pixelSize: 26; font.bold: true; color: root.ink }
                    Label {
                        text: "Meet Spicy. His ginger stripes, white socks, pink toe beans and little red heart are all here."
                        color: root.ink; wrapMode: Text.Wrap; Layout.fillWidth: true
                    }
                    Label { text: "Live desktop alpha · Debian 13 · KDE Plasma"; color: root.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                }
            }
            Label { text: "Make yourself comfortable"; font.pixelSize: 22; font.bold: true; color: root.ink }
            GridLayout {
                columns: root.compact ? 1 : 2
                columnSpacing: 16; rowSpacing: 16
                Layout.fillWidth: true
                Repeater {
                    model: [
                        { name: "Daylight", key: "daylight", detail: "Ivory, apricot and warm ginger", color: "#faf8f2", pose: "sitting" },
                        { name: "Night Prowl", key: "night-prowl", detail: "Deep slate with warm accents", color: "#151c20", pose: "reclining" }
                    ]
                    delegate: Rectangle {
                        id: themeCard
                        required property var modelData
                        Layout.fillWidth: true
                        implicitHeight: 218
                        radius: 18
                        color: modelData.color
                        border.color: backend.currentTheme === modelData.key ? "#c56724" : root.night ? "#485257" : "#d9d3c9"
                        border.width: backend.currentTheme === modelData.key ? 2 : 1
                        Image {
                            source: spicyArtwork + themeCard.modelData.pose + ".png"
                            anchors.right: parent.right; anchors.top: parent.top
                            anchors.margins: 12
                            width: parent.width * .46; height: 136
                            fillMode: Image.PreserveAspectFit
                            horizontalAlignment: Image.AlignRight
                        }
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 16
                            spacing: 8
                            Label { text: themeCard.modelData.name; color: themeCard.modelData.key === "daylight" ? "#30383d" : "#f4efe7"; font.pixelSize: 22; font.bold: true }
                            Label { text: themeCard.modelData.detail; color: themeCard.modelData.key === "daylight" ? "#5d6464" : "#bac0bc"; Layout.maximumWidth: parent.width * .51; wrapMode: Text.Wrap }
                            Item { Layout.fillHeight: true }
                            SpicyButton {
                                objectName: "apply-" + themeCard.modelData.key
                                text: backend.currentTheme === themeCard.modelData.key ? "Use " + themeCard.modelData.name : "Use " + themeCard.modelData.name
                                Layout.fillWidth: true; implicitHeight: 44
                                night: themeCard.modelData.key === "night-prowl"
                                primary: true
                                enabled: !backend.busy
                                onClicked: backend.setTheme(themeCard.modelData.key)
                                scale: pressed && !backend.reducedMotion ? .98 : 1
                                Behavior on scale { NumberAnimation { duration: backend.reducedMotion ? 0 : 100 } }
                            }
                        }
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Image {
                    source: spicyArtwork + "beans.svg"
                    Layout.preferredWidth: 44; Layout.preferredHeight: 44
                    SequentialAnimation on scale {
                        running: backend.busy && !backend.reducedMotion
                        loops: Animation.Infinite
                        NumberAnimation { to: 1.08; duration: 300 }
                        NumberAnimation { to: 1; duration: 300 }
                    }
                }
                Label { text: backend.status; color: root.muted; wrapMode: Text.Wrap; Layout.fillWidth: true; Accessible.role: Accessible.StaticText }
            }
            Switch {
                objectName: "reducedMotion"
                text: "Reduce motion"
                enabled: !backend.busy
                checked: backend.reducedMotion
                onToggled: backend.setReducedMotion(checked)
                Accessible.description: "Use still artwork and remove decorative animations"
            }
            Flow {
                Layout.fillWidth: true
                spacing: 12
                SpicyButton { objectName: "openSettings"; night: root.night; text: "System Settings"; onClicked: backend.openSettings() }
                SpicyButton { objectName: "openFiles"; night: root.night; text: "Your files"; onClicked: backend.openFiles() }
                SpicyButton { objectName: "openGuide"; night: root.night; text: "Project guide"; onClicked: backend.openGuide() }
            }
            Label {
                text: "Spicy Little Tip: a precise pointer, a white paw and those pink toe beans."
                color: root.muted; wrapMode: Text.Wrap; Layout.fillWidth: true
            }
            Item { implicitHeight: 8 }
        }
    }
}
