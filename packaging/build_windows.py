#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze the common application and build a per-user NSIS Windows installer."""
import argparse,json,os,shutil,subprocess,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def assemble(payload,inputs,build):
    internal=payload/'_internal';internal.mkdir(exist_ok=True)
    # Explicit runtime allowlist: never copy private documentation or test data.
    runtime=json.loads((ROOT/'packaging/runtime-files.json').read_text(encoding='utf-8'))
    for name,destination in runtime.items():
        source=ROOT/name
        if name.startswith('src/') and source.suffix=='.py':continue
        target=internal/destination;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
    # Windows retains its independent geometric icon and wallpaper set.
    for source in (ROOT/'assets/windows').iterdir():
        if source.is_file() and 'assets/windows/'+source.name in runtime:
            shutil.copy2(source,internal/'assets'/source.name)
    vendor=internal/'vendor/7zip';vendor.mkdir(parents=True,exist_ok=True)
    for name in ['7z.exe','7z.dll','License.txt']:
        shutil.copy2(inputs/'7zip-full'/name,vendor/name)
    licenses=internal/'licenses';licenses.mkdir(exist_ok=True)
    shutil.copy2(inputs/'windows-python/LICENSE.txt',licenses/'CPython-LICENSE.txt')
    spec=json.loads((ROOT/'packaging/inputs.json').read_text(encoding='utf-8'))
    for item in spec['windows_wheels']:
        with zipfile.ZipFile(inputs/'windows-wheels'/item['name']) as wheel:
            for name in wheel.namelist():
                if name.endswith('/') or '.dist-info/' not in name:continue
                if not any(word in name.lower() for word in ['license','copying','notice','metadata']):continue
                out=licenses/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(wheel.read(name))
    shutil.copy2(ROOT/'packaging/inputs.json',licenses/'build-inputs.json')
    (internal/'distribution-marker.json').write_text(json.dumps(dict(version='1.0.0',format='windows')),encoding='utf-8')
    remove=build/'remove-windows.nsh';lines=[]
    for f in sorted(payload.rglob('*'),reverse=True):
        relative=str(f.relative_to(payload)).replace('/',chr(92))
        lines.append(('Delete' if f.is_file() else 'RMDir')+' "$INSTDIR'+chr(92)+relative+'"')
    lines.insert(0,'Delete "$INSTDIR'+chr(92)+'_internal'+chr(92)+'first-language.json"')
    remove.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return remove

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--wine-python',type=Path);parser.add_argument('--nsis-root',type=Path)
    parser.add_argument('--inputs-dir',type=Path,default=ROOT/'.cache/distribution-20261113')
    parser.add_argument('--build-dir',type=Path,default=ROOT/'.cache/windows-build')
    parser.add_argument('--output',type=Path,default=ROOT/'dist/ums-control-1.0.0-windows-x86_64-setup.exe')
    args=parser.parse_args();inputs=args.inputs_dir.resolve();build=args.build_dir.resolve();output=args.output.resolve()
    if os.name!='nt' and (not args.wine_python or not args.nsis_root):parser.error('Cross-build requires --wine-python and --nsis-root')
    if os.name!='nt' and not all(p.is_relative_to(ROOT) for p in [build,output]):parser.error('Cross-build output and build directory must be inside the source root')
    build.mkdir(parents=True,exist_ok=True);output.parent.mkdir(parents=True,exist_ok=True)
    def win(path):return str(path) if os.name=='nt' else 'Z:'+str(path).replace('/',chr(92))
    driver=build/'freeze_driver.py'
    freeze=['--noconfirm','--clean','--windowed','--name','UMS-Control','--icon',win(ROOT/'assets/windows/ums-control.ico'),'--distpath',win(build/'dist'),'--workpath',win(build/'work'),'--specpath',win(build),win(ROOT/'src/launcher.py')]
    driver.write_text('import os\nos.environ.setdefault("PATH",r"C:\\windows\\system32;C:\\windows")\nfrom PyInstaller.__main__ import run\nrun('+repr(freeze)+')\n',encoding='utf-8')
    command=[str(sys.executable),str(driver)] if os.name=='nt' else ['wine',str(args.wine_python),win(driver)]
    subprocess.run(command,check=True)
    payload=build/'dist/UMS-Control';remove=assemble(payload,inputs,build)
    if os.name=='nt':command=['makensis','/DPAYLOAD='+str(payload),'/DOUTPUT='+str(output),'/DREMOVE_FILES='+str(remove),str(ROOT/'packaging/ums-control.nsi')]
    else:
        def sandbox(path):return '/src/'+path.relative_to(ROOT).as_posix()
        command=['bwrap','--ro-bind',str(args.nsis_root),'/', '--bind',str(ROOT),'/src','--dev','/dev','--proc','/proc','--tmpfs','/tmp','--chdir','/src/packaging','/usr/bin/makensis','-DPAYLOAD='+sandbox(payload),'-DOUTPUT='+sandbox(output),'-DREMOVE_FILES='+sandbox(remove),'ums-control.nsi']
    subprocess.run(command,check=True);print('Windows EXE built:',output)
if __name__=='__main__':main()
