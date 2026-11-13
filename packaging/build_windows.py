#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze the common application and build a per-user NSIS Windows installer."""
import argparse,json,os,shutil,subprocess,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];CACHE=ROOT/'.cache/distribution-20261113'

def assemble(payload):
    internal=payload/'_internal';internal.mkdir(exist_ok=True)
    for name in ['LICENSE','THIRD_PARTY_NOTICES.md','README.md','README_ES.md']:
        shutil.copy2(ROOT/name,internal/name)
    shutil.copy2(ROOT/'src/translations.json',internal/'translations.json')
    for name in ['assets','docs','server-support','patches']:
        shutil.copytree(ROOT/name,internal/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
    # Windows retains its independent geometric icon and wallpaper set.
    shutil.copytree(ROOT/'assets/windows',internal/'assets',dirs_exist_ok=True)
    vendor=internal/'vendor/7zip';vendor.mkdir(parents=True,exist_ok=True)
    for name in ['7z.exe','7z.dll','License.txt']:
        shutil.copy2(CACHE/'7zip-full'/name,vendor/name)
    # Retain the actual wheel license texts and package metadata next to the EXE.
    licenses=internal/'licenses';licenses.mkdir(exist_ok=True)
    shutil.copy2(CACHE/'windows-python/LICENSE.txt',licenses/'CPython-LICENSE.txt')
    spec=json.loads((ROOT/'packaging/inputs.json').read_text(encoding='utf-8'))
    for item in spec['windows_wheels']:
        with zipfile.ZipFile(CACHE/'windows-wheels'/item['name']) as wheel:
            for name in wheel.namelist():
                if name.endswith('/') or '.dist-info/' not in name:continue
                if not any(word in name.lower() for word in ['license','copying','notice','metadata']):continue
                out=licenses/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(wheel.read(name))
    shutil.copy2(ROOT/'packaging/inputs.json',licenses/'build-inputs.json')
    (internal/'distribution-marker.json').write_text(json.dumps(dict(version='1.0.0',format='windows')),encoding='utf-8')
    remove=CACHE/'remove-windows.nsh';lines=[]
    for f in sorted(payload.rglob('*'),reverse=True):
        relative=str(f.relative_to(payload)).replace('/','\\')
        lines.append(('Delete' if f.is_file() else 'RMDir')+' "$INSTDIR\\'+relative+'"')
    lines.insert(0,'Delete "$INSTDIR\\_internal\\first-language.json"')
    remove.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return remove

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--wine-python',type=Path);parser.add_argument('--nsis-root',type=Path);args=parser.parse_args()
    driver=CACHE/'freeze_driver.py'
    driver.write_text('import os\nos.environ.setdefault("PATH",r"C:\\windows\\system32;C:\\windows")\nfrom PyInstaller.__main__ import run\nrun('+repr(['--noconfirm','--clean','--windowed','--name','UMS-Control','--distpath',str(CACHE/'windows-dist') if os.name=='nt' else 'Z:'+str(CACHE/'windows-dist').replace('/','\\'),'--workpath',str(CACHE/'windows-build') if os.name=='nt' else 'Z:'+str(CACHE/'windows-build').replace('/','\\'),'--specpath',str(CACHE) if os.name=='nt' else 'Z:'+str(CACHE).replace('/','\\'),str(ROOT/'src/launcher.py') if os.name=='nt' else 'Z:'+str(ROOT/'src/launcher.py').replace('/','\\')])+')\n',encoding='utf-8')
    command=[str(sys.executable),str(driver)] if os.name=='nt' else ['wine',str(args.wine_python),'Z:'+str(driver).replace('/','\\')]
    subprocess.run(command,check=True)
    payload=CACHE/'windows-dist/UMS-Control';remove=assemble(payload);dist=ROOT/'dist';dist.mkdir(exist_ok=True)
    output=dist/'ums-control-1.0.0-windows-x86_64-setup.exe'
    if os.name=='nt':command=['makensis','/DPAYLOAD='+str(payload),'/DOUTPUT='+str(output),'/DREMOVE_FILES='+str(remove),str(ROOT/'packaging/ums-control.nsi')]
    else:
        command=['bwrap','--ro-bind',str(args.nsis_root),'/', '--bind',str(ROOT),'/src','--dev','/dev','--proc','/proc','--tmpfs','/tmp','--chdir','/src/packaging','/usr/bin/makensis','-DPAYLOAD=/src/.cache/distribution-20261113/windows-dist/UMS-Control','-DOUTPUT=/src/dist/'+output.name,'-DREMOVE_FILES=/src/.cache/distribution-20261113/remove-windows.nsh','ums-control.nsi']
    subprocess.run(command,check=True);print('Windows EXE built:',output)
if __name__=='__main__':main()
