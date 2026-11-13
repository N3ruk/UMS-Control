#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Rebuild twice from verified clean upstream, compare with shipped Java overrides."""
import hashlib,importlib.util,json,sys,tarfile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from native_dependencies import fetch
spec=importlib.util.spec_from_file_location('patch_builder',ROOT/'patches/build.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
def main():
 upstream=json.loads((ROOT/'server-support/upstream.json').read_text(encoding='utf-8'));archive=fetch(upstream['runtime'],ROOT/'.cache')
 with tempfile.TemporaryDirectory(prefix='ums-rebuild-') as temp:
  temp=Path(temp)
  with tarfile.open(archive) as tf:
   member=tf.getmember('ums-15.9.0/ums.jar');tf.extract(member,temp,filter='data')
  for name in ['one.jar','two.jar']:builder.build(temp/'ums-15.9.0/ums.jar',temp/name)
  assert (temp/'one.jar').read_bytes()==(temp/'two.jar').read_bytes()==(ROOT/'server-support/update.jar').read_bytes(),'Java output is not reproducible with this compiler'
  print('Two clean builds match shipped update.jar:',hashlib.sha256((temp/'one.jar').read_bytes()).hexdigest())
if __name__=='__main__':main()
