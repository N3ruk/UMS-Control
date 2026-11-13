"""Network labels must preserve interface identity and distinguish virtual links."""
import copy,json,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import baul_core as c

class NetworkTests(unittest.TestCase):
 def test_physical_wireless_and_virtual_devices_are_distinct(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp)
   for name,medium in [('enp2s0','ethernet'),('enp1s0','ethernet'),('wlan1','wifi'),('wlan0','wifi'),('br0','virtual')]:
    p=root/name;p.mkdir();(p/'type').write_text('1', encoding='utf-8');(p/'operstate').write_text('up', encoding='utf-8')
    if medium=='ethernet':(p/'device').mkdir()
    if medium=='wifi':(p/'wireless').mkdir()
   with patch.object(c.socket,'if_nameindex',return_value=[(i,n) for i,n in enumerate(['lo','wlan1','enp2s0','br0','wlan0','enp1s0'])]):
    actual={i['name']:(i['kind'],i['number']) for i in c.network_interfaces(root)}
   self.assertEqual(actual,{'br0':('other',1),'enp1s0':('ethernet',1),'enp2s0':('ethernet',2),'wlan0':('wifi',1),'wlan1':('wifi',2)})
 def test_initial_interface_follows_available_default_route(self):
  networks=[dict(name='wifi-test',kind='wifi',up=True),dict(name='ether-test',kind='ethernet',up=True)]
  result=subprocess.CompletedProcess([],0,json.dumps([{'dev':'removed','metric':0},{'dev':'ether-test','metric':100},{'dev':'wifi-test','metric':600}]),'')
  with patch.object(c,'network_interfaces',return_value=networks),patch.object(c,'run',return_value=result):
   self.assertEqual(c.defaults(),dict(version=2,name='UMS Control',interface='ether-test',tvs=[]))
 def test_saved_identity_survives_friendly_labels_and_language_changes(self):
  from PyQt6.QtWidgets import QApplication
  import baul_gui as g
  app=QApplication.instance() or QApplication([])
  state=dict(version=1,name='My library',interface='second-ether',folders=[],tvs=[])
  networks=[dict(name='first-ether',kind='ethernet',number=1),dict(name='second-ether',kind='ethernet',number=2),dict(name='first-wifi',kind='wifi',number=1),dict(name='second-wifi',kind='wifi',number=2),dict(name='bridge-test',kind='other',number=1)]
  with patch.object(c,'load_state',side_effect=lambda:copy.deepcopy(state)),patch.object(c,'network_interfaces',return_value=networks),patch.object(g.Window,'refresh'),patch.object(g.appearance,'load',return_value=dict(theme='current',language='es')),patch.object(g.appearance,'save'):
   w=g.Window();w.timer.stop()
   try:
    self.assertEqual([w.interface.itemText(i) for i in range(w.interface.count())],['Ethernet','Ethernet 2','WiFi','WiFi 2','Otra red (bridge-test)'])
    for language in ['en','fr','de','it','zh','ja','es']:
     w.set_ui_language(language);self.assertEqual(w.snapshot()['interface'],'second-ether')
    w.interface.setCurrentIndex(w.interface.findData('second-wifi'));self.assertEqual(w.snapshot()['interface'],'second-wifi')
   finally:w.dirty=False;w.close()
 def test_missing_saved_network_is_not_silently_replaced(self):
  from PyQt6.QtWidgets import QApplication
  import baul_gui as g
  app=QApplication.instance() or QApplication([])
  state=dict(version=1,name='My library',interface='unplugged',folders=[],tvs=[])
  with patch.object(c,'load_state',return_value=state),patch.object(c,'network_interfaces',return_value=[]),patch.object(g.Window,'refresh'),patch.object(g.appearance,'load',return_value=dict(theme='current',language='es')):
   w=g.Window();w.timer.stop()
   try:self.assertEqual(w.snapshot()['interface'],'unplugged');self.assertIn('no disponible',w.interface.currentText())
   finally:w.dirty=False;w.close()

if __name__=='__main__':unittest.main()
