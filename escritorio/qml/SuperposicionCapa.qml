// SuperposicionCapa — la rueda en Wayland con layer-shell (org.kde.layershell): una capa de superposición anclada a
// los cuatro bordes (toda la pantalla, encima de los paneles), con el teclado mientras se ve. Con `residente`, la
// franja del borde derecho es otra capa: lo que se arrastra hasta ahí abre la rueda.
import QtQuick
import QtQuick.Window
import QtQml
import org.kde.layershell 1.0 as LayerShell
import org.kde.kirigami as Kirigami

Window {
    id: ventana
    title: "Muyu"
    color: "transparent"
    visible: inicialVisible
    LayerShell.Window.scope: "muyu"
    LayerShell.Window.layer: LayerShell.Window.LayerOverlay
    LayerShell.Window.anchors: LayerShell.Window.AnchorTop | LayerShell.Window.AnchorBottom | LayerShell.Window.AnchorLeft | LayerShell.Window.AnchorRight
    LayerShell.Window.exclusionZone: -1
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityExclusive

    function mostrarRueda() {
        contenido.preparar()
        ventana.visible = true
        rueda.fijarVisible(true)
    }
    function ocultar() {
        ventana.visible = false
        ventanaRueda.ocultada()
    }
    Component.onCompleted: if (visible) rueda.fijarVisible(true)
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
            width: Kirigami.Units.smallSpacing * 2
            height: Math.round(Screen.height * 0.3)
            visible: true
            LayerShell.Window.scope: "muyu-borde"
            LayerShell.Window.layer: LayerShell.Window.LayerTop
            LayerShell.Window.anchors: LayerShell.Window.AnchorRight
            LayerShell.Window.exclusionZone: -1
            LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityNone
            Borde { anchors.fill: parent; onLlega: ventana.mostrarRueda() }
        }
    }
}
