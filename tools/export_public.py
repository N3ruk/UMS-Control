#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Validate or export only the explicit public source allowlist."""
import argparse,hashlib,json,re,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MANIFEST='packaging/source-manifest.json'
BLOCKED_PARTS={'.cache','__pycache__','.git'}

def safe_path(name):
    path=Path(name)
    if path.is_absolute() or '..' in path.parts or BLOCKED_PARTS.intersection(path.parts):
        raise ValueError('Unsafe path: '+name)
    return path

def source_hashes():
    files=json.loads((ROOT/'packaging/public-files.json').read_text(encoding='utf-8'))['files']
    if len(files)!=len(set(files)):raise ValueError('Duplicate public path')
    hashes={}
    for name in files:
        path=ROOT/safe_path(name)
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT) or not path.is_file():raise ValueError('Invalid public source: '+name)
        if path.suffix in {'.deb','.tgz','.log','.pyc'} or path.name.startswith('test_'):raise ValueError('Development file in public source: '+name)
        if path.suffix not in {'.jar','.png'}:
            content=path.read_text(encoding='utf-8')
            if re.search(('/'+'home'+r'/[^/\s]+/|'+'/'+'run/media'+r'/[^/\s]+/|docs/CONTINUAR\.md|192\.168\.1\.(?:133|141|149)\b'),content):raise ValueError('Private workstation data: '+name)
        hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    runtime=json.loads((ROOT/'packaging/runtime-files.json').read_text(encoding='utf-8'))
    if len(set(runtime.values()))!=len(runtime):raise ValueError('Duplicate runtime destination')
    for name,destination in runtime.items():
        safe_path(destination)
        if name not in hashes:raise ValueError('Non-public runtime source: '+name)
        if Path(name).parts[0] in {'tools','packaging','.github'}:raise ValueError('Development tool in runtime: '+name)
    return dict(sorted(hashes.items()))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--update-manifest',action='store_true')
    parser.add_argument('--destination',type=Path)
    args=parser.parse_args();hashes=source_hashes();manifest=ROOT/MANIFEST
    serialized=json.dumps(hashes,indent=2)+'\n'
    if args.update_manifest:manifest.write_text(serialized,encoding='utf-8')
    elif not manifest.is_file() or json.loads(manifest.read_text(encoding='utf-8'))!=hashes:raise ValueError('Source manifest is stale; run --update-manifest after reviewing changes')
    if args.destination:
        target=args.destination.resolve()
        if target==ROOT or ROOT.is_relative_to(target):raise ValueError('Destination must not contain the source tree')
        if target.exists() and any(target.iterdir()):raise ValueError('Destination must be empty')
        target.mkdir(parents=True,exist_ok=True)
        for name in [*hashes,MANIFEST]:
            out=target/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,out)
    print('Public source validated:',len(hashes),'files; runtime:',len(json.loads((ROOT/'packaging/runtime-files.json').read_text(encoding='utf-8'))),'files')
if __name__=='__main__':main()
