"""Damaged configuration must never silently replace server profiles."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import appearance,baul_core as c
from configuration import ConfigurationError,preserve
class RecoveryTests(unittest.TestCase):
 def test_invalid_settings_are_reported_and_preserved(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(c,'CONFIG',Path(tmp)):
   path=Path(tmp)/'settings.json'
   for raw in [b'{"version":',b'[]',b'{"version":2,"tvs":null}',b'\xff',json.dumps(dict(version=2,name='Server',interface='lo',tvs=[{}])).encode()]:
    path.write_bytes(raw)
    with self.assertRaises(ConfigurationError):c.load_state()
    self.assertEqual(path.read_bytes(),raw)
    backup=preserve(path);self.assertEqual(backup.read_bytes(),raw);self.assertEqual(backup.stat().st_mode&0o777,0o600)
 def test_bad_ui_is_reported_without_overwrite(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(c,'CONFIG',Path(tmp)):
   path=Path(tmp)/'ui.json'
   for raw in ['[]','null','{"theme":','{"theme": []}']:
    path.write_text(raw, encoding='utf-8')
    with self.assertRaises(ConfigurationError):appearance.load()
    self.assertEqual(path.read_text(encoding='utf-8'),raw)
 def test_absent_and_disconnected_settings_are_not_damage(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(c,'CONFIG',Path(tmp)):
   self.assertEqual(c.load_state()['tvs'],[])
   state=c.defaults();state['interface']='disconnected-nic';tv=c.default_tv('Disconnected','192.0.2.10');tv['folders']=['/not-mounted/library'];state['tvs']=[tv]
   (Path(tmp)/'settings.json').write_text(json.dumps(state), encoding='utf-8');self.assertEqual(c.load_state()['tvs'][0]['folders'],tv['folders'])
