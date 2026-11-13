#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Rootless Ubuntu 24.04 test environment. Does not install anything on the host."""
import hashlib,json,shutil,subprocess,sys,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from native_dependencies import fetch
BASE=ROOT/'.cache/ubuntu24-root'
URL='https://cdimage.ubuntu.com/ubuntu-base/releases/24.04/release/ubuntu-base-24.04.3-base-amd64.tar.gz'
SHA='6bc2cde3930ad088b3bb46fa45279e96d25bc3810f209850ecbe4722711874f9'
PACKAGES=['python3','python3-pyqt6','python3-psutil','python3-send2trash','python3-zstandard','qt6-translations-l10n','openjdk-17-jdk-headless','iproute2','libglib2.0-bin','desktop-file-utils','libcurl3t64-gnutls','libmms0','ffmpeg','fonts-dejavu-core','ca-certificates','systemd','dbus-bin','dbus-daemon']
def sandbox(argv):
    return ['bwrap','--bind',str(BASE),'/', '--bind',str(ROOT),'/src','--dev','/dev','--proc','/proc','--unshare-user','--uid','1000','--gid','1000','--chdir','/src','--setenv','HOME','/tmp/ums-test-user','--setenv','LANG','C.UTF-8','--setenv','PATH','/usr/sbin:/usr/bin:/sbin:/bin','--unsetenv','PYTHONPATH','--setenv','QT_QPA_PLATFORM','offscreen','--setenv','XDG_RUNTIME_DIR','/tmp/ums-test-run','--unsetenv','DBUS_SESSION_BUS_ADDRESS',*argv]
def main():
    cache=ROOT/'.cache';cache.mkdir(exist_ok=True);archive=cache/'ubuntu-base-24.04.3-base-amd64.tar.gz'
    if not archive.is_file():
        import urllib.request
        with urllib.request.urlopen(URL,timeout=60) as source,archive.open('wb') as target:shutil.copyfileobj(source,target)
    with archive.open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
    if actual!=SHA:raise RuntimeError('Ubuntu Base checksum mismatch')
    if not (BASE/'bin/bash').exists():
        BASE.mkdir(parents=True,exist_ok=True);subprocess.run(['tar','--no-same-owner','-xzf',str(archive),'-C',str(BASE)],check=True,capture_output=True)
    resolver=BASE/'etc/resolv.conf'
    if resolver.is_symlink():resolver.unlink()
    resolver.write_bytes(Path('/etc/resolv.conf').read_bytes())
    cert=BASE/'etc/ssl/certs/ca-certificates.crt';cert.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile('/etc/ssl/certs/ca-certificates.crt',cert)
    for sources in list((BASE/'etc/apt').rglob('*.sources'))+list((BASE/'etc/apt').glob('sources.list')):
        sources.write_text(sources.read_text(encoding='utf-8').replace('http://','https://'), encoding='utf-8')
    (BASE/'etc/apt/apt.conf.d/00rootless').write_text('APT::Sandbox::User "root";\n', encoding='utf-8')
    (BASE/'usr/local/share/fonts').mkdir(parents=True,exist_ok=True)
    (BASE/'etc/machine-id').write_text(__import__('uuid').uuid4().hex+'\n', encoding='utf-8')
    (BASE/'tmp/ums-test-run').mkdir(mode=0o700,parents=True,exist_ok=True)
    (BASE/'tmp/ums-test-user').mkdir(parents=True,exist_ok=True)
    (BASE/'usr/sbin/policy-rc.d').write_text('#!/bin/sh\nexit 101\n', encoding='utf-8');(BASE/'usr/sbin/policy-rc.d').chmod(0o755)
    argv=sandbox(['/bin/sh','-ec','export DEBIAN_FRONTEND=noninteractive; apt-get update; apt-get remove -y dbus; apt-get install -y --no-install-recommends '+' '.join(PACKAGES)])
    # Fake root inside the user namespace is necessary only for apt in this throwaway root.
    argv[argv.index('--uid')+1]='0';argv[argv.index('--gid')+1]='0'
    with (cache/'ubuntu24-apt.log').open('w') as log:result=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT)
    if result.returncode:
        print((cache/'ubuntu24-apt.log').read_text(encoding='utf-8')[-2500:]);raise SystemExit(result.returncode)
    print('Ubuntu 24.04 clean test root ready; host untouched')
if __name__=='__main__':main()
