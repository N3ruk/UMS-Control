# SPDX-License-Identifier: GPL-3.0-or-later
"""Small OS boundary shared by the identical Qt frontend and Java integration."""
import contextlib,json,os,shutil,socket,subprocess,sys,tarfile
from pathlib import Path
WINDOWS=os.name=='nt'
CODE_ROOT=Path(__file__).resolve().parent
ROOT=CODE_ROOT.parent if CODE_ROOT.name=='src' else CODE_ROOT
LOCK_EX=2;LOCK_NB=4

def flock(stream,flags):
    if WINDOWS:
        import msvcrt
        # Lock a single byte. Closing the file always releases the lock.
        stream.seek(0);stream.write('0');stream.flush();stream.seek(0)
        msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
    else:
        import fcntl
        fcntl.flock(stream,flags)

def appdata(local=True):
    name='LOCALAPPDATA' if local else 'APPDATA'
    if os.environ.get(name):return Path(os.environ[name])
    if WINDOWS:
        import ctypes
        buffer=ctypes.create_unicode_buffer(32768)
        if ctypes.windll.shell32.SHGetFolderPathW(None,28 if local else 26,None,0,buffer)==0 and buffer.value:return Path(buffer.value)
    return Path.home()/'AppData'/('Local' if local else 'Roaming')

def home_paths(home):
    if WINDOWS:
        base=appdata()/'UMS Control'
        return base/'preferences',base/'profiles',base/'server'
    return home/'.config/baul-media-control',home/'.config/baul-ums',home/'.local/share/baul-ums'

def clean_environment():
    env=dict(os.environ)
    # Private Qt libraries must never override the desktop's GIO, dpkg or systemctl.
    env.pop('LD_LIBRARY_PATH',None);env.pop('LD_PRELOAD',None)
    return env

def systemd():
    if WINDOWS:return False
    # The Linux DEB/ZIP can also work on desktops without a user systemd manager.
    return bool(shutil.which('systemctl') and os.environ.get('XDG_RUNTIME_DIR') and (Path(os.environ['XDG_RUNTIME_DIR'])/'systemd/private').exists())

def addresses():
    import psutil
    try:return [dict(ifname=n,addr_info=[dict(family='inet',local=a.address) for a in aa if a.family==socket.AF_INET]) for n,aa in psutil.net_if_addrs().items()]
    except (OSError,RuntimeError):return []

def networks():
    import psutil
    try:stats=psutil.net_if_stats();adapters=psutil.net_if_addrs()
    except (OSError,RuntimeError):return []
    result=[];counts={}
    for name,aa in sorted(adapters.items()):
        if not any(a.family==socket.AF_INET and not a.address.startswith('127.') for a in aa):continue
        kind='wifi' if any(s in name.lower() for s in ('wi-fi','wifi','wlan','wireless')) else 'ethernet'
        counts[kind]=counts.get(kind,0)+1
        result.append(dict(name=name,kind=kind,number=counts[kind],up=bool(stats.get(name) and stats[name].isup)))
    return result

def ffmpeg(runtime):return Path(runtime)/('bin/ffmpeg.exe' if WINDOWS else 'linux/ffmpeg')

def java(runtime):
    candidates=sorted(Path(runtime).glob('jre*/bin/'+('java.exe' if WINDOWS else 'java')))
    if len(candidates)!=1:raise RuntimeError('No se ha encontrado el entorno Java del servidor.')
    return candidates[0]

def command(runtime,profile):
    runtime=Path(runtime)
    return [str(java(runtime)),'-Xmx2048M','--enable-preview','--add-modules','jdk.incubator.vector','--add-opens','java.base/sun.nio.ch=ALL-UNNAMED','-Djna.nosys=true','-Djava.awt.headless=true','-Djava.net.preferIPv4Stack=true','-Dfile.encoding=UTF-8','-Djna.library.path='+str(runtime/'bin' if WINDOWS else runtime.parent/'native/usr/lib/x86_64-linux-gnu'),'-Dums.profile.path='+str(Path(profile)/'UMS.conf'),'-cp',os.pathsep.join(str(runtime/n) for n in ('update.jar','ums.jar')),'net.pms.PMS','console']

def process_options():return dict(creationflags=subprocess.CREATE_NO_WINDOW) if WINDOWS else dict(start_new_session=True)

def recycle(path):
    from send2trash import send2trash
    path=Path(path)
    if path.exists() or path.is_symlink():send2trash(str(path.absolute()))

def extract_deb(archive,target):
    """Read the ar container in Python, so non-Debian hosts need no dpkg."""
    if shutil.which('dpkg-deb'):
        subprocess.run(['dpkg-deb','-x',str(archive),str(target)],check=True,capture_output=True,env=clean_environment());return
    with Path(archive).open('rb') as stream:
        if stream.read(8)!=b'!<arch>\n':raise ValueError('Invalid ar package')
        while header:=stream.read(60):
            if len(header)!=60 or header[58:]!=b'`\n':raise ValueError('Invalid ar member')
            name=header[:16].decode().strip().rstrip('/');size=int(header[48:58]);start=stream.tell()
            if name.startswith('data.tar'):
                import io
                payload=stream.read(size)
                if len(payload)!=size:raise ValueError('Truncated Debian payload')
                if name.endswith('.zst'):
                    import zstandard
                    with zstandard.ZstdDecompressor().stream_reader(io.BytesIO(payload)) as raw:
                        with tarfile.open(fileobj=raw,mode='r|') as tf:tf.extractall(target,filter='data')
                else:
                    with tarfile.open(fileobj=io.BytesIO(payload),mode='r:*') as tf:tf.extractall(target,filter='data')
                return
            stream.seek(start+size+(size%2))
    raise ValueError('Missing Debian data archive')
