# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 N3ruk
"""Offline, nontechnical help. Opening it never applies server settings."""
from html import escape
from PyQt6.QtCore import Qt, QSize, QRect
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QTextBrowser, QSplitter, QDialogButtonBox)
from localization import tr

SECTIONS = [
    (
        'Primeros pasos',
        'Instalación: el ordenador y el reproductor deben estar conectados a la misma red. En la pestaña Resumen, el botón Instalar servidor UMS permite instalar el servidor previa confirmación. Se requiere conexión a Internet. Una vez instalado, el botón Iniciar permite ponerlo en funcionamiento. El ordenador debe permanecer encendido durante la reproducción.',
        'Configuración inicial: tras añadir un dispositivo y seleccionar sus carpetas compartidas, Guardar y aplicar activa la configuración. La biblioteca se selecciona desde la sección de servidores multimedia del televisor o la consola. Cerrar UMS Control no detiene el servidor.',
    ),
    (
        'Gestionar el servidor',
        'Estado y diagnóstico: tras la instalación, el botón Instalar servidor UMS de la pestaña Resumen se sustituye por Salud del servidor. Esta ventana muestra el estado y los avisos, permite Ver registro del servidor y ofrece la reinstalación cuando se detecta una instalación dañada, conservando los ajustes. El estado Detenido no indica una avería; el botón Iniciar permite activar el servidor.',
        'Actualización del servidor: Actualizar servidor UMS solo aparece en la pestaña Resumen cuando se detecta una versión posterior a la instalada. La comprobación se realiza al abrir el panel; la instalación requiere confirmación y conserva carpetas, perfiles y ajustes. Si el servidor está activo, se reinicia y se interrumpe la reproducción. Si está detenido, permanece detenido. Esta operación es distinta de Actualizar catálogo multimedia, que renueva la lista de contenidos.',
        'Desinstalación: Desinstalar servidor UMS solicita confirmación, detiene el servidor gestionado, desactiva su inicio automático y envía sus archivos a la papelera. UMS Control, los ajustes, los perfiles y los archivos multimedia se conservan. No se desinstalan otros servidores. Instalar servidor UMS permite instalarlo de nuevo.',
    ),
    (
        'Buscar dispositivos',
        'Búsqueda en la red: el botón Buscar en la red de la pestaña Dispositivos detecta reproductores disponibles. El reproductor debe estar encendido y tener abierta la búsqueda de servidores multimedia. En PS3, esta función se encuentra en Vídeo → Buscar servidores multimedia. La selección de un resultado permite añadir el dispositivo.',
        'Identificación manual: Añadir por IP permite registrar un dispositivo mediante su dirección IP local. Si aparece como UnknownRenderer, la dirección IP permite verificar su identidad y el campo Identificación permite asignarle un nombre. Los reproductores que utilizan la misma IP en un ordenador comparten perfil.',
    ),
    (
        'Compartir carpetas',
        'Selección de carpetas: con el dispositivo seleccionado, Carpetas compartidas → Añadir carpeta permite definir el contenido accesible para ese dispositivo. Las subcarpetas se incluyen automáticamente. Para limitar el acceso a una parte de la biblioteca, se debe añadir directamente la subcarpeta correspondiente.',
        'Disponibilidad y retirada: los discos compartidos deben estar conectados durante la reproducción. Dejar de compartir selección y Retirar perfil eliminan el acceso al guardar, sin borrar los archivos multimedia. Los dispositivos nuevos no tienen carpetas compartidas hasta que se les asignan.',
    ),
    (
        'Modos de reproducción',
        'Modo Original: envía el archivo sin modificar y requiere que el reproductor admita su formato. La conversión adapta vídeos no compatibles o reduce la calidad enviada. Se realiza durante la reproducción, sin sustituir los originales ni generar una colección adicional en el disco.',
        'Modos de conversión: en el modo manual se seleccionan las carpetas que se convertirán; el árbol permite definir excepciones por subcarpeta. El modo automático evalúa todos los vídeos compartidos y no utiliza esa selección. En ambos modos, Transcodificar → título contiene las variantes disponibles y Sin transcodificación para acceder al original. Los vídeos no se muestran fuera de esta estructura.',
    ),
    (
        'Elegir audio y subtítulos',
        'Selección de pistas: A · Gestionados por el dispositivo mantiene las pistas juntas y permite seleccionarlas con el mando si el reproductor lo admite. B · Preseleccionados e incrustados ofrece combinaciones de audio y subtítulos en Transcodificar. Los subtítulos incrustados forman parte de la imagen y no pueden desactivarse desde el reproductor.',
        'Subtítulos externos: Buscar subtítulos junto al vídeo permite utilizar archivos como Pelicula.spa.srt situados junto a Pelicula.mkv. Tras guardar los cambios, es necesario volver a abrir Transcodificar en el reproductor. En Original y Sin transcodificación, la selección de pistas depende de las funciones del reproductor.',
    ),
    (
        'Ajustar calidad y audio',
        'Resolución y bitrate: Calidad y audio solo está disponible durante la conversión. Los valores actuales y Contenedor Automático constituyen una configuración inicial. Si se producen interrupciones, un límite de resolución o bitrate inferior puede reducir la carga de transmisión. Sin límite no aumenta la capacidad de la conexión. Una reducción excesiva puede deteriorar la imagen.',
        'Audio y procesamiento: Estéreo ofrece una salida de dos canales; hasta 5.1 requiere pistas y equipos compatibles. CPU utiliza el procesador del ordenador. NVIDIA NVENC requiere una tarjeta gráfica compatible. Estos ajustes se aplican únicamente al dispositivo seleccionado y no modifican el archivo original.',
    ),
    (
        'Usar nombres compatibles',
        'Ámbito de aplicación: Reproducción → Nombres anunciados al dispositivo permite conservar el nombre original o simplificarlo en todas las carpetas o en las seleccionadas. Esta opción está destinada a reproductores con dificultades para mostrar determinados nombres; no garantiza la resolución de otros problemas de reproducción.',
        'Efectos y selección: solo se modifica el nombre anunciado al reproductor, sin renombrar los archivos ni convertir el vídeo. La opción también está disponible en Original. El árbol permite seleccionar subcarpetas; una casilla parcialmente marcada indica que existen excepciones dentro de esa carpeta.',
    ),
    (
        'Guardar y actualizar catálogo',
        'Aplicación de cambios: Guardar y aplicar activa los cambios de carpetas y reproducción. Si UMS está activo, se reinicia y se interrumpe la reproducción en curso. Si está detenido, no se inicia. Descartar cambios recupera la última configuración guardada.',
        'Actualización del catálogo: tras añadir contenido, Actualizar catálogo multimedia en la pestaña Resumen renueva la biblioteca. Las carpetas nuevas deben guardarse antes de esta operación. Si el reproductor conserva la lista anterior, es necesario volver a abrir el servidor desde el dispositivo. Actualizar el catálogo no convierte los vídeos.',
    ),
    (
        'Resolución de problemas',
        'Servidor o carpetas no disponibles: se debe comprobar que el ordenador esté encendido, UMS iniciado y ambos equipos conectados a la misma red. Red del servidor, en la pestaña Resumen, permite revisar la conexión. Si faltan carpetas, deben verificarse el dispositivo seleccionado, la conexión del disco y la configuración guardada.',
        'Fallos e interrupciones de reproducción: ante un fallo en Original, la conversión automática permite comprobar una alternativa. Si falla una variante convertida, puede seleccionarse otra variante o Sin transcodificación. Tras cambiar el modo, es necesario volver a abrir el servidor desde el reproductor. Una conexión Ethernet o una calidad inferior pueden reducir interrupciones. Los errores de UMS deben consultarse en Salud del servidor; el estado Detenido, por sí solo, no requiere reinstalación.',
    ),
    (
        'Tema, idioma y otros controles',
        'Apariencia e idioma: Tema modifica el aspecto del panel; UGM incluye un fondo ilustrado. Idioma cambia los textos de la aplicación, no los títulos de los vídeos. Ambas preferencias se guardan al seleccionarlas y no reinician el servidor. La consulta de esta guía tampoco modifica la configuración.',
        'Otros controles: la pestaña Resumen permite activar el inicio del servidor al iniciar sesión en Ubuntu. Abrir UMS web muestra la administración del servidor en el navegador. Actualizar servidor UMS modifica la versión del servidor; Actualizar catálogo multimedia renueva únicamente la lista de contenidos.',
    ),
]


def format_paragraph(text):
    """Emphasize the action label while preserving escaped, selectable text."""
    label, separator, body = text.partition(': ')
    if not separator:
        return escape(text)
    return '<strong>' + escape(label) + ':</strong> ' + escape(body)


class CategoryList(QListWidget):
    """Wrap long translated headings to the actual list width."""
    def resizeEvent(self, event):
        super().resizeEvent(event)
        width = max(80, self.viewport().width() - 2)
        for index in range(self.count()):
            item = self.item(index)
            bounds = self.fontMetrics().boundingRect(
                QRect(0, 0, max(30, width - 28), 2000),
                int(Qt.TextFlag.TextWordWrap), item.text())
            item.setSizeHint(QSize(width, max(42, bounds.height() + 24)))


class GuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('Instrucciones'))
        self.resize(940, 620)
        self.setMinimumSize(680, 460)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        title = QLabel(tr('Guía de uso · UMS Control'))
        title.setObjectName('sectionTitle')
        layout.addWidget(title)
        intro = QLabel(tr('Seleccione una categoría para consultar las instrucciones. La consulta de esta guía no modifica la configuración.'))
        intro.setWordWrap(True)
        intro.setObjectName('muted')
        layout.addWidget(intro)
        split = QSplitter()
        split.setChildrenCollapsible(False)
        self.categories = CategoryList()
        self.categories.setObjectName('guideCategories')
        self.categories.setAccessibleName(tr('Categorías de ayuda'))
        self.categories.setWordWrap(True)
        self.categories.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.categories.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.categories.setMinimumWidth(170)
        for heading, *_ in SECTIONS:
            item = QListWidgetItem(tr(heading))
            item.setToolTip(tr(heading))
            self.categories.addItem(item)
        self.view = QTextBrowser()
        self.view.setObjectName('guideText')
        self.view.setMinimumWidth(300)
        self.view.setOpenExternalLinks(False)
        split.addWidget(self.categories)
        split.addWidget(self.view)
        split.setStretchFactor(1, 1)
        split.setSizes([230, 640])
        layout.addWidget(split, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.categories.currentRowChanged.connect(self.show_category)
        self.categories.setCurrentRow(0)

    def show_category(self, index):
        if not 0 <= index < len(SECTIONS):
            return
        heading, *paragraphs = SECTIONS[index]
        self.view.setAccessibleName(tr(heading))
        self.view.setHtml('<h2>' + escape(tr(heading)) + '</h2>' + ''.join(
            '<p style="line-height:145%; margin-top:16px;">' + format_paragraph(tr(text)) + '</p>'
            for text in paragraphs))
        self.view.verticalScrollBar().setValue(0)
