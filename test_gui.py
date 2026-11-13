"""Offscreen interaction regression; never changes production configuration."""
import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
import baul_gui as g
import baul_core as c
REAL_REFRESH=g.Window.refresh
class GuiTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  s=c.defaults();s['tvs']=[c.default_tv('Sala','192.168.1.20'),c.default_tv('Otra','192.168.1.21')];s['tvs'][1]['mode']='direct'
  self.patches=[patch.object(g.Window,'refresh'),patch.object(g.Window,'check_updates'),patch.object(g.appearance,'load',return_value={'theme':'current','language':'es'}),patch.object(g.appearance,'save'),patch.object(c,'load_state',side_effect=lambda:copy.deepcopy(s))]
  for p in self.patches:p.start()
  self.w=g.Window();self.w.show();self.app.processEvents()
 def tearDown(self):
  self.w.dirty=False;self.w.close()
  for p in self.patches:p.stop()
 def test_refresh_uses_portable_addresses_and_keeps_remote_devices(self):
  health=dict(present=True,kind='healthy',repairable=True,status='active')
  own=dict(ifname='Ethernet',addr_info=[dict(family='inet',local='192.168.50.10')])
  remote=dict(address='/192.168.50.20',name='Living room')
  with patch.object(g.manager,'health',return_value=health),patch.object(c,'active',return_value='active'),patch.object(c,'autostart',return_value=False),patch.object(c,'live_activity',return_value=[]),patch.object(c.platform_os,'addresses',return_value=[own]),patch.object(c,'api',return_value=dict(renderers=[dict(address='/192.168.50.10'),remote])),patch.object(c,'run') as run,patch.object(self.w,'task',side_effect=lambda work,done,**kw:done(work())):
   REAL_REFRESH(self.w);self.assertEqual(self.w.activity_data['devices'],[remote]);self.assertTrue(self.w.activity_data['devices_available']);run.assert_not_called()
 def test_summary_has_no_unnecessary_scrollbar(self):
  self.w.resize(1140,840);self.app.processEvents();scroll=self.w.tabs.widget(0)
  self.assertEqual(scroll.verticalScrollBar().maximum(),0)
  self.w.resize(860,620);self.app.processEvents()
  self.assertEqual(scroll.horizontalScrollBar().maximum(),0)
  self.assertGreater(scroll.verticalScrollBar().maximum(),0) # Accessibility on small screens.
 def test_resolution_recommendations_keep_manual_profile_bitrates(self):
  self.w.state['tvs'][1]['bitrate']=37
  for resolution,bitrate in g.RECOMMENDED_BITRATES.items():
   field=self.w.fields['resolution'];field.setCurrentIndex(field.findData(resolution));self.assertEqual(self.w.fields['bitrate'].currentData(),bitrate)
   rate=self.w.fields['bitrate'];rate.setCurrentIndex(rate.findData(30))
   self.w.tvlist.setCurrentRow(1);self.assertEqual(rate.currentData(),37)
   self.w.tvlist.setCurrentRow(0);self.assertEqual(rate.currentData(),30)
 def test_recovery_cancel_keeps_damaged_file_and_server(self):
  from configuration import ConfigurationError,StartupCancelled
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'settings.json';path.write_bytes(b'{broken')
   with patch.object(g.QMessageBox,'exec'),patch.object(g.QMessageBox,'clickedButton',return_value=None),patch.object(c,'apply') as apply,patch.object(c,'service') as service:
    with self.assertRaises(StartupCancelled):g.load_with_recovery(lambda:(_ for _ in ()).throw(ConfigurationError(path,'invalid')),c.defaults)
    self.assertEqual(path.read_bytes(),b'{broken');apply.assert_not_called();service.assert_not_called()
 def test_profiles_independent(self):
  self.w.fields['name'].setText('Sala nueva');self.w.tvlist.setCurrentRow(1)
  self.assertEqual(self.w.state['tvs'][0]['name'],'Sala nueva');self.assertEqual(self.w.fields['name'].text(),'Otra')
  self.assertFalse(self.w.advanced.isEnabled());self.w.tvlist.setCurrentRow(0);self.assertTrue(self.w.advanced.isEnabled())
 def test_folder_remove_does_not_touch_disk(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp)/'original.mkv';p.write_bytes(b'unchanged');self.w.folders.clear();self.w.folders.addItem(temp);self.w.folders.setCurrentRow(0);self.w.remove_folders()
   self.assertEqual(self.w.folders.count(),0);self.assertEqual(p.read_bytes(),b'unchanged')
 def test_remove_correct_profile(self):
  self.w.tvlist.setCurrentRow(1);self.w.remove_tv();self.assertEqual(len(self.w.state['tvs']),1);self.assertEqual(self.w.fields['name'].text(),'Sala')
 def test_force_mode_enables_options(self):
  self.w.tvlist.setCurrentRow(1);self.w.fields['mode'].setCurrentIndex(self.w.fields['mode'].findData('force'));self.assertTrue(self.w.advanced.isEnabled());self.assertEqual(self.w.snapshot()['tvs'][1]['mode'],'force')
 def test_invalid_address_never_apply(self):
  self.w.fields['ip'].setText('8.8.8.8')
  with patch.object(g.QMessageBox,'warning') as warning,patch.object(c,'apply') as apply:
   self.w.apply();warning.assert_called_once();apply.assert_not_called()
 def test_brand_and_no_diagnostic(self):
  self.assertEqual(self.w.windowTitle(),'UMS Control');self.assertEqual([self.w.tabs.tabText(i) for i in range(self.w.tabs.count())],['Resumen','Dispositivos'])
 def test_quality_values_preserved_catalog_bound(self):
  t=self.w.snapshot()['tvs'][0];self.assertFalse(t['resume']);self.assertTrue(t['external_subtitles']);self.assertEqual(t['audio_bitrate'],448)
  self.assertTrue(t['show_transcode_folder']);self.assertNotIn('preset',self.w.fields)
 def test_catalog_follows_conversion_mode_not_subtitles(self):
  w=self.w.fields;self.assertNotIn('show_transcode_folder',w);self.assertNotIn('resume',w)
  w['subtitles'].setCurrentIndex(w['subtitles'].findData('passthrough'))
  self.assertTrue(self.w.snapshot()['tvs'][0]['show_transcode_folder'])
  w['subtitles'].setCurrentIndex(w['subtitles'].findData('burn'));self.assertTrue(self.w.snapshot()['tvs'][0]['show_transcode_folder'])
 def test_subtitle_controls_follow_mode(self):
  w=self.w.fields;w['subtitles'].setCurrentIndex(w['subtitles'].findData('passthrough'));self.assertFalse(w['external_subtitles'].isEnabled());self.assertIn('MKV',self.w.subtitle_help.text())
  w['subtitles'].setCurrentIndex(w['subtitles'].findData('burn'));self.assertTrue(w['external_subtitles'].isEnabled())
  w['mode'].setCurrentIndex(w['mode'].findData('direct'));self.assertFalse(w['subtitles'].isEnabled());self.assertIn('intacto',self.w.mode_help.text());self.assertNotIn('subtitle_languages',self.w.language_choices)
  self.assertFalse(self.w.subtitle_group.isEnabled());self.assertTrue(self.w.subtitle_group.isHidden());self.assertTrue(self.w.conversion_group.isHidden());self.assertFalse(self.w.detail_tabs.isTabEnabled(2));self.assertFalse(self.w.quality_page.isEnabled())
  w['mode'].setCurrentIndex(w['mode'].findData('force'));self.assertTrue(self.w.detail_tabs.isTabEnabled(2));self.assertTrue(self.w.subtitle_group.isEnabled());self.assertFalse(self.w.subtitle_group.isHidden());self.assertFalse(self.w.conversion_group.isHidden())
 def test_only_explicit_modes_and_two_subtitle_options(self):
  self.assertFalse(hasattr(self.w,'quick'))
  self.assertEqual([self.w.fields['mode'].itemData(i) for i in range(self.w.fields['mode'].count())],['direct','force','auto'])
  self.assertEqual([self.w.fields['subtitles'].itemData(i) for i in range(self.w.fields['subtitles'].count())],['passthrough','burn'])
 def test_subtitle_selection_has_no_preference_or_duplicate_label(self):
  self.assertNotIn('subtitle_languages',self.w.fields);self.assertNotIn('subtitle_languages',self.w.language_choices)
  self.assertEqual(self.w.fields['external_subtitles'].text(),'Buscar subtítulos junto al vídeo')
  self.assertIsNone(self.w.fields['external_subtitles'].parentWidget().layout().labelForField(self.w.fields['external_subtitles']))
  self.assertIn('Pelicula.spa.srt',self.w.external_subtitle_help.text())
  self.assertIn('Transcodificar',self.w.subtitle_help.text())
 def test_hidden_subtitle_preference_preserved_on_edit(self):
  self.w.state['tvs'][0]['subtitle_languages']='fra,deu,eng'
  self.w.fields['bitrate'].setCurrentIndex(self.w.fields['bitrate'].findData(30));self.assertEqual(self.w.snapshot()['tvs'][0]['subtitle_languages'],'fra,deu,eng')
 def test_quality_explains_scope(self):
  self.assertIn('carpetas seleccionadas',self.w.direct_notice.text());self.assertIn('automático',self.w.direct_notice.text())
 def test_quality_survives_original_roundtrip(self):
  w=self.w.fields;w['bitrate'].setCurrentIndex(w['bitrate'].findData(40));w['mode'].setCurrentIndex(w['mode'].findData('direct'));w['mode'].setCurrentIndex(w['mode'].findData('force'));self.assertEqual(w['bitrate'].currentData(),40)
 def test_audio_preference_removed_but_saved_priority_preserved(self):
  self.assertNotIn('audio_languages',self.w.fields)
  self.w.state['tvs'][0]['audio_languages']='jpn,fra,eng'
  self.w.fields['bitrate'].setCurrentIndex(self.w.fields['bitrate'].findData(40))
  self.assertEqual(self.w.snapshot()['tvs'][0]['audio_languages'],'jpn,fra,eng')
  self.assertEqual(self.w.snapshot()['tvs'][1]['audio_languages'],'spa,esp,eng,und')
 def test_automatic_audio_explained_without_preference(self):
  self.assertIn('automática',self.w.audio_selection_help.text())
  self.assertNotIn('audio_languages',self.w.fields)
 def test_copy_preserves_destination_identity(self):
  self.w.tvlist.setCurrentRow(1);identity={k:self.w.state['tvs'][1][k] for k in ['id','name','ip','udn']}
  with patch.object(g.QDialog,'exec',return_value=g.QDialog.DialogCode.Accepted),patch.object(c,'apply') as apply:self.w.copy_tv_settings();apply.assert_not_called()
  t=self.w.snapshot()['tvs'][1];self.assertEqual(t['mode'],'force')
  for key,value in identity.items():self.assertEqual(t[key],value)
 def test_discard_reloads_without_server_changes(self):
  self.w.fields['bitrate'].setCurrentIndex(self.w.fields['bitrate'].findData(8))
  with patch.object(g.QMessageBox,'question',return_value=g.QMessageBox.StandardButton.Discard),patch.object(c,'apply') as apply,patch.object(c,'service') as svc:self.w.discard_changes();apply.assert_not_called();svc.assert_not_called()
  self.assertEqual(self.w.fields['bitrate'].currentData(),25);self.assertFalse(self.w.dirty);self.assertFalse(self.w.save.isEnabled())
 def test_unlimited_catalog_roundtrip_and_profile_isolation(self):
  b=self.w.fields['bitrate'];self.assertFalse(b.isEditable());self.assertEqual(b.itemText(b.findData(0)),'Sin límite')
  b.setCurrentIndex(b.findData(0));self.assertEqual(self.w.snapshot()['tvs'][0]['bitrate'],0)
  self.w.tvlist.setCurrentRow(1);self.assertEqual(b.currentData(),25)
  self.w.tvlist.setCurrentRow(0);self.assertEqual(b.currentData(),0)
  w=self.w.fields;w['mode'].setCurrentIndex(w['mode'].findData('direct'));w['mode'].setCurrentIndex(w['mode'].findData('force'));self.assertEqual(b.currentData(),0)
 def test_saved_non_catalog_bitrate_is_not_silently_changed(self):
  self.w.state['tvs'][1]['bitrate']=37;self.w.tvlist.setCurrentRow(1)
  self.assertEqual(self.w.fields['bitrate'].currentData(),37);self.assertEqual(self.w.snapshot()['tvs'][1]['bitrate'],37)
 def test_empty_list_then_add(self):
  self.w.remove_tv();self.w.remove_tv();self.assertFalse(self.w.editor.isEnabled());self.assertEqual(self.w.row,-1);self.w.add_tv();self.assertEqual(self.w.row,0);self.assertTrue(self.w.editor.isEnabled())
 def test_force_and_mpeg_disable_irrelevant_controls(self):
  w=self.w.fields;w['mode'].setCurrentIndex(w['mode'].findData('force'));self.assertNotIn('preset',w);w['target'].setCurrentIndex(w['target'].findData('MPEGPS-MPEG2-AC3'));self.assertFalse(w['encoder'].isEnabled());self.assertIn('CPU',self.w.encoding_help.text())
 def test_auto_ignores_manual_folder_checks_and_preserves_them(self):
  self.w.render_folders(['/media/a','/media/b'],['/media/a']);w=self.w.fields
  w['mode'].setCurrentIndex(w['mode'].findData('auto'))
  self.assertFalse(self.w.conversion_group.isEnabled());self.assertTrue(self.w.advanced.isEnabled())
  self.assertEqual(self.w.snapshot()['tvs'][0]['convert_folders'],['/media/a'])
  w['mode'].setCurrentIndex(w['mode'].findData('force'));self.assertTrue(self.w.conversion_group.isEnabled())
 def test_container_independent_per_device(self):
  w=self.w.fields;w['container'].setCurrentIndex(w['container'].findData('mp4'))
  self.w.tvlist.setCurrentRow(1);self.assertEqual(w['container'].currentData(),'auto')
  self.w.tvlist.setCurrentRow(0);self.assertEqual(w['container'].currentData(),'mp4')
  w['target'].setCurrentIndex(w['target'].findData('MPEGPS-MPEG2-AC3'))
  with patch.object(g.QMessageBox,'warning') as warning,patch.object(c,'apply') as apply:
   self.w.apply();warning.assert_called_once();apply.assert_not_called()
if __name__=='__main__':unittest.main()
