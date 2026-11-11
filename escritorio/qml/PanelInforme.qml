// PanelInforme — lo que dijo una herramienta de información (los metadatos de un archivo, la información de un PDF o
// de un vídeo, una suma de verificación, las firmas…): una fila por dato, agrupadas por archivo, con un buscador y
// «Copiar todo». Los datos llegan aplanados del controlador (`rueda.informe`); aquí no se nombra ninguna operación.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Rectangle {
    id: panel
    signal cerrar()
    radius: Kirigami.Units.cornerRadius * 2
    color: Kirigami.Theme.backgroundColor
    border.color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.15)
    Kirigami.Theme.colorSet: Kirigami.Theme.Window
    Kirigami.Theme.inherit: false

    function llenar() {
        filas.clear()
        const f = buscar.text.toLowerCase()
        for (const bloque of rueda.informe)
            for (const fila of bloque.filas)
                if (!f || (fila.clave + " " + fila.valor).toLowerCase().includes(f))
                    filas.append({seccion: bloque.entrada, clave: fila.clave, valor: fila.valor})
    }
    ListModel { id: filas }
    Connections { target: rueda; function onCambiada() { panel.llenar() } }
    Component.onCompleted: llenar()
    MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons; onWheel: wheel => wheel.accepted = false }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Kirigami.Units.gridUnit * 0.7
        spacing: Kirigami.Units.smallSpacing
        RowLayout {
            Layout.fillWidth: true
            BotonCerrar { visible: rueda.cerrarIzquierda; onClicked: panel.cerrar() }
            Kirigami.Icon { source: "documentinfo"; Layout.preferredWidth: Kirigami.Units.iconSizes.medium; Layout.preferredHeight: Layout.preferredWidth }
            Kirigami.Heading { Layout.fillWidth: true; level: 3; text: rueda.mensaje; elide: Text.ElideRight }
            BotonCerrar { visible: !rueda.cerrarIzquierda; onClicked: panel.cerrar() }
        }
        Kirigami.SearchField {
            id: buscar
            Layout.fillWidth: true
            placeholderText: "Buscar en el informe…"
            onTextChanged: panel.llenar()
        }
        QQC2.ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            ListView {
                id: lista
                model: filas
                clip: true
                section.property: "seccion"
                section.delegate: Kirigami.ListSectionHeader { width: lista.width; text: section; visible: rueda.informe.length > 1 }
                delegate: QQC2.ItemDelegate {
                    required property string clave
                    required property string valor
                    width: lista.width
                    contentItem: RowLayout {
                        QQC2.Label {
                            Layout.preferredWidth: lista.width * 0.38
                            visible: parent.parent.clave !== ""
                            text: parent.parent.clave
                            color: Kirigami.Theme.disabledTextColor
                            wrapMode: Text.WrapAnywhere
                        }
                        QQC2.Label {
                            Layout.fillWidth: true
                            text: parent.parent.valor
                            wrapMode: Text.WrapAnywhere
                            textFormat: Text.PlainText
                        }
                    }
                    onClicked: { buscar.forceActiveFocus(); }
                }
                Kirigami.PlaceholderMessage {
                    anchors.centerIn: parent
                    visible: lista.count === 0
                    text: buscar.text ? "Nada coincide" : "Sin datos"
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            QQC2.Label { Layout.fillWidth: true; text: filas.count + " datos"; color: Kirigami.Theme.disabledTextColor }
            QQC2.Button { text: "Copiar todo"; icon.name: "edit-copy"; onClicked: rueda.copiarInforme() }
            QQC2.Button { text: "Cerrar"; icon.name: "dialog-close"; onClicked: panel.cerrar() }
        }
    }
}
