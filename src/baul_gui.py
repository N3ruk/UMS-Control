#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 N3ruk
"""Native desktop companion for Universal Media Server; Spanish UI."""
import copy, json, sys, shutil
from pathlib import Path
from PyQt6.QtCore import Qt, QObject, QRunnable, QThreadPool, pyqtSignal, QTimer, QLockFile, QStandardPaths, QSignalBlocker
from PyQt6.QtGui import QIcon, QDesktopServices, QCloseEvent, QActionGroup, QPixmap, QPainter, QColor
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTabWidget,QListWidget,QListWidgetItem,QAbstractItemView,QLineEdit,QComboBox,QSpinBox,QFormLayout,QGroupBox,QFileDialog,QMessageBox,QCheckBox,QScrollArea,QSplitter,QDialog,QDialogButtonBox,QSizePolicy,QTextBrowser)
import baul_core as core
import appearance
from platform_support import ROOT as RESOURCE_ROOT
from user_guide import GuideDialog
from folder_rules import FolderRuleTree
import server_manager as manager
import server_releases as releases
from localization import tr, set_language, translate_between
from configuration import ConfigurationError, StartupCancelled, preserve

# Starting points for conversion, not network measurements or device limits.
RECOMMENDED_BITRATES = {'480p':5,'720p':10,'1080p':25,'1440p':40,'2160p':60,'original':0}

class Signals(QObject):
    done=pyqtSignal(object)
    error=pyqtSignal(str)
    finished=pyqtSignal()

class Job(QRunnable):
    def __init__(self,fn):
        super().__init__();self.fn=fn;self.signals=Signals()
    def run(self):
        try:self.signals.done.emit(self.fn())
        except Exception as e:self.signals.error.emit(str(e))
        finally:self.signals.finished.emit()

STYLE='''
QWidget {font-family: "Noto Sans", "DejaVu Sans"; font-size: 10.5pt; color: #e9ecf5;}
QMainWindow,QDialog {background:#101521;}
QTabWidget::pane {border:1px solid #303a50; border-radius:8px; background:#171e2d;}
QTabBar::tab {background:#192133; padding:11px 23px; margin-right:4px; border-top-left-radius:6px; border-top-right-radius:6px;}
QTabBar::tab:selected {background:#304667; color:#a9dcff;}
QLineEdit,QComboBox,QSpinBox,QListWidget,QTreeWidget {background:#101725;border:1px solid #39465d;border-radius:5px;padding:7px;selection-background-color:#35547d;}
QComboBox QAbstractItemView {background:#172235;color:#e9ecf5;selection-background-color:#35547d;}
QPushButton {background:#2b3b55;border:1px solid #485b78;border-radius:5px;padding:8px 15px;}
QPushButton:hover {background:#3a5275;}
QPushButton:focus,QComboBox:focus,QLineEdit:focus,QSpinBox:focus,QListWidget:focus,QTreeWidget:focus {border:2px solid #82d5ff;}
QLabel#sectionTitle {font-size:16pt;font-weight:600;}
QLabel#explanation {background:#202e43;border:1px solid #425c7b;border-radius:6px;padding:12px;color:#e5f2ff;}
QCheckBox::indicator {width:22px;height:22px;}
QCheckBox:focus {outline:2px solid #82d5ff;}
QWidget:disabled {color:#7d8797;}
QGroupBox:disabled {border-color:#303744;}
QGroupBox::title:disabled {color:#758095;}
QTabBar#deviceTabBar::tab {padding:9px 10px;}
QTabBar::tab:disabled {color:#758095;background:#171b24;}
QLabel#muted:disabled {color:#758095;}
QPushButton:disabled {color:#78859a;background:#222c3b;border-color:#303a49;}
QPushButton#primary {background:#2864a5;border-color:#4a97d9;font-weight:bold;}
QGroupBox {border:1px solid #344157;border-radius:7px;margin-top:14px;padding:15px;}
QGroupBox::title {subcontrol-origin:margin;left:12px;padding:0 6px;color:#a9c7ee;}
QLabel#title {font-size:25pt;font-weight:700;color:#f2f7ff;}
QLabel#muted {color:#a8b5c9;}
QLabel#status {font-size:14pt;font-weight:600;color:#80d3ba;}
QScrollArea {border:0;background:transparent;}
QCheckBox {spacing:8px;}
QListWidget::item,QTreeWidget::item {padding:8px;border-radius:4px;}
QListWidget::item:selected,QTreeWidget::item:selected {background:#2d476a;}
QToolTip {background:#293d59;color:white;border:1px solid #6085b2;}
'''

def label(text,muted=False):
    w=QLabel(text);w.setWordWrap(True);w.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Minimum)
    if muted:w.setObjectName('muted')
    w.setTextFormat(Qt.TextFormat.PlainText)
    return w

def button(text,fn,primary=False):
    b=QPushButton(text);b.clicked.connect(fn)
    if primary:b.setObjectName('primary')
    return b

class FocusComboBox(QComboBox):
    def wheelEvent(self,event):
        if self.hasFocus():super().wheelEvent(event)
        else:event.ignore()

class FocusSpinBox(QSpinBox):
    def wheelEvent(self,event):
        if self.hasFocus():super().wheelEvent(event)
        else:event.ignore()

def combo(items):
    c=FocusComboBox();c.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon);c.setMinimumContentsLength(12);c.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    for text,value in items:c.addItem(text,value)
    return c

class AppBackdrop(QWidget):
    """Cached aspect-fill wallpaper for the illustrated palettes."""
    def __init__(self,parent):
        super().__init__(parent);self.setObjectName('appBackdrop');self.window_owner=parent;self.image=QPixmap();self.scaled=QPixmap();self.scaled_size=None;self.image_theme=None
    def load_image(self):
        theme=self.window_owner.preferences['theme']
        if theme in appearance.WALLPAPER_THEMES and self.image_theme!=theme:
            self.image=QPixmap(str((RESOURCE_ROOT/'assets')/(theme+'-background.png')));self.image_theme=theme;self.scaled_size=None

    def paintEvent(self,event):
        self.load_image()
        theme=self.window_owner.preferences['theme']
        if theme not in appearance.WALLPAPER_THEMES:
            super().paintEvent(event);return
        if self.image.isNull():super().paintEvent(event);return
        if self.scaled_size!=self.size():
            self.scaled=self.image.scaled(self.size(),Qt.AspectRatioMode.KeepAspectRatioByExpanding,Qt.TransformationMode.SmoothTransformation);self.scaled_size=self.size()
        painter=QPainter(self);painter.drawPixmap((self.width()-self.scaled.width())//2,(self.height()-self.scaled.height())//2,self.scaled)
        if theme=='ugm':painter.fillRect(self.rect(),QColor(12,7,24,65))
        elif theme=='current':painter.fillRect(self.rect(),QColor(6,13,26,65))
        elif theme=='green':painter.fillRect(self.rect(),QColor(8,18,7,65))
        painter.end()

def load_with_recovery(loader,default):
    try:return loader()
    except ConfigurationError as error:
        dialog=QMessageBox(QMessageBox.Icon.Warning,'UMS Control',tr('No se puede leer la configuración guardada. El archivo original y el servidor no se modificarán.'),QMessageBox.StandardButton.Cancel)
        dialog.setInformativeText(str(error.path)+'\n\n'+tr('Es posible conservar una copia del archivo y abrir un borrador con los valores iniciales. Los perfiles del servidor solo se modificarán al guardar y aplicar.'))
        reset=dialog.addButton(tr('Conservar copia y abrir borrador'),QMessageBox.ButtonRole.AcceptRole)
        folder=dialog.addButton(tr('Abrir carpeta'),QMessageBox.ButtonRole.ActionRole)
        dialog.setDefaultButton(QMessageBox.StandardButton.Cancel)
        while True:
            dialog.exec()
            if dialog.clickedButton()==folder:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(error.path.parent)));continue
            if dialog.clickedButton()!=reset:raise StartupCancelled()
            try:backup=preserve(error.path)
            except OSError as failure:
                QMessageBox.warning(None,'UMS Control',tr('No se ha podido conservar el archivo. No se realizará la recuperación.')+'\n'+str(failure));raise StartupCancelled() from failure
            QMessageBox.information(None,'UMS Control',tr('Copia de recuperación conservada en:')+'\n'+str(backup))
            return default()

class SummaryBody(QWidget):
    def minimumSizeHint(self):
        # Word-wrapped labels must be measured at their actual width, not their
        # narrow minimum width (which creates an unnecessary outer scrollbar).
        from PyQt6.QtCore import QSize
        return QSize(0,max(0,self.layout().totalHeightForWidth(max(1,self.width()))))

class Window(QMainWindow):
    def __init__(self,preferences=None):
        super().__init__();self.state=load_with_recovery(core.load_state,core.defaults);self.legacy_migration=any(core.editable_tv(t)!=t for t in self.state['tvs']);self.state['tvs']=[core.editable_tv(t) for t in self.state['tvs']];self.row=-1;self.loading=False;self.dirty=False;self.busy=False;self.refreshing=False;self.jobs=set();self.latest_release=None;self.update_check_error=None;self.control_generation=0
        self.preferences=preferences or load_with_recovery(appearance.load,lambda:dict(theme='current',language='es'));initial_language=self.preferences['language'];self.preferences['language']='es';self.ui_texts={};set_language('es');configure_qt_language(QApplication.instance(),self.preferences['language']);self.language_choices={};self.make_menus()
        self.setWindowTitle('UMS Control');self.setWindowIcon(QIcon(str((RESOURCE_ROOT/'assets')/'ums-control.png')));self.resize(1140,840);self.setMinimumSize(860,620)
        root=AppBackdrop(self);self.setCentralWidget(root);v=QVBoxLayout(root);v.setContentsMargins(24,20,24,18);v.setSpacing(14)
        h=QHBoxLayout();title=label('UMS Control');title.setObjectName('title');h.addWidget(title);h.addStretch();self.ums_brand=label('Universal Media Server',True);self.ums_brand.setWordWrap(False);h.addWidget(self.ums_brand);v.addLayout(h)
        v.addWidget(label(tr('Tu biblioteca multimedia en un único servidor.'),True))
        self.tabs=QTabWidget();v.addWidget(self.tabs,1)
        self.make_home();self.make_tvs()
        foot=QHBoxLayout();self.message=label(tr('Sin cambios pendientes'),True);foot.addWidget(self.message,1)
        self.discard=button(tr('Descartar cambios'),self.discard_changes);foot.addWidget(self.discard);self.save=button(tr('Guardar y aplicar'),self.apply,True);self.save.setShortcut('Ctrl+S');self.save.setToolTip(tr('Guardar ajustes y reiniciar UMS si está activo · Ctrl+S'));foot.addWidget(self.save);v.addLayout(foot)
        self.populate();self.set_ui_language(initial_language,persist=False);self.discard.setEnabled(False);self.save.setEnabled(False);self.refresh();self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(10000)
        if self.legacy_migration:self.mark();self.message.setText(tr('Hay ajustes pendientes de guardar'))
        QTimer.singleShot(0,self.check_updates)

    def make_menus(self):
        themes=self.menuBar().addMenu(tr('Tema'));self.theme_actions={};group=QActionGroup(self);group.setExclusive(True)
        for key,title in appearance.THEMES.items():
            action=themes.addAction(tr(title));action.setCheckable(True);action.setChecked(key==self.preferences['theme']);group.addAction(action);self.theme_actions[key]=action;action.triggered.connect(lambda checked,k=key:self.set_theme(k))
        languages=self.menuBar().addMenu(tr('Idioma'));group=QActionGroup(self);group.setExclusive(True);self.language_actions={}
        for key,title in appearance.LANGUAGES.items():
            action=languages.addAction(title);action.setCheckable(True);action.setChecked(key==self.preferences['language']);group.addAction(action);self.language_actions[key]=action;action.triggered.connect(lambda checked,k=key:self.set_ui_language(k))
        self.menuBar().addAction(tr('Instrucciones'),self.instructions)
        self.menuBar().addAction(tr('Acerca de'),self.about)

    def instructions(self):
        GuideDialog(self).exec()

    def set_theme(self,key):
        self.preferences['theme']=key;self.centralWidget().load_image();configure_theme(QApplication.instance(),key);self.theme_actions[key].setChecked(True);appearance.save(**self.preferences)

    def ui_translation(self,obj,slot,text,previous,key):
        identity=(obj,slot);saved=self.ui_texts.get(identity)
        source=saved[0] if saved and saved[1]==text else translate_between(text,previous,'es')
        translated=translate_between(source,'es',key);self.ui_texts[identity]=(source,translated)
        return translated

    def set_ui_language(self,key,persist=True):
        self.language_actions[key].setChecked(True);previous=self.preferences['language'];self.preferences['language']=key;set_language(key);configure_qt_language(QApplication.instance(),key)
        # Translate only UI captions, never names, paths, addresses, media titles or data.
        self.loading=True
        from PyQt6.QtGui import QAction
        for obj in [self]+self.findChildren(QObject):
            if isinstance(obj,QLineEdit):
                obj.setPlaceholderText(self.ui_translation(obj,'placeholder',obj.placeholderText(),previous,key))
            elif isinstance(obj,(QLabel,QPushButton,QCheckBox,QAction)):
                if obj in [self.tv_heading,self.now,self.ums_brand]:continue
                if isinstance(obj,QAction) and obj in self.language_actions.values():continue
                obj.setText(self.ui_translation(obj,'text',obj.text(),previous,key))
            elif isinstance(obj,QGroupBox):obj.setTitle(self.ui_translation(obj,'title',obj.title(),previous,key))
            if isinstance(obj,QComboBox):
                for i in range(obj.count()):obj.setItemText(i,self.ui_translation(obj,('item',i),obj.itemText(i),previous,key))
            if isinstance(obj,QTabWidget):
                for i in range(obj.count()):obj.setTabText(i,self.ui_translation(obj,('tab',i),obj.tabText(i),previous,key))
            if isinstance(obj,QWidget):
                obj.setToolTip(self.ui_translation(obj,'tooltip',obj.toolTip(),previous,key));obj.setAccessibleName(self.ui_translation(obj,'accessible',obj.accessibleName(),previous,key))
        self.loading=False
        if self.row>=0:self.mode_changed()
        if hasattr(self,'activity_data'):self.render_activity(self.activity_data)
        else:self.now.setText(tr('Sin datos todavía'))
        if persist:appearance.save(**self.preferences)

    def about(self):
        d=QDialog(self);d.setWindowTitle(tr('Acerca de UMS Control'));d.resize(620,480);v=QVBoxLayout(d)
        v.addWidget(label(tr('UMS Control · versión 1.0')))
        v.addWidget(label(tr('Aplicación creada por N3ruk.')))
        link=QLabel('<a href="https://github.com/N3ruk">GitHub · N3ruk ↗</a>');link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction);link.setOpenExternalLinks(True);v.addWidget(link)
        v.addWidget(label(tr('Licencia del frontend: GNU GPL v3.0 o posterior (GPL-3.0-or-later).')))
        v.addWidget(label(tr('UMS Control es una capa de gestión o frontend independiente. No desarrollamos el código de Universal Media Server ni somos una aplicación oficial del proyecto.')))
        v.addWidget(label(tr('El servidor es Universal Media Server (GPL-2.0), basado en PS3 Media Server. Incluye correcciones locales de integración con sus fuentes y licencia; no se presenta como código propio ni como una versión oficial. FFmpeg, Java y MediaInfo conservan sus respectivos créditos y licencias.')))
        v.addWidget(button(tr('Licencia del frontend'),lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str((RESOURCE_ROOT/'LICENSE'))))))
        v.addWidget(button(tr('Proyecto Universal Media Server ↗'),lambda:QDesktopServices.openUrl(QUrl('https://github.com/UniversalMediaServer/UniversalMediaServer'))))
        bb=QDialogButtonBox(QDialogButtonBox.StandardButton.Close);bb.rejected.connect(d.reject);v.addWidget(bb);d.exec()

    def update_server_buttons(self,report):
        self.server_report=report;present=report['present']
        self.health_button.setText(tr('Salud del servidor') if present else tr('Instalar servidor UMS'))
        self.uninstall_button.setEnabled(present and report['repairable'])
        # Integrity diagnosis must not prevent stopping a damaged process or opening its web.
        managed=present and report['kind']!='incompatible'
        status=report['status'];running=status in {'active','activating','reloading','deactivating'}
        self.server_controls[0].setEnabled(managed and not running)
        self.server_controls[1].setEnabled(managed and running)
        self.server_controls[2].setEnabled(managed and status=='active')
        self.web_button.setEnabled(present and status=='active');self.auto.setEnabled(managed)
        self.update_update_button()

    def check_updates(self):
        # A background job on every launch; never downloads/installs by itself.
        job=Job(releases.check_update);self.jobs.add(job)
        def done(result):
            self.latest_release=result['release'] if result['available'] else None;self.update_check_error=result['error'];self.update_status.setText(tr('No se pudo comprobar si hay actualizaciones del servidor. Se reintentará al abrir UMS Control.'));self.update_status.setToolTip(self.update_check_error or '');self.update_status.setVisible(bool(self.update_check_error));self.update_update_button()
        job.signals.done.connect(done);job.signals.finished.connect(lambda:self.jobs.discard(job));QThreadPool.globalInstance().start(job)

    def update_update_button(self):
        release=self.latest_release;report=getattr(self,'server_report',None)
        available=False
        if release and report and report['present'] and report['repairable']:
            try:available=releases.version_tuple(release['version'])>releases.version_tuple(releases.jar_version(core.RUNTIME))
            except (OSError,ValueError):pass
        self.update_button.setVisible(available)
        self.update_button.setToolTip(tr('Nueva versión disponible: {value}').replace('{value}',release['version']) if release else '')

    def update_server(self):
        release=self.latest_release
        if not release:return
        text=tr('Se actualizará el servidor a UMS {value}. Se conservarán carpetas, perfiles y configuración. Si está en ejecución, se reiniciará y se interrumpirá la reproducción. Si falla la actualización, se restaurará la instalación anterior.').replace('{value}',release['version'])
        if QMessageBox.question(self,tr('Actualizar servidor UMS'),text,QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Cancel)!=QMessageBox.StandardButton.Yes:return
        def done(report):
            self.latest_release=None;self.update_server_buttons(report);self.message.setText(tr('Servidor actualizado'));self.refresh()
        self.task(lambda:manager.update(release),done)

    def server_health(self):
        def done(report):
            self.update_server_buttons(report)
            if not report['present']:self.confirm_server_install(report);return
            d=QDialog(self);d.setWindowTitle(tr('Salud del servidor'));d.resize(660,490);v=QVBoxLayout(d)
            headings={'healthy':tr('Instalación compatible e íntegra'),'damaged':tr('Instalación dañada o incompleta'),'incompatible':tr('Instalación no compatible'),'absent':tr('Servidor no instalado')}
            v.addWidget(label(headings[report['kind']]))
            statuses={'active':tr('En ejecución'),'inactive':tr('Detenido (no es una avería)'),'failed':tr('Servicio con error'),'activating':tr('iniciando'),'deactivating':tr('Deteniéndose')}
            v.addWidget(label(statuses.get(report['status'],report['status'])))
            details=QTextBrowser();details.setPlainText('\n\n'.join(tr(s) for s in report['issues']+report['warnings']) or tr('No se han detectado problemas. Detener el servidor no requiere reinstalarlo.'));v.addWidget(details)
            if report['kind']=='damaged' and report['repairable']:
                v.addWidget(label(tr('Se recomienda reinstalar los archivos del servidor. Se conservarán ajustes, perfiles y archivos multimedia.')))
                def repair():
                    d.accept();self.confirm_server_install(report,repair=True)
                v.addWidget(button(tr('Reinstalar servidor UMS…'),repair,True))
            v.addWidget(button(tr('Ver registro del servidor'),self.server_log))
            bb=QDialogButtonBox(QDialogButtonBox.StandardButton.Close);bb.rejected.connect(d.reject);v.addWidget(bb);d.exec()
        self.task(lambda:manager.health(deep=True),done)

    def server_log(self):
        def done(text):
            d=QDialog(self);d.setWindowTitle(tr('Registro del servidor'));d.resize(800,480);v=QVBoxLayout(d);view=QTextBrowser();view.setPlainText(text);v.addWidget(view);bb=QDialogButtonBox(QDialogButtonBox.StandardButton.Close);bb.rejected.connect(d.reject);v.addWidget(bb);d.exec()
        self.task(core.server_log,done)

    def confirm_server_install(self,report,repair=False):
        if not report['repairable']:
            QMessageBox.warning(self,tr('Servidor no compatible'),tr('La ruta o el servicio pertenece a otra instalación; no se modificará.'));return
        text=tr('Se descargará la última versión estable de UMS desde el proyecto oficial y se verificará su huella y compatibilidad. Se instalará solo para tu usuario, sin permisos de administrador. Se conservarán los ajustes y los archivos multimedia. No se iniciará un servidor que estuviera detenido.')
        if report['foreign']:text+='\n\n'+tr('Se ha detectado otra instalación de UMS. No se modificará ni se desinstalará. Evita iniciar ambos servidores a la vez.')
        title=tr('Reinstalar servidor UMS') if repair else tr('Instalar servidor UMS')
        if QMessageBox.question(self,title,text,QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Cancel)!=QMessageBox.StandardButton.Yes:return
        def done(result):
            self.update_server_buttons(result)
            if not (core.PROFILE/'UMS.conf').exists():self.mark()
            self.message.setText(tr('Operación del servidor completada'));self.refresh()
        self.task(lambda:manager.install(repair=repair),done)

    def uninstall_server(self):
        text=tr('Se detendrá y deshabilitará únicamente el servidor UMS gestionado por esta aplicación y sus archivos se moverán a la papelera. UMS Control seguirá instalado. Se conservarán perfiles, configuración, archivos multimedia y otros servidores. ¿Continuar?')
        if QMessageBox.question(self,tr('Desinstalar servidor UMS'),text,QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Cancel)!=QMessageBox.StandardButton.Yes:return
        self.task(manager.uninstall,lambda report:(self.update_server_buttons(report),self.message.setText(tr('Servidor desinstalado. Configuración y archivos multimedia conservados.'))))

    def task(self,fn,done=None,busy=True,quiet=False):
        j=Job(fn);self.jobs.add(j)
        if busy:self.control_generation+=1;self.busy=True;self.centralWidget().setEnabled(False);self.menuBar().setEnabled(False);self.message.setText(tr('Trabajando…'))
        def error(s):
            finish()
            self.message.setText(tr('No se pudo completar la operación'))
            if not quiet:QMessageBox.warning(self,'UMS Control',tr(s))
            if busy:self.refresh()
        def finish():
            if j not in self.jobs:return
            self.jobs.discard(j)
            if busy:self.busy=False;self.centralWidget().setEnabled(True);self.menuBar().setEnabled(True)
        if done:
            def deliver(value):
                finish()
                try:done(value)
                except Exception as e:error(str(e))
            j.signals.done.connect(deliver)
        j.signals.error.connect(lambda _:setattr(self,'refreshing',False) if not busy else None);j.signals.error.connect(error);j.signals.finished.connect(finish);QThreadPool.globalInstance().start(j)

    def mark(self,*_):
        if self.loading:return
        self.dirty=True;self.discard.setEnabled(True);self.save.setEnabled(True);self.message.setText(tr('Sin aplicar · Guardar reinicia UMS e interrumpe la reproducción'))

    def make_home(self):
        w=SummaryBody();w.setObjectName('scrollBody');v=QVBoxLayout(w);v.setContentsMargins(16,12,16,12);v.setSpacing(6)
        self.status=label(tr('Comprobando servidor…'));self.status.setObjectName('status');v.addWidget(self.status)
        controls=QHBoxLayout()
        for txt,act in [(tr('Iniciar'),'start'),(tr('Detener'),'stop'),(tr('Reiniciar'),'restart')]:controls.addWidget(button(txt,lambda _,a=act:self.server_action(a)))
        controls.addStretch();web_column=QVBoxLayout();self.web_button=button(tr('Abrir UMS web ↗'),self.open_web);web_column.addWidget(self.web_button)
        self.update_button=button(tr('Actualizar servidor UMS'),self.update_server);self.update_button.hide();web_column.addWidget(self.update_button);controls.addLayout(web_column);v.addLayout(controls)
        management=QHBoxLayout();self.health_button=button(tr('Comprobando servidor…'),self.server_health);management.addWidget(self.health_button);self.uninstall_button=button(tr('Desinstalar servidor UMS'),self.uninstall_server);management.addWidget(self.uninstall_button);management.addStretch();v.addLayout(management)
        self.update_status=label('',True);self.update_status.hide();v.addWidget(self.update_status)
        self.server_controls=[controls.itemAt(i).widget() for i in range(3)]
        self.server_report=None
        self.auto=QCheckBox(tr('Iniciar el servidor al entrar en mi sesión de Ubuntu'));self.auto.clicked.connect(self.toggle_autostart);v.addWidget(self.auto)
        box=QGroupBox(tr('Dispositivos y reproducción'));b=QVBoxLayout(box)
        b.addWidget(label(tr('Dispositivos detectados por UMS. Se actualiza cada 10 segundos; la disponibilidad y la reproducción dependen de la información que envía cada dispositivo.'),True))
        self.now=label(tr('Sin datos todavía'),True);b.addWidget(self.now);v.addWidget(box)
        box=QGroupBox(tr('Servidor'));form=QFormLayout(box);self.server_name=QLineEdit();self.server_name.textEdited.connect(self.mark);form.addRow(tr('Nombre desde cliente'),self.server_name)
        self.server_name.setToolTip(tr('Nombre con el que los dispositivos ven esta biblioteca multimedia.'))
        self.interface=combo(self.network_choices());self.interface.currentIndexChanged.connect(self.mark);form.addRow(tr('Red del servidor'),self.interface)
        form.addRow(label(tr('Selecciona la conexión de este equipo que comparte red con tus dispositivos.'),True));v.addWidget(box)
        v.addWidget(button(tr('Actualizar catálogo multimedia'),self.scan))
        v.addWidget(label(tr('Vuelve a explorar las carpetas guardadas para detectar archivos nuevos, modificados o eliminados. No modifica los originales. Puede tardar según el tamaño de la biblioteca.'),True))
        v.addStretch();scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(w);self.tabs.addTab(scroll,tr('Resumen'))

    def network_choices(self):
        choices=[]
        for item in core.network_interfaces():
            name=item['name'];kind=item['kind'];number=item['number']
            if kind=='other':title=tr('Otra red ({value})').replace('{value}',name)
            else:title=('Ethernet' if kind=='ethernet' else 'WiFi')+(' '+str(number) if number>1 else '')
            choices.append((title,name))
        saved=self.state['interface']
        if saved and saved not in {name for _,name in choices}:choices.append((tr('Red no disponible ({value})').replace('{value}',saved),saved))
        return choices

    def make_tvs(self):
        w=QWidget();w.setObjectName('tabBody');outer=QVBoxLayout(w);outer.setContentsMargins(16,14,16,14)
        outer.addWidget(label(tr('Cada dispositivo tiene sus propios ajustes. Selecciona uno para ver cómo recibirá los vídeos.'),True))
        split=QSplitter();outer.addWidget(split,1);split.setChildrenCollapsible(False)
        left=QWidget();lv=QVBoxLayout(left);lv.setContentsMargins(0,0,10,0)
        lv.addWidget(label(tr('DISPOSITIVOS'),True))
        self.tvlist=QListWidget();self.tvlist.setAccessibleName(tr('Dispositivos configurados'));self.tvlist.setMinimumWidth(180);self.tvlist.currentRowChanged.connect(self.select_tv);lv.addWidget(self.tvlist,1)
        lv.addWidget(button(tr('Buscar en la red…'),self.search_tvs));lv.addWidget(button(tr('Añadir por IP'),self.add_tv))
        self.remove_button=button(tr('Retirar perfil'),self.remove_tv);self.remove_button.setToolTip(tr('Deja de compartir carpetas con este dispositivo al guardar. No borra archivos.'));lv.addWidget(self.remove_button);split.addWidget(left)
        self.editor=QWidget();ev=QVBoxLayout(self.editor);ev.setContentsMargins(8,0,0,0)
        self.tv_heading=label(tr('Selecciona o añade un dispositivo'));self.tv_heading.setObjectName('sectionTitle');ev.addWidget(self.tv_heading)
        self.profile_summary=label('');self.profile_summary.setObjectName('explanation');self.profile_summary.setAccessibleName(tr('Resumen del perfil seleccionado'));ev.addWidget(self.profile_summary)
        self.detail_tabs=QTabWidget();self.detail_tabs.tabBar().setObjectName('deviceTabBar');ev.addWidget(self.detail_tabs,1);self.fields={}
        def page(title):
            scroll=QScrollArea();scroll.setWidgetResizable(True);body=QWidget();body.setObjectName('scrollBody');layout=QVBoxLayout(body);layout.setContentsMargins(12,10,12,12);layout.setSpacing(12);scroll.setWidget(body);self.detail_tabs.addTab(scroll,title);return layout
        def group(parent,title):
            box=QGroupBox(title);form=QFormLayout(box);form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows);form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow);form.setVerticalSpacing(10);parent.addWidget(box);return form
        def field(form,key,title,values=None,widget=None,tip=''):
            control=widget if widget is not None else combo(values)
            control.setAccessibleName(title or control.text());control.setToolTip(tip);self.fields[key]=control
            if title:
                caption=QLabel(title);caption.setBuddy(control);form.addRow(caption,control)
            else:form.addRow(control)
            return control
        shared=page(tr('Carpetas compartidas'))
        shared.addWidget(label(tr('Elige las carpetas que verá este dispositivo. La selección no afecta a otros dispositivos y no crea copias de los archivos.'),True))
        self.folders=QListWidget();self.folders.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection);self.folders.setMinimumHeight(150);self.folders.setAccessibleName(tr('Carpetas compartidas'));shared.addWidget(self.folders,1)
        h=QHBoxLayout();h.addWidget(button(tr('Añadir carpeta…'),self.add_folder));h.addWidget(button(tr('Dejar de compartir selección'),self.remove_folders));h.addStretch();shared.addLayout(h)
        shared.addWidget(label(tr('La selección incluye subcarpetas. Dejar de compartir no borra archivos. Para compartir solo una parte, añade las subcarpetas en lugar de su carpeta padre.'),True))
        play=page(tr('Reproducción'))
        f=group(play,tr('Cómo enviar los vídeos'))
        field(f,'mode',tr('Reproducción'),[(tr('Original · enviar el archivo intacto'),'direct'),(tr('Convertir las carpetas seleccionadas'),'force'),(tr('Convertir incompatibles automáticamente'),'auto')])
        self.mode_help=label('',True);f.addRow(self.mode_help)
        f=group(play,tr('Audio y subtítulos'))
        self.subtitle_group=f.parentWidget()
        field(f,'subtitles',tr('Tratamiento'),[(tr('A · Gestionados por el dispositivo'),'passthrough'),(tr('B · Preseleccionados e incrustados'),'burn')])
        self.subtitle_help=label('',True);f.addRow(self.subtitle_help)
        field(f,'external_subtitles','',widget=QCheckBox(tr('Buscar subtítulos junto al vídeo')),tip=tr('Añade los archivos encontrados a las combinaciones de Transcodificar. No descarga ni fuerza un subtítulo externo.'))
        self.external_subtitle_help=label(tr('Misma carpeta y nombre del vídeo: Pelicula.mkv + Pelicula.spa.srt (también ASS/SSA). Guarda y aplica; después vuelve a entrar en Transcodificar desde el dispositivo.'),True);f.addRow(self.external_subtitle_help)
        f=group(play,tr('Carpetas que se convierten'))
        self.conversion_group=f.parentWidget()
        self.conversion_folders=FolderRuleTree();self.conversion_folders.setAccessibleName(tr('Carpetas que se convierten'));self.conversion_folders.rulesChanged.connect(self.tv_edited);f.addRow(self.conversion_folders)
        self.conversion_empty=label(tr('Añade carpetas en Carpetas compartidas para elegir cuáles convertir.'),True);f.addRow(self.conversion_empty)
        f.addRow(label(tr('Marcada: convertir. Sin marcar: enviar original. Despliega para elegir subcarpetas y crear excepciones. Las carpetas nuevas heredan la regla de su carpeta padre.'),True))
        f=group(play,tr('Nombres anunciados al dispositivo'))
        field(f,'name_mode',tr('Nombre de los vídeos'),[(tr('Nombre original'),'original'),(tr('Nombre compatible · todas las carpetas'),'compatible'),(tr('Nombre compatible · carpetas seleccionadas'),'selected')])
        self.name_help=label(tr('Solo cambia el título y el nombre del enlace: minúsculas, sin tildes, ñ, espacios ni signos. Conserva el título reconocible y la extensión. No modifica archivos ni convierte el vídeo.'),True);f.addRow(self.name_help)
        self.name_folders=FolderRuleTree();self.name_folders.setAccessibleName(tr('Carpetas con nombres compatibles'));self.name_folders.rulesChanged.connect(self.tv_edited);f.addRow(self.name_folders)
        self.name_tree_help=label(tr('Despliega las carpetas para elegir subcarpetas. Una selección parcial indica excepciones; marcar o desmarcar una carpeta aplica la regla a toda su rama.'),True);f.addRow(self.name_tree_help)
        play.addStretch()
        quality=page(tr('Calidad y audio'));self.quality_page=self.detail_tabs.widget(2)
        self.direct_notice=label(tr('Ajustes por dispositivo: se aplican a las carpetas seleccionadas o a los archivos que necesiten adaptación en modo automático. Original no modifica el archivo.'),True);quality.addWidget(self.direct_notice)
        self.advanced=QWidget();quality.addWidget(self.advanced);ql=QVBoxLayout(self.advanced);ql.setContentsMargins(0,0,0,0)
        f=group(ql,tr('Vídeo · límites y conversión'))
        field(f,'resolution',tr('Resolución máxima'),[(tr('480p · consumo mínimo'),'480p'),(tr('720p · conexión limitada'),'720p'),(tr('1080p · Full HD'),'1080p'),(tr('1440p · QHD'),'1440p'),(tr('2160p · 4K'),'2160p'),(tr('Sin límite de resolución'),'original')])
        field(f,'bitrate',tr('Bitrate máximo'),[(f'{n} Mbps',n) for n in [3,5,8,10,15,20,25,30,40,50,60,80,100]]+[(tr('Sin límite'),0)],tip=tr('Límite de la conversión en megabits por segundo. Sin límite deja variar el bitrate según el contenido y la calidad de codificación.'))
        self.bitrate_help=label(tr('Al cambiar la resolución se preselecciona un bitrate recomendado, que puede modificarse después.')+' '+tr('Elige un límite del catálogo o Sin límite: bitrate variable según el contenido y la calidad de conversión, sin máximo impuesto por el panel. No se adapta a la velocidad de la red. Un límite bajo puede reducir la calidad.'),True);f.addRow(self.bitrate_help)
        field(f,'target',tr('Formato convertido'),[(tr('H.264 + AC3 · compatibilidad amplia'),'MPEGTS-H264-AC3'),(tr('H.264 + AAC · compatibilidad alta en equipos modernos'),'MPEGTS-H264-AAC'),(tr('MPEG-2 + AC3 · orientado a equipos antiguos'),'MPEGPS-MPEG2-AC3')])
        self.format_help=label('',True);f.addRow(self.format_help)
        field(f,'container',tr('Contenedor'),[(tr('Automático'),'auto'),('MKV · Matroska','mkv'),('MPEG-TS','mpegts'),('MPEG-PS · MPEG-2','mpegps'),('MP4 · H.264','mp4')])
        self.container_help=label('',True);f.addRow(self.container_help)
        field(f,'encoder',tr('Procesador de vídeo'),[(tr('CPU · procesador del PC'),'cpu'),(tr('NVIDIA NVENC · tarjeta gráfica compatible'),'nvidia')])
        self.encoding_help=label('',True);f.addRow(self.encoding_help)
        f=group(ql,tr('Audio · pistas y calidad al convertir'))
        field(f,'channels',tr('Canales'),[(tr('Estéreo · 2 canales'),2),(tr('Envolvente · hasta 5.1'),6)])
        field(f,'audio_bitrate',tr('Bitrate de audio'),[(f'{n} kbps'+(tr(' · valor UMS habitual') if n==448 else ''),n) for n in [128,192,256,384,448,640]])
        self.audio_help=label('',True);f.addRow(self.audio_help)
        self.audio_selection_help=label(tr('Modo A: convierte todas las pistas de audio para elegirlas en el dispositivo. Modo B: envía el audio elegido en Transcodificar; la entrada principal mantiene la selección automática. Hasta 5.1 requiere una pista y un equipo compatibles.'),True);f.addRow(self.audio_selection_help);quality.addStretch()
        identity=page(tr('Identificación'));f=group(identity,tr('Cómo identificar este dispositivo'))
        for key,title,placeholder in [('name',tr('Nombre del perfil'),tr('Ej. Dispositivo del salón')),('ip',tr('Dirección IPv4'),tr('Ej. 192.168.1.20')),('udn',tr('UUID detectado'),tr('uuid:… (opcional si hay IP)'))]:
            edit=QLineEdit();edit.setPlaceholderText(placeholder);field(f,key,title,widget=edit)
        f.addRow(label(tr('El nombre es una etiqueta local. El UUID permite reconocer el dispositivo aunque cambie de IP; si usas solo IP, resérvala en el router. Es necesaria al menos una de las dos identificaciones.'),True))
        f=group(identity,tr('Reutilizar ajustes'))
        f.addRow(button(tr('Copiar ajustes de otro dispositivo…'),self.copy_tv_settings));f.addRow(label(tr('Copia reproducción, calidad y audio. Mantiene la identificación, las carpetas compartidas y su selección de conversión.'),True));identity.addStretch()
        split.addWidget(self.editor);split.setSizes([220,820]);self.tabs.addTab(w,tr('Dispositivos'))
        for key,control in self.fields.items():
            if isinstance(control,QComboBox):control.currentIndexChanged.connect(self.resolution_changed if key=='resolution' else self.tv_edited)
            elif isinstance(control,QSpinBox):control.valueChanged.connect(self.tv_edited)
            elif isinstance(control,QCheckBox):control.toggled.connect(self.tv_edited)
            else:control.textEdited.connect(self.tv_edited)
        self.fields['name'].textEdited.connect(self.update_tv_name)

    def resolution_changed(self,*_):
        if self.loading or self.row<0:return
        bitrate=self.fields['bitrate']
        with QSignalBlocker(bitrate):
            bitrate.setCurrentIndex(bitrate.findData(RECOMMENDED_BITRATES[self.fields['resolution'].currentData()]))
        self.tv_edited()

    def tv_edited(self,*_):
        if self.loading:return
        self.mark();self.mode_changed()

    def update_tv_name(self,text):
        if self.row>=0:self.tvlist.item(self.row).setText(text.strip() or tr('Sin nombre'))

    def copy_tv_settings(self):
        if self.row<0:return
        others=[t for i,t in enumerate(self.state['tvs']) if i!=self.row]
        if not others:QMessageBox.information(self,tr('Copiar ajustes'),tr('Añade otro dispositivo para poder copiar sus ajustes.'));return
        d=QDialog(self);d.setWindowTitle(tr('Copiar ajustes a ')+self.fields['name'].text());layout=QVBoxLayout(d);layout.addWidget(label(tr('Se sustituirán los ajustes de este dispositivo en el formulario, sin cambiar su identificación. El servidor no cambia hasta guardar.')))
        source=combo([(t['name']+' · '+t['ip'],t['id']) for t in others]);source.setAccessibleName(tr('Dispositivo de origen'));layout.addWidget(source)
        bb=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);bb.accepted.connect(d.accept);bb.rejected.connect(d.reject);layout.addWidget(bb)
        if d.exec()!=QDialog.DialogCode.Accepted:return
        self.commit_tv();origin=next(t for t in others if t['id']==source.currentData());target=self.state['tvs'][self.row]
        for key in self.fields:
            if key not in {'name','ip','udn'}:target[key]=copy.deepcopy(origin.get(key,True) if key=='show_transcode_folder' else core.tv_value(origin,key) if key in {'resume','external_subtitles','audio_bitrate','container','name_mode'} else origin[key])
        self.row=-1;self.select_tv(self.tvlist.currentRow());self.mark()

    def discard_changes(self):
        if not self.dirty:return
        if QMessageBox.question(self,tr('Descartar cambios'),tr('¿Volver a la configuración guardada? Se perderán los cambios sin aplicar.'),QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Cancel)!=QMessageBox.StandardButton.Discard:return
        self.state=core.load_state();self.state['tvs']=[core.editable_tv(t) for t in self.state['tvs']];self.populate();self.dirty=False;self.save.setEnabled(False);self.discard.setEnabled(False);self.message.setText(tr('Configuración guardada recuperada · Sin reiniciar UMS'))

    def populate(self):
        self.loading=True;self.server_name.setText(self.state['name']);self.interface.setCurrentIndex(self.interface.findData(self.state['interface']))
        self.row=-1;self.tvlist.clear()
        for t in self.state['tvs']:self.tvlist.addItem(t['name'])
        self.loading=False
        if self.state['tvs']:self.tvlist.setCurrentRow(0)
        else:self.select_tv(-1)

    def commit_tv(self):
        if self.row<0 or self.row>=len(self.state['tvs']):return
        t=self.state['tvs'][self.row]
        for k,w in self.fields.items():
            t[k]=w.currentData() if isinstance(w,QComboBox) else w.value() if isinstance(w,QSpinBox) else w.isChecked() if isinstance(w,QCheckBox) else w.text().strip()
        t['folders']=[self.folders.item(i).text() for i in range(self.folders.count())]
        t['convert_folders'],t['convert_exclusions']=self.conversion_folders.selection()
        t['name_folders'],t['name_exclusions']=self.name_folders.selection()
        t.update(preset='compatible',show_transcode_folder=t['mode']!='direct',resume=False)
        self.tvlist.item(self.row).setText(t['name'] or tr('Sin nombre'))

    def select_tv(self,row):
        if self.loading:return
        self.commit_tv();self.row=row;self.editor.setEnabled(row>=0);self.remove_button.setEnabled(row>=0)
        if row<0:self.folders.clear();self.conversion_folders.configure([],[]);self.name_folders.configure([],[]);self.tv_heading.setText(tr('Añade un dispositivo para configurar su reproducción'));self.profile_summary.setText(tr('Usa «Buscar en la red» o «Añadir por IP».'));return
        self.loading=True;t=self.state['tvs'][row]
        self.render_folders(t['folders'],t['convert_folders'],core.tv_value(t,'convert_exclusions'),core.tv_value(t,'name_folders'),core.tv_value(t,'name_exclusions'))
        for k,w in self.fields.items():
            if k=='bitrate' and w.findData(t[k])<0:w.addItem(str(t[k])+tr(' Mbps · valor guardado'),t[k])
            if isinstance(w,QComboBox):w.setCurrentIndex(w.findData(t.get(k,True) if k=='show_transcode_folder' else core.tv_value(t,k) if k in {'audio_bitrate','container','name_mode'} else t[k]))
            elif isinstance(w,QSpinBox):w.setValue(core.tv_value(t,k) if k in {'audio_bitrate','container','name_mode'} else t[k])
            elif isinstance(w,QCheckBox):w.setChecked(core.tv_value(t,k))
            else:w.setText(t[k])
        self.loading=False;self.mode_changed()

    def render_folders(self,folders,converted,excluded=(),named=None,name_excluded=None):
        previous=self.loading;self.loading=True
        if named is None:named=self.name_folders.selection()[0]
        if name_excluded is None:name_excluded=self.name_folders.selection()[1]
        self.folders.clear()
        for path in folders:
            item=QListWidgetItem(path);item.setToolTip(tr('Disponible') if Path(path).is_dir() else tr('Ubicación no disponible: comprueba su conexión y permisos.'));self.folders.addItem(item)
        self.conversion_folders.configure(folders,converted,excluded)
        self.name_folders.configure(folders,named,name_excluded)
        self.conversion_empty.setVisible(not folders);self.loading=previous

    def mode_changed(self):
        direct=self.fields['mode'].currentData()=='direct';automatic=self.fields['mode'].currentData()=='auto';sub=self.fields['subtitles'].currentData();burn=sub=='burn'
        selected_names=self.fields['name_mode'].currentData()=='selected'
        self.name_folders.setVisible(selected_names);self.name_tree_help.setVisible(selected_names)
        self.subtitle_group.setVisible(not direct);self.conversion_group.setVisible(not direct)
        self.subtitle_group.setEnabled(not direct);self.conversion_group.setEnabled(not direct and not automatic)
        self.detail_tabs.setTabEnabled(2,not direct);self.quality_page.setEnabled(not direct);self.advanced.setEnabled(not direct)
        if direct and self.detail_tabs.currentIndex()==2:self.detail_tabs.setCurrentIndex(1)
        self.fields['external_subtitles'].setEnabled(not direct and burn)
        self.external_subtitle_help.setVisible(burn)
        self.fields['encoder'].setEnabled(self.fields['target'].currentData()!='MPEGPS-MPEG2-AC3')
        self.mode_help.setText(tr('Envía el archivo intacto: vídeo, audio y subtítulos originales. Sin límite artificial de bitrate; la velocidad necesaria depende de los picos del archivo y de la red, no solo de su tamaño (p. ej. 50 GB). No muestra Transcodificar ni alternativas.') if direct else tr('Convierte solo los vídeos de las carpetas marcadas en el apartado 3. El resto se envía en original. La conversión consume recursos y no modifica los archivos.'))
        self.subtitle_help.setText(tr('No se aplica: en Original, el dispositivo recibe las pistas del archivo sin modificar.') if direct else tr('En Transcodificar, elige el audio y el subtítulo antes de reproducir, o Sin subtítulos. Se envía un único audio y se incrusta el subtítulo elegido. La entrada principal conserva la selección automática del servidor.') if burn else tr('Conserva las pistas de audio para elegirlas en el dispositivo. MKV mantiene los subtítulos integrados; MP4 conserva los de texto; MPEG-TS y MPEG-PS no conservan subtítulos seleccionables. Usa B para incrustarlos. No incorpora subtítulos externos.'))
        nvidia=self.fields['encoder'].currentData()=='nvidia';mpeg=self.fields['target'].currentData()=='MPEGPS-MPEG2-AC3'
        self.audio_help.setText(tr('UMS limita AAC a 320 kbps y puede ajustar AC3 según los canales; el resultado depende del códec. Se convierte también el audio para respetar estos ajustes.'))
        descriptions={'MPEGTS-H264-AC3':tr('H.264 + AC3: vídeo eficiente y audio Dolby Digital, frecuente en dispositivos y receptores. Compatibilidad general amplia; algunos móviles o navegadores no admiten AC3.'), 'MPEGTS-H264-AAC':tr('H.264 + AAC: vídeo eficiente y audio habitual en dispositivos modernos. Compatibilidad general alta; algunos dispositivos antiguos tienen limitaciones con AAC multicanal.'), 'MPEGPS-MPEG2-AC3':tr('MPEG-2 + AC3: orientado a dispositivos antiguos. Necesita más ancho de banda para una calidad similar a H.264; no es la opción más eficiente para HD/4K.')}
        self.format_help.setText(descriptions[self.fields['target'].currentData()]+tr(' La compatibilidad final depende del contenedor, las pistas y el dispositivo; no es universal.'))
        container=self.fields['container'].currentData()
        for index in range(self.fields['container'].count()):
            value=self.fields['container'].itemData(index)
            self.fields['container'].model().item(index).setEnabled(not (value=='mpegps' and not mpeg) and not (value=='mp4' and mpeg))
        invalid=(container=='mpegps' and not mpeg) or (container=='mp4' and mpeg)
        self.container_help.setText(tr('MPEG-PS necesita MPEG-2 + AC3. MP4 necesita H.264. Cambia el formato o el contenedor antes de guardar.') if invalid else tr('Contenedor automático: en conversión manual usa MKV en A y MPEG-TS/PS en B; en modo automático consulta el perfil del dispositivo. Elegir un contenedor fuerza esa entrega al adaptar; Original permanece intacto.'))
        self.encoding_help.setText((tr('MPEG-2 se codifica por CPU; NVENC no se usa para esta salida.') if mpeg else tr('NVENC requiere NVIDIA y controlador compatible. Acelera la codificación H.264, no la decodificación de High 10.') if nvidia else tr('La CPU convierte el vídeo. La fluidez depende de la carga y resolución.'))+tr(' No se garantiza equivalencia HDR/SDR.'))
        name=self.fields['name'].text().strip() or tr('Dispositivo sin nombre');address=self.fields['ip'].text() or tr('identificada por UUID');self.tv_heading.setText(name+' · '+address)
        self.profile_summary.setText(tr('Original intacto · sin límite de conversión · sin Transcodificar') if direct else tr('Conversión por carpeta · ')+(tr('audio preseleccionado y subtítulos incrustados · Transcodificar visible') if burn else tr('MKV con audio y subtítulos seleccionables · sin Transcodificar')))

        if not direct and not burn:
            self.profile_summary.setText(tr('Conversión por carpeta · audio seleccionable · contenedor configurable'))
        if automatic:
            self.mode_help.setText(tr('Comprueba cada archivo de todas las carpetas compartidas con el perfil del dispositivo y los límites elegidos. Envía original lo compatible; adapta contenedor, audio o vídeo cuando hace falta. Si UMS no reconoce el modelo, usa reglas conservadoras.'))
            self.profile_summary.setText(tr('Automático · original si es compatible · adaptación cuando sea necesaria'))
            self.audio_help.setText(tr('Automático conserva los audios compatibles y convierte los demás. Los límites de canales se aplican al adaptar; la calidad de audio solo cambia al recodificar.'))

    def snapshot(self):
        self.commit_tv();s=copy.deepcopy(self.state);s['name']=self.server_name.text().strip();s['interface']=self.interface.currentData();return s

    def apply(self):
        try:s=self.snapshot();core.validate(s)
        except Exception as e:QMessageBox.warning(self,tr('Revisa los ajustes'),tr(str(e)));return
        def done(_):
            self.state=core.load_state();self.dirty=False;self.save.setEnabled(False);self.discard.setEnabled(False);self.message.setText(tr('Configuración aplicada y confirmada por UMS') if core.active()=='active' else tr('Configuración guardada · Servidor detenido'));self.refresh()
        self.task(lambda:core.apply(s),done)

    def add_folder(self):
        selected=self.folders.currentItem()
        initial=Path(selected.text()) if selected else Path.home()
        if not initial.is_dir():initial=Path.home()
        p=QFileDialog.getExistingDirectory(self,tr('Seleccionar carpeta para compartir'),str(initial))
        if not p or self.row<0:return
        folders=[self.folders.item(i).text() for i in range(self.folders.count())]
        try:core.validate_folders(folders+[p])
        except ValueError as e:QMessageBox.warning(self,tr('Revisa los ajustes'),tr(str(e)));return
        self.commit_tv();tv=self.state['tvs'][self.row];self.render_folders(folders+[p],tv['convert_folders'],tv['convert_exclusions']);self.mark();self.mode_changed()

    def remove_folders(self):
        if self.row<0:return
        self.commit_tv();removed={it.text() for it in self.folders.selectedItems()};tv=self.state['tvs'][self.row]
        self.render_folders([f for f in tv['folders'] if f not in removed],tv['convert_folders'],tv['convert_exclusions']);self.mark();self.mode_changed()

    def add_tv(self):
        self.commit_tv();t=core.default_tv(tr('Nuevo dispositivo'));self.state['tvs'].append(t);self.tvlist.addItem(t['name']);self.tvlist.setCurrentRow(len(self.state['tvs'])-1);self.mark()

    def remove_tv(self):
        row=self.tvlist.currentRow()
        if row<0:return
        self.loading=True;self.row=-1;self.state['tvs'].pop(row);self.tvlist.takeItem(row);self.loading=False
        row=min(row,len(self.state['tvs'])-1);self.tvlist.setCurrentRow(row);self.select_tv(row);self.mark()

    def search_tvs(self):
        interface=self.interface.currentData()
        self.message.setText(tr('Buscando dispositivos y clientes UMS… En PS3, abre Vídeo → Buscar servidores multimedia durante la búsqueda.'))
        def found(devices):
            if not devices:QMessageBox.information(self,tr('Buscar dispositivos'),tr('No se han detectado dispositivos. Enciende el dispositivo, abre su cliente multimedia compatible con DLNA e inténtalo de nuevo. También puedes añadir su IP manualmente.'));return
            d=QDialog(self);d.setWindowTitle(tr('Dispositivos detectados'));d.resize(640,350);v=QVBoxLayout(d);v.addWidget(label(tr('Selecciona los dispositivos que quieras añadir o actualizar. Los ajustes existentes se conservan.'),True));lst=QListWidget();lst.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
            for t in devices:lst.addItem(t['name']+' · '+t['ip']+' · '+t['model'])
            v.addWidget(lst);bb=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);bb.accepted.connect(d.accept);bb.rejected.connect(d.reject);v.addWidget(bb)
            if d.exec()!=QDialog.DialogCode.Accepted:return
            self.commit_tv()
            for item in lst.selectedItems():
                t=devices[lst.row(item)];existing=next((x for x in self.state['tvs'] if (x['udn'] and x['udn']==t['udn']) or x['ip']==t['ip']),None)
                if existing:
                    existing['ip']=t['ip']
                    if t['udn']:existing['udn']=t['udn']
                else:self.state['tvs'].append(core.default_tv(t['name'],t['ip'],t['udn']))
            self.state['name']=self.server_name.text();self.state['interface']=self.interface.currentData();self.populate();self.mark()
        self.task(lambda:core.discover(interface),found)

    def server_action(self,action):
        def done(report):
            self.update_server_buttons(report);self.message.setText(tr('Servidor ')+(tr('detenido') if action=='stop' else tr('disponible')));self.refresh()
        self.task(lambda:manager.control(action),done)

    def open_web(self):
        try:
            url=core.web_url()
            # Prefer the session's registered browser independently of Qt portal appID.
            opener=shutil.which('gio') or shutil.which('xdg-open')
            if opener:
                args=[opener,'open',url] if Path(opener).name=='gio' else [opener,url]
                def opened(result):
                    if result.returncode and not QDesktopServices.openUrl(QUrl(url)):
                        QMessageBox.warning(self,'UMS Control',result.stderr or result.stdout or tr('No se pudo completar la operación'))
                self.task(lambda:core.run(args,check=False,timeout=15),opened,busy=False)
            elif not QDesktopServices.openUrl(QUrl(url)):raise RuntimeError(tr('No se pudo completar la operación'))
        except Exception as e:QMessageBox.warning(self,'UMS Control',tr(str(e)))

    def toggle_autostart(self,checked):self.task(lambda:manager.control('enable' if checked else 'disable'),lambda _:(self.message.setText(tr('Inicio automático ')+(tr('activado') if checked else tr('desactivado'))),self.refresh()))

    def refresh(self):
        if self.refreshing or self.busy:return
        self.refreshing=True;generation=self.control_generation
        def work():
            data=dict(health=manager.health(),status=core.active(),auto=core.autostart(),activity=core.live_activity(),devices_available=False)
            try:
                addresses=core.platform_os.addresses()
                own_ips={a['local'] for i in addresses for a in i.get('addr_info',[]) if a['family']=='inet'}
                data['devices']=[t for t in core.api('renderers/').get('renderers',[]) if t.get('address','').lstrip('/') not in own_ips]
                data['devices_available']=True
            except Exception:data['devices']=[]
            return data
        def done(d):
            if generation!=self.control_generation:
                self.refreshing=False
                if not self.busy:self.refresh()
                return
            self.refreshing=False;self.update_server_buttons(d['health']);self.status.setText(tr('● UMS disponible') if d['status']=='active' else tr('○ UMS ')+{'inactive':tr('detenido'),'failed':tr('con error'),'activating':tr('iniciando')}.get(d['status'],d['status']))
            self.auto.setChecked(d['auto'])
            self.activity_data=d;self.render_activity(d)
        self.task(work,done,busy=False,quiet=True)

    def render_activity(self,d):
        lines=[]
        for t in d['devices']:
            state=t.get('state',{});playing=t.get('playing','').strip();lines.append(f"{core.device_display_name(t,self.state['tvs']) or tr('Dispositivo')} · {t.get('address','')} · "+(tr('activo') if t.get('isActive') else tr('sin actividad'))+(tr('\n  Reproduciendo: ')+playing+tr(' · búfer: ')+str(state.get('buffer',0)) if playing else ''))
        for a in d['activity']: lines.append(tr('Conversión activa · ')+a['video']+' + '+a['audio']+' · '+a['input'])
        if lines:self.now.setText('\n'.join(lines))
        elif d.get('status')!='active':self.now.setText(tr('Inicia el servidor para consultar los dispositivos.'))
        elif not d.get('devices_available',True):self.now.setText(tr('No se ha podido consultar los dispositivos. Se volverá a intentar automáticamente.'))
        else:self.now.setText(tr('No se han detectado dispositivos.'))

    def scan(self):self.task(lambda:core.api('actions/',{'operation':'Server.ScanAllSharedFolders'}),lambda _:self.message.setText(tr('Actualización del catálogo solicitada a UMS')))

    def closeEvent(self,event:QCloseEvent):
        if self.busy:QMessageBox.information(self,tr('Operación en curso'),tr('Espera a que termine la operación.'));event.ignore();return
        if self.dirty:
            answer=QMessageBox.question(self,tr('Cambios sin aplicar'),tr('Hay cambios pendientes. ¿Cerrar sin aplicarlos?'),QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Cancel)
            if answer!=QMessageBox.StandardButton.Discard:event.ignore();return
        event.accept()

def configure_qt_language(app,language):
    from PyQt6.QtCore import QTranslator
    previous=getattr(app,'ums_translator',None)
    if previous:app.removeTranslator(previous)
    translator=QTranslator(app);code='zh_CN' if language=='zh' else language
    base=(RESOURCE_ROOT/'qt-translations')
    if not translator.load(str(base/('qtbase_'+code+'.qm'))):translator.load('/usr/share/qt6/translations/qtbase_'+code+'.qm')
    app.ums_translator=translator;app.installTranslator(translator)

def configure_theme(app,theme=None):
    appearance.apply(app,STYLE,theme or appearance.load()['theme'])

def main():
    if core.platform_os.WINDOWS:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('N3ruk.UMSControl')
    app=QApplication(sys.argv);app.setApplicationName('UMS Control');app.setOrganizationName('N3ruk');app.setDesktopFileName('ums-control')
    app.setWindowIcon(QIcon(str(RESOURCE_ROOT/'assets/ums-control.png')))
    try:preferences=load_with_recovery(appearance.load,lambda:dict(theme='current',language='es'))
    except StartupCancelled:return 1
    if not (core.CONFIG/'ui.json').exists():appearance.save(preferences['theme'],preferences['language'])
    configure_theme(app,preferences['theme'])
    lock=QLockFile(str(Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.TempLocation if core.platform_os.WINDOWS else QStandardPaths.StandardLocation.RuntimeLocation))/'baul-media-control.lock'));lock.setStaleLockTime(0)
    set_language(preferences['language']);configure_qt_language(app,preferences['language'])
    if not lock.tryLock(100):QMessageBox.information(None,'UMS Control',tr('UMS Control ya está abierto.'));return 0
    try:w=Window(preferences=preferences)
    except StartupCancelled:return 1
    w.show()
    if '--smoke-gui' in sys.argv:
        def finish_smoke():
            if '--report' in sys.argv:
                Path(sys.argv[sys.argv.index('--report')+1]).write_text(json.dumps(dict(passed=True,language=w.preferences['language'],platform=sys.platform,visible=w.isVisible())),encoding='utf-8')
            w.dirty=False;w.close();app.quit()
        QTimer.singleShot(1500,finish_smoke)
    exit_code=app.exec()
    # Keep the application, window and worker signals alive until QRunnables
    # finish; native Windows otherwise aborts during signal-owner teardown.
    QThreadPool.globalInstance().waitForDone()
    return exit_code

if __name__=='__main__':sys.exit(main())
