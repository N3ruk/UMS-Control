"""OS boundary regressions: language precedence, safe archives and owned process IDs."""
import io,json,os,socket,subprocess,tarfile,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import baul_core as c,platform_support as p,first_run,portable_service as service
class PortabilityTests(unittest.TestCase):
 def test_language_first_default_and_existing_user_preference(self):
  import appearance
  with tempfile.TemporaryDirectory() as temp,patch.object(c,'CONFIG',Path(temp)),patch.object(first_run,'initial_language',return_value='de'):
   with patch.object(appearance,'initial_language',return_value='de'):self.assertEqual(appearance.load()['language'],'de')
   appearance.save('current','ja')
   with patch.object(appearance,'initial_language',return_value='fr'):self.assertEqual(appearance.load()['language'],'ja')
 def test_explicit_language_and_noninteractive_input(self):
  for code in first_run.LANGUAGES:self.assertEqual(first_run.choose(code),code)
  with self.assertRaises(ValueError):first_run.choose('invalid')
  with patch('sys.stdin.isatty',return_value=False),patch('builtins.print'):
   with self.assertRaises(RuntimeError):first_run.choose()
 def test_debian_extraction_without_dpkg(self):
  data=io.BytesIO()
  with tarfile.open(fileobj=data,mode='w:xz') as tf:
   item=tarfile.TarInfo('usr/lib/test.txt');item.size=4;tf.addfile(item,io.BytesIO(b'test'))
  raw=data.getvalue();header=('data.tar.xz/    '.ljust(16)+'0'.ljust(12)+'0'.ljust(6)+'0'.ljust(6)+'100644'.ljust(8)+str(len(raw)).ljust(10)+'`\n').encode()
  with tempfile.TemporaryDirectory() as temp,patch.object(p.shutil,'which',return_value=None):
   root=Path(temp);archive=root/'library.deb';archive.write_bytes(b'!<arch>\n'+header+raw+(b'\n' if len(raw)%2 else b''));p.extract_deb(archive,root/'out');self.assertEqual((root/'out/usr/lib/test.txt').read_text(encoding='utf-8'),'test')
 def test_pid_reuse_never_targets_an_unrelated_process(self):
  import psutil
  with tempfile.TemporaryDirectory() as temp,patch.object(c,'CONFIG',Path(temp)):
   proc=psutil.Process(os.getpid());service.statefile().write_text(json.dumps(dict(pid=proc.pid,created=proc.create_time()-100)),encoding='utf-8')
   self.assertIsNone(service.process());service.control('stop');self.assertTrue(proc.is_running())
 def test_windows_properties_bind_selected_ipv4_not_a_java_interface_alias(self):
  state=dict(server_uuid='11111111-1111-1111-1111-111111111111',name='Test',interface='Wi-Fi')
  with tempfile.TemporaryDirectory() as temp,patch.object(c,'PROFILE',Path(temp)),patch.object(p,'WINDOWS',True),patch.object(p,'addresses',return_value=[dict(ifname='Ethernet',addr_info=[dict(local='192.168.50.1')]),dict(ifname='Wi-Fi',addr_info=[dict(local='192.168.50.2')])]):
   config=c.main_config(state);self.assertIn('hostname = 192.168.50.2',config);self.assertIn('network_interface = \n',config)
 def test_system_commands_do_not_inherit_private_library_overrides(self):
  with patch.dict(os.environ,{'LD_LIBRARY_PATH':'/private/qt/libs','LD_PRELOAD':'/private/override.so'}),patch.object(c.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'','')) as run:
   c.run(['gio','version']);env=run.call_args.kwargs['env'];self.assertNotIn('LD_LIBRARY_PATH',env);self.assertNotIn('LD_PRELOAD',env)
 def test_portable_server_log_uses_bounded_local_files_not_journalctl(self):
  with tempfile.TemporaryDirectory() as temp,patch.object(c,'PROFILE',Path(temp)),patch.object(p,'systemd',return_value=False),patch.object(c,'run') as run:
   (Path(temp)/'console.log').write_bytes(b'x'*18000+b'END');text=c.server_log();self.assertTrue(text.endswith('END'));self.assertLess(len(text),12100);run.assert_not_called()
 def test_network_api_failure_keeps_frontend_available(self):
  import psutil
  with patch.object(psutil,'net_if_stats',side_effect=RuntimeError('no adapters')):self.assertEqual(p.networks(),[])
if __name__=='__main__':unittest.main()
