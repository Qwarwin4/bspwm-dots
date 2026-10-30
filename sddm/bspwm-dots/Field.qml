import QtQuick 2.15

Rectangle {
    id: f

    property alias text: input.text
    property alias input: input
    property string icon: ""
    property string placeholder: ""
    property bool password: false
    property string fontName: "JetBrainsMono Nerd Font"
    property color fg: "#d9e0ee"
    property color muted: "#646870"
    property color accent: "#989cfa"

    signal accepted()

    height: 44
    radius: 8
    color: "#2b2f37"
    border.width: 2
    border.color: input.activeFocus ? accent : "transparent"

    Behavior on border.color { ColorAnimation { duration: 150 } }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.IBeamCursor
        onClicked: input.forceActiveFocus()
    }

    Text {
        id: ic
        anchors.left: parent.left
        anchors.leftMargin: 14
        anchors.verticalCenter: parent.verticalCenter
        text: f.icon
        color: input.activeFocus ? f.accent : f.muted
        font.family: f.fontName
        font.pixelSize: 16
    }

    TextInput {
        id: input
        anchors.left: ic.right
        anchors.leftMargin: 12
        anchors.right: parent.right
        anchors.rightMargin: 14
        anchors.verticalCenter: parent.verticalCenter
        color: f.fg
        selectionColor: f.accent
        selectedTextColor: "#1e222a"
        font.family: f.fontName
        font.pixelSize: 15
        clip: true
        selectByMouse: true
        echoMode: f.password ? TextInput.Password : TextInput.Normal
        passwordCharacter: "•"
        onAccepted: f.accepted()

        Text {
            anchors.fill: parent
            verticalAlignment: Text.AlignVCenter
            text: f.placeholder
            color: f.muted
            font: input.font
            visible: input.text.length === 0
        }
    }
}
