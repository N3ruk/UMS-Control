# SPDX-License-Identifier: GPL-3.0-or-later
"""Common application entry point for source, DEB, ZIP and Windows EXE."""
import json,os,sys
from pathlib import Path

def main():
    if '--version' in sys.argv:print('UMS Control 1.0.0');return 0
    if '--uninstall-panel' in sys.argv:
        import baul_core as c
        c.service('stop');c.service('disable');return 0
    if '--start-server' in sys.argv:
        import server_manager as manager
        manager.control('start');return 0
    if '--self-test' in sys.argv:
        import platform_support as p,server_manager as m,first_run
        from PyQt6.QtWidgets import QApplication
        import baul_gui as g
        m.verify_bundle();app=QApplication([]);g.configure_theme(app,'current')
        assert set(first_run.LANGUAGES)==set(g.appearance.LANGUAGES)
        g.set_language('en')
        report=dict(passed=True,version='1.0.0',platform=sys.platform,languages=7,qt=app.style().objectName(),session_label=g.tr('Iniciar el servidor al entrar en mi sesión de Ubuntu'))
        if '--report' in sys.argv:Path(sys.argv[sys.argv.index('--report')+1]).write_text(json.dumps(report,indent=2), encoding='utf-8')
        if sys.stdout:print(json.dumps(report))
        return 0
    if '--screenshots' in sys.argv:
        from distribution import screenshots
        return screenshots(Path(sys.argv[sys.argv.index('--screenshots')+1]))
    import baul_gui
    return baul_gui.main()
if __name__=='__main__':sys.exit(main())
