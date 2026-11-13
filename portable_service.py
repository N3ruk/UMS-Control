# SPDX-License-Identifier: GPL-3.0-or-later
"""Per-user process and session autostart, without admin rights or shell commands."""
import json,os,subprocess,sys,time
from pathlib import Path
import platform_support as p
import baul_core as c

def statefile():return c.CONFIG/'server-process.json'
def process():
    import psutil
    try:
        state=json.loads(statefile().read_text(encoding='utf-8'));proc=psutil.Process(state['pid'])
        if abs(proc.create_time()-state['created'])>.01:return None
        args=proc.cmdline()
        if str(c.PROFILE/'UMS.conf') not in ''.join(args) or 'net.pms.PMS' not in args:return None
        return proc if proc.is_running() and proc.status()!=psutil.STATUS_ZOMBIE else None
    except (OSError,ValueError,KeyError,psutil.Error):return None

def active():return 'active' if process() else 'inactive'
def autostart_path():
    if p.WINDOWS:return p.appdata(local=False)/'Microsoft/Windows/Start Menu/Programs/Startup/UMS Control Server.vbs'
    return c.HOME/'.config/autostart/ums-control-server.desktop'

def autostart_text():
    executable=Path(sys.executable)
    if getattr(sys,'frozen',False):argv=[str(executable),'--start-server']
    else:argv=[str(executable),str(p.ROOT/'launcher.py'),'--start-server']
    if p.WINDOWS:
        command=subprocess.list2cmdline(argv).replace('"','""')
        return 'CreateObject("WScript.Shell").Run "'+command+'", 0, False\r\n'
    from install import desktop_exec
    return '[Desktop Entry]\nType=Application\nName=UMS Control Server\nExec='+desktop_exec(executable)+' '+('' if getattr(sys,'frozen',False) else desktop_exec(p.ROOT/'launcher.py')+' ')+'--start-server\nTerminal=false\n'

def autostart():
    path=autostart_path()
    return path.is_file() and path.read_text(encoding='utf-8')==autostart_text()

def control(action):
    import psutil
    if action in ('enable','disable'):
        path=autostart_path()
        if path.exists() and not autostart():raise RuntimeError('Autostart entry belongs to another installation.')
        if action=='enable':c.atomic_write(path,autostart_text())
        else:path.unlink(missing_ok=True)
        return
    if action in ('stop','restart'):
        proc=process()
        if proc:
            children=proc.children(recursive=True)
            proc.terminate()
            try:proc.wait(timeout=25)
            except psutil.TimeoutExpired:proc.kill();proc.wait(timeout=5)
            for child in children:
                try:child.terminate()
                except psutil.Error:pass
            _,alive=psutil.wait_procs(children,timeout=5)
            for child in alive:
                try:child.kill()
                except psutil.Error:pass
        statefile().unlink(missing_ok=True)
    if action in ('start','restart') and not process():
        c.PROFILE.mkdir(parents=True,exist_ok=True)
        env=dict(os.environ,UMS_PROFILE=str(c.PROFILE/'UMS.conf'),PMS_HOME=str(c.RUNTIME))
        if not p.WINDOWS:env['LD_LIBRARY_PATH']=str(c.DATA/'native/usr/lib/x86_64-linux-gnu')
        with (c.PROFILE/'console.log').open('ab') as log:
            proc=subprocess.Popen(p.command(c.RUNTIME,c.PROFILE),cwd=c.RUNTIME,env=env,stdout=log,stderr=subprocess.STDOUT,**p.process_options())
        created=psutil.Process(proc.pid).create_time()
        c.atomic_write(statefile(),json.dumps(dict(pid=proc.pid,created=created)))
    if action not in ('start','stop','restart'):raise ValueError('Invalid service action')

def activity():
    import psutil
    root=process();result=[]
    if not root:return result
    try:children=root.children(recursive=True)
    except psutil.Error:return result
    for child in children:
        try:
            args=child.cmdline()
            if not args or Path(args[0]).stem!='ffmpeg' or '-i' not in args:continue
            def value(*keys):
                for key in keys:
                    if key in args and args.index(key)+1<len(args):return args[args.index(key)+1]
                return 'automático'
            result.append(dict(pid=child.pid,video=value('-c:v','-vcodec'),audio=value('-c:a','-acodec'),input=Path(value('-i')).name))
        except psutil.Error:pass
    return result
