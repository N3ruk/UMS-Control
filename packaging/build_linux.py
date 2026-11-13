#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build matched DEB and self-contained ZIP from pinned portable inputs."""
import argparse,hashlib,json,os,re,shutil,subprocess,sys,tarfile,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import native_dependencies
CACHE=ROOT/'.cache/distribution-20261113'

def digest(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def copy_source(target):
    spec=json.loads((ROOT/'public-files.json').read_text(encoding='utf-8'))
    for name in spec['files']+['assets/'+name for name in spec['generated_assets']]:
        f=ROOT/name
        if f.is_file():
            out=target/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,out)
    shutil.copy2(ROOT/'PUBLIC-MANIFEST.json',target/'PUBLIC-MANIFEST.json')
    (target/'distribution-marker.json').write_text(json.dumps(dict(version='1.0.0',format='linux',native_baseline='jammy')), encoding='utf-8')

def build(args):
    stage=CACHE/'linux-payload';stage.mkdir(parents=True,exist_ok=True);copy_source(stage)
    # The runtime is pinned in inputs.json; the archive is verified before extraction.
    pin=json.loads((ROOT/'packaging/inputs.json').read_text(encoding='utf-8'))['linux_python']
    archive=CACHE/'python-linux.tar.gz'
    if digest(archive)!=pin['sha256']:raise RuntimeError('Portable Python input mismatch')
    if not (stage/'python').exists():shutil.copytree(CACHE/'linux-toolchain/python',stage/'python',symlinks=True,ignore=shutil.ignore_patterns('__pycache__'))
    (stage/'python/bin/python3').chmod(0o755)
    # Keep package licenses and exact wheel metadata. These are not system installs.
    lib=stage/'lib';lib.mkdir(exist_ok=True)
    native=stage/'native-support';native.mkdir(exist_ok=True)
    spec=json.loads((ROOT/'server-support/dependencies-portable.json').read_text(encoding='utf-8'))
    for item in spec['packages']:
        deb=native_dependencies.fetch(item,ROOT/'.cache/upstream');subprocess.run(['dpkg-deb','-x',str(deb),str(native)],check=True,capture_output=True)
    nlib=native/'usr/lib/x86_64-linux-gnu'
    for name in ('libmediainfo','libzen'):
        f=nlib/(name+'.so')
        if not f.exists():f.symlink_to(name+'.so.0')
    # Resolve all shipped Qt plugins and native-library dependencies in the older build base.
    base=Path(args.base).resolve()
    candidates=[f for f in (stage/'python/lib/python3.12/site-packages/PyQt6').rglob('*.so*') if f.is_file()]+[f for f in nlib.glob('*.so*') if f.is_file()]
    skipped={'libc.so.6','libm.so.6','libpthread.so.0','libdl.so.2','librt.so.1','libutil.so.1','libresolv.so.2','ld-linux-x86-64.so.2'}
    # libcurl-gnutls may not be present in the baseline root; prepare it first using the pinned dependency helper.
    for round in range(4):
        command=['bwrap','--ro-bind',str(base),'/', '--ro-bind',str(stage),'/mnt','--dev','/dev','--proc','/proc','--setenv','LD_LIBRARY_PATH','/mnt/lib:/mnt/native-support/usr/lib/x86_64-linux-gnu:/mnt/python/lib/python3.12/site-packages/PyQt6/Qt6/lib','/usr/bin/ldd',*['/mnt/'+str(f.relative_to(stage)) for f in candidates]]
        result=subprocess.run(command,capture_output=True,text=True)
        if 'bwrap:' in result.stderr or not result.stdout:raise RuntimeError('Dependency sandbox failed: '+result.stderr)
        missing=sorted(set(re.findall(r'(\S+) => not found',result.stdout)))
        paths=set(re.findall(r'=> (/[^\s]+)',result.stdout));new=0
        for name in paths:
            source=base/name.lstrip('/')
            if name.startswith('/mnt/') or Path(name).name in skipped or not source.exists():continue
            destination=lib/Path(name).name
            if not destination.exists():shutil.copy2(source,destination);new+=1
        candidates=list(lib.glob('*.so*'))+candidates
        if not new:break
    # Vulkan and OpenGL driver loader dependencies remain provided by the desktop.
    (CACHE/'linux-ldd-missing.json').write_text(json.dumps(missing,indent=2), encoding='utf-8')
    # Server dependencies receive their complete private closure too, avoiding distro-specific SONAME assumptions.
    for f in lib.iterdir():shutil.copy2(f,nlib/f.name)
    # Preserve the actual shared-library copyright notices and exact source versions.
    query=['bwrap','--ro-bind',str(base),'/', '--dev','/dev','--proc','/proc','dpkg-query','-S']
    query += [directory+f.name for f in lib.iterdir() for directory in ['/usr/lib/x86_64-linux-gnu/','/lib/x86_64-linux-gnu/']]
    ownership=subprocess.run(query,capture_output=True,text=True)
    packages=sorted({line.split(': ',1)[0] for line in ownership.stdout.splitlines() if ': ' in line})
    versions=subprocess.run(['bwrap','--ro-bind',str(base),'/', '--dev','/dev','--proc','/proc','dpkg-query','-W','-f=${binary:Package}\t${Version}\t${source:Package}\t${source:Version}\n',*packages],capture_output=True,text=True,check=True)
    sbom=[]
    for row in versions.stdout.splitlines():
        name,version,source,source_version=row.split('\t');short=name.split(':')[0]
        copyright=base/'usr/share/doc'/short/'copyright'
        if copyright.is_file():
            output=stage/'licenses/linux'/short;output.mkdir(parents=True,exist_ok=True);shutil.copy2(copyright,output/'copyright')
        sbom.append(dict(package=name,version=version,source=source,source_version=source_version,source_url='https://launchpad.net/ubuntu/+source/'+source+'/'+source_version))
    (stage/'licenses/linux-packages.json').write_text(json.dumps(sbom,indent=2)+'\n',encoding='utf-8')
    launcher='#!/bin/sh\nset -eu\nBASE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nexport LD_LIBRARY_PATH="$BASE/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\nexec "$BASE/python/bin/python3" "$BASE/launcher.py" "$@"\n'
    (stage/'ums-control').write_text(launcher, encoding='utf-8');(stage/'ums-control').chmod(0o755)
    (stage/'install.sh').write_text('#!/bin/sh\nset -eu\nBASE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nexport LD_LIBRARY_PATH="$BASE/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\nexec "$BASE/python/bin/python3" "$BASE/distribution.py" "$@"\n', encoding='utf-8');(stage/'install.sh').chmod(0o755)
    (stage/'uninstall.sh').write_text((stage/'install.sh').read_text(encoding='utf-8').replace('"$BASE/distribution.py" "$@"','"$BASE/distribution.py" --uninstall "$@"'),encoding='utf-8');(stage/'uninstall.sh').chmod(0o755)
    dist=ROOT/'dist';dist.mkdir(exist_ok=True)
    archive=dist/'ums-control-1.0.0-linux-x86_64.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for f in sorted(stage.rglob('*')):
            if f.is_file():z.write(f,'ums-control-1.0.0/'+f.relative_to(stage).as_posix())
    debroot=Path(tempfile.mkdtemp(prefix='deb-root-',dir=CACHE));payload=debroot/'opt/ums-control';payload.mkdir(parents=True,exist_ok=True);shutil.copytree(stage,payload,dirs_exist_ok=True,symlinks=False)
    control=debroot/'DEBIAN';control.mkdir(exist_ok=True)
    size=sum(f.stat().st_size for f in payload.rglob('*') if f.is_file())//1024
    (control/'control').write_text(f'Package: ums-control\nVersion: 1.0.0-1\nArchitecture: amd64\nMaintainer: N3ruk\nSection: video\nPriority: optional\nInstalled-Size: {size}\nDepends: libc6 (>= 2.35), debconf (>= 0.5) | debconf-2.0, iproute2\nRecommends: libgl1, libegl1, fonts-noto-cjk\nDescription: Independent per-device DLNA control panel for Universal Media Server\n Includes its own Python/Qt runtime. Does not start or install the UMS server.\n', encoding='utf-8')
    (control/'templates').write_text('Template: ums-control/first-language\nType: select\nChoices: English, Spanish, French, German, Italian, Chinese, Japanese\nDefault: English\nDescription: Select the language for the first launch of UMS Control.\n The language can also be changed later from the Language menu in the program.\n Existing user preferences are preserved.\n', encoding='utf-8')
    (control/'config').write_text('#!/bin/sh\nset -e\n. /usr/share/debconf/confmodule\ndb_input high ums-control/first-language || true\ndb_go\n', encoding='utf-8');(control/'config').chmod(0o755)
    (control/'postinst').write_text('''#!/bin/sh
set -e
if [ "$1" = configure ]; then
 . /usr/share/debconf/confmodule
 db_get ums-control/first-language
 case "$RET" in Spanish) lang=es;; French) lang=fr;; German) lang=de;; Italian) lang=it;; Chinese) lang=zh;; Japanese) lang=ja;; *) lang=en;; esac
 install -d -m 755 /etc/ums-control
 printf '%s\\n' "$lang" > /etc/ums-control/first-language
 chmod 644 /etc/ums-control/first-language
fi
''', encoding='utf-8');(control/'postinst').chmod(0o755)
    (control/'postrm').write_text('#!/bin/sh\nset -e\nif [ "$1" = purge ]; then\n . /usr/share/debconf/confmodule\n db_purge\n if [ -f /etc/ums-control/first-language ]; then unlink /etc/ums-control/first-language; fi\n rmdir --ignore-fail-on-non-empty /etc/ums-control 2>/dev/null || true\nfi\n', encoding='utf-8');(control/'postrm').chmod(0o755)
    bindir=debroot/'usr/bin';bindir.mkdir(parents=True,exist_ok=True);(bindir/'ums-control').write_text('#!/bin/sh\nexec /opt/ums-control/ums-control "$@"\n', encoding='utf-8');(bindir/'ums-control').chmod(0o755)
    desktop=debroot/'usr/share/applications';desktop.mkdir(parents=True,exist_ok=True);(desktop/'ums-control.desktop').write_text('[Desktop Entry]\nType=Application\nName=UMS Control\nComment=Per-device DLNA folders and playback settings\nExec=/opt/ums-control/ums-control\nIcon=/opt/ums-control/assets/ums-control.png\nTerminal=false\nCategories=AudioVideo;Settings;\nStartupWMClass=ums-control\n', encoding='utf-8')
    subprocess.run(['dpkg-deb','--root-owner-group','-Zxz','--build',str(debroot),str(dist/'ums-control_1.0.0-1_amd64.deb')],check=True)
    print('DEB and ZIP built; unresolved optional graphics libraries:',missing)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--base',required=True,help='Prepared Ubuntu 22.04 dependency build root');build(parser.parse_args())
