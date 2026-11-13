# SPDX-License-Identifier: GPL-3.0-or-later
"""Staged Windows UMS installation. Never runs the upstream system installer."""
import json,os,shutil,subprocess,tempfile
from pathlib import Path
import baul_core as c
import platform_support as p
import server_releases as r
import native_dependencies

def safe():
    if c.DATA.is_symlink() or c.RUNTIME.is_symlink():raise RuntimeError('La ruta o el servicio pertenece a otra instalación; no se modificará.')
    if c.DATA.exists() and not (c.DATA/'managed-installation.json').is_file():raise RuntimeError('La ruta o el servicio pertenece a otra instalación; no se modificará.')

def health(deep=False):
    import server_manager as m
    c.RUNTIME=c.discover_runtime();report=dict(kind='absent',present=c.DATA.exists(),issues=[],warnings=[],repairable=True,status=c.active(),foreign=[])
    if not report['present']:return report
    try:
        safe();m.verify_bundle();metadata=json.loads((c.DATA/'managed-installation.json').read_text(encoding='utf-8'))
        files=metadata['files'];names=files if deep else ['ums.jar',p.java(c.RUNTIME).relative_to(c.RUNTIME).as_posix(),'bin/ffmpeg.exe','update.jar']
        for name in names:
            f=c.RUNTIME/name
            if not f.is_file() or m.digest(f)!=files[name]:report['issues'].append('Archivo del servidor ausente o modificado: '+name)
        if metadata['patch_sources_sha256']!=r.source_digest():report['issues'].append('Faltan las correcciones compatibles de UMS Control o están modificadas.')
        if deep:
            for args in ([str(p.java(c.RUNTIME)),'-version'],[str(p.ffmpeg(c.RUNTIME)),'-version']):
                c.run(args,timeout=20)
    except (OSError,ValueError,KeyError,RuntimeError,subprocess.SubprocessError) as error:report['issues'].append(str(error))
    if not (c.PROFILE/'UMS.conf').exists():report['warnings'].append('Guarda y aplica los ajustes para crear la configuración del servidor.')
    report['kind']='damaged' if report['issues'] else 'healthy';return report

def install(repair=False,archive=None,release=None):
    import server_manager as m
    safe();m.verify_bundle();release=r.validate_release(release) if release else r.latest_release()
    if c.DATA.exists() and not repair:raise RuntimeError('Ya existe una instalación. Usa Salud del servidor para revisarla.')
    with m.operation_lock():
        c.DATA.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.ums-install-',dir=c.DATA.parent) as temp:
            temp=Path(temp);payload=temp/'payload';runtime=payload/'runtime';runtime.mkdir(parents=True)
            download=Path(archive) if archive else native_dependencies.fetch(release,c.CONFIG/'downloads')
            if download.stat().st_size!=release['size'] or m.digest(download)!=release['sha256']:raise RuntimeError('La descarga del servidor no coincide con la huella oficial esperada.')
            extractor=p.ROOT/'vendor/7zip/7z.exe'
            if not extractor.is_file():raise RuntimeError('Missing packaged archive extractor. Reinstall UMS Control.')
            c.run([str(extractor),'x','-y','-o'+str(runtime),str(download),'-x!$PLUGINSDIR/*','-x!Uninstall.exe'],timeout=180)
            if r.jar_version(runtime)!=release['version']:raise RuntimeError('La versión descargada no coincide con la versión oficial solicitada.')
            mode=r.prepare_patch(runtime)
            for args in ([str(p.java(runtime)),'-version'],[str(p.ffmpeg(runtime)),'-version']):c.run(args,timeout=30)
            r.probe_runtime(runtime,payload/'native')
            files={f.relative_to(runtime).as_posix():m.digest(f) for f in runtime.rglob('*') if f.is_file() and not f.name.endswith('.log')}
            (payload/'managed-installation.json').write_text(json.dumps(dict(version=release['version'],release=release,files=files,patch_sources_sha256=r.source_digest(),patch_mode=mode),indent=2), encoding='utf-8')
            old=temp/'previous';old_runtime=c.RUNTIME;was_active=c.active()=='active';moved=False;installed=False
            try:
                if was_active:c.service('stop')
                if c.DATA.exists():c.DATA.rename(old);moved=True
                payload.rename(c.DATA);installed=True;c.RUNTIME=c.DATA/'runtime'
                if was_active:c.service('start');c.ready()
            except Exception:
                if installed:c.service('stop');m.trash(c.DATA)
                if moved:old.rename(c.DATA)
                c.RUNTIME=old_runtime
                if was_active:c.service('start')
                raise
            if moved:m.trash(old)
    if not (c.PROFILE/'UMS.conf').exists() and not (c.CONFIG/'settings.json').exists():c.apply(c.defaults(),restart=False)
    return health(deep=True)

def uninstall():
    import server_manager as m
    safe()
    with m.operation_lock():c.service('stop');c.service('disable');m.trash(c.DATA)
    return health()
