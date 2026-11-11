// Superposicion — la rueda sin layer-shell (X11, o Wayland sin el módulo de KDE, o las pruebas sin pantalla): una
// ventana transparente, sin marco y encima de todo, a pantalla completa. Con `residente`, la franja del borde.
import QtQuick
import QtQuick.Window
import QtQml
import org.kde.kirigami as Kirigami

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

    ContenidoRueda {
        id: contenido
        anchors.fill: parent
        onCerrar: ventana.ocultar()
    }

    Instantiator {
        active: residente
        delegate: Window {
            title: "Muyu — borde"
            color: "transparent"
            flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus
            width: Kirigami.Units.smallSpacing * 2
            height: Screen.height * 0.3
            x: Screen.width - width
            y: (Screen.height - height) / 2
            visible: true
            Borde { anchors.fill: parent; onLlega: ventana.mostrarRueda() }
        }
    }
}
