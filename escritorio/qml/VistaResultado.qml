// VistaResultado — la vista previa del panel de opciones: lo que la operación daría (la operación de verdad sobre una
// copia en la caché) o, con «Ver el original» o mientras le falte algo a la operación, el archivo de entrada. Un PDF va
// en el visor de gui-comun (VistaPdf: desplazar, zoom, miniaturas, seleccionar y copiar texto, buscar); una imagen se
// amplía con la rueda del ratón y se arrastra; un texto (TXT, Markdown, subtítulos) se lee entero.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import GuiComun

ColumnLayout {
    id: vr
    spacing: Kirigami.Units.smallSpacing
    readonly property string tipo: rueda.vistaTipo

    RowLayout {
        Layout.fillWidth: true
        QQC2.Switch {
            id: original
            text: "Ver el original"
            enabled: rueda.vistaEstado === "lista"
            checked: rueda.viendoOriginal
            onToggled: rueda.verOriginal(checked)
            QQC2.ToolTip.text: "Compara: así está ahora · así quedaría"
            QQC2.ToolTip.visible: hovered
        }
        QQC2.BusyIndicator { implicitWidth: Kirigami.Units.iconSizes.medium; implicitHeight: implicitWidth; running: visible; visible: rueda.vistaEstado === "cargando" }
        Item { Layout.fillWidth: true }
        QQC2.Label {
            text: rueda.vistaEstado === "cargando" ? "Calculando…" : rueda.viendoOriginal ? "Original" : rueda.vistaEstado === "lista" ? "Así quedaría" : ""
            color: Kirigami.Theme.disabledTextColor
        }
        QQC2.ToolButton { visible: vr.tipo === "imagen"; icon.name: "zoom-out"; display: QQC2.AbstractButton.IconOnly; text: "Alejar"; onClicked: lienzo.multiplicar(1 / 1.25) }
        QQC2.ToolButton { visible: vr.tipo === "imagen"; icon.name: "zoom-fit-best"; display: QQC2.AbstractButton.IconOnly; text: "Ajustar"; onClicked: lienzo.zoom = 0 }
        QQC2.ToolButton { visible: vr.tipo === "imagen"; icon.name: "zoom-original"; display: QQC2.AbstractButton.IconOnly; text: "Tamaño real"; onClicked: lienzo.zoom = 1 }
        QQC2.ToolButton { visible: vr.tipo === "imagen"; icon.name: "zoom-in"; display: QQC2.AbstractButton.IconOnly; text: "Acercar"; onClicked: lienzo.multiplicar(1.25) }
    }
    Kirigami.InlineMessage {
        Layout.fillWidth: true
        visible: rueda.vistaEstado === "error"
        type: Kirigami.MessageType.Information
        text: rueda.vistaNota + (rueda.vistaTipo ? " Mientras tanto, se ve el original." : "")
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.fillHeight: true
        radius: Kirigami.Units.cornerRadius
        color: Kirigami.Theme.alternateBackgroundColor
        clip: true

        // imagen: rueda del ratón = zoom en el punto; arrastrar = mover
        Flickable {
            id: lienzo
            anchors.fill: parent
            visible: vr.tipo === "imagen"
            property real zoom: 0                                   // 0: ajustar a la vista
            readonly property real ajuste: imagen.implicitWidth > 0 ? Math.min(width / imagen.implicitWidth, height / imagen.implicitHeight, 1) : 1
            readonly property real escala: zoom > 0 ? zoom : ajuste
            function multiplicar(f) { zoom = Math.max(0.05, Math.min(8, escala * f)) }
            contentWidth: Math.max(width, imagen.implicitWidth * escala)
            contentHeight: Math.max(height, imagen.implicitHeight * escala)
            boundsBehavior: Flickable.StopAtBounds
            QQC2.ScrollBar.vertical: QQC2.ScrollBar {}
            QQC2.ScrollBar.horizontal: QQC2.ScrollBar {}
            Image {
                id: imagen
                source: vr.tipo === "imagen" ? rueda.vistaUrl : ""
                width: implicitWidth * lienzo.escala
                height: implicitHeight * lienzo.escala
                x: Math.max(0, (lienzo.contentWidth - width) / 2)
                y: Math.max(0, (lienzo.contentHeight - height) / 2)
                fillMode: Image.PreserveAspectFit
                cache: false
                smooth: true
                mipmap: true
                autoTransform: true
                opacity: rueda.vistaEstado === "cargando" ? 0.6 : 1
            }
            WheelHandler {
                acceptedModifiers: Qt.NoModifier | Qt.ControlModifier
                onWheel: evento => lienzo.multiplicar(evento.angleDelta.y > 0 ? 1.15 : 1 / 1.15)
            }
        }

        VistaPdf {
            anchors.fill: parent
            visible: vr.tipo === "pdf"
            visor: rueda.visorPdf
            miniaturas: false
            mensajeVacio: "Sin páginas"
            explicacionVacia: "No se pudo leer el PDF."
        }

        VistaTexto {
            anchors.fill: parent
            visible: vr.tipo === "texto"
            texto: rueda.vistaContenido
            nombreAccesible: "Vista previa del texto"
        }

        Kirigami.PlaceholderMessage {
            anchors.centerIn: parent
            width: parent.width - Kirigami.Units.gridUnit * 2
            visible: vr.tipo === "" && rueda.vistaEstado !== "cargando"
            icon.name: "view-preview"
            text: "Sin vista previa"
            explanation: rueda.vistaNota || "Este resultado no se puede ver aquí: se ve al aplicar."
        }
    }
}
