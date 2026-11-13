"""Release API contract, version comparisons and offline error handling."""
import copy,io,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import baul_core as c
import server_releases as r
import server_manager as manager

class ReleaseTests(unittest.TestCase):
 def metadata(self,version='15.10.0'):
  return dict(version=version,tag=version,url=r.DOWNLOAD_PREFIX+version+'/UMS-Linux-'+version+'-x86_64.tgz',sha256='a'*64,size=12345)
 def response(self,version='15.10.0'):
  m=self.metadata(version)
  return dict(tag_name=version,draft=False,prerelease=False,assets=[dict(name='UMS-Linux-'+version+'-x86_64.tgz',browser_download_url=m['url'],digest='sha256:'+m['sha256'],size=m['size'])])
 def installed(self,root,version):
  root.mkdir(exist_ok=True)
  with zipfile.ZipFile(root/'ums.jar','w') as z:z.writestr('META-INF/MANIFEST.MF','Implementation-Version: '+version+'\n')
 def test_latest_download_is_not_pinned(self):
  for version in ['15.10.0','16.0.0','22.1.5']:
   with patch.object(r.urllib.request,'urlopen',return_value=io.BytesIO(json.dumps(self.response(version)).encode())) as get:
    self.assertEqual(r.latest_release(),self.metadata(version));self.assertEqual(get.call_args.args[0].full_url,r.LATEST_URL)
 def test_v_tag_is_supported(self):
  raw=self.response();raw['tag_name']='v15.10.0';raw['assets'][0]['browser_download_url']=raw['assets'][0]['browser_download_url'].replace('/15.10.0/','/v15.10.0/')
  with patch.object(r.urllib.request,'urlopen',return_value=io.BytesIO(json.dumps(raw).encode())):self.assertEqual(r.latest_release()['tag'],'v15.10.0')
 def test_rejects_preview_wrong_platform_and_missing_digest(self):
  for kind in ['prerelease','draft','platform','digest','url','size']:
   raw=self.response()
   if kind in ['prerelease','draft']:raw[kind]=True
   elif kind=='platform':raw['assets'][0]['name']='UMS-Windows-15.10.0.exe'
   elif kind=='digest':raw['assets'][0]['digest']=None
   elif kind=='url':raw['assets'][0]['browser_download_url']='https://example.com/server.tgz'
   elif kind=='size':raw['assets'][0]['size']=-1
   with self.subTest(kind=kind),patch.object(r.urllib.request,'urlopen',return_value=io.BytesIO(json.dumps(raw).encode())):
    with self.assertRaises(ValueError):r.latest_release()
 def test_numeric_version_not_lexical(self):self.assertGreater(r.version_tuple('15.10.0'),r.version_tuple('15.9.0'))
 def test_new_equal_older_and_absent(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(c,'RUNTIME',Path(tmp)/'runtime'),patch.object(r,'latest_release',return_value=self.metadata()):
   self.assertFalse(r.check_update()['available'])
   for version,expected in [('15.9.0',True),('15.10.0',False),('16.0.0',False)]:
    self.installed(c.RUNTIME,version);result=r.check_update();self.assertEqual(result['available'],expected);self.assertEqual(result['installed'],version)
 def test_offline_is_not_a_false_update_or_a_false_success(self):
  with patch.object(r,'latest_release',side_effect=OSError('offline')):
   result=r.check_update();self.assertFalse(result['available']);self.assertEqual(result['error'],'offline');self.assertIsNone(result['release'])
 def test_update_uses_the_official_discovered_release_and_never_downgrades(self):
  release=self.metadata()
  with patch.object(r,'jar_version',return_value='15.9.0'),patch.object(manager,'install',return_value={'kind':'healthy'}) as install:
   self.assertEqual(manager.update(release),{'kind':'healthy'});install.assert_called_once_with(repair=True,release=release)
  for version in ['15.10.0','16.0.0']:
   with patch.object(r,'jar_version',return_value=version),patch.object(manager,'install') as install:
    with self.assertRaises(RuntimeError):manager.update(release)
    install.assert_not_called()
 def test_checksum_and_tag_cannot_be_injected(self):
  for key,value in [('tag','../15.10.0'),('sha256','bad'),('version','15.10.0-rc1')]:
   metadata=self.metadata();metadata[key]=value
   with self.assertRaises(ValueError):r.validate_release(metadata)

if __name__=='__main__':unittest.main()
