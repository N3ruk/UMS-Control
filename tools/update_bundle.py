#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Refresh integrity metadata after an intentional source/native lock revision."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    support=ROOT/'server-support';names=['dependencies.json','dependencies-portable.json','upstream.json','update.jar','update-windows.jar','runtime-manifest.json','native-manifest.json']
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    (support/'bundle.json').write_text(json.dumps({n:digest(support/n) for n in names},indent=2)+'\n', encoding='utf-8')
    path=ROOT/'server_manager.py';s=path.read_text(encoding='utf-8');s=re.sub(r"BUNDLE_SHA='[a-f0-9]{64}'","BUNDLE_SHA='"+digest(support/'bundle.json')+"'",s);path.write_text(s, encoding='utf-8')
    print('Integrity metadata refreshed')
if __name__=='__main__':main()
