#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only UI verification with synthetic profiles and no server actions."""
import argparse,copy,json,os,sys
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from PyQt6.QtWidgets import QApplication,QScrollArea
import baul_gui as g,baul_core as c

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'.cache/ui-verification');args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
 app=QApplication.instance() or QApplication([]);g.configure_theme(app,'current');state=c.defaults();state['tvs']=[c.editable_tv(c.default_tv('Synthetic device','192.168.1.20'))]
 with ExitStack() as stack:
  for item in [patch.object(g.Window,'refresh'),patch.object(g.Window,'check_updates'),patch.object(c,'load_state',side_effect=lambda:copy.deepcopy(state)),patch.object(g.appearance,'load',return_value=dict(theme='current',language='es')),patch.object(g.appearance,'save')]:stack.enter_context(item)
  apply=stack.enter_context(patch.object(c,'apply'));service=stack.enter_context(patch.object(c,'service'))
  w=g.Window();w.timer.stop();w.show();app.processEvents();views=0
  for theme in g.appearance.THEMES:
   w.set_theme(theme)
   for language in g.appearance.LANGUAGES:
    w.set_ui_language(language)
    for width,height in [(1140,840),(860,620)]:
     w.resize(width,height);app.processEvents();scroll=w.tabs.widget(0)
     assert scroll.horizontalScrollBar().maximum()==0,(theme,language,width)
     if language=='es' and width==1140:assert scroll.verticalScrollBar().maximum()==0,(theme,scroll.verticalScrollBar().maximum())
     for tab in range(w.tabs.count()):
      w.tabs.setCurrentIndex(tab);app.processEvents()
      assert not [a for a in w.findChildren(QScrollArea) if a.isVisible() and a.horizontalScrollBar().maximum()>0],(theme,language,width,tab)
      views+=1
   w.set_ui_language('es');w.resize(1140,840);w.tabs.setCurrentIndex(0);app.processEvents();assert w.grab().save(str(args.output/(theme+'-summary.png')))
  apply.assert_not_called();service.assert_not_called();w.dirty=False;w.close()
 (args.output/'verification.json').write_text(json.dumps(dict(passed=True,views=views,themes=6,languages=7,server_actions=0),indent=2)+'\n', encoding='utf-8');print('UI views passed:',views)
if __name__=='__main__':main()
