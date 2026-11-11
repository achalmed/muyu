// Superposicion — la rueda sin layer-shell (X11, o Wayland sin el módulo de KDE, o las pruebas sin pantalla): una
// ventana transparente, sin marco y encima de todo, a pantalla completa. Con `residente`, la franja del borde.
import QtQuick
import QtQuick.Window
import QtQml
import org.kde.kirigami as Kirigami
import "pantallas.js" as Pantallas

Window {
    id: ventana
    title: "Muyu"
    color: "transparent"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
    width: 1280
    height: 860
    visible: inicialVisible
    visibility: visible && Qt.platform.pluginName !== "offscreen" ? Window.FullScreen : Window.Windowed

    function mostrarRueda() {
        const i = ventanaRueda.pantallaDelPuntero()      // en X11 se sabe dónde está el puntero: esa pantalla
        if (i >= 0 && i < Qt.application.screens.length) {
            const g = ventanaRueda.geometria(Qt.application.screens[i].name)   // X11: a pantalla completa en esa
            if (g.length) { ventana.x = g[0]; ventana.y = g[1] }
        }
        contenido.preparar()
        ventana.visible = true
        ventana.requestActivate()
        rueda.fijarVisible(true)
    }
    function ocultar() {
        ventana.visible = false
        ventanaRueda.ocultada()
    }
    Component.onCompleted: if (visible) { rueda.fijarVisible(true); requestActivate() }
    Connections { target: rueda; function onMostrar() { ventana.mostrarRueda() } }
    onScreenChanged: if (depurar) console.log("muyu: la rueda está en " + ventana.screen.name)

    ContenidoRueda {
        id: contenido
        anchors.fill: parent
        onCerrar: ventana.ocultar()
    }

    // una franja por pantalla, en el borde que no toca a otro monitor
    Instantiator {
        active: residente
        model: residente ? pantallasQt : []
        delegate: Window {
            id: franja
            required property var modelData
            readonly property string lado: Pantallas.lado(modelData, pantallasQt)
            readonly property bool vertical: lado !== "arriba"
            title: "Muyu — borde"
            color: "transparent"
            flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus
            width: vertical ? Kirigami.Units.smallSpacing * 2 : Math.round(modelData.geometry.width * 0.25)
            height: vertical ? Math.round(modelData.geometry.height * 0.3) : Kirigami.Units.smallSpacing * 2
            x: modelData.geometry.x + (lado === "derecha" ? modelData.geometry.width - width : lado === "izquierda" ? 0 : (modelData.geometry.width - width) / 2)
            y: modelData.geometry.y + (vertical ? (modelData.geometry.height - height) / 2 : 0)
            visible: true
            Borde { anchors.fill: parent; lado: parent.lado; onLlega: ventana.mostrarRueda() }
            Component.onCompleted: if (depurar) console.log("muyu: franja en " + modelData.name + " (" + lado + ")")
        }
    }
}
