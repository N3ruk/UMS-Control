#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 N3ruk
"""Original geometric public artwork; no imported wallpaper, logo or characters."""
import argparse,hashlib,json,os,sys
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PyQt6.QtGui import QImage,QPainter,QColor,QLinearGradient,QPen,QPainterPath
from PyQt6.QtCore import Qt,QRectF
from PyQt6.QtWidgets import QApplication
PALETTES={'current':('#071427','#183e64','#69bde8'),'green':('#101e15','#40552a','#dfd36f'),'ugm':('#130e27','#48305d','#5ed4ef'),'anime':('#152338','#71515a','#efb269')}
def render(directory):
 directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
 app=QApplication.instance() or QApplication([])
 for name,(dark,mid,accent) in PALETTES.items():
  image=QImage(1600,1000,QImage.Format.Format_RGB32);p=QPainter(image);p.setRenderHint(QPainter.RenderHint.Antialiasing)
  gradient=QLinearGradient(0,0,1600,1000);gradient.setColorAt(0,QColor(dark));gradient.setColorAt(1,QColor(mid));p.fillRect(image.rect(),gradient)
  for i in range(8):
   color=QColor(accent);color.setAlpha(12+i*3);p.setPen(QPen(color,2));p.setBrush(Qt.BrushStyle.NoBrush);p.drawEllipse(QRectF(900+i*28,100-i*24,520+i*55,520+i*55))
  for i in range(5):
   color=QColor(accent);color.setAlpha(10+i*4);p.setBrush(color);p.setPen(Qt.PenStyle.NoPen);path=QPainterPath();path.moveTo(0,650+i*45);path.cubicTo(600,430+i*50,950,1050-i*65,1600,600+i*60);path.lineTo(1600,1000);path.lineTo(0,1000);p.drawPath(path)
  p.end();assert image.save(str(directory/(name+'-background.png')))
 image=QImage(512,512,QImage.Format.Format_ARGB32);image.fill(Qt.GlobalColor.transparent);p=QPainter(image);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor('#172c46'));p.drawRoundedRect(QRectF(12,12,488,488),100,100);p.setBrush(QColor('#71d4ed'));p.drawRoundedRect(QRectF(90,115,332,220),24,24);p.setBrush(QColor('#172c46'));path=QPainterPath();path.moveTo(220,165);path.lineTo(220,285);path.lineTo(315,225);path.closeSubpath();p.drawPath(path);p.setBrush(QColor('#71d4ed'));p.drawRoundedRect(QRectF(160,370,192,25),12,12);p.end();assert image.save(str(directory/'ums-control.png'))
 files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*.png')}
 (directory/'ORIGIN.md').write_text('# Public artwork\n\nCopyright (C) 2026 N3ruk. GPL-3.0-or-later.\n\nAll five PNG files are original geometric renders from `tools/render_assets.py`. No third-party artwork, characters, logos, photos, fonts or private wallpapers are incorporated. The script is the preferred editable source. Theme identifiers are compatibility identifiers, not third-party endorsements.\n\n'+''.join('- `'+n+'`: SHA256 `'+h+'`\n' for n,h in sorted(files.items())), encoding='utf-8')
 return files
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();print(json.dumps(render(args.output)))
if __name__=='__main__':main()
