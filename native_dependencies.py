# SPDX-License-Identifier: GPL-3.0-or-later
"""Pinned upstream dependencies; downloaded, never redistributed by this project."""
import argparse, hashlib, json, os, tempfile, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
LOCK=ROOT/'server-support/dependencies.json'

def manifest():
    marker=ROOT/'distribution-marker.json'
    portable=marker.is_file() and json.loads(marker.read_text(encoding='utf-8')).get('native_baseline')=='jammy'
    return json.loads((ROOT/'server-support/dependencies-portable.json' if portable else LOCK).read_text(encoding='utf-8'))
def fetch(item,cache):
    cache=Path(cache);cache.mkdir(parents=True,exist_ok=True)
    target=cache/Path(item['url']).name
    def valid(path):
        if not path.is_file() or path.stat().st_size!=item['size']:return False
        with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()==item['sha256']
    if valid(target):return target
    descriptor,name=tempfile.mkstemp(prefix='.download-',dir=cache)
    try:
        with os.fdopen(descriptor,'wb') as output,urllib.request.urlopen(urllib.request.Request(item['url'],headers={'User-Agent':'UMS-Control/1.0'}),timeout=60) as response:
            remaining=item['size']+1
            while remaining:
                chunk=response.read(min(1024*1024,remaining))
                if not chunk:break
                output.write(chunk);remaining-=len(chunk)
        if not valid(Path(name)):raise RuntimeError('La descarga no coincide con la huella esperada: '+target.name)
        os.replace(name,target)
    finally:
        Path(name).unlink(missing_ok=True)
    return target

def packages(cache):return [fetch(item,cache) for item in manifest()['packages']]
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=ROOT/'.cache/upstream')
    parser.add_argument('--sources',action='store_true',help='Fetch exact corresponding Ubuntu source packages too')
    args=parser.parse_args();items=list(manifest()['packages'])
    if args.sources:items += [f for source in manifest()['sources'] for f in source['files']]
    for item in items:print(fetch(item,args.cache))
if __name__=='__main__':main()
