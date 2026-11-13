"""Automatic-mode settings and multi-source discovery regression."""
import copy,json,socket,unittest
from unittest.mock import patch,MagicMock
from types import SimpleNamespace
import baul_core as c
class AutomaticTests(unittest.TestCase):
 def test_old_profile_keeps_automatic_container(self):
  t=c.default_tv('TV','192.168.1.20');t.pop('container');before=copy.deepcopy(t)
  self.assertEqual(c.tv_value(t,'container'),'auto');self.assertEqual(c.editable_tv(t)['container'],'auto');self.assertEqual(t,before)
 def test_explicit_container_matrix(self):
  s=c.defaults();s['interface']='lo';t=c.default_tv('TV','192.168.1.20');s['tvs']=[t]
  for target in c.TARGETS:
   for container in c.CONTAINERS:
    for sub in ['burn','passthrough']:
     t.update(target=target,container=container,subtitles=sub,mode='auto')
     bad=(container=='mpegps' and target!='MPEGPS-MPEG2-AC3') or (container=='mp4' and target=='MPEGPS-MPEG2-AC3')
     if bad:self.assertRaises(ValueError,c.validate,s)
     else:
      c.validate(s);text=c.device_config(t);self.assertIn('ums_control_auto = true',text);self.assertNotIn('Supported = f:',text);self.assertNotIn('force_transcode_for_extensions = *',text)
      if container!='auto':self.assertIn('TranscodeVideo = '+container.upper()+'-'+target.split('-',1)[1],text)
 def test_invalid_container_rejected_before_service(self):
  s=c.defaults();s['interface']='lo';s['tvs']=[c.default_tv('TV','192.168.1.20')];s['tvs'][0]['container']='invalid'
  with patch.object(c,'service') as service:self.assertRaises(ValueError,c.apply,s);service.assert_not_called()
 def test_ps3_search_identity(self):
  for h in [{'user-agent':'PLAYSTATION 3'},{'x-av-client-info':'av=5.0; cn="Sony Computer Entertainment Inc."; mn="PLAYSTATION 3"; mv="1.0"'}]:
   t=c.discovery_identity(h,'192.168.1.30');self.assertEqual(t['name'],'PlayStation 3');self.assertEqual(t['udn'],'')
  self.assertIsNone(c.discovery_identity({'user-agent':'Windows UPnP/1.0'},'192.168.1.30'))
 def test_merge_clients_without_fake_identity_or_duplicates(self):
  def item(ip,name='UnknownRenderer',udn='',source='ums'):return dict(ip=ip,name=name,udn=udn,source=source,model=name,manufacturer='',location='')
  rows=[item('192.168.1.20',udn='uuid:generated'),item('192.168.1.20','TV',udn='uuid:real',source='ssdp'),*[item('192.168.1.1',source=source) for source in ['server','ums','ssdp','ssdp-client']],item('8.8.8.8'),item('192.168.1.30'),c.discovery_identity({'user-agent':'PLAYSTATION 3'},'192.168.1.30')]
  result=c.merge_discovered(rows,{'192.168.1.1'});self.assertEqual(len(result),2);self.assertEqual(result[0]['udn'],'uuid:real');self.assertEqual(result[0]['name'],'TV');self.assertEqual(result[1]['name'],'PlayStation 3');self.assertEqual(result[1]['udn'],'')
 def test_ums_clients_survive_multicast_failure(self):
  interfaces=[dict(ifname='lo',addr_info=[dict(family='inet',local='127.0.0.1')])]
  clients=dict(renderers=[dict(name='PS3',address='/192.168.1.30',isActive=True,uuid='generated'),dict(name='stale',address='192.168.1.31',isActive=False)])
  with patch.object(c,'run',return_value=SimpleNamespace(stdout=json.dumps(interfaces))),patch.object(socket,'socket',side_effect=OSError('offline')),patch.object(c,'api',return_value=clients):
   result=c.discover('lo')
  self.assertEqual([t['name'] for t in result],['PS3']);self.assertEqual(result[0]['udn'],'')
 def test_no_clients_with_server_offline(self):
  with patch.object(c,'run',return_value=SimpleNamespace(stdout='[]')),patch.object(c,'api',side_effect=OSError('offline')):self.assertEqual(c.discover('lo'),[])
 def test_active_renderer_and_passive_ps3_in_same_scan(self):
  import select,itertools
  sender=MagicMock();listener=MagicMock()
  sender.recvfrom.return_value=(b'HTTP/1.1 200 OK\r\nLOCATION: http://192.168.1.20/desc.xml\r\n\r\n',('192.168.1.20',1900))
  listener.recvfrom.return_value=(b'M-SEARCH * HTTP/1.1\r\nX-AV-Client-Info: mn="PLAYSTATION 3"\r\nST: urn:schemas-upnp-org:device:MediaServer:1\r\n\r\n',('192.168.1.30',1900))
  interfaces=[dict(ifname='eno2',addr_info=[dict(family='inet',local='192.168.1.10')])]
  tv=dict(name='TV',ip='192.168.1.20',udn='uuid:hardware',model='TV',manufacturer='',location='http://192.168.1.20/desc.xml')
  ticks=itertools.count(0,.3)
  with patch.object(c,'run',return_value=SimpleNamespace(stdout=json.dumps(interfaces))),patch.object(c.socket,'socket',side_effect=[sender,listener]),patch.object(select,'select',return_value=([sender,listener],[],[])),patch.object(c.time,'monotonic',side_effect=lambda:next(ticks)),patch.object(c,'describe',return_value=tv),patch.object(c,'api',return_value={'renderers':[]}):
   result=c.discover('eno2')
  self.assertEqual({t['name'] for t in result},{'TV','PlayStation 3'})
  self.assertTrue(any(b'ST: ssdp:all' in call.args[0] for call in sender.sendto.call_args_list))
  self.assertTrue(any(b'ST: urn:schemas-upnp-org:device:MediaRenderer:1' in call.args[0] for call in sender.sendto.call_args_list))
  sender.close.assert_called_once();listener.close.assert_called_once()
 def test_local_ums_client_excluded_after_multicast_failure(self):
  interfaces=[dict(ifname='eno2',addr_info=[dict(family='inet',local='192.168.1.10')])]
  clients=dict(renderers=[dict(name='UnknownRenderer',address='/192.168.1.10',isActive=True,uuid='generated'),dict(name='PS3',address='/192.168.1.30',isActive=True)])
  with patch.object(c,'run',return_value=SimpleNamespace(stdout=json.dumps(interfaces))),patch.object(socket,'socket',side_effect=OSError('offline')),patch.object(c,'api',return_value=clients):
   result=c.discover('eno2')
  self.assertEqual([t['ip'] for t in result],['192.168.1.30']);self.assertEqual(result[0]['source'],'ums');self.assertEqual(result[0]['udn'],'')
 def test_local_renderer_and_media_server_excluded_before_http(self):
  import select,itertools,io
  own='192.168.1.10';interfaces=[dict(ifname='eno2',addr_info=[dict(family='inet',local=own)])]
  sender=MagicMock();listener=MagicMock()
  sender.recvfrom.return_value=(b'HTTP/1.1 200 OK\r\nLOCATION: http://192.168.1.10:5001/desc\r\n\r\n',(own,1900))
  listener.recvfrom.return_value=(b'HTTP/1.1 200 OK\r\nLOCATION: http://192.168.1.10:49152/desc\r\n\r\n',(own,1900))
  def response(url,timeout):
   kind='MediaServer' if ':5001/' in url else 'MediaRenderer'
   return io.BytesIO(('<root xmlns="urn:schemas-upnp-org:device-1-0"><device><deviceType>urn:schemas-upnp-org:device:'+kind+':1</deviceType><friendlyName>'+kind+'</friendlyName></device></root>').encode())
  opener=MagicMock();opener.open.side_effect=response;ticks=itertools.count(0,.3)
  with patch.object(c,'run',return_value=SimpleNamespace(stdout=json.dumps(interfaces))),patch.object(c.socket,'socket',side_effect=[sender,listener]),patch.object(select,'select',return_value=([sender,listener],[],[])),patch.object(c.time,'monotonic',side_effect=lambda:next(ticks)),patch.object(c.urllib.request,'build_opener',return_value=opener),patch.object(c,'api',return_value={'renderers':[]}):
   result=c.discover('eno2',extra_urls=('http://192.168.1.10:49152/desc',))
  self.assertEqual(result,[]);opener.open.assert_not_called()
if __name__=='__main__':unittest.main()
