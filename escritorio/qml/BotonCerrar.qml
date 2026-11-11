// BotonCerrar — el cerrar de los paneles de la rueda con el aspecto del de las ventanas de la sesión: un punto del
// color negativo del tema que muestra la cruz al pasar encima (como la decoración de KWin al estilo macOS), y en el
// mismo lado que ella (`rueda.cerrarIzquierda`, leído de ButtonsOnLeft en kwinrc). Quien lo usa lo pone a un lado u otro.
import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

QQC2.AbstractButton {
    id: boton
    property string texto: "Cerrar (Esc)"
    implicitWidth: Math.round(Kirigami.Units.gridUnit * 0.8)
    implicitHeight: implicitWidth
    hoverEnabled: true
    focusPolicy: Qt.NoFocus
    Accessible.name: texto
    QQC2.ToolTip.text: texto
    QQC2.ToolTip.visible: hovered
    QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
    contentItem: Item {}
    background: Rectangle {
        radius: width / 2
        color: boton.pressed ? Qt.darker(Kirigami.Theme.negativeTextColor, 1.25) : Kirigami.Theme.negativeTextColor
        border.color: Qt.darker(Kirigami.Theme.negativeTextColor, 1.3)
        border.width: 1
        Kirigami.Icon {
            anchors.centerIn: parent
            width: parent.width * 0.7
            height: width
            source: "window-close-symbolic"
            isMask: true
            color: Qt.darker(Kirigami.Theme.negativeTextColor, 2.4)
            visible: boton.hovered
        }
    }
}
