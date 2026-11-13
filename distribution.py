# SPDX-License-Identifier: GPL-3.0-or-later
"""Per-user ZIP installation and truthful, synthetic-data product screenshots."""
import argparse,json,os,shlex,shutil,sys,tempfile
from pathlib import Path
import first_run
import platform_support as p

def install_zip(language):
    if hasattr(os,'geteuid') and os.geteuid()==0:raise RuntimeError('Run install.sh as the desktop user, not root.')
    import baul_core as c
    from install import desktop_exec
    language=first_run.choose(language)
    target=c.HOME/'.local/share/ums-control';target.parent.mkdir(parents=True,exist_ok=True)
    if target.is_symlink():raise RuntimeError('Installation target is a symbolic link; it will not be modified.')
    with tempfile.TemporaryDirectory(prefix='.ums-control-',dir=target.parent) as temp:
        staged=Path(temp)/'new';shutil.copytree(p.ROOT,staged,ignore=shutil.ignore_patterns('__pycache__','.cache','.git'))
        (staged/'first-language.json').write_text(json.dumps(dict(language=language)), encoding='utf-8')
        if target.exists():
            if not (target/'distribution-marker.json').is_file():raise RuntimeError('Existing directory is not a managed UMS Control installation.')
            # Use desktop trash, retaining old application files but no duplicate settings.
            p.recycle(target)
        staged.rename(target)
    bindir=c.HOME/'.local/bin';bindir.mkdir(parents=True,exist_ok=True)
    launcher=bindir/'ums-control';c.atomic_write(launcher,'#!/bin/sh\nexec '+shlex.quote(str(target/'ums-control'))+' "$@"\n');launcher.chmod(0o755)
    desktop=c.HOME/'.local/share/applications/ums-control.desktop'
    c.atomic_write(desktop,'[Desktop Entry]\nType=Application\nName=UMS Control\nComment=Per-device DLNA folders and playback settings\nExec='+desktop_exec(launcher)+'\nIcon='+str(target/'assets/ums-control.png')+'\nTerminal=false\nCategories=AudioVideo;Settings;\nStartupWMClass=ums-control\n')
    print('UMS Control installed:',launcher);print(first_run.NOTICE)

def uninstall_zip():
    import baul_core as c
    target=c.HOME/'.local/share/ums-control'
    if target.resolve()!=p.ROOT.resolve() or not (target/'distribution-marker.json').is_file():raise RuntimeError('Run uninstall.sh from the managed user installation.')
    c.service('stop');c.service('disable')
    launcher=c.HOME/'.local/bin/ums-control'
    if launcher.is_file() and str(target/'ums-control') in launcher.read_text(encoding='utf-8'):p.recycle(launcher)
    desktop=c.HOME/'.local/share/applications/ums-control.desktop'
    if desktop.is_file() and str(target/'assets/ums-control.png') in desktop.read_text(encoding='utf-8'):p.recycle(desktop)
    p.recycle(target)
    print('UMS Control removed. Server binaries, preferences, profiles and media have been preserved.')

def screenshots(output):
    """Real Qt rendering, explicitly labelled demonstration data in documentation."""
    from contextlib import ExitStack
    from unittest.mock import patch
    import copy
    from PyQt6.QtWidgets import QApplication
    import baul_gui as g,baul_core as c
    output.mkdir(parents=True,exist_ok=True)
    app=QApplication.instance() or QApplication([]);g.configure_theme(app,'current')
    state=dict(version=2,name='UMS Control',interface='demo-interface',tvs=[]);state['name']='UMS Control';state['tvs']=[c.editable_tv(c.default_tv('Living room','192.168.50.20')),c.editable_tv(c.default_tv('Game console','192.168.50.30'))]
    state['tvs'][0]['mode']='direct'
    with ExitStack() as stack:
        for item in [patch.object(c,'network_interfaces',return_value=[dict(name='demo-interface',kind='ethernet',number=1,up=True)]),patch.object(g.Window,'refresh'),patch.object(g.Window,'check_updates'),patch.object(c,'load_state',side_effect=lambda:copy.deepcopy(state)),patch.object(g.appearance,'load',return_value=dict(theme='current',language='en')),patch.object(g.appearance,'save')]:stack.enter_context(item)
        w=g.Window(preferences=dict(theme='current',language='en'));w.timer.stop();w.resize(1140,840);w.update_server_buttons(dict(present=False,kind='absent',repairable=True,status='inactive'));w.status.setText(g.tr('Servidor no instalado'));w.render_activity(dict(devices=[],activity=[],status='inactive'));w.dirty=False;w.message.setText(g.tr('Sin cambios pendientes'));w.show();app.processEvents()
        for theme in g.appearance.THEMES:
            w.set_theme(theme);app.processEvents()
            for tab,name in [(0,'summary'),(1,'devices')]:
                w.tabs.setCurrentIndex(tab);app.processEvents()
                image=w.grab()
                if not image.save(str(output/(theme+'-'+name+'.png'))):raise RuntimeError('Screenshot failed')
                if theme=='current' and not image.save(str(output/(name+'.png'))):raise RuntimeError('Screenshot failed')
        w.dirty=False;w.close()
    (output/'capture.json').write_text(json.dumps(dict(platform=sys.platform,language='en',synthetic_data=True,version='1.0.0',themes=list(g.appearance.THEMES)),indent=2), encoding='utf-8')
    return 0

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--language',choices=first_run.LANGUAGES);parser.add_argument('--uninstall',action='store_true');args=parser.parse_args()
    if args.uninstall:uninstall_zip()
    else:install_zip(args.language)
if __name__=='__main__':main()
