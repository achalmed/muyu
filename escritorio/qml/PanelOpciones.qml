// PanelOpciones — las opciones de un sector, generadas de su ficha (PaginaFormulario de gui-comun), con la vista previa
// en vivo (VistaResultado: la operación de verdad sobre una copia, en la caché, cada vez que se cambia algo; un PDF en
// el visor con zoom, desplazamiento, selección y búsqueda) o, si un parámetro trae la pista de edición «caja», el editor
// del rectángulo sobre la imagen. Si la operación sabe leer lo que el archivo ya tiene (`con_actuales`: el título y el
// autor de un PDF), el formulario llega relleno. «Ampliar» lo lleva a casi toda la pantalla, con la vista a la
// izquierda y las opciones a la derecha. Los botones quedan siempre a la vista; las opciones se desplazan. Genérico: no
// sabe de ninguna operación.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import GuiComun

Rectangle {
    id: panel
    property var sector: null
    property bool ampliado: false
    signal cerrar()

    readonly property real u: Kirigami.Units.gridUnit
    readonly property string claveCaja: sector && sector.editor === "caja" ? sector.editor_clave : ""
    // con el editor, la proporción que lo limita: el campo de opciones cuyas opciones son proporciones (1:1, 16:9…)
    readonly property var campoProporcion: claveCaja ? (sector.campos.find(c => c.tipo === "opcion" && c.opciones.some(o => /^\d+:\d+$/.test(String(o[0])))) || null) : null
    readonly property bool conEditor: claveCaja !== "" && rueda.primeraEsImagen && rueda.cuantos === 1
    readonly property bool conVista: sector !== null && !conEditor && rueda.tieneVista(sector.clave)
    readonly property var camposVisibles: sector ? sector.campos.filter(c => sector.fijos.indexOf(c.clave) < 0
                                                    && !(conEditor && (c.clave === claveCaja || (campoProporcion && c.clave === campoProporcion.clave)))) : []
    readonly property bool dosColumnas: width > u * 46 && (conVista || conEditor)

    function valores() {
        // lo que se ve en cada campo: su valor por omisión si no se escribió otro (PaginaFormulario da solo lo escrito)
        const v = {}
        for (const c of camposVisibles)
            if (c.defecto !== null && c.defecto !== undefined && c.defecto !== "")
                v[c.clave] = c.defecto
        Object.assign(v, propuestos(), formulario.valores)
        if (conEditor) {
            v[claveCaja] = editor.caja
            if (campoProporcion)
                v[campoProporcion.clave] = editor.proporcion === "libre" ? "libre" : editor.proporcion
        }
        return v
    }
    // lo que la opción propone y se puede cambiar (p. ej. Firefox en «con tu sesión»): los parámetros que no son fijos
    function propuestos() {
        const v = {}
        if (sector) {
            for (const k in sector.params)
                if (sector.fijos.indexOf(k) < 0)
                    v[k] = sector.params[k]
            // la página que estás leyendo en Okular, para lo que trabaja en una página (un sello, una nota)
            if (rueda.paginaOkular > 0 && sector.campos.some(c => c.clave === "pagina" && c.tipo === "entero"))
                v.pagina = rueda.paginaOkular
        }
        return v
    }
    function aplicar() {
        rueda.correr(sector.clave, valores())
        cerrar()
    }
    function pedirVista() {
        if (conVista)
            espera.restart()
    }

    radius: Kirigami.Units.cornerRadius * 2
    color: Kirigami.Theme.backgroundColor
    border.color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.15)
    Kirigami.Theme.colorSet: Kirigami.Theme.Window
    Kirigami.Theme.inherit: false

    onSectorChanged: {
        if (!sector)
            return
        formulario.restablecer()
        formulario.poner(propuestos())
        editor.reiniciar()
        rueda.pedirActuales(sector.clave)
        Qt.callLater(pedirVista)            // después de que conVista se recalcule para el sector nuevo
        aplicarBoton.forceActiveFocus()
    }
    Timer { id: espera; interval: 350; onTriggered: if (panel.sector) rueda.previsualizar(panel.sector.clave, panel.valores()) }
    Connections {
        target: rueda
        function onValoresActuales(clave, valores) {
            if (panel.sector && clave === panel.sector.clave) {
                formulario.poner(valores)
                panel.pedirVista()
            }
        }
    }

    // que los clics no lleguen a la rueda de debajo (cerraría)
    MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons; hoverEnabled: true; onWheel: wheel => wheel.accepted = false }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: panel.u * 0.7
        spacing: Kirigami.Units.smallSpacing

        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing
            BotonCerrar { visible: rueda.cerrarIzquierda; onClicked: panel.cerrar() }
            Kirigami.Icon { source: panel.sector ? panel.sector.icono : ""; Layout.preferredWidth: Kirigami.Units.iconSizes.medium; Layout.preferredHeight: Layout.preferredWidth }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0
                Kirigami.Heading { Layout.fillWidth: true; level: 3; text: panel.sector ? panel.sector.titulo : ""; elide: Text.ElideRight }
                QQC2.Label {
                    Layout.fillWidth: true
                    text: rueda.cuantos > 1 ? rueda.cuantos + " archivos" + (panel.sector && panel.sector.junta ? " · una sola salida" : " · una salida por archivo") : rueda.texto
                    color: Kirigami.Theme.disabledTextColor; elide: Text.ElideMiddle
                }
            }
            QQC2.ToolButton {
                icon.name: panel.ampliado ? "view-restore" : "view-fullscreen"
                text: panel.ampliado ? "Reducir" : "Ampliar"
                display: QQC2.AbstractButton.IconOnly
                onClicked: panel.ampliado = !panel.ampliado
                QQC2.ToolTip.text: text + " (F11)"; QQC2.ToolTip.visible: hovered
            }
            BotonCerrar { visible: !rueda.cerrarIzquierda; onClicked: panel.cerrar() }
        }
        QQC2.Label {
            Layout.fillWidth: true
            text: panel.sector ? panel.sector.descripcion : ""
            wrapMode: Text.WordWrap
            maximumLineCount: panel.ampliado ? 3 : 2
            elide: Text.ElideRight
            color: Kirigami.Theme.disabledTextColor
            visible: text !== ""
        }

        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: panel.dosColumnas ? 2 : 1
            columnSpacing: panel.u * 0.7
            rowSpacing: Kirigami.Units.smallSpacing

            EditorCaja {
                id: editor
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: panel.u * 10
                visible: panel.conEditor
                fuente: panel.conEditor ? rueda.url(rueda.primera) : ""
                proporciones: panel.campoProporcion ? panel.campoProporcion.opciones.map(o => String(o[0])) : ["libre"]
            }
            VistaResultado {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: panel.u * 10
                visible: panel.conVista
            }
            QQC2.ScrollView {
                id: desplazable
                Layout.fillWidth: !panel.dosColumnas
                Layout.preferredWidth: panel.dosColumnas ? panel.u * 22 : -1
                Layout.fillHeight: panel.dosColumnas || !(panel.conVista || panel.conEditor)
                Layout.preferredHeight: panel.dosColumnas ? -1 : Math.min(formulario.implicitHeight + 4, panel.u * 13)
                Layout.minimumHeight: Math.min(formulario.implicitHeight, panel.u * 5)
                contentWidth: availableWidth
                QQC2.ScrollBar.horizontal.policy: QQC2.ScrollBar.AlwaysOff
                PaginaFormulario {
                    id: formulario
                    width: desplazable.availableWidth - Kirigami.Units.smallSpacing
                    campos: panel.camposVisibles
                    nombreAccesible: "Opciones de " + (panel.sector ? panel.sector.titulo : "")
                    mensajeVacio: panel.conEditor ? "" : "Sin más opciones."
                    onCambiado: (clave, valor) => panel.pedirVista()
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            QQC2.Label {
                Layout.fillWidth: true
                text: rueda.sonEnlaces ? "Se guarda en tu carpeta de Descargas." : "El original no se toca: la salida va a su lado."
                font.pointSize: Kirigami.Theme.smallFont.pointSize
                color: Kirigami.Theme.disabledTextColor
                wrapMode: Text.WordWrap
            }
            QQC2.Button { text: "Cancelar"; icon.name: "dialog-cancel"; onClicked: panel.cerrar() }
            QQC2.Button {
                id: aplicarBoton
                text: "Aplicar"
                icon.name: "dialog-ok-apply"
                highlighted: true
                onClicked: panel.aplicar()
                Keys.onReturnPressed: panel.aplicar()
                Keys.onEnterPressed: panel.aplicar()
            }
        }
    }
    Shortcut { sequences: ["Ctrl+Return", "Ctrl+Enter"]; enabled: panel.visible; onActivated: panel.aplicar() }
    Shortcut { sequence: "F11"; enabled: panel.visible; onActivated: panel.ampliado = !panel.ampliado }
    Connections { target: editor; function onCajaChanged() { panel.pedirVista() } }
}
