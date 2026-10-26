// SPDX-License-Identifier: GPL-2.0-only
import QtQuick

Item {
    id: root
    property int stage: 0
    property url artworkRoot: typeof spicyArtwork !== "undefined" ? spicyArtwork : "file:///usr/share/spicy/artwork/"
    Rectangle { anchors.fill: parent; color: "#151c20" }
    Column {
        anchors.centerIn: parent
        width: Math.min(parent.width * .7, 460)
        spacing: 20
        Image {
            anchors.horizontalCenter: parent.horizontalCenter
            source: root.artworkRoot + "portrait.png"
            width: Math.min(root.width * .22, root.height * .34)
            height: width
            fillMode: Image.PreserveAspectFit
        }
        Text { text: "Spicy Linux"; color: "#faf8f2"; font.family: "Atkinson Hyperlegible"; font.pixelSize: Math.max(22, Math.min(42, root.height * .045)); anchors.horizontalCenter: parent.horizontalCenter }
        Rectangle {
            width: parent.width; height: 5; radius: 2.5; color: "#354247"
            Rectangle { width: parent.width * Math.min(1, Math.max(.03, root.stage / 6)); height: parent.height; radius: parent.radius; color: "#f3bb7a"; Behavior on width { NumberAnimation { duration: 180 } } }
        }
    }
}
