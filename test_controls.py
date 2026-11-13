"""Button clicks, service migrations and configured endpoints; production untouched."""
import copy,json,subprocess,tempfile,time,unittest,uuid
from pathlib import Path
from unittest.mock import patch,MagicMock
from PyQt6.QtWidgets import QApplication,QMessageBox
import baul_core as c
import baul_gui as g
import server_manager as m
REAL_REFRESH=g.Window.refresh

def report(status='inactive',kind='healthy'):
 return dict(kind=kind,present=True,repairable=True,status=status,issues=[],warnings=[],foreign=[])

class ControlBackendTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);data=self.root/'data';self.runtime=data/'runtime';self.runtime.mkdir(parents=True)
  for name in ['UMS.sh','ums.jar']:(self.runtime/name).write_text('fixture', encoding='utf-8')
  profile=self.root/'profile';profile.mkdir();self.identity=str(uuid.uuid4());(profile/'UMS.conf').write_text(f'uuid = {self.identity}\nnetwork_interface = lo\nweb_gui_port = 9219\nport = 5219\n', encoding='utf-8')
  self.patches=[patch.object(m.platform_os,'systemd',return_value=True),patch.object(c,'HOME',self.root),patch.object(c,'DATA',data),patch.object(c,'RUNTIME',data/'obsolete'),patch.object(c,'PROFILE',profile),patch.object(c,'CONFIG',self.root/'config')]
  for p in self.patches:p.start()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup()
 def test_missing_unit_is_created_reloaded_and_started(self):
  with patch.object(c,'run',return_value=subprocess.CompletedProcess([],0,'','')) as run,patch.object(c,'ready') as ready,patch.object(m,'health',return_value=report('active')):
   m.control('start');self.assertEqual(c.RUNTIME,self.runtime);self.assertEqual(m.unit_path().read_text(encoding='utf-8'),m.unit_text());ready.assert_called_once()
   self.assertEqual([x.args[0][2] for x in run.call_args_list],['daemon-reload','reset-failed','start'])
 def test_quoted_legacy_unit_is_repaired_at_restart(self):
  c.RUNTIME=self.runtime
  old=m.unit_text().replace('WorkingDirectory='+str(c.RUNTIME),'WorkingDirectory="'+str(c.RUNTIME)+'"');c.atomic_write(m.unit_path(),old)
  with patch.object(c,'run',return_value=subprocess.CompletedProcess([],0,'','')),patch.object(c,'ready'),patch.object(m,'health',return_value=report('active')):m.control('restart')
  self.assertEqual(m.unit_path().read_text(encoding='utf-8'),m.unit_text())
 def test_existing_unit_is_reloaded_even_if_text_unchanged(self):
  c.RUNTIME=self.runtime;c.atomic_write(m.unit_path(),m.unit_text())
  with patch.object(c,'run',return_value=subprocess.CompletedProcess([],0,'','')) as run,patch.object(c,'ready'),patch.object(m,'health',return_value=report('active')):m.control('start')
  self.assertEqual(run.call_args_list[0].args[0],['systemctl','--user','daemon-reload'])
 def test_stop_damaged_runtime_does_not_require_integrity_or_ready(self):
  (self.runtime/'ums.jar').unlink()
  with patch.object(c,'run',return_value=subprocess.CompletedProcess([],0,'','')) as run,patch.object(c,'ready') as ready,patch.object(m,'health',return_value=report('inactive','damaged')):m.control('stop')
  self.assertEqual(run.call_args.args[0],['systemctl','--user','stop',c.SERVICE]);ready.assert_not_called()
 def test_foreign_unit_is_never_replaced_or_controlled(self):
  c.atomic_write(m.unit_path(),'[Service]\nExecStart=/opt/foreign/ums\n')
  with patch.object(c,'run') as run:
   for action in ['start','stop','restart','enable','disable']:
    with self.assertRaises(RuntimeError):m.control(action)
   run.assert_not_called()
 def test_missing_profile_is_actionable_not_false_available(self):
  (c.PROFILE/'UMS.conf').unlink()
  with patch.object(c,'run',return_value=subprocess.CompletedProcess([],0,'','')) as run:
   with self.assertRaisesRegex(RuntimeError,'Guarda y aplica'):m.control('start')
   self.assertNotIn('start',[x.args[0][2] for x in run.call_args_list])
 def test_enable_does_not_start_or_require_network_ready(self):
  with patch.object(c,'run',return_value=subprocess.CompletedProcess([],0,'','')) as run,patch.object(c,'ready') as ready,patch.object(m,'health',return_value=report()):m.control('enable')
  self.assertNotIn('start',[x.args[0][2] for x in run.call_args_list]);ready.assert_not_called()
 def test_web_and_api_follow_saved_port(self):
  self.assertEqual(c.web_url(),'http://127.0.0.1:9219')
  with patch.object(c.urllib.request,'urlopen') as urlopen:
   urlopen.return_value.__enter__.return_value.read.return_value=b'{}';c.api('shared/')
   self.assertEqual(urlopen.call_args.args[0].full_url,'http://127.0.0.1:9219/v1/api/shared/')
 def test_invalid_port_never_opens_arbitrary_url(self):
  (c.PROFILE/'UMS.conf').write_text('web_gui_port = 9001/evil\n', encoding='utf-8')
  with self.assertRaises(ValueError):c.web_url()
 def test_ready_uses_real_profile_without_settings_uuid(self):
  with patch.object(c,'api',return_value={}),patch.object(c,'load_state',side_effect=AssertionError('must not read UI settings')),patch.object(c,'run',return_value=subprocess.CompletedProcess([],0,json.dumps([dict(addr_info=[dict(local='127.0.0.1',family='inet')])]),'')),patch.object(c.urllib.request,'urlopen') as openurl:
   openurl.return_value.__enter__.return_value.status=200;c.ready(timeout=1)
   self.assertEqual(openurl.call_args.args[0],f'http://127.0.0.1:5219/dev/{self.identity}/desc')
 def test_legacy_runtime_is_found_even_when_jar_is_missing(self):
  self.runtime.rename(c.DATA/'ums-15.9.0');(c.DATA/'ums-15.9.0/ums.jar').unlink();self.assertEqual(c.discover_runtime(),c.DATA/'ums-15.9.0')
 def test_runtime_discovery_is_not_version_pinned(self):
  self.runtime.rename(c.DATA/'ums-42.1.0');self.assertEqual(c.discover_runtime(),c.DATA/'ums-42.1.0')

class ButtonTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  self.patches=[patch.object(g.Window,'refresh'),patch.object(g.Window,'check_updates'),patch.object(c,'load_state',return_value=c.defaults()),patch.object(g.appearance,'load',return_value=dict(theme='current',language='es')),patch.object(g.appearance,'save')]
  for p in self.patches:p.start()
  self.w=g.Window();self.w.timer.stop();self.w.show();self.app.processEvents()
 def drain(self):
  end=time.monotonic()+3
  while self.w.jobs and time.monotonic()<end:self.app.processEvents();time.sleep(.002)
  self.assertFalse(self.w.jobs)
 def tearDown(self):
  self.drain();self.w.dirty=False;self.w.close()
  for p in reversed(self.patches):p.stop()
 def test_real_clicked_signals_start_stop_restart(self):
  with patch.object(m,'control',side_effect=lambda action:report('inactive' if action=='stop' else 'active')) as control:
   for index,action,status in [(0,'start','inactive'),(1,'stop','active'),(2,'restart','active')]:
    self.w.update_server_buttons(report(status));self.w.server_controls[index].click();self.drain();self.assertEqual(control.call_args.args,(action,));self.assertFalse(self.w.busy);self.assertTrue(self.w.centralWidget().isEnabled())
 def test_damaged_active_server_can_be_stopped_and_web_opened(self):
  self.w.update_server_buttons(report('active','damaged'));self.assertTrue(self.w.server_controls[1].isEnabled());self.assertTrue(self.w.web_button.isEnabled());self.assertFalse(self.w.server_controls[0].isEnabled())
 def test_bad_repair_bundle_does_not_disable_stop(self):
  r=report('active','damaged');r['repairable']=False;self.w.update_server_buttons(r);self.assertTrue(self.w.server_controls[1].isEnabled());self.assertTrue(self.w.web_button.isEnabled())
 def test_absent_installation_disables_service_controls(self):
  r=report();r.update(kind='absent',present=False);self.w.update_server_buttons(r)
  self.assertTrue(all(not b.isEnabled() for b in self.w.server_controls));self.assertFalse(self.w.web_button.isEnabled())
 def test_web_click_uses_registered_browser_not_qt_portal(self):
  self.w.update_server_buttons(report('active'))
  with patch.object(g.shutil,'which',return_value='/usr/bin/gio'),patch.object(c,'web_url',return_value='http://127.0.0.1:9222'),patch.object(c,'run',return_value=subprocess.CompletedProcess([],0,'','')) as run,patch.object(g.QDesktopServices,'openUrl') as qt:
   self.w.web_button.click();self.drain();self.assertEqual(run.call_args.args[0],['/usr/bin/gio','open','http://127.0.0.1:9222']);qt.assert_not_called()
 def test_web_falls_back_to_qt_if_gio_fails(self):
  with patch.object(g.shutil,'which',return_value='/usr/bin/gio'),patch.object(c,'run',return_value=subprocess.CompletedProcess([],1,'','failed')),patch.object(g.QDesktopServices,'openUrl',return_value=True) as qt:
   self.w.open_web();self.drain();qt.assert_called_once()
 def test_failure_releases_ui_before_warning(self):
  def warning(*_):self.assertFalse(self.w.busy);self.assertTrue(self.w.centralWidget().isEnabled())
  with patch.object(m,'control',side_effect=RuntimeError('fixture failure')),patch.object(g.QMessageBox,'warning',side_effect=warning) as warn:
   self.w.server_action('start');self.drain();warn.assert_called_once();self.w.refresh.assert_called()
 def test_activity_excludes_all_host_addresses_but_keeps_network_clients(self):
  addresses=[dict(addr_info=[dict(family='inet',local=ip)]) for ip in ['127.0.0.1','192.168.1.10','10.0.0.2']]
  clients=[dict(name='local',address=ip,isActive=True) for ip in ['/192.168.1.10','192.168.1.10','/10.0.0.2','127.0.0.1']]
  clients.append(dict(name='PS3',address='/192.168.1.30',isActive=True))
  with patch.object(m,'health',return_value=report('active')),patch.object(c,'active',return_value='active'),patch.object(c,'autostart',return_value=False),patch.object(c,'live_activity',return_value=[]),patch.object(c.platform_os,'addresses',return_value=addresses),patch.object(c,'api',return_value={'renderers':clients}),patch.object(self.w,'task') as task:
   REAL_REFRESH(self.w);work,done=task.call_args.args[:2];data=work();done(data)
  self.assertTrue(data['devices_available']);self.assertEqual([t['name'] for t in data['devices']],['PS3']);self.assertIn('PS3',self.w.now.text());self.assertNotIn('local',self.w.now.text())
 def test_summary_uses_local_names_without_changing_server_data(self):
  self.w.state['tvs']=[c.default_tv('Device A','192.168.1.20','uuid:bedroom'),c.default_tv('Device B','192.168.1.21','uuid:lounge'),c.default_tv('PS3','192.168.1.30')]
  clients=[dict(name='Renderer A',uuid='bedroom',address='192.168.1.20',isActive=True,playing='Capítulo 1',state={'buffer':3}),dict(name='Renderer B',uuid='lounge',address='/192.168.1.21'),dict(name='PlayStation 3',address='192.168.1.30'),dict(name='Sin perfil',address='192.168.1.222')]
  before=copy.deepcopy(clients);self.w.render_activity(dict(devices=clients,activity=[]))
  text=self.w.now.text()
  for name in ['Device A','Device B','PS3','Sin perfil','Capítulo 1']:self.assertIn(name,text)
  for name in ['Renderer A','Renderer B','PlayStation 3']:self.assertNotIn(name,text)
  self.assertEqual(clients,before)
  self.w.state['tvs'][0]['name']='Nuevo nombre';self.w.render_activity(dict(devices=clients,activity=[]));self.assertIn('Nuevo nombre',self.w.now.text())
 def test_summary_identity_survives_ip_change_but_rejects_reassigned_ip(self):
  profiles=[c.default_tv('Device A','192.168.1.20','uuid:BEDROOM'),c.default_tv('Solo IP','192.168.1.22')]
  self.assertEqual(c.device_display_name(dict(name='Antiguo',uuid='bedroom',address='/192.168.1.200'),profiles),'Device A')
  self.assertEqual(c.device_display_name(dict(name='Otro dispositivo',uuid='different',address='192.168.1.20'),profiles),'Otro dispositivo')
  self.assertEqual(c.device_display_name(dict(name='Sin UUID',address='/192.168.1.20'),profiles),'Device A')
  self.assertEqual(c.device_display_name(dict(name='Original',uuid='random',address='192.168.1.22'),profiles),'Solo IP')
  self.assertEqual(c.device_display_name(dict(name='Original',address='192.168.1.22'),profiles+[c.default_tv('Duplicado','192.168.1.22')]),'Original')
 def test_old_refresh_cannot_overwrite_action_result(self):
  real_refresh=g.Window.refresh
  # Class refresh is stubbed by this fixture; load the original saved below.
  with patch.object(self.w,'task') as task:
   REAL_REFRESH(self.w);done=task.call_args.args[1];self.w.control_generation+=1
   done(dict(health=report('inactive'),status='inactive',auto=False,devices=[],activity=[]))
  self.assertFalse(self.w.refreshing);self.assertIsNone(self.w.server_report)

if __name__=='__main__':unittest.main()
