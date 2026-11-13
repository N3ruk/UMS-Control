import copy,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import baul_core as c
class ConfigurationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  self.patches=[patch.object(c,'CONFIG',self.root/'panel'),patch.object(c,'PROFILE',self.root/'ums')]
  for p in self.patches:p.start()
  self.s=c.defaults();self.s['interface']='lo';self.s['tvs']=[c.default_tv('Sala','192.168.1.22','uuid:abcd')]
 def tearDown(self):
  for p in self.patches:p.stop()
  self.temp.cleanup()
 def test_direct_per_device(self):
  t=self.s['tvs'][0];t['mode']='direct';x=c.device_config(t)
  self.assertIn('disable_transcoding = true',x);self.assertIn('Device = abcd, 192.168.1.22',x)
 def test_force_distinct(self):
  a=copy.deepcopy(self.s['tvs'][0]);a['mode']='direct';b=copy.deepcopy(a);b['mode']='force'
  self.assertNotIn('force_transcode_for_extensions = *',c.device_config(a));self.assertIn('force_transcode_for_extensions = *',c.device_config(b))
  self.assertNotIn('Supported = f:mkv',c.device_config(b))
 def test_high10_not_direct(self):
  x=c.device_config(self.s['tvs'][0]);self.assertIn('force_transcode_for_extensions = *',x);self.assertIn('SupportedVideoBitDepths = 8',x);self.assertNotIn('f:.+',x)
 def test_native_not_override(self):
  t=self.s['tvs'][0];t['preset']='native';t['mode']='direct';self.assertNotIn('Supported =',c.device_config(t))
 def test_nvidia_encoding_only(self):
  t=self.s['tvs'][0];t['encoder']='nvidia';x=c.device_config(t)
  self.assertIn('acceleration_method = none',x);self.assertIn('acceleration_method = h264_nvenc',x)
 def test_subtitles_off(self):
  self.s['tvs'][0]['subtitles']='off';self.assertIn('disable_subtitles = true',c.device_config(self.s['tvs'][0]))
 def test_empty_sharing_no_home_fallback(self):self.assertEqual(json.loads(c.shared_config(self.s)),[])
 def test_share_json_unicode(self):
  self.s['tvs'][0]['folders']=['/media/Series Ñ/"test"'];self.assertEqual(json.loads(c.shared_config(self.s))[0]['file'],self.s['tvs'][0]['folders'][0])
 def test_duplicate_ip_rejected(self):
  self.s['tvs'].append(c.default_tv('Otra','192.168.1.22'));self.assertRaises(ValueError,c.validate,self.s)
 def test_duplicate_uuid_rejected(self):
  self.s['tvs'].append(c.default_tv('Otra','192.168.1.23','uuid:abcd'));self.assertRaises(ValueError,c.validate,self.s)
 def test_config_injection_rejected(self):
  self.s['tvs'][0]['name']='Sala\nDevice = 192.168.1.99';self.assertRaises(ValueError,c.validate,self.s)
 def test_unsafe_id_rejected(self):
  self.s['tvs'][0]['id']='../../bad';self.assertRaises(ValueError,c.validate,self.s)
 def test_public_address_rejected(self):
  self.s['tvs'][0]['ip']='8.8.8.8';self.assertRaises(ValueError,c.validate,self.s)
 def test_invalid_before_stop(self):
  self.s['tvs'][0]['target']='invalid'
  with patch.object(c,'service') as svc:
   self.assertRaises(ValueError,c.apply,self.s);svc.assert_not_called()
 def test_write_and_remove_profile(self):
  with patch.object(c,'active',return_value='inactive'):
   c.apply(self.s);paths=list((c.PROFILE/'renderers').glob('baul-*.conf'));self.assertEqual(len(paths),1)
   self.s['tvs']=[];c.apply(self.s);self.assertFalse(paths[0].exists())
 def test_stable_server_uuid(self):
  with patch.object(c,'active',return_value='inactive'):
   c.apply(self.s);saved=c.load_state();identity=saved['server_uuid'];c.apply(saved)
   self.assertEqual(c.load_state()['server_uuid'],identity);self.assertIn('uuid = '+identity,(c.PROFILE/'UMS.conf').read_text(encoding='utf-8'))
 def test_rollback_failed_start(self):
  with patch.object(c,'active',return_value='inactive'):c.apply(self.s)
  before=(c.PROFILE/'UMS.conf').read_bytes();old=c.load_state();self.s['name']='Changed'
  with patch.object(c,'active',return_value='active'),patch.object(c,'service'),patch.object(c,'ready',side_effect=RuntimeError('startup failed')):
   self.assertRaises(RuntimeError,c.apply,self.s)
  self.assertEqual((c.PROFILE/'UMS.conf').read_bytes(),before);self.assertEqual(c.load_state(),old)
 def test_source_directory_never_touched(self):
  media=self.root/'media';media.mkdir();video=media/'a.mkv';video.write_bytes(b'ORIGINAL');self.s['tvs'][0]['folders']=[str(media)]
  with patch.object(c,'active',return_value='inactive'):
   c.apply(self.s);self.s['tvs'][0]['folders']=[];c.apply(self.s)
  self.assertEqual(video.read_bytes(),b'ORIGINAL')
 def test_ssdp_urls_lan_only(self):
  for url in ['http://8.8.8.8/a','file:///etc/passwd','http://127.0.0.1:18789/','http://user:pw@192.168.1.3/','http://0.0.0.0/']:
   self.assertFalse(c.local_url(url),url)
  self.assertTrue(c.local_url('http://192.168.1.136:18400/desc.xml'))
 def test_no_external_metadata(self):
  self.s['server_uuid']='test';x=c.main_config(self.s)
  self.assertIn('external_network = false',x);self.assertIn('use_api_info = false',x)
 def test_catalog_derived_from_mode_independent_of_subtitles(self):
  t=self.s['tvs'][0];t.update(mode='force',subtitles='burn',show_transcode_folder=False,resume=True)
  x=c.device_config(t);self.assertIn('show_transcode_folder = true',x);self.assertIn('resume = false',x)
  t['subtitles']='passthrough';self.assertIn('show_transcode_folder = true',c.device_config(t))
  t.update(mode='direct',subtitles='burn');self.assertIn('show_transcode_folder = false',c.device_config(t))
 def test_direct_unlimited_ignores_conversion_caps(self):
  t=self.s['tvs'][0];t.update(mode='direct',resolution='480p',bitrate=3)
  x=c.device_config(t)
  for line in ['MaxVideoWidth = 0','MaxVideoHeight = 0','MaxVideoBitrateMbps = 0','maximum_bitrate = 0','disable_subtitles = true','autoload_external_subtitles = false']:
   self.assertIn(line,x)
 def test_soft_subtitles_select_matroska_for_each_codec(self):
  t=self.s['tvs'][0];t.update(mode='force',subtitles='passthrough')
  for target in c.TARGETS:
   t['target']=target;x=c.device_config(t)
   self.assertIn('TranscodeVideo = '+target.replace('MPEGTS-','MKV-').replace('MPEGPS-','MKV-'),x)
   self.assertIn('disable_subtitles = true',x);self.assertIn('show_transcode_folder = true',x)
 def test_legacy_migration_is_pure_and_deterministic(self):
  t=self.s['tvs'][0];t.update(mode='auto',subtitles='off',resume=True)
  before=copy.deepcopy(t);converted=c.editable_tv(t)
  self.assertEqual(t,before);self.assertEqual(converted['mode'],'auto');self.assertEqual(converted['subtitles'],'passthrough');self.assertFalse(converted['resume'])
  t.update(mode='direct',subtitles='auto');converted=c.editable_tv(t);self.assertEqual(converted['mode'],'direct');self.assertFalse(converted['show_transcode_folder'])
 def test_burn_does_not_suppress_subtitles_matching_audio_language(self):
  t=self.s['tvs'][0];t.update(mode='force',subtitles='burn')
  self.assertIn('audio_subtitles_languages = \n',c.device_config(t));self.assertIn('disable_subtitles = false',c.device_config(t))
 def test_automatic_mode_saved_without_starting_stopped_server(self):
  self.s['tvs'][0]['mode']='auto'
  with patch.object(c,'active',return_value='inactive'),patch.object(c,'service') as svc:
   c.apply(self.s);svc.assert_not_called()
  self.assertEqual(c.load_state()['tvs'][0]['mode'],'auto')
 def test_external_subtitles_mapping_and_passthrough(self):
  t=self.s['tvs'][0];t['subtitles']='burn';t['external_subtitles']=False;x=c.device_config(t);self.assertIn('autoload_external_subtitles = false',x);self.assertIn('force_external_subtitles = false',x)
  t['external_subtitles']=True;x=c.device_config(t);self.assertIn('autoload_external_subtitles = true',x);self.assertIn('force_external_subtitles = false',x);t['subtitles']='passthrough';x=c.device_config(t);self.assertIn('disable_subtitles = true',x);self.assertIn('autoload_external_subtitles = false',x)
 def test_unlimited_conversion_persisted_without_automatic_bandwidth(self):
  t=self.s['tvs'][0];t['bitrate']=0
  with patch.object(c,'active',return_value='inactive'):c.apply(self.s)
  saved=c.load_state()['tvs'][0];self.assertEqual(saved['bitrate'],0)
  for sub in ['burn','passthrough']:
   saved['subtitles']=sub;x=c.device_config(saved)
   for line in ['MaxVideoBitrateMbps = 0','maximum_bitrate = 0','automatic_maximum_bitrate = false']:self.assertIn(line,x)
 def test_invalid_bitrate_rejected_before_touching_service(self):
  for value in [-1,1,2,101,True,False,25.5,'0',None]:
   self.s['tvs'][0]['bitrate']=value
   with patch.object(c,'service') as svc:self.assertRaises(ValueError,c.apply,self.s);svc.assert_not_called()
 def test_new_options_validated_and_persisted(self):
  t=self.s['tvs'][0];t.update(resolution='1440p',audio_bitrate=192,resume=False,external_subtitles=False)
  with patch.object(c,'active',return_value='inactive'):c.apply(self.s)
  saved=c.load_state()['tvs'][0];self.assertEqual(saved['audio_bitrate'],192);self.assertFalse(saved['resume']);x=c.device_config(saved);self.assertIn('MaxVideoWidth = 2560',x);self.assertIn('audio_bitrate = 192',x)
  for key,bad in [('audio_bitrate',999),('resume','false'),('external_subtitles',1)]:
   invalid=copy.deepcopy(self.s);invalid['tvs'][0][key]=bad
   with patch.object(c,'service') as svc:self.assertRaises(ValueError,c.apply,invalid);svc.assert_not_called()
if __name__=='__main__':unittest.main()
