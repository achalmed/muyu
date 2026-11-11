// ContenidoRueda — la rueda de Muyu: el centro (lo que se suelta, el trabajo en curso, el resultado que se arrastra
// fuera), el anillo interior «Convertir a», el exterior «Herramientas», la tarjeta de abajo (qué hace el sector bajo el
// puntero, el mensaje, Abrir · Mostrar · Deshacer · Volver) y el panel de opciones. Todo lo que ofrece sale del motor
// (`rueda.interior`, `rueda.exterior`): aquí no se nombra ninguna operación.
//
// Se usa con el ratón (clic: correr; clic derecho: con opciones), soltando encima (desde Dolphin, Krusader o el escritorio)
// y con el teclado: ← → recorren los sectores, Intro corre, Menú o Espacio abre las opciones, 1–9 eligen en el anillo
// interior, Retroceso vuelve al archivo anterior, Ctrl+Z deshace, Esc cierra (un trabajo en curso sigue y avisa al acabar).
import QtQuick
import QtQuick.Layouts
import QtQuick.Shapes
import QtQuick.Effects
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

FocusScope {
    id: raiz
    signal cerrar()

    readonly property real u: Kirigami.Units.gridUnit
    readonly property real r0: u * 4.4                 // el centro
    readonly property real r1a: r0 + 5                 // anillo interior
    readonly property real r1b: u * 8.4
    readonly property real r2a: r1b + 5                // anillo exterior
    readonly property real r2b: u * 13
    readonly property real r3a: r2b + 5                // anillo de afuera: «Abrir con…», solo iconos
    readonly property real r3b: r2b + u * 2.7
    readonly property real borde: rueda.apps.length ? r3b : r2b
    readonly property real margen: u * 1.5
    // el centro de la rueda: el de la ventana hasta que el puntero dice dónde está (solo justo al aparecer)
    property point puesto
    property bool colocada: false
    property bool aTiempo: true
    readonly property point centro: colocada ? puesto : Qt.point(width / 2, height / 2 - u * 2)
    property var hover: null                           // {anillo, indice, clave}
    property int foco: -1                              // el sector del teclado, en orden: interior y luego exterior
    property var panel: null                           // el sector cuyas opciones están abiertas
    property bool verInforme: false                    // el panel con lo que dijo una herramienta de información
    readonly property bool ampliado: panel !== null && panelOpciones.ampliado
    readonly property var todos: rueda.apps.map((s, i) => ({anillo: "apps", indice: i, s: s})).concat(rueda.interior.map((s, i) => ({anillo: "interior", indice: i, s: s})))
                                .concat(rueda.exterior.map((s, i) => ({anillo: "exterior", indice: i, s: s})))
    readonly property var sectorVisto: hover ? (hover.anillo === "interior" ? rueda.interior[hover.indice]
                                              : hover.anillo === "apps" ? rueda.apps[hover.indice] : rueda.exterior[hover.indice])
                                     : (foco >= 0 && foco < todos.length ? todos[foco].s : null)

    focus: true

    // --- al mostrarse: bajo el puntero, si llega pronto (Wayland manda la posición al aparecer)
    function preparar() {
        colocada = false
        aTiempo = true
        hover = null
        foco = -1
        panel = null
        colocacion.restart()
        aparecer.restart()
        rueda.refrescarOkular()
        raiz.forceActiveFocus()
    }
    function colocar(x, y) {
        if (colocada || !aTiempo || width === 0 || Qt.platform.pluginName === "offscreen")   // sin pantalla no hay puntero
            return
        const rx = borde + margen, abajo = u * 6
        puesto = Qt.point(Math.max(rx, Math.min(width - rx, x)), Math.max(rx, Math.min(height - rx - abajo, y)))
        colocada = true
    }
    Timer { id: colocacion; interval: 600; onTriggered: raiz.aTiempo = false }
    Component.onCompleted: { preparar(); Qt.callLater(abrirPrueba) }

    // pruebas y capturas: RAPHI_RUEDA_PANEL=exterior:2 abre las opciones de ese sector en cuanto hay anillos
    function abrirPrueba() {
        if (pruebaPanel === "" || rueda.estado !== "lista" || raiz.panel)
            return
        const partes = pruebaPanel.split(":"), lista = partes[0] === "interior" ? rueda.interior : rueda.exterior
        if (lista.length > Number(partes[1])) {
            raiz.panel = rueda.sector(lista[Number(partes[1])].clave)
            panelOpciones.ampliado = partes[2] === "ampliado"
        }
    }

    // --- geometría
    function sectorEn(x, y) {
        const dx = x - centro.x, dy = y - centro.y, d = Math.sqrt(dx * dx + dy * dy)
        let anillo = "", lista = []
        if (d < r0)
            return {anillo: "centro", indice: -1, clave: ""}
        if (d >= r1a - 2 && d <= r1b + 2) { anillo = "interior"; lista = rueda.interior }
        else if (d >= r2a - 2 && d <= r2b + 2) { anillo = "exterior"; lista = rueda.exterior }
        else if (d >= r3a - 2 && d <= r3b + 2) { anillo = "apps"; lista = rueda.apps }
        if (!anillo || lista.length === 0)
            return null
        const paso = 360 / lista.length
        const a = ((Math.atan2(dx, -dy) * 180 / Math.PI) + 360 + paso / 2) % 360
        const i = Math.min(lista.length - 1, Math.floor(a / paso))
        return {anillo: anillo, indice: i, clave: lista[i].clave}
    }
    // lo que trae un arrastre: sus URL (archivos de Dolphin, un enlace del navegador) o los enlaces de un texto
    function soltado(evento) {
        if (evento.hasUrls && evento.urls.length)
            return evento.urls.map(u => String(u))
        if (evento.hasText)
            return String(evento.text).split(/\s+/).filter(t => /^https?:\/\//.test(t))
        return []
    }
    function dentro(x, y) {
        const dx = x - centro.x, dy = y - centro.y
        return Math.sqrt(dx * dx + dy * dy) <= borde + 4
    }
    function elegir(clave, conOpciones) {
        if (clave)
            rueda.elegir(clave, conOpciones)
    }

    // --- con el panel abierto, si no cabe a ningún lado de la rueda, la rueda se aparta
    onPanelChanged: if (panel) { verInforme = false; Qt.callLater(acomodar) }
    function acomodar() {
        const ancho = panelOpciones.width, hace = borde * 2 + u + ancho + margen * 2
        const derecha = centro.x + borde + u + ancho + margen <= width
        const izquierda = centro.x - borde - u - ancho >= margen
        if (width >= hace && !derecha && !izquierda) {
            puesto = Qt.point(margen + borde + (width - hace) / 2, centro.y)
            colocada = true
        }
    }

    // --- pedir opciones: el panel
    Connections {
        target: rueda
        function onAbierto(nombre) { raiz.cerrar() }
        function onPedirOpciones(sector) { raiz.panel = sector }
        function onCambiada() {
            if (raiz.foco >= raiz.todos.length)
                raiz.foco = -1
            raiz.abrirPrueba()
        }
    }

    // --- el puntero sobre la ventana: elegir, cerrar fuera
    MouseArea {
        id: puntero
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onPositionChanged: mouse => {
            raiz.colocar(mouse.x, mouse.y)
            const s = raiz.sectorEn(mouse.x, mouse.y)
            raiz.hover = s && s.clave ? s : null
        }
        onExited: raiz.hover = null
        onClicked: mouse => {
            const s = raiz.sectorEn(mouse.x, mouse.y)
            if (s && s.clave)
                raiz.elegir(s.clave, mouse.button === Qt.RightButton)
            else if (!s && !raiz.dentro(mouse.x, mouse.y) && !tarjeta.contains(mapToItem(tarjeta, mouse.x, mouse.y)))
                raiz.cerrar()
        }
    }

    // --- lo que se suelta encima (de Dolphin, de Krusader, del escritorio o el resultado de la propia rueda)
    DropArea {
        anchors.fill: parent
        onEntered: drag => {
            raiz.colocar(drag.x, drag.y)
            const lista = raiz.soltado(drag)
            if (lista.length)
                rueda.cargar(lista)
            drag.accept(Qt.CopyAction)
        }
        onPositionChanged: drag => {
            const s = raiz.sectorEn(drag.x, drag.y)
            raiz.hover = s && s.clave ? s : null
            if (raiz.hover && raiz.hover.clave.startsWith("mas:") || raiz.hover && raiz.hover.clave.startsWith("volver:"))
                resorte.restart()
            else
                resorte.stop()
        }
        onExited: { raiz.hover = null; resorte.stop() }
        onDropped: drop => {
            const lista = raiz.soltado(drop)
            if (lista.length)
                rueda.cargar(lista)
            const s = raiz.sectorEn(drop.x, drop.y)
            raiz.hover = null
            if (s && s.clave)
                raiz.elegir(s.clave, false)
            drop.accept(Qt.CopyAction)
        }
    }
    Timer { id: resorte; interval: 650; onTriggered: if (raiz.hover) rueda.elegir(raiz.hover.clave, false) }   // «Más» se abre al pasar encima arrastrando

    // --- la rueda
    Item {
        id: rueda_
        x: raiz.centro.x - raiz.borde
        y: raiz.centro.y - raiz.borde
        width: raiz.borde * 2
        height: width
        transformOrigin: Item.Center
        visible: opacity > 0 && !raiz.ampliado
        Behavior on x { enabled: raiz.colocada; NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic } }
        Behavior on y { enabled: raiz.colocada; NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic } }
        ParallelAnimation {
            id: aparecer
            NumberAnimation { target: rueda_; property: "scale"; from: 0.82; to: 1; duration: Kirigami.Units.longDuration; easing.type: Easing.OutBack }
            NumberAnimation { target: rueda_; property: "opacity"; from: 0; to: 1; duration: Kirigami.Units.shortDuration }
        }

        // la sombra de toda la rueda
        Rectangle {
            id: disco
            anchors.fill: parent
            radius: width / 2
            color: Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g, Kirigami.Theme.backgroundColor.b, 0.55)
            visible: false
        }
        MultiEffect {
            source: disco
            anchors.fill: disco
            shadowEnabled: true
            shadowBlur: 1.0
            shadowOpacity: 0.45
            shadowVerticalOffset: raiz.u * 0.3
            shadowColor: "black"
        }

        readonly property real c: raiz.borde
        Repeater {
            model: rueda.interior
            delegate: Sector {
                rotulo: false
                required property var modelData
                required property int index
                anchors.fill: parent
                cx: rueda_.c; cy: rueda_.c
                radioIn: raiz.r1a; radioOut: raiz.r1b
                readonly property real paso: 360 / Math.max(1, rueda.interior.length)
                inicio: -90 - paso / 2 + index * paso + 0.8
                barrido: paso - 1.6
                icono: modelData.icono
                etiqueta: modelData.etiqueta
                especial: modelData.mas
                apagado: modelData.faltan.length > 0
                fondo: Qt.tint(Kirigami.Theme.backgroundColor, Qt.rgba(Kirigami.Theme.highlightColor.r, Kirigami.Theme.highlightColor.g, Kirigami.Theme.highlightColor.b, 0.10))
                resaltado: raiz.hover !== null && raiz.hover.anillo === "interior" && raiz.hover.indice === index
                enFoco: raiz.foco === rueda.apps.length + index
            }
        }
        Repeater {
            model: rueda.exterior
            delegate: Sector {
                rotulo: false
                required property var modelData
                required property int index
                anchors.fill: parent
                cx: rueda_.c; cy: rueda_.c
                radioIn: raiz.r2a; radioOut: raiz.r2b
                readonly property real paso: 360 / Math.max(1, rueda.exterior.length)
                inicio: -90 - paso / 2 + index * paso + 0.6
                barrido: paso - 1.2
                icono: modelData.icono
                etiqueta: modelData.etiqueta
                especial: modelData.mas
                apagado: modelData.faltan.length > 0
                resaltado: raiz.hover !== null && raiz.hover.anillo === "exterior" && raiz.hover.indice === index
                enFoco: raiz.foco === rueda.apps.length + rueda.interior.length + index
            }
        }

        Repeater {
            model: rueda.apps
            delegate: Sector {
                required property var modelData
                required property int index
                rotulo: false
                anchors.fill: parent
                cx: rueda_.c; cy: rueda_.c
                radioIn: raiz.r3a; radioOut: raiz.r3b
                readonly property real paso: 360 / Math.max(1, rueda.apps.length)
                inicio: -90 - paso / 2 + index * paso + 0.5
                barrido: paso - 1
                icono: modelData.icono
                etiqueta: ""
                soloIcono: true
                marcado: modelData.predeterminada
                especial: modelData.mas
                fondo: Qt.tint(Kirigami.Theme.backgroundColor, Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.04))
                resaltado: raiz.hover !== null && raiz.hover.anillo === "apps" && raiz.hover.indice === index
                enFoco: raiz.foco === index
            }
        }
        // las etiquetas, encima de todas las formas
        Repeater {
            model: rueda.apps
            delegate: Sector {
                required property var modelData
                required property int index
                forma: false
                anchors.fill: parent
                cx: rueda_.c; cy: rueda_.c
                radioIn: raiz.r3a; radioOut: raiz.r3b
                readonly property real paso: 360 / Math.max(1, rueda.apps.length)
                inicio: -90 - paso / 2 + index * paso + 0.5
                barrido: paso - 1
                icono: modelData.icono
                etiqueta: ""
                soloIcono: true
                marcado: modelData.predeterminada
                especial: modelData.mas
                fondo: Qt.tint(Kirigami.Theme.backgroundColor, Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.04))
                resaltado: raiz.hover !== null && raiz.hover.anillo === "apps" && raiz.hover.indice === index
                enFoco: raiz.foco === index
            }
        }
        Repeater {
            model: rueda.interior
            delegate: Sector {
                forma: false
                required property var modelData
                required property int index
                anchors.fill: parent
                cx: rueda_.c; cy: rueda_.c
                radioIn: raiz.r1a; radioOut: raiz.r1b
                readonly property real paso: 360 / Math.max(1, rueda.interior.length)
                inicio: -90 - paso / 2 + index * paso + 0.8
                barrido: paso - 1.6
                icono: modelData.icono
                etiqueta: modelData.etiqueta
                especial: modelData.mas
                apagado: modelData.faltan.length > 0
                fondo: Qt.tint(Kirigami.Theme.backgroundColor, Qt.rgba(Kirigami.Theme.highlightColor.r, Kirigami.Theme.highlightColor.g, Kirigami.Theme.highlightColor.b, 0.10))
                resaltado: raiz.hover !== null && raiz.hover.anillo === "interior" && raiz.hover.indice === index
                enFoco: raiz.foco === rueda.apps.length + index
            }
        }
        Repeater {
            model: rueda.exterior
            delegate: Sector {
                forma: false
                required property var modelData
                required property int index
                anchors.fill: parent
                cx: rueda_.c; cy: rueda_.c
                radioIn: raiz.r2a; radioOut: raiz.r2b
                readonly property real paso: 360 / Math.max(1, rueda.exterior.length)
                inicio: -90 - paso / 2 + index * paso + 0.6
                barrido: paso - 1.2
                icono: modelData.icono
                etiqueta: modelData.etiqueta
                especial: modelData.mas
                apagado: modelData.faltan.length > 0
                resaltado: raiz.hover !== null && raiz.hover.anillo === "exterior" && raiz.hover.indice === index
                enFoco: raiz.foco === rueda.apps.length + rueda.interior.length + index
            }
        }

        // el anillo vacío mientras llegan las opciones (o si no hay ninguna)
        Rectangle {
            visible: rueda.interior.length === 0 && rueda.exterior.length === 0
            anchors.centerIn: parent
            width: raiz.borde * 2; height: width; radius: width / 2
            color: Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g, Kirigami.Theme.backgroundColor.b, 0.82)
            border.color: Kirigami.Theme.highlightColor
            border.width: rueda.estado === "vacia" ? 2 : 0
            QQC2.Label {
                anchors.horizontalCenter: parent.horizontalCenter
                y: parent.height - raiz.u * 3.2
                text: rueda.estado === "cargando" ? "Preguntando al motor…" : "Suelta un archivo o una carpeta"
                color: Kirigami.Theme.disabledTextColor
            }
        }

        // --- el centro
        Rectangle {
            id: centro_
            anchors.centerIn: parent
            width: raiz.r0 * 2; height: width; radius: width / 2
            color: Kirigami.Theme.backgroundColor
            border.color: rueda.estado === "hecha" ? Kirigami.Theme.positiveTextColor
                        : rueda.estado === "error" ? Kirigami.Theme.negativeTextColor : Qt.rgba(0, 0, 0, 0)
            border.width: 2

            // la miniatura (o el icono del tipo) — se arrastra fuera
            Item {
                id: miniatura
                anchors.centerIn: parent
                anchors.verticalCenterOffset: -raiz.u * 0.6
                width: raiz.r0 * 1.05; height: width
                visible: rueda.estado !== "corriendo" && rueda.estado !== "cargando"
                Image {
                    id: imagen
                    anchors.fill: parent
                    visible: rueda.primeraEsImagen && status === Image.Ready
                    source: rueda.primeraEsImagen ? rueda.url(rueda.primera) : ""
                    sourceSize.width: 256
                    fillMode: Image.PreserveAspectFit
                    asynchronous: true
                    autoTransform: true
                    cache: false
                }
                Kirigami.Icon {
                    anchors.fill: parent
                    anchors.margins: raiz.u * 0.4
                    visible: !imagen.visible
                    source: rueda.estado === "error" ? "dialog-error" : rueda.icono
                }
                Rectangle {        // cuántos
                    visible: rueda.cuantos > 1
                    anchors.right: parent.right; anchors.top: parent.top
                    width: Math.max(height, cuenta.implicitWidth + 8); height: raiz.u * 1.1; radius: height / 2
                    color: Kirigami.Theme.highlightColor
                    QQC2.Label { id: cuenta; anchors.centerIn: parent; text: rueda.cuantos; color: Kirigami.Theme.highlightedTextColor; font.pointSize: Kirigami.Theme.smallFont.pointSize }
                }
                Kirigami.Icon {    // listo
                    visible: rueda.estado === "hecha" || rueda.estado === "informe"
                    anchors.right: parent.right; anchors.bottom: parent.bottom
                    width: Kirigami.Units.iconSizes.smallMedium; height: width
                    source: "emblem-success"
                }
            }
            QQC2.Label {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: miniatura.bottom
                anchors.topMargin: 2
                width: raiz.r0 * 1.6
                horizontalAlignment: Text.AlignHCenter
                visible: miniatura.visible
                text: rueda.texto
                elide: Text.ElideMiddle
                font.pointSize: Kirigami.Theme.smallFont.pointSize
            }
            // el asa invisible del arrastre hacia fuera (a Dolphin, al escritorio, a otra app o a un sector)
            Item {
                id: asa
                width: miniatura.width; height: miniatura.height
                x: miniatura.x; y: miniatura.y
                enabled: rueda.cuantos > 0 && miniatura.visible
                Drag.active: arrastre.drag.active
                Drag.dragType: Drag.Automatic
                Drag.supportedActions: Qt.CopyAction
                Drag.mimeData: ({"text/uri-list": rueda.uriList})
                Drag.onDragStarted: {
                    const p = rueda_.mapToItem(raiz, 0, 0)
                    ventanaRueda.soloCirculo(Math.round(p.x), Math.round(p.y), Math.round(rueda_.width), Math.round(rueda_.height))
                }
                Drag.onDragFinished: dropAction => {
                    ventanaRueda.todaLaPantalla()
                    asa.x = miniatura.x; asa.y = miniatura.y
                }
                MouseArea {
                    id: arrastre
                    anchors.fill: parent
                    drag.target: asa
                    cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                    onPressed: miniatura.grabToImage(r => asa.Drag.imageSource = r.url)
                    onDoubleClicked: rueda.abrirPredeterminada()
                    QQC2.ToolTip.visible: containsMouse && !pressed
                    QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
                    QQC2.ToolTip.text: "Arrástralo a Dolphin, al escritorio o a otra aplicación (doble clic: abrir)"
                    hoverEnabled: true
                }
            }

            // trabajando: el anillo de progreso y cancelar
            Shape {
                anchors.fill: parent
                visible: rueda.estado === "corriendo" && rueda.progreso > 0
                preferredRendererType: Shape.CurveRenderer
                ShapePath {
                    fillColor: "transparent"
                    strokeColor: Kirigami.Theme.highlightColor
                    strokeWidth: 5
                    capStyle: ShapePath.RoundCap
                    PathAngleArc { centerX: raiz.r0; centerY: raiz.r0; radiusX: raiz.r0 - 6; radiusY: raiz.r0 - 6; startAngle: -90; sweepAngle: rueda.progreso * 3.6 }
                }
            }
            QQC2.BusyIndicator {
                anchors.centerIn: parent
                anchors.verticalCenterOffset: -raiz.u * 0.6
                running: visible
                visible: rueda.estado === "cargando" || (rueda.estado === "corriendo" && rueda.progreso === 0)
            }
            ColumnLayout {
                anchors.centerIn: parent
                anchors.verticalCenterOffset: raiz.u * (rueda.progreso === 0 ? 1.6 : 0)
                visible: rueda.estado === "corriendo"
                spacing: 0
                QQC2.Label { Layout.alignment: Qt.AlignHCenter; visible: rueda.progreso > 0; text: rueda.progreso + " %"; font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.4; font.weight: Font.DemiBold }
                QQC2.ToolButton {
                    Layout.alignment: Qt.AlignHCenter
                    icon.name: "process-stop"
                    text: "Cancelar"
                    display: QQC2.AbstractButton.IconOnly
                    onClicked: rueda.cancelar()
                    QQC2.ToolTip.text: text; QQC2.ToolTip.visible: hovered
                }
            }
        }
    }

    // --- la tarjeta de abajo: qué hace lo que está bajo el puntero, el mensaje, las acciones del resultado
    Rectangle {
        id: tarjeta
        width: Math.min(raiz.borde * 2, raiz.width - raiz.margen * 2)
        x: Math.max(raiz.margen, Math.min(raiz.width - width - raiz.margen, raiz.centro.x - width / 2))
        y: raiz.centro.y + raiz.borde + raiz.u * 0.6
        height: columna.implicitHeight + raiz.u
        radius: Kirigami.Units.cornerRadius * 2
        color: Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g, Kirigami.Theme.backgroundColor.b, 0.94)
        border.color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.12)
        opacity: rueda_.opacity
        visible: !raiz.ampliado
        ColumnLayout {
            id: columna
            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
            anchors.margins: raiz.u * 0.5
            spacing: 2
            QQC2.Label {
                Layout.fillWidth: true
                font.weight: Font.DemiBold
                elide: Text.ElideRight
                text: raiz.sectorVisto ? raiz.sectorVisto.titulo + (raiz.sectorVisto.junta ? " · todos en uno" : "")
                    : rueda.estado === "hecha" ? "Listo: " + rueda.mensaje
                    : rueda.estado === "corriendo" ? rueda.mensaje
                    : rueda.estado === "error" ? "No se pudo"
                    : rueda.estado === "vacia" ? "Muyu"
                    : rueda.cadena
            }
            QQC2.Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                maximumLineCount: 3
                elide: Text.ElideRight
                color: raiz.sectorVisto && raiz.sectorVisto.faltan.length ? Kirigami.Theme.neutralTextColor
                     : rueda.estado === "error" ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.disabledTextColor
                text: raiz.sectorVisto ? (raiz.sectorVisto.faltan.length ? "Falta en esta máquina: " + raiz.sectorVisto.faltan.join(", ") : raiz.sectorVisto.descripcion)
                    : rueda.estado === "vacia" ? "Arrastra aquí un archivo desde Dolphin, Krusader o el escritorio, o un enlace desde el navegador (o pégalo con Ctrl+V), y suéltalo sobre lo que quieras hacer."
                    : rueda.estado === "hecha" ? "Arrástralo desde el centro a donde quieras, o sigue: los anillos ya son para el resultado."
                    : rueda.estado === "lista" ? (rueda.mensaje || ((rueda.predeterminada ? "Intro abre con " + rueda.predeterminada + ". " : "")
                                                 + "Afuera: abrir con otra aplicación. Interior: convertir. Exterior: herramientas. Clic derecho: con opciones."))
                    : rueda.mensaje
                visible: text !== ""
            }
            Repeater {
                model: rueda.estado === "vacia" && !raiz.sectorVisto ? rueda.okular.slice(0, 3) : []
                delegate: QQC2.ToolButton {
                    required property var modelData
                    Layout.fillWidth: true
                    icon.name: "okular"
                    text: "Desde Okular: " + modelData.nombre + (modelData.pagina ? " (pág. " + modelData.pagina + ")" : "")
                    onClicked: rueda.cargar([modelData.ruta])
                }
            }
            RowLayout {
                Layout.fillWidth: true
                visible: !raiz.sectorVisto && (rueda.estado === "hecha" || rueda.hayHistorial || rueda.cuantos > 0)
                spacing: 0
                QQC2.ToolButton { icon.name: "document-open"; text: "Abrir"; visible: rueda.cuantos > 0 && !rueda.sonEnlaces; onClicked: rueda.abrirPredeterminada() }
                QQC2.ToolButton { icon.name: "okular"; text: "Okular"; display: QQC2.AbstractButton.IconOnly
                                  visible: rueda.cuantos === 1 && rueda.primera.toLowerCase().endsWith(".pdf"); onClicked: rueda.abrirEnOkular(rueda.primera)
                                  QQC2.ToolTip.text: "Abrir en Okular"; QQC2.ToolTip.visible: hovered }
                QQC2.ToolButton { icon.name: "mail-message-new"; text: "Enviar"; display: QQC2.AbstractButton.IconOnly
                                  visible: rueda.estado === "hecha"; onClicked: rueda.enviarPorCorreo()
                                  QQC2.ToolTip.text: "Enviar por correo"; QQC2.ToolTip.visible: hovered }
                QQC2.ToolButton { icon.name: "edit-copy"; text: "Copiar"; display: QQC2.AbstractButton.IconOnly
                                  visible: rueda.cuantos > 0 && !rueda.sonEnlaces; onClicked: rueda.copiarArchivos()
                                  QQC2.ToolTip.text: "Copiar el archivo (para pegarlo en Dolphin o en un chat)"; QQC2.ToolTip.visible: hovered }
                QQC2.ToolButton { icon.name: "system-file-manager"; text: "Mostrar"; visible: rueda.cuantos > 0 && !rueda.sonEnlaces; onClicked: escritorio.mostrarEnDolphin(rueda.primera) }
                Item { Layout.fillWidth: true }
                QQC2.ToolButton { icon.name: "go-previous"; text: "Volver"; visible: rueda.hayHistorial && rueda.estado !== "corriendo"; onClicked: rueda.volver()
                                  QQC2.ToolTip.text: "Al archivo anterior, sin borrar nada (Retroceso)"; QQC2.ToolTip.visible: hovered }
                QQC2.ToolButton { icon.name: "documentinfo"; text: "Ver informe"; visible: rueda.informe.length > 0; onClicked: raiz.verInforme = true }
                QQC2.ToolButton { icon.name: "edit-undo"; text: "Deshacer"; visible: rueda.estado === "hecha"; onClicked: rueda.deshacer()
                                  QQC2.ToolTip.text: "El resultado, a la papelera (Ctrl+Z)"; QQC2.ToolTip.visible: hovered }
            }
        }
    }

    // --- el panel de opciones
    PanelOpciones {
        id: panelOpciones
        sector: raiz.panel
        visible: raiz.panel !== null
        readonly property bool aLaDerecha: raiz.centro.x + raiz.borde + raiz.u + width + raiz.margen <= raiz.width
        x: aLaDerecha ? raiz.centro.x + raiz.borde + raiz.u : Math.max(raiz.margen, raiz.centro.x - raiz.borde - raiz.u - width)
        y: Math.max(raiz.margen, Math.min(raiz.height - height - raiz.margen, raiz.centro.y - height / 2))
        width: ampliado ? raiz.width - raiz.margen * 2 : Math.min(Math.max(raiz.u * 28, raiz.width * 0.32), raiz.width - raiz.margen * 2)
        height: ampliado ? raiz.height - raiz.margen * 2 : Math.min(raiz.u * 40, raiz.height - raiz.margen * 2)
        states: State {
            when: panelOpciones.ampliado
            PropertyChanges { target: panelOpciones; x: raiz.margen; y: raiz.margen }
        }
        onCerrar: { raiz.panel = null; ampliado = false; rueda.limpiarVista(); raiz.forceActiveFocus() }
    }

    // --- el informe de una herramienta de información (metadatos, información de un PDF o un vídeo, sumas…)
    PanelInforme {
        id: panelInforme
        visible: raiz.verInforme && raiz.panel === null
        readonly property bool aLaDerecha: raiz.centro.x + raiz.borde + raiz.u + width + raiz.margen <= raiz.width
        x: aLaDerecha ? raiz.centro.x + raiz.borde + raiz.u : Math.max(raiz.margen, raiz.centro.x - raiz.borde - raiz.u - width)
        y: Math.max(raiz.margen, Math.min(raiz.height - height - raiz.margen, raiz.centro.y - height / 2))
        width: Math.min(Math.max(raiz.u * 26, raiz.width * 0.3), raiz.width - raiz.margen * 2)
        height: Math.min(raiz.u * 34, raiz.height - raiz.margen * 2)
        onCerrar: { raiz.verInforme = false; raiz.forceActiveFocus() }
    }
    Connections {
        target: rueda
        function onTerminado(ok, mensaje) { if (rueda.estado === "informe") raiz.verInforme = true }
    }

    // --- el teclado
    Keys.onPressed: evento => {
        const n = raiz.todos.length
        if (evento.key === Qt.Key_Escape) {
            if (raiz.panel) { raiz.panel = null; panelOpciones.ampliado = false; rueda.limpiarVista() }
            else if (raiz.verInforme) raiz.verInforme = false
            else raiz.cerrar()
        } else if (evento.key === Qt.Key_Right || evento.key === Qt.Key_Down || evento.key === Qt.Key_Tab) {
            if (n) raiz.foco = (raiz.foco + 1) % n
        } else if (evento.key === Qt.Key_Left || evento.key === Qt.Key_Up || evento.key === Qt.Key_Backtab) {
            if (n) raiz.foco = (raiz.foco - 1 + n) % n
        } else if ((evento.key === Qt.Key_Return || evento.key === Qt.Key_Enter) && raiz.foco >= 0 && raiz.foco < n) {
            raiz.elegir(raiz.todos[raiz.foco].s.clave, false)
        } else if (evento.key === Qt.Key_Return || evento.key === Qt.Key_Enter) {
            rueda.abrirPredeterminada()                  // Intro sin nada elegido: con la de siempre (el doble clic de antes)
        } else if ((evento.key === Qt.Key_Menu || evento.key === Qt.Key_Space) && raiz.foco >= 0 && raiz.foco < n) {
            raiz.elegir(raiz.todos[raiz.foco].s.clave, true)
        } else if (evento.key >= Qt.Key_1 && evento.key <= Qt.Key_9 && evento.key - Qt.Key_1 < rueda.interior.length) {
            raiz.elegir(rueda.interior[evento.key - Qt.Key_1].clave, (evento.modifiers & Qt.ShiftModifier) !== 0)
        } else if (evento.key === Qt.Key_Backspace) {
            rueda.volver()
        } else if (evento.key === Qt.Key_Z && (evento.modifiers & Qt.ControlModifier)) {
            rueda.deshacer()
        } else if (evento.key === Qt.Key_V && (evento.modifiers & Qt.ControlModifier)) {
            rueda.pegar()
        } else {
            return
        }
        evento.accepted = true
    }
}
