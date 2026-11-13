#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic real DLNA test. Only disposable profiles/media and separate ports.

Never calls systemctl, apply(), or the installed runtime. No TV is required.
"""
import argparse,hashlib,http.client,json,os,shutil,signal,socket,subprocess,sys,tarfile,tempfile,time,urllib.parse,urllib.request,uuid
from pathlib import Path
import xml.etree.ElementTree as E
from xml.sax.saxutils import escape
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import baul_core as c
import native_dependencies as native
NS={'d':'urn:schemas-upnp-org:device-1-0','dc':'http://purl.org/dc/elements/1.1/','l':'urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/'}
def request(ip,method,url,body=None,headers=None):
 u=urllib.parse.urlsplit(url);connection=http.client.HTTPConnection(u.hostname,u.port,timeout=20,source_address=(ip,0))
 try:
  connection.request(method,u.path+('?' +u.query if u.query else ''),body,headers or {});response=connection.getresponse();return response.status,dict(response.getheaders()),response.read(32*1024*1024)
 finally:connection.close()
def browse(ip,endpoint,obj='0',start=0,count=40):
 fields=dict(ObjectID=obj,BrowseFlag='BrowseDirectChildren',Filter='*',StartingIndex=start,RequestedCount=count,SortCriteria='')
 body=('<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body><u:Browse xmlns:u="urn:schemas-upnp-org:service:ContentDirectory:1">'+''.join('<'+k+'>'+escape(str(v))+'</'+k+'>' for k,v in fields.items())+'</u:Browse></s:Body></s:Envelope>').encode()
 status,_,data=request(ip,'POST',endpoint,body,{'Content-Type':'text/xml; charset="utf-8"','SOAPAction':'"urn:schemas-upnp-org:service:ContentDirectory:1#Browse"'})
 assert status==200,(status,data[:400]);tree=E.fromstring(data);result=next(x.text for x in tree.iter() if x.tag.endswith('Result'))
 return [dict(id=x.get('id'),title=x.findtext('dc:title','',NS),urls=[a.text for a in x.findall('l:res',NS)],protocols=[a.get('protocolInfo') for a in x.findall('l:res',NS)]) for x in E.fromstring(result)]
def search(ip,endpoint):
 fields=dict(ContainerID='0',SearchCriteria='upnp:class derivedfrom "object.item.videoItem"',Filter='*',StartingIndex=0,RequestedCount=0,SortCriteria='')
 body=('<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body><u:Search xmlns:u="urn:schemas-upnp-org:service:ContentDirectory:1">'+''.join('<'+k+'>'+escape(str(v))+'</'+k+'>' for k,v in fields.items())+'</u:Search></s:Body></s:Envelope>').encode()
 status,_,data=request(ip,'POST',endpoint,body,{'Content-Type':'text/xml; charset="utf-8"','SOAPAction':'"urn:schemas-upnp-org:service:ContentDirectory:1#Search"'})
 assert status==200,(status,data[:400]);tree=E.fromstring(data);return int(next(x.text for x in tree.iter() if x.tag.endswith('TotalMatches')))
def port():
 with socket.socket() as sock:sock.bind(('0.0.0.0',0));return sock.getsockname()[1]
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'.cache/integration.json');parser.add_argument('--mode',choices=['direct','force','auto'],default='direct');parser.add_argument('--subtitles',choices=['burn','passthrough'],default='burn');args=parser.parse_args()
 spec=json.loads((ROOT/'server-support/upstream.json').read_text(encoding='utf-8'));archive=native.fetch(spec['runtime'],ROOT/'.cache');packages=native.packages(ROOT/'.cache/upstream')
 interfaces=json.loads(subprocess.check_output(['ip','-j','-4','addr','show'],text=True))
 addresses=[(item['ifname'],a['local']) for item in interfaces for a in item.get('addr_info',[]) if a.get('scope')=='global']
 if not addresses:raise RuntimeError('A non-loopback IPv4 interface is required for the isolated DLNA listener')
 interface,primary=addresses[0];secondary='127.0.0.2';unknown='127.0.0.3';checks=[]
 def passed(name):checks.append(name);print('PASS',name,flush=True)
 with tempfile.TemporaryDirectory(prefix='ums-dlna-integration-') as temp:
  temp=Path(temp);runtime=temp/'ums-15.9.0'
  with tarfile.open(archive) as tf:tf.extractall(temp,filter='data')
  shutil.copy2(ROOT/'server-support/update.jar',runtime/'update.jar')
  for p in packages:subprocess.run(['dpkg-deb','-x',str(p),str(temp/'native')],check=True,capture_output=True)
  libs=temp/'native/usr/lib/x86_64-linux-gnu'
  for n in ['libzen','libmediainfo']:(libs/(n+'.so')).symlink_to(n+'.so.0')
  library=temp/'library';library.mkdir();private=library/'private';private.mkdir();outside=temp/'outside.mkv'
  ffmpeg=runtime/'linux/ffmpeg';source=library/'Episode 001.mkv';subtitles=temp/'test.srt';subtitles.write_text('1\n00:00:00,000 --> 00:00:03,000\nSynthetic subtitle\n', encoding='utf-8')
  subprocess.run([str(ffmpeg),'-v','error','-f','lavfi','-i','testsrc2=size=1280x720:rate=24','-f','lavfi','-i','sine=frequency=440','-f','lavfi','-i','sine=frequency=880','-i',str(subtitles),'-map','0:v','-map','1:a','-map','2:a','-map','3:s','-c:s','srt','-metadata:s:a:0','language=spa','-metadata:s:a:1','language=jpn','-metadata:s:s:0','language=spa','-t','4','-c:v','libx264','-threads','2','-preset','ultrafast','-pix_fmt','yuv420p','-c:a','aac',str(source)],check=True,timeout=40)
  shutil.copy2(source,private/'Private.mkv');shutil.copy2(source,outside);(library/'escape.mkv').symlink_to(outside);original=source.read_bytes()
  c.PROFILE=temp/'profile';c.PROFILE.mkdir();renderers=c.PROFILE/'renderers';renderers.mkdir()
  profiles=[]
  for name,ip,folder in [('Primary',primary,library),('Secondary',secondary,private)]:
   tv=c.default_tv(name,ip);tv.update(mode=args.mode if name=='Primary' else 'direct',subtitles=args.subtitles,folders=[str(folder)],convert_folders=[str(folder)],resolution='480p',bitrate=5);profiles.append(tv)
   (renderers/(name+'.conf')).write_text(c.device_config(tv), encoding='utf-8')
  p1,p2=port(),port()
  while p1==p2:p2=port()
  state=c.defaults();state.update(server_uuid=str(uuid.uuid4()),name='Synthetic UMS verification',interface=interface,tvs=profiles)
  config=c.main_config(state).replace('port = 5001','port = '+str(p1)).replace('web_gui_port = 9001','web_gui_port = '+str(p2))+'hostname = '+primary+'\n'
  (c.PROFILE/'UMS.conf').write_text(config, encoding='utf-8');(c.PROFILE/'SHARED.conf').write_text(c.shared_config(state), encoding='utf-8')
  java=next(runtime.glob('jre*/bin/java'));env=dict(os.environ,LD_LIBRARY_PATH=str(libs),UMS_PROFILE=str(c.PROFILE/'UMS.conf'),PMS_HOME=str(runtime))
  command=[str(java),'-Xmx512M','-Djava.awt.headless=true','--enable-preview','--add-modules','jdk.incubator.vector','--add-opens','java.base/sun.nio.ch=ALL-UNNAMED','-Dfile.encoding=UTF-8','-Djava.net.preferIPv4Stack=true','-Djna.nosys=true','-cp',str(runtime/'update.jar')+':'+str(runtime/'ums.jar'),'net.pms.PMS','console']
  with (temp/'server.log').open('w+') as log:
   proc=subprocess.Popen(command,cwd=runtime,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   try:
    location=f'http://{primary}:{p1}/dev/{state["server_uuid"]}/desc';deadline=time.monotonic()+55
    while True:
     if proc.poll() is not None:raise RuntimeError('Isolated server exited')
     try:
      status,_,body=request(primary,'GET',location)
      if status==200 and b'ContentDirectory' in body:break
     except OSError:pass
     if time.monotonic()>deadline:raise RuntimeError('Isolated listener timed out')
     time.sleep(.3)
    service=next(x for x in E.fromstring(body).findall('.//d:service',NS) if 'ContentDirectory' in x.findtext('d:serviceType','',NS));endpoint=urllib.parse.urljoin(location,service.findtext('d:controlURL','',NS));passed('real-server-separate-ports')
    roots=browse(primary,endpoint);root=next(x for x in roots if x['title']=='library');items=browse(primary,endpoint,root['id'])
    if args.mode=='direct':video=next(x for x in items if any(':video/' in p for p in x['protocols']))
    else:
     assert not any(any(':video/' in p for p in x['protocols']) for x in items),items
     transcode=next(x for x in items if 'transcod' in x['title'].lower());episodes=browse(primary,endpoint,transcode['id']);variants=browse(primary,endpoint,episodes[0]['id'])
     video=next(x for x in variants if 'transcod' in x['title'].lower() and 'ffmpeg' not in x['title'].lower())
     converted=next(x for x in variants if x['urls'] and x['id']!=video['id'])
     status,_,data=request(primary,'GET',converted['urls'][0],headers={'Range':'bytes=0-1048575'});assert status==206 and data,(status,len(data))
     sample=temp/'converted.bin';sample.write_bytes(data);streams=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(sample)],text=True))['streams'];height=next(x['height'] for x in streams if x['codec_type']=='video');assert height<=480,height
     if args.subtitles=='passthrough':assert len([x for x in streams if x['codec_type']=='audio'])==2,streams
     passed('converted-only-in-transcode-480p-'+args.subtitles)
    assert not any('escape' in x['title'] for x in items);passed('external-symlink-hidden')
    for method,rng,expected in [('GET','bytes=0-154',original[:155]),('GET','bytes=10000-14095',original[10000:14096]),('HEAD','bytes=0-154',b'')]:
     status,_,body=request(primary,method,video['urls'][0],headers={'Range':rng});assert status==206 and body==expected,(method,status,len(body))
    passed('get-head-initial-and-noninitial-ranges')
    status,_,body=request(primary,'GET',video['urls'][0]);assert status==200 and hashlib.sha256(body).digest()==hashlib.sha256(original).digest();passed('full-original-byte-identical')
    other=browse(secondary,endpoint);assert [x['title'] for x in other]==['private'],other;passed('independent-device-folders')
    browse(secondary,endpoint,other[0]['id'])
    deadline=time.monotonic()+12
    while search(secondary,endpoint)!=1 and time.monotonic()<deadline:time.sleep(.3)
    assert search(secondary,endpoint)==1
    assert search(unknown,endpoint)==0
    if args.mode!='direct':assert search(primary,endpoint)==0
    passed('search-excludes-unshared-and-hidden-exterior-videos')
    assert not browse(unknown,endpoint);status,_,_=request(secondary,'GET',video['urls'][0]);assert status in [401,403,404],status;passed('unknown-client-and-cross-profile-url-denied')
    for start in range(len(items)):
     page=browse(primary,endpoint,root['id'],start,1);assert [x['id'] for x in page]==[items[start]['id']]
    passed('browse-pagination')
   except BaseException:
    log.flush();log.seek(0);args.output.parent.mkdir(parents=True,exist_ok=True);args.output.with_suffix('.failed.log').write_text(log.read()[-12000:], encoding='utf-8');raise
   finally:
    if proc.poll() is None:
     os.killpg(proc.pid,signal.SIGTERM)
     try:proc.wait(12)
     except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(dict(passed=True,checks=checks,mode=args.mode,subtitles=args.subtitles,synthetic_only=True,production_not_accessed=True),indent=2)+'\n', encoding='utf-8');print('Integration passed:',len(checks),'groups')
if __name__=='__main__':main()
