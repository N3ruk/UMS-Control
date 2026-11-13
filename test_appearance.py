"""Themes, complete translations, language switching and permission boundaries."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication,QDialog,QLabel,QMessageBox,QScrollArea
import baul_gui as g
import baul_core as c
import localization as loc
REAL_LOAD=g.appearance.load
REAL_SAVE=g.appearance.save
REAL_CHECK_UPDATES=g.Window.check_updates

class AppearanceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  state=c.defaults();state['tvs']=[c.default_tv('Tema / Sin límite','192.168.1.20')]
  self.patches=[patch.object(g.Window,'refresh'),patch.object(g.Window,'check_updates'),patch.object(c,'load_state',side_effect=lambda:copy.deepcopy(state)),patch.object(g.appearance,'load',return_value={'theme':'current','language':'es'}),patch.object(g.appearance,'save')]
  for p in self.patches:p.start()
  self.w=g.Window();self.w.show();self.app.processEvents()
 def tearDown(self):
  self.w.dirty=False;self.w.close();loc.set_language('es')
  for p in reversed(self.patches):p.stop()
 def test_seven_complete_catalogs(self):
  for source,values in loc.CATALOG.items():
   self.assertEqual(set(values),{'en','fr','de','it','zh','ja'})
   for text in values.values():self.assertTrue(text);self.assertEqual(source.count('{value}'),text.count('{value}'))
 def test_live_language_switch_keeps_unsaved_values_and_identifiers(self):
  self.w.fields['bitrate'].setCurrentIndex(self.w.fields['bitrate'].findData(0));before=self.w.snapshot()
  for language in ['en','fr','de','it','zh','ja','es']:
   self.w.set_ui_language(language);self.app.processEvents()
   self.assertEqual(self.w.snapshot(),before,language);self.assertTrue(self.w.dirty)
   self.assertEqual(self.w.fields['name'].text(),'Tema / Sin límite')
   self.assertEqual(self.w.tabs.tabText(0),loc.tr('Resumen'))
   source='Iniciar el servidor al entrar en mi sesión de Ubuntu';expected=loc.platform_text(source if language=='es' else loc.CATALOG[source][language]);self.assertEqual(self.w.auto.text(),expected,language)
   self.assertEqual(self.w.menuBar().actions()[0].text(),loc.tr('Tema'))
   self.assertEqual(self.w.fields['bitrate'].itemText(self.w.fields['bitrate'].findData(0)),loc.tr('Sin límite'))
 def test_all_five_themes_apply_without_server_changes(self):
  with patch.object(c,'service') as service,patch.object(c,'apply') as apply:
   for theme,colors in g.appearance.COLORS.items():
    self.w.set_theme(theme);self.assertEqual(self.app.palette().window().color().name(),colors[0]);self.assertTrue(self.w.theme_actions[theme].isChecked())
   service.assert_not_called();apply.assert_not_called()
 def test_format_explanations_follow_choice(self):
  for value,expected in [('MPEGTS-H264-AC3','Dolby'),('MPEGTS-H264-AAC','AAC'),('MPEGPS-MPEG2-AC3','ancho de banda')]:
   self.w.fields['target'].setCurrentIndex(self.w.fields['target'].findData(value));self.assertIn(expected,self.w.format_help.text())
 def test_dynamic_server_buttons(self):
  for kind,present,title in [('absent',False,'Instalar servidor UMS'),('healthy',True,'Salud del servidor'),('damaged',True,'Salud del servidor')]:
   self.w.update_server_buttons(dict(kind=kind,present=present,repairable=True,status='inactive'))
   self.assertEqual(self.w.health_button.text(),title);self.assertEqual(self.w.uninstall_button.isEnabled(),present)
   self.assertEqual(self.w.server_controls[0].isEnabled(),present)
 def test_install_and_uninstall_cancel_never_mutate_server(self):
  with patch.object(g.QMessageBox,'question',return_value=QMessageBox.StandardButton.Cancel),patch.object(g.manager,'install') as install,patch.object(g.manager,'uninstall') as uninstall:
   self.w.confirm_server_install(dict(repairable=True,foreign=[]));self.w.uninstall_server();install.assert_not_called();uninstall.assert_not_called()
 def test_confirmed_operations_use_background_job(self):
  with patch.object(g.QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes),patch.object(self.w,'task') as task:
   self.w.uninstall_server();self.assertEqual(task.call_args.args[0],g.manager.uninstall)
 def test_about_has_author_version_license_and_independence(self):
  def inspect(dialog):
   texts=' '.join(x.text() for x in dialog.findChildren(QLabel))
   for term in ['N3ruk','1.0','GPL-3.0-or-later','independiente','No desarrollamos','https://github.com/N3ruk']:self.assertIn(term,texts)
   return QDialog.DialogCode.Rejected
  with patch.object(QDialog,'exec',inspect):self.w.about()
 def test_preferences_are_separate_from_server_profiles(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(c,'CONFIG',Path(tmp)):
   # Use real helpers, not the test's save stub.
   import importlib
   load=REAL_LOAD
   REAL_SAVE('ugm','ja')
   self.assertEqual(load(),dict(theme='ugm',language='ja'));self.assertFalse((Path(tmp)/'settings.json').exists())
 def test_update_only_for_newer_version_and_below_web(self):
  self.w.update_server_buttons(dict(kind='healthy',present=True,repairable=True,status='inactive'))
  with patch.object(g.releases,'jar_version',return_value='15.9.0'):
   self.w.latest_release=None;self.w.update_update_button();self.assertTrue(self.w.update_button.isHidden())
   self.w.latest_release=dict(version='15.10.0');self.w.update_update_button();self.app.processEvents();self.assertFalse(self.w.update_button.isHidden())
   self.assertEqual(self.w.web_button.objectName(),self.w.update_button.objectName())
   self.assertGreaterEqual(self.w.update_button.y(),self.w.web_button.y()+self.w.web_button.height())
   self.w.latest_release=dict(version='15.9.0');self.w.update_update_button();self.assertTrue(self.w.update_button.isHidden())
 def test_update_requires_click_and_confirmation(self):
  self.w.latest_release=dict(version='15.10.0')
  with patch.object(g.QMessageBox,'question',return_value=QMessageBox.StandardButton.Cancel),patch.object(g.manager,'update') as update,patch.object(self.w,'task') as task:
   self.w.update_server();update.assert_not_called();task.assert_not_called()
  with patch.object(g.QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes),patch.object(g.manager,'update') as update,patch.object(self.w,'task') as task:
   self.w.update_server();update.assert_not_called();task.call_args.args[0]();update.assert_called_once_with(self.w.latest_release)
 def test_startup_check_background_result_and_no_automatic_install(self):
  import time
  with patch.object(g.releases,'check_update',return_value=dict(available=True,release=dict(version='15.10.0'),error=None)),patch.object(g.releases,'jar_version',return_value='15.9.0'),patch.object(g.manager,'update') as update,patch.object(g.manager,'install') as install:
   self.w.update_server_buttons(dict(kind='healthy',present=True,repairable=True,status='inactive'));REAL_CHECK_UPDATES(self.w)
   deadline=time.monotonic()+2
   while self.w.jobs and time.monotonic()<deadline:self.app.processEvents()
   self.assertFalse(self.w.update_button.isHidden());self.assertFalse(self.w.busy);update.assert_not_called();install.assert_not_called()
 def test_ugm_wallpaper_orange_cyan_and_anime_asset(self):
  self.assertEqual(g.appearance.THEMES['current'],'Azul');self.w.set_theme('ugm');self.assertIn('#ad421a',self.app.styleSheet());self.assertIn('#ffad80',self.app.styleSheet())
  self.assertEqual(self.w.centralWidget().image_theme,'ugm');self.assertFalse(self.w.centralWidget().image.isNull());self.assertIn('#64ddff',self.app.styleSheet())
  self.w.set_theme('anime');self.assertEqual(self.w.centralWidget().image_theme,'anime');self.assertFalse(self.w.centralWidget().image.isNull());self.assertEqual(g.appearance.COLORS['anime'][0],'#1b2532')
 def test_overview_scrollable_in_compact_window(self):self.assertIsInstance(self.w.tabs.widget(0),QScrollArea)

if __name__=='__main__':unittest.main()
