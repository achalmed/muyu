// Borde — la franja del borde de la pantalla de la rueda residente: casi invisible; cuando algo arrastrado llega,
// se enciende y abre la rueda (que aparece bajo el puntero y recibe el arrastre).
import QtQuick
import org.kde.kirigami as Kirigami

Item {
    id: borde
    signal llega()
    Rectangle {
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        width: zona.containsDrag ? parent.width : Math.max(2, parent.width / 3)
        height: parent.height * (zona.containsDrag ? 1 : 0.6)
        radius: width / 2
        color: Kirigami.Theme.highlightColor
        opacity: zona.containsDrag ? 0.9 : 0.35
        Behavior on width { NumberAnimation { duration: Kirigami.Units.shortDuration } }
        Behavior on height { NumberAnimation { duration: Kirigami.Units.shortDuration } }
    }
    DropArea {
        id: zona
        anchors.fill: parent
        onEntered: drag => { drag.accept(Qt.CopyAction); borde.llega() }
    }
}
