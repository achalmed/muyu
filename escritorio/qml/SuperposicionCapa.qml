// SuperposicionCapa — la rueda en Wayland con layer-shell (org.kde.layershell): una capa de superposición anclada a
// los cuatro bordes (toda la pantalla, encima de los paneles), con el teclado mientras se ve. Con varias pantallas, la
// elige KWin cada vez que aparece (ScreenFromCompositor: su pantalla activa, la del puntero), no la principal. Con
// `residente`, una franja en cada pantalla, en el borde que no toca a otro monitor (pantallas.js).
import QtQuick
import QtQuick.Window
import QtQml
import org.kde.layershell 1.0 as LayerShell
import org.kde.kirigami as Kirigami
import "pantallas.js" as Pantallas

Window {
    id: ventana
    title: "Muyu"
    color: "transparent"
    visible: inicialVisible
    LayerShell.Window.scope: "muyu"
    LayerShell.Window.wantsToBeOnActiveScreen: true          // la pantalla la elige KWin: la activa, la del puntero
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
    onScreenChanged: if (depurar) console.log("muyu: la rueda está en " + ventana.screen.name)

    ContenidoRueda {
        id: contenido
        anchors.fill: parent
        onCerrar: ventana.ocultar()
    }

    // una franja por pantalla (también las que se conectan después)
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
            width: vertical ? Kirigami.Units.smallSpacing * 2 : Math.round(modelData.geometry.width * 0.25)
            height: vertical ? Math.round(modelData.geometry.height * 0.3) : Kirigami.Units.smallSpacing * 2
            visible: true
            LayerShell.Window.scope: "muyu-borde"
            LayerShell.Window.screen: modelData                  // el QScreen de verdad: manda sobre el de la ventana
            LayerShell.Window.layer: LayerShell.Window.LayerTop
            LayerShell.Window.anchors: lado === "derecha" ? LayerShell.Window.AnchorRight
                                     : lado === "izquierda" ? LayerShell.Window.AnchorLeft : LayerShell.Window.AnchorTop
            LayerShell.Window.exclusionZone: -1
            LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityNone
            Borde { anchors.fill: parent; lado: franja.lado; onLlega: ventana.mostrarRueda() }
            // primero la pantalla, después visible: si no, la capa se crea en la pantalla por omisión
            Component.onCompleted: if (depurar) console.log("muyu: franja en " + modelData.name + " (" + lado + ")")
        }
    }
}
