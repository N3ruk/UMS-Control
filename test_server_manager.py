"""Isolated lifecycle regression. Never controls the user's real service."""
import copy,json,os,shutil,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import baul_core as c
import server_manager as m

class ManagerTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.stopped=True;self.enabled=False;self.calls=[];self.trash_count=0
  home=self.root/'home';data=home/'.local/share/baul-ums'
  self.patches=[patch.object(m.platform_os,'systemd',return_value=True),patch.object(c,'HOME',home),patch.object(c,'DATA',data),patch.object(c,'RUNTIME',data/'ums-15.9.0'),patch.object(c,'CONFIG',home/'.config/baul-media-control'),patch.object(c,'PROFILE',home/'.config/baul-ums'),patch.object(c,'active',side_effect=lambda:'inactive' if self.stopped else 'active'),patch.object(c,'autostart',side_effect=lambda:self.enabled),patch.object(c,'ready'),patch.object(c,'api',return_value={}),patch.object(c,'run',side_effect=self.run_command),patch.object(m,'foreign_installations',return_value=[]),patch.object(m.native_dependencies,'packages',side_effect=lambda cache:[m.native_dependencies.fetch(item,Path(__file__).parent/'.cache/upstream') for item in m.native_dependencies.manifest()['packages']]),patch.object(m.releases,'latest_release',return_value=dict(version='15.9.0',tag='15.9.0',url=m.releases.DOWNLOAD_PREFIX+'15.9.0/UMS-Linux-15.9.0-x86_64.tgz',sha256='532d6311539beb27f44a353762f164b0b4e9dc452903476b4818d8af8d948ac9',size=246213103))]
  for p in self.patches:p.start()
  c.CONFIG.mkdir(parents=True);c.PROFILE.mkdir(parents=True)
  self.media=self.root/'movie.mkv';self.media.write_bytes(b'original media')
  state=c.defaults();state.update(folders=[str(self.root)],interface='lo',tvs=[])
  (c.CONFIG/'settings.json').write_text(json.dumps(state), encoding='utf-8');(c.PROFILE/'UMS.conf').write_text('untouched configuration', encoding='utf-8')
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup()
 def run_command(self,args,timeout=40,check=True):
  if args[0]=='systemctl':
   self.calls.append(args)
   if 'stop' in args:self.stopped=True
   if 'start' in args:self.stopped=False
   if 'disable' in args:self.enabled=False
   if 'enable' in args:self.enabled=True
   return subprocess.CompletedProcess(args,0,'','')
  if args[:2]==['gio','trash']:
   dest=self.root/'trash'/str(self.trash_count);dest.parent.mkdir(exist_ok=True);self.trash_count+=1;Path(args[2]).rename(dest)
   return subprocess.CompletedProcess(args,0,'','')
  return subprocess.run(args,capture_output=True,text=True,timeout=timeout,check=check)
 def test_absent(self):self.assertEqual(m.health()['kind'],'absent')
 def test_foreign_unit_cannot_be_removed(self):
  c.atomic_write(m.unit_path(),'[Service]\nExecStart=/opt/some-other-ums/start\n')
  self.assertEqual(m.health()['kind'],'incompatible')
  with self.assertRaises(RuntimeError):m.uninstall()
  self.assertEqual(self.calls,[])
 def test_symlink_install_is_never_modified(self):
  c.DATA.parent.mkdir(parents=True);c.DATA.symlink_to(self.root,target_is_directory=True)
  with self.assertRaises(RuntimeError):m.install(repair=True)
  self.assertEqual(self.calls,[])
 def test_bad_download_changes_nothing(self):
  archive=self.root/'bad.tgz';archive.write_bytes(b'invalid')
  with self.assertRaises(RuntimeError):m.install(archive=archive)
  self.assertFalse(c.DATA.exists());self.assertEqual(self.calls,[])
 def test_failed_service_is_not_itself_a_reinstall_reason(self):
  # A missing installation stays absent even if systemd has a stale failed state.
  with patch.object(c,'active',return_value='failed'):self.assertEqual(m.health()['kind'],'absent')
 def test_unit_handles_spaces_and_systemd_specifiers(self):
  with patch.object(c,'RUNTIME',self.root/'a b%/runtime'):
   self.assertIn('"'+str(self.root)+'/a b%%/runtime/UMS.sh" console',m.unit_text())
 def test_systemd_accepts_generated_working_directory(self):
  c.atomic_write(m.unit_path(),m.unit_text())
  result=subprocess.run(['systemd-analyze','--user','verify',str(m.unit_path())],capture_output=True,text=True,timeout=15)
  # Runtime files do not exist in this fixture. The directory itself must parse.
  self.assertNotIn('WorkingDirectory= path is not absolute',result.stderr)
  self.assertIn('WorkingDirectory='+str(c.RUNTIME)+'\n',m.unit_text())
 def test_legacy_working_directory_is_repaired_without_starting(self):
  text=m.unit_text().replace('WorkingDirectory='+str(c.RUNTIME),'WorkingDirectory="'+str(c.RUNTIME)+'"')
  c.atomic_write(m.unit_path(),text);self.assertTrue(m.owned_unit());self.assertTrue(m.refresh_service_unit())
  self.assertEqual(m.unit_path().read_text(encoding='utf-8'),m.unit_text());self.assertEqual(self.calls,[['systemctl','--user','daemon-reload']])
  self.assertFalse(m.refresh_service_unit())
 def test_full_install_diagnose_repair_rollback_uninstall(self):
  archive=Path(__file__).parent/'.cache/UMS-Linux-15.9.0-x86_64.tgz'
  if not archive.exists():
   if os.environ.get('UMS_REQUIRE_INTEGRATION')=='1':self.fail('Run tools/fetch_upstream.py first; integration must not be skipped')
   self.skipTest('Run tools/fetch_upstream.py to provision the official archive')
  original=(c.CONFIG/'settings.json').read_bytes();profile=(c.PROFILE/'UMS.conf').read_bytes()
  report=m.install(archive=archive);self.assertEqual(report['kind'],'healthy',report);self.assertTrue(self.stopped)
  self.assertTrue((c.RUNTIME/'jre17/bin/java').is_file());self.assertTrue(m.owned_unit())
  with self.assertRaises(RuntimeError):m.install(archive=archive)
  (c.RUNTIME/'update.jar').write_bytes(b'damaged');self.assertEqual(m.health(deep=True)['kind'],'damaged')
  # A failed restart restores the exact previous damaged installation rather than losing it.
  self.stopped=False;self.enabled=True
  def fail_ready():
   (c.PROFILE/'UMS.conf').write_text('simulated configuration migration', encoding='utf-8');raise RuntimeError('simulated restart failure')
  with patch.object(c,'ready',side_effect=fail_ready):
   with self.assertRaises(RuntimeError):m.install(repair=True,archive=archive)
  self.assertEqual((c.PROFILE/'UMS.conf').read_bytes(),profile)
  self.assertEqual((c.RUNTIME/'update.jar').read_bytes(),b'damaged');self.assertFalse(self.stopped);self.assertTrue(self.enabled)
  report=m.install(repair=True,archive=archive);self.assertEqual(report['kind'],'healthy',report);self.assertFalse(self.stopped)
  report=m.uninstall();self.assertEqual(report['kind'],'absent');self.assertTrue(self.stopped);self.assertFalse(self.enabled)
  self.assertFalse(c.DATA.exists());self.assertFalse(m.unit_path().exists())
  self.assertEqual((c.CONFIG/'settings.json').read_bytes(),original);self.assertEqual((c.PROFILE/'UMS.conf').read_bytes(),profile);self.assertEqual(self.media.read_bytes(),b'original media')
  self.assertGreaterEqual(self.trash_count,3)

if __name__=='__main__':unittest.main()
