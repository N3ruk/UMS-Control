"""Naming is presentation-only; nested rules preserve independent client choices."""
import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import baul_core as c
import test_gui
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog

class NestedRuleTests(unittest.TestCase):
 def test_longest_rule_and_path_boundaries(self):
  include=['/library','/library/series/keep/convert'];exclude=['/library/series']
  for path,expected in [('/library/a',True),('/library/series/a',False),('/library/series/keep/convert/a',True),('/library2/a',False)]:
   self.assertEqual(c.rule_enabled(path,include,exclude),expected)
 def test_validation_rejects_escape_symlink_and_contradiction(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/'library';root.mkdir();outside=Path(tmp)/'outside';outside.mkdir();(root/'escape').symlink_to(outside)
   for inc,exc in [([str(root/'escape')],[]),([str(outside)],[]),([str(root)],[str(root)])]:
    with self.assertRaises(ValueError):c.validate_folder_rules([str(root)],inc,exc)
   c.validate_folder_rules([str(root)],[str(root),str(root/'missing/again')],[str(root/'missing')])
 def test_migration_disabled_by_default_and_no_disk_write(self):
  old=c.defaults();old['tvs']=[c.default_tv('Client','192.168.1.20')];before=copy.deepcopy(old)
  migrated=c.migrate_state(old);self.assertEqual(old,before)
  tv=migrated['tvs'][0];self.assertEqual(tv['name_mode'],'original');self.assertEqual(tv['name_folders'],[])
 def test_original_with_naming_never_enables_conversion(self):
  tv=c.default_tv('Client','192.168.1.20');tv.update(mode='direct',name_mode='selected',folders=['/media'],convert_folders=['/media'],convert_exclusions=['/media/plain'],name_folders=['/media/series'])
  before=copy.deepcopy(tv);conf=c.device_config(tv)
  for line in ['disable_transcoding = true','ums_control_convert_folders = []','ums_control_convert_exclusions = []','ums_control_name_mode = selected','MaxVideoBitrateMbps = 0']:self.assertIn(line,conf)
  self.assertEqual(tv,before)

class NameRuleUiTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):test_gui.GuiTests.setUpClass.__func__(cls)
 def setUp(self):test_gui.GuiTests.setUp(self)
 def tearDown(self):test_gui.GuiTests.tearDown(self)
 def test_nested_exception_unexpanded_roundtrip_and_parent_reset(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'series/plain/again').mkdir(parents=True);(root/'films').mkdir()
   self.w.render_folders([tmp],[tmp],[str(root/'series/plain')])
   tree=self.w.conversion_folders;top=tree.topLevelItem(0)
   self.assertEqual(top.checkState(0),Qt.CheckState.PartiallyChecked)
   self.assertEqual(self.w.snapshot()['tvs'][0]['convert_exclusions'],[str(root/'series/plain')])
   top.setExpanded(True);series=next(top.child(i) for i in range(top.childCount()) if top.child(i).text(0)=='series');series.setExpanded(True)
   plain=series.child(0);plain.setExpanded(True);plain.child(0).setCheckState(0,Qt.CheckState.Checked)
   snapshot=self.w.snapshot()['tvs'][0];self.assertIn(str(root/'series/plain/again'),snapshot['convert_folders'])
   self.w.tvlist.setCurrentRow(1);self.w.tvlist.setCurrentRow(0)
   self.assertEqual(self.w.snapshot()['tvs'][0]['convert_folders'],snapshot['convert_folders'])
   tree.topLevelItem(0).setCheckState(0,Qt.CheckState.Checked)
   self.assertEqual(tree.selection(),([tmp],[]))
 def test_naming_in_original_and_selections_independent(self):
  self.w.fields['mode'].setCurrentIndex(0);self.w.fields['name_mode'].setCurrentIndex(2)
  self.w.render_folders(['/shared'],['/shared'],[],['/shared/a'],['/shared/a/b'])
  self.assertFalse(self.w.detail_tabs.isTabEnabled(2));self.assertTrue(self.w.name_folders.isEnabled());self.assertFalse(self.w.subtitle_group.isEnabled())
  before=self.w.snapshot();self.w.fields['name_mode'].setCurrentIndex(1);self.w.fields['name_mode'].setCurrentIndex(2)
  self.assertEqual(before,self.w.snapshot())
  for language in ['en','fr','de','it','zh','ja','es']:
   self.w.set_ui_language(language);self.assertEqual(before,self.w.snapshot())
 def test_remove_share_prunes_descendant_rules_only_for_client(self):
  self.w.render_folders(['/a','/b'],['/a/sub'],['/a/sub/plain'],['/a'],['/a/except'])
  self.w.folders.setCurrentRow(0);self.w.remove_folders();tv=self.w.snapshot()['tvs'][0]
  self.assertEqual(tv['folders'],['/b'])
  for key in ['convert_folders','convert_exclusions','name_folders','name_exclusions']:self.assertEqual(tv[key],[])
 def test_copy_preserves_destination_folder_exceptions(self):
  self.w.fields['name_mode'].setCurrentIndex(1);self.w.tvlist.setCurrentRow(1)
  self.w.render_folders(['/destination'],['/destination'],['/destination/plain'],['/destination/named'],['/destination/named/plain'])
  before=self.w.snapshot()['tvs'][1]
  import baul_gui as g
  with patch.object(g.QDialog,'exec',return_value=QDialog.DialogCode.Accepted):self.w.copy_tv_settings()
  after=self.w.snapshot()['tvs'][1];self.assertEqual(after['name_mode'],'compatible')
  for key in ['folders','convert_folders','convert_exclusions','name_folders','name_exclusions']:self.assertEqual(after[key],before[key])
