// Sector — un sector anular de la rueda (entre dos radios y dos ángulos) con su icono y su etiqueta en el medio.
// Los ángulos van en grados desde las 3 en punto y en el sentido del reloj, como PathAngleArc.
import QtQuick
import QtQuick.Shapes
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Item {
    id: s
    z: resaltado ? 2 : 0                 // la etiqueta del resaltado, encima de los vecinos
    property real cx: 0
    property real cy: 0
    property real radioIn: 0
    property real radioOut: 0
    property real inicio: 0
    property real barrido: 0
    property string icono: ""
    property string etiqueta: ""
    property bool resaltado: false
    property bool enFoco: false          // el teclado está aquí
    property bool apagado: false         // le falta algo a la máquina
    property bool especial: false        // «Más» y «Volver»
    property color fondo: Kirigami.Theme.backgroundColor
    property bool soloIcono: false       // el anillo de las aplicaciones: el icono grande, el nombre en la tarjeta
    property bool marcado: false         // la aplicación de siempre (la que abre Intro)
    property bool forma: true            // la rueda dibuja primero todas las formas y luego todas las etiquetas:
    property bool rotulo: true           // así ninguna forma vecina tapa una etiqueta larga

    readonly property real medio: (inicio + barrido / 2) * Math.PI / 180
    readonly property real radioMedio: (radioIn + radioOut) / 2
    readonly property real cuerda: 2 * radioMedio * Math.sin(Math.min(barrido, 179) * Math.PI / 360)

    Shape {
        anchors.fill: parent
        visible: s.forma
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            fillColor: s.resaltado ? Kirigami.Theme.highlightColor
                     : (s.especial ? Qt.tint(s.fondo, Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.06)) : s.fondo)
            strokeColor: s.enFoco ? Kirigami.Theme.focusColor : "transparent"
            strokeWidth: s.enFoco ? 2 : 0
            Behavior on fillColor { ColorAnimation { duration: Kirigami.Units.shortDuration } }
            PathAngleArc { centerX: s.cx; centerY: s.cy; radiusX: s.radioOut; radiusY: s.radioOut; startAngle: s.inicio; sweepAngle: s.barrido }
            PathAngleArc { centerX: s.cx; centerY: s.cy; radiusX: s.radioIn; radiusY: s.radioIn; startAngle: s.inicio + s.barrido; sweepAngle: -s.barrido; moveToStart: false }
        }
    }

    Column {
        visible: s.rotulo
        x: s.cx + s.radioMedio * Math.cos(s.medio) - width / 2
        y: s.cy + s.radioMedio * Math.sin(s.medio) - height / 2
        spacing: 2
        opacity: s.apagado ? 0.45 : 1
        // a los lados el anillo es angosto en horizontal: el ancho cabe en el sector en ese ángulo
        width: Math.min(s.cuerda - Kirigami.Units.smallSpacing * 2,
                        (s.radioOut - s.radioIn - Kirigami.Units.smallSpacing) / Math.max(Math.abs(Math.cos(s.medio)), 0.4))
        Kirigami.Icon {
            anchors.horizontalCenter: parent.horizontalCenter
            source: s.icono
            width: s.soloIcono ? Kirigami.Units.iconSizes.medium : Kirigami.Units.iconSizes.smallMedium
            height: width
            color: s.resaltado ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
            isMask: s.resaltado && !s.soloIcono
        }
        Rectangle {                      // la marca de la de siempre
            visible: s.marcado
            anchors.horizontalCenter: parent.horizontalCenter
            width: Kirigami.Units.smallSpacing * 1.5; height: width; radius: width / 2
            color: s.resaltado ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.highlightColor
        }
        QQC2.Label {
            visible: !s.soloIcono
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: s.etiqueta
            font.pointSize: Kirigami.Theme.smallFont.pointSize
            font.weight: s.resaltado ? Font.DemiBold : Font.Normal
            color: s.resaltado ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
            wrapMode: Text.Wrap                  // una palabra más larga que el sector se parte antes que salirse
            maximumLineCount: 2
            elide: Text.ElideRight
        }
    }
}
