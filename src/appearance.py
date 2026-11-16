# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 N3ruk
"""Independent appearance preferences; never apply server settings."""
import json
import sys
from first_run import initial_language
import baul_core as c
from PyQt6.QtGui import QPalette,QColor
from PyQt6.QtCore import QObject,QEvent
from PyQt6.QtWidgets import QWidget
LANGUAGES={'es':'Español','en':'English','fr':'Français','de':'Deutsch','it':'Italiano','zh':'中文','ja':'日本語'}
THEMES={'current':'Azul','ugm':'UGM','classic':'Windows clásico','contrast':'Alto contraste','green':'Verde/amarillo','anime':'Anime'}
WALLPAPER_THEMES={'current','green','ugm','anime'}
class LinuxWindowChrome(QObject):
 """Keep native decoration black without changing any content theme."""
 def eventFilter(self,window,event):
  if event.type()==QEvent.Type.Show and isinstance(window,QWidget) and window.isWindow():
   self.apply_window(window)
  return False

 def apply_window(self,window):
  window.setPalette(self.content_palette)
  if self.parent().platformName()!='xcb':return
  # Ask the X11 window manager for its dark native decoration. Wayland's Qt
  # decoration reads the application palette instead of this local palette.
  try:
   import ctypes,ctypes.util
   x11=ctypes.CDLL(ctypes.util.find_library('X11') or 'libX11.so.6')
   x11.XOpenDisplay.argtypes=[ctypes.c_char_p];x11.XOpenDisplay.restype=ctypes.c_void_p
   x11.XInternAtom.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_int];x11.XInternAtom.restype=ctypes.c_ulong
   x11.XChangeProperty.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_int,ctypes.c_int,ctypes.c_char_p,ctypes.c_int]
   x11.XCloseDisplay.argtypes=[ctypes.c_void_p]
   display=x11.XOpenDisplay(None)
   if display:
    try:x11.XChangeProperty(display,int(window.winId()),x11.XInternAtom(display,b'_GTK_THEME_VARIANT',0),x11.XInternAtom(display,b'UTF8_STRING',0),8,0,b'dark',4)
    finally:x11.XCloseDisplay(display)
  except (OSError,AttributeError):pass

# background, surface, text, muted, input, border, accent, button, highlight, heading
COLORS={
 'current':('#101521','#171e2d','#e9ecf5','#a8b5c9','#101725','#39465d','#82d5ff','#2b3b55','#35547d','#a9dcff'),
 'ugm':('#100d20','#1c1630','#f6f1ff','#d0c4e3','#161124','#6d5790','#64ddff','#342347','#59376e','#b3ecff'),
 'anime':('#1b2532','#242e3f','#f6eee3','#d7c2b1','#171c26','#60738f','#f4b967','#3b485f','#805342','#f7c684'),
 'classic':('#c0c0c0','#d4d0c8','#000000','#303030','#ffffff','#606060','#000080','#d4d0c8','#000080','#000080'),
 'contrast':('#000000','#000000','#ffffff','#ffffff','#000000','#ffffff','#ffff00','#000000','#ffff00','#ffff00'),
 'green':('#101b10','#182819','#f5ffd7','#c2d59b','#0c170d','#718845','#ffec65','#2c4c25','#436333','#ffe869')}

def load():
 data=c.read_object(c.CONFIG/'ui.json',lambda:{})
 for key in ['theme','language']:
  if key in data and not isinstance(data[key],str):raise c.ConfigurationError(c.CONFIG/'ui.json','Preferencia visual no válida: '+key)

 return {'theme':data.get('theme') if isinstance(data.get('theme'),str) and data['theme'] in THEMES else 'current','language':data.get('language') if isinstance(data.get('language'),str) and data['language'] in LANGUAGES else initial_language()}

def save(theme,language):
 if theme not in THEMES or language not in LANGUAGES:raise ValueError('Invalid appearance preference')
 c.atomic_write(c.CONFIG/'ui.json',json.dumps(dict(theme=theme,language=language),ensure_ascii=False,indent=2))

def apply(app,style,theme='current'):
 bg,surface,text,muted,base,border,accent,btn,highlight,heading=COLORS[theme]
 original=COLORS['current'];replacements={
 '#101521':bg,'#171e2d':surface,'#e9ecf5':text,'#a8b5c9':muted,'#101725':base,'#39465d':border,'#82d5ff':accent,'#2b3b55':btn,'#35547d':highlight,'#a9dcff':heading,
 '#192133':surface,'#304667':btn,'#303a50':border,'#172235':base,'#485b78':border,'#3a5275':highlight,'#202e43':surface,'#425c7b':border,'#e5f2ff':text,'#344157':border,'#a9c7ee':heading,'#f2f7ff':text,'#80d3ba':accent,'#293d59':surface,'#6085b2':border,'#2d476a':highlight,
 '#7d8797':muted,'#303744':border,'#758095':muted,'#171b24':surface,'#78859a':muted,'#222c3b':surface,'#303a49':border,'#2864a5':btn,'#4a97d9':accent}
 import re
 styled=re.sub(r'#[0-9a-fA-F]{6}',lambda m:replacements.get(m[0],m[0]),style)
 styled+='\nQMenuBar,QMenu {background:'+surface+';color:'+text+';} QMenu::item:selected,QMenuBar::item:selected {background:'+highlight+';color:'+('black' if theme=='contrast' else 'white')+';}\n'
 if theme in {'classic','contrast'}:styled+='QWidget {border-radius:0;} QComboBox QAbstractItemView::item:selected,QListWidget::item:selected {color:'+('black' if theme=='contrast' else 'white')+';} QToolTip {color:'+text+';}'
 app.setStyle('Fusion')
 palette=QPalette()
 for role,color in {'Window':bg,'WindowText':text,'Base':base,'AlternateBase':surface,'Text':text,'Button':btn,'ButtonText':text,'Highlight':highlight,'HighlightedText':'#000000' if theme=='contrast' else '#ffffff','ToolTipBase':surface,'ToolTipText':text,'Link':accent,'Light':border,'Mid':border,'Dark':border}.items():palette.setColor(getattr(QPalette.ColorRole,role),QColor(color))
 for role in ['Text','WindowText','ButtonText']:palette.setColor(QPalette.ColorGroup.Disabled,getattr(QPalette.ColorRole,role),QColor(muted))
 chrome=None
 if sys.platform.startswith('linux'):
  chrome=getattr(app,'ums_window_chrome',None)
  if chrome is None:
   chrome=LinuxWindowChrome(app);app.installEventFilter(chrome);app.ums_window_chrome=chrome
  chrome.content_palette=QPalette(palette)
 styled+='QScrollArea > QWidget, QWidget#scrollBody {background:'+surface+';} QScrollBar {background:'+surface+';} QScrollBar::handle {background:'+border+';min-height:20px;min-width:20px;} QCheckBox::indicator:unchecked {background:'+base+';border:1px solid '+border+';} QCheckBox::indicator:checked {background:'+highlight+';border:2px solid '+accent+';}'
 if theme in {'current','green'}:
  panel='16,21,33' if theme=='current' else '16,27,16'
  group='23,30,45' if theme=='current' else '24,40,25'
  styled+='QWidget#appBackdrop {background:transparent;} QTabWidget::pane {background:transparent;} QWidget#tabBody,QWidget#scrollBody {background:rgba('+panel+',165);} QScrollArea > QWidget {background:transparent;} QGroupBox {background:rgba('+group+',145);} QWidget#appBackdrop > QLabel#muted {background:rgba('+panel+',215);padding:4px 6px;border-radius:4px;}'
 if theme=='ugm':
  styled+='QWidget#appBackdrop {background:transparent;} QTabWidget::pane {background:transparent;} QWidget#tabBody,QWidget#scrollBody {background:rgba(16,13,32,165);} QScrollArea > QWidget {background:transparent;} QGroupBox {background:rgba(28,22,48,145);} QLabel#explanation {background:rgba(38,28,58,235);border-color:#6d5790;} QPushButton#primary {background:#ad421a;border-color:#ffad80;} QPushButton#primary:hover {background:#c44f22;} QTabBar::tab:selected {background:#49305f;color:#b3ecff;border-bottom:2px solid #64ddff;} QWidget#appBackdrop > QLabel#muted {background:rgba(16,13,32,215);padding:4px 6px;border-radius:4px;} QLabel#title {color:#fff6ff;} QLabel#status {color:#8fe7ff;}'
 styled+='QTextBrowser#guideText {background:'+base+';color:'+text+';border:1px solid '+border+';border-radius:7px;padding:18px;selection-background-color:'+highlight+';} QListWidget#guideCategories {background:'+base+';} QListWidget#guideCategories::item {padding:10px;} QListWidget#guideCategories::item:selected {background:'+highlight+';color:'+('#000000' if theme=='contrast' else '#ffffff')+';}'
 if theme=='anime':
  styled+='QWidget#appBackdrop {background:transparent;} QTabWidget::pane {background:transparent;border-color:#60738f;} QWidget#tabBody,QWidget#scrollBody {background:rgba(27,37,50,175);} QScrollArea > QWidget {background:transparent;} QGroupBox {background:rgba(27,37,50,165);} QLabel#explanation {background:rgba(59,72,95,215);} QPushButton#primary {background:#805342;border-color:#f4b967;} QPushButton#primary:hover {background:#a0643e;}'
 app.setStyleSheet(styled)
 if chrome:
  decoration=QPalette(palette);decoration.setColor(QPalette.ColorRole.Window,QColor('#000000'));decoration.setColor(QPalette.ColorRole.WindowText,QColor('#ffffff'));app.setPalette(decoration)
  for window in app.topLevelWidgets():chrome.apply_window(window)
 else:app.setPalette(palette)
 for window in app.topLevelWidgets():window.update()
