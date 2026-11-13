"""Desktop Entry escaping is verified by GIO, not by a shell-like parser."""
import json,os,shutil,subprocess,tempfile,unittest
from pathlib import Path
from install import desktop_exec
class DesktopTests(unittest.TestCase):
 def test_launcher_with_spaces_and_reserved_characters(self):
  if not shutil.which('gio'):self.fail('gio is a declared runtime/test prerequisite')
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp)/'User With Spaces $money `literal` "quote" %percent \\backslash';root.mkdir()
   marker=Path(temp)/'result.json';script=root/'record.py';script.write_text('import json,os,sys\nfrom pathlib import Path\nPath(os.environ["UMS_TEST_MARKER"]).write_text(json.dumps(sys.argv))\n', encoding='utf-8')
   launcher=root/'ums-control';launcher.write_text('#!/usr/bin/python3\n'+script.read_text(encoding='utf-8'), encoding='utf-8');launcher.chmod(0o755)
   desktop=Path(temp)/'test.desktop';desktop.write_text('[Desktop Entry]\nType=Application\nName=UMS Test\nExec='+desktop_exec(launcher)+'\nTerminal=false\n', encoding='utf-8')
   result=subprocess.run(['desktop-file-validate',str(desktop)],capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
   result=subprocess.run(['gio','launch',str(desktop)],env=dict(os.environ,UMS_TEST_MARKER=str(marker)),capture_output=True,text=True,timeout=15);self.assertEqual(result.returncode,0,result.stderr)
   import time
   deadline=time.monotonic()+5
   while not marker.exists() and time.monotonic()<deadline:time.sleep(.05)
   self.assertTrue(marker.exists(),result.stderr);self.assertEqual(json.loads(marker.read_text(encoding='utf-8')),[str(launcher)])

 def test_frontend_install_and_update_are_isolated(self):
  from contextlib import ExitStack,redirect_stdout
  from unittest.mock import patch
  import io,sys
  import baul_core as c,install
  with tempfile.TemporaryDirectory() as temp,ExitStack() as stack:
   home=Path(temp)/'Desktop User';home.mkdir();data=home/'.local/share/baul-ums'
   for key,value in dict(HOME=home,CONFIG=home/'.config/baul-media-control',PROFILE=home/'.config/baul-ums',DATA=data,RUNTIME=data/'runtime').items():stack.enter_context(patch.object(c,key,value))
   commands=stack.enter_context(patch.object(c,'run',return_value=subprocess.CompletedProcess([],0,'','')))
   stack.enter_context(patch.object(c,'active',return_value='inactive'));stack.enter_context(patch.object(sys,'argv',['install.py']))
   with redirect_stdout(io.StringIO()):install.main();install.main()
   target=home/'.local/share/baul-media-control';manifest=json.loads((target/'install-manifest.json').read_text(encoding='utf-8'))
   self.assertIn('configuration.py',manifest);self.assertIn('native_dependencies.py',manifest)
   self.assertFalse((c.CONFIG/'settings.json').exists());self.assertFalse(data.exists())
   self.assertFalse(list((target/'server-support').glob('*.deb')))
   self.assertFalse(any(call.args[0][0]=='systemctl' for call in commands.call_args_list))
