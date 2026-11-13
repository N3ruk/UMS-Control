#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Download exact build inputs. All input bytes are checked before extraction."""
import argparse,json,os,subprocess,sys,tarfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));from native_dependencies import fetch
CACHE=ROOT/'.cache/distribution-20261113'
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--windows',action='store_true');args=parser.parse_args();spec=json.loads((ROOT/'packaging/inputs.json').read_text(encoding='utf-8'));CACHE.mkdir(parents=True,exist_ok=True)
 platform='windows' if args.windows else 'linux';entry=spec[platform+'_python'];download=fetch(entry,CACHE/'inputs');target=CACHE/('windows-python' if args.windows else 'linux-toolchain')
 if not target.exists():
  target.mkdir()
  if args.windows:
   with zipfile.ZipFile(download) as z:z.extractall(target)
   (target/'python312._pth').write_text('python312.zip\n.\nLib/site-packages\nimport site\n',encoding='utf-8')
  else:
   with tarfile.open(download) as t:t.extractall(target,filter='data')
 wheels=CACHE/(platform+'-wheels');wheels.mkdir(exist_ok=True)
 for entry in spec[platform+'_wheels']:
  file=fetch(entry,wheels)
  if file.name!=entry['name']:file.rename(wheels/entry['name'])
 if args.windows:
  seven=fetch(spec['7zip'],CACHE/'inputs');subprocess.run(['7z','x','-y',str(seven),'-o'+str(CACHE/'7zip-full')],check=True)
  # These locked wheels contain only importable files, with no script/data scheme.
  # Installing their verified contents also works with embedded Python without pip.
  site=target/'Lib/site-packages';site.mkdir(parents=True,exist_ok=True)
  for item in spec['windows_wheels']:
   with zipfile.ZipFile(wheels/item['name']) as wheel:
    if any('.data/' in name or '..' in Path(name).parts or Path(name).is_absolute() for name in wheel.namelist()):raise RuntimeError('Unsupported wheel layout: '+item['name'])
    wheel.extractall(site)
  source=str(ROOT/'src') if os.name=='nt' else 'Z:'+str(ROOT/'src').replace('/','\\')
  (target/'python312._pth').write_text('python312.zip\n.\nLib/site-packages\n'+source+'\nimport site\n',encoding='utf-8')
  print('Windows Python and locked wheels prepared without system installation. Run packaging/build_windows.py; cross-builds require Wine.')
 else:
  subprocess.run([str(target/'python/bin/python3'),'-m','pip','install','--no-index','--find-links',str(wheels),'PyQt6==6.5.3','PyQt6-Qt6==6.5.3','PyQt6-sip==13.10.2','psutil==7.2.2','Send2Trash==2.1.0','zstandard==0.25.0'],check=True)
  # Keep stable names expected by the build recipe while preserving verified input bytes.
  import shutil;shutil.copy2(download,CACHE/'python-linux.tar.gz')
if __name__=='__main__':main()
