// EditorCaja — el editor de un parámetro con la pista «caja» (un rectángulo x,y,ancho,alto en píxeles de la imagen de
// entrada, ya girada según su EXIF): la imagen, el rectángulo con sus cuatro esquinas para estirar y el cuerpo para
// moverlo, lo de fuera oscurecido, la proporción en un desplegable y el tamaño en píxeles. `caja` es el texto que
// recibe el motor; `proporcion`, la elegida («libre» o «a:b»).
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

ColumnLayout {
    id: editor
    property url fuente
    property var proporciones: ["libre"]
    property string proporcion: "libre"
    readonly property color sombra: Qt.rgba(0, 0, 0, 0.55)        // lo que queda fuera del recorte
    // la selección normalizada al área pintada de la imagen [0, 1]
    property real sx: 0.1
    property real sy: 0.1
    property real sw: 0.8
    property real sh: 0.8
    // el tamaño real en píxeles (ya girada según su EXIF): la imagen se carga entera, sin reducir, para que el
    // rectángulo salga en las coordenadas del archivo y no en las de una copia (una foto de 4000 px no es una de 1600)
    readonly property size real: imagen.status === Image.Ready && imagen.implicitWidth > 0
                                 ? Qt.size(imagen.implicitWidth, imagen.implicitHeight) : Qt.size(0, 0)
    readonly property string caja: real.width > 0
        ? [Math.round(sx * real.width), Math.round(sy * real.height), Math.max(1, Math.round(sw * real.width)), Math.max(1, Math.round(sh * real.height))].join(",")
        : ""
    spacing: Kirigami.Units.smallSpacing

    function razon() {
        if (proporcion === "libre" || !proporcion.includes(":") || real.width <= 0)
            return 0
        const p = proporcion.split(":")
        return (Number(p[0]) / Number(p[1])) * real.height / real.width      // en unidades normalizadas: sw / sh
    }
    function reiniciar() {
        proporcion = proporciones.indexOf("libre") >= 0 ? "libre" : (proporciones[0] || "libre")
        encajar()
    }
    function encajar() {            // la mayor caja centrada con la proporción elegida
        const r = razon()
        if (!r) { sx = 0.05; sy = 0.05; sw = 0.9; sh = 0.9; return }
        if (r >= 1) { sw = 1; sh = 1 / r } else { sh = 1; sw = r }
        if (sh > 1) { sw /= sh; sh = 1 }
        if (sw > 1) { sh /= sw; sw = 1 }
        sx = (1 - sw) / 2; sy = (1 - sh) / 2
    }
    onProporcionChanged: encajar()
    onRealChanged: if (real.width > 0) encajar()

    Item {
        id: lienzo
        Layout.fillWidth: true
        Layout.fillHeight: true
        Image {
            id: imagen
            anchors.fill: parent
            source: editor.fuente
            fillMode: Image.PreserveAspectFit
            autoTransform: true
            asynchronous: true
        }
        // el área pintada de la imagen
        Item {
            id: area
            width: imagen.paintedWidth; height: imagen.paintedHeight
            x: (imagen.width - width) / 2; y: (imagen.height - height) / 2

            Rectangle { color: editor.sombra; x: 0; y: 0; width: area.width; height: editor.sy * area.height }
            Rectangle { color: editor.sombra; x: 0; y: (editor.sy + editor.sh) * area.height; width: area.width; height: area.height - y }
            Rectangle { color: editor.sombra; x: 0; y: editor.sy * area.height; width: editor.sx * area.width; height: editor.sh * area.height }
            Rectangle { color: editor.sombra; x: (editor.sx + editor.sw) * area.width; y: editor.sy * area.height; width: area.width - x; height: editor.sh * area.height }

            Rectangle {
                id: seleccion
                x: editor.sx * area.width; y: editor.sy * area.height
                width: editor.sw * area.width; height: editor.sh * area.height
                color: "transparent"
                border.color: Kirigami.Theme.highlightColor
                border.width: 2
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.SizeAllCursor
                    property point inicio
                    property real ox; property real oy
                    onPressed: mouse => { inicio = mapToItem(area, mouse.x, mouse.y); ox = editor.sx; oy = editor.sy }
                    onPositionChanged: mouse => {
                        const p = mapToItem(area, mouse.x, mouse.y)
                        editor.sx = Math.max(0, Math.min(1 - editor.sw, ox + (p.x - inicio.x) / area.width))
                        editor.sy = Math.max(0, Math.min(1 - editor.sh, oy + (p.y - inicio.y) / area.height))
                    }
                }
                Repeater {
                    model: [[0, 0], [1, 0], [0, 1], [1, 1]]
                    delegate: Rectangle {
                        required property var modelData
                        readonly property int ex: modelData[0]
                        readonly property int ey: modelData[1]
                        width: Kirigami.Units.gridUnit * 0.8; height: width; radius: width / 2
                        x: ex * seleccion.width - width / 2; y: ey * seleccion.height - height / 2
                        color: Kirigami.Theme.highlightColor
                        border.color: Kirigami.Theme.highlightedTextColor
                        MouseArea {
                            anchors.fill: parent
                            anchors.margins: -Kirigami.Units.smallSpacing
                            cursorShape: (parent.ex === parent.ey) ? Qt.SizeFDiagCursor : Qt.SizeBDiagCursor
                            onPositionChanged: mouse => {
                                const p = mapToItem(area, mouse.x, mouse.y)
                                const nx = Math.max(0, Math.min(1, p.x / area.width)), ny = Math.max(0, Math.min(1, p.y / area.height))
                                // la esquina opuesta queda fija
                                const fx = parent.ex ? editor.sx : editor.sx + editor.sw
                                const fy = parent.ey ? editor.sy : editor.sy + editor.sh
                                let w = Math.max(0.02, Math.abs(nx - fx)), h = Math.max(0.02, Math.abs(ny - fy))
                                const r = editor.razon()
                                if (r) {
                                    if (w / h > r) w = h * r; else h = w / r
                                    const mw = parent.ex ? 1 - fx : fx, mh = parent.ey ? 1 - fy : fy
                                    if (w > mw) { w = mw; h = w / r }
                                    if (h > mh) { h = mh; w = h * r }
                                }
                                editor.sw = w; editor.sh = h
                                editor.sx = parent.ex ? fx : fx - w
                                editor.sy = parent.ey ? fy : fy - h
                            }
                        }
                    }
                }
            }
        }
    }
    RowLayout {
        Layout.fillWidth: true
        QQC2.Label { text: "Proporción:" }
        QQC2.ComboBox {
            id: elegirProporcion
            model: editor.proporciones.map(p => p === "libre" ? "Libre" : p)
            currentIndex: Math.max(0, editor.proporciones.indexOf(editor.proporcion))
            onActivated: i => editor.proporcion = editor.proporciones[i]
            Accessible.name: "Proporción del recorte"
        }
        Item { Layout.fillWidth: true }
        QQC2.Label {
            text: editor.caja ? editor.caja.split(",")[2] + " × " + editor.caja.split(",")[3] + " px" : ""
            color: Kirigami.Theme.disabledTextColor
        }
        QQC2.ToolButton { icon.name: "edit-reset"; text: "Restablecer"; display: QQC2.AbstractButton.IconOnly; onClicked: editor.encajar()
                          QQC2.ToolTip.text: text; QQC2.ToolTip.visible: hovered }
    }
}
