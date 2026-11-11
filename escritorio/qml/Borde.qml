// Borde — la franja del borde de la pantalla de la rueda residente: casi invisible; cuando algo arrastrado llega,
// se enciende y abre la rueda (que aparece bajo el puntero y recibe el arrastre).
import QtQuick
import org.kde.kirigami as Kirigami

Item {
    id: borde
    property string lado: "derecha"                  // derecha · izquierda · arriba (pantallas.js)
    readonly property bool vertical: lado !== "arriba"
    signal llega()
    Rectangle {
        x: borde.lado === "derecha" ? parent.width - width : borde.lado === "izquierda" ? 0 : (parent.width - width) / 2
        y: borde.vertical ? (parent.height - height) / 2 : 0
        width: borde.vertical ? (zona.containsDrag ? parent.width : Math.max(2, parent.width / 3)) : parent.width * (zona.containsDrag ? 1 : 0.6)
        height: borde.vertical ? parent.height * (zona.containsDrag ? 1 : 0.6) : (zona.containsDrag ? parent.height : Math.max(2, parent.height / 3))
        radius: Math.min(width, height) / 2
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
