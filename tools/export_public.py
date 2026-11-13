#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit source allowlist. Export an ordinary directory, never a package."""
import argparse,hashlib,json,re,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
BLOCKED_PARTS={'.cache','__pycache__','.git'}
def listing():
 spec=json.loads((ROOT/'public-files.json').read_text(encoding='utf-8'));files=spec['files']
 if len(files)!=len(set(files)):raise ValueError('Duplicate public path')
 for name in files:
  path=Path(name)
  if path.is_absolute() or '..' in path.parts or BLOCKED_PARTS.intersection(path.parts) or path.suffix in {'.deb','.tgz','.log','.pyc'}:raise ValueError('Unsafe public path: '+name)
  if not (ROOT/path).is_file():raise ValueError('Missing public source: '+name)
  if (ROOT/path).is_symlink() or not (ROOT/path).resolve().is_relative_to(ROOT.resolve()):raise ValueError('Public source must not escape through a symlink: '+name)
 return spec

def check():
 spec=listing();issues=[]
 # Detect accidental workstation paths or links into private diagnostic trees.
 for name in spec['files']:
  path=ROOT/name
  if path.suffix in {'.jar','.png'}:continue
  text=path.read_text(encoding='utf-8')
  if re.search(('/'+'home'+r'/[^/\s]+/|'+'/'+'run/media'+r'/[^/\s]+/|docs/CONTINUAR\.md|192\.168\.1\.(?:133|141|149)\b'),text):issues.append(name)
 if issues:raise ValueError('Private workstation data found: '+', '.join(issues))
 return spec

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');parser.add_argument('--destination',type=Path);parser.add_argument('--refresh',action='store_true');args=parser.parse_args();spec=check()
 if args.destination:
  target=args.destination.resolve()
  if target==ROOT or ROOT.is_relative_to(target):raise ValueError('Destination must not contain the source tree')
  if target.exists() and not args.refresh:raise ValueError('Destination exists; choose a new directory or explicit --refresh')
  target.mkdir(parents=True,exist_ok=True)
  for name in spec['files']:
   destination=target/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,destination)
  from tools.render_assets import render
  render(target/'assets')
  paths=spec['files']+['assets/'+name for name in spec['generated_assets']]
  hashes={name:hashlib.sha256((target/name).read_bytes()).hexdigest() for name in sorted(paths)}
  (target/'PUBLIC-MANIFEST.json').write_text(json.dumps(hashes,indent=2)+'\n', encoding='utf-8')
  print('Public source directory ready:',target,'files:',len(hashes))
 else:print('Public source allowlist validated:',len(spec['files']),'files; private artwork excluded')
if __name__=='__main__':main()
