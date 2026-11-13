#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Provision the pinned test runtime, without reading or controlling user UMS."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from native_dependencies import fetch,packages

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cache',type=Path,default=ROOT/'.cache');parser.add_argument('--sources',action='store_true');args=parser.parse_args()
    spec=json.loads((ROOT/'server-support/upstream.json').read_text(encoding='utf-8'))
    print(fetch(spec['runtime'],args.cache))
    if args.sources:print(fetch(spec['source'],args.cache/'upstream'))
    for p in packages(args.cache/'upstream'):print(p)
if __name__=='__main__':main()
