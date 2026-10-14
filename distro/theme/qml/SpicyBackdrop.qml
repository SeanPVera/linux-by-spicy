// SPDX-License-Identifier: GPL-2.0-only
import QtQuick

Item {
    id: root
    property bool night: false
    property string pose: night ? "reclining" : "sitting"
    property url artworkRoot: typeof spicyArtwork !== "undefined" ? spicyArtwork : Qt.resolvedUrl("../artwork/")
    Rectangle { anchors.fill: parent; color: root.night ? "#151c20" : "#faf8f2" }
    Rectangle {
        width: parent.width * 1.2; height: width; radius: width / 2
        x: parent.width * .5; y: parent.height * .1
        color: root.night ? "#202a2e" : "#f9d8ad"
    }
    Image {
        anchors.right: parent.right; anchors.rightMargin: parent.width * .08
        anchors.bottom: parent.bottom; anchors.bottomMargin: parent.height * .10
        width: parent.width * .44; height: parent.height * .65
        source: root.artworkRoot + root.pose + ".png"
        fillMode: Image.PreserveAspectFit
        horizontalAlignment: Image.AlignRight
        verticalAlignment: Image.AlignBottom
        asynchronous: true
    }
}
