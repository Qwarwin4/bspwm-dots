import QtQuick 2.15

Rectangle {
    id: root

    property string fontName: config.font || "JetBrainsMono Nerd Font"
    property color bgc: config.bg || "#1e222a"
    property color pill: config.pill || "#2b2f37"
    property color fg: config.fg || "#d9e0ee"
    property color muted: config.muted || "#646870"
    property color accent: config.accent || "#989cfa"
    property color red: config.red || "#d35f5e"
    property int session: sessionModel.lastIndex >= 0 ? sessionModel.lastIndex : 0

    width: 1920
    height: 1080
    color: bgc

    function login() {
        if (user.text.length === 0) {
            user.input.forceActiveFocus()
            return
        }
        err.text = ""
        busy.visible = true
        sddm.login(user.text, pass.text, root.session)
    }

    function now() {
        var d = new Date()
        clock.text = Qt.formatTime(d, "HH:mm")
        day.text = d.toLocaleDateString(Qt.locale(), "dddd, d MMMM")
    }

    Connections {
        target: sddm
        function onLoginFailed() {
            busy.visible = false
            pass.text = ""
            err.text = "Неверный пароль"
            shake.restart()
            pass.input.forceActiveFocus()
        }
        function onLoginSucceeded() {
            err.text = ""
        }
    }

    Repeater {
        id: sessions
        model: sessionModel
        delegate: Item { property string sname: name }
    }

    Repeater {
        id: users
        model: userModel
        delegate: Item { property string uname: name }
    }

    Image {
        id: wall
        anchors.fill: parent
        source: config.background || config.fallback
        fillMode: Image.PreserveAspectCrop
        asynchronous: false
        cache: false
        smooth: true
        onStatusChanged: {
            if (status === Image.Error && source != Qt.resolvedUrl(config.fallback))
                source = config.fallback
        }
    }

    Rectangle {
        anchors.fill: parent
        color: root.bgc
        opacity: config.dim !== undefined && config.dim !== "" ? Number(config.dim) : 0.35
    }

    Timer {
        interval: 1000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: root.now()
    }

    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: card.top
        anchors.bottomMargin: 48
        spacing: 2

        Text {
            id: clock
            anchors.horizontalCenter: parent.horizontalCenter
            color: root.fg
            font.family: root.fontName
            font.pixelSize: 112
            font.bold: true
        }

        Text {
            id: day
            anchors.horizontalCenter: parent.horizontalCenter
            color: root.fg
            opacity: 0.85
            font.family: root.fontName
            font.pixelSize: 22
        }
    }

    Rectangle {
        id: card
        width: 380
        height: form.implicitHeight + 48
        anchors.centerIn: parent
        anchors.verticalCenterOffset: 90
        radius: 12
        color: Qt.rgba(root.bgc.r, root.bgc.g, root.bgc.b, 0.92)
        border.width: 2
        border.color: root.accent

        transform: Translate { id: shift }

        SequentialAnimation {
            id: shake
            NumberAnimation { target: shift; property: "x"; to: -12; duration: 50 }
            NumberAnimation { target: shift; property: "x"; to: 12; duration: 70 }
            NumberAnimation { target: shift; property: "x"; to: -8; duration: 70 }
            NumberAnimation { target: shift; property: "x"; to: 0; duration: 60 }
        }

        Column {
            id: form
            anchors.top: parent.top
            anchors.topMargin: 24
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width - 48
            spacing: 12

            Field {
                id: user
                width: parent.width
                icon: ""
                placeholder: "Пользователь"
                fontName: root.fontName
                fg: root.fg
                muted: root.muted
                accent: root.accent
                text: userModel.lastUser
                onAccepted: pass.input.forceActiveFocus()
                KeyNavigation.tab: pass.input
            }

            Field {
                id: pass
                width: parent.width
                icon: ""
                placeholder: "Пароль"
                password: true
                fontName: root.fontName
                fg: root.fg
                muted: root.muted
                accent: root.accent
                onAccepted: root.login()
                KeyNavigation.tab: user.input
            }

            Item {
                width: parent.width
                height: 28

                Text {
                    id: sess
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    property string sname: sessions.count > 0 && sessions.itemAt(root.session) ? sessions.itemAt(root.session).sname : ""
                    text: "  " + sname + "  "
                    color: sessArea.containsMouse ? root.accent : root.muted
                    font.family: root.fontName
                    font.pixelSize: 13

                    MouseArea {
                        id: sessArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: if (sessions.count > 0) root.session = (root.session + 1) % sessions.count
                    }
                }

                Text {
                    id: busy
                    anchors.right: go.left
                    anchors.rightMargin: 10
                    anchors.verticalCenter: parent.verticalCenter
                    visible: false
                    text: "..."
                    color: root.muted
                    font.family: root.fontName
                    font.pixelSize: 13
                }

                Rectangle {
                    id: go
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    width: 44
                    height: 28
                    radius: 6
                    color: goArea.containsMouse ? root.accent : root.pill

                    Text {
                        anchors.centerIn: parent
                        text: ""
                        color: goArea.containsMouse ? root.bgc : root.fg
                        font.family: root.fontName
                        font.pixelSize: 14
                    }

                    MouseArea {
                        id: goArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.login()
                    }
                }
            }

            Text {
                id: err
                width: parent.width
                height: text.length > 0 ? implicitHeight : 0
                horizontalAlignment: Text.AlignHCenter
                color: root.red
                font.family: root.fontName
                font.pixelSize: 13
            }
        }
    }

    Row {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.margins: 24
        spacing: 16

        Text {
            property var lay: keyboard.layouts && keyboard.layouts.length > keyboard.currentLayout ? keyboard.layouts[keyboard.currentLayout] : null
            text: "󰌌  " + (lay ? lay.shortName : "")
            visible: lay !== null
            color: kbArea.containsMouse ? root.accent : root.fg
            font.family: root.fontName
            font.pixelSize: 14

            MouseArea {
                id: kbArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: keyboard.currentLayout = (keyboard.currentLayout + 1) % keyboard.layouts.length
            }
        }

        Text {
            text: "󰘲 Caps Lock"
            visible: keyboard.capsLock
            color: root.red
            font.family: root.fontName
            font.pixelSize: 14
        }
    }

    Row {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 24
        spacing: 22

        Repeater {
            model: [
                { icon: "󰒲", act: "suspend", ok: sddm.canSuspend },
                { icon: "󰜉", act: "reboot", ok: sddm.canReboot },
                { icon: "󰐥", act: "poweroff", ok: sddm.canPowerOff }
            ]

            delegate: Text {
                visible: modelData.ok
                text: modelData.icon
                color: btn.containsMouse ? (modelData.act === "poweroff" ? root.red : root.accent) : root.fg
                font.family: root.fontName
                font.pixelSize: 22

                MouseArea {
                    id: btn
                    anchors.fill: parent
                    anchors.margins: -6
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (modelData.act === "suspend") sddm.suspend()
                        else if (modelData.act === "reboot") sddm.reboot()
                        else sddm.powerOff()
                    }
                }
            }
        }
    }

    Component.onCompleted: {
        if (user.text.length === 0 && users.count === 1)
            user.text = users.itemAt(0).uname
        if (user.text.length > 0)
            pass.input.forceActiveFocus()
        else
            user.input.forceActiveFocus()
    }
}
