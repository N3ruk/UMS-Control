"""Per-device folder isolation, migration and UI state regressions."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import baul_core as c

class FolderModelTests(unittest.TestCase):
 def test_migration_preserves_modes_and_does_not_write(self):
  a=c.default_tv('PS3','192.168.1.10');b=c.default_tv('TV','192.168.1.11');b['mode']='direct'
  old=dict(version=1,name='Media',interface='lo',server_uuid='existing',folders=['/media/series'],tvs=[a,b]);before=copy.deepcopy(old)
  new=c.migrate_state(old)
  self.assertEqual(old,before);self.assertEqual(new['version'],2);self.assertNotIn('folders',new)
  self.assertEqual(new['tvs'][0]['convert_folders'],['/media/series']);self.assertEqual(new['tvs'][1]['convert_folders'],[])
  self.assertEqual(new['tvs'][0]['folders'],new['tvs'][1]['folders']);self.assertEqual(c.migrate_state(new),new)
  new['tvs'][0]['folders'].clear();self.assertEqual(new['tvs'][1]['folders'],['/media/series'])
 def test_read_migration_leaves_file_untouched(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(c,'CONFIG',Path(tmp)):
   p=Path(tmp)/'settings.json';p.write_text(json.dumps(dict(version=1,name='Media',interface='lo',folders=['/one'],tvs=[c.default_tv('Client','192.168.1.20')])), encoding='utf-8');before=p.read_bytes()
   self.assertEqual(c.load_state()['version'],2);self.assertEqual(before,p.read_bytes())
 def test_union_deduplicates_without_device_rule_merge(self):
  a=c.default_tv();b=c.default_tv();a.update(folders=['/one','/both'],convert_folders=['/both']);b.update(folders=['/both','/two'],convert_folders=[])
  state=c.defaults();state['tvs']=[a,b]
  self.assertEqual(c.shared_folders(state),['/one','/both','/two']);self.assertIn('["/both"]',c.device_config(a));self.assertIn('ums_control_convert_folders = []',c.device_config(b))
 def test_parent_child_and_symlink_overlap_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   a=Path(tmp)/'a';a.mkdir();link=Path(tmp)/'alias';link.symlink_to(a)
   for paths in [[str(a),str(a/'child')],[str(a/'child'),str(a)],[str(a),str(link)]]:self.assertRaises(ValueError,c.validate_folders,paths)
 def test_conversion_must_be_shared_with_same_device(self):
  state=c.defaults();state['interface']='lo';tv=c.default_tv('TV','192.168.1.21');tv.update(folders=['/one'],convert_folders=['/two']);state['tvs']=[tv]
  with patch.object(c,'service') as service:self.assertRaises(ValueError,c.apply,state);service.assert_not_called()
 def test_direct_keeps_saved_selection_but_sends_empty_conversion_rule(self):
  tv=c.default_tv();tv.update(folders=['/one'],convert_folders=['/one'],mode='direct')
  self.assertIn('ums_control_convert_folders = []',c.device_config(tv));self.assertEqual(tv['convert_folders'],['/one'])
 def test_apply_preserves_unavailable_folder_when_ums_omits_it(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(c,'CONFIG',Path(tmp)/'panel'),patch.object(c,'PROFILE',Path(tmp)/'ums'):
   state=c.defaults();state.update(interface='lo',tvs=[c.default_tv('Client','192.168.1.20')]);missing=str(Path(tmp)/'unplugged')
   state['tvs'][0].update(folders=[missing],convert_folders=[missing])
   with patch.object(c,'active',return_value='active'),patch.object(c,'service'),patch.object(c,'ready'),patch.object(c,'api',return_value={'shared_content':[]}):c.apply(state)
   self.assertEqual(c.load_state()['tvs'][0]['folders'],[missing]);self.assertEqual(json.loads((c.PROFILE/'SHARED.conf').read_text(encoding='utf-8'))[0]['file'],missing)

 def test_new_device_does_not_inherit_shares(self):
  tv=c.default_tv();self.assertEqual(tv['folders'],[]);self.assertEqual(tv['convert_folders'],[])

import test_gui
from PyQt6.QtCore import Qt
class FolderUiTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):test_gui.GuiTests.setUpClass.__func__(cls)
 def setUp(self):test_gui.GuiTests.setUp(self)
 def tearDown(self):test_gui.GuiTests.tearDown(self)
 def test_device_switch_and_mode_roundtrip_preserve_selections(self):
  self.w.render_folders(['/one','/two'],['/one']);self.w.mark();self.w.tvlist.setCurrentRow(1)
  self.assertEqual(self.w.folders.count(),0);self.w.render_folders(['/two'],[]);self.w.tvlist.setCurrentRow(0)
  self.assertEqual(self.w.conversion_folders.topLevelItem(0).checkState(0),Qt.CheckState.Checked)
  self.w.fields['mode'].setCurrentIndex(0);self.assertFalse(self.w.conversion_group.isEnabled());self.w.fields['mode'].setCurrentIndex(1)
  self.assertEqual(self.w.snapshot()['tvs'][0]['convert_folders'],['/one']);self.assertEqual(self.w.snapshot()['tvs'][1]['folders'],['/two'])
 def test_added_folder_defaults_original_remove_prunes_only_selected_device(self):
  import baul_gui as g
  self.w.render_folders(['/one'],['/one']);self.w.commit_tv()
  with patch.object(g.QFileDialog,'getExistingDirectory',return_value='/two'):self.w.add_folder()
  self.assertEqual(self.w.snapshot()['tvs'][0]['convert_folders'],['/one'])
  self.w.folders.setCurrentRow(0);self.w.remove_folders();self.assertEqual(self.w.snapshot()['tvs'][0]['convert_folders'],[]);self.assertEqual(self.w.snapshot()['tvs'][0]['folders'],['/two'])
 def test_copy_does_not_copy_folder_rules(self):
  import baul_gui as g
  self.w.render_folders(['/source'],['/source']);self.w.tvlist.setCurrentRow(1);self.w.render_folders(['/destination'],[])
  with patch.object(g.QDialog,'exec',return_value=g.QDialog.DialogCode.Accepted):self.w.copy_tv_settings()
  self.assertEqual(self.w.snapshot()['tvs'][1]['folders'],['/destination']);self.assertEqual(self.w.snapshot()['tvs'][1]['convert_folders'],[])
 def test_translation_preserves_user_paths_and_checked_state(self):
  self.w.render_folders(['/media/Carpetas compartidas','/media/Dispositivos'],['/media/Dispositivos']);before=self.w.snapshot()
  for language in ['en','fr','de','it','zh','ja','es']:
   self.w.set_ui_language(language);self.assertEqual(self.w.snapshot(),before)
  self.assertEqual(self.w.tabs.tabText(1),'Dispositivos')
 def test_final_tab_structure(self):
  self.assertEqual([self.w.detail_tabs.tabText(i) for i in range(4)],['Carpetas compartidas','Reproducción','Calidad y audio','Identificación'])
