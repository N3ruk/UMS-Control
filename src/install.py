#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 N3ruk
"""Install/update the companion on this host. --activate completes DLNA handover."""
import argparse,hashlib,json,os,pathlib,shlex,shutil,sys
import baul_core as c
from platform_support import ROOT, CODE_ROOT

def desktop_exec(path):
 # GLib rejects %% in the executable token. For that exceptional case, a
 # fixed Python trampoline decodes the path as data and execs it without a shell.
 def quote(value):
  value='"'+''.join('\\'+ch if ch in '\\"`$' else ch for ch in value)+'"'
  return value.replace('\\','\\\\').replace('\n','\\n').replace('\r','\\r')
 if '%' in str(path):
  code="import os; p=os.fsdecode(bytes.fromhex('"+os.fsencode(path).hex()+"')); os.execv(p,[p])"
  return '/usr/bin/python3 -c '+quote(code)
 return quote(str(path))

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--activate',action='store_true');args=parser.parse_args()
 if sys.version_info<(3,12):raise SystemExit('Python 3.12 o posterior es obligatorio.')
 if os.geteuid()==0:raise SystemExit('Ejecuta este instalador como usuario, no como root.')
 import PyQt6.QtWidgets  # Check before changing the installation.
 # Frontend installation is independent from server presence. Its own UI can repair UMS.
 import server_manager as manager
 manager.verify_bundle()
 manager.refresh_service_unit()
 patch=ROOT/'server-support/update.jar';installed=c.RUNTIME/'update.jar'
 official=c.RUNTIME/'ums.jar'
 runtime_ok=official.is_file() and manager.digest(official)==manager.releases.BOOTSTRAP_JAR_SHA
 managed=(c.DATA/'managed-installation.json').is_file()
 if args.activate and not (runtime_ok or managed):raise SystemExit('Instala primero el servidor desde UMS Control.')
 if runtime_ok and not managed:
  patch_changed=not installed.exists() or manager.digest(installed)!=manager.digest(patch)
  if patch_changed and c.active()=='active':raise SystemExit('Detén UMS desde Resumen antes de actualizar el motor; después ejecuta de nuevo el instalador.')
  if patch_changed:
   staged=c.RUNTIME/'.update.jar-new';shutil.copy2(patch,staged);os.replace(staged,installed)
 target=c.HOME/'.local/share/baul-media-control';target.mkdir(parents=True,exist_ok=True)
 names=['platform_support.py','portable_service.py','windows_server.py','launcher.py','distribution.py','first_run.py','user_guide.py','folder_rules.py','baul_core.py','baul_gui.py','server_manager.py','server_releases.py','appearance.py','configuration.py','native_dependencies.py','localization.py','translations.json','baul.svg','README.md','README_ES.md','LICENSE','THIRD_PARTY_NOTICES.md']
 for name in names:
  shutil.copy2((CODE_ROOT if name.endswith('.py') or name=='translations.json' else ROOT)/name,target/name)
 support=target/'server-support';support.mkdir(exist_ok=True)
 for name in ['bundle.json',*manager.verify_bundle()]:shutil.copy2(ROOT/'server-support'/name,support/name)
 for directory in ['qt-translations','patches','assets','docs']:
  if not (ROOT/directory).is_dir():continue
  shutil.copytree(ROOT/directory,target/directory,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
 for d in [c.CONFIG,c.PROFILE]:d.mkdir(parents=True,exist_ok=True);d.chmod(0o700)
 bindir=c.HOME/'.local/bin';bindir.mkdir(parents=True,exist_ok=True)
 launcher=bindir/'ums-control';c.atomic_write(launcher,'#!/bin/sh\nexec /usr/bin/python3 '+shlex.quote(str(target/'baul_gui.py'))+' "$@"\n');launcher.chmod(0o755)
 legacy=bindir/'baul-media-control';c.atomic_write(legacy,'#!/bin/sh\nexec '+shlex.quote(str(launcher))+' "$@"\n');legacy.chmod(0o755)
 desktop=c.HOME/'.local/share/applications/ums-control.desktop'
 c.atomic_write(desktop,'[Desktop Entry]\nType=Application\nVersion=1.0\nName=UMS Control\nComment=Carpetas y conversión DLNA por dispositivo · Universal Media Server\nExec='+desktop_exec(launcher)+'\nIcon='+str(target/'assets/ums-control.png')+'\nTerminal=false\nCategories=AudioVideo;Settings;\nKeywords=UMS;Control;DLNA;Media;Servidor;\nStartupNotify=true\nStartupWMClass=ums-control\n')
 legacy_desktop=desktop.with_name('baul-media-control.desktop')
 if legacy_desktop.is_file():
  old=legacy_desktop.read_text(encoding='utf-8')
  if 'ums-control' in old or 'baul-media-control' in old:manager.trash(legacy_desktop)
 for folder in ['Escritorio','Desktop']:
  old=c.HOME/folder/'baul-media-control.desktop'
  if old.is_file() and 'baul-media-control' in old.read_text(encoding='utf-8'):
   c.atomic_write(old.with_name('ums-control.desktop'),desktop.read_text(encoding='utf-8'));old.with_name('ums-control.desktop').chmod(0o755);manager.trash(old)
 manifest={name:hashlib.sha256((target/name).read_bytes()).hexdigest() for name in names}
 for directory in ['server-support','qt-translations','patches','assets','docs']:
  for file in (target/directory).rglob('*'):
   if file.is_file():manifest[str(file.relative_to(target))]=hashlib.sha256(file.read_bytes()).hexdigest()
 manifest['runtime_update_sha256']=manager.digest(installed) if installed.is_file() else None
 c.atomic_write(target/'install-manifest.json',json.dumps(manifest,indent=2))
 if shutil.which('update-desktop-database'):c.run(['update-desktop-database',str(desktop.parent)],check=False)
 if args.activate:
  # Only switch away from MiniDLNA after both UMS services are responsive.
  c.service('start');c.ready();c.service('enable')
  c.run(['systemctl','--user','disable','--now','baul-dlna.service'])
 print('Instalado:',launcher)
 print('Servidor UMS:',c.active())
if __name__=='__main__':main()
