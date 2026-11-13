# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 N3ruk
"""Official stable releases, integrity and staged integration compatibility."""
import hashlib,json,os,re,shutil,socket,subprocess,tempfile,time,urllib.error,urllib.request,uuid,zipfile
from pathlib import Path
import baul_core as c
import platform_support as platform_os

LATEST_URL='https://api.github.com/repos/UniversalMediaServer/UniversalMediaServer/releases/latest'
DOWNLOAD_PREFIX='https://github.com/UniversalMediaServer/UniversalMediaServer/releases/download/'
ROOT=Path(__file__).resolve().parent
# Bootstrap recognition only: never selects which release is downloaded.
WINDOWS_JAR_SHA='c84b86cfcfc09852ce979be539775ad4797be983f58ef0e38893638e560190c1'
BOOTSTRAP_JAR_SHA='d4154acba671955a4ccfc793e8c654c0a853eca006dbb4ca8b5825265885ea5c'

def version_tuple(value):
    match=re.fullmatch(r'v?(\d+\.\d+\.\d+(?:\.\d+)?)',str(value))
    if not match:raise ValueError('La versión oficial del servidor no es válida.')
    return tuple(int(n) for n in match[1].split('.'))

def validate_release(data):
    version=str(data['version']);version_tuple(version)
    if version.startswith('v') or not re.fullmatch('[a-f0-9]{64}',str(data['sha256'])):raise ValueError('La descarga oficial no incluye una huella SHA256 válida.')
    tag=str(data['tag']);version_tuple(tag)
    expected_name=f'UMS-Windows-{version}-x86_64.exe' if platform_os.WINDOWS else f'UMS-Linux-{version}-x86_64.tgz'
    if tag.removeprefix('v')!=version or data['url']!=DOWNLOAD_PREFIX+tag+'/'+expected_name:raise ValueError('La dirección de descarga no pertenece a la versión oficial de UMS.')
    if type(data['size']) is not int or not 0<data['size']<2*1024**3:raise ValueError('El tamaño de la descarga oficial no es válido.')
    return dict(version=version,tag=tag,url=data['url'],sha256=data['sha256'],size=data['size'])

def latest_release():
    request=urllib.request.Request(LATEST_URL,headers={'User-Agent':'UMS-Control/1.0','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(request,timeout=15) as response:
        raw=response.read(2*1024**2+1)
    if len(raw)>2*1024**2:raise ValueError('La respuesta de actualizaciones es demasiado grande.')
    data=json.loads(raw)
    if data.get('draft') or data.get('prerelease'):raise ValueError('No se ha recibido una versión estable de UMS.')
    tag=data['tag_name'];version_tuple(tag);version=tag.removeprefix('v')
    name=f'UMS-Windows-{version}-x86_64.exe' if platform_os.WINDOWS else f'UMS-Linux-{version}-x86_64.tgz'
    assets=[a for a in data['assets'] if a.get('name')==name]
    if len(assets)!=1:raise ValueError('No hay una descarga Linux x86_64 disponible para la última versión.')
    asset=assets[0];checksum=asset.get('digest') or ''
    if not checksum.startswith('sha256:'):raise ValueError('La descarga oficial no incluye una huella SHA256 válida.')
    return validate_release(dict(version=version,tag=tag,url=asset['browser_download_url'],sha256=checksum[7:],size=asset['size']))

def jar_version(runtime):
    try:
        with zipfile.ZipFile(Path(runtime)/'ums.jar') as jar:
            text=jar.read('META-INF/MANIFEST.MF').decode('utf-8')
    except (zipfile.BadZipFile,KeyError) as error:raise ValueError('No se puede identificar la versión instalada del servidor.') from error
    match=re.search(r'^Implementation-Version: (\S+)',text,re.M)
    if not match:raise ValueError('No se puede identificar la versión instalada del servidor.')
    version=match[1];version_tuple(version);return version

def check_update():
    try:
        release=latest_release();installed=jar_version(c.RUNTIME) if (c.RUNTIME/'ums.jar').is_file() else None
        return dict(available=bool(installed and version_tuple(release['version'])>version_tuple(installed)),release=release,installed=installed,error=None)
    except (OSError,ValueError,KeyError,zipfile.BadZipFile) as error:
        return dict(available=False,release=None,installed=None,error=str(error))

def java_path(runtime):
    return platform_os.java(runtime)

def source_digest():
    sha=hashlib.sha256()
    for path in sorted((ROOT/'patches/net').rglob('*.java')):
        sha.update(str(path.relative_to(ROOT/'patches')).encode());sha.update(path.read_bytes())
    return sha.hexdigest()

def prepare_patch(runtime):
    """Never reuse version-specific bytecode with an unknown official JAR."""
    runtime=Path(runtime)
    with (runtime/'ums.jar').open('rb') as stream:known=hashlib.file_digest(stream,'sha256').hexdigest()==(WINDOWS_JAR_SHA if platform_os.WINDOWS else BOOTSTRAP_JAR_SHA)
    if known:shutil.copy2(ROOT/('server-support/update-windows.jar' if platform_os.WINDOWS else 'server-support/update.jar'),runtime/'update.jar');return 'verified-bootstrap'
    javac=shutil.which('javac')
    if not javac:raise RuntimeError('Para integrar esta versión de UMS se necesita el compilador Java (JDK). La instalación anterior no se ha modificado.')
    with zipfile.ZipFile(runtime/'ums.jar') as jar:
        manifest=jar.read('META-INF/MANIFEST.MF').decode()
    match=re.search(r'^Build-Jdk-Spec: (\d+)',manifest,re.M);level=match[1] if match else '17'
    with tempfile.TemporaryDirectory(prefix='ums-integration-') as temp:
        classes=Path(temp)/'classes';classes.mkdir()
        sources=sorted(str(p) for p in (ROOT/'patches/net').rglob('*.java'))
        result=subprocess.run([javac,'--release',level,'-cp',str(runtime/'ums.jar'),'-d',str(classes),*sources],capture_output=True,text=True,timeout=180)
        if result.returncode:raise RuntimeError('La nueva versión de UMS no es compatible con la integración de reproducción. La instalación anterior no se ha modificado.\n'+result.stderr[-1800:])
        with zipfile.ZipFile(runtime/'update.jar','w',zipfile.ZIP_DEFLATED) as jar:
            for path in sorted(classes.rglob('*.class')):jar.write(path,path.relative_to(classes).as_posix())
    return 'rebuilt-from-source'

def probe_runtime(runtime,native):
    """Smoke-test only loopback, empty shares and a fresh disposable profile."""
    runtime=Path(runtime);native=Path(native)
    with tempfile.TemporaryDirectory(prefix='ums-compatibility-') as temp:
        profile=Path(temp);ports=[]
        while len(ports)<2:
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            if port not in ports:ports.append(port)
        config=c.properties([('uuid',str(uuid.uuid4())),('server_name','UMS compatibility check'),('network_interface','' if platform_os.WINDOWS else 'lo'),('hostname','127.0.0.1'),('port',ports[0]),('web_gui_port',ports[1]),('run_wizard','false'),('auto_update','false'),('external_network','false'),('use_api_info','false'),('authentication_enabled','true'),('authenticate_localhost_as_admin','true'),('web_gui_on_start','false'),('web_player_enable','false'),('scan_shared_folders_on_startup','false'),('use_cache','false'),('upnp_cds_write','false'),('generate_thumbnails','false'),('logging_filter_console','WARN')])
        (profile/'UMS.conf').write_text(config, encoding='utf-8');(profile/'SHARED.conf').write_text('[]', encoding='utf-8');(profile/'renderers').mkdir()
        env=dict(os.environ,UMS_PROFILE=str(profile/'UMS.conf'),PMS_HOME=str(runtime),UMS_MAX_MEMORY='512M',LD_LIBRARY_PATH=str(native/'usr/lib/x86_64-linux-gnu'),JAVA_OPTS='-Djava.awt.headless=true -Duser.home='+str(profile))
        with (profile/'probe.log').open('w+') as log:
            proc=subprocess.Popen(platform_os.command(runtime,profile) if platform_os.WINDOWS else [str(runtime/'UMS.sh'),'console'],cwd=runtime,env=env,stdout=log,stderr=subprocess.STDOUT,**platform_os.process_options())
            try:
                deadline=time.monotonic()+55
                while time.monotonic()<deadline:
                    if proc.poll() is not None:break
                    try:
                        for endpoint,key in [('shared/','shared_content'),('renderers/','renderers')]:
                            with urllib.request.urlopen(f'http://127.0.0.1:{ports[1]}/v1/api/{endpoint}',timeout=2) as response:data=json.load(response)
                            if key not in data or not isinstance(data[key],list):raise ValueError('API incompatible')
                            if key=='shared_content' and data[key]:raise ValueError('Biblioteca de prueba no vacía')
                        return
                    except (OSError,ValueError):time.sleep(.3)
                log.flush();log.seek(0);tail=log.read()[-2200:]
                raise RuntimeError('La nueva versión no ha superado la comprobación de compatibilidad. La instalación anterior no se ha modificado.\n'+tail)
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:proc.wait(timeout=12)
                    except subprocess.TimeoutExpired:proc.kill();proc.wait()
