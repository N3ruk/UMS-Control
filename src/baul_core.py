# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 N3ruk
"""Adapter for the managed Universal Media Server runtime. No shell, Samba or media mutations."""
from __future__ import annotations
import concurrent.futures, copy, ipaddress, json, os, re, socket, subprocess, tempfile, time, uuid
from pathlib import Path, PureWindowsPath
import urllib.parse, urllib.request
from configuration import ConfigurationError, read_object
import xml.etree.ElementTree as ET
import platform_support as platform_os
import platform_support as fcntl
HOME = Path.home()
CONFIG, PROFILE, DATA = platform_os.home_paths(HOME)
def discover_runtime():
    """Stable managed path, or one unambiguous legacy installation of any version."""
    if (DATA/'runtime').is_dir():return DATA/'runtime'
    legacy=[p for p in DATA.glob('ums-*') if p.is_dir() and re.fullmatch(r'ums-\d+(?:\.\d+)+',p.name)]
    return legacy[0] if len(legacy)==1 else DATA/'runtime'

RUNTIME = discover_runtime()
SERVICE = 'baul-ums.service'
MODES = {'direct','force','auto'}
CONTAINERS = {'auto','mkv','mpegts','mpegps','mp4'}
PRESETS = {'compatible','native'}
TARGETS = {'MPEGTS-H264-AC3','MPEGTS-H264-AAC','MPEGPS-MPEG2-AC3'}
RESOLUTIONS = {'original':(0,0),'1080p':(1920,1080),'720p':(1280,720),'480p':(854,480),'1440p':(2560,1440),'2160p':(3840,2160)}

def run(args, timeout=40, check=True):
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, env=platform_os.clean_environment(), **(dict(creationflags=subprocess.CREATE_NO_WINDOW) if platform_os.WINDOWS else {}))
    if check and r.returncode:
        raise RuntimeError((r.stderr or r.stdout or f'Error {r.returncode}: {args[0]}').strip()[-2500:])
    return r

def atomic_write(path, text, encoding="utf-8"):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fd,name = tempfile.mkstemp(prefix='.'+path.name,dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding=encoding) as f:
            f.write(text); f.flush(); os.fsync(f.fileno())
        os.chmod(name,0o600); os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)

def default_tv(name='Nuevo dispositivo',ip='',udn=''):
    return dict(folders=[],convert_folders=[],id=uuid.uuid4().hex,name=name,ip=ip,udn=udn,mode='force',container='auto',preset='compatible',resolution='1080p',bitrate=25,target='MPEGTS-H264-AC3',channels=2,subtitles='burn',audio_languages='spa,esp,eng,und',subtitle_languages='spa,esp,eng,und',encoder='cpu',show_transcode_folder=True,resume=False)

def tv_value(tv, key):
    # Legacy profiles retain exactly the previous effective settings.
    fallback = {'resume':tv.get('show_transcode_folder',True), 'external_subtitles':True, 'audio_bitrate':448, 'container':'auto', 'name_mode':'original', 'name_folders':[], 'name_exclusions':[], 'convert_exclusions':[]}
    return tv.get(key, fallback.get(key))

def editable_tv(tv):
    """Explicit form migration; never writes or applies a saved profile on open."""
    result = copy.deepcopy(tv)
    result['mode'] = tv['mode'] if tv['mode'] in MODES else 'force'
    result['container'] = tv_value(tv,'container')
    for key in ['name_mode','name_folders','name_exclusions','convert_exclusions']:
        result[key] = copy.deepcopy(tv_value(tv,key))
    result['subtitles'] = 'burn' if tv['subtitles'] in {'auto','burn'} else 'passthrough'
    result['preset'] = 'compatible'
    result['show_transcode_folder'] = result['mode'] != 'direct'
    result['resume'] = False
    return result


def network_interfaces(sys_root=Path('/sys/class/net')):
    """Identify actual wireless/physical Ethernet devices, not every ether-like link."""
    if platform_os.WINDOWS:return platform_os.networks()
    result=[];counts={}
    for _,name in sorted(socket.if_nameindex(),key=lambda item:item[1]):
        if name=='lo':continue
        path=sys_root/name
        if (path/'wireless').exists() or (path/'phy80211').exists():kind='wifi'
        else:
            try:is_ethernet=(path/'type').read_text(encoding='utf-8').strip()=='1' and (path/'device').exists()
            except OSError:is_ethernet=False
            kind='ethernet' if is_ethernet else 'other'
        counts[kind]=counts.get(kind,0)+1
        try:up=(path/'operstate').read_text(encoding='utf-8').strip()=='up'
        except OSError:up=False
        result.append(dict(name=name,kind=kind,number=counts[kind],up=up))
    return result

def default_interface():
    interfaces=network_interfaces();available={item['name'] for item in interfaces}
    if platform_os.WINDOWS:
        return next((i['name'] for i in interfaces if i.get('up')),interfaces[0]['name'] if interfaces else '')
    try:
        routes=json.loads(run(['ip','-j','-4','route','show','default'],check=False,timeout=4).stdout)
        for route in sorted(routes,key=lambda item:item.get('metric',0)):
            if route.get('dev') in available:return route['dev']
    except (OSError,ValueError,subprocess.SubprocessError):pass
    for item in interfaces:
        if item['up'] and item['kind']!='other':return item['name']
    return interfaces[0]['name'] if interfaces else ''

def defaults():
    return dict(version=2,name='UMS Control',interface=default_interface(),tvs=[])

def load_state():
    p=CONFIG/'settings.json'
    try:
        state=read_object(p,defaults)
        validate_state_structure(state)
        return migrate_state(state)
    except (ValueError,TypeError,KeyError) as error:
        if isinstance(error,ConfigurationError):raise
        raise ConfigurationError(p,str(error)) from error

def validate_state_structure(state):
    """Validate saved data without requiring connected disks or an available NIC."""
    if type(state.get('version',1)) is not int or state.get('version',1) not in {1,2}:
        raise ValueError('Versión de configuración no compatible.')
    if not all(isinstance(state.get(k),str) for k in ['name','interface']) or not isinstance(state.get('tvs'),list):
        raise ValueError('Estructura de configuración no válida.')
    if 'server_uuid' in state and not isinstance(state['server_uuid'],str):raise ValueError('UUID no válido.')
    if state.get('version',1)==1 and not isinstance(state.get('folders',[]),list):raise ValueError('Lista de carpetas no válida.')
    for tv in state['tvs']:
        if not isinstance(tv,dict):raise ValueError('Perfil de dispositivo no válido.')
        for key in ['id','name','ip','udn','mode','preset','resolution','target','subtitles','audio_languages','subtitle_languages','encoder']:
            if not isinstance(tv.get(key),str):raise ValueError('Campo de perfil no válido: '+key)
        for key in ['bitrate','channels']:
            if type(tv.get(key)) is not int:raise ValueError('Campo numérico no válido: '+key)
        for key in ['folders','convert_folders','convert_exclusions','name_folders','name_exclusions']:
            if key not in tv and (key not in {'folders','convert_folders'} or state.get('version',1)==1):continue
            if not isinstance(tv.get(key),list) or not all(isinstance(v,str) for v in tv[key]):raise ValueError('Lista de carpetas no válida: '+key)
        for key in ['show_transcode_folder','resume','external_subtitles']:
            if key in tv and type(tv[key]) is not bool:raise ValueError('Opción de perfil no válida: '+key)
        if 'container' in tv and tv['container'] not in CONTAINERS:raise ValueError('Contenedor no válido.')
        if 'name_mode' in tv and tv['name_mode'] not in {'original','compatible','selected'}:raise ValueError('Modo de nombres no válido.')
        if 'audio_bitrate' in tv and type(tv['audio_bitrate']) is not int:raise ValueError('Calidad de audio no válida.')
        if tv['resolution'] not in RESOLUTIONS or tv['target'] not in TARGETS or tv['encoder'] not in {'cpu','nvidia'}:raise ValueError('Ajuste de conversión no válido.')
        if tv['subtitles'] not in {'auto','off','burn','passthrough'}:raise ValueError('Subtítulos no válidos.')
    return state

def migrate_state(state):
    """In-memory schema transition; existing device behavior is preserved."""
    result=copy.deepcopy(state)
    if result.get('version',1)<2:
        folders=result.pop('folders',[])
        for device in result['tvs']:
            device['folders']=copy.deepcopy(folders)
            device['convert_folders']=copy.deepcopy(folders) if device['mode']!='direct' else []
        result['version']=2
    for device in result['tvs']:
        device.setdefault('container','auto')
        for key in ['name_mode','name_folders','name_exclusions','convert_exclusions']:
            device.setdefault(key,copy.deepcopy(tv_value(device,key)))
    return result

def shared_folders(state):
    return list(dict.fromkeys(f for device in state['tvs'] for f in device['folders']))

def _same_folder_list(actual,expected):
    if platform_os.WINDOWS:
        return [PureWindowsPath(f) for f in actual]==[PureWindowsPath(f) for f in expected]
    return actual==expected

def validate_folders(folders):
    if not isinstance(folders,list):raise ValueError('Lista de carpetas no válida.')
    paths=[]
    for folder in folders:
        if not valid_line(folder) or not Path(folder).is_absolute():raise ValueError('Usa rutas absolutas válidas.')
        if Path(folder).exists() and not Path(folder).is_dir():raise ValueError('No es una carpeta: '+folder)
        path=Path(folder).resolve()
        if any(path==other or path in other.parents or other in path.parents for other in paths):
            raise ValueError('No añadas carpetas duplicadas ni subcarpetas ya incluidas en este dispositivo.')
        paths.append(path)
    return folders

def rule_enabled(path, included, excluded):
    """Most specific directory wins; paths are canonical and segment-aware."""
    target=Path(path).resolve();matches=[]
    for value,paths in [(True,included),(False,excluded)]:
        for entry in paths:
            root=Path(entry).resolve()
            if target==root or root in target.parents:matches.append((len(root.parts),value))
    return max(matches,default=(0,False))[1]

def validate_folder_rules(shared,included,excluded):
    if not isinstance(included,list) or not isinstance(excluded,list):raise ValueError('Lista de carpetas no válida.')
    roots=[Path(f).resolve() for f in shared];seen=set()
    for folder in included+excluded:
        if not valid_line(folder) or not Path(folder).is_absolute():raise ValueError('Usa rutas absolutas válidas.')
        target=Path(folder).resolve()
        if target in seen:raise ValueError('Reglas de carpeta duplicadas o contradictorias.')
        seen.add(target)
        if not any(target==root or root in target.parents for root in roots):
            raise ValueError('Las reglas solo pueden aplicarse dentro de las carpetas compartidas con este dispositivo.')
        if target.exists() and not target.is_dir():raise ValueError('No es una carpeta: '+folder)
    return included,excluded

def valid_line(v):
    return isinstance(v,str) and not any(c in v for c in '\r\n\x00')

def validate(state):
    if not valid_line(state['name']) or not state['name'].strip(): raise ValueError('Nombre de servidor no válido.')
    if state['interface'] not in ([n['name'] for n in network_interfaces()] if platform_os.WINDOWS else [n for _,n in socket.if_nameindex()]): raise ValueError('Selecciona una interfaz de red disponible.')
    if state.get('version')!=2 or 'folders' in state:raise ValueError('Configuración de dispositivos no válida.')
    ids,addresses,udns=set(),set(),set()
    for tv in state['tvs']:
        validate_folders(tv['folders'])
        validate_folder_rules(tv['folders'],tv['convert_folders'],tv_value(tv,'convert_exclusions'))
        validate_folder_rules(tv['folders'],tv_value(tv,'name_folders'),tv_value(tv,'name_exclusions'))
        if tv_value(tv,'name_mode') not in {'original','compatible','selected'}:raise ValueError('Modo de nombres no válido.')
        if not re.fullmatch('[a-f0-9]{32}',tv['id']) or tv['id'] in ids: raise ValueError('Identificador de perfil inválido o repetido.')
        ids.add(tv['id'])
        if not valid_line(tv['name']) or not tv['name'].strip(): raise ValueError('Pon un nombre válido a cada dispositivo.')
        if tv['ip']:
            ip=ipaddress.ip_address(tv['ip'])
            if ip.version!=4 or not ip.is_private or ip.is_loopback or ip.is_multicast or ip.is_unspecified: raise ValueError('Usa la IPv4 local del dispositivo.')
            if str(ip) in addresses: raise ValueError('Dos perfiles no pueden tener la misma IP.')
            addresses.add(str(ip))
        if tv['udn']:
            if not re.fullmatch(r'uuid:[a-zA-Z0-9_-]+',tv['udn']): raise ValueError('UUID de dispositivo no válido.')
            if tv['udn'] in udns: raise ValueError('Dos perfiles no pueden tener el mismo UUID.')
            udns.add(tv['udn'])
        if not tv['ip'] and not tv['udn']: raise ValueError('Cada dispositivo necesita una IP local o un UUID detectado.')
        if tv_value(tv,'container') not in CONTAINERS: raise ValueError('Contenedor no válido.')
        if tv_value(tv,'container')=='mpegps' and tv['target']!='MPEGPS-MPEG2-AC3': raise ValueError('MPEG-PS necesita MPEG-2 + AC3.')
        if tv_value(tv,'container')=='mp4' and tv['target']=='MPEGPS-MPEG2-AC3': raise ValueError('MP4 necesita H.264.')
        if tv['mode'] not in MODES or tv['preset'] not in PRESETS or tv['resolution'] not in RESOLUTIONS or tv['target'] not in TARGETS: raise ValueError('Modo de reproducción no válido.')
        for key in ['show_transcode_folder','resume','external_subtitles']:
            value = tv.get(key,True) if key=='show_transcode_folder' else tv_value(tv,key)
            if not isinstance(value,bool): raise ValueError('Opción no válida: '+key)
        if tv_value(tv,'audio_bitrate') not in {128,192,256,384,448,640}: raise ValueError('Calidad de audio no válida.')
        if tv['subtitles'] not in {'burn','passthrough'} or tv['encoder'] not in {'cpu','nvidia'}: raise ValueError('Ajuste de conversión no válido.')
        if type(tv['bitrate']) is not int or (tv['bitrate']!=0 and not 3<=tv['bitrate']<=100) or tv['channels'] not in {2,6}: raise ValueError('Bitrate o canales fuera de rango.')
        for key in ['audio_languages','subtitle_languages']:
            if not re.fullmatch('[a-zA-Z, -]*',tv[key]): raise ValueError('Usa códigos de idioma separados por comas: spa,eng,und.')
    return state

def properties(entries):
    return '\n'.join(f'{k} = '+str(v).replace('\\','\\\\') for k,v in entries)+'\n'

def output_target(tv):
    container=tv_value(tv,'container')
    if container=='auto':
        container='mkv' if tv['subtitles']=='passthrough' else ('mpegps' if tv['target']=='MPEGPS-MPEG2-AC3' else 'mpegts')
    codecs=tv['target'].split('-',1)[1]
    return container.upper()+'-'+codecs

def device_config(tv):
    direct=tv['mode']=='direct'; soft=not direct and tv['subtitles']=='passthrough'
    w,h=(0,0) if direct else RESOLUTIONS[tv['resolution']]
    bitrate=0 if direct else tv['bitrate']
    target=output_target(tv)
    e=[('ums_control_auto',str(tv['mode']=='auto').lower()),('ums_control_container',tv_value(tv,'container')),('ums_control_soft_subtitles',str(soft).lower()),('ums_control_shared_folders',json.dumps(tv['folders'],ensure_ascii=False)),('ums_control_convert_folders',json.dumps(tv['convert_folders'] if not direct else [],ensure_ascii=False)),('ums_control_convert_exclusions',json.dumps(tv_value(tv,'convert_exclusions') if not direct else [],ensure_ascii=False)),('ums_control_name_mode',tv_value(tv,'name_mode')),('ums_control_name_folders',json.dumps(tv_value(tv,'name_folders'),ensure_ascii=False)),('ums_control_name_exclusions',json.dumps(tv_value(tv,'name_exclusions'),ensure_ascii=False)),('Device',', '.join(v for v in [tv['udn'].removeprefix('uuid:'),tv['ip']] if v)),('RendererName',tv['name']),
       ('disable_transcoding',str(tv['mode']=='direct').lower()),('force_transcode_for_extensions','*' if tv['mode']=='force' else ''),
       ('disable_transcode_for_extensions','*' if tv['mode']=='direct' else ''),('TranscodeVideo',target),('TranscodeAudio','MP3'),
       ('MaxVideoWidth',w),('MaxVideoHeight',h),('MaxVideoBitrateMbps',bitrate),('maximum_bitrate',bitrate),
       ('automatic_maximum_bitrate','false'),('audio_channels',tv['channels']),('audio_bitrate',tv_value(tv,'audio_bitrate')),('audio_languages',tv['audio_languages']),
       ('subtitles_languages',tv['subtitle_languages']),('audio_subtitles_languages',''),('disable_subtitles',str(direct or tv['subtitles'] in {'off','passthrough'}).lower()),
       ('autoload_external_subtitles',str(not direct and tv['subtitles']=='burn' and tv_value(tv,'external_subtitles')).lower()),('force_external_subtitles','false'),
       ('ffmpeg_gpu_decoding_acceleration_method','none'),('ffmpeg_gpu_encoding_H264_acceleration_method','h264_nvenc' if tv['encoder']=='nvidia' else 'libx264'),
       ('audio_embed_dts_in_pcm','false'),('encoded_audio_passthrough','false'),('audio_remux_ac3',str(tv['mode']=='auto').lower()),('show_transcode_folder',str(not direct).lower()),('resume','false')]
    if not direct and (tv['preset']=='compatible' or tv['mode']=='force'):
        e += [('MediaInfo','true'),('SupportedVideoBitDepths','8'),('H264LevelLimit','4.1'),('CustomFFmpegOptions','-pix_fmt yuv420p'+(' -preset p4' if tv['encoder']=='nvidia' and tv['target']!='MPEGPS-MPEG2-AC3' else '')),('MimeTypesChanges','video/vnd.dlna.mpeg-tts=video/mpeg|video/mp2t=video/mpeg')]
        # Automatic uses the actual UMS model's Supported list. Unknown models
        # receive a conservative fallback in RendererConfiguration, never f:.+.
        if tv['mode']=='force':
            e += [('Supported','f:mp3 m:audio/mpeg'),('Supported','f:jpg m:image/jpeg'),('Supported','f:png m:image/png')]
    if not direct and tv['subtitles']=='burn': e += [('SupportedInternalSubtitlesFormats',''),('SupportedExternalSubtitlesFormats','')]
    return '# Managed by UMS Control. Per-device settings.\n'+properties(e)

def main_config(s):
    result = '# Managed by UMS Control. Samba is independent.\n'+properties([('ums_control_folder_policy','true'),('uuid',s['server_uuid']),
      ('server_name',s['name']),('language','es'),('network_interface',s['interface']),('port',5001),('web_gui_port',9001),
      ('upnp_cds_write','false'),('fully_played_action',0),('audio_update_rating_tag','false'),('web_gui_on_start','false'),('authentication_enabled','true'),('authenticate_localhost_as_admin','true'),('web_player_enable','false'),
      ('run_wizard','false'),('auto_update','false'),('external_network','false'),('use_api_info','false'),
      ('ffmpeg_mux_tsmuxer_compatible','false'),('engines','FFmpegVideo,FFmpegAudio'),('engines_priority','FFmpegVideo,FFmpegAudio'),('scan_shared_folders_on_startup','false'),
      ('use_cache','true'),('generate_thumbnails','false'),('image_thumbnails','false'),('show_media_library_folder','false'),
      ('show_recently_played_folder','false'),('show_server_settings_folder','false'),('show_transcode_folder','true'),
      ('hide_empty_folders','false'),('audio_languages','spa,esp,eng,und'),('subtitles_languages','spa,esp,eng,und'),
      ('maximum_video_buffer_size',200),('folder_names_ignored','.Trash-1000,$RECYCLE.BIN,＄RECYCLE.BIN,System Volume Information'),
      ('log_level','INFO'),('logging_filter_console','WARN')])
    if platform_os.WINDOWS:
        ips=[a['local'] for i in platform_os.addresses() if i['ifname']==s['interface'] for a in i['addr_info']]
        if not ips:raise RuntimeError('La interfaz seleccionada no tiene IPv4.')
        result=re.sub(r'^network_interface = .*$', 'network_interface = ',result,flags=re.M)
        result+=properties([('hostname',ips[0])])
    controlled={line.split('=',1)[0].strip() for line in result.splitlines() if '=' in line}
    current=PROFILE/'UMS.conf'
    if current.exists():
        for line in current.read_text(encoding='utf-8').splitlines():
            match=re.match(r'^\s*([^#! =:]+)\s*[=:]',line)
            if match and match.group(1) not in controlled: result+=line+'\n'
    return result

def shared_config(s):
    return json.dumps([dict(type='Folder',file=f,monitored=True,metadata=False,active=True,groups=[]) for f in shared_folders(s)],ensure_ascii=False,indent=2)+'\n'

def active():
    if platform_os.WINDOWS or not platform_os.systemd():
        import portable_service;return portable_service.active()
    return run(['systemctl','--user','is-active',SERVICE],check=False,timeout=4).stdout.strip()

def service(action):
    if action not in {'start','stop','restart','enable','disable'}: raise ValueError('Acción no válida.')
    if platform_os.WINDOWS or not platform_os.systemd():
        import portable_service;return portable_service.control(action)
    run(['systemctl','--user',action,SERVICE],timeout=70)

def autostart():
    if platform_os.WINDOWS or not platform_os.systemd():
        import portable_service;return portable_service.autostart()
    return run(['systemctl','--user','is-enabled',SERVICE],check=False,timeout=4).returncode==0

def server_properties():
    values={}
    path=PROFILE/'UMS.conf'
    if path.is_file():
        for line in path.read_text(encoding='utf-8').splitlines():
            match=re.match(r'^\s*([^#!\s=:]+)\s*[=:]\s*(.*?)\s*$',line)
            if match:values[match[1]]=match[2]
    return values

def server_port(name,default):
    value=server_properties().get(name,str(default))
    if not value.isascii() or not value.isdecimal() or not 0<int(value)<65536:raise ValueError('Puerto del servidor no válido.')
    return int(value)

def web_url():return 'http://127.0.0.1:'+str(server_port('web_gui_port',9001))

def api(path,data=None):
    req=urllib.request.Request(web_url()+'/v1/api/'+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=8) as r: return json.load(r)

def ready(timeout=50):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        try:
            api('shared/')
            values=server_properties();interface=values.get('network_interface') or load_state()['interface']
            interfaces=platform_os.addresses() if platform_os.WINDOWS or not __import__('shutil').which('ip') else json.loads(run(['ip','-j','-4','addr','show','dev',interface]).stdout)
            ips=[a['local'] for i in interfaces if i.get('ifname',interface)==interface for a in i.get('addr_info',[]) if a['family']=='inet']
            if not ips: raise RuntimeError('La interfaz seleccionada no tiene IPv4.')
            identity=str(uuid.UUID(values['uuid']));port=server_port('port',5001)
            location=f"http://{ips[0]}:{port}/dev/{identity}/desc"
            with urllib.request.urlopen(location,timeout=3) as response:
                if response.status==200: return
        except Exception:
            if active() in {'failed','inactive','unknown'}: break
            time.sleep(1)
    raise RuntimeError('UMS no está listo. Revisa el estado en Resumen o abre la administración web de UMS.')

def apply(state,restart=True):
    """Validate first, stop writer, atomic transaction and rollback on failure."""
    state=copy.deepcopy(validate(state)); state.setdefault('server_uuid',str(uuid.uuid4())); CONFIG.mkdir(parents=True,exist_ok=True)
    PROFILE.mkdir(parents=True,exist_ok=True); rd=PROFILE/'renderers'; rd.mkdir(exist_ok=True)
    with (CONFIG/'.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        files={PROFILE/'UMS.conf':main_config(state),PROFILE/'SHARED.conf':shared_config(state),CONFIG/'settings.json':json.dumps(state,ensure_ascii=False,indent=2)+'\n'}
        for tv in state['tvs']: files[rd/('baul-'+tv['id']+'.conf')]=device_config(tv)
        stale=set(rd.glob('baul-*.conf'))-files.keys()
        old={p:p.read_text(encoding='utf-8') if p.exists() else None for p in set(files)|stale}
        was_active=active()=='active'
        if was_active: service('stop')
        try:
            atomic_write(CONFIG/'previous-configuration.json',json.dumps({str(p):v for p,v in old.items()},ensure_ascii=False,indent=2))
            for p,content in files.items(): atomic_write(p,content)
            for p in stale: p.unlink()
            if was_active and restart:
                service('start'); ready()
                got=[x.get('file') for x in api('shared/')['shared_content'] if x.get('type')=='Folder']
                if not _same_folder_list(got,[f for f in shared_folders(state) if Path(f).is_dir()]): raise RuntimeError('UMS no confirmó las carpetas configuradas.')
        except Exception:
            service('stop')
            for p,content in old.items():
                if content is None: p.unlink(missing_ok=True)
                else: atomic_write(p,content)
            if was_active: service('start')
            raise

def local_url(url):
    p=urllib.parse.urlparse(url)
    if p.scheme!='http' or p.username or p.password or not p.hostname: return False
    try:
        ip=ipaddress.ip_address(p.hostname)
        return ip.version==4 and ip.is_private and not ip.is_loopback and not ip.is_multicast and not ip.is_unspecified
    except ValueError: return False

def describe(url):
    if not local_url(url): return None
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs): return None
    with urllib.request.build_opener(NoRedirect).open(url,timeout=2) as r: data=r.read(131073)
    if len(data)>131072 or b'<!DOCTYPE' in data.upper(): return None
    root=ET.fromstring(data); ns={'d':'urn:schemas-upnp-org:device-1-0'}
    for dev in root.findall('.//d:device',ns):
        if 'MediaRenderer' in dev.findtext('d:deviceType','',ns):
            return dict(name=dev.findtext('d:friendlyName','Dispositivo DLNA',ns),manufacturer=dev.findtext('d:manufacturer','',ns),model=dev.findtext('d:modelName','',ns),udn=dev.findtext('d:UDN','',ns),ip=urllib.parse.urlparse(url).hostname,location=url)
    return None

def discovery_identity(headers, address):
    """Only recognize identifiable DLNA clients; an arbitrary M-SEARCH is not a TV."""
    signature=' '.join(headers.get(k,'') for k in ('user-agent','x-av-client-info','server'))
    if re.search(r'PLAYSTATION\s*3',signature,re.I):
        return dict(name='PlayStation 3',manufacturer='Sony',model='PlayStation 3',udn='',ip=address,location='',source='ssdp-client')
    return None

def merge_discovered(items, own_ips=()):
    result=[]
    for raw in items:
        item=dict(raw)
        if not local_url('http://'+str(item.get('ip',''))):continue
        if item.get('ip') in own_ips:continue
        # UMS may generate a UUID from an IP: never use it as a hardware identity.
        if item.get('source')=='ums':item['udn']=''
        udn=item.get('udn','')
        if not re.fullmatch(r'uuid:[a-zA-Z0-9_-]+',udn):item['udn']=''
        previous=next((x for x in result if x['ip']==item['ip'] or (item['udn'] and x['udn']==item['udn'])),None)
        if previous:
            if not previous['udn'] and item['udn']:previous['udn']=item['udn']
            if item.get('source')=='ssdp-client' or previous.get('name') in {'UnknownRenderer','Dispositivo DLNA'}:
                previous.update({k:item[k] for k in ('name','model','manufacturer')})
            continue
        result.append(item)
    return result

def discover(interface=None,extra_urls=()):
    """Six-second SSDP scan plus bounded parallel descriptions and UMS recognition."""
    import select
    interface=interface or default_interface()
    all_interfaces=platform_os.addresses() if platform_os.WINDOWS or not __import__('shutil').which('ip') else json.loads(run(['ip','-j','-4','addr','show'],timeout=4).stdout)
    own_ips={a['local'] for i in all_interfaces for a in i.get('addr_info',[]) if a['family']=='inet'}
    ips=[a['local'] for i in all_interfaces if i.get('ifname')==interface for a in i.get('addr_info',[]) if a['family']=='inet']
    locations=set(extra_urls);observed=[];sockets=[]
    try:
        if ips:
            sender=socket.socket(socket.AF_INET,socket.SOCK_DGRAM,socket.IPPROTO_UDP);sockets.append(sender)
            sender.setsockopt(socket.IPPROTO_IP,socket.IP_MULTICAST_IF,socket.inet_aton(ips[0]));sender.setsockopt(socket.IPPROTO_IP,socket.IP_MULTICAST_TTL,2);sender.bind((ips[0],0))
            listener=socket.socket(socket.AF_INET,socket.SOCK_DGRAM,socket.IPPROTO_UDP)
            try:
                listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);listener.bind(('',1900))
                listener.setsockopt(socket.IPPROTO_IP,socket.IP_ADD_MEMBERSHIP,socket.inet_aton('239.255.255.250')+socket.inet_aton(ips[0]));sockets.append(listener)
            except OSError:listener.close()  # UMS recognition remains available if multicast port is exclusive.
            end=time.monotonic()+6;next_search=0
            while time.monotonic()<end:
                if time.monotonic()>=next_search:
                    for st in ('urn:schemas-upnp-org:device:MediaRenderer:1','ssdp:all'):
                        msg=('M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: "ssdp:discover"\r\nMX: 2\r\nST: '+st+'\r\n\r\n').encode()
                        sender.sendto(msg,('239.255.255.250',1900))
                    next_search=time.monotonic()+3
                for sock in select.select(sockets,[],[],min(.25,max(0,end-time.monotonic())))[0]:
                    response,peer=sock.recvfrom(16384)
                    if peer[0] in own_ips:continue
                    headers={line.split(':',1)[0].strip().lower():line.split(':',1)[1].strip() for line in response.decode(errors='replace').splitlines()[1:] if ':' in line}
                    location=headers.get('location','')
                    if len(locations)<64 and local_url(location) and urllib.parse.urlparse(location).hostname==peer[0]:locations.add(location)
                    item=discovery_identity(headers,peer[0])
                    if item and len(observed)<256:observed.append(item)
    except OSError:
        pass  # Disconnected multicast must not suppress known UMS clients.
    finally:
        for sock in sockets:sock.close()
    def safely(url):
        if urllib.parse.urlparse(url).hostname in own_ips:return None
        try:
            item=describe(url)
            if item:item['source']='ssdp'
            return item
        except (OSError,ValueError,ET.ParseError):return None
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        found=[x for x in pool.map(safely,sorted(locations)[:64]) if x]
    try:
        for client in api('renderers/').get('renderers',[]):
            if not client.get('isActive'):continue
            address=client.get('address','').lstrip('/')
            name=client.get('name') or 'Dispositivo DLNA'
            found.append(dict(name=name,manufacturer='',model=name,udn='',ip=address,location='',source='ums'))
    except (OSError,ValueError,RuntimeError):pass
    return merge_discovered(observed+found,own_ips)

def probe(path):
    if not Path(path).is_file(): raise ValueError('Selecciona un archivo de vídeo existente.')
    r=run([str(RUNTIME/('bin/ffprobe.exe' if platform_os.WINDOWS else 'linux/ffprobe')),'-v','error','-show_entries','format=format_name,duration,size:stream=index,codec_name,codec_type,profile,pix_fmt,width,height,channels:stream_tags=language','-of','json',str(path)],timeout=30)
    return json.loads(r.stdout)

def diagnostics():
    result=dict(service=active(),autostart=autostart())
    try: result['renderers']=api('renderers/')
    except Exception as e: result['api_error']=str(e)
    result['activity']=live_activity()
    try:
        p=PROFILE/'debug.log'
        with p.open('rb') as f:
            f.seek(max(0,p.stat().st_size-22000));result['ums_log']=f.read().decode(errors='replace')[-16000:]
    except OSError: pass
    if platform_os.WINDOWS or not platform_os.systemd():
        log=PROFILE/'console.log'
        if log.exists():
            with log.open('rb') as stream:stream.seek(max(0,log.stat().st_size-14000));result['log']=stream.read().decode('utf-8',errors='replace')
        return result
    result['log']=run(['journalctl','--user','-u',SERVICE,'-n','55','--no-pager','-o','cat'],check=False).stdout[-14000:]
    return result

def transcode_sample(path,tv):
    """Bounded local encode test, not a claim of physical device playback."""
    info=probe(path); direct=tv['mode']=='direct'; soft=not direct and tv['subtitles']=='passthrough'
    w,h=(0,0) if direct else RESOLUTIONS[tv['resolution']]
    bitrate=0 if direct else tv['bitrate']
    target=output_target(tv); w=w or 3840; h=h or 2160
    encoder='h264_nvenc' if tv['encoder']=='nvidia' else 'libx264'
    if tv['target']=='MPEGPS-MPEG2-AC3': encoder='mpeg2video'
    audio='aac' if tv['target']=='MPEGTS-H264-AAC' else 'ac3'
    with tempfile.TemporaryDirectory(prefix='baul-probe-') as temp:
        dest=Path(temp)/('sample.mpg' if encoder=='mpeg2video' else 'sample.ts')
        args=[str(platform_os.ffmpeg(RUNTIME)),'-hide_banner','-nostdin','-v','error','-threads','4','-i',str(path),'-t','8','-map','0:v:0','-map','0:a:0?','-sn','-dn','-vf',f'scale=w={w}:h={h}:force_original_aspect_ratio=decrease:force_divisible_by=2,format=yuv420p','-c:v',encoder]
        if encoder=='libx264': args+=['-preset','veryfast','-crf','22','-threads','4']
        elif encoder=='mpeg2video': args+=['-q:v','3']
        elif bitrate==0: args+=['-rc','vbr','-cq','22','-b:v','0']
        if bitrate: args+=['-maxrate',str(bitrate)+'M','-bufsize',str(bitrate*2)+'M']
        args+=['-c:a',audio,'-b:a','192k','-ac',str(tv['channels']),'-ar','48000','-f',{'MKV':'matroska','MP4':'mp4','MPEGTS':'mpegts','MPEGPS':'mpeg'}[target.split('-',1)[0]],str(dest)]
        start=time.monotonic();run(args,timeout=150);elapsed=time.monotonic()-start;output=probe(dest)
        return dict(test='Conversión local de los primeros 8 s, sin subtítulos. No verifica la reproducción en el dispositivo ni sustituye una prueba DLNA.',profile=tv['name'],encoder=encoder,seconds=round(elapsed,2),approx_speed=round(8/elapsed,2),result=output)


def device_display_name(renderer, profiles):
    """Match the engine: saved UUID first, then an unambiguous explicit peer IP.

    UPnP identifiers may change across TV restarts. This display-only lookup
    neither edits saved identities nor grants access to media.
    """
    def identity(value):
        return (value or '').strip().lower().removeprefix('uuid:')
    remote_id=identity(renderer.get('uuid'))
    matches=[p for p in profiles if remote_id and identity(p.get('udn'))==remote_id]
    if not matches:
        address=renderer.get('address','').strip().lstrip('/')
        matches=[p for p in profiles if address and p.get('ip','').strip()==address]
    if len(matches)==1 and matches[0].get('name','').strip():
        return matches[0]['name'].strip()
    return renderer.get('name') or ''


def live_activity():
    """Only ffmpeg descendants of our UMS unit, not other user applications."""
    if platform_os.WINDOWS or not platform_os.systemd():
        import portable_service;return portable_service.activity()
    main=run(['systemctl','--user','show',SERVICE,'--property=MainPID','--value'],check=False,timeout=4).stdout.strip()
    if not main.isdigit() or main=='0': return []
    rows={}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit(): continue
        try:
            stat=(p/'stat').read_text(encoding='utf-8');parent=int(stat[stat.rfind(')')+2:].split()[1]);rows[int(p.name)]=(parent,p)
        except (OSError,ValueError,IndexError): pass
    children={int(main)}
    while True:
        more={pid for pid,(parent,_) in rows.items() if parent in children}-children
        if not more: break
        children.update(more)
    result=[]
    for pid in children-{int(main)}:
        try:
            args=(rows[pid][1]/'cmdline').read_bytes().decode(errors='replace').split('\x00')
            if Path(args[0]).name!='ffmpeg' or '-i' not in args or not any(k in args for k in ['-c:v','-vcodec']): continue
            def value(*keys):
                for key in keys:
                    if key in args and args.index(key)+1<len(args): return args[args.index(key)+1]
                return 'automático'
            result.append(dict(pid=pid,video=value('-c:v','-vcodec'),audio=value('-c:a','-acodec'),input=Path(value('-i')).name))
        except (OSError,KeyError,IndexError): pass
    return result


def server_log():
    """Bounded readable log for both user-service and portable server backends."""
    if platform_os.systemd():return run(['journalctl','--user','-u',SERVICE,'-n','80','--no-pager'],check=False).stdout
    parts=[]
    for name in ['console.log','debug.log']:
        path=PROFILE/name
        try:
            with path.open('rb') as stream:
                stream.seek(max(0,path.stat().st_size-12000));parts.append(name+'\n'+stream.read().decode('utf-8',errors='replace'))
        except OSError:pass
    return '\n\n'.join(parts)
