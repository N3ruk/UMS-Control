# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 N3ruk
"""Manage only the per-user UMS installation owned by UMS Control.

No root, shell command strings, system package removal or media mutations.
"""
import contextlib, hashlib, json, os, platform, shutil, subprocess, tarfile, tempfile, urllib.request
from pathlib import Path
import baul_core as c
import server_releases as releases
import native_dependencies
import platform_support as platform_os
import platform_support as fcntl

SUPPORT=Path(__file__).resolve().parent/'server-support'
BUNDLE_SHA='98556b264710793ecc02eceb8fc3031b979131cd0f000c96b0700a50f3f16abc'

def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def unit_path():return c.HOME/'.config/systemd/user'/c.SERVICE

def unit_text():
    def quote(p):return '"'+str(p).replace('\\','\\\\').replace('"','\\"').replace('%','%%')+'"'
    return '\n'.join(['[Unit]','Description=BAUL - Universal Media Server','After=network.target','StartLimitIntervalSec=60','StartLimitBurst=20','','[Service]','Type=simple',
      'WorkingDirectory='+str(c.RUNTIME).replace('\\','\\\\').replace('%','%%'),'Environment='+quote('UMS_PROFILE='+str(c.PROFILE/'UMS.conf')),'Environment=UMS_MAX_MEMORY=2048M',
      'Environment='+quote('LD_LIBRARY_PATH='+str(c.DATA/'native/usr/lib/x86_64-linux-gnu')),'ExecStart='+quote(c.RUNTIME/'UMS.sh')+' console',
      'SuccessExitStatus=143','Restart=on-failure','RestartSec=10','TimeoutStopSec=25','UMask=0077','NoNewPrivileges=yes','Nice=5','','[Install]','WantedBy=default.target',''])

def owned_unit():
    p=unit_path()
    if p.is_symlink():return False
    if not p.exists():return True
    # Accept the original unquoted unit as well as the portable unit generated here.
    text=p.read_text(encoding='utf-8');expected=unit_text()
    raw_path=str(c.RUNTIME).replace('\\','\\\\').replace('%','%%')
    legacy=expected.replace('WorkingDirectory='+raw_path,'WorkingDirectory="'+raw_path+'"')
    return text in {expected,expected.replace('"','').replace('%%','%'),legacy,legacy.replace('"','').replace('%%','%')}

def refresh_service_unit():
    """Repair only an exactly recognized generated unit; never start/stop it."""
    path=unit_path()
    if platform_os.WINDOWS or not platform_os.systemd():return False
    if not path.is_file() or not owned_unit() or path.read_text(encoding='utf-8')==unit_text():return False
    with operation_lock():
        if not owned_unit():raise RuntimeError('La ruta o el servicio pertenece a otra instalación; no se modificará.')
        c.atomic_write(path,unit_text());c.run(['systemctl','--user','daemon-reload'])
    return True

def prepare_service():
    """Reconcile recognized units at action time; caller holds operation_lock."""
    c.RUNTIME=c.discover_runtime()
    if platform_os.WINDOWS:
        if not (c.RUNTIME/'ums.jar').is_file():raise RuntimeError('Instala primero el servidor desde UMS Control.')
        return
    if not owned_unit() or c.DATA.is_symlink() or c.RUNTIME.is_symlink():raise RuntimeError('La ruta o el servicio pertenece a otra instalación; no se modificará.')
    if not (c.RUNTIME/'UMS.sh').is_file() or not (c.RUNTIME/'ums.jar').is_file():raise RuntimeError('Instala primero el servidor desde UMS Control.')
    path=unit_path()
    if not path.exists() or path.read_text(encoding='utf-8')!=unit_text():c.atomic_write(path,unit_text())
    if not platform_os.systemd():return
    # Updaters may write a unit without reloading the manager's cached definition.
    c.run(['systemctl','--user','daemon-reload'])

def control(action):
    if action not in {'start','stop','restart','enable','disable'}:raise ValueError('Acción no válida.')
    with operation_lock():
        c.RUNTIME=c.discover_runtime()
        if not owned_unit() or c.DATA.is_symlink() or c.RUNTIME.is_symlink():raise RuntimeError('La ruta o el servicio pertenece a otra instalación; no se modificará.')
        if action in {'start','restart','enable'}:prepare_service()
        if action in {'start','restart'}:
            if not (c.PROFILE/'UMS.conf').is_file():raise RuntimeError('Guarda y aplica los ajustes para crear la configuración del servidor.')
            if platform_os.systemd():c.run(['systemctl','--user','reset-failed',c.SERVICE],check=False)
        c.service(action)
        if action in {'start','restart'}:c.ready()
    return health()

def verify_bundle():
    if digest(SUPPORT/'bundle.json')!=BUNDLE_SHA:raise RuntimeError('El soporte de instalación está dañado. Reinstala UMS Control.')
    items=json.loads((SUPPORT/'bundle.json').read_text(encoding='utf-8'))
    for name,sha in items.items():
        if Path(name).name!=name or digest(SUPPORT/name)!=sha:raise RuntimeError('El soporte de instalación está dañado. Reinstala UMS Control.')
    return items

def foreign_installations():
    if platform_os.WINDOWS:return []
    paths=[Path('/opt/ums'),Path('/opt/universalmediaserver'),Path('/usr/share/ums'),c.HOME/'UMS']
    found=[str(p) for p in paths if p.exists()]
    if not platform_os.systemd():return found
    result=c.run(['systemctl','--user','show',c.SERVICE,'-p','FragmentPath','--value'],check=False,timeout=4)
    fragment=result.stdout.strip()
    if fragment and fragment!=str(unit_path()):found.append(fragment)
    return found

def health(deep=False):
    if platform_os.WINDOWS:
        import windows_server;return windows_server.health(deep)
    c.RUNTIME=c.discover_runtime()
    present=c.RUNTIME.exists() or c.DATA.exists() or unit_path().exists() or unit_path().is_symlink()
    result=dict(kind='absent',present=present,issues=[],warnings=[],repairable=True,status=c.active(),foreign=foreign_installations())
    if not present:
        if result['foreign']:result['kind']='incompatible'
        return result
    issues=result['issues'];warnings=result['warnings']
    if not owned_unit() or c.DATA.is_symlink() or c.RUNTIME.is_symlink():
        result.update(kind='incompatible',repairable=False);issues.append('La ruta o el servicio pertenece a otra instalación; no se modificará.');return result
    try:
        verify_bundle();metadata_path=c.DATA/'managed-installation.json'
        metadata=json.loads(metadata_path.read_text(encoding='utf-8')) if metadata_path.exists() else None
        manifest=metadata['files'] if metadata else json.loads((SUPPORT/'runtime-manifest.json').read_text(encoding='utf-8'))
        keys=manifest if deep else ['ums.jar','UMS.sh',str(releases.java_path(c.RUNTIME).relative_to(c.RUNTIME)),'linux/ffmpeg']
        for name in keys:
            p=c.RUNTIME/name
            if not p.is_file() or (deep or name in {'ums.jar','UMS.sh'}) and digest(p)!=manifest[name]:issues.append('Archivo del servidor ausente o modificado: {value}'.replace('{value}',name))
        if not (c.RUNTIME/'update.jar').is_file() or digest(c.RUNTIME/'update.jar')!=(metadata['patch_sha256'] if metadata else digest(SUPPORT/'update.jar')):issues.append('Faltan las correcciones compatibles de UMS Control o están modificadas.')
        for name in ['libmediainfo.so','libzen.so',metadata.get('tinyxml','libtinyxml2.so.11') if metadata else 'libtinyxml2.so.11']:
            if not (c.DATA/'native/usr/lib/x86_64-linux-gnu'/name).exists():issues.append('Dependencia privada ausente: {value}'.replace('{value}',name))
        if deep:
            for name,expected in (metadata.get('native_files') if metadata and metadata.get('native_files') else json.loads((SUPPORT/'native-manifest.json').read_text(encoding='utf-8'))).items():
                p=c.DATA/'native'/name
                good=p.is_symlink() and str(p.readlink())==expected['link'] if 'link' in expected else p.is_file() and digest(p)==expected['sha256']
                if not good:issues.append('Dependencia privada ausente: {value}'.replace('{value}',name))
        if metadata and metadata['patch_sources_sha256']!=releases.source_digest():issues.append('Faltan las correcciones compatibles de UMS Control o están modificadas.')
        if not unit_path().is_file():issues.append('Falta el servicio de usuario del servidor.')
        if deep:
            env=dict(os.environ,LD_LIBRARY_PATH=str(c.DATA/'native/usr/lib/x86_64-linux-gnu'))
            for args in [[str(releases.java_path(c.RUNTIME)),'-version'],[str(c.RUNTIME/'linux/ffmpeg'),'-version']]:
                r=subprocess.run(args,capture_output=True,text=True,timeout=15,env=env)
                if r.returncode:issues.append('Un componente del servidor no puede ejecutarse: {value}'.replace('{value}',Path(args[0]).name))
            for name in ['libmediainfo.so','libzen.so',metadata.get('tinyxml','libtinyxml2.so.11') if metadata else 'libtinyxml2.so.11']:
                p=c.DATA/'native/usr/lib/x86_64-linux-gnu'/name
                if p.exists():
                    r=subprocess.run(['ldd',str(p)],capture_output=True,text=True,timeout=10,env=env)
                    if r.returncode or 'not found' in r.stdout:issues.append('Dependencias del sistema incompatibles: {value}'.replace('{value}',name))
    except (OSError,ValueError,KeyError,RuntimeError,subprocess.SubprocessError) as e:
        issues.append(str(e))
        if 'soporte de instalación' in str(e):result['repairable']=False
    if (c.PROFILE/'UMS.conf').exists():
        try:
            state=c.load_state();state['tvs']=[c.editable_tv(t) for t in state['tvs']];c.validate(state)
        except Exception:warnings.append('Revisa la configuración guardada y la interfaz de red; reinstalar no corrige estos ajustes.')
    else:warnings.append('Guarda y aplica los ajustes para crear la configuración del servidor.')
    if result['status']=='active':
        try:c.api('shared/')
        except Exception:warnings.append('El proceso está activo, pero la administración local no responde; puede estar iniciándose.')
    elif result['status']=='failed':warnings.append('El servicio ha fallado. Revisa el registro; no se recomienda reinstalar si los archivos están íntegros.')
    result['kind']='damaged' if issues else 'healthy'
    return result

@contextlib.contextmanager
def operation_lock():
    c.CONFIG.mkdir(parents=True,exist_ok=True)
    with (c.CONFIG/'.server-operation.lock').open('w') as f:
        fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        # Serialize with configuration apply too.
        with (c.CONFIG/'.lock').open('w') as config:
            fcntl.flock(config,fcntl.LOCK_EX|fcntl.LOCK_NB);yield

def trash(path):
    if path.exists() or path.is_symlink():
        if shutil.which('gio') and not platform_os.WINDOWS:c.run(['gio','trash',str(path)],timeout=90)
        else:platform_os.recycle(path)

def install(repair=False,archive=None,release=None):
    if platform_os.WINDOWS:
        import windows_server;return windows_server.install(repair,archive,release)
    if platform.system()!='Linux' or platform.machine() not in {'x86_64','amd64'}:raise RuntimeError('Esta versión del servidor requiere Linux x86_64.')
    verify_bundle()
    if not owned_unit() or c.DATA.is_symlink() or c.RUNTIME.is_symlink():raise RuntimeError('La ruta o el servicio pertenece a otra instalación; no se modificará.')
    # Network metadata is resolved fresh for every explicit install/reinstall.
    release=releases.validate_release(release) if release else releases.latest_release()
    with operation_lock():
        if c.DATA.exists() and not repair:raise RuntimeError('Ya existe una instalación. Usa Salud del servidor para revisarla.')
        c.DATA.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.ums-install-',dir=c.DATA.parent) as temp:
            temp=Path(temp);payload=temp/'payload';payload.mkdir();archive=Path(archive) if archive else temp/'ums.tgz'
            if not archive.exists():
                with urllib.request.urlopen(urllib.request.Request(release['url'],headers={'User-Agent':'UMS-Control/1.0'}),timeout=45) as r,archive.open('wb') as out:shutil.copyfileobj(r,out)
            if archive.stat().st_size!=release['size'] or digest(archive)!=release['sha256']:raise RuntimeError('La descarga del servidor no coincide con la huella oficial esperada.')
            with tarfile.open(archive) as tf:
                prefix='ums-'+release['version']
                if any(m.name!=prefix and not m.name.startswith(prefix+'/') for m in tf.getmembers()):raise RuntimeError('Estructura de descarga no válida.')
                tf.extractall(payload,filter='data')
            staged_runtime=payload/'runtime';(payload/prefix).rename(staged_runtime)
            if releases.jar_version(staged_runtime)!=release['version']:raise RuntimeError('La versión descargada no coincide con la versión oficial solicitada.')
            native=payload/'native';native.mkdir()
            if (platform_os.ROOT/'native-support').is_dir():shutil.copytree(platform_os.ROOT/'native-support',native,dirs_exist_ok=True)
            for deb in native_dependencies.packages(c.HOME/'.cache/ums-control/upstream'):platform_os.extract_deb(deb,native)
            libdir=native/'usr/lib/x86_64-linux-gnu'
            for name in ['libmediainfo','libzen']:
                link=libdir/(name+'.so')
                if not link.exists():link.symlink_to(name+'.so.0')
            patch_mode=releases.prepare_patch(staged_runtime)
            env=dict(os.environ,LD_LIBRARY_PATH=str(native/'usr/lib/x86_64-linux-gnu'))
            for lib in ['libmediainfo.so','libzen.so',native_dependencies.manifest().get('tinyxml','libtinyxml2.so.10')]:
                r=subprocess.run(['ldd',str(native/'usr/lib/x86_64-linux-gnu'/lib)],env=env,capture_output=True,text=True,timeout=15)
                if r.returncode or 'not found' in r.stdout:raise RuntimeError('Las bibliotecas del servidor no son compatibles con este sistema. No se ha cambiado la instalación.')
            for args in [[str(releases.java_path(staged_runtime)),'-version'],[str(staged_runtime/'linux/ffmpeg'),'-version']]:
                subprocess.run(args,env=env,check=True,capture_output=True,timeout=20)
            releases.probe_runtime(staged_runtime,native)
            files={str(p.relative_to(staged_runtime)):digest(p) for p in staged_runtime.rglob('*') if p.is_file() and not p.is_symlink() and p.name!='update.jar' and not p.name.endswith('.log')}
            native_files={str(p.relative_to(native)):dict(link=str(p.readlink())) if p.is_symlink() else dict(sha256=digest(p)) for p in native.rglob('*') if p.is_file() or p.is_symlink()}
            metadata=dict(native_files=native_files,tinyxml=native_dependencies.manifest().get('tinyxml','libtinyxml2.so.10'),version=release['version'],release=release,files=files,patch_sha256=digest(staged_runtime/'update.jar'),patch_sources_sha256=releases.source_digest(),patch_mode=patch_mode)
            (payload/'managed-installation.json').write_text(json.dumps(metadata,indent=2), encoding='utf-8')
            previous_runtime=c.RUNTIME
            was_active=c.active()=='active';old_unit=unit_path().read_text(encoding='utf-8') if unit_path().exists() else None
            old_enabled=c.autostart();old=temp/'previous';previous_profile=temp/'previous-profile';moved=False;installed=False;profile_saved=False
            try:
                if was_active:c.service('stop')
                if was_active and c.PROFILE.exists():
                    shutil.copytree(c.PROFILE,previous_profile,symlinks=True);profile_saved=True
                if c.DATA.exists():c.DATA.rename(old);moved=True
                payload.rename(c.DATA);installed=True;c.RUNTIME=c.DATA/'runtime'
                c.atomic_write(unit_path(),unit_text())
                if platform_os.systemd():c.run(['systemctl','--user','daemon-reload'])
                if was_active:c.service('start');c.ready()
            except Exception:
                if installed:
                    c.service('stop');trash(c.DATA)
                if moved:old.rename(c.DATA)
                c.RUNTIME=previous_runtime
                if installed and profile_saved:
                    trash(c.PROFILE);previous_profile.rename(c.PROFILE)
                if old_unit is None:unit_path().unlink(missing_ok=True)
                else:c.atomic_write(unit_path(),old_unit)
                if platform_os.systemd():c.run(['systemctl','--user','daemon-reload'])
                if old_enabled:c.service('enable')
                if was_active:c.service('start')
                raise
            # Keep previous binaries recoverable in the desktop trash, never profile/media data.
            if moved:trash(old)
    # Initialize only a genuinely new user; never regenerate existing profiles.
    if not (c.PROFILE/'UMS.conf').exists() and not (c.CONFIG/'settings.json').exists():c.apply(c.defaults(),restart=False)
    return health(deep=True)

def update(release):
    release=releases.validate_release(release)
    if releases.version_tuple(release['version'])<=releases.version_tuple(releases.jar_version(c.RUNTIME)):raise RuntimeError('El servidor ya está actualizado.')
    return install(repair=True,release=release)

def uninstall():
    if platform_os.WINDOWS:
        import windows_server;return windows_server.uninstall()
    if not shutil.which('gio'):
        import send2trash
    if not owned_unit() or c.DATA.is_symlink() or c.RUNTIME.is_symlink():raise RuntimeError('La ruta o el servicio pertenece a otra instalación; no se modificará.')
    with operation_lock():
        c.service('stop');c.service('disable')
        trash(c.DATA);trash(unit_path())
        if platform_os.systemd():
            c.run(['systemctl','--user','daemon-reload'])
            c.run(['systemctl','--user','reset-failed',c.SERVICE],check=False)
    return health()
